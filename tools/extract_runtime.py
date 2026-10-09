"""Extract the hash-pinned executable's exact movement sine table for local use."""
import hashlib
from pathlib import Path
from analyse_le import load
root=Path(__file__).resolve().parents[1]
raw,objects,_,_=load(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
assert hashlib.sha256(raw).hexdigest()=='99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'
for obj in objects:
    off=0xc50c4-obj['base']
    if 0<=off and off+2050<=len(obj['data']):
        (root/'work/reference-assets/sine.bin').write_bytes(obj['data'][off:off+2050])
        break
else: raise RuntimeError('Sine table not mapped')
print('Extracted 1025 original sine values')
