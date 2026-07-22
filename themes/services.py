import io
import mimetypes
import os
import shutil
import zipfile

from django.conf import settings
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from .models import Theme, ThemeAsset

MAX_ZIP_SIZE_BYTES = 50 * 1024 * 1024          # 50 MB hard limit
MAX_EXTRACTED_SIZE_BYTES = 100 * 1024 * 1024   # 100 MB total extracted
MAX_FILE_COUNT = 500                            # prevent zip-bombs

ALLOWED_EXTENSIONS = {
    "html", "htm", "css", "js", "mjs", "json", "xml", "txt", "md",
    "jpg", "jpeg", "png", "gif", "svg", "webp", "ico", "avif", "bmp",
    "woff", "woff2", "ttf", "eot", "otf", "map",
}


class ThemeUploadError(Exception):
    """Raised when validation or processing of a theme zip fails."""
    pass


def _validate_zip(zip_file_obj, max_size: int = MAX_ZIP_SIZE_BYTES):
    zip_file_obj.seek(0, 2)
    size = zip_file_obj.tell()
    zip_file_obj.seek(0)
    if size > max_size:
        raise ThemeUploadError(
            f"ZIP file is too large ({size / 1024 / 1024:.1f} MB). Maximum allowed size is {max_size // 1024 // 1024} MB."
        )
    if size == 0:
        raise ThemeUploadError("Uploaded file is empty.")

    if not zipfile.is_zipfile(zip_file_obj):
        zip_file_obj.seek(0)
        raise ThemeUploadError("Uploaded file is not a valid ZIP archive.")
    zip_file_obj.seek(0)

    with zipfile.ZipFile(zip_file_obj, "r") as zf:
        members = zf.infolist()
        if len(members) > MAX_FILE_COUNT:
            raise ThemeUploadError(
                f"ZIP contains too many files ({len(members)}). Maximum allowed is {MAX_FILE_COUNT}."
            )

        total_extracted = 0
        for member in members:
            if ".." in member.filename or member.filename.startswith("/") or member.filename.startswith("\\"):
                raise ThemeUploadError(
                    f"Security violation: ZIP entry '{member.filename}' contains an unsafe path."
                )
            total_extracted += member.file_size

        if total_extracted > MAX_EXTRACTED_SIZE_BYTES:
            raise ThemeUploadError(
                f"ZIP would extract to {total_extracted / 1024 / 1024:.1f} MB. Maximum extracted size is {MAX_EXTRACTED_SIZE_BYTES // 1024 // 1024} MB."
            )

        all_names = [m.filename for m in members if not m.is_dir()]
        for name in all_names:
            ext = os.path.splitext(name)[1].lower().lstrip(".")
            if ext and ext not in ALLOWED_EXTENSIONS:
                raise ThemeUploadError(
                    f"File type '.{ext}' is not allowed inside the ZIP (found in '{name}')."
                )

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
    return os.path.join(settings.MEDIA_ROOT, "themes", "extracted", slug)


def _get_extraction_relative(slug: str) -> str:
    return os.path.join("themes", "extracted", slug)


def _extract_zip(zip_file_obj, dest_dir: str):
    os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_file_obj, "r") as zf:
        for member in zf.infolist():
            member_path = member.filename
            target_path = os.path.realpath(os.path.join(dest_dir, member_path))
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


def _scan_assets(theme: Theme, dest_dir: str):
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
                    file_path=rel_path.replace("\\", "/"),
                    file_name=filename,
                    file_size=file_size,
                    mime_type=mime_type or "",
                )
            )
    ThemeAsset.objects.bulk_create(assets_to_create)


def _generate_placeholder_thumbnail(theme: Theme):
    width, height = 800, 500
    bg_color = (15, 23, 42)
    accent = (99, 102, 241)

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 6], fill=accent)

    try:
        font = ImageFont.truetype("arial.ttf", 44)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), theme.name, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((width - text_w) / 2, (height - text_h) / 2 - 20),
        theme.name,
        fill=(255, 255, 255),
        font=font,
    )

    thumb_dir = os.path.join(settings.MEDIA_ROOT, "themes", "thumbnails")
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_filename = f"{theme.slug}.png"
    thumb_abs = os.path.join(thumb_dir, thumb_filename)
    img.save(thumb_abs, "PNG", optimize=True)

    theme.thumbnail = f"themes/thumbnails/{thumb_filename}"
    theme.save(update_fields=["thumbnail"])


@transaction.atomic
def process_theme_upload(theme: Theme, zip_file_obj) -> None:
    dest_dir = _get_extraction_root(theme.slug)
    try:
        _validate_zip(zip_file_obj)
        _extract_zip(zip_file_obj, dest_dir)
        theme.extracted_path = _get_extraction_relative(theme.slug)
        theme.save(update_fields=["extracted_path"])
        _scan_assets(theme, dest_dir)
        _generate_placeholder_thumbnail(theme)
    except ThemeUploadError:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        raise
    except Exception as exc:
        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir, ignore_errors=True)
        raise ThemeUploadError(f"Unexpected error during processing: {exc}") from exc
