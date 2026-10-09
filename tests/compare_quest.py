"""City quest contact, inventory consumption and key gates against original DOS code."""
from compare_city import *
from compare_inventory import Inventory
def main():
 o=CityOracle();o.static_calls=0;f=parse(ROOT/'work/reference-assets/DATA/LEVEL2.PHD');o.install(f);o.install_models(f)
 for start,end in [(0xc2c00,0xc3500),(0xcee50,0xcee5c),(0xc37f2,0xc37f4)]:o.allowed.update(range(start,end))
 for addr in (0x24d00,0x21498):o.uc.hook_add(UC_HOOK_CODE,lambda *args:o.ret(),begin=addr,end=addr)
 rng=random.Random(961020)
 for suffix in ('','_debug'):
  d=bind(ROOT/'build'/f'step_test{suffix}.dll');d.tomb_quest_contact.argtypes=[C.POINTER(Object),C.POINTER(Actor),C.POINTER(AnimContext),C.POINTER(Inventory),C.POINTER(I16),C.POINTER(I16),C.c_int]
  d.tomb_key_trigger.argtypes=[C.POINTER(Object),C.c_int]
  err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL2.PHD').encode(),err,256);q=l.contents
  @EVENT
  def event(*args):pass
  for trial in range(1000):
   puzzle=trial%2;id=118 if puzzle else 137;chosen=rng.choice([114,133,-1]);yaw=rng.choice([0,16384,-16384,-32768])
   b=Object(Actor(50000,0,50000,0,0,0,0,0,0,yaw,0,32),0,0,id,0)
   xx,zz={0:(0,400),16384:(400,0),-16384:(-400,0),-32768:(0,-400)}[yaw]
   a=Actor(50000+xx,0,50000+zz,2,2,11,185,0,0,yaw,0,32)
   if trial%3:a.x+=rng.randrange(-250,251);a.z+=rng.randrange(-250,251)
   pitch=I16(rng.choice([0,0,1820,1821]));roll=I16(0);action=rng.randrange(2);weapon=rng.choice([0,0,0,1])
   inv=Inventory();inv.chosen=chosen;inv.quest[0]=inv.quest[4]=1
   o.call(0x23d3c,0,0,0,0);o.call(0x2371c,110,0,0,0);o.call(0x2371c,129,0,0,0)
   ctx=AnimContext(q.animations,q.animation_count,q.changes,q.change_count,q.ranges,q.range_count,q.commands,q.command_count,o.sine,a.yaw,0,weapon,event,None)
   o.put_object(b);o.put(ITEM,a,ACTOR);o.write(ITEM+0x3c,pitch.value,2);o.write(ITEM+0x40,roll.value,2)
   for addr,val,width in [(0xc37f2,chosen,2),(0xce966,weapon,2),(0xce9ce,a.yaw,2),(0xce96c,0,2),(0xce92c,64 if action else 0,4)]:o.write(addr,val,width)
   o.call(0x34904 if puzzle else 0x346c4,0,ITEM,0,0)
   result=d.tomb_quest_contact(C.byref(b),C.byref(a),C.byref(ctx),C.byref(inv),C.byref(pitch),C.byref(roll),action);assert result
   assert state(a)==state(o.get(ITEM,Actor,ACTOR)),('actor',trial,state(a),state(o.get(ITEM,Actor,ACTOR)))
   assert ctx.weapon_status==o.read(0xce966,2);o.compare(b)
   assert inv.chosen==o.read(0xc37f2,2),('chosen',trial)
   assert inv.quest[0]==o.call(0x23cc0,110,0,0,0) and inv.quest[4]==o.call(0x23cc0,129,0,0,0),('inventory',trial)
   # Original status gate holds the door trigger until hands are free, consumes once.
   for status in (0,2,4,6):
    b.actor.flags=32|status;o.put_object(b);o.write(0xce966,weapon,2)
    expected=o.call(0x34c50,0,0,0,0);actual=d.tomb_key_trigger(C.byref(b),weapon);assert actual==expected;o.compare(b)
  # Closed/open trapdoor controller and its timer are original instructions.
  trap_hook=o.uc.hook_add(UC_HOOK_CODE,lambda *args:o.ret(),begin=0x16ff4,end=0x16ff4)
  d.tomb_trapdoor_control.argtypes=[C.POINTER(Object)]
  for trial in range(1000):
   b=Object(Actor(current=trial%2,goal=rng.randrange(2),flags=35),rng.choice([0,0x3e00,0x4000,0x7e00]),rng.choice([-1,0,1,2,30]),65,1)
   o.put_object(b);o.call(0x3a47c,0,0,0,0);d.tomb_trapdoor_control(C.byref(b));o.compare(b)
  o.uc.hook_del(trap_hook)
  d.tomb_level_free(l)
 print('PASS: per build 1000 key/idol contacts and consumption cases, 4000 key-trigger gates, 1000 trapdoor controls against DOS')
if __name__=='__main__':main()
