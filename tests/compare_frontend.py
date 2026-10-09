"""Original executable checks for option descriptors, title motion, passport
meshes/animation and death-menu timing. Does not claim full screen equality."""
from compare_ring import *

def main():
 o=RingOracle();o.uc.hook_add(UC_HOOK_CODE,lambda *args:o.ret(),begin=0x3dcf4,end=0x3dcf4)
 for suffix in ('','_debug'):
  d=C.CDLL(str(ROOT/'build'/f'step_test{suffix}.dll'))
  d.tomb_ring_init_options.argtypes=[C.POINTER(Ring),C.c_int];d.tomb_ring_motion_tick.argtypes=[C.POINTER(Ring)]
  d.tomb_ring_animate.argtypes=[C.POINTER(RingItem)];d.tomb_death_menu_due.argtypes=[C.c_int,C.c_uint]
  for title in (0,1):
   r=Ring();assert d.tomb_ring_init_options(C.byref(r),title)
   for i,addr in zip(r.items[:r.count],(0xc322c,0xc32ec,0xc326c,0xc32ac,0xc336c)):assert bytes(i)==bytes(o.uc.mem_read(addr,56))
   o.install(r);o.write(0xc3814,title,4);o.call(0x240bc,RO,1,LI,r.count,(0,MO));o.call(0x242c0,RO,24);o.compare(r)
   for tick in range(32):o.call(0x24304);d.tomb_ring_motion_tick(C.byref(r));o.compare(r)
  for frame in range(30):
   for goal in (0,14,19,24,29):
    r=Ring();d.tomb_ring_init_options(C.byref(r),0);i=r.items[0];i.object=71;i.frame=frame;i.goal=goal;i.direction=1 if goal>frame else -1
    o.install(r);expected=o.call(0x227cc,IT);actual=d.tomb_ring_animate(C.byref(i));assert expected==actual;o.compare(r)
  for ticks in (0,1,59,60,61,149,150,299,300,301,500):
   for input in (0,1,64,256,4096):
    o.write(0xce97a,ticks,2);o.write(0xce92c,input,4);o.write(0xc2034,1,4)
    def stop(uc,at,size,data):
     if at in (0x16dea,0x16e2b):uc.emu_stop()
    hook=o.uc.hook_add(UC_HOOK_CODE,stop);o.uc.emu_start(0x16dc4,RETURN,count=40);o.uc.hook_del(hook)
    assert bool(d.tomb_death_menu_due(ticks,input))==(o.uc.reg_read(UC_X86_REG_EIP)==0x16dea)
 print('PASS: DOS options/title initialization and 64 motion ticks, 150 passport animation/mask cases, 55 death-timing boundaries per build')
if __name__=='__main__':main()
