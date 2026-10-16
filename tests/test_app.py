import pytest

from app.app import app, is_even


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_is_even():
    assert is_even(4) is True
    assert is_even(7) is False
    assert is_even(0) is True
    assert is_even(-2) is True
    assert is_even(-3) is False


def test_check_even(client):
    res = client.get("/check?number=10")
    assert res.status_code == 200
    assert res.get_json() == {"number": 10, "even": True}


def test_check_odd(client):
    res = client.get("/check?number=7")
    assert res.status_code == 200
    assert res.get_json()["even"] is False


def test_missing_number(client):
    res = client.get("/check")
    assert res.status_code == 400


def test_not_a_number(client):
    res = client.get("/check?number=abc")
    assert res.status_code == 400

    res = client.get("/check?number=2.5")
    assert res.status_code == 400
