import json
import pytest
from fastapi.testclient import TestClient

from main import app
from agent import CustomReActAgent
from tools import ToolContext
from models import AgentEvent

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama_model" in data
    assert data["ollama_connected"] is True

def test_research_endpoint_empty_query():
    response = client.post("/api/research", json={"question": "   "})
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]

def test_citation_filtering_logic():
    agent = CustomReActAgent()
    valid_urls = {
        "https://example.com/ai-report",
        "https://harvard.edu/paper",
    }
    
    text_with_mixed_urls = """
    Based on findings in [1] https://example.com/ai-report and [2] https://harvard.edu/paper,
    we can see progress. A hallucinated source was https://fake-news.com/fake.
    """
    
    citations = agent._extract_citations_from_text(text_with_mixed_urls, valid_urls)
    # Only valid fetched URLs should be extracted
    assert "https://example.com/ai-report" in citations
    assert "https://harvard.edu/paper" in citations
    assert "https://fake-news.com/fake" not in citations

def test_tool_failure_recovery_in_context():
    ctx = ToolContext()
    # Malformed URL should not throw unhandled exception
    res = ctx.fetch_page("not-a-valid-url")
    assert res["success"] is False
    assert "error" in res

    # Private IP address blocked by SSRF
    res_ssrf = ctx.fetch_page("http://192.168.1.100")
    assert res_ssrf["success"] is False
    assert "forbidden" in res_ssrf["error"]

    # Calculator invalid syntax
    res_calc = ctx.calculator("10 / * 5")
    assert res_calc["success"] is False
    assert "error" in res_calc

def test_max_steps_attribute():
    agent = CustomReActAgent()
    assert agent.max_steps == 8

def test_agent_event_serialization():
    event = AgentEvent(
        type="tool_call",
        step=2,
        tool="calculator",
        arguments={"expression": "25 * 4"},
        message="Evaluating math expression"
    )
    json_str = event.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["type"] == "tool_call"
    assert parsed["step"] == 2
    assert parsed["tool"] == "calculator"
    assert parsed["arguments"]["expression"] == "25 * 4"
