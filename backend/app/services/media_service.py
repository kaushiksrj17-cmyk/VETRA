import hashlib
import os
from pathlib import Path
import time
from typing import Optional, Tuple
from PIL import Image

from app.config import settings



BASE_MEDIA_DIR = Path(r"D:\VETRA\media")
IMAGES_DIR = BASE_MEDIA_DIR / "images"
VIDEOS_DIR = BASE_MEDIA_DIR / "videos"
THUMBNAILS_DIR = BASE_MEDIA_DIR / "thumbnails"

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024   # 10 MB
MAX_VIDEO_SIZE_BYTES = 25 * 1024 * 1024   # 25 MB

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTS = {".mp4", ".avi", ".mov"}

ALLOWED_IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp"
}

ALLOWED_VIDEO_MIMES = {
    "video/mp4",
    "video/x-msvideo",
    "video/quicktime",
    "video/avi"
}


def ensure_media_directories():
    """
    Ensure base media directories exist with proper access rights.
    """
    try:
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def compute_sha256(content: bytes) -> str:
    """
    Compute cryptographic SHA-256 hash of media bytes.
    """
    return hashlib.sha256(content).hexdigest()


def sanitize_filename(filename: str) -> str:
    """
    Sanitize client-provided filename to prevent directory traversal and injection.
    """
    cleaned = os.path.basename(filename)
    cleaned = cleaned.replace("..", "").replace("/", "").replace("\\", "").replace("\x00", "")
    return cleaned or "unnamed_media"


def validate_media_upload(
    filename: str,
    content: bytes,
    content_type: Optional[str] = None
) -> Tuple[bool, str, str]:
    """
    Validate uploaded media for extension, MIME type, file size, corruption, and path traversal.

    Returns:
        (is_valid, media_type, error_message)
    """
    if not filename or not content:
        return False, "", "Empty file or filename provided."

    # 1. Path traversal check
    if ".." in filename or "/" in filename or "\\" in filename or "\x00" in filename:
        return False, "", "Security violation: Invalid characters or path traversal pattern in filename."

    ext = Path(filename).suffix.lower()
    size = len(content)

    max_image_bytes = min(MAX_IMAGE_SIZE_BYTES, settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024)
    max_video_bytes = min(MAX_VIDEO_SIZE_BYTES, settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024)

    # 2. Image Check
    if ext in ALLOWED_IMAGE_EXTS:
        if size > max_image_bytes:
            return False, "image", f"Image file size ({size / 1024 / 1024:.1f} MB) exceeds maximum allowed {max_image_bytes / 1024 / 1024:.0f} MB."

        # Magic byte validation for image formats
        is_known_image = False
        if content.startswith(b"\xff\xd8\xff"):  # JPEG
            is_known_image = True
        elif content.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
            is_known_image = True
        elif content.startswith(b"RIFF") and len(content) > 12 and content[8:12] == b"WEBP":  # WebP
            is_known_image = True

        if not is_known_image and content_type not in ALLOWED_IMAGE_MIMES:
            return False, "image", "Unrecognized or mismatched image file signature."

        # Validate that image is decodable
        try:
            import io
            with Image.open(io.BytesIO(content)) as img:
                img.verify()
        except Exception:
            return False, "image", "Corrupted or unreadable image file."
        return True, "image", ""

    # 3. Video Check
    if ext in ALLOWED_VIDEO_EXTS:
        if size > max_video_bytes:
            return False, "video", f"Video file size ({size / 1024 / 1024:.1f} MB) exceeds maximum allowed {max_video_bytes / 1024 / 1024:.0f} MB."
        return True, "video", ""

    return False, "", f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_IMAGE_EXTS | ALLOWED_VIDEO_EXTS)}"


def save_media_file(
    content: bytes,
    filename: str,
    media_type: str
) -> Tuple[str, str, str]:
    """
    Save validated media using a safe content-derived filename with path traversal protection.

    Returns:
        (relative_storage_path, absolute_storage_path, media_hash)
    """
    ensure_media_directories()
    media_hash = compute_sha256(content)
    clean_name = sanitize_filename(filename)
    ext = Path(clean_name).suffix.lower()

    # Generate safe non-user-controlled filename
    safe_name = f"{media_hash[:16]}_{int(time.time())}{ext}"

    if media_type == "video":
        target_dir = VIDEOS_DIR
        rel_dir = "videos"
    else:
        target_dir = IMAGES_DIR
        rel_dir = "images"

    target_path = target_dir / safe_name

    # Path traversal protection check
    abs_base = os.path.abspath(BASE_MEDIA_DIR)
    abs_target = os.path.abspath(target_path)
    if not abs_target.startswith(abs_base):
        raise ValueError("Security violation: Path traversal attempt detected.")

    with open(target_path, "wb") as f:
        f.write(content)

    rel_path = f"{rel_dir}/{safe_name}"
    return rel_path, str(target_path), media_hash


def get_absolute_media_path(rel_path: str) -> Optional[str]:
    """
    Resolve and verify relative media path safely inside BASE_MEDIA_DIR.
    """
    if ".." in rel_path or "\x00" in rel_path:
        return None

    target = BASE_MEDIA_DIR / rel_path
    abs_base = os.path.abspath(BASE_MEDIA_DIR)
    abs_target = os.path.abspath(target)
    if not abs_target.startswith(abs_base):
        return None
    if os.path.exists(abs_target):
        return abs_target
    return None
