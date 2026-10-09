"""Original object callbacks and dispatch through floor data. Runtime states in
fixtures are controlled inputs, not claimed original item initialization.
"""
import ctypes as C
import hashlib
import json
import random
import time
from pathlib import Path
from compare_level import ROOT,Item,Level,Room,Sector,Heights,Ref,bind,parse,ITEMS,FLOOR,U16
from compare_static import StaticOracle,StaticContact
from compare_terrain import Terrain
from compare_step import (Actor,Contact,I16,I32,SZ,state,clone,COLL,STACK,RETURN,
    UC_X86_REG_EAX,UC_X86_REG_EDX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESP,
    UC_X86_REG_EFLAGS,UC_X86_REG_EIP)

CALLBACKS={35:(0x3a848,0x3a878),41:(0x2fe88,0x2febc),65:(0x3a4c0,0x3a4f8),
           66:(0x3a4c0,0x3a4f8),68:(0x2ff18,0x2ff2c),69:(0x2ff8c,0x2ffb0),70:(0x2ffd8,0x2fffc)}

class ItemOracle(StaticOracle):
    def __init__(self):
        super().__init__(); self.allowed.update(range(RETURN+0x104,RETURN+0x106))
    def put_item(self,a,index=0):
        at=ITEMS+68*index
        self.uc.mem_write(at,bytes(68))
        for off,name,width in [(12,'object',2),(14,'state',2),(24,'room',2),(48,'x',4),
                               (52,'y',4),(56,'z',4),(62,'yaw',2)]: self.write(at+off,getattr(a,name),width)
    def setup_items(self,items):
        for ident in range(191):
            funcs=CALLBACKS.get(ident,(0,0))
            for j,fn in enumerate(funcs): self.write(0xcc074+ident*50+j*4,fn,4)
        for i,a in enumerate(items): self.put_item(a,i)
    def callback(self,a,x,y,z,ceiling,initial):
        self.put_item(a); self.write(RETURN+0x104,initial,2)
        self.write(STACK+0x800,RETURN,4); self.write(STACK+0x804,RETURN+0x104,4)
        for reg,v in [(UC_X86_REG_EAX,ITEMS),(UC_X86_REG_EDX,x),(UC_X86_REG_EBX,y),
                      (UC_X86_REG_ECX,z),(UC_X86_REG_ESP,STACK+0x800),(UC_X86_REG_EFLAGS,2)]:
            self.uc.reg_write(reg,v&0xffffffff)
        self.bad=[]; self.uc.emu_start(CALLBACKS[a.object][ceiling],RETURN,count=1000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN and self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x808
        assert not self.bad,self.bad
        return self.read(RETURN+0x104,2)

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--dll',nargs='+',type=Path,required=True); args=p.parse_args()
    dlls=[bind(path) for path in args.dll]; oracle=ItemOracle(); rng=random.Random(19961105); started=time.monotonic()
    for dll in dlls:
        dll.tomb_item_height.argtypes=[C.POINTER(Item),I32,I32,I32,C.c_int,C.POINTER(I16)]
        dll.tomb_item_heights.argtypes=[C.POINTER(Level),Ref,I32,I32,I32,C.c_int,C.POINTER(Item),SZ,C.POINTER(Heights)]
        dll.tomb_active_contact.argtypes=[C.POINTER(Level),C.POINTER(Actor),C.POINTER(Contact),I32,I32,I32,C.POINTER(I16),C.c_int,C.POINTER(Item),SZ,C.POINTER(Terrain),C.POINTER(StaticContact)]
    direct=0; changes={}; world_count=0; height_count=0; levels=[]
    def check_callback(a,x,y,z,initial):
        nonlocal direct
        for ceiling in (0,1):
            expected=oracle.callback(a,x,y,z,ceiling,initial)
            for dll in dlls:
                actual=I16(initial); assert dll.tomb_item_height(C.byref(a),x,y,z,ceiling,C.byref(actual))
                assert actual.value==expected,(state(a),x,y,z,ceiling,initial,actual.value,expected)
            if expected!=initial: changes[a.object]=changes.get(a.object,0)+1
            direct+=1
    for ident in CALLBACKS:
        for st in [-1,0,1,2]:
            for yaw in [0,16384,-32768,-16384,8192]:
                a=Item(x=-1024,y=1024,z=2048,object=ident,yaw=yaw,state=st,state_known=1)
                for dx in [-2049,-2048,-1024,-1,0,1023,2048]:
                    for dz in [-2049,-2048,-1024,-1,0,1023,2048]:
                        for dy in [-513,-512,-1,0,1,255,256,511,512]:
                            check_callback(a,a.x+dx,a.y+dy,a.z+dz,[-32768,0,32767][(dx+dz+dy)%3])
    for _ in range(4000):
        a=Item(x=rng.randint(-2147483648,2147483647),y=rng.randint(-2147483648,2147483647),
            z=rng.randint(-2147483648,2147483647),object=rng.choice(list(CALLBACKS)),yaw=rng.randint(-32768,32767),
            state=rng.randint(-2,3),state_known=1)
        check_callback(a,rng.randint(-2147483648,2147483647),rng.randint(-2147483648,2147483647),
                       rng.randint(-2147483648,2147483647),rng.randint(-32768,32767))
    assert set(changes)==set(CALLBACKS),changes
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name; f=parse(path); oracle.install(f); loaded=[]
        for dll in dlls:
            err=C.create_string_buffer(256); ptr=dll.tomb_level_load(str(path).encode(),err,len(err)); assert ptr,err.value
            loaded.append((dll,ptr))
        runtime=(Item*len(f['items']))(*(clone(loaded[0][1].contents.items[i]) for i in range(len(f['items']))))
        for i,a in enumerate(runtime): a.state=i%3; a.state_known=1
        oracle.setup_items(runtime); before_h=height_count; before_w=world_count; changed=0
        for room,r in enumerate(f['rooms']):
            for index,s in enumerate(r['sectors']):
                ix,iz=divmod(index,r['nz']); x=r['x']+ix*1024+512; z=r['z']+iz*1024+512
                for dy in [-513,0,1]:
                    y=s[3]*256+dy; ref,address=oracle.find(x,y,z,room); oracle.write(0xc17b0,0,4)
                    floor=C.c_int16(oracle.call(0x1767c,address,x,y,z)).value
                    kind=oracle.read(0xc17b4,4); trigger=oracle.read(0xcb39c,4)
                    trigger=(trigger-FLOOR)//2 if trigger else 0
                    ceiling=C.c_int16(oracle.call(0x180e8,address,x,y,z)).value
                    for dll,ptr in loaded:
                        h=Heights(); assert dll.tomb_item_heights(ptr,ref,x,y,z,0,runtime,len(runtime),C.byref(h))
                        assert (h.floor,h.ceiling,h.floor_type,h.trigger_index)==(floor,ceiling,kind,trigger),(name,room,index,dy,state(h),(floor,ceiling,kind,trigger))
                        structural=Heights(); assert dll.tomb_static_heights(ptr,ref,x,z,0,C.byref(structural))
                    changed+=(h.floor,h.ceiling)!=(structural.floor,structural.ceiling); height_count+=1
                if index%3==0:
                    a=Actor(x=x,y=s[3]*256,z=z,room=room)
                    c=Contact(positive_limit=384,negative_limit=-384,old_x=x-10,old_y=a.y,old_z=z+10,
                              facing=C.c_int16(index*910).value,flags=7)
                    expected,samples,meta=oracle.contact(a,c,762,100,a.y); rooms,hit=oracle.result()
                    for dll,ptr in loaded:
                        actual=clone(c); t=Terrain(); sc=StaticContact()
                        assert dll.tomb_active_contact(ptr,C.byref(a),C.byref(actual),762,100,a.y,oracle.sine,0,runtime,len(runtime),C.byref(t),C.byref(sc))
                        assert state(actual)==state(expected),(name,room,index,state(actual),state(expected))
                        assert [state(s) for s in t.samples]==samples
                        assert {k:getattr(t,k) for k in meta}==meta
                        assert sc.hit==hit and list(sc.rooms[:sc.room_count])==rooms and not t.static_meshes_pending
                    world_count+=1
        for dll,ptr in loaded: dll.tomb_level_free(ptr)
        result=dict(level=name,items=len(runtime),height_queries=height_count-before_h,combined_queries=world_count-before_w,
                    queries_changed_by_callbacks=changed,sha256=hashlib.sha256(f['data']).hexdigest())
        levels.append(result); print(json.dumps(result),flush=True)
    # Trigger dispatch order with slopes preceding multiple object actions.
    dispatched=0; fd=(U16*8)(0,2,0x0102,0x8004,0,0,1,0x8002)
    sector_values=[(1,0,255,10,255,-10)]*25
    sectors=(Sector*25)(*(Sector(*v) for v in sector_values))
    ra=(Room*1)(Room(0,0,2560,-2560,5,5,sectors,-1,0)); l=Level()
    l.rooms=ra; l.room_count=1; l.floor_data=fd; l.floor_count=len(fd)
    sf=dict(f,rooms=[dict(x=0,z=0,nz=5,nx=5,sectors=sector_values,statics=[])],static_defs=[],
            sections=dict(f['sections'],floor=dict(bytes=bytes(fd))))
    ids=list(CALLBACKS)
    for start in range(len(ids)):
        for st in [0,1,2]:
            for reverse in [False,True]:
                chosen=[ids[(start+j)%len(ids)] for j in range(3)]
                if reverse: chosen.reverse()
                runtime=(Item*3)(*(Item(x=2048,y=j*128,z=4096 if ident==41 else 2048,
                    object=ident,state=st,state_known=1) for j,ident in enumerate(chosen)))
                oracle.install(sf); oracle.setup_items(runtime); oracle.write(0xc17b0,0,4)
                for y in [-1024,-1,0,257,1024]:
                    ref,address=oracle.find(2560,y,2560,0)
                    floor=C.c_int16(oracle.call(0x1767c,address,2560,y,2560)).value
                    kind=oracle.read(0xc17b4,4); trigger=(oracle.read(0xcb39c,4)-FLOOR)//2
                    ceiling=C.c_int16(oracle.call(0x180e8,address,2560,y,2560)).value
                    for dll in dlls:
                        h=Heights(); assert dll.tomb_item_heights(C.byref(l),ref,2560,y,2560,0,runtime,3,C.byref(h))
                        assert (h.floor,h.ceiling,h.floor_type,h.trigger_index)==(floor,ceiling,kind,trigger),(chosen,st,y,state(h),(floor,ceiling,kind,trigger))
                        assert h.object_references==0
                    dispatched+=1
    # Unsupported types and missing runtime state must stay visibly unresolved.
    for dll in dlls:
        for a in [Item(object=35),Item(object=0,state_known=1)]:
            h=I16(123); assert not dll.tomb_item_height(C.byref(a),0,0,0,0,C.byref(h)) and h.value==123
        runtime=(Item*3)(Item(object=35),Item(object=0,state_known=1),Item(object=68))
        h=Heights(); assert dll.tomb_item_heights(C.byref(l),Ref(0,12),2560,0,2560,0,runtime,3,C.byref(h))
        assert h.object_references==2
        h=Heights(123,456,7,8,9); original=bytes(h)
        assert not dll.tomb_item_heights(C.byref(l),Ref(0,12),2560,0,2560,0,runtime,1,C.byref(h))
        assert bytes(h)==original
    report=dict(direct_cases_per_build=direct,ordered_dispatch_cases_per_build=dispatched,changed_callbacks=changes,levels=levels,
        height_queries_per_build=height_count,combined_queries_per_build=world_count,seconds=round(time.monotonic()-started,2),
        limits='Seven recovered callback IDs. Runtime states are controlled fixtures, not reconstructed initialization or object control. Other object types remain marked unresolved in C. No door sector mutation, triggers, or full-game equivalence claimed.',
        builds=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in args.dll],
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [ROOT/'src/item_height.c',ROOT/'src/geometry.c',ROOT/'src/terrain.c',ROOT/'src/level.c',ROOT/'src/level.h',Path(__file__)]})
    (ROOT/'analysis/c-item-validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: item callbacks, dispatched heights and combined contacts')

if __name__=='__main__': main()
