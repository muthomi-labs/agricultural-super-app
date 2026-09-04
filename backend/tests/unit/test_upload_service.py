# tests/unit/test_upload_service.py

import io
import os

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from app.errors import ValidationAPIError
from app.services import upload_service


def _image_bytes(fmt="PNG", size=(50, 40), color=(100, 150, 80)):
    buf = io.BytesIO()
    Image.new("RGB", size, color=color).save(buf, format=fmt)
    buf.seek(0)
    return buf.read()


def _file_storage(data, filename="test.png", content_type="image/png"):
    return FileStorage(stream=io.BytesIO(data), filename=filename, content_type=content_type)


class TestSaveUploadedImage:
    def test_saves_valid_png_and_returns_filename(self, tmp_path):
        filename, _ = upload_service.save_uploaded_image(_file_storage(_image_bytes("PNG")), str(tmp_path))
        assert filename.endswith(".png")
        assert os.path.exists(os.path.join(tmp_path, filename))

    def test_saves_valid_jpeg(self, tmp_path):
        data = _image_bytes("JPEG")
        filename, _ = upload_service.save_uploaded_image(
            _file_storage(data, filename="photo.jpg", content_type="image/jpeg"), str(tmp_path)
        )
        assert filename.endswith(".jpg")
        with Image.open(os.path.join(tmp_path, filename)) as img:
            assert img.format == "JPEG"

    def test_saves_valid_webp(self, tmp_path):
        data = _image_bytes("WEBP")
        filename, _ = upload_service.save_uploaded_image(
            _file_storage(data, filename="photo.webp", content_type="image/webp"), str(tmp_path)
        )
        assert filename.endswith(".webp")

    def test_generates_random_filename_ignoring_client_supplied_name(self, tmp_path):
        # The client filename is deliberately never trusted -- including
        # as a source of the extension -- so a client claiming ".png" for
        # bytes that are actually a JPEG still gets saved as .jpg, and a
        # path-traversal-style client filename has zero effect either way.
        data = _image_bytes("JPEG")
        filename, _ = upload_service.save_uploaded_image(
            _file_storage(data, filename="../../etc/passwd.png", content_type="image/png"), str(tmp_path)
        )
        assert ".." not in filename
        assert "/" not in filename
        assert filename.endswith(".jpg")  # real content (JPEG) wins over claimed name/type

    def test_rejects_non_image_file(self, tmp_path):
        fake = b"this is definitely not an image, just text pretending to be one"
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_image(_file_storage(fake, filename="fake.jpg"), str(tmp_path))

    def test_rejects_empty_file(self, tmp_path):
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_image(_file_storage(b"", filename="empty.png"), str(tmp_path))

    def test_rejects_no_file(self, tmp_path):
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_image(None, str(tmp_path))

    def test_rejects_oversized_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_service, "MAX_FILE_SIZE_BYTES", 100)
        data = _image_bytes("PNG", size=(200, 200))  # comfortably over 100 bytes
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_image(_file_storage(data), str(tmp_path))

    def test_downscales_oversized_dimensions(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_service, "MAX_DIMENSION_PX", 100)
        data = _image_bytes("PNG", size=(400, 300))
        filename, _ = upload_service.save_uploaded_image(_file_storage(data), str(tmp_path))
        with Image.open(os.path.join(tmp_path, filename)) as img:
            assert max(img.size) <= 100

    def test_two_uploads_never_collide(self, tmp_path):
        data = _image_bytes("PNG")
        first, _ = upload_service.save_uploaded_image(_file_storage(data), str(tmp_path))
        second, _ = upload_service.save_uploaded_image(_file_storage(data), str(tmp_path))
        assert first != second

    def test_creates_upload_folder_if_missing(self, tmp_path):
        nested = str(tmp_path / "does" / "not" / "exist" / "yet")
        filename, _ = upload_service.save_uploaded_image(_file_storage(_image_bytes("PNG")), nested)
        assert os.path.exists(os.path.join(nested, filename))


def _video_bytes(kind="mp4", padding=200):
    if kind == "webm":
        return b"\x1a\x45\xdf\xa3" + b"\x00" * padding
    return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * padding


class TestSaveUploadedVideo:
    def test_saves_valid_mp4_and_returns_filename(self, tmp_path):
        filename, _ = upload_service.save_uploaded_video(
            _file_storage(_video_bytes("mp4"), filename="clip.mp4", content_type="video/mp4"),
            str(tmp_path),
        )
        assert filename.endswith(".mp4")
        assert os.path.exists(os.path.join(tmp_path, filename))

    def test_saves_valid_webm(self, tmp_path):
        filename, _ = upload_service.save_uploaded_video(
            _file_storage(_video_bytes("webm"), filename="clip.webm", content_type="video/webm"),
            str(tmp_path),
        )
        assert filename.endswith(".webm")

    def test_saves_valid_quicktime_as_mov(self, tmp_path):
        filename, _ = upload_service.save_uploaded_video(
            _file_storage(_video_bytes("mp4"), filename="clip.mov", content_type="video/quicktime"),
            str(tmp_path),
        )
        assert filename.endswith(".mov")

    def test_generates_random_filename_ignoring_client_supplied_name(self, tmp_path):
        filename, _ = upload_service.save_uploaded_video(
            _file_storage(_video_bytes("mp4"), filename="../../etc/passwd.mp4", content_type="video/mp4"),
            str(tmp_path),
        )
        assert ".." not in filename
        assert "/" not in filename

    def test_rejects_unsupported_content_type(self, tmp_path):
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_video(
                _file_storage(_video_bytes("mp4"), filename="clip.avi", content_type="video/x-msvideo"),
                str(tmp_path),
            )

    def test_rejects_disguised_non_video_file(self, tmp_path):
        fake = b"not actually a video, just text pretending to be one"
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_video(
                _file_storage(fake, filename="fake.mp4", content_type="video/mp4"), str(tmp_path)
            )

    def test_rejects_empty_file(self, tmp_path):
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_video(
                _file_storage(b"", filename="empty.mp4", content_type="video/mp4"), str(tmp_path)
            )

    def test_rejects_no_file(self, tmp_path):
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_video(None, str(tmp_path))

    def test_rejects_oversized_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(upload_service, "MAX_VIDEO_SIZE_BYTES", 100)
        data = _video_bytes("mp4", padding=200)
        with pytest.raises(ValidationAPIError):
            upload_service.save_uploaded_video(
                _file_storage(data, filename="big.mp4", content_type="video/mp4"), str(tmp_path)
            )

    def test_two_uploads_never_collide(self, tmp_path):
        data = _video_bytes("mp4")
        first, _ = upload_service.save_uploaded_video(
            _file_storage(data, filename="a.mp4", content_type="video/mp4"), str(tmp_path)
        )
        second, _ = upload_service.save_uploaded_video(
            _file_storage(data, filename="b.mp4", content_type="video/mp4"), str(tmp_path)
        )
        assert first != second
