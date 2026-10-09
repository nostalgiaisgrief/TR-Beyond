"""Swan/fast-dive controls and collision against the supplied DOS executable."""
from compare_air import *
def main():
 o=AirOracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'));rng=random.Random(961019)
 for suffix in ('','_debug'):
  d=setup_library(ROOT/'build'/f'step_test{suffix}.dll')
  d.tomb_swan_control.argtypes=[C.POINTER(Actor),C.POINTER(Contact)]
  d.tomb_swan_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air)]
  for trial in range(4000):
   st=52+trial%2;a=Actor(x=123,y=456,z=789,current=st,goal=st,animation=119,frame=2000,speed=rng.randrange(-32768,32768),fall_speed=rng.choice([-1,0,1,130,131,132,133,134,160,32767]),yaw=rng.randrange(-32768,32768),room=1,flags=rng.randrange(256))
   c=Contact(floor=rng.choice([-32512,-200,-1,0,1,200]),shift_x=8,shift_y=-5,shift_z=2,old_x=123,old_y=456,old_z=789,facing=17,type=rng.choice([0,1,2,3,4,8,16,32,64]),flags=rng.randrange(256))
   expected=o.run(0x26014 if st==52 else 0x26038,a,c);ec=o.get(COLL,Contact,CONTACT)
   aa=clone(a);cc=clone(c);d.tomb_swan_control(C.byref(aa),C.byref(cc));assert state(aa)==state(expected) and state(cc)==state(ec),('control',trial)
   o.write(0xce9ce,17,2);expected=o.run(0x27280 if st==52 else 0x27304,a,c);ec=o.get(COLL,Contact,CONTACT);ev=o.events[:]
   events=[]
   @QUERY
   def query(_,pa,pc,h):events.append(('query',state(pa.contents),state(pc.contents),h))
   aa=clone(a);cc=clone(c);ctx=Air(query,ACTION(),None,o.sine,17)
   assert d.tomb_swan_collision(C.byref(aa),C.byref(cc),C.byref(ctx))
   assert state(aa)==state(expected),(trial,state(aa),state(expected))
   assert state(cc)==state(ec) and ctx.move_angle==o.read(0xce9ce,2) and events==ev,('collision',trial)
 print('PASS: each build matches DOS for 4000 swan/fast-dive controls and 4000 collision cases')
if __name__=='__main__':main()
