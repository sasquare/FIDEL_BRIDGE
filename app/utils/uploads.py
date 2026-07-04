"""Thin, category-specific wrappers around app/utils/storage.py's backend
abstraction (local disk in dev/testing, Cloudflare R2 in production).
Route code imports from here rather than storage.py directly, so each
call site doesn't need to repeat the local-folder-config-key/prefix pair
for its category.
"""
from flask import current_app

from app.utils import storage


def save_portfolio_image(file_storage, user_id):
    return storage.save(
        file_storage,
        local_folder_config_key="PORTFOLIO_UPLOAD_FOLDER",
        r2_prefix="portfolio",
        user_id=user_id,
        allowed_extensions=current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
    )


def delete_portfolio_image(key):
    storage.delete(key, local_folder_config_key="PORTFOLIO_UPLOAD_FOLDER", r2_prefix="portfolio")


def portfolio_image_url(key):
    return storage.public_url(
        key,
        local_folder_config_key="PORTFOLIO_UPLOAD_FOLDER",
        r2_prefix="portfolio",
        static_subpath="uploads/portfolio",
    )


def save_verification_document(file_storage, user_id):
    return storage.save(
        file_storage,
        local_folder_config_key="VERIFICATION_UPLOAD_FOLDER",
        r2_prefix="verifications",
        user_id=user_id,
        allowed_extensions=current_app.config["ALLOWED_DOCUMENT_EXTENSIONS"],
    )


def verification_document_response(key):
    return storage.private_download_response(
        key, local_folder_config_key="VERIFICATION_UPLOAD_FOLDER", r2_prefix="verifications"
    )


def save_profile_photo(file_storage, user_id):
    return storage.save(
        file_storage,
        local_folder_config_key="PROFILE_PHOTO_UPLOAD_FOLDER",
        r2_prefix="profile_photos",
        user_id=user_id,
        allowed_extensions=current_app.config["ALLOWED_IMAGE_EXTENSIONS"],
    )


def delete_profile_photo(key):
    storage.delete(key, local_folder_config_key="PROFILE_PHOTO_UPLOAD_FOLDER", r2_prefix="profile_photos")


def profile_photo_url(key):
    return storage.public_url(
        key,
        local_folder_config_key="PROFILE_PHOTO_UPLOAD_FOLDER",
        r2_prefix="profile_photos",
        static_subpath="uploads/profile_photos",
    )
