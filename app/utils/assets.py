"""Cache-busted static asset URLs.

Static assets are served with a long Cache-Control max-age (see
SEND_FILE_MAX_AGE_DEFAULT in app/config.py). Since filenames like
output.css and main.js aren't content-hashed, a browser could keep serving
a stale cached copy after a deploy changes the file. Appending the file's
mtime as a query string forces a fresh fetch whenever the file changes,
without needing a build-time hashing step.
"""
import os

from flask import current_app, url_for


def asset_url(filename):
    static_path = os.path.join(current_app.static_folder, filename)
    try:
        version = int(os.path.getmtime(static_path))
    except OSError:
        version = 0
    return url_for("static", filename=filename, v=version)
