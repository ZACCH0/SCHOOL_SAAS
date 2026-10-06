import pytest

# Create your tests here.
@pytest.mark.django_db
def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"School Management Platform" in response.content