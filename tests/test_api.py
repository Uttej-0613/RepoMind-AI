import pytest
from fastapi.testclient import TestClient
from repomind.api import app

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "ok"}

def test_unconfigured(monkeypatch):
    monkeypatch.delenv("REPOMIND_ROOT", raising=False)
    assert client.post("/ask", json={"question": "find authentication"}).status_code == 503

def test_query_validation():
    assert client.post("/ask", json={"question": "x"}).status_code == 422

def test_ask(monkeypatch, tmp_path):
    (tmp_path / "app.py").write_text("def login():\n    return True\n")
    monkeypatch.setenv("REPOMIND_ROOT", str(tmp_path))
    response = client.post("/ask", json={"question": "login"})
    assert response.status_code == 200
    assert response.json()["citations"][0]["name"] == "login"
