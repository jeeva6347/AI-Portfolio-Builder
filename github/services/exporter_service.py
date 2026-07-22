import os
from django.conf import settings


def compile_theme_static_bundle(theme) -> dict:
    """
    Reads all extracted files of a theme (HTML, CSS, JS, images, fonts, manifest)
    from media/themes/extracted/<slug>/ into an in-memory dictionary.
    
    Returns:
        dict mapping relative file paths (e.g. "index.html", "static/css/style.css")
        to raw bytes content.
    """
    if not theme.extracted_path:
        raise ValueError(f"Theme '{theme.name}' has no extracted_path set.")

    theme_root = os.path.join(settings.MEDIA_ROOT, theme.extracted_path)
    if not os.path.exists(theme_root):
        raise FileNotFoundError(f"Theme directory not found at {theme_root}")

    bundle = {}
    for root, _dirs, files in os.walk(theme_root):
        for file in files:
            abs_file_path = os.path.join(root, file)
            rel_file_path = os.path.relpath(abs_file_path, theme_root).replace("\\", "/")

            with open(abs_file_path, "rb") as f:
                bundle[rel_file_path] = f.read()

    if "index.html" not in bundle:
        raise ValueError(f"Theme '{theme.name}' bundle must contain an 'index.html' at the root.")

    return bundle
