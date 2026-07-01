import uuid
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename


def _extension(filename):
    return Path(secure_filename(filename)).suffix.lower().lstrip(".")


def _save(file_storage, base_folder, user_id, allowed_extensions):
    """Save an upload under base_folder/<user_id>/<random-name>.<ext>.

    Returns the "<user_id>/<random-name>.<ext>" relative path to store in the
    database, which is enough to locate the file again without ever trusting
    the uploader's original filename.
    """
    ext = _extension(file_storage.filename)
    if ext not in allowed_extensions:
        raise ValueError(f"Unsupported file type: .{ext}")

    folder = Path(base_folder) / str(user_id)
    folder.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(folder / stored_name)
    return f"{user_id}/{stored_name}"


def save_portfolio_image(file_storage, user_id):
    return _save(
        file_storage, current_app.config["PORTFOLIO_UPLOAD_FOLDER"], user_id, current_app.config["ALLOWED_IMAGE_EXTENSIONS"]
    )


def save_verification_document(file_storage, user_id):
    return _save(
        file_storage,
        current_app.config["VERIFICATION_UPLOAD_FOLDER"],
        user_id,
        current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"],
    )
