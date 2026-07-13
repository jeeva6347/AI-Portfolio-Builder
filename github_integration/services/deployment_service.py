import os
import time
import base64
from django.utils import timezone

from github_integration.models import GitHubDeployment
from . import repository_service
from .exporter_service import compile_portfolio_static_bundle
from .pages_service import enable_github_pages, get_github_pages_info


def publish_portfolio_to_github(portfolio, token, commit_message="Update portfolio site via AI Portfolio Builder") -> GitHubDeployment:
    """
    Orchestrates the entire one-click publication workflow:
    1. Compiles static site in-memory.
    2. Pushes files to GitHub using Git Data REST APIs.
    3. Activates and verifies GitHub Pages.
    4. Records the metadata history log.
    """
    config = getattr(portfolio, "github_config", None)
    if not config:
        raise Exception("Portfolio is not connected to a repository configuration.")

    owner = config.repository_owner
    repo = config.repo_name
    branch = config.branch_name

    start_time = time.time()
    
    # Calculate next version number
    prev_version = portfolio.deployments.filter(status=GitHubDeployment.Status.SUCCESS).count()
    version = prev_version + 1

    # Initialize deployment record
    deployment = GitHubDeployment.objects.create(
        portfolio=portfolio,
        repo_name=repo,
        repository_owner=owner,
        branch_name=branch,
        deployment_version=version,
        deployment_message=commit_message,
        status=GitHubDeployment.Status.PENDING
    )

    try:
        # Step 1: Package in-memory static bundle
        bundle = compile_portfolio_static_bundle(portfolio)

        # Step 2: Push changes to GitHub using Git Data APIs
        # A. Fetch branch reference to get parent commit SHA
        ref_url = f"https://api.github.com/repos/{owner}/{repo}/git/ref/heads/{branch}"
        ref_data, _ = repository_service.github_api_request(ref_url, token)
        parent_sha = ref_data["object"]["sha"]

        # B. Get parent commit tree SHA
        commit_url = f"https://api.github.com/repos/{owner}/{repo}/git/commits/{parent_sha}"
        commit_data, _ = repository_service.github_api_request(commit_url, token)
        parent_tree_sha = commit_data["tree"]["sha"]

        # C. Prepare tree items
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
                    pass  # Fallback to binary upload if decoding fails

            # Binary blob upload
            b64_str = base64.b64encode(content).decode("utf-8")
            blob_payload = {
                "content": b64_str,
                "encoding": "base64"
            }
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

        # D. Create new tree
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

        # E. Create commit
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

        # F. Update branch reference ref pointer
        ref_payload = {
            "sha": new_commit_sha,
            "force": True
        }
        repository_service.github_api_request(
            f"https://api.github.com/repos/{owner}/{repo}/git/refs/heads/{branch}",
            token,
            data=ref_payload,
            method="PATCH"
        )

        # Step 3: Enable Pages
        published_url = ""
        pages_enabled = False
        try:
            published_url = enable_github_pages(token, owner, repo)
            pages_enabled = True
        except Exception as e:
            # Fallback retrieve page config if enable triggers errors
            pages_info = get_github_pages_info(token, owner, repo)
            pages_enabled = pages_info["pages_enabled"]
            published_url = pages_info["published_url"]

        # Update deployment record with success details
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
