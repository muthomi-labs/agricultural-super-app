# app/services/upload_service.py

"""
Image upload handling, shared by post images and profile images -- both
already just store an `image_url` string (see PostImage.image_url,
Profile.profile_image_url), so this doesn't touch either model or
schema. It only adds a way to turn an uploaded file into a URL; once you
have that URL, it flows through the existing post/profile endpoints
exactly like a pasted URL always did.

Security posture (see docs/TECHNICAL_DEBT.md-style reasoning): a file's
extension and declared Content-Type are both attacker-controlled and
proves nothing. The only thing trusted here is whether Pillow can
actually decode the bytes as one of the allowed image formats -- a
disguised executable, a corrupt file, or an SVG with embedded script
content all fail this check. The re-encode step (rather than saving the
uploaded bytes verbatim) also strips EXIF/metadata that could otherwise
carry something unwanted through to every viewer of the image. Filenames
are never taken from the client -- always a fresh random UUID -- so
there's no path-traversal or overwrite-another-upload surface at all.
"""

import io
import os
import urllib.error
import urllib.request
import uuid

from flask import current_app
from PIL import Image, UnidentifiedImageError

from app.errors import ValidationAPIError

SUPABASE_UPLOAD_TIMEOUT_SECONDS = 30

# Extension -> MIME type for the Content-Type Supabase Storage stores the
# object under (and later serves it as, on GET).
CONTENT_TYPE_BY_EXTENSION = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "mp4": "video/mp4",
    "mov": "video/quicktime",
    "webm": "video/webm",
}

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DIMENSION_PX = 2000  # downscale anything larger, aspect ratio preserved

# Pillow's declared format -> (file extension, save format, allows alpha)
ALLOWED_FORMATS = {
    "JPEG": ("jpg", "JPEG", False),
    "PNG": ("png", "PNG", True),
    "WEBP": ("webp", "WEBP", True),
}


MAX_VIDEO_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB

# (extension, expected magic-byte check). There's no video-processing
# dependency in this project (no ffmpeg/opencv), so unlike images this
# can't be decoded and re-encoded to prove it's genuine -- this is a
# narrower, documented trade-off: a lightweight structural sniff of each
# container format's own header, not a full parse.
ALLOWED_VIDEO_TYPES = {
    "video/mp4": "mp4",
    "video/quicktime": "mov",
    "video/webm": "webm",
}


def _looks_like_mp4(header):
    # An MP4/MOV file is a sequence of boxes; the first box is usually
    # "ftyp" starting at byte 4 (bytes 0-3 are the box size).
    return header[4:8] == b"ftyp"


def _looks_like_webm(header):
    # WebM/Matroska files start with the EBML magic number.
    return header[:4] == b"\x1a\x45\xdf\xa3"


def _ensure_upload_folder(upload_folder):
    os.makedirs(upload_folder, exist_ok=True)


def _upload_to_supabase(raw_bytes, filename, extension, supabase_url, service_role_key, bucket):
    """
    Uploads via the Supabase Storage REST API
    (POST {supabase_url}/storage/v1/object/{bucket}/{path}, raw body,
    Authorization: Bearer <service role key> -- Storage requires both
    that header and `apikey` set to the same key). Returns the resulting
    public URL (requires the bucket itself be set to Public in the
    Supabase dashboard), or raises ValidationAPIError if the upload
    fails -- callers already only have that one error path documented
    for this endpoint, so this doesn't introduce a new one.
    """
    content_type = CONTENT_TYPE_BY_EXTENSION.get(extension, "application/octet-stream")
    path = f"{filename}"

    request_obj = urllib.request.Request(
        f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{path}",
        data=raw_bytes,
        method="POST",
        headers={
            "Content-Type": content_type,
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
        },
    )

    try:
        with urllib.request.urlopen(request_obj, timeout=SUPABASE_UPLOAD_TIMEOUT_SECONDS) as response:
            response.read()  # drain; success body isn't needed, the URL is built from `path`
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="replace")
        current_app.logger.error("Supabase Storage upload rejected (HTTP %s): %s", err.code, detail)
        raise ValidationAPIError("The file could not be uploaded right now. Please try again.")
    except (urllib.error.URLError, TimeoutError) as err:
        current_app.logger.error("Supabase Storage upload failed: %s", err)
        raise ValidationAPIError("The file could not be uploaded right now. Please try again.")

    return f"{supabase_url.rstrip('/')}/storage/v1/object/public/{bucket}/{path}"


