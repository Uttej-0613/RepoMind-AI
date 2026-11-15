from pathlib import Path
from fastapi.testclient import TestClient
import pytest
import repomind.api as api
from repomind.workspace import Workspace


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    root = tmp_path / 'source'
    root.mkdir()
    (root / 'repo.py').write_text('def authenticate_user(password):\n    """Validate login password."""\n    return bool(password)\n')
    monkeypatch.setenv('REPOMIND_ROOT', str(root))
    monkeypatch.delenv('REPOMIND_API_KEY', raising=False)
    monkeypatch.delenv('REPOMIND_LLM_API_KEY', raising=False)
    monkeypatch.setattr(api, 'workspace', Workspace(data_dir=tmp_path / '.cache'))
    with TestClient(api.app) as web:
        yield web


def test_dashboard_and_endpoints(client):
    assert '<!doctype html>' in client.get('/').text.lower()
    assert client.get('/api/health').json()['status'] == 'ok'
    assert client.get('/api/overview').json()['symbols_indexed'] == 1
    assert client.get('/api/overview').json()['name'] == 'source'
    assert client.get('/api/search', params={'q': 'validate login'}).json()['results'][0]['path'] == 'repo.py'
    assert client.get('/api/graph').status_code == 200
    assert client.get('/api/files').json()['files'][0]['path'] == 'repo.py'
    assert 'authenticate_user' in client.get('/api/file', params={'path': 'repo.py'}).json()['content']
    assert client.post('/api/reindex').status_code == 200


def test_chat_is_evidence_without_key(client):
    response = client.post('/api/chat', json={'question': 'validate login'})
    assert response.status_code == 200
    assert response.json()['mode'] == 'evidence'
    assert response.json()['citations']
    assert client.get('/api/config').json()['llm_enabled'] is False


def test_validation_auth_and_traversal(client, monkeypatch):
    assert client.get('/api/search', params={'q': 'a'}).status_code == 422
    assert client.post('/api/chat', json={'question': 'x'}).status_code == 422
    assert client.get('/api/file', params={'path': '../repo.py'}).status_code == 404
    assert client.get('/api/file', params={'path': 'unknown.py'}).status_code == 404
    monkeypatch.setenv('REPOMIND_API_KEY', 'test-local-key')
    assert client.get('/api/overview').status_code == 401
    assert client.get('/api/overview', headers={'X-API-Key': 'bad'}).status_code == 401
    assert client.get('/api/overview', headers={'X-API-Key': 'test-local-key'}).status_code == 200


def test_import_github(client, monkeypatch):
    import io
    import zipfile
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as archive:
        archive.writestr('sample-repo-hash/src/api.py', 'def get_status():\n    return True\n')
    monkeypatch.setattr('repomind.workspace.download_github_archive', lambda owner, repo: data.getvalue())
    response = client.post('/api/import-github', json={'url': 'https://github.com/example/sample-repo'})
    assert response.status_code == 200, response.text
    assert response.json()['name'] == 'example/sample-repo'
    assert response.json()['files_scanned'] == 1
    assert client.get('/api/file', params={'path': 'src/api.py'}).status_code == 200
    assert client.post('/api/use-local').json()['name'] == 'source'
    assert client.post('/api/import-github', json={'url': 'http://localhost/admin'}).status_code == 422
