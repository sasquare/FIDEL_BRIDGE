"""File storage abstraction: local disk in development/testing, Cloudflare
R2 (S3-compatible object storage) in production - so uploaded files
survive Render's ephemeral filesystem across deploys and restarts (see
the Bug 2 investigation: local disk on Render's free plan is wiped on
every deploy/restart, while the database's filename references persist).

Backend is selected automatically per-request via r2_enabled(): if R2
credentials are configured, use R2; otherwise fall back to local disk,
matching this app's existing pattern of environment-specific config
(SQLite locally, Postgres in production; console-logged email locally,
real SMTP in production).

Both backends are addressed by the same "<user_id>/<random-name>.<ext>"
key shape, so the DB columns that store these (profile_photo_filename,
image_filename, Verification.filename) don't change meaning between
backends - no migration needed for the column values themselves.

Public assets (profile photos, portfolio images) and private ones
(verification documents) are both served via short-lived presigned R2
URLs rather than making the bucket public - presigned URL generation is
a local HMAC signature, not a network call, so this costs nothing
extra per page render, and it means a verification document is never
reachable by anyone who merely guesses its object key.
"""
import uuid
from pathlib import Path

from flask import abort, current_app, redirect, send_from_directory, url_for
from werkzeug.utils import secure_filename

# Presigned URLs for public-facing images can live longer, since they're
# only ever used to load an <img> tag on the page that generated them.
PUBLIC_URL_EXPIRY = 3600
# Verification documents are sensitive - a much shorter window limits how
# long a copied/leaked link would remain useful.
PRIVATE_URL_EXPIRY = 300


def r2_enabled():
    return bool(current_app.config.get("R2_ACCOUNT_ID"))


def _r2_client():
    import boto3
    from botocore.config import Config as BotoConfig

    cfg = current_app.config
    return boto3.client(
        "s3",
        endpoint_url=f"https://{cfg['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=cfg["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["R2_SECRET_ACCESS_KEY"],
        config=BotoConfig(signature_version="s3v4"),
        region_name="auto",
    )


def _extension(filename):
    return Path(secure_filename(filename)).suffix.lower().lstrip(".")


def save(file_storage, *, local_folder_config_key, r2_prefix, user_id, allowed_extensions):
    """Save an upload, returning "<user_id>/<random-name>.<ext>" - the
    same key shape regardless of backend."""
    ext = _extension(file_storage.filename)
    if ext not in allowed_extensions:
        raise ValueError(f"Unsupported file type: .{ext}")

    stored_name = f"{uuid.uuid4().hex}.{ext}"
    key = f"{user_id}/{stored_name}"

    if r2_enabled():
        file_storage.stream.seek(0)
        extra_args = {"ContentType": file_storage.mimetype} if file_storage.mimetype else {}
        _r2_client().upload_fileobj(
            file_storage.stream,
            current_app.config["R2_BUCKET_NAME"],
            f"{r2_prefix}/{key}",
            ExtraArgs=extra_args,
        )
    else:
        folder = Path(current_app.config[local_folder_config_key]) / str(user_id)
        folder.mkdir(parents=True, exist_ok=True)
        file_storage.save(folder / stored_name)

    return key


def delete(key, *, local_folder_config_key, r2_prefix):
    """Best-effort delete. Missing files are not an error - the DB row is
    the source of truth for whether something is "still there" from the
    app's perspective."""
    if r2_enabled():
        _r2_client().delete_object(Bucket=current_app.config["R2_BUCKET_NAME"], Key=f"{r2_prefix}/{key}")
    else:
        path = Path(current_app.config[local_folder_config_key]) / key
        path.unlink(missing_ok=True)


def public_url(key, *, local_folder_config_key, r2_prefix, static_subpath):
    """Presigned (R2) or static (local dev) URL for a public asset, or
    None if key is falsy or (local dev only) the file no longer exists
    on disk."""
    if not key:
        return None

    if r2_enabled():
        return _r2_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": current_app.config["R2_BUCKET_NAME"], "Key": f"{r2_prefix}/{key}"},
            ExpiresIn=PUBLIC_URL_EXPIRY,
        )

    # Local dev/test fallback: local disk has no durability guarantee
    # either, so keep checking the file actually exists before pointing
    # an <img> tag at it (the same fix Bug 2 originally shipped).
    local_path = Path(current_app.config[local_folder_config_key]) / key
    if not local_path.is_file():
        return None
    return url_for("static", filename=f"{static_subpath}/{key}")


def private_download_response(key, *, local_folder_config_key, r2_prefix):
    """A Flask response for downloading a private file (verification
    documents): a redirect to a short-lived presigned R2 URL in
    production, or a direct authenticated file stream from local disk
    in development. Never makes the file reachable by URL guessing."""
    if r2_enabled():
        url = _r2_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": current_app.config["R2_BUCKET_NAME"], "Key": f"{r2_prefix}/{key}"},
            ExpiresIn=PRIVATE_URL_EXPIRY,
        )
        return redirect(url)

    directory = current_app.config[local_folder_config_key]
    try:
        return send_from_directory(directory, key)
    except FileNotFoundError:
        abort(404)
