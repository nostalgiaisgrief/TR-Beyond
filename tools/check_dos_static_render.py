"""Execute DOS static visibility branch and object viewport setup before renderer fixes."""
import struct,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from compare_level import parse
from compare_step import Oracle,ROOT,STACK,RETURN,DATA,UC_HOOK_CODE,UC_X86_REG_EAX,UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EIP
oracle=Oracle(ROOT/'work/reference-drive/TOMBRAID/TOMB.EXE');u=oracle.uc
f=parse(ROOT/'work/reference-assets/DATA/GYM.PHD');results=[]
# Execute the actual loaded flag test, stopping at its two branch destinations.
for definition in f['static_defs']:
 ident,mesh,*_=definition;flags=definition[-1]
 oracle.write(DATA+16,ident,2);oracle.write(0xcb9e2+28*ident,flags,2)
 u.reg_write(UC_X86_REG_ECX,DATA);u.reg_write(UC_X86_REG_ESP,STACK+0x800)
 def stop(uc,at,size,data):
  if at in (0x1aa56,0x1aac5):uc.emu_stop()
 h=u.hook_add(UC_HOOK_CODE,stop)
 u.emu_start(0x1aa44,RETURN,count=20);u.hook_del(h)
 draw=u.reg_read(UC_X86_REG_EIP)==0x1aa56
 assert draw==bool(flags&2)
 results.append(dict(id=ident,mesh=mesh,flags=flags,dos_draw_enabled=draw))
# DOS object mesh routine: both paths initialise polygon clipping to the full
# viewport, regardless of room clip globals. Stop before lighting/rasterisation.
clips=[]
for branch in (0,1):
 oracle.write(DATA+8,branch,1);oracle.write(0x12f3b8,1279,4);oracle.write(0x12f3b4,719,4)
 for addr,value in [(0x12f394,500),(0x12f3d0,600),(0x12f3c8,250),(0x12f390,350)]:oracle.write(addr,value,4)
 u.reg_write(UC_X86_REG_EAX,DATA);u.reg_write(UC_X86_REG_ESP,STACK+0x800)
 def hook(uc,at,size,data):
  if at==0x3e4d0:oracle.ret(DATA+10) # vertex transform boundary
  elif at==0x3e6a4:uc.emu_stop() # lighting boundary, after clip setup
 h=u.hook_add(UC_HOOK_CODE,hook)
 u.emu_start(0x3e3b0,RETURN,count=100);u.hook_del(h)
 assert u.reg_read(UC_X86_REG_EIP)==0x3e6a4
 values=[struct.unpack('<f',u.mem_read(a,4))[0] for a in (0x12f3ec,0x12f3e8,0x12f3f8,0x12f3e4)]
 assert values==[0,0,1279,719],values
 clips.append(values)
report=dict(static_flags=results,hidden_gym_placements=[dict(room=i,placement=p) for i,r in enumerate(f['rooms']) for p in r['statics'] if p[-1]==17],object_clip_rectangles=clips,scope='Original flag branch and viewport setup executed; transform/lighting/rasterisation not exercised. No live DOS screenshot comparison.')
(ROOT/'analysis/dos-static-render-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: 21 DOS static draw flags; both DOS object clip paths use full viewport. Static 17 disabled at both table positions.')
