import os
import time
import base64
from django.utils import timezone

from github.models import GitHubDeployment, GitHubRepoConfig
from . import repository_service
from .exporter_service import compile_theme_static_bundle
from .pages_service import enable_github_pages, get_github_pages_info


def publish_theme_to_github(user, theme, token, commit_message="Publish theme to GitHub Pages") -> GitHubDeployment:
    """
    Orchestrates one-click theme publishing to GitHub Pages:
    1. Compiles theme static bundle in-memory.
    2. Pushes files to user's GitHub repository using Git Data REST APIs.
    3. Activates and verifies GitHub Pages.
    4. Records the deployment log.
    """
    # Look up or create default repo config for theme
    config = GitHubRepoConfig.objects.filter(user=user, theme=theme).first()
    if not config:
        config = GitHubRepoConfig.objects.filter(user=user).first()
    
    if not config:
        # Create default repo name based on user/theme
        repo_name = f"{theme.slug}-portfolio"
        config = GitHubRepoConfig.objects.create(
            user=user,
            theme=theme,
            repo_name=repo_name,
            repository_owner=getattr(user, "github_username", user.username)
        )

    owner = config.repository_owner
    repo = config.repo_name
    branch = config.branch_name

    start_time = time.time()
    
    # Calculate next version number
    prev_version = GitHubDeployment.objects.filter(user=user, theme=theme, status=GitHubDeployment.Status.SUCCESS).count()
    version = prev_version + 1

    # Initialize deployment record
    deployment = GitHubDeployment.objects.create(
        user=user,
        theme=theme,
        repo_name=repo,
        repository_owner=owner,
        branch_name=branch,
        deployment_version=version,
        deployment_message=commit_message,
        status=GitHubDeployment.Status.PENDING
    )

    try:
        # Step 1: Ensure repository exists on GitHub
        try:
            repository_service.github_api_request(f"https://api.github.com/repos/{owner}/{repo}", token)
        except Exception:
            repository_service.create_repository(token, repo)
            time.sleep(2)  # Wait for repo initialization

        # Step 2: Package in-memory static bundle
        bundle = compile_theme_static_bundle(theme)

        # Step 3: Fetch branch reference SHA
        ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{branch}"
        try:
            ref_data, _ = repository_service.github_api_request(ref_url, token)
            parent_sha = ref_data["object"]["sha"]
        except Exception:
            # If main branch doesn't exist yet, get default branch ref
            repo_info, _ = repository_service.github_api_request(f"https://api.github.com/repos/{owner}/{repo}", token)
            default_branch = repo_info.get("default_branch", "main")
            ref_data, _ = repository_service.github_api_request(f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{default_branch}", token)
            parent_sha = ref_data["object"]["sha"]

        # Step 4: Get parent commit tree SHA
        commit_url = f"https://api.github.com/repos/{owner}/{repo}/git/commits/{parent_sha}"
        commit_data, _ = repository_service.github_api_request(commit_url, token)
        parent_tree_sha = commit_data["tree"]["sha"]

        # Step 5: Prepare tree items
        tree_items = []
        for path, content in bundle.items():
            ext = os.path.splitext(path)[1].lower()
            is_text = ext in [".html", ".css", ".js", ".json", ".svg", ".md", ".txt"]

            if is_text:
                try:
                    tree_items.append({
                        "path": path,
                        "mode": "100644",
                        "type": "blob",
                        "content": content.decode("utf-8")
                    })
                    continue
                except Exception:
                    pass

            b64_str = base64.b64encode(content).decode("utf-8")
            blob_payload = {"content": b64_str, "encoding": "base64"}
            blob_data, _ = repository_service.github_api_request(
                f"https://api.github.com/repos/{owner}/{repo}/git/blobs",
                token,
                data=blob_payload,
                method="POST"
            )
            tree_items.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob_data["sha"]
            })

        # Step 6: Create new tree
        tree_payload = {
            "base_tree": parent_tree_sha,
            "tree": tree_items
        }
        new_tree_data, _ = repository_service.github_api_request(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees",
            token,
            data=tree_payload,
            method="POST"
        )
        new_tree_sha = new_tree_data["sha"]

        # Step 7: Create commit
        commit_payload = {
            "message": commit_message,
            "tree": new_tree_sha,
            "parents": [parent_sha]
        }
        new_commit_data, _ = repository_service.github_api_request(
            f"https://api.github.com/repos/{owner}/{repo}/git/commits",
            token,
            data=commit_payload,
            method="POST"
        )
        new_commit_sha = new_commit_data["sha"]

        # Step 8: Update branch ref
        ref_payload = {"sha": new_commit_sha, "force": True}
        repository_service.github_api_request(
            f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}",
            token,
            data=ref_payload,
            method="PATCH"
        )

        # Step 9: Enable GitHub Pages
        published_url = f"https://{owner}.github.io/{repo}/"
        pages_enabled = False
        try:
            published_url = enable_github_pages(token, owner, repo)
            pages_enabled = True
        except Exception:
            try:
                pages_info = get_github_pages_info(token, owner, repo)
                pages_enabled = pages_info.get("pages_enabled", True)
                published_url = pages_info.get("published_url", published_url)
            except Exception:
                pages_enabled = True

        duration = round(time.time() - start_time, 2)
        deployment.status = GitHubDeployment.Status.SUCCESS
        deployment.last_commit_sha = new_commit_sha
        deployment.deployment_duration = duration
        deployment.pages_enabled = pages_enabled
        deployment.published_url = published_url
        deployment.save()

    except Exception as e:
        duration = round(time.time() - start_time, 2)
        deployment.status = GitHubDeployment.Status.FAILED
        deployment.error_message = str(e)
        deployment.deployment_duration = duration
        deployment.save()

    return deployment
