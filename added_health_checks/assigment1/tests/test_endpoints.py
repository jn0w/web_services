# api endpoint tests
# run: python3 -m pytest tests/ -v

import pytest
from fastapi.testclient import TestClient

from app.main import app

TEST_PRODUCT_ID = 99999


# test client with app startup and shutdown
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_get_single_product(client):
    response = client.get("/getSingleProduct", params={"id": 1001})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1001
    assert "name" in data
    assert "price" in data
    assert "quantity" in data
    assert "description" in data


def test_get_single_product_not_found(client):
    response = client.get("/getSingleProduct", params={"id": 999999})
    assert response.status_code == 404


def test_get_all(client):
    response = client.get("/getAll")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_add_new_product(client):
    new_product = {
        "id": TEST_PRODUCT_ID,
        "name": "Test Product For Unit Test",
        "price": 19.99,
        "quantity": 10,
        "description": "This is a temporary test product",
    }
    response = client.post("/addNew", json=new_product)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == TEST_PRODUCT_ID
    assert data["name"] == "Test Product For Unit Test"


def test_add_duplicate_product(client):
    duplicate = {
        "id": TEST_PRODUCT_ID,
        "name": "Duplicate",
        "price": 5.00,
        "quantity": 1,
        "description": "Should fail",
    }
    response = client.post("/addNew", json=duplicate)
    assert response.status_code == 409


def test_delete_product(client):
    response = client.delete("/deleteOne", params={"id": TEST_PRODUCT_ID})
    assert response.status_code == 200


def test_delete_product_not_found(client):
    response = client.delete("/deleteOne", params={"id": 999999})
    assert response.status_code == 404


def test_starts_with(client):
    response = client.get("/startsWith", params={"letter": "N"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # every product name starts with N
    for product in data:
        assert product["name"].upper().startswith("N")


def test_paginate(client):
    response = client.get("/paginate", params={"start": 1001, "end": 1020})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10
    # sorted by id
    ids = [p["id"] for p in data]
    assert ids == sorted(ids)


def test_paginate_invalid_range(client):
    response = client.get("/paginate", params={"start": 1020, "end": 1001})
    assert response.status_code == 400


def test_convert(client):
    response = client.get("/convert", params={"id": 1001})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1001
    assert "original_price_usd" in data
    assert "converted_price_eur" in data
    assert "exchange_rate" in data
    assert data["exchange_rate"] > 0
    assert data["converted_price_eur"] > 0


def test_pydantic_validation_bad_id(client):
    response = client.get("/getSingleProduct", params={"id": "abc"})
    assert response.status_code == 422


def test_pydantic_validation_missing_fields(client):
    response = client.post("/addNew", json={"id": 1, "name": "Incomplete"})
    assert response.status_code == 422
