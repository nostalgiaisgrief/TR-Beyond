"""Print live DOS dialog descriptors for inspection (run from project root)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from compare_dialog import oracle
for kind in (95,96,97,71):
 o,pointers=oracle(kind,0)
 print('object',kind)
 for p in pointers:
  text=bytes(o.uc.mem_read(o.read(p+54,4),64)).split(b'\0')[0].decode('latin1')
  print(repr(text),'x/y',o.read(p+10,2),o.read(p+12,2),'flags',hex(o.read(p,2)),'panel',o.read(p+36,2),o.read(p+38,2))
