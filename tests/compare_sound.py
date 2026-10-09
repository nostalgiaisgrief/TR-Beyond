"""Compare sample selection parameters with the original DOS sound routine."""
from compare_step import *
import math
class Detail(C.Structure):_fields_=[(n,C.c_uint16) for n in ('sample','volume','chance','flags')]
class Plan(C.Structure):_fields_=[(n,C.c_int) for n in ('sample','volume','pitch','mode')]
def main():
 raw,objects,_,_=load(ROOT/'work/reference-drive/TOMBRAID/TOMB.EXE')
 assert hashlib.sha256(raw).hexdigest()=='99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'
 u=Uc(UC_ARCH_X86,UC_MODE_32)
 for o in objects:u.mem_map(o['base'],(len(o['data'])+4095)&~4095);u.mem_write(o['base'],bytes(o['data']))
 for address,size in [(DATA,0x10000),(ITEM,8192),(STACK,4096),(RETURN,4096)]:u.mem_map(address,size)
 def put(a,v,n=4):u.mem_write(a,(v&((1<<(8*n))-1)).to_bytes(n,'little'))
 def get(a):return int.from_bytes(u.mem_read(a,4),'little')
 put(0xc3b38,1);put(0xcec44,0,2);put(0xcee44,DATA);put(0xcc058,DATA+0x1000);put(0xcb284,0,2);put(0xce960,ITEM)
 put(0xcb288,0);put(0xcb28c,0);put(0xcb290,0)
 seen=[]
 def stop(uc,at,size,user):
  sp=uc.reg_read(UC_X86_REG_ESP)
  seen.append((uc.reg_read(UC_X86_REG_EBP),get(sp+0x24),get(sp+0x18),uc.reg_read(UC_X86_REG_ECX)));uc.emu_stop()
 u.hook_add(UC_HOOK_CODE,stop,begin=0x2d50d,end=0x2d50d)
 libs=[C.CDLL(str(ROOT/'build'/f'step_test{s}.dll')) for s in ('','_debug')]
 for lib in libs:lib.tomb_sound_plan.argtypes=[C.POINTER(Detail),C.c_int,C.c_int,C.c_int,C.POINTER(C.c_uint32),C.POINTER(Plan)]
 rng=random.Random(1996)
 for case in range(10000):
  d=Detail(rng.randrange(100),rng.choice([0,1,16383,32767]),rng.choice([0,1,16383,32767]),rng.choice([0,1])|rng.choice([1,2,4])*4|rng.choice([0,0x2000,0x4000,0x6000]))
  distance=rng.choice([0,1,4096,8192,rng.randrange(8193)]);env=rng.randrange(3);wet=rng.randrange(2);seed=rng.getrandbits(32)
  u.mem_write(DATA,bytes(d));put(DATA+0x1042,wet,2);put(DATA+0x2000,distance);put(DATA+0x2004,0);put(DATA+0x2008,0);put(0xc19a8,seed)
  u.reg_write(UC_X86_REG_EAX,0);u.reg_write(UC_X86_REG_EDX,DATA+0x2000);u.reg_write(UC_X86_REG_EBX,env)
  u.reg_write(UC_X86_REG_ESP,STACK+0x800);put(STACK+0x800,RETURN);u.reg_write(UC_X86_REG_EFLAGS,2);seen.clear()
  u.emu_start(0x2d2b4,RETURN,count=10000)
  assert u.reg_read(UC_X86_REG_EIP) in (RETURN,0x2d50d)
  expected_seed=get(0xc19a8)
  for lib in libs:
   s=C.c_uint32(seed);p=Plan();ok=lib.tomb_sound_plan(C.byref(d),distance,env,wet,C.byref(s),C.byref(p))
   assert bool(ok)==bool(seen),(case,bytes(d),distance,env,wet,seen,ok)
   assert s.value==expected_seed,(case,s.value,expected_seed)
   if ok:assert tuple(getattr(p,n) for n,_ in Plan._fields_)==seen[0],(case,seen,p.sample,p.volume,p.pitch,p.mode)
 (ROOT/'analysis/sound-parameters-validation.json').write_text(json.dumps(dict(cases_per_build=10000,builds=2,scope='Original 0x2d2b4 through 0x2d50d, including real RNG/distance math; before channel allocation and hardware playback.'),indent=2)+'\n')
 print('PASS: 10000 DOS sound chance/environment/volume/pitch/sample/RNG cases per build')
if __name__=='__main__':main()
