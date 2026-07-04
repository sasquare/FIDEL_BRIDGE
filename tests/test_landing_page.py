def test_landing_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Bridging the" in response.data


def test_404_page(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404
    assert b"404" in response.data


def test_public_page_is_not_forced_no_store(client):
    # Only authenticated pages need no-store (see the authenticated test
    # below) - the public homepage should keep normal caching behavior.
    response = client.get("/")
    assert response.headers.get("Cache-Control") != "no-store"


def _register_professional(client, category_id, email="cache-test@example.com"):
    return client.post(
        "/auth/register/professional",
        data={
            "full_name": "Tunde Bello",
            "email": email,
            "phone": "08099999999",
            "profession": "Electrician",
            "category_id": category_id,
            "city": "Abuja",
            "password": "supersecret",
            "confirm_password": "supersecret",
        },
        follow_redirects=True,
    )


def test_authenticated_page_is_not_bfcached(client, app, category):
    # Regression test for the notification-badge bug: without
    # Cache-Control: no-store, browsers can restore a fully-rendered
    # previous page (badge and all) from the back/forward cache after the
    # server-side state has already changed, showing stale per-user data
    # without ever asking the server again.
    _register_professional(client, category)
    response = client.get("/professional/dashboard")
    assert response.headers.get("Cache-Control") == "no-store"


def test_static_assets_keep_normal_caching_even_when_authenticated(client, app, category):
    _register_professional(client, category)
    response = client.get("/static/css/output.css")
    assert response.headers.get("Cache-Control") != "no-store"


def test_dashboard_sidebar_wraps_instead_of_hiding_items_on_mobile(client, app, category):
    # Regression test: the mobile sidebar used to be a horizontally-
    # scrolling row with no affordance, which put most nav items
    # (Skills, Portfolio, Verification, Accountability) off-screen with
    # no visual hint they existed. It must wrap instead, so every item
    # is visible without any gesture.
    _register_professional(client, category)
    response = client.get("/professional/dashboard")
    html = response.data.decode()
    assert "overflow-x-auto" not in html
    assert "flex-wrap" in html
    # Every sidebar section a professional should always have access to.
    for label in ("My Profile", "Skills", "Portfolio", "Verification", "Accountability"):
        assert label in html


def test_csp_img_src_stays_self_only_when_r2_not_configured(client):
    # Local dev/testing: no R2 credentials, so uploads still (would) come
    # from local disk - the CSP should stay strict.
    response = client.get("/")
    csp = response.headers.get("Content-Security-Policy", "")
    assert "img-src 'self' data:;" in csp


def test_csp_img_src_allows_r2_origin_when_configured(client, app):
    # Regression test: profile photos/portfolio images/verification docs
    # are served via presigned R2 URLs pointing at a different origin than
    # fidelbridge.com. Without the R2 origin in img-src, the browser's CSP
    # silently blocks every one of them from rendering - the file uploads
    # fine, but the <img> never shows anything, with no server-side error
    # to point at (the bug looks like a storage problem but isn't one).
    app.config["R2_ACCOUNT_ID"] = "test-account-id"
    try:
        response = client.get("/")
        csp = response.headers.get("Content-Security-Policy", "")
        assert "https://test-account-id.r2.cloudflarestorage.com" in csp
    finally:
        app.config["R2_ACCOUNT_ID"] = None
