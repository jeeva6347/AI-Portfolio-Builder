"""
themes/services.py — Theme Engine business logic.

Handles:
  - ZIP validation (format, size, zip-slip, file types, structure)
  - Safe extraction to media/themes/<slug>/
  - ThemeAsset record creation
  - Placeholder thumbnail generation
  - Full atomic rollback on any failure

All public entry point: process_theme_upload(theme, zip_file) → None | raises ThemeUploadError
"""

import io
import mimetypes
import os
import shutil
import zipfile

from django.conf import settings
from django.db import transaction
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont

from .models import Theme, ThemeAsset

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_ZIP_SIZE_BYTES = 50 * 1024 * 1024          # 50 MB hard limit
MAX_EXTRACTED_SIZE_BYTES = 100 * 1024 * 1024   # 100 MB total extracted
MAX_FILE_COUNT = 500                            # prevent zip-bombs

# Extensions allowed inside the zip. Any other extension → rejected.
ALLOWED_EXTENSIONS = {
    # Web
    "html", "htm", "css", "js", "mjs", "json", "xml", "txt",
    # Images
    "jpg", "jpeg", "png", "gif", "svg", "webp", "ico", "avif", "bmp",
    # Fonts
    "woff", "woff2", "ttf", "eot", "otf",
    # Misc
    "map",  # source maps
}

# ── Exceptions ─────────────────────────────────────────────────────────────────

class ThemeUploadError(Exception):
    """Raised when validation or processing of a theme zip fails."""
    pass


# ── Validation ─────────────────────────────────────────────────────────────────

def _validate_zip(zip_file_obj, max_size: int = MAX_ZIP_SIZE_BYTES):
    """
    Run all validations against the uploaded file object BEFORE extracting.
    Raises ThemeUploadError with a user-friendly message on failure.
    """
    # 1. Size check (in-memory/uploaded file)
    zip_file_obj.seek(0, 2)  # seek to end
    size = zip_file_obj.tell()
    zip_file_obj.seek(0)
    if size > max_size:
        raise ThemeUploadError(
            f"ZIP file is too large ({size / 1024 / 1024:.1f} MB). Maximum allowed size is {max_size // 1024 // 1024} MB."
        )
    if size == 0:
        raise ThemeUploadError("Uploaded file is empty.")

    # 2. Valid ZIP format
    if not zipfile.is_zipfile(zip_file_obj):
        zip_file_obj.seek(0)
        raise ThemeUploadError("Uploaded file is not a valid ZIP archive.")
    zip_file_obj.seek(0)

    with zipfile.ZipFile(zip_file_obj, "r") as zf:
        members = zf.infolist()

        # 3. File count limit (zip-bomb protection)
        if len(members) > MAX_FILE_COUNT:
            raise ThemeUploadError(
                f"ZIP contains too many files ({len(members)}). Maximum allowed is {MAX_FILE_COUNT}."
            )

        # 4. Extract size limit and ZIP-Slip protection
        total_extracted = 0
        for member in members:
            # ZIP-Slip: reject any path that contains ".." or is absolute
            if ".." in member.filename or member.filename.startswith("/") or member.filename.startswith("\\"):
                raise ThemeUploadError(
                    f"Security violation: ZIP entry '{member.filename}' contains an unsafe path."
                )
            total_extracted += member.file_size

        if total_extracted > MAX_EXTRACTED_SIZE_BYTES:
            raise ThemeUploadError(
                f"ZIP would extract to {total_extracted / 1024 / 1024:.1f} MB. Maximum extracted size is {MAX_EXTRACTED_SIZE_BYTES // 1024 // 1024} MB."
            )

        # 5. File extension whitelist
        all_names = [m.filename for m in members if not m.is_dir()]
        for name in all_names:
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext and ext not in ALLOWED_EXTENSIONS:
                raise ThemeUploadError(
                    f"File type '.{ext}' is not allowed inside the ZIP (found in '{name}')."
                )

        # 6. Required file check — must have an index.html somewhere
        lower_names = [n.lower() for n in all_names]
        has_index = any(
            n == "index.html" or n.endswith("/index.html")
            for n in lower_names
        )
        if not has_index:
            raise ThemeUploadError(
                "ZIP must contain an 'index.html' file at the root or in a subdirectory."
            )

    zip_file_obj.seek(0)


def _get_extraction_root(slug: str) -> str:
    """
    Returns the absolute path to the directory where the zip will be extracted.
    Relative to MEDIA_ROOT: themes/extracted/<slug>/
    """
    return os.path.join(settings.MEDIA_ROOT, "themes", "extracted", slug)


def _get_extraction_relative(slug: str) -> str:
    """Media-relative path (stored in Theme.extracted_path)."""
    return os.path.join("themes", "extracted", slug)


# ── Extraction ─────────────────────────────────────────────────────────────────

