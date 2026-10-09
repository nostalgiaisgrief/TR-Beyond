"""DOS camera box-shift arithmetic and pitch projection, using original instructions.
Geometry clearance is tested separately by follow_camera_test; no full-camera
DOS equivalence is implied by these isolated arithmetic probes.
"""
import ctypes as C, hashlib, json, math, random, struct, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from analyse_le import load
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import *
raw,objects,_,_=load(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
assert hashlib.sha256(raw).hexdigest()=='99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'
u=Uc(UC_ARCH_X86,UC_MODE_32)
for o in objects:
    u.mem_map(o['base'],(len(o['data'])+4095)&~4095);u.mem_write(o['base'],bytes(o['data']))
u.mem_map(0x200000,0x4000)
def put(a,*values):u.mem_write(a,struct.pack('<'+'i'*len(values),*values))
def reg(r,v):u.reg_write(r,v&0xffffffff)
libraries=[C.CDLL(str(ROOT/'build'/('step_test'+suffix+'.dll'))) for suffix in ('','_debug')]
for dll in libraries:
    dll.tomb_camera_box_shift.argtypes=[C.POINTER(C.c_double),C.POINTER(C.c_double)]+[C.c_double]*7
rng=random.Random(19961009)
for i in range(12000):
    tp,tq=[rng.randrange(-5000,5000) for _ in range(2)]
    bound,opposite=[tp+rng.randrange(-3000,3001) for _ in range(2)]
    near,far=[tq+rng.randrange(-3000,3001) for _ in range(2)]
    r2=rng.choice([0,65536,1800**2,rng.randrange(1,9000000)])
    p,q=tp+rng.randrange(-2000,2001),tq+rng.randrange(-2000,2001)
    put(0x200000,p,q);put(0xcb2b5,r2)
    put(0x202000,0x203000,bound,near,opposite,far)
    for r,v in [(UC_X86_REG_EAX,0x200000),(UC_X86_REG_EDX,0x200004),(UC_X86_REG_EBX,tp),(UC_X86_REG_ECX,tq),(UC_X86_REG_ESP,0x202000)]:reg(r,v)
    u.emu_start(0x13978,0x203000,count=2000)
    actual=struct.unpack('<2i',u.mem_read(0x200000,8))
    for dll in libraries:
        cp,cq=C.c_double(p),C.c_double(q)
        dll.tomb_camera_box_shift(C.byref(cp),C.byref(cq),tp,tq,bound,near,opposite,far,r2)
        assert (cp.value,cq.value)==actual,(i,actual,cp.value,cq.value,tp,tq,bound,near,opposite,far,r2)
# Normal submerged chase starts with zero elevation; surface adds -4004.
# Execute original trigonometry too. Small differences are lookup quantization.
max_error=0
for base in (0,-4004):
    for pitch in range(-18200,18201,364):
        for yaw in (0,8192,16384,-16384,32767):
            u.mem_write(0x200000,bytes(80))
            u.mem_write(0x20003c,struct.pack('<hh',pitch,yaw))
            u.mem_write(0xcb2bd,struct.pack('<h',base))
            u.mem_write(0xcb2b9,struct.pack('<h',0))
            put(0xcb288,4096,-2048,4096);put(0xcb2b1,1800)
            reg(UC_X86_REG_EAX,0x200000);reg(UC_X86_REG_ESP,0x202000)
            u.emu_start(0x13f54,0x14025,count=1000)
            sp=u.reg_read(UC_X86_REG_ESP)
            actual=struct.unpack('<3i',u.mem_read(sp,12))
            elev=max(-15470,min(15470,pitch+base))*math.tau/65536
            angle=yaw*math.tau/65536
            expected=(4096-math.sin(angle)*math.cos(elev)*1800,-2048+math.sin(elev)*1800,4096-math.cos(angle)*math.cos(elev)*1800)
            err=max(abs(a-b) for a,b in zip(actual,expected));max_error=max(max_error,err)
            assert err<5,(base,pitch,yaw,actual,expected,err)
result=dict(box_cases=12000,builds=2,pitch_projection_cases=1010,max_projection_error=max_error,
            scope=__doc__)
(ROOT/'analysis/camera-obstacle-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: 12000 DOS box-shift cases per build and 1010 DOS pitch projections; max error',max_error)
