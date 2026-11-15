import io
import stat
import zipfile
import pytest

from repomind.workspace import ImportErrorSafe, extract_source_archive, parse_github_url, Workspace


def archive_of(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        for name, data in files.items():
            z.writestr(name, data)
    return output.getvalue()


def test_valid_import(tmp_path, monkeypatch):
    data = archive_of({'root/src/health.py': 'def health():\n    return "ok"\n', 'root/node_modules/vendor.js': 'const vendor = () => 1'})
    monkeypatch.setattr('repomind.workspace.download_github_archive', lambda owner, repo: data)
    workspace = Workspace(tmp_path / 'data')
    result = workspace.import_github('https://github.com/owner/repo')
    assert result['files_scanned'] == 1
    assert workspace.index().search('health')[0]['path'] == 'src/health.py'
    assert Workspace(tmp_path / 'data').info()['name'] == 'owner/repo'


def test_path_traversal_rejected(tmp_path):
    data = archive_of({'root/../../outside.py': 'def no(): pass'})
    with pytest.raises(ImportErrorSafe, match='Unsafe archive path'):
        extract_source_archive(data, tmp_path / 'out')


def test_bad_remote_urls_rejected():
    for url in ['https://github.com.evil.com/u/r', 'https://github.com/u/r/tree/main', 'https://127.0.0.1/x/y', 'file:///etc/passwd']:
        with pytest.raises(ImportErrorSafe):
            parse_github_url(url)


def test_zip_symlink_skipped(tmp_path):
    blob = io.BytesIO()
    link = zipfile.ZipInfo('root/shortcut.py')
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(blob, 'w') as z:
        z.writestr(link, '../../etc/passwd')
        z.writestr('root/valid.py', 'def yes(): return True')
    assert extract_source_archive(blob.getvalue(), tmp_path / 'sources') == 1
    assert not (tmp_path / 'sources/shortcut.py').exists()


def test_unsupported_files_rejected(tmp_path):
    with pytest.raises(ImportErrorSafe, match='No supported'):
        extract_source_archive(archive_of({'root/package.json': '{}'}), tmp_path / 'source')
