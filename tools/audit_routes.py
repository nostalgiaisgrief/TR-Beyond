"""Read-only coverage audit of every floor-data chain used by Caves/City.
This is a route-content audit, not an uninterrupted playthrough comparison.
Bridge references 68..70 use static height callbacks, not moving controllers.
"""
import sys,struct,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from compare_level import parse,ROOT
from collections import Counter
report=[]
for name in ('LEVEL1.PHD','LEVEL2.PHD'):
 f=parse(ROOT/'work/reference-assets/DATA'/name)
 section=f['sections']['floor'];offset,count=section[:2] if not isinstance(section,dict) else (section['offset'],section['count'])
 floor=struct.unpack_from('<'+'H'*count,f['data'],offset)
 seen=set();triggers=[]
 for ri,r in enumerate(f['rooms']):
  for si,sector in enumerate(r['sectors']):
   at=sector[0]
   if not at or at in seen:continue
   seen.add(at)
   while at<len(floor):
    header=floor[at];at+=1;kind=header&31
    if kind in (1,2,3):at+=1
    elif kind==4:
     typ=(header>>8)&63;flags=floor[at];at+=1;gate=None
     if typ in (2,3,4):gate=floor[at]&1023;at+=1
     actions=[]
     while at<len(floor):
      w=floor[at];at+=1;action=(w&0x3fff)>>10;value=w&1023
      actions.append(dict(action=action,value=value,object=f['items'][value][0] if action in (0,6) else None))
      if action==1:w=floor[at];at+=1
      if w&0x8000:break
     triggers.append(dict(room=ri,sector=si,type=typ,gate=gate,flags=flags,actions=actions))
    elif kind!=5:raise AssertionError((name,at,kind))
    if header&0x8000:break
 actions=Counter(a['action'] for t in triggers for a in t['actions']);unsupported=[t for t in triggers if t['type'] not in (0,1,2,3,5,6) or any(a['action'] not in (0,1,6,7,8,10) or (a['action']==0 and a['object'] not in (7,8,9,35,36,40,57,58,59,60,61,62,63,64,65,66,68,69,70)) for a in t['actions'])]
 objects=Counter(i[0] for i in f['items']);summary=dict(level=name,rooms=len(f['rooms']),items=len(f['items']),objects=dict(objects),unique_floor_chains=len(seen),trigger_lists=len(triggers),action_counts=dict(actions),unimplemented_action_lists=unsupported,triggers=triggers)
 report.append(summary);print(name,'triggers',len(triggers),'actions',actions,'unimplemented',len(unsupported))
(ROOT/'analysis/route-content-audit.json').write_text(json.dumps(dict(scope=__doc__,levels=report),indent=2)+'\n')
