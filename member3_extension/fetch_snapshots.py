"""Fetch only selected executable package files from pinned public ZIP snapshots."""
import hashlib
import binascii
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REV = '162e3ffbea1717ac8a20fe9b26465e29117229e4'
PACKAGES = {'mcp-sequentialthinking-tools': 'thinktools',
            '@modelcontextprotocol/server-filesystem': 'fs_official',
            '@modelcontextprotocol/server-sequential-thinking': 'thinking'}
SIZES = {'original':1218495812, 'iter3':1088423924, 'iter5':1088574402}
OUTPUT = ROOT/'member3_extension/snapshots'


class RemoteZip(io.RawIOBase):
    def __init__(self, url, size):
        self.url, self.size, self.pos = url, size, 0
        self.buffers = []
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos
    def read(self, n=-1):
        n = self.size-self.pos if n < 0 else min(n, self.size-self.pos)
        if n <= 0: return b''
        if n > 128*1024*1024: raise ValueError('Unexpectedly large ZIP index request')
        start = self.pos
        for offset, buffer in self.buffers:
            if offset <= start and start+n <= offset+len(buffer):
                self.pos += n
                return buffer[start-offset:start-offset+n]
        fetch_size = min(max(n, 262144), self.size-start)
        cache = ROOT/'.tmp/zip-ranges'/hashlib.sha256(f'{self.url}:{start}:{fetch_size}'.encode()).hexdigest()
        cache.parent.mkdir(parents=True, exist_ok=True)
        if cache.exists(): data = cache.read_bytes()
        else:
            req = urllib.request.Request(self.url, headers={'Range': f'bytes={start}-{start+fetch_size-1}'})
            with urllib.request.urlopen(req, timeout=45) as response:
                if response.status != 206: raise ValueError('Server ignored range request')
                data = response.read(fetch_size+1)
                if len(data) != fetch_size: raise ValueError('Range length mismatch')
            cache.write_bytes(data)
        self.buffers.append((start,data))
        self.pos += n
        return data[:n]


def main():
    output = OUTPUT
    records, inventories = [], {}
    for snapshot, size in SIZES.items():
        url = f'https://huggingface.co/datasets/anonymous2233/evol-servers/resolve/{REV}/{snapshot}_servers.zip'
        with zipfile.ZipFile(RemoteZip(url, size)) as archive:
            names = archive.namelist()
            for package, alias in PACKAGES.items():
                prefix = f'node_modules/{package}/'
                selected = [n for n in names if n.startswith(prefix)
                            and not n[len(prefix):].startswith('node_modules/')
                            and '/node_modules/' not in n[len(prefix):]
                            and Path(n).suffix in ('.js', '.json', '.mjs', '.cjs')]
                if not selected: raise ValueError(f'Package missing from official archive: {snapshot}/{package}')
                inventories[f'{snapshot}/{package}'] = selected
                for name in selected:
                    target = (output/snapshot/alias/name[len(prefix):]).resolve()
                    if not target.is_relative_to(output.resolve()): raise ValueError('Unsafe ZIP path')
                    info = archive.getinfo(name)
                    if target.exists():
                        raw = target.read_bytes()
                        if len(raw) != info.file_size or binascii.crc32(raw) != info.CRC:
                            raise ValueError('Existing snapshot differs from official ZIP CRC/size')
                    else:
                        raw = archive.read(name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists() and target.read_bytes() != raw: raise ValueError('Refusing to overwrite a different snapshot')
                    target.write_bytes(raw)
                    records.append({'snapshot': snapshot, 'server': package, 'archive_path': name,
                        'local_path': target.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(raw).hexdigest()})
                print(snapshot, package, len(selected), 'files', flush=True)
    result = {'source':'https://huggingface.co/datasets/anonymous2233/evol-servers', 'revision':REV,
              'extraction':'HTTP Range; executable JavaScript and package metadata only', 'files':records}
    (output/'provenance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print('Fetched',len(records),'official files',flush=True)


if __name__ == '__main__': main()
