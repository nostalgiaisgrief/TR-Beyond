"""Print placed controllers and actual trigger chains in the two Peru levels."""
import sys, struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from compare_level import parse, ROOT
for name in ('LEVEL3A','LEVEL3B'):
    f=parse(ROOT/'work/reference-assets/DATA'/f'{name}.PHD')
    print(name,'alternates',[(i,r['alternate']) for i,r in enumerate(f['rooms']) if r['alternate']>=0])
    for i,p in enumerate(f['items']):
        if p[0] in (24,27,37,38,52,53,74,75,76,110,118,143):print('item',i,p)
    fd=struct.unpack('<'+'H'*f['sections']['floor']['count'],f['sections']['floor']['bytes']);seen=set()
    for room,r in enumerate(f['rooms']):
        for sector,s in enumerate(r['sectors']):
            at=s[0]
            while at and at<len(fd):
                h=fd[at];at+=1;kind=h&31
                if kind in (1,2,3):at+=1
                elif kind==4:
                    start=at-1;flags=fd[at];at+=1;typ=(h>>8)&63;gate=None
                    if typ in (2,3,4):gate=fd[at]&1023;at+=1
                    actions=[]
                    while True:
                        word=fd[at];at+=1;act=(word&0x3fff)>>10;v=word&1023
                        actions.append((act,v,f['items'][v][0] if act==0 else None))
                        if act==1:word=fd[at];at+=1
                        if word&0x8000:break
                    if start not in seen:
                        print('trigger',start,'room',room,'sector',sector,'type',typ,'flags',hex(flags),'gate',gate,'actions',actions);seen.add(start)
                if h&0x8000:break
