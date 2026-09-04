# app/routes/upload_routes.py

from flask import Blueprint, current_app, jsonify, request, send_from_directory

from app.auth.decorators import jwt_required
from app.services import upload_service

uploads_bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")


@uploads_bp.post("")
@jwt_required
def upload_image():
    """
    Auth required -- any authenticated user can upload an image for
    their own post or profile (ownership of *where the URL gets used* is
    still enforced by the existing post/profile endpoints; this endpoint
    only ever produces a URL, it doesn't attach anything to anything).

    Body: multipart/form-data with a single file field named "image".
    ---
    tags:
      - Uploads
    security:
      - BearerAuth: []
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: image
        type: file
        required: true
        description: JPEG, PNG, or WebP. Max 5MB by default (MAX_CONTENT_LENGTH).
    responses:
      201:
        description: Image stored.
        schema:
          type: object
          properties:
            url:
              type: string
            filename:
              type: string
      422:
        description: Missing file, or not a genuine, safe image.
        schema:
          $ref: '#/definitions/Error'
      413:
        description: File exceeds MAX_CONTENT_LENGTH.
        schema:
          $ref: '#/definitions/Error'
    """
    file_storage = request.files.get("image")
    filename, external_url = upload_service.save_uploaded_image(
        file_storage,
        current_app.config["UPLOAD_FOLDER"],
        supabase_url=current_app.config.get("SUPABASE_URL"),
        supabase_key=current_app.config.get("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_bucket=current_app.config.get("SUPABASE_STORAGE_BUCKET"),
    )

    url = external_url or request.host_url.rstrip("/") + f"/api/uploads/{filename}"
    return jsonify({"url": url, "filename": filename}), 201


@uploads_bp.post("/video")
@jwt_required
def upload_video():
    """
    Auth required -- uploads a video for a Reel (a post with video_url
    set). Same posture as image upload: this only ever produces a URL,
    ownership of where it gets attached is enforced by the post endpoints.

    Body: multipart/form-data with a single file field named "video".
    ---
    tags:
      - Uploads
    security:
      - BearerAuth: []
    consumes:
      - multipart/form-data
    parameters:
      - in: formData
        name: video
        type: file
        required: true
        description: MP4, MOV, or WebM. Max 50MB.
    responses:
      201:
        description: Video stored.
        schema:
          type: object
          properties:
            url:
              type: string
            filename:
              type: string
      422:
        description: Missing file, or not a genuine, supported video.
        schema:
          $ref: '#/definitions/Error'
      413:
        description: File exceeds MAX_CONTENT_LENGTH.
        schema:
          $ref: '#/definitions/Error'
    """
    file_storage = request.files.get("video")
    filename, external_url = upload_service.save_uploaded_video(
        file_storage,
        current_app.config["UPLOAD_FOLDER"],
        supabase_url=current_app.config.get("SUPABASE_URL"),
        supabase_key=current_app.config.get("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_bucket=current_app.config.get("SUPABASE_STORAGE_BUCKET"),
    )

    url = external_url or request.host_url.rstrip("/") + f"/api/uploads/{filename}"
    return jsonify({"url": url, "filename": filename}), 201


@uploads_bp.get("/<path:filename>")
def serve_upload(filename):
    """
    Public (no auth) -- these are meant to be viewable anywhere the
    image_url they're stored under is already publicly dumped (post
    images, profile images). send_from_directory rejects any filename
    containing '..' or an absolute path itself, so this is safe against
    path traversal regardless of what's in the URL.
    ---
    tags:
      - Uploads
    parameters:
      - in: path
        name: filename
        type: string
        required: true
    produces:
      - image/jpeg
      - image/png
      - image/webp
    responses:
      200:
        description: The image file.
      404:
        description: File not found.
    """
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
