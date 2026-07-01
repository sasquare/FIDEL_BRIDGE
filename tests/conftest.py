import pytest

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
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
