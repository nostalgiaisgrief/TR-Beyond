"""Original contact classifier, with ONLY static-mesh service explicitly deferred.
Real room, floor, ceiling, tilt and trig routines execute unchanged. Object height
callbacks remain unset, as in compare_level. These are structural contact tests.
"""
import ctypes as C
import hashlib
import json
import random
import time
from pathlib import Path
from compare_level import GeometryOracle,parse,bind,Level,Room,Sector,Ref,FLOOR,ROOT
from compare_step import (Actor,Contact,state,clone,I16,I32,U8,ITEM,COLL,STACK,RETURN,
    CONTACT,ACTOR,UC_HOOK_CODE,UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EBX,
    UC_X86_REG_ECX,UC_X86_REG_ESP,UC_X86_REG_EFLAGS,UC_X86_REG_EIP)

class Sample(C.Structure): _fields_=[('floor',I32),('ceiling',I32),('type',I32)]
class Terrain(C.Structure):
    _fields_=[('samples',Sample*4),('trigger_index',C.c_uint32),('object_references',C.c_uint32),
        ('quadrant',I16),('tilt_x',I16),('tilt_z',I16),('static_meshes_pending',U8)]

class ContactOracle(GeometryOracle):
    def __init__(self):
        super().__init__()
        self.uc.hook_add(UC_HOOK_CODE,self.static_mesh,begin=0x158a8,end=0x158a8)
        for addr,width in [(COLL,48),(COLL+0x5a,2),(COLL+0x5e,6),(COLL+0x65,1),(0xcc058,4)]:
            self.allowed.update(range(addr,addr+width))
        self.write(0xce960,ITEM,4)
    def external(self,uc,address,size,data):
        if address==0x151c0: return # Execute original classifier, not the old controlled query.
        return super().external(uc,address,size,data)
    def static_mesh(self,uc,address,size,data):
        self.static_calls+=1
        self.write(COLL+0x65,0,1)
        self.ret(0,pop=8)
    def contact(self,a,c,height,radius,lara_y):
        self.put(ITEM,a,ACTOR); self.write(ITEM+0x34,lara_y,4)
        self.put(COLL,c,CONTACT); self.write(COLL+0x30,radius,4)
        self.write(STACK+0x800,RETURN,4); self.write(STACK+0x804,a.room,4); self.write(STACK+0x808,height,4)
        for reg,v in [(UC_X86_REG_EAX,COLL),(UC_X86_REG_EDX,a.x),(UC_X86_REG_EBX,a.y),
                      (UC_X86_REG_ECX,a.z),(UC_X86_REG_ESP,STACK+0x800),(UC_X86_REG_EFLAGS,2)]:
            self.uc.reg_write(reg,v&0xffffffff)
        self.bad=[]; self.static_calls=0
        self.uc.emu_start(0x151c0,RETURN,count=30000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN
        assert self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x80c and not self.bad,self.bad
        assert self.static_calls==1
        samples=[dict(zip(('floor','ceiling','type'),[self.read(COLL+i*12+j*4,4) for j in range(3)])) for i in range(4)]
        trigger=self.read(COLL+0x5e,4)
        meta=dict(quadrant=self.read(COLL+0x5a,2),tilt_x=C.c_int8(self.read(COLL+0x62,1)).value,
                  tilt_z=C.c_int8(self.read(COLL+0x63,1)).value,trigger_index=(trigger-FLOOR)//2 if trigger else 0)
        return self.get(COLL,Contact,CONTACT),samples,meta

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--dll',nargs='+',type=Path,required=True); args=p.parse_args()
    dlls=[bind(path) for path in args.dll]; oracle=ContactOracle(); rng=random.Random(19961008)
    for dll in dlls:
        assert dll.tomb_test_size(9)==C.sizeof(Terrain)
        dll.tomb_terrain_contact.argtypes=[C.POINTER(Level),C.POINTER(Actor),C.POINTER(Contact),I32,I32,I32,C.POINTER(I16),C.c_int,C.POINTER(Terrain)]
    results=[]; started=time.monotonic()
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name; fixture=parse(path); oracle.install(fixture)
        err=C.create_string_buffer(256); loaded=[]
        for dll in dlls:
            ptr=dll.tomb_level_load(str(path).encode(),err,len(err)); assert ptr,err.value; loaded.append((dll,ptr))
        count=0; types={}; pending=0; slopes=set(); angles=[-32768,-24577,-24576,-8193,-8192,0,8191,8192,16384,24575,24576,32767]
        for room,r in enumerate(fixture['rooms']):
            for index,s in enumerate(r['sectors']):
                ix,iz=divmod(index,r['nz'])
                for j in range(8):
                    dx,dz=[(512,512),(1,1023),(1023,1),(100,924)][j%4]
                    a=Actor(x=r['x']+ix*1024+dx,y=s[3]*256+[0,-128,128,-512,512,-762,384,-384][j],
                            z=r['z']+iz*1024+dz,room=room)
                    c=Contact(positive_limit=[384,128,32767,0][j%4],negative_limit=[-384,-128,-32767,0][j%4],
                        ceiling_limit=[0,128,-128,0][j%4],old_x=a.x+rng.randint(-100,100),old_y=a.y+27,
                        old_z=a.z+rng.randint(-100,100),facing=angles[(index+j)%len(angles)],flags=j)
                    height=[762,400,1000,0][j%4]; radius=[100,200,1,256][j%4]; heavy=j%2
                    lara_y=a.y+([0,-512,512][j%3]); oracle.write(0xc17b0,heavy,4)
                    expected,samples,meta=oracle.contact(a,c,height,radius,lara_y)
                    for dll,ptr in loaded:
                        actual=clone(c); terrain=Terrain()
                        ok=dll.tomb_terrain_contact(ptr,C.byref(a),C.byref(actual),height,radius,lara_y,oracle.sine,heavy,C.byref(terrain))
                        label=(name,room,index,j,state(a),state(c),height,radius)
                        assert ok,('declined',label)
                        assert state(actual)==state(expected),(label,state(actual),state(expected))
                        assert [state(v) for v in terrain.samples]==samples,(label,[state(v) for v in terrain.samples],samples)
                        assert {k:getattr(terrain,k) for k in meta}==meta,(label,meta)
                        assert terrain.static_meshes_pending==1
                    pending+=bool(terrain.object_references); types[expected.type]=types.get(expected.type,0)+1
                    slopes.add((meta['tilt_x'],meta['tilt_z'])); count+=1
        for dll,ptr in loaded: dll.tomb_level_free(ptr)
        result=dict(level=name,sha256=hashlib.sha256(fixture['data']).hexdigest(),cases_per_build=count,
                    contact_types=types,tilt_pairs=len(slopes),queries_with_deferred_objects=pending)
        results.append(result); print(json.dumps(result),flush=True)
    # Controlled geometry fills exact ceiling equality and precedence gaps in
    # real-level sampling. All geometry/classifier instructions remain original.
    synthetic_types={}; synthetic_count=0
    for centre_ceiling in [0,4,8]:
        for front_ceiling in [0,4,8]:
            for y in [762,1786,2560]:
                sectors=[(0,0,255,10,255,0) for _ in range(25)]
                sectors[12]=(0,0,255,10,255,centre_ceiling)
                sectors[13]=(0,0,255,10,255,front_ceiling)
                room=dict(x=0,z=0,bottom=2560,top=0,nz=5,nx=5,sectors=sectors,alternate=-1,flags=0)
                sf=dict(fixture,rooms=[room]); oracle.install(sf); oracle.write(0xc17b0,0,4)
                sector_array=(Sector*25)(*(Sector(*v) for v in sectors))
                rooms=(Room*1)(Room(0,0,2560,0,5,5,sector_array,-1,0))
                level=Level(); level.rooms=rooms; level.room_count=1
                a=Actor(x=2560,y=y,z=3000,room=0)
                c=Contact(positive_limit=10000,negative_limit=-10000,ceiling_limit=0,
                    old_x=2550,old_y=y-5,old_z=2980,facing=0,flags=7)
                expected,samples,meta=oracle.contact(a,c,762,100,y)
                for dll in dlls:
                    actual=clone(c); t=Terrain()
                    assert dll.tomb_terrain_contact(C.byref(level),C.byref(a),C.byref(actual),762,100,y,oracle.sine,0,C.byref(t))
                    assert state(actual)==state(expected),(centre_ceiling,front_ceiling,y,state(actual),state(expected))
                    assert [state(s) for s in t.samples]==samples
                    assert {k:getattr(t,k) for k in meta}==meta
                    assert t.static_meshes_pending==1 and not t.object_references
                synthetic_types[expected.type]=synthetic_types.get(expected.type,0)+1; synthetic_count+=1
    assert 8 in synthetic_types and 16 in synthetic_types,synthetic_types
    all_types=set(synthetic_types)
    for result in results: all_types.update(result['contact_types'])
    assert all_types=={0,1,2,4,8,16,32},all_types
    report=dict(levels=results,synthetic_cases_per_build=synthetic_count,synthetic_contact_types=synthetic_types,
        seconds=round(time.monotonic()-started,2),seed=19961008,
        limits='Structural contact classifier only. Static mesh routine replaced by explicit no-contact service; object height callbacks unset. No vault/slide or full-frame integration.',
        builds=[dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in args.dll],
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [ROOT/'src/terrain.c',ROOT/'src/geometry.c',ROOT/'src/level.h',Path(__file__)]})
    (ROOT/'analysis/c-terrain-validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: original structural contact classifier matched both builds')

if __name__=='__main__': main()
