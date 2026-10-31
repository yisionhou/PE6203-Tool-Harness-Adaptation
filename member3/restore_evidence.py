"""Restore archived formal runs offline, verifying hashes before any writes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = (
    'outputs/member3-replication-v2/',
    'member3_extension/workspace/outputs/member3-expansion-v1/',
    'member3_migration/workspace/outputs/member3-migration-v1/',
)


def restore(root=ROOT, archive=None, check_only=False):
    root = Path(root).resolve()
    archive = Path(archive) if archive else root/'member3/evidence/raw-runs.zip'
    expected = archive.with_suffix('.sha256').read_text(encoding='ascii').split()[0]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise ValueError('Raw evidence archive fingerprint mismatch')
    pending = []
    with zipfile.ZipFile(archive) as source:
        inventory = json.loads(source.read('ARCHIVE_MANIFEST.json'))
        paths = [item['path'] for item in inventory]
        if len(paths) != len(set(paths)) or sorted(source.namelist()) != sorted(paths+['ARCHIVE_MANIFEST.json']):
            raise ValueError('Archive inventory does not match its entries')
        for item in inventory:
            name = item['path']
            relative = PurePosixPath(name)
            if not name.startswith(PREFIXES) or relative.is_absolute() or '..' in relative.parts or '\\' in name:
                raise ValueError('Unsafe evidence path: '+name)
            target = root.joinpath(*relative.parts).resolve()
            if not target.is_relative_to(root):
                raise ValueError('Evidence path escapes the repository')
            raw = source.read(name)
            if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
                raise ValueError('Evidence fingerprint mismatch: '+name)
            if target.exists():
                if not target.is_file() or target.read_bytes() != raw:
                    raise ValueError('Refusing to overwrite different evidence: '+name)
            else:
                pending.append((target, raw))
    if not check_only:
        for target, raw in pending:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as output:
                output.write(raw)
    return {'verified_files': len(inventory), 'restored_files': 0 if check_only else len(pending),
            'check_only': check_only, 'model_api_requests': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(restore(check_only=args.check_only)))


if __name__ == '__main__':
    main()
