"""Compare reconstructed dialog baselines, alignments and panel rectangles with
original DOS option/requester code and Text_Draw. Final rasterization is modern.
"""
from compare_ring import *
class Entry(C.Structure):
 _fields_=[(n,C.c_int) for n in ('x','y','flags','panel_width','panel_height')]

def oracle(kind,selected):
 o=RingOracle();o.allowed.update(range(0xc0000,0x140000))
 for addr,val,size in [(0xc2054,640,2),(0xc2056,480,2),(0x12f3ac,640,4),(0xcb24c,1,4),(0xc3f90,0,4)]:o.write(addr,val,size)
 def sprintf(u,at,size,user):
  sp=u.reg_read(UC_X86_REG_ESP);dst=o.read(sp+4,4);fmt=bytes(u.mem_read(o.read(sp+8,4),64)).split(b'\0')[0]
  result=fmt%o.read(sp+12,4);u.mem_write(dst,result+b'\0');o.ret(len(result))
 o.uc.hook_add(UC_HOOK_CODE,sprintf,begin=0x47dc5,end=0x47dc5)
 if kind==95:
  o.write(0xc3b94,2-selected,4);o.call(0x30b7c)
  pointers=[o.read(a,4) for a in (0xc3c1c,0xc3c20,0xc3c18,0xc3c14,0xc3c10)]
 elif kind==96:
  o.call(0x30e30)
  if selected:o.write(0xc37e8,2,4);o.call(0x30e30)
  pointers=[o.read(a,4) for a in (0xc3c2c,0xc3c30,0xc3c24,0xc3c28)]
 elif kind==97:
  o.call(0x31414);pointers=[o.read(a,4) for a in (0xc3c38,0xc3c34)]+[o.read(a,4) for a in range(0xc3b98,0xc3c00,4)]
 else:
  o.write(0xc34fc,16,2);o.write(0xc34fe,selected,2);o.call(0x32054,0xc34fc)
  pointers=[o.read(a,4) for a in (0xc351e,0xc351a)]+[o.read(a,4) for a in range(0xc352a,0xc3552,4)]
 return o,pointers

def main():
 total=0
 for suffix in ('','_debug'):
  d=C.CDLL(str(ROOT/'build'/f'step_test{suffix}.dll'));d.tomb_dialog_layout.argtypes=[C.c_int,C.c_int,C.c_int,C.POINTER(Entry)];d.tomb_dialog_bounds.argtypes=[C.POINTER(Entry),C.c_int,C.POINTER(C.c_int)]
  for kind,choices in [(95,range(3)),(96,range(2)),(97,range(1)),(71,range(10))]:
   for selected in choices:
    o,pointers=oracle(kind,selected);entries=(Entry*32)();count=d.tomb_dialog_layout(kind,selected,kind==71,entries);assert count==len(pointers)
    draws=[]
    def draw(u,at,size,user):
     sp=u.reg_read(UC_X86_REG_ESP)
     if at==0x1f938:draws.append([C.c_int32(u.reg_read(r)).value for r in (UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_ECX)]+[o.read(sp+4,4)])
     o.ret(pop=16)
    for at in (0x1f6e0,0x1fa5c,0x1f938):o.uc.hook_add(UC_HOOK_CODE,draw,begin=at,end=at)
    for n,(p,e) in enumerate(zip(pointers,entries)):
     assert (e.x,e.y,e.flags)==(o.read(p+10,2),o.read(p+12,2),o.read(p,2)&0x1b0),(kind,n,'baseline',tuple(getattr(e,k) for k,_ in Entry._fields_))
     assert e.panel_width==(o.read(p+36,2) if o.read(p,2)&0x200 else 0),(kind,n,'width')
     if e.panel_width:assert e.panel_height==(o.read(p+38,2) or 16),(kind,n,'height')
     if e.panel_width:
      w=o.call(0x3985c,p);draws.clear();o.call(0x399bc,p);b=(C.c_int*4)();d.tomb_dialog_bounds(C.byref(e),w,b);assert list(b)==draws[-1],(kind,n,list(b),draws)
     total+=1
 print(f'PASS: {total} DOS dialog entries across detail, sound, controls and ten requester selections; panel rectangles match Text_Draw')
if __name__=='__main__':main()
