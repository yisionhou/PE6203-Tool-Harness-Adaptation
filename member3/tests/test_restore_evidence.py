"""Verify archive restoration without touching the formal study evidence."""
import hashlib
import json
import zipfile

import pytest

from member3.restore_evidence import restore


def make_archive(tmp_path, name='outputs/member3-replication-v2/example.json'):
    archive = tmp_path/'fixture.zip'
    raw = b'{"preserved":true}\n'
    inventory = [{'path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}]
    with zipfile.ZipFile(archive, 'w') as output:
        output.writestr(name, raw)
        output.writestr('ARCHIVE_MANIFEST.json', json.dumps(inventory))
    archive.with_suffix('.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest())
    return archive, name, raw


def test_restore_is_verified_and_idempotent(tmp_path):
    archive, name, raw = make_archive(tmp_path)
    root = tmp_path/'repo'
    assert restore(root, archive, check_only=True)['restored_files'] == 0
    assert not root.exists()
    assert restore(root, archive)['restored_files'] == 1
    assert (root/name).read_bytes() == raw
    assert restore(root, archive)['restored_files'] == 0


def test_archive_tampering_is_rejected_before_writes(tmp_path):
    archive, _, _ = make_archive(tmp_path)
    archive.write_bytes(archive.read_bytes()+b'tampered')
    root = tmp_path/'repo'
    with pytest.raises(ValueError, match='archive fingerprint'):
        restore(root, archive)
    assert not root.exists()


def test_different_existing_evidence_is_never_overwritten(tmp_path):
    archive, name, _ = make_archive(tmp_path)
    root = tmp_path/'repo';target = root/name
    target.parent.mkdir(parents=True);target.write_bytes(b'keep me')
    with pytest.raises(ValueError, match='Refusing to overwrite'):
        restore(root, archive)
    assert target.read_bytes() == b'keep me'


def test_archive_path_traversal_is_rejected(tmp_path):
    archive, _, _ = make_archive(tmp_path, 'outputs/member3-replication-v2/../../escape.txt')
    root = tmp_path/'repo'
    with pytest.raises(ValueError, match='Unsafe evidence path'):
        restore(root, archive)
    assert not root.exists()
