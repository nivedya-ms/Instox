import pytest

from backend import create_app
from backend.config import TestConfig
from backend.database.db import db


@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def registered_user(client):
    res = client.post(
        "/api/auth/register",
        json={
            "username": "ramesh",
            "email": "ramesh@example.com",
            "password": "secret123",
            "shop_name": "Ramesh Textiles",
        },
    )
    assert res.status_code == 201, res.get_json()
    return res.get_json()["data"]


@pytest.fixture
def auth_client(client, registered_user):
    return client
