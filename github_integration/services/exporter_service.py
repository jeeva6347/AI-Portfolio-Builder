import os
from bs4 import BeautifulSoup
from django.conf import settings

from themes.services import apply_theme_mapping


def compile_portfolio_static_bundle(portfolio) -> dict:
    """
    Compiles the portfolio's active theme template, gathers all related theme assets
    (stylesheets, javascript, fonts) and user uploaded media assets,
    converts absolute links to relative, and bundles them into an in-memory dictionary.
    
    Returns:
        dict: A dictionary mapping relative git paths to binary contents.
              e.g. {"index.html": b"...", "assets/css/style.css": b"..."}
    """
    theme = portfolio.selected_theme
    if not theme:
        raise Exception("No theme selected for this portfolio.")

    mapping = theme.mappings.filter(is_active=True).first()
    if not mapping:
        raise Exception(f"The active theme '{theme.name}' does not have a mapped layout profile.")

    index_path = theme.index_html_path
    if not index_path or not os.path.exists(index_path):
        raise Exception("Theme index.html template file is missing.")

    # 1. Read original index template
    with open(index_path, "r", encoding="utf-8", errors="ignore") as f:
        html_template = f.read()

    # 2. Compile portfolio data values into HTML
    compiled_html = apply_theme_mapping(html_template, mapping, portfolio.get_fields_dict())

    # 3. Parse with BeautifulSoup to resolve resource links
    soup = BeautifulSoup(compiled_html, "html.parser")
    
    # Remove local preview <base href="..."> if mapper injected one
    base_tag = soup.find("base")
    if base_tag:
        base_tag.decompose()

    bundle = {}

    # Helper to capture local media resource files and update HTML paths to relative
    def capture_local_media(tag, attr):
        val = tag[attr]
        if val.startswith("/media/") or val.startswith("media/"):
            # Normalize path name (remove leading slash)
            norm_path = val.lstrip("/")
            full_media_path = os.path.join(settings.BASE_DIR, norm_path)
            
            if os.path.exists(full_media_path):
                try:
                    with open(full_media_path, "rb") as f:
                        bundle[norm_path] = f.read()
                except Exception as e:
                    # Log warning or skip corrupt files gracefully
                    print(f"Skipping packaging media file {norm_path}: {e}")
            
            # Rewrite HTML attribute to be relative
            tag[attr] = norm_path

    # Extract src assets (e.g. project images, profile pictures)
    for tag in soup.find_all(src=True):
        capture_local_media(tag, "src")

    # Extract href assets (e.g. resume PDFs)
    for tag in soup.find_all(href=True):
        capture_local_media(tag, "href")

    # 4. Gather all theme asset files (CSS, JS, fonts, images) from extracted dir
    theme_dir = os.path.join(settings.MEDIA_ROOT, "themes", "extracted", theme.slug)
    if os.path.exists(theme_dir):
        for root, dirs, files in os.walk(theme_dir):
            for file in files:
                # Do not package the index.html template file itself since we generate a fresh index.html
                if file == "index.html" and root == theme_dir:
                    continue
                
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, theme_dir)
                git_path = rel_path.replace("\\", "/") # Convert Windows backslashes
                
                try:
                    with open(full_path, "rb") as f:
                        bundle[git_path] = f.read()
                except Exception as e:
                    print(f"Skipping theme asset {git_path}: {e}")

    # 5. Inject the updated index.html at root of bundle
    bundle["index.html"] = str(soup).encode("utf-8")

    return bundle
