import pytest
from repomind.llm import answer, LLMUnavailable


def test_no_key_produces_deterministic_evidence(monkeypatch):
    monkeypatch.delenv('REPOMIND_LLM_API_KEY', raising=False)
    result = answer('where?', [{'citation': 'main.py:L1-L3'}])
    assert result['mode'] == 'evidence'


def test_http_endpoint_rejected(monkeypatch):
    monkeypatch.setenv('REPOMIND_LLM_API_KEY', 'fake')
    monkeypatch.setenv('REPOMIND_LLM_URL', 'http://localhost:9000/chat')
    with pytest.raises(LLMUnavailable, match='HTTPS'):
        answer('where?', [{'citation': 'main.py:L1-L3', 'qualified_name': 'main', 'snippet': 'pass'}])
