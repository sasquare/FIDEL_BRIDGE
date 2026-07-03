from app.extensions import db
from app.models.category import Category
from app.models.professional import ProfessionalProfile
from app.models.user import User


def _make_professional(app, category_id, full_name="Chidi Okafor", email="chidi@example.com", city="Lagos", verified=False):
    with app.app_context():
        user = User(full_name=full_name, email=email, role="professional")
        user.set_password("supersecret")
        user.professional_profile = ProfessionalProfile(
            profession="Plumber", category_id=category_id, city=city, bio="Reliable plumbing services.", is_verified=verified
        )
        db.session.add(user)
        db.session.commit()
        return user.id


def test_categories_page_lists_seeded_categories(client, category, app):
    response = client.get("/browse/categories")
    assert response.status_code == 200
    with app.app_context():
        cat = db.session.get(Category, category)
        assert cat.name.encode() in response.data


def test_professionals_page_lists_active_professionals(client, app, category):
    _make_professional(app, category)
    response = client.get("/browse/professionals")
    assert response.status_code == 200
    assert b"Chidi Okafor" in response.data


def test_professionals_search_filters_by_category(client, app, category):
    _make_professional(app, category)
    with app.app_context():
        other_category = Category(name="Painters", slug="painters", icon_path="M0 0")
        db.session.add(other_category)
        db.session.commit()
        other_id = other_category.id
    _make_professional(app, other_id, full_name="Uche Bello", email="uche@example.com")

    with app.app_context():
        cat = db.session.get(Category, category)
        slug = cat.slug

    response = client.get(f"/browse/professionals?category={slug}")
    assert b"Chidi Okafor" in response.data
    assert b"Uche Bello" not in response.data


def test_professionals_search_filters_by_keyword(client, app, category):
    _make_professional(app, category, full_name="Chidi Okafor", email="chidi@example.com")
    _make_professional(app, category, full_name="Uche Bello", email="uche2@example.com")

    response = client.get("/browse/professionals?q=Chidi")
    assert b"Chidi Okafor" in response.data
    assert b"Uche Bello" not in response.data


def test_professionals_search_matches_category_name(client, app, category):
    # The homepage search bar's autocomplete suggests category names (see
    # the hero-categories datalist in main/index.html) - searching one of
    # those suggestions must actually return professionals in that
    # category, even when the category name itself appears nowhere in
    # their name/profession/bio/skills (here: "Electricians" vs a
    # professional whose profession is "Plumber").
    _make_professional(app, category, full_name="Chidi Okafor", email="chidi@example.com")

    response = client.get("/browse/professionals?q=Electricians")
    assert b"Chidi Okafor" in response.data


def test_professional_profile_page_renders(client, app, category):
    user_id = _make_professional(app, category, verified=True)
    response = client.get(f"/browse/professionals/{user_id}")
    assert response.status_code == 200
    assert b"Chidi Okafor" in response.data
    assert b"Verified" in response.data


def test_professional_profile_404_for_non_professional(client, app):
    with app.app_context():
        customer = User(full_name="Ada Lovelace", email="ada@example.com", role="customer")
        customer.set_password("supersecret")
        db.session.add(customer)
        db.session.commit()
        customer_id = customer.id

    response = client.get(f"/browse/professionals/{customer_id}")
    assert response.status_code == 404
