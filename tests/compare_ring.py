"""DOS ring initialization/motion/rotation/selection and item animation helpers.
Full screen rendering and main inventory input loop are not emulated here.
"""
from compare_inventory import Inventory
from compare_step import *
class RingItem(C.Structure):
 _fields_=[(n,I16) for n in ('object','frames','frame','goal','open_frame','direction','speed','delay','pivot','pivot_now','selected_x','x','selected_y','y')]+[(n,I32) for n in ('selected_yoff','yoff','selected_zoff','zoff')]+[('initial_meshes',C.c_uint32),('meshes',C.c_uint32),('order',I32)]
class Motion(C.Structure):
 _fields_=[(n,I16) for n in ('count','status','target','radius','radius_rate','camera','camera_rate','pitch','pitch_rate','angle','angle_rate','pivot','pivot_rate','x','x_rate')]+[(n,I32) for n in ('y','y_rate','z','z_rate')]
class Ring(C.Structure):
 _fields_=[('items',RingItem*12),('motion',Motion)]+[(n,I16) for n in ('radius','pitch','rotating','rotate_count','current','target','count','step','adder','left_adder','right_adder','angle')]+[('camera_y',I32),('chosen',C.c_int),('ready',C.c_int),('sound',C.c_int)]
RO=DATA;MO=DATA+256;LI=DATA+512;IT=DATA+1024
ring_offsets=dict(radius=6,pitch=8,rotating=10,rotate_count=12,current=14,target=16,count=18,step=20,adder=22,left_adder=24,right_adder=26,angle=42,camera_y=50)
motion_offsets={name:(i*2 if i<15 else 30+(i-15)*4) for i,(name,typ) in enumerate(Motion._fields_)}
class RingOracle(Oracle):
 def __init__(self):
  super().__init__(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'));self.allowed.update(range(DATA,DATA+8192))
 def call(self,fn,eax=RO,edx=0,ebx=0,ecx=0,extra=()):
  self.write(STACK+2048,RETURN,4)
  for n,v in enumerate(extra):self.write(STACK+2052+4*n,v,4)
  for reg,val in [(UC_X86_REG_ESP,STACK+2048),(UC_X86_REG_EAX,eax),(UC_X86_REG_EDX,edx),(UC_X86_REG_EBX,ebx),(UC_X86_REG_ECX,ecx)]:self.uc.reg_write(reg,val&0xffffffff)
  self.bad=[];self.uc.emu_start(fn,RETURN,count=20000);assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN and not self.bad,self.bad
  return self.uc.reg_read(UC_X86_REG_EAX)
 def install(self,r):
  self.uc.mem_write(RO,bytes(80));self.uc.mem_write(MO,bytes(50));self.write(RO,LI,4);self.write(RO+76,MO,4)
  for name,off in ring_offsets.items():self.write(RO+off,getattr(r,name),4 if name=='camera_y' else 2)
  for name,typ in Motion._fields_:self.write(MO+motion_offsets[name],getattr(r.motion,name),C.sizeof(typ))
  for i in range(r.count):self.write(LI+4*i,IT+64*i,4);self.uc.mem_write(IT+64*i,bytes(64));self.uc.mem_write(IT+64*i+4,bytes(r.items[i]))
 def compare(self,r):
  for name,off in ring_offsets.items():assert getattr(r,name)==self.read(RO+off,4 if name=='camera_y' else 2),(name,getattr(r,name),self.read(RO+off,4 if name=='camera_y' else 2))
  for name,typ in Motion._fields_:assert getattr(r.motion,name)==self.read(MO+motion_offsets[name],C.sizeof(typ)),('motion',name,getattr(r.motion,name),self.read(MO+motion_offsets[name],C.sizeof(typ)))
  for i in range(r.count):assert bytes(r.items[i])==bytes(self.uc.mem_read(IT+64*i+4,56)),('item',i)
def main():
 o=RingOracle();rng=random.Random(19961017);total=0
 o.uc.hook_add(UC_HOOK_CODE,lambda *args:o.ret(),begin=0x3dcf4,end=0x3dcf4)
 for suffix in ('','_debug'):
  d=C.CDLL(str(ROOT/'build'/f'step_test{suffix}.dll'));d.tomb_ring_init.argtypes=[C.POINTER(Ring),C.POINTER(Inventory)]
  for fn in ['tomb_ring_motion_tick']:getattr(d,fn).argtypes=[C.POINTER(Ring)]
  for fn in ['tomb_ring_rotate','tomb_ring_select','tomb_ring_tick']:getattr(d,fn).argtypes=[C.POINTER(Ring),C.c_int]
  d.tomb_ring_animate.argtypes=[C.POINTER(RingItem)]
  for trial in range(100):
   inv=Inventory();inv.counts[0]=1
   for slot in [1,2,3,5,6,7,9,10]:inv.counts[slot]=rng.randrange(2)
   r=Ring();assert d.tomb_ring_init(C.byref(r),C.byref(inv));o.install(r)
   o.write(0xc3814,0,4);o.call(0x240bc,RO,0,LI,r.count,(0,MO));o.call(0x242c0,RO,24);o.compare(r)
   for _ in range(32):o.call(0x24304);d.tomb_ring_motion_tick(C.byref(r));o.compare(r);total+=1
   for turn in range(6):
    right=rng.randrange(2);o.call(0x24484 if right else 0x244b4);d.tomb_ring_rotate(C.byref(r),right);o.compare(r)
    for t in range(24):o.call(0x24304);d.tomb_ring_motion_tick(C.byref(r));o.compare(r);total+=1
   for deselect in [0,1]:
    r.motion=Motion();r.motion.count=16;o.install(r);o.call(0x24678 if deselect else 0x2460c,RO,IT+64*r.current);d.tomb_ring_select(C.byref(r),deselect);o.compare(r)
    for _ in range(16):o.call(0x24304);d.tomb_ring_motion_tick(C.byref(r));o.compare(r);total+=1
   for index in range(r.count):
    item=r.items[index];item.frame=rng.randrange(item.frames);item.goal=rng.randrange(item.frames);item.direction=rng.choice([-1,1]);o.install(r)
    for _ in range(55):
     expected=o.call(0x227cc,IT+64*index);actual=d.tomb_ring_animate(C.byref(item));assert expected==actual;o.compare(r);total+=1
  d.tomb_ring_init_keys.argtypes=[C.POINTER(Ring),C.POINTER(Inventory)]
  d.tomb_ring_change_begin.argtypes=[C.POINTER(Ring),C.c_int]
  d.tomb_ring_change_end.argtypes=[C.POINTER(Ring),C.c_int,C.c_int]
  for keys in (0,1):
   inv=Inventory();inv.counts[0]=1
   for q in range(8):inv.quest[q]=1
   r=Ring();assert d.tomb_ring_init_keys(C.byref(r),C.byref(inv))
   addresses={114:0xc302c,115:0xc306c,116:0xc30ac,117:0xc30ec,133:0xc312c,134:0xc316c,135:0xc31ac,136:0xc31ec}
   for item in r.items[:r.count]:assert bytes(item)==bytes(o.uc.mem_read(addresses[item.object],56)),('quest descriptor',item.object)
   o.install(r);o.write(0xc3814,0,4);o.call(0x240bc,RO,2,LI,r.count,(0,MO));o.call(0x242c0,RO,24)
   # Ring type itself is external to the compact native Ring structure.
   o.compare(r)
   for _ in range(32):o.call(0x24304);d.tomb_ring_motion_tick(C.byref(r));o.compare(r)
   o.install(r);o.call(0x24564,RO,2,4 if keys else 5,24);o.call(0x24580,RO,0);o.call(0x245a8,RO,-32768,C.c_int16(r.angle-32768).value);o.call(0x245ec,RO,8192 if keys else -8192)
   assert d.tomb_ring_change_begin(C.byref(r),keys);o.compare(r)
   for _ in range(24):o.call(0x24304);d.tomb_ring_motion_tick(C.byref(r));o.compare(r)
  d.tomb_ring_item_spin.argtypes=[C.POINTER(RingItem),C.c_int,C.c_int,C.c_int,C.c_int,C.c_uint]
  o.allowed.update(range(0x12f3f0,0x12f3f4))
  for trial in range(2000):
   item=RingItem();item.y=rng.randrange(-128,128)*256;item.selected_y=rng.choice([0,-4096,-8192]);selected=rng.randrange(2);rotating=rng.randrange(2);status=rng.randrange(14);count=rng.randrange(1,11);input=rng.randrange(4)
   o.uc.mem_write(IT+4,bytes(item));sp=STACK+2048;o.uc.mem_write(sp,bytes(128));o.write(sp+10,rotating,2);o.write(sp+18,count,2);o.write(sp+82,status,2)
   o.write(0xc2590,1,4);o.write(0xce92c,(4 if input&1 else 0)|(8 if input&2 else 0),4)
   for reg,val in [(UC_X86_REG_ESP,sp),(UC_X86_REG_ECX,IT),(UC_X86_REG_EAX,0)]:o.uc.reg_write(reg,val)
   o.bad=[];o.uc.emu_start(0x2179c if selected else 0x218e6,0x21888 if selected else 0x21922,count=1000);assert not o.bad,o.bad
   d.tomb_ring_item_spin(C.byref(item),selected,rotating,status,count,input)
   assert item.y==o.read(IT+30,2),(trial,selected,rotating,status,item.y,o.read(IT+30,2))
  d.tomb_ring_compass.argtypes=[I16,I16,C.POINTER(I16),C.POINTER(I16)]
  o.allowed.update(range(0xc3822,0xc3826))
  for trial in range(1000):
   yaw=rng.randrange(-32768,32768);lara=rng.randrange(-32768,32768);angle=I16(rng.randrange(-32768,32768));velocity=I16(rng.randrange(-2000,2001))
   o.write(IT+30,yaw,2);o.write(0xce960,ITEM,4);o.write(ITEM+62,lara,2);o.write(0xc3822,velocity.value,2);o.write(0xc3824,angle.value,2)
   o.uc.reg_write(UC_X86_REG_ESP,STACK+2048);o.uc.reg_write(UC_X86_REG_EAX,IT);o.bad=[];o.uc.emu_start(0x22b70,0x22bd5,count=1000);assert not o.bad,o.bad
   d.tomb_ring_compass(yaw,lara,C.byref(angle),C.byref(velocity));assert angle.value==o.read(0xc3824,2) and velocity.value==o.read(0xc3822,2)
  # Execute DOS object/bone gating as well as the integrator: lid/body must not rotate.
  d.tomb_ring_compass_bone.argtypes=[C.c_int,C.c_uint,C.c_uint]
  for object_id in (72,99,108):
   for mesh_count in (4,5,8):
    for index in range(1,mesh_count):
     o.write(IT+4,object_id,2);o.write(IT+30,4096,2);o.write(0xce960,ITEM,4);o.write(ITEM+62,8192,2)
     o.write(0xc3822,20,2);o.write(0xc3824,100,2);o.write(STACK+2048+24,IT,4)
     o.uc.reg_write(UC_X86_REG_ESP,STACK+2048);o.uc.reg_write(UC_X86_REG_ESI,mesh_count-index)
     o.bad=[];o.uc.emu_start(0x22b5a,0x22bd5,count=1000);assert not o.bad,o.bad
     angle=I16(100);velocity=I16(20)
     if d.tomb_ring_compass_bone(object_id,mesh_count,index):d.tomb_ring_compass(4096,8192,C.byref(angle),C.byref(velocity))
     assert (angle.value,velocity.value)==(o.read(0xc3824,2),o.read(0xc3822,2)),(object_id,mesh_count,index)
  # Complete native input lifecycle: repeated rotation, opening, item use and back.
  inv=Inventory();inv.counts[0]=1;inv.counts[9]=1;r=Ring();d.tomb_ring_init(C.byref(r),C.byref(inv))
  for _ in range(16):d.tomb_ring_tick(C.byref(r),0)
  assert r.motion.status==1 and r.radius==688
  d.tomb_ring_tick(C.byref(r),2)
  for _ in range(12):d.tomb_ring_tick(C.byref(r),0)
  assert r.items[r.current].object==108
  d.tomb_ring_tick(C.byref(r),4)
  for _ in range(160):d.tomb_ring_tick(C.byref(r),0)
  assert r.motion.status==13 and r.chosen==108
  d.tomb_ring_init(C.byref(r),C.byref(inv))
  for _ in range(16):d.tomb_ring_tick(C.byref(r),0)
  d.tomb_ring_tick(C.byref(r),4)
  for _ in range(80):d.tomb_ring_tick(C.byref(r),0)
  assert r.ready and r.items[0].frame==10
  d.tomb_ring_tick(C.byref(r),8)
  for _ in range(80):d.tomb_ring_tick(C.byref(r),0)
  assert r.motion.status==1 and r.items[0].frame==24 and r.items[0].zoff==0
 (ROOT/'analysis/ring-validation.json').write_text(json.dumps(dict(builds=2,original_helper_ticks=total,spin_cases_per_build=2000,compass_cases_per_build=1000,scope=__doc__),indent=2))
 print('PASS: DOS ring helpers and item animation:',total,'ticks; native use/cancel lifecycle')
if __name__=='__main__':main()
