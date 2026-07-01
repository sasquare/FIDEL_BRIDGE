def test_landing_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Bridging the" in response.data


def test_404_page(client):
    response = client.get("/this-page-does-not-exist")
    assert response.status_code == 404
    assert b"404" in response.data
