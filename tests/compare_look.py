"""Original surface look and release damping, including limits and both directions."""
from compare_ground import *
def main():
 o=Oracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'));rng=random.Random(19961020)
 for at,w in [(0xce9d0,2),(0xce9d2,2),(0xce9d6,2),(0xce9d8,2),(0xcb298,1)]:o.allowed.update(range(at,at+w))
 for suffix in ('','_debug'):
  d=C.CDLL(str(ROOT/'build'/f'step_test{suffix}.dll'))
  d.tomb_surface_look.argtypes=d.tomb_look_relax.argtypes=[C.POINTER(Movement)]
  for n in range(4000):
   m=Movement(input=512|rng.randrange(16),head_yaw=rng.randrange(-12000,12001),head_pitch=rng.randrange(-10000,10001),camera_mode=rng.choice([0,2]))
   for fn,start,end in [(d.tomb_surface_look,0x29f90,0x2a057),(d.tomb_look_relax,0x24fe0,0x25089)]:
    if start==0x24fe0:m.camera_mode=rng.choice([0,2])
    o.write(0xce92c,m.input,4);o.write(0xce9d0,m.head_yaw,2);o.write(0xce9d2,m.head_pitch,2);o.write(0xce9d6,m.torso_yaw,2);o.write(0xce9d8,m.torso_pitch,2);o.write(0xcb298,m.camera_mode,1)
    o.uc.reg_write(UC_X86_REG_ESP,STACK+2048);o.bad=[];o.uc.emu_start(start,end,count=1000);assert not o.bad,o.bad
    fn(C.byref(m))
    assert (m.head_yaw,m.head_pitch,m.torso_yaw,m.torso_pitch,m.camera_mode)==tuple(o.read(at,w) for at,w in [(0xce9d0,2),(0xce9d2,2),(0xce9d6,2),(0xce9d8,2),(0xcb298,1)])
 print('PASS: 4000 surface look and release pairs per build against DOS')
if __name__=='__main__':main()
