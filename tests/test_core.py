from repomind.core import answer, index_repository, search

def test_index_and_citations(tmp_path):
    (tmp_path / "service.py").write_text("def authenticate(token):\n    return bool(token)\n")
    chunks = index_repository(tmp_path)
    assert len(chunks) == 1
    assert chunks[0].name == "authenticate"
    result = answer(tmp_path, "authenticate token")
    assert result["citations"][0]["path"] == "service.py"
    assert result["citations"][0]["start_line"] == 1

def test_invalid_syntax_skipped(tmp_path):
    (tmp_path / "broken.py").write_text("def invalid(\n")
    assert index_repository(tmp_path) == []

def test_ignore_hidden_and_large(tmp_path):
    (tmp_path / ".secret.py").write_text("def secret(): pass")
    assert index_repository(tmp_path) == []

def test_empty_query(tmp_path):
    assert search([], "   ") == []

def test_limit_validation():
    import pytest
    with pytest.raises(ValueError):
        search([], "test", 0)
