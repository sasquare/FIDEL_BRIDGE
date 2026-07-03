from sqlalchemy import event

from app.extensions import db
from app.models.booking import STATUS_COMPLETED, Booking
from app.models.category import Category
from app.models.customer import CustomerProfile
from app.models.professional import ProfessionalProfile
from app.models.review import Review
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


def test_professionals_page_shows_result_count_when_all_fit_on_one_page(client, app, category):
    _make_professional(app, category, full_name="Chidi Okafor", email="chidi@example.com")
    _make_professional(app, category, full_name="Uche Bello", email="uche_count@example.com")

    response = client.get("/browse/professionals")
    assert b"Showing 2 professionals" in response.data


def test_professionals_page_shows_partial_result_count_across_pages(client, app, category):
    for i in range(14):
        _make_professional(app, category, full_name=f"Pro Number {i}", email=f"pronum{i}@example.com")

    response = client.get("/browse/professionals")
    # PER_PAGE is 12, so page 1 of 14 total professionals shows 12.
    assert b"Showing 12 of 14 professionals" in response.data


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


def test_professionals_search_shows_ratings_without_n_plus_one(client, app, category):
    with app.app_context():
        customer_user = User(full_name="Ada Customer", email="ada_customer@example.com", role="customer")
        customer_user.set_password("supersecret")
        customer_user.customer_profile = CustomerProfile()
        db.session.add(customer_user)
        db.session.commit()
        customer_profile_id = customer_user.customer_profile.id

    professional_ids = []
    for i in range(3):
        user_id = _make_professional(app, category, full_name=f"Pro {i}", email=f"pro{i}@example.com")
        with app.app_context():
            user = db.session.get(User, user_id)
            professional_ids.append(user.professional_profile.id)

    # Two completed, reviewed bookings per professional, so the search
    # results page has real ratings/review counts to render.
    with app.app_context():
        for professional_id in professional_ids:
            for _ in range(2):
                booking = Booking(
                    customer_profile_id=customer_profile_id,
                    professional_profile_id=professional_id,
                    title="Fix the wiring",
                    description="Kitchen socket isn't working.",
                    status=STATUS_COMPLETED,
                )
                db.session.add(booking)
                db.session.commit()
                db.session.add(
                    Review(
                        booking_id=booking.id,
                        customer_profile_id=customer_profile_id,
                        professional_profile_id=professional_id,
                        rating=5,
                    )
                )
        db.session.commit()

    queries = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        if statement.strip().upper().startswith("SELECT"):
            queries.append(statement)

    with app.app_context():
        engine = db.engine
    event.listen(engine, "before_cursor_execute", _record)
    try:
        response = client.get("/browse/professionals")
    finally:
        event.remove(engine, "before_cursor_execute", _record)

    assert response.status_code == 200
    assert b"5.0 (2)" in response.data

    # A fixed, small number of SELECTs (results page, categories dropdown,
    # count query, one aggregate rating query) regardless of how many
    # professionals have reviews - not one extra SELECT per professional,
    # which is what professional.average_rating/review_count would trigger
    # via lazy-loading the full reviews relationship per card.
    assert len(queries) <= 8, f"expected a small fixed number of queries, got {len(queries)}:\n" + "\n".join(queries)


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