def save_uploaded_image(file_storage, upload_folder, supabase_url=None, supabase_key=None, supabase_bucket=None):
    """
    Validate and persist an uploaded image file.

    `file_storage` is a werkzeug FileStorage (from request.files). Raises
    ValidationAPIError for anything that fails validation. Returns
    (filename, external_url): external_url is the Supabase Storage
    public URL when the `supabase_*` args are all set, otherwise None --
    the route builds a local /api/uploads/<filename> URL in that case.
    """
    if file_storage is None or not file_storage.filename:
        raise ValidationAPIError("No image file was provided.")

    raw_bytes = file_storage.read()
    if not raw_bytes:
        raise ValidationAPIError("The uploaded file is empty.")
    if len(raw_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValidationAPIError(
            f"Image is too large. Maximum size is {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image.verify()  # cheap structural check; the image object is unusable after this
        # Re-open: verify() consumes the parser state, and we still need
        # to actually decode pixel data below to confirm it's not just a
        # well-formed header on truncated/malicious data.
        image = Image.open(io.BytesIO(raw_bytes))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationAPIError(
            "This file is not a valid image. Supported formats: JPEG, PNG, WebP."
        )

    format_info = ALLOWED_FORMATS.get(image.format)
    if format_info is None:
        raise ValidationAPIError(
            f"Unsupported image format ({image.format or 'unknown'}). "
            "Supported formats: JPEG, PNG, WebP."
        )
    extension, save_format, allows_alpha = format_info

    # Downscale oversized images rather than rejecting them outright --
    # a phone photo is routinely 4000px+ wide, which is a worse user
    # experience to bounce than to just resize.
    if image.width > MAX_DIMENSION_PX or image.height > MAX_DIMENSION_PX:
        image.thumbnail((MAX_DIMENSION_PX, MAX_DIMENSION_PX), Image.LANCZOS)

    if save_format == "JPEG" and image.mode in ("RGBA", "P"):
        image = image.convert("RGB")  # JPEG has no alpha channel
    elif not allows_alpha and image.mode == "P":
        image = image.convert("RGB")

    filename = f"{uuid.uuid4().hex}.{extension}"

    save_kwargs = {"format": save_format}
    if save_format == "JPEG":
        save_kwargs["quality"] = 85
        save_kwargs["optimize"] = True

    if supabase_url and supabase_key and supabase_bucket:
        buffer = io.BytesIO()
        image.save(buffer, **save_kwargs)
        url = _upload_to_supabase(buffer.getvalue(), filename, extension, supabase_url, supabase_key, supabase_bucket)
        return filename, url

    _ensure_upload_folder(upload_folder)
    destination = os.path.join(upload_folder, filename)
    image.save(destination, **save_kwargs)
    return filename, None


def save_uploaded_video(file_storage, upload_folder, supabase_url=None, supabase_key=None, supabase_bucket=None):
    """
    Validate and persist an uploaded video file (for Reels/FarmClips).

    Same untrusted-input posture as save_uploaded_image: the declared
    Content-Type and filename extension are both attacker-controlled, so
    they're only used to pick which magic-byte check to run, never
    trusted on their own. The file is stored as-is (no re-encode -- that
    would need ffmpeg, which this project doesn't depend on).

    Returns (filename, external_url) -- see save_uploaded_image.
    """
    if file_storage is None or not file_storage.filename:
        raise ValidationAPIError("No video file was provided.")

    raw_bytes = file_storage.read()
    if not raw_bytes:
        raise ValidationAPIError("The uploaded file is empty.")
    if len(raw_bytes) > MAX_VIDEO_SIZE_BYTES:
        raise ValidationAPIError(
            f"Video is too large. Maximum size is {MAX_VIDEO_SIZE_BYTES // (1024 * 1024)}MB."
        )

    content_type = (file_storage.mimetype or "").lower()
    extension = ALLOWED_VIDEO_TYPES.get(content_type)
    if extension is None:
        raise ValidationAPIError(
            "Unsupported video type. Supported formats: MP4, MOV, WebM."
        )

    header = raw_bytes[:16]
    is_valid = (
        (extension in ("mp4", "mov") and _looks_like_mp4(header))
        or (extension == "webm" and _looks_like_webm(header))
    )
    if not is_valid:
        raise ValidationAPIError(
            "This file does not look like a genuine video. "
            "Supported formats: MP4, MOV, WebM."
        )

    filename = f"{uuid.uuid4().hex}.{extension}"

    if supabase_url and supabase_key and supabase_bucket:
        url = _upload_to_supabase(raw_bytes, filename, extension, supabase_url, supabase_key, supabase_bucket)
        return filename, url

    _ensure_upload_folder(upload_folder)
    destination = os.path.join(upload_folder, filename)
    with open(destination, "wb") as out:
        out.write(raw_bytes)
    return filename, None
