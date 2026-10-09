"""Execute DOS HUD decisions, palette line primitives and completion text calls."""
from compare_ring import RingOracle
from compare_ground import *
from compare_inventory import Inventory
class Hud(C.Structure):
 _fields_=[('health',C.c_int),('last_health',C.c_int),('timer',C.c_int),('pickup_id',C.c_int*3),('pickup_time',C.c_int*3)]
LINE=C.CFUNCTYPE(None,C.c_void_p,*([C.c_int]*5))
def main():
 o=RingOracle();lines=[];printed=[];shown=[];counts={};rng=random.Random(19961021)
 def string(at):
  out=bytearray()
  while (v:=o.uc.mem_read(at,1)[0]):out.append(v);at+=1
  return out.decode('latin1')
 def hook(u,at,size,data):
  sp=u.reg_read(UC_X86_REG_ESP)
  if at==0x3d530:
   lines.append(tuple(C.c_int32(u.reg_read(r)).value for r in [UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EBX,UC_X86_REG_ECX])+(o.read(sp+8,4),));o.ret(pop=8)
  elif at==0x47dc5:
   dest=o.read(sp+4,4);fmt=string(o.read(sp+8,4));types=__import__('re').findall(r'%[^a-zA-Z]*([sd])',fmt)
   args=[o.read(sp+12+4*i,4) for i in range(len(types))];args=[string(v) if t=='s' else v for t,v in zip(types,args)]
   result=(fmt%tuple(args)).encode('latin1');o.uc.mem_write(dest,result+b'\0');o.ret(len(result))
  elif at==0x39614:
   printed.append((C.c_int32(u.reg_read(UC_X86_REG_EAX)).value,C.c_int32(u.reg_read(UC_X86_REG_EDX)).value,string(u.reg_read(UC_X86_REG_ECX))));o.ret(DATA+1000+len(printed)*64)
  elif at in (0x3981c,0x3982c,0x3984c,0x209b8):o.ret()
  elif at==0x23cc0:o.ret(counts.get(u.reg_read(UC_X86_REG_EAX),0))
  elif at==0x10668:shown.append(u.reg_read(UC_X86_REG_EAX));o.ret()
 for at in [0x3d530,0x47dc5,0x39614,0x3981c,0x3982c,0x3984c,0x23cc0]:o.uc.hook_add(UC_HOOK_CODE,hook,begin=at,end=at)
 for at,n in [(0xc2038,4),(0xc387c,4),(0xcefb6,2)]:o.allowed.update(range(at,at+n))
 for suffix in ('','_debug'):
  d=C.CDLL(str(ROOT/'build'/f'step_test{suffix}.dll'));d.tomb_hud_bar.argtypes=[C.c_int,C.c_int,C.c_int,LINE,C.c_void_p]
  d.tomb_statistics.argtypes=[C.c_uint,C.c_uint,C.c_uint,C.c_uint,C.c_int,C.c_void_p]
  d.tomb_hud_health.argtypes=[C.POINTER(Hud),C.c_int,C.c_int,C.c_int]
  d.tomb_hud_pickup.argtypes=[C.POINTER(Hud),C.c_int]
  d.tomb_hud_tick.argtypes=[C.POINTER(Hud),C.c_int]
  d.tomb_inventory_label.argtypes=[C.POINTER(Inventory),C.c_int,C.c_void_p]
  for air in (0,1):
   for width in (320,640,960):
    for percent in (0,1,25,50,99,100):
     lines.clear();o.write(0xc2054,width,2);o.call(0x1083c if air else 0x10668,percent)
     expected=lines[:];actual=[]
     cb=LINE(lambda _,a,b,c,e,f:actual.append((a,b,c,e,f)));d.tomb_hud_bar(percent,air,width,cb,None)
     assert actual==expected,('bar',air,width,percent,actual,expected)
  hhook=o.uc.hook_add(UC_HOOK_CODE,hook,begin=0x10668,end=0x10668)
  for n in range(1000):
   health=rng.randrange(-1000,2001);old=rng.randrange(1001);timer=rng.randrange(-10,50);weapon=rng.randrange(5)
   o.write(0xce960,ITEM,4);o.write(ITEM+0x22,health,2);o.write(0xc2038,old,4);o.write(0xc387c,timer,4);o.write(0xce966,weapon,2);shown.clear();o.call(0x209b8)
   h=Hud(health,old,timer);value=d.tomb_hud_health(C.byref(h),health,weapon,0)
   assert value==(shown[0] if shown else -1) and h.timer==o.read(0xc387c,4) and h.last_health==o.read(0xc2038,4)
  o.uc.hook_del(hhook)
  for ticks in (0,29,30,1799,1800,107999,108000,129599,1234567):
   for secrets in (0,1,7,0x8080):
    kills=rng.randrange(100);pickups=rng.randrange(256);o.write(0xcefae,ticks,4);o.write(0xcefb2,kills,4);o.write(0xcefba,pickups,1);o.write(0xcefb6,secrets,2)
    o.uc.reg_write(UC_X86_REG_ESI,1);o.uc.reg_write(UC_X86_REG_ESP,STACK+2048);printed.clear();o.bad=[]
    o.uc.emu_start(0x20154,0x2037e,count=10000);assert not o.bad,o.bad
    out=((C.c_char*80)*4)();d.tomb_statistics(ticks,kills,pickups,secrets,3,out)
    expected={y:text for x,y,text in printed};assert [bytes(row).split(b'\0')[0].decode() for row in out]==[expected[y] for y in (-20,10,40,70)],printed
  med_hook=o.uc.hook_add(UC_HOOK_CODE,hook,begin=0x209b8,end=0x209b8)
  o.allowed.update(range(0xc34e0,0xc34e8))
  inv=Inventory();buf=C.create_string_buffer(64)
  for id in (72,99,100,101,102,104,105,106,108,109):
   for amount in (1,2,15,123):
    counts.clear();counts.update({i:amount for i in (72,99,100,101,102,104,105,106,108,109)})
    for j in range(11):inv.counts[j]=amount
    for j in range(4):inv.ammo[j]=amount*9
    o.write(0xcea20,inv.ammo[1],4);o.write(0xcea08,inv.ammo[2],4);o.write(0xcea14,inv.ammo[3],4);o.write(0xcefbb,0,1)
    o.write(0xc34e0,0,4);o.write(0xc34e4,0,4);o.write(DATA,DATA+256,4);o.write(DATA+4,id,2);o.uc.mem_write(DATA+256,b'Name\0');printed.clear()
    o.call(0x22ef0,DATA);d.tomb_inventory_label(C.byref(inv),id,buf)
    expected=[text.encode('latin1') for x,y,text in printed if x==64 and y==-56]
    assert buf.value==(expected[0] if expected else b''),(id,amount,buf.value,printed)
  o.uc.hook_del(med_hook)

  assert not d.tomb_inventory_label(C.byref(inv),99,buf) # No unlimited-ammo placeholder.
  for count in (0,1,2,15):
   inv.counts[9]=count;result=d.tomb_inventory_label(C.byref(inv),108,buf);assert bool(result)==(count>1)
  h=Hud();d.tomb_hud_pickup(C.byref(h),93);d.tomb_hud_pickup(C.byref(h),94);d.tomb_hud_pickup(C.byref(h),89);d.tomb_hud_pickup(C.byref(h),90)
  assert list(h.pickup_id)==[93,94,89] and list(h.pickup_time)==[75]*3
  for _ in range(75):d.tomb_hud_tick(C.byref(h),1000)
  assert not any(h.pickup_time)
 print('PASS: DOS health/air line primitives, HUD visibility, completion strings/positions, inventory and pickup slots (both builds)')
if __name__=='__main__':main()
