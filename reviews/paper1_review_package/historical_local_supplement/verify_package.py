from pathlib import Path
import hashlib,json
p=Path(__file__).resolve().parent
m=json.loads((p/'package_manifest.json').read_text(encoding='utf-8'))
for name,digest in m['files'].items():
    assert hashlib.sha256((p/name).read_bytes()).hexdigest()==digest,name
print('Verified',len(m['files']),'packaged files. This is an integrity check, not proof validation.')
