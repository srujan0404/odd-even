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


def test_negative_and_big_numbers(client):
    res = client.get("/check?number=-8")
    assert res.get_json() == {"number": -8, "even": True}

    big = "9" * 50
    res = client.get("/check?number=" + big)
    assert res.status_code == 200
    assert res.get_json()["even"] is False


def test_number_too_long(client):
    res = client.get("/check?number=" + "1" * 101)
    assert res.status_code == 400


def test_health_and_ready(client):
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200


def test_version(client):
    res = client.get("/version")
    assert res.status_code == 200
    assert "version" in res.get_json()


def test_response_headers(client):
    res = client.get("/check?number=3", headers={"X-Request-ID": "abc123"})
    assert res.headers["X-Request-ID"] == "abc123"
    assert "X-App-Version" in res.headers


def test_metrics(client):
    client.get("/check?number=2")
    client.get("/check?number=abc")
    res = client.get("/metrics")
    text = res.get_data(as_text=True)

    assert res.status_code == 200
    assert "evenodd_requests_total" in text
    assert 'evenodd_checks_total{result="even"}' in text
    assert 'status="400"' in text
