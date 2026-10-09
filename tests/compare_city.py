"""Compare City bounds, block floor mutation, move clearance and object animation with DOS."""
from compare_dos_camera import *
from compare_static import StaticOracle
class CityOracle(CameraOracle,StaticOracle):pass

def main():
 rng=random.Random(961017);f=parse(ROOT/'work/reference-assets/DATA/LEVEL2.PHD');o=CityOracle();o.static_calls=0;o.install(f);o.install_models(f)
 for suffix in ('','_debug'):
  d=bind(ROOT/'build'/f'step_test{suffix}.dll')
  d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p
  d.tomb_objects_init.argtypes=[C.POINTER(Objects),C.POINTER(Level),C.c_void_p]
  d.tomb_objects_free.argtypes=[C.POINTER(Objects)];d.tomb_visual_free.argtypes=[C.c_void_p]
  d.tomb_city_bounds.argtypes=[C.POINTER(Actor),C.POINTER(Actor),I16,I16,C.c_int,C.POINTER(I16)]
  d.tomb_block_floor.argtypes=[C.POINTER(Objects),SZ,C.c_int]
  d.tomb_block_can_move.argtypes=[C.POINTER(Objects),C.POINTER(Actor),SZ,C.c_int,C.c_int]
  d.tomb_water_switch_contact.argtypes=[C.POINTER(Object),C.POINTER(Actor),C.POINTER(AnimContext),C.c_uint32,C.c_int,C.POINTER(I16),C.POINTER(I16)]
  d.tomb_object_animate.argtypes=[C.POINTER(Object),C.POINTER(AnimContext)]
  err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL2.PHD').encode(),err,256);v=d.tomb_visual_load(l,err,256);assert v,err.value
  w=Objects();assert d.tomb_objects_init(C.byref(w),l,v)
  def sync():
   for ri,(at,n) in enumerate(o.sectors):o.uc.mem_write(at,C.string_at(l.contents.rooms[ri].sectors,n*8))
   for i in range(l.contents.box_count):o.write(BOXES+20*i+18,l.contents.boxes[i].overlap,2)
  sync()
  for water in (0,1):
   for trial in range(1200):
    b=Actor(50000,1024,50000,1,1,233,0,0,0,rng.choice([0,16384,-16384,-32768]),0,32)
    a=clone(b);a.x+=rng.randrange(-1100,1101);a.z+=rng.randrange(-1100,1101);a.y+=rng.choice([0,0,rng.randrange(-1100,1101)]);a.yaw=C.c_int16(b.yaw+rng.randrange(-15000,15001)).value
    pitch=rng.choice([0,rng.randrange(-15000,15001)]);roll=rng.choice([0,rng.randrange(-15000,15001)])
    o.put(ITEM,a,ACTOR);o.write(ITEM+0x3c,pitch,2);o.write(ITEM+0x40,roll,2);o.put_object(Object(b,0,0,56 if water else 48,0))
    expected=o.call(0x168b0,0xc3d8c if water else 0xc3b6c,ITEMS,ITEM,0)
    actual=d.tomb_city_bounds(C.byref(a),C.byref(b),pitch,roll,water,o.sine);assert bool(actual)==bool(expected),(trial,water)
  # Exact original floor and navigation-box changes, alternating removal/addition.
  for delta in (1024,-1024)*10:
   o.put_object(w.items[0]);o.call(0x2f380,ITEMS,delta,0,0);assert d.tomb_block_floor(C.byref(w),0,delta)
   for ri,(at,n) in enumerate(o.sectors):assert bytes(o.uc.mem_read(at,n*8))==C.string_at(l.contents.rooms[ri].sectors,n*8),('floor',ri,delta)
  # Actual City geometry and statics, all cardinal push/pull directions and nearby placements.
  original=clone(w.items[0].actor)
  for trial in range(240):
   b=w.items[0].actor;b.x=original.x+rng.choice([0,0,-1024,1024]);b.z=original.z+rng.choice([0,0,-1024,1024]);b.y=original.y
   q=trial%4;b.yaw=C.c_int16(q*16384).value;a=clone(b);dx=[0,1,0,-1][q];dz=[1,0,-1,0][q];a.x-=dx*612;a.z-=dz*612
   o.put_object(w.items[0]);o.put(ITEM,a,ACTOR);o.write(0xce960,ITEM,4)
   for pull in (0,1):
    expected=o.call(0x2f00c if pull else 0x2eefc,ITEMS,1024,q,0)
    actual=d.tomb_block_can_move(C.byref(w),C.byref(a),0,q,pull);assert bool(actual)==bool(expected),('move',trial,q,pull,actual,expected)
  w.items[0].actor=original
  @EVENT
  def event(*args):pass
  q=l.contents;ctx=AnimContext(q.animations,q.animation_count,q.changes,q.change_count,q.ranges,q.range_count,q.commands,q.command_count,o.sine,0,0,0,event,None)
  for trial in range(800):
   yaw=rng.choice([0,16384,-16384,-32768]);current=rng.randrange(2);an=q.animations[240 if current else 241]
   b=Object(Actor(50000,1024,50000,current,current,240 if current else 241,an.first_frame,0,0,yaw,26,32),0,0,56,0)
   a=Actor(50000,1024,50000,13,13,108,1736,0,rng.randrange(30),yaw,26,32)
   if trial%3:
    a.x+=rng.randrange(-1100,1101);a.y+=rng.randrange(-1100,1101);a.z+=rng.randrange(-1100,1101)
   else:
    a.x+=[0,108,-108,0][[0,16384,-16384,-32768].index(yaw)];a.z+=[108,0,0,-108][[0,16384,-16384,-32768].index(yaw)]
   pitch=I16(rng.choice([0,0,1000]));roll=I16(rng.choice([0,0,-500]));water=rng.choice([1,1,1,2]);inp=rng.choice([64,64,0]);ctx.weapon_status=0;ctx.move_angle=a.yaw
   o.put_object(b);o.put(ITEM,a,ACTOR);o.write(ITEM+0x3c,pitch.value,2);o.write(ITEM+0x40,roll.value,2)
   for addr,val,width in [(0xce96e,water,2),(0xce966,0,2),(0xce9ce,a.yaw,2),(0xce96c,0,2),(0xce92c,inp,4)]:o.write(addr,val,width)
   o.call(0x345d4,0,ITEM,0,0)
   assert d.tomb_water_switch_contact(C.byref(b),C.byref(a),C.byref(ctx),inp,water,C.byref(pitch),C.byref(roll))
   assert state(a)==state(o.get(ITEM,Actor,ACTOR)),('switch',trial,state(a),state(o.get(ITEM,Actor,ACTOR)))
   assert pitch.value==o.read(ITEM+0x3c,2) and roll.value==o.read(ITEM+0x40,2)
   assert ctx.weapon_status==o.read(0xce966,2);o.compare(b)
  for animation in (234,235,242,243):
   an=q.animations[animation]
   for frame in range(an.first_frame,an.last_frame+1):
    b=Object(Actor(60928,1024,29184,an.state,an.state,animation,frame,0,0,rng.choice([0,16384,-16384,-32768]),0,35),0,0,48 if animation<240 else 56,1)
    o.put_object(b);o.call(0x16ff4,ITEMS,0,0,0);assert d.tomb_object_animate(C.byref(b),C.byref(ctx));o.compare(b)
  d.tomb_objects_free(C.byref(w));d.tomb_visual_free(v);d.tomb_level_free(l)
 print('PASS: both builds, 2400 bounds, 20 floor mutations, 480 move checks, 800 underwater switch contacts and 571 object animation frames against DOS')
if __name__=='__main__':main()
