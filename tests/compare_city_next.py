"""DOS automatic interest look and City pendulum controller/damage decisions."""
from compare_dos_camera import *
def main():
 o=CameraOracle();f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o.install(f);o.install_models(f)
 rng=random.Random(961021)
 for suffix in ('','_debug'):
  o.install(f);o.install_models(f)
  d=bind(ROOT/'build'/f'step_test{suffix}.dll')
  d.tomb_camera_interest.argtypes=[C.POINTER(Actor),C.POINTER(I16),C.POINTER(Actor),C.POINTER(I16),C.POINTER(I16),C.POINTER(I16)]
  d.tomb_blade_control.argtypes=[C.POINTER(Object),C.c_uint32]
  for t in range(4000):
   a=Actor(50000,3000,30000,2,2,11,185,0,0,rng.randrange(-32768,32768),4,32)
   b=Actor(a.x+rng.randrange(-12000,12001),a.y+rng.randrange(-12000,12001),a.z+rng.randrange(-12000,12001),0,0,0,0,0,0,0,4,32)
   o.put(ITEM,a,ACTOR);o.write(ITEM+12,0,2);o.put_object(Object(b,0,0,169,0));o.write(0xcb2c9,ITEMS,4)
   bp=o.call(0x1d444,ITEM,0,0,0);ab=(I16*6).from_buffer_copy(o.uc.mem_read(bp,12));bp=o.call(0x1d444,ITEMS,0,0,0);bb=(I16*6).from_buffer_copy(o.uc.mem_read(bp,12))
   hy=I16(rng.randrange(-10000,10001));hp=I16(rng.randrange(-15000,15001));o.write(0xce9d0,hy.value,2);o.write(0xce9d2,hp.value,2);o.write(0xcb298,0,1)
   for reg,val in [(UC_X86_REG_ESP,STACK+1024),(UC_X86_REG_ESI,ITEM),(UC_X86_REG_EDI,0),(UC_X86_REG_EBX,a.y+ab[3]+((3*(ab[2]-ab[3]))>>2))]:o.uc.reg_write(reg,val&0xffffffff)
   o.uc.emu_start(0x146f8,0x1487b,count=1000)
   result=d.tomb_camera_interest(C.byref(a),ab,C.byref(b),bb,C.byref(hy),C.byref(hp))
   assert result==(o.read(0xcb298,1)==2) and hy.value==o.read(0xce9d0,2) and hp.value==o.read(0xce9d2,2),('look',t,result,hy.value,hp.value,o.read(0xce9d0,2),o.read(0xce9d2,2))
  # Blood RNG/particle creation is skipped here; health, hit flag, trigger timer and goals execute.
  hook=o.uc.hook_add(UC_HOOK_CODE,lambda u,*args:u.reg_write(UC_X86_REG_EIP,0x3a6f5),begin=0x3a64b,end=0x3a64b)
  for t in range(2000):
   b=Object(Actor(current=rng.randrange(3),goal=rng.randrange(3),flags=35),rng.choice([0,0x3e00,0x4000,0x7e00]),rng.choice([-1,0,1,2,30]),36,1);touch=rng.choice([0,1,4,7])
   o.put_object(b);o.write(ITEMS+4,touch,4);o.write(0xce960,ITEM,4);o.write(ITEM+0x22,1000,2);o.write(ITEM+0x42,32,1)
   o.uc.reg_write(UC_X86_REG_EAX,0);o.uc.reg_write(UC_X86_REG_ESP,STACK+1024);o.uc.emu_start(0x3a5d8,0x3a6f5,count=1000)
   damage=d.tomb_blade_control(C.byref(b),touch);o.compare(b);assert damage==1000-o.read(ITEM+0x22,2);assert bool(damage)==bool(o.read(ITEM+0x42,1)&16)
  o.uc.hook_del(hook)
  city=parse(ROOT/'work/reference-assets/DATA/LEVEL2.PHD');o.install(city);o.install_models(city)
  err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL2.PHD').encode(),err,256);q=l.contents
  models=[struct.unpack_from('<IHHIIH',city['sections']['models']['bytes'],18*i) for i in range(city['sections']['models']['count'])]
  first=next(m[-1] for m in models if m[0]==36);end=min(m[-1] for m in models if first<m[-1]<65535)
  events=[]
  @EVENT
  def event(_,kind,id,a):events.append((kind,id))
  ctx=AnimContext(q.animations,q.animation_count,q.changes,q.change_count,q.ranges,q.range_count,q.commands,q.command_count,o.sine,0,0,0,event,None)
  d.tomb_object_animate.argtypes=[C.POINTER(Object),C.POINTER(AnimContext)]
  cases=0;sounds=set()
  for index in range(first,end):
   an=q.animations[index]
   for frame in range(an.first_frame,an.last_frame+1):
    for goal in (0,2):
     b=Object(Actor(24064,-1024,29184,an.state,goal,index,frame,0,0,-16384,61,35),0,0,36,1)
     o.put_object(b);o.events=[];events.clear();o.call(0x16ff4,ITEMS,0,0,0)
     assert d.tomb_object_animate(C.byref(b),C.byref(ctx));o.compare(b)
     assert events==[(e[0],e[1]) for e in o.events];sounds.update(id for kind,id in events if kind==5);cases+=1
  assert sounds;d.tomb_level_free(l);print('Blade animation frames/goals',suffix or 'release',cases,'sound IDs',sorted(sounds))
 print('PASS: each build: 4000 DOS automatic-look angle/limit/smoothing cases, 2000 pendulum trigger/damage cases')
if __name__=='__main__':main()
