import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()

    # Deliberately not held open for the whole test: the Flask test client
    # pushes its own app context (and gets a fresh, correctly-scoped
    # SQLAlchemy session) per request, same as in production. Keeping one
    # context alive for the whole test would make every client.get/post
    # share a single session, whose identity map can silently mask writes
    # made through a separate `with app.app_context()` block in a test.
    yield application

    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def category(app):
    from app.models.category import Category

    with app.app_context():
        cat = Category(name="Electricians", slug="electricians", icon_path="M0 0", description="Wiring and repairs.")
        db.session.add(cat)
        db.session.commit()
        return cat.id
