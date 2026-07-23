"""Tests for API Endpoints (Phase 2)."""

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from core.config.settings import Settings
from tests.test_llm_provider import MockLLMProvider


@pytest.fixture
def client_with_mock_orchestrator():
    """Fixture providing TestClient with mock orchestrator initialized."""
    with TestClient(app) as client:
        from core.di.container import build_orchestrator

        test_settings = Settings()
        test_settings.llm.gemini_api_key = "mock_key"

        orchestrator = build_orchestrator(test_settings)
        research_agent = orchestrator.agent_registry.get_agent("ResearchAgent")
        research_agent.llm_provider = MockLLMProvider("Mocked LLM answer about LangGraph.")

        app.state.orchestrator = orchestrator
        yield client


def test_health_endpoint(client_with_mock_orchestrator):
    response = client_with_mock_orchestrator.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["research_agent_registered"] is True


def test_chat_endpoint_flow(client_with_mock_orchestrator):
    response = client_with_mock_orchestrator.post(
        "/chat", json={"message": "Explain what LangGraph is."}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Mocked LLM answer" in data["response"]
    assert len(data["tasks"]) == 1
    assert data["tasks"][0]["agent_id"].startswith("ResearchAgent")
