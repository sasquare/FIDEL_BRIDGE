import io
from unittest.mock import MagicMock, patch

from app.utils import storage


def test_r2_disabled_by_default_in_testing_config(app):
    with app.app_context():
        assert storage.r2_enabled() is False


def test_r2_enabled_when_account_id_configured(app):
    with app.app_context():
        app.config["R2_ACCOUNT_ID"] = "test-account"
        try:
            assert storage.r2_enabled() is True
        finally:
            app.config["R2_ACCOUNT_ID"] = None


def _fake_file(name="photo.png", content=b"fake-bytes"):
    return FakeFileStorage(name, content)


class FakeFileStorage:
    """Minimal stand-in for a Werkzeug FileStorage - just enough for
    storage.save()'s stream/filename/mimetype/save() usage."""

    def __init__(self, filename, content):
        self.filename = filename
        self.mimetype = "image/png"
        self.stream = io.BytesIO(content)

    def save(self, dst):
        with open(dst, "wb") as f:
            f.write(self.stream.getvalue())


def test_save_uploads_to_r2_when_enabled(app):
    with app.app_context():
        app.config["R2_ACCOUNT_ID"] = "test-account"
        app.config["R2_ACCESS_KEY_ID"] = "test-key"
        app.config["R2_SECRET_ACCESS_KEY"] = "test-secret"
        app.config["R2_BUCKET_NAME"] = "fidelbridge-files"
        try:
            fake_client = MagicMock()
            with patch("app.utils.storage._r2_client", return_value=fake_client):
                key = storage.save(
                    _fake_file(),
                    local_folder_config_key="PROFILE_PHOTO_UPLOAD_FOLDER",
                    r2_prefix="profile_photos",
                    owner_id=7,
                    allowed_extensions={"png", "jpg", "jpeg"},
                )
            assert key.startswith("7/")
            assert key.endswith(".png")
            fake_client.upload_fileobj.assert_called_once()
            args, kwargs = fake_client.upload_fileobj.call_args
            assert args[1] == "fidelbridge-files"
            assert args[2] == f"profile_photos/{key}"
        finally:
            app.config["R2_ACCOUNT_ID"] = None


def test_public_url_generates_presigned_url_when_r2_enabled(app):
    with app.app_context():
        app.config["R2_ACCOUNT_ID"] = "test-account"
        app.config["R2_ACCESS_KEY_ID"] = "test-key"
        app.config["R2_SECRET_ACCESS_KEY"] = "test-secret"
        app.config["R2_BUCKET_NAME"] = "fidelbridge-files"
        try:
            fake_client = MagicMock()
            fake_client.generate_presigned_url.return_value = "https://r2.example/signed-url"
            with patch("app.utils.storage._r2_client", return_value=fake_client):
                url = storage.public_url(
                    "7/abc123.png",
                    local_folder_config_key="PROFILE_PHOTO_UPLOAD_FOLDER",
                    r2_prefix="profile_photos",
                    static_subpath="uploads/profile_photos",
                )
            assert url == "https://r2.example/signed-url"
            _, kwargs = fake_client.generate_presigned_url.call_args
            assert kwargs["Params"]["Key"] == "profile_photos/7/abc123.png"
            assert kwargs["ExpiresIn"] == storage.PUBLIC_URL_EXPIRY
        finally:
            app.config["R2_ACCOUNT_ID"] = None


def test_public_url_returns_none_for_falsy_key_regardless_of_backend(app):
    with app.app_context():
        assert storage.public_url(
            None, local_folder_config_key="PROFILE_PHOTO_UPLOAD_FOLDER", r2_prefix="profile_photos",
            static_subpath="uploads/profile_photos",
        ) is None


def test_private_download_response_redirects_to_presigned_url_when_r2_enabled(app):
    with app.app_context():
        app.config["R2_ACCOUNT_ID"] = "test-account"
        app.config["R2_ACCESS_KEY_ID"] = "test-key"
        app.config["R2_SECRET_ACCESS_KEY"] = "test-secret"
        app.config["R2_BUCKET_NAME"] = "fidelbridge-files"
        try:
            fake_client = MagicMock()
            fake_client.generate_presigned_url.return_value = "https://r2.example/private-signed-url"
            with patch("app.utils.storage._r2_client", return_value=fake_client):
                response = storage.private_download_response(
                    "9/id-card.pdf",
                    local_folder_config_key="VERIFICATION_UPLOAD_FOLDER",
                    r2_prefix="verifications",
                )
            assert response.status_code == 302
            assert response.location == "https://r2.example/private-signed-url"
            _, kwargs = fake_client.generate_presigned_url.call_args
            assert kwargs["Params"]["Key"] == "verifications/9/id-card.pdf"
            # Verification documents get a much shorter-lived URL than
            # public images, since they're sensitive personal documents.
            assert kwargs["ExpiresIn"] == storage.PRIVATE_URL_EXPIRY
            assert storage.PRIVATE_URL_EXPIRY < storage.PUBLIC_URL_EXPIRY
        finally:
            app.config["R2_ACCOUNT_ID"] = None


def test_delete_calls_r2_delete_object_when_enabled(app):
    with app.app_context():
        app.config["R2_ACCOUNT_ID"] = "test-account"
        app.config["R2_ACCESS_KEY_ID"] = "test-key"
        app.config["R2_SECRET_ACCESS_KEY"] = "test-secret"
        app.config["R2_BUCKET_NAME"] = "fidelbridge-files"
        try:
            fake_client = MagicMock()
            with patch("app.utils.storage._r2_client", return_value=fake_client):
                storage.delete(
                    "7/abc123.png", local_folder_config_key="PROFILE_PHOTO_UPLOAD_FOLDER", r2_prefix="profile_photos"
                )
            fake_client.delete_object.assert_called_once_with(
                Bucket="fidelbridge-files", Key="profile_photos/7/abc123.png"
            )
        finally:
            app.config["R2_ACCOUNT_ID"] = None


def test_save_category_image_uploads_to_r2_when_enabled(app):
    from app.utils.uploads import save_category_image

    with app.app_context():
        app.config["R2_ACCOUNT_ID"] = "test-account"
        app.config["R2_ACCESS_KEY_ID"] = "test-key"
        app.config["R2_SECRET_ACCESS_KEY"] = "test-secret"
        app.config["R2_BUCKET_NAME"] = "fidelbridge-files"
        try:
            fake_client = MagicMock()
            with patch("app.utils.storage._r2_client", return_value=fake_client):
                key = save_category_image(_fake_file(), "electricians")
            assert key.startswith("electricians/")
            args, kwargs = fake_client.upload_fileobj.call_args
            assert args[2] == f"categories/{key}"
        finally:
            app.config["R2_ACCOUNT_ID"] = None


def test_category_image_url_returns_none_for_missing_file_in_dev(app):
    from app.utils.uploads import category_image_url

    with app.test_request_context():
        assert category_image_url("does-not-exist/photo.png") is None


def test_category_image_url_present_after_save_in_dev(app):
    from app.utils.uploads import category_image_url, save_category_image

    with app.test_request_context():
        key = save_category_image(_fake_file(), "electricians")
        url = category_image_url(key)
        assert url is not None
        assert "electricians" in url
