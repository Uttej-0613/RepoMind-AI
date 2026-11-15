from pathlib import Path
import pytest
from repomind import Index
from repomind.core import tokens


def test_python_nested_symbols_and_search(tmp_path: Path):
    (tmp_path / 'auth.py').write_text('''import secrets
class TokenService:
    def validate_token(self, token):
        """Verify user authentication token."""
        return secrets.compare_digest(token, 'abc')
''')
    index = Index(tmp_path)
    assert index.summary()['files_scanned'] == 1
    assert index.summary()['symbols_indexed'] == 2
    result = index.search('authentication token')
    assert result[0]['qualified_name'] == 'TokenService.validate_token'
    assert result[0]['citation'] == 'auth.py:L3-L5'
    assert index.graph()['edges'][0]['target'] == 'secrets'


def test_js_ts_declarations(tmp_path: Path):
    (tmp_path / 'client.ts').write_text('export async function loadProfile(id: string) { return id; }\nconst fetchUser = async (id) => id;\n')
    (tmp_path / 'view.jsx').write_text('export class LoginScreen {}\n')
    index = Index(tmp_path)
    assert set(sym.qualified_name for sym in index.symbols) == {'loadProfile', 'fetchUser', 'LoginScreen'}
    assert index.summary()['languages'] == {'typescript': 1, 'javascript': 1}


def test_skip_symlink_and_hidden_files(tmp_path: Path):
    (tmp_path / '.venv').mkdir()
    (tmp_path / '.venv' / 'hidden.py').write_text('def invisible(): pass')
    (tmp_path / 'valid.py').write_text('def visible(): return 1')
    (tmp_path / 'bad.py').write_text('def invalid(:')
    index = Index(tmp_path)
    assert [symbol.qualified_name for symbol in index.symbols] == ['visible']
    assert len(index.parse_errors) == 1


def test_symlink_is_not_indexed(tmp_path: Path):
    """Check symlink exclusion when the OS permits creating symlinks."""
    target = tmp_path / 'valid.py'
    target.write_text('def visible(): return 1')
    link = tmp_path / 'link.py'
    try:
        link.symlink_to(target)
    except OSError as exc:
        if getattr(exc, 'winerror', None) == 1314:
            pytest.skip('Windows account lacks symbolic link creation privilege')
        raise
    index = Index(tmp_path)
    assert [symbol.qualified_name for symbol in index.symbols] == ['visible']


def test_limits_and_no_matches(tmp_path: Path):
    (tmp_path / 'example.py').write_text('def apple(): pass')
    index = Index(tmp_path)
    with pytest.raises(ValueError):
        index.search('test', 0)
    with pytest.raises(ValueError):
        index.graph(0)
    assert index.search('quantumzebra') == []
    assert tokens('how does validateToken() work') == ['validate', 'token', 'work']


def test_file_size_limit(tmp_path: Path):
    (tmp_path / 'huge.py').write_text('a' * 300000)
    assert Index(tmp_path).summary()['files_scanned'] == 0
