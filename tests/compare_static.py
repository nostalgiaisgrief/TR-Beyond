"""Execute original static and combined terrain collision without static stubs.
Only dynamic object height callbacks remain unset. No rendering is involved.
"""
import ctypes as C
import hashlib
import json
import random
import struct
import time
from pathlib import Path
from compare_level import ROOT,Level,Room,Sector,Placement,StaticDef,parse,bind,ROOMS
from compare_terrain import ContactOracle,Terrain
from compare_step import (Actor,Contact,clone,state,I16,I32,U8,ITEM,COLL,STACK,RETURN,CONTACT,
    UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESP,
    UC_X86_REG_EFLAGS,UC_X86_REG_EIP)

class StaticContact(C.Structure):
    _fields_=[('rooms',I16*9),('room_count',C.c_uint16),('hit',U8)]

class StaticOracle(ContactOracle):
    def __init__(self):
        super().__init__()
        self.allowed.update(range(0xcbf58,0xcbf58+18)); self.allowed.update(range(0xcc05c,0xcc05c+4))
    def static_mesh(self,uc,address,size,data):
        self.static_calls+=1 # Observe only: original code executes unchanged.
    def install(self,f):
        super().install(f); at=0x600000
        for i,r in enumerate(f['rooms']):
            placements=r.get('statics',[])
            self.write(ROOMS+i*68+0x10,at,4); self.write(ROOMS+i*68+0x30,len(placements),2)
            data=b''.join(struct.pack('<iiiHHH',*p) for p in placements)
            if data: self.uc.mem_write(at,data)
            at+=len(data)
        assert at<0x700000
        for d in f.get('static_defs',[]):
            ident,mesh,*rest=d; assert ident<50
            self.uc.mem_write(0xcb9e0+ident*28,struct.pack('<HH12h',mesh,rest[-1],*rest[:-1]))
    def static(self,a,c,height,radius,quadrant):
        self.put(COLL,c,CONTACT); self.write(COLL+0x30,radius,4); self.write(COLL+0x5a,quadrant,2)
        self.write(STACK+0x800,RETURN,4); self.write(STACK+0x804,a.room,4); self.write(STACK+0x808,height,4)
        for reg,v in [(UC_X86_REG_EAX,COLL),(UC_X86_REG_EDX,a.x),(UC_X86_REG_EBX,a.y),
                      (UC_X86_REG_ECX,a.z),(UC_X86_REG_ESP,STACK+0x800),(UC_X86_REG_EFLAGS,2)]:
            self.uc.reg_write(reg,v&0xffffffff)
        self.bad=[]; self.static_calls=0; self.uc.emu_start(0x158a8,RETURN,count=30000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN and self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x80c
        assert not self.bad,self.bad
        assert self.uc.reg_read(UC_X86_REG_EAX)==self.read(COLL+0x65,1)
        return self.get(COLL,Contact,CONTACT)
    def result(self):
        n=self.read(0xcc05c,4); assert 1<=n<=9
        return [self.read(0xcbf58+2*i,2) for i in range(n)],self.read(COLL+0x65,1)

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--dll',nargs='+',type=Path,required=True); args=p.parse_args()
    dlls=[bind(path) for path in args.dll]; oracle=StaticOracle(); started=time.monotonic(); results=[]
    for dll in dlls:
        assert dll.tomb_test_size(12)==C.sizeof(StaticContact)
        dll.tomb_static_contact.argtypes=[C.POINTER(Level),C.POINTER(Actor),C.POINTER(Contact),I32,I32,I16,C.POINTER(StaticContact)]
        dll.tomb_world_contact.argtypes=[C.POINTER(Level),C.POINTER(Actor),C.POINTER(Contact),I32,I32,I32,C.POINTER(I16),C.c_int,C.POINTER(Terrain),C.POINTER(StaticContact)]
    counts={}; hit_types={}; world_hits=0; multiroom=0
    def check(loaded,a,c,height,radius,quadrant,world=False):
        nonlocal world_hits,multiroom
        oracle.write(0xc17b0,0,4)
        if world: expected,samples,meta=oracle.contact(a,c,height,radius,a.y)
        else: expected=oracle.static(a,c,height,radius,quadrant)
        rooms,hit=oracle.result(); multiroom+=len(rooms)>1
        if world: world_hits+=hit
        elif hit: hit_types[expected.type]=hit_types.get(expected.type,0)+1
        for dll,ptr in loaded:
            actual=clone(c); sc=StaticContact(); t=Terrain()
            if world:
                ok=dll.tomb_world_contact(ptr,C.byref(a),C.byref(actual),height,radius,a.y,oracle.sine,0,C.byref(t),C.byref(sc))
            else: ok=dll.tomb_static_contact(ptr,C.byref(a),C.byref(actual),height,radius,quadrant,C.byref(sc))
            label=(state(a),state(c),height,radius,quadrant,world)
            assert ok,('declined',label)
            assert state(actual)==state(expected),(label,state(actual),state(expected))
            assert sc.hit==hit and list(sc.rooms[:sc.room_count])==rooms,(label,list(sc.rooms[:sc.room_count]),rooms,sc.hit,hit)
            if world:
                assert [state(s) for s in t.samples]==samples,(label,[state(s) for s in t.samples],samples)
                assert {k:getattr(t,k) for k in meta}==meta
                assert t.static_meshes_pending==0
        key='combined' if world else 'static'; counts[key]=counts.get(key,0)+1
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name; f=parse(path); oracle.install(f); loaded=[]
        for dll in dlls:
            err=C.create_string_buffer(256); ptr=dll.tomb_level_load(str(path).encode(),err,len(err)); assert ptr,err.value
            loaded.append((dll,ptr))
        before=dict(counts); defs={d[0]:d for d in f['static_defs']}; placements=0
        for room,r in enumerate(f['rooms']):
            for px,py,pz,rot,intensity,ident in r['statics']:
                placements+=1; d=defs[ident]; bx0,bx1,by0,by1,bz0,bz1=d[8:14]
                # Transform bounds only to position probes; expected responses
                # always come from original instructions.
                corners=[(x,z) for x in (bx0,bx1) for z in (bz0,bz1)]
                if rot==16384: corners=[(z,-x) for x,z in corners]
                elif rot==32768: corners=[(-x,-z) for x,z in corners]
                elif rot==49152: corners=[(-z,x) for x,z in corners]
                lo_x,hi_x=min(x for x,z in corners)+px,max(x for x,z in corners)+px
                lo_z,hi_z=min(z for x,z in corners)+pz,max(z for x,z in corners)+pz
                xs=[lo_x-101,lo_x-100,lo_x-99,(lo_x+hi_x)//2,hi_x+99,hi_x+100,hi_x+101]
                zs=[lo_z-101,lo_z-100,lo_z-99,(lo_z+hi_z)//2,hi_z+99,hi_z+100,hi_z+101]
                for i,x in enumerate(xs):
                    for j,z in enumerate(zs):
                        for q in range(4):
                            a=Actor(x=x,y=py+(by0+by1)//2+381,z=z,room=room)
                            c=Contact(positive_limit=384,negative_limit=-384,old_x=x-11,old_y=a.y-13,old_z=z+17,
                                      facing=C.c_int16(q*16384).value,flags=7,type=8,shift_x=19,shift_y=23,shift_z=29)
                            check(loaded,a,c,762,100,q)
                            if i==3 and j==3: check(loaded,a,c,762,100,q,True)
                # Exact vertical touches and their immediate inside/outside neighbours.
                for y in [py+by0-1,py+by0,py+by0+1,py+by1+761,py+by1+762,py+by1+763]:
                    a=Actor(x=(lo_x+hi_x)//2,y=y,z=(lo_z+hi_z)//2,room=room)
                    c=Contact(old_x=a.x-11,old_y=y,old_z=a.z-11)
                    check(loaded,a,c,762,100,0)
        # Combined classifier probes distributed over real sectors, including
        # room boundaries where static collection starts in the last sampled room.
        rng=random.Random(19961008)
        for _ in range(1000):
            room=rng.randrange(len(f['rooms'])); r=f['rooms'][room]; index=rng.randrange(len(r['sectors']))
            ix,iz=divmod(index,r['nz']); a=Actor(x=r['x']+ix*1024+rng.randrange(1024),
                y=r['sectors'][index][3]*256,z=r['z']+iz*1024+rng.randrange(1024),room=room)
            c=Contact(positive_limit=384,negative_limit=-384,old_x=a.x-10,old_y=a.y,old_z=a.z-10,
                      facing=rng.randint(-32768,32767),flags=7)
            check(loaded,a,c,762,100,0,True)
        for dll,ptr in loaded: dll.tomb_level_free(ptr)
        result=dict(level=name,sha256=hashlib.sha256(f['data']).hexdigest(),placements=placements,
                    cases_per_build={k:v-before.get(k,0) for k,v in counts.items()})
        results.append(result); print(json.dumps(result),flush=True)
    # Synthetic asymmetrical box: all exact rotations and a non-cardinal angle,
    # disabled collision flag, tie breaking and first-placement order.
    sectors=(Sector*25)(*(Sector(0,0,255,10,255,0) for _ in range(25)))
    for rot in [0,16384,32768,49152,8192]:
        for flags in [0,1]:
            definitions=[(0,0,*([0]*6),-120,230,-500,0,-80,310,flags),
                         (1,0,*([0]*6),-300,300,-500,0,-300,300,0)]
            placements=[(2560,2560,2560,rot,0,0),(2560,2560,2560,0,0,1)]
            for reverse in [False,True]:
                ps=placements[::-1] if reverse else placements
                room=dict(x=0,z=0,nz=5,nx=5,sectors=[(0,0,255,10,255,0)]*25,statics=ps)
                oracle.install(dict(f,rooms=[room],static_defs=definitions))
                pa=(Placement*2)(*(Placement(*v) for v in ps)); da=(StaticDef*2)(*(StaticDef(d[0],d[1],d[-1],(I16*6)(*d[8:14])) for d in definitions))
                ra=(Room*1)(Room(0,0,2560,0,5,5,sectors,-1,0,pa,2)); l=Level()
                l.rooms=ra; l.room_count=1; l.static_defs=da; l.static_def_count=2
                for dx,dz in [(0,0),(1,-1),(-300,0),(300,0),(0,-300),(0,300),(-400,-400),(400,400)]:
                    for q in range(4):
                        a=Actor(x=2560+dx,y=2560,z=2560+dz,room=0)
                        c=Contact(old_x=a.x-20,old_y=a.y,old_z=a.z+20,type=8,shift_y=5)
                        check([(dll,C.pointer(l)) for dll in dlls],a,c,762,100,q)
    assert all(k in hit_types for k in [1,2,4]) and world_hits>0 and multiroom>0
    report=dict(levels=results,totals_per_build=counts,hit_types=hit_types,combined_hits=world_hits,
        multiroom_queries=multiroom,seconds=round(time.monotonic()-started,2),
        limits='Original static and combined classifier executed without static substitutes. Dynamic object height callbacks unset; full gameplay integration remains pending.',
        builds=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in args.dll],
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [ROOT/'src/static.c',ROOT/'src/terrain.c',ROOT/'src/level.c',ROOT/'src/level.h',Path(__file__)]})
    (ROOT/'analysis/c-static-validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: static contacts and combined classifier matched original code')

if __name__=='__main__': main()
