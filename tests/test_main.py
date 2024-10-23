# tests/test_main.py

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

def test_fetch_data():
    response = client.get("/fetch")
    assert response.status_code == 200
    assert "data" in response.json()

def test_review_data():
    response = client.get("/review")
    assert response.status_code == 200
    assert "reviewed" in response.json()