def _extract_zip(zip_file_obj, dest_dir: str):
    """
    Safely extract zip to dest_dir. 
    Re-validates each member path during extraction (double-check against zip-slip).
    """
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_file_obj, "r") as zf:
        for member in zf.infolist():
            # Strip leading component if the zip has a single root folder
            # so extracted_path/index.html always works regardless of zip structure
            member_path = member.filename

            # Resolve the absolute target path
            target_path = os.path.realpath(os.path.join(dest_dir, member_path))
            # Ensure it is still inside dest_dir (second zip-slip guard)
            if not target_path.startswith(os.path.realpath(dest_dir)):
                raise ThemeUploadError(
                    f"Security violation during extraction: '{member.filename}' attempted path traversal."
                )

            if member.is_dir():
                os.makedirs(target_path, exist_ok=True)
            else:
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zf.open(member) as src, open(target_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)


# ── Asset scanning ─────────────────────────────────────────────────────────────

def _scan_assets(theme: Theme, dest_dir: str):
    """Walk dest_dir and create a ThemeAsset record for every file."""
    assets_to_create = []
    for dirpath, _dirnames, filenames in os.walk(dest_dir):
        for filename in filenames:
            abs_path = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(abs_path, dest_dir)
            file_size = os.path.getsize(abs_path)
            mime_type, _ = mimetypes.guess_type(abs_path)
            asset_type = ThemeAsset.classify(filename)
            assets_to_create.append(
                ThemeAsset(
                    theme=theme,
                    asset_type=asset_type,
                    file_path=rel_path.replace("\\", "/"),  # normalize to forward slashes
                    file_name=filename,
                    file_size=file_size,
                    mime_type=mime_type or "",
                )
            )
    ThemeAsset.objects.bulk_create(assets_to_create)


# ── Thumbnail generation ────────────────────────────────────────────────────────

def _generate_placeholder_thumbnail(theme: Theme):
    """
    Creates a simple styled PNG thumbnail with the theme name and saves it 
    to media/themes/thumbnails/<slug>.png.
    
    A headless-browser screenshot can replace this in a future module.
    """
    width, height = 800, 500
    bg_colors = [
        (15, 23, 42),   # slate-900
        (30, 41, 59),   # slate-800
        (17, 24, 39),   # gray-900
        (7, 89, 133),   # cyan-800
        (88, 28, 135),  # purple-900
    ]
    # Pick a deterministic colour based on the theme name
    bg_color = bg_colors[len(theme.name) % len(bg_colors)]
    accent = (99, 102, 241)   # indigo-500

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Accent bar at top
    draw.rectangle([0, 0, width, 6], fill=accent)

    # Theme name (wrapped text)
    name = theme.name
    # Centre the name text
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((width - text_w) / 2, (height - text_h) / 2 - 30),
        name,
        fill=(255, 255, 255),
        font=font,
    )

    # Subtitle
    try:
        small_font = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        small_font = ImageFont.load_default()

    subtitle = "AI Portfolio Builder Theme"
    sub_bbox = draw.textbbox((0, 0), subtitle, font=small_font)
    sub_w = sub_bbox[2] - sub_bbox[0]
    draw.text(
        ((width - sub_w) / 2, (height + text_h) / 2 - 10),
        subtitle,
        fill=(148, 163, 184),   # slate-400
        font=small_font,
    )

    # Save
    thumb_dir = os.path.join(settings.MEDIA_ROOT, "themes", "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{theme.slug}.png"
    thumb_abs = os.path.join(thumb_dir, thumb_filename)
    img.save(thumb_abs, "PNG", optimize=True)

    # Store relative path in model
    theme.thumbnail = f"themes/thumbnails/{thumb_filename}"
    theme.save(update_fields=["thumbnail"])


# ── Main entry point ────────────────────────────────────────────────────────────

@transaction.atomic
def process_theme_upload(theme: Theme, zip_file_obj) -> None:
    """
    Full pipeline: validate → extract → scan → thumbnail → save.
    
    Wrapped in an atomic transaction so that any failure rolls back DB changes.
    File-system changes are cleaned up manually in the except block because
    Django transactions don't cover file I/O.

    Args:
        theme:        Theme instance (already saved, status=draft).
        zip_file_obj: File-like object of the uploaded zip.
    
    Raises:
        ThemeUploadError: on any validation or processing failure.
    """
    dest_dir = _get_extraction_root(theme.slug)

    try:
        # Step 1 — Validate
        _validate_zip(zip_file_obj)

        # Step 2 — Extract safely
        _extract_zip(zip_file_obj, dest_dir)

        # Step 3 — Store extracted_path on the Theme record
        theme.extracted_path = _get_extraction_relative(theme.slug)
        theme.save(update_fields=["extracted_path"])

        # Step 4 — Scan and create ThemeAsset records
        _scan_assets(theme, dest_dir)

        # Step 5 — Placeholder thumbnail
        _generate_placeholder_thumbnail(theme)

    except ThemeUploadError:
        # Clean up extracted files if any were created
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        raise  # re-raise so the view can show the error to the user

    except Exception as exc:
        # Unexpected error — clean up and wrap
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        raise ThemeUploadError(f"Unexpected error during processing: {exc}") from exc
