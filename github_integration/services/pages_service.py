from . import repository_service


def enable_github_pages(token, owner, repo_name) -> str:
    """
    Triggers GitHub REST API request to enable GitHub Pages on the main branch.
    Returns:
        str: The published URL of the Pages site.
    """
    url = f"https://api.github.com/repos/{owner}/{repo_name}/pages"
    payload = {
        "source": {
            "branch": "main",
            "path": "/"
        }
    }
    try:
        data, status = repository_service.github_api_request(url, token, data=payload, method="POST")
        return data.get("html_url", f"https://{owner}.github.io/{repo_name}/")
    except Exception as e:
        # Check if already enabled (often raises conflict if already configured)
        if "conflict" in str(e).lower() or "already" in str(e).lower():
            info = get_github_pages_info(token, owner, repo_name)
            if info["pages_enabled"]:
                return info["published_url"]
        raise Exception(f"Failed to enable GitHub Pages: {str(e)}")


def get_github_pages_info(token, owner, repo_name) -> dict:
    """
    Retrieves the current GitHub Pages deployment configurations.
    Returns:
        dict: {
            "pages_enabled": bool,
            "published_url": str,
            "status": str (e.g. built, building, null)
        }
    """
    url = f"https://api.github.com/repos/{owner}/{repo_name}/pages"
    try:
        data, status = repository_service.github_api_request(url, token, method="GET")
        return {
            "pages_enabled": True,
            "published_url": data.get("html_url", f"https://{owner}.github.io/{repo_name}/"),
            "status": data.get("status", "built")
        }
    except Exception:
        # If pages is not enabled, the API returns a 404
        return {
            "pages_enabled": False,
            "published_url": f"https://{owner}.github.io/{repo_name}/",
            "status": "not_configured"
        }
