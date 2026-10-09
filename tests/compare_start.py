"""Fresh Lara movement state against generic item init + original Lara reset.
Inventory/weapon/mesh setup and scratch allocation are explicit service doubles.
"""
import ctypes as C
import hashlib
import json
import random
import struct
import time
from pathlib import Path
from compare_level import ROOT,GeometryOracle,Level,Item,bind,parse,ROOMS,ITEMS
from compare_step import Actor,I16,I32,state,clone,ACTOR,STACK,RETURN,UC_HOOK_CODE,UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EFLAGS

GLOBAL_FIELDS=dict(health=None,air=0xce976,water_status=0xce96e,turn_rate=0xce9cc,move_angle=0xce9ce,
    fall_override=0xce96c,pitch=None,lean=None,head_yaw=0xce9d0,head_pitch=0xce9d2,
    head_roll=0xce9d4,torso_yaw=0xce9d6,torso_pitch=0xce9d8,torso_roll=0xce9da)
class Start(C.Structure):
    _fields_=[('actor',Actor),('item_index',C.c_uint32),('sector_floor',I32)]+[(n,I16) for n in GLOBAL_FIELDS]+[('services_pending',C.c_uint8)]

class StartOracle(GeometryOracle):
    def __init__(self):
        super().__init__(); self.boundaries=[]
        for addr in [0x2d11c,0x28e9c]: self.uc.hook_add(UC_HOOK_CODE,self.service,begin=addr,end=addr)
        self.allowed.update(range(0xce960,0xcea40))
    def service(self,uc,addr,size,data):
        self.boundaries.append(addr); self.ret()
    def initialize(self,f,index,item,flags):
        at=ITEMS+index*68
        self.allowed.update(range(at,at+68)); self.allowed.update(range(ROOMS+item.room*68+0x3c,ROOMS+item.room*68+0x3e))
        self.uc.mem_write(at,bytes([0xa5])*68)
        for off,val,width in [(12,0,2),(24,item.room,2),(40,0,2),(48,item.x,4),(52,item.y,4),(56,item.z,4),(62,item.yaw,2),(66,0,1)]:
            self.write(at+off,val,width)
        self.write(ROOMS+item.room*68+0x42,flags,2); self.write(ROOMS+item.room*68+0x3c,-1,2)
        models=f['sections']['models']; base=None
        for j in range(models['count']):
            if struct.unpack_from('<I',models['bytes'],j*18)[0]==0: base=struct.unpack_from('<h',models['bytes'],j*18+16)[0]
        assert base is not None
        self.write(0xcc084,base,2); self.write(0xcc086,1000,2); self.write(0xcc06c,0x28d14,4)
        self.write(0xcefbb,0,1); self.uc.mem_write(0xce960,bytes([0xa5])*(0xcea40-0xce960))
        self.boundaries=[]; self.bad=[]
        for fn in [0x24870,0x28d38]:
            self.write(STACK+0x800,RETURN,4); self.uc.reg_write(UC_X86_REG_ESP,STACK+0x800)
            self.uc.reg_write(UC_X86_REG_EAX,index); self.uc.reg_write(UC_X86_REG_EFLAGS,2)
            self.uc.emu_start(fn,RETURN,count=10000)
            assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN and self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x804
        assert not self.bad,self.bad
        assert self.boundaries==[0x2d11c,0x28e9c]
        assert self.read(0xce960,4)==at and self.read(0xce964,2)==index
        result=dict(actor=state(self.get(at,Actor,ACTOR)),item_index=index,sector_floor=self.read(at,4),services_pending=3)
        for name,address in GLOBAL_FIELDS.items():
            address=address if address else at+{'health':0x22,'pitch':0x3c,'lean':0x40}[name]
            result[name]=self.read(address,2)
        return result

def snapshot(s):
    result=state(s); result['actor']=state(s.actor); return result

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--dll',nargs='+',type=Path,required=True); args=p.parse_args()
    dlls=[bind(path) for path in args.dll]; oracle=StartOracle(); rng=random.Random(19961008); results=[]; count=0; begun=time.monotonic()
    for dll in dlls:
        assert dll.tomb_test_size(14)==C.sizeof(Start)
        dll.tomb_lara_start.argtypes=[C.POINTER(Level),C.POINTER(Start)]
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name; f=parse(path); oracle.install(f); loaded=[]
        index=next(i for i,v in enumerate(f['items']) if v[0]==0)
        for dll in dlls:
            err=C.create_string_buffer(256); ptr=dll.tomb_level_load(str(path).encode(),err,len(err)); assert ptr,err.value
            loaded.append((dll,ptr))
        initial=clone(loaded[0][1].contents.items[index]); initial_flags=loaded[0][1].contents.rooms[initial.room].flags
        assert initial.flags==0
        original_snapshot=None
        for j in range(1001):
            item=clone(initial); flags=initial_flags
            if j:
                item.yaw=rng.randint(-32768,32767); item.y=rng.randint(-32768,32767)
                flags=C.c_int16(rng.randrange(65536)).value
            expected=oracle.initialize(f,index,item,flags)
            for dll,ptr in loaded:
                ptr.contents.items[index]=item; ptr.contents.rooms[item.room].flags=flags
                actual=Start(); C.memset(C.byref(actual),0x96,C.sizeof(actual))
                assert dll.tomb_lara_start(ptr,C.byref(actual)),(name,j)
                assert snapshot(actual)==expected,(name,j,snapshot(actual),expected)
            if j==0: original_snapshot=expected
            count+=1
        # Reject ambiguous/invalid startup rather than silently create Lara.
        rejected=0
        for dll,ptr in loaded:
            l=ptr.contents; l.items[index]=initial; l.rooms[initial.room].flags=initial_flags
            out=Start(); C.memset(C.byref(out),0x96,C.sizeof(out)); before=bytes(out)
            original_count=l.item_count; original_anims=l.animation_count
            checks=[('missing',None),('flags',256),('room',-1),('position',-2147483648),('animations',0)]
            for kind,value in checks:
                if kind=='missing': l.items[index].object=1
                elif kind=='flags': l.items[index].flags=value
                elif kind=='room': l.items[index].room=value
                elif kind=='position': l.items[index].x=value
                else: l.animation_count=value
                assert not dll.tomb_lara_start(ptr,C.byref(out)) and bytes(out)==before,(name,kind)
                l.items[index]=initial; l.item_count=original_count; l.animation_count=original_anims; rejected+=1
            dll.tomb_level_free(ptr)
        result=dict(level=name,cases_per_build=1001,start=original_snapshot,rejections_across_builds=rejected)
        results.append(result); print(json.dumps(result),flush=True)
    report=dict(total_per_build=count,levels=results,seconds=round(time.monotonic()-begun,2),
        limits='Fresh ordinary Lara placement movement state. Inventory/weapon/mesh setup and scratch allocator are service doubles. No save restoration, camera, rendering or playable simulation.',
        builds=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in args.dll],
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 [ROOT/'src/lara_start.c',ROOT/'src/lara_start.h',Path(__file__)]})
    (ROOT/'analysis/c-start-validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: Lara fresh-start movement state')

if __name__=='__main__': main()
