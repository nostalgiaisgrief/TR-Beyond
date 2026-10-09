"""Execute only the DOS coordinate-smoothing span; no collision doubles needed.
Native follow_camera_test separately checks the renderer response and clearance.
"""
from pathlib import Path
import hashlib, json, random, struct, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from analyse_le import load
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_ESP
raw,objects,_,_=load(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
assert hashlib.sha256(raw).hexdigest()=='99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'
u=Uc(UC_ARCH_X86,UC_MODE_32)
for o in objects:
    u.mem_map(o['base'],(len(o['data'])+4095)&~4095)
    u.mem_write(o['base'],bytes(o['data']))
u.mem_map(0x200000,8192)
rng=random.Random(1996)
for case in range(4000):
    old=[rng.randrange(-100000,100000) for _ in range(3)]
    dest=[rng.randrange(-100000,100000) for _ in range(3)]
    speed=rng.choice([1,4,8,12])
    u.mem_write(0xcb278,struct.pack('<3i',*old))
    u.mem_write(0x200000,struct.pack('<3ih',*dest,0))
    u.reg_write(UC_X86_REG_ESP,0x201ff0)
    u.reg_write(UC_X86_REG_EAX,0x200000)
    u.reg_write(UC_X86_REG_EDX,speed)
    u.emu_start(0x13608,0x13669,count=100)
    actual=struct.unpack('<3i',u.mem_read(0xcb278,12))
    expected=tuple(x+int((y-x)/speed) for x,y in zip(old,dest))
    assert actual==expected,(case,actual,expected)
    # Floating presentation differs only by the DOS integer truncation here.
    assert all(abs(got-(x+(y-x)/speed))<1 for got,x,y in zip(actual,old,dest))
result=dict(cases=4000,span='0x13608..0x13669',normal_chase_divisor=12,
            scope='coordinate update only, not complete DOS camera equivalence')
(ROOT/'analysis/dos-camera-smoothing-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: 4000 DOS camera coordinate updates; signed division and normal chase rate verified')
