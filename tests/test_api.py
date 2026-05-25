"""Tests básicos del API."""
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_health_check(client):
    """El endpoint de salud responde OK."""
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["assistant"] == settings.assistant_name


def test_chat_init_returns_greeting(client):
    """El init devuelve un saludo."""
    response = client.post("/api/v1/chat/init", json={
        "session_id": "test_session_123",
        "page": {"path": "/", "title": "Home"}
    })
    assert response.status_code == 200
    data = response.json()
    assert "greeting" in data
    assert "T-rrenito" in data["greeting"] or "🌱" in data["greeting"]


def test_chat_init_path_specific_greeting(client):
    """Saludo cambia según la URL."""
    response = client.post("/api/v1/chat/init", json={
        "session_id": "test_session_456",
        "page": {"path": "/pago/spei", "title": "Pago SPEI"}
    })
    assert response.status_code == 200
    data = response.json()
    assert "pago" in data["greeting"].lower() or "referencia" in data["greeting"].lower()


def test_chat_validates_input(client):
    """Mensajes vacíos son rechazados."""
    response = client.post("/api/v1/chat", json={
        "session_id": "test_session_789",
        "message": ""
    })
    assert response.status_code == 422  # Validation error
