"""Compare C animation and collision code to original DOS instructions.

Audio/effects and room/vault/slide services are explicit controlled test doubles
on BOTH sides. Original transition, fixed-point motion, sine lookup, command
decode, ceiling, wall and shift routines execute without replacements.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from analyse_le import load
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn.x86_const import *

I16, I32, U8, SZ = C.c_int16, C.c_int32, C.c_uint8, C.c_size_t
class Actor(C.Structure):
    _fields_ = [(n,I32) for n in ('x','y','z')] + [(n,I16) for n in
        ('current','goal','animation','frame','speed','fall_speed','yaw','room')] + [('flags',U8)]
class Anim(C.Structure):
    _fields_ = [(n,I32) for n in ('velocity','acceleration')] + [(n,I16) for n in
        ('state','first_frame','last_frame','next_animation','next_frame','change_count','change_index','command_count','command_index')]
class Change(C.Structure):
    _fields_ = [(n,I16) for n in ('goal','count','index')]
class Range(C.Structure):
    _fields_ = [(n,I16) for n in ('first','last','animation','frame')]
EVENT = C.CFUNCTYPE(None,C.c_void_p,C.c_int,I16,C.POINTER(Actor))
class AnimContext(C.Structure):
    _fields_ = [('animations',C.POINTER(Anim)),('animation_count',SZ),
        ('changes',C.POINTER(Change)),('change_count',SZ),('ranges',C.POINTER(Range)),('range_count',SZ),
        ('commands',C.POINTER(I16)),('command_count',SZ),('sine_quarter',C.POINTER(I16)),
        ('move_angle',I16),('fall_override',I16),('weapon_status',I16),('event',EVENT),('user',C.c_void_p)]
class Contact(C.Structure):
    _fields_ = [(n,I32) for n in ('floor','positive_limit','negative_limit','ceiling_limit',
        'shift_x','shift_y','shift_z','old_x','old_y','old_z')] + [('facing',I16),('type',I16),('flags',U8)]
QUERY = C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Actor),C.POINTER(Contact),I32)
ACTION = C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(Actor),C.POINTER(Contact))
class WalkContext(C.Structure):
    _fields_ = [('query',QUERY),('vault',ACTION),('slide',ACTION),('user',C.c_void_p),('move_angle',I16)]

ITEM,COLL,STACK,RETURN,DATA,FX = 0x200000,0x201000,0x210000,0x220000,0x300000,0x390000
ACTOR = dict(x=(0x30,4),y=(0x34,4),z=(0x38,4),current=(0xe,2),goal=(0x10,2),
    animation=(0x14,2),frame=(0x16,2),speed=(0x1e,2),fall_speed=(0x20,2),yaw=(0x3e,2),room=(0x18,2),flags=(0x42,1))
CONTACT = dict(floor=(0,4),positive_limit=(0x34,4),negative_limit=(0x38,4),ceiling_limit=(0x3c,4),
    shift_x=(0x40,4),shift_y=(0x44,4),shift_z=(0x48,4),old_x=(0x4c,4),old_y=(0x50,4),old_z=(0x54,4),
    facing=(0x58,2),type=(0x5c,2),flags=(0x66,1))

def state(s):
    return {name:getattr(s,name) for name,_ in s._fields_}
def wrap32(x):
    return C.c_int32(x).value
def clone(s):
    return type(s).from_buffer_copy(bytes(s))


class Oracle:
    def __init__(self,exe):
        raw,objects,_,_=load(exe)
        assert hashlib.sha256(raw).hexdigest()=='99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'
        self.uc=Uc(UC_ARCH_X86,UC_MODE_32)
        for o in objects:
            self.uc.mem_map(o['base'],(len(o['data'])+4095)&~4095)
            self.uc.mem_write(o['base'],bytes(o['data']))
        for address,size in [(ITEM,8192),(STACK,4096),(RETURN,4096),(DATA,0x10000),(FX,4096)]:
            self.uc.mem_map(address,size)
        self.sine=(I16*1025).from_buffer_copy(self.uc.mem_read(0xc50c4,2050))
        for i in range(17): self.write(0xc1858+i*4,FX+i*16,4)
        self.events=[]; self.bad=[]; self.vault=0; self.slide=0
        for address in [0x2d2b4,0x151c0,0x27b44,0x28128]:
            self.uc.hook_add(UC_HOOK_CODE,self.external,begin=address,end=address)
        self.uc.hook_add(UC_HOOK_CODE,self.external,begin=FX,end=FX+256)
        self.uc.hook_add(UC_HOOK_MEM_WRITE,self.writes)
        self.allowed=set()
        for base,fields in [(ITEM,ACTOR),(COLL,CONTACT)]:
            for off,width in fields.values(): self.allowed.update(range(base+off,base+off+width))
        # Walking uses a word OR spanning both flag bytes; second byte stays unchanged.
        self.allowed.add(ITEM+0x43)
        for addr,width in [(0xce96c,2),(0xce966,2),(0xce9ce,2)]: self.allowed.update(range(addr,addr+width))

    def write(self,address,value,width):
        self.uc.mem_write(address,(value & ((1<<(8*width))-1)).to_bytes(width,'little'))
    def read(self,address,width):
        return int.from_bytes(self.uc.mem_read(address,width),'little',signed=width!=1)
    def put(self,base,s,fields):
        self.uc.mem_write(base,bytes([0xa5])*256)
        for name,(off,width) in fields.items(): self.write(base+off,getattr(s,name),width)
    def get(self,base,cls,fields):
        return cls(**{name:self.read(base+off,width) for name,(off,width) in fields.items()})
    def writes(self,uc,access,addr,size,value,data):
        if STACK<=addr and addr+size<=STACK+4096: return
        if any(a not in self.allowed for a in range(addr,addr+size)): self.bad.append((addr,size))
    def ret(self,result=None,pop=0):
        sp=self.uc.reg_read(UC_X86_REG_ESP)
        target=int.from_bytes(self.uc.mem_read(sp,4),'little')
        self.uc.reg_write(UC_X86_REG_ESP,sp+4+pop)
        self.uc.reg_write(UC_X86_REG_EIP,target)
        if result is not None: self.uc.reg_write(UC_X86_REG_EAX,result)
    def external(self,uc,address,size,data):
        actor=self.get(ITEM,Actor,ACTOR)
        if address==0x2d2b4 or FX<=address<FX+272:
            kind=5 if address==0x2d2b4 else 6
            ident=C.c_int32(uc.reg_read(UC_X86_REG_EAX)).value if kind==5 else (address-FX)//16
            self.events.append((kind,ident,state(actor)))
            if kind==6: self.write(ITEM+0x30,actor.x+ident,4)
            self.ret(); return
        contact=self.get(COLL,Contact,CONTACT)
        if address==0x151c0:
            sp=uc.reg_read(UC_X86_REG_ESP)
            room=self.read(sp+4,4); height=self.read(sp+8,4)
            assert room==actor.room and height==762
            assert uc.reg_read(UC_X86_REG_EAX)==COLL
            assert C.c_int32(uc.reg_read(UC_X86_REG_EDX)).value==actor.x
            assert C.c_int32(uc.reg_read(UC_X86_REG_EBX)).value==actor.y
            assert C.c_int32(uc.reg_read(UC_X86_REG_ECX)).value==actor.z
            self.events.append(('query',state(actor),state(contact),height))
            self.ret(pop=8)
        else:
            label='vault' if address==0x27b44 else 'slide'
            result=self.vault if label=='vault' else self.slide
            self.events.append((label,state(actor),state(contact)))
            # Exercise caller ordering with a visible effect at the service boundary.
            if result: self.write(ITEM+0x30,actor.x+17,4)
            self.ret(result)
    def run(self,address,a,c=None):
        self.put(ITEM,a,ACTOR)
        if c is not None: self.put(COLL,c,CONTACT)
        self.write(STACK+0x800,RETURN,4)
        for reg in [UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESI,UC_X86_REG_EDI,UC_X86_REG_EBP]:
            self.uc.reg_write(reg,0x12345678)
        self.uc.reg_write(UC_X86_REG_EFLAGS,2)
        self.uc.reg_write(UC_X86_REG_EAX,ITEM); self.uc.reg_write(UC_X86_REG_EDX,COLL)
        self.uc.reg_write(UC_X86_REG_ESP,STACK+0x800)
        self.events=[]; self.bad=[]
        self.uc.emu_start(address,RETURN,count=10000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN
        assert self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x804
        assert not self.bad, self.bad
        return self.get(ITEM,Actor,ACTOR)


def setup_library(path):
    dll=C.CDLL(str(path.resolve()))
    dll.tomb_test_size.argtypes=[C.c_int]; dll.tomb_test_size.restype=SZ
    for i,cls in enumerate([Actor,Anim,AnimContext,Contact,WalkContext]):
        assert dll.tomb_test_size(i)==C.sizeof(cls),(cls,C.sizeof(cls),dll.tomb_test_size(i))
    dll.tomb_animate.argtypes=[C.POINTER(Actor),C.POINTER(AnimContext)]
    for name in ['tomb_contact_shift','tomb_ceiling_response','tomb_wall_response']:
        getattr(dll,name).argtypes=[C.POINTER(Actor),C.POINTER(Contact)]
    dll.tomb_contact_shift.restype=None
    dll.tomb_walk_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(WalkContext)]
    return dll


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dll',type=Path,nargs='+',required=True)
    parser.add_argument('--original',type=Path,default=Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    args=parser.parse_args()
    oracle=Oracle(args.original); libs=[setup_library(p) for p in args.dll]
    rng=random.Random(19961007); counts={'animation':0,'collision_helpers':0,'walk_orchestration':0}
    start=time.monotonic()
    edges=[-32768,-32767,-1,0,1,127,128,129,32766,32767]
    def actor():
        return Actor(x=rng.randint(-2147483648,2147483647),y=rng.randint(-2147483648,2147483647),
            z=rng.randint(-2147483648,2147483647),current=rng.randrange(4),goal=rng.randrange(4),
            animation=0,frame=rng.choice(edges+[10,11,12,13]),speed=rng.choice(edges),
            fall_speed=rng.choice(edges),yaw=rng.randint(-32768,32767),room=rng.randrange(20),flags=rng.randrange(256))
    for case in range(6000):
        a=actor(); move=rng.randint(-32768,32767); override=rng.choice(edges); weapon=rng.choice(edges)
        anims=(Anim*3)(); changes=(Change*3)(Change(1,2,0),Change(2,1,2),Change(1,1,3))
        ranges=(Range*4)(Range(-32768,0,1,4),Range(10,12,2,14),Range(0,15,1,6),Range(-32768,32767,2,8))
        if case%8==0: a.current=0; a.goal=1; a.frame=9+(case%4)
        if case%8==1: a.current=0; a.goal=0; a.frame=12
        words=[]
        for i in range(3):
            index=len(words)
            # Include move, jump, weapon reset, no-op, timed sound and effect.
            ops=[(1,[rng.choice(edges),rng.choice(edges),rng.choice(edges)]),
                 (2,[rng.choice(edges),rng.choice(edges)]),(3,[]),(4,[]),
                 (5,[rng.choice([4,6,8,13,14]),rng.randrange(100)]),
                 (6,[rng.choice([4,6,8,13,14]),rng.randrange(17)])]
            rng.shuffle(ops)
            selected=ops[:rng.randrange(7)]
            for op,params in selected: words += [op]+params
            anims[i]=Anim(velocity=rng.randint(-2147483648,2147483647),
                acceleration=rng.choice([0,65536,-65536,2147483647,-2147483648,rng.randint(-2147483648,2147483647)]),
                state=i,first_frame=rng.choice([-32768,0,4,10,32767]),last_frame=12,
                next_animation=(i+1)%3,next_frame=rng.choice([4,6,8,13,14]),
                change_count=3 if i==0 and case%3 else 0,change_index=0,
                command_count=len(selected),command_index=index)
        commands=(I16*max(1,len(words)))(*words)
        for i,anim in enumerate(anims):
            b=bytearray(32)
            struct.pack_into('<hii8h',b,6,anim.state,anim.velocity,anim.acceleration,
                anim.first_frame,anim.last_frame,anim.next_animation,anim.next_frame,
                anim.change_count,anim.change_index,anim.command_count,anim.command_index)
            oracle.uc.mem_write(DATA+i*32,bytes(b))
        oracle.uc.mem_write(DATA+0x1000,bytes(changes)); oracle.uc.mem_write(DATA+0x2000,bytes(ranges))
        oracle.uc.mem_write(DATA+0x3000,bytes(commands))
        for dest,value in [(0xcc03c,DATA),(0xcc054,DATA+0x1000),(0xcc04c,DATA+0x2000),(0xcc048,DATA+0x3000)]: oracle.write(dest,value,4)
        oracle.write(0xce9ce,move,2); oracle.write(0xce96c,override,2); oracle.write(0xce966,weapon,2)
        expected=oracle.run(0x28820,a)
        expected_context=(oracle.read(0xce96c,2),oracle.read(0xce966,2))
        expected_events=list(oracle.events)
        for dll in libs:
            events=[]
            @EVENT
            def event(user,kind,ident,ptr):
                events.append((kind,ident,state(ptr.contents)))
                if kind==6: ptr.contents.x=wrap32(ptr.contents.x+ident)
            ctx=AnimContext(anims,3,changes,3,ranges,4,commands,len(words),oracle.sine,move,override,weapon,event,None)
            actual=clone(a)
            assert dll.tomb_animate(C.byref(actual),C.byref(ctx))==1
            assert state(actual)==state(expected),(case,'animation',state(a),state(actual),state(expected))
            assert (ctx.fall_override,ctx.weapon_status)==expected_context
            assert events==expected_events,(case,'events',events,expected_events)
        counts['animation']+=1
    print('Animation comparisons passed',flush=True)
    floors=[-2147483648,-385,-384,-383,-129,-128,-127,0,127,128,129,383,384,385,2147483647]
    frames=[-32768,21,22,26,27,28,29,44,45,46,47,48,57,58,32767]
    for case in range(6000):
        a=actor(); a.frame=frames[case%len(frames)]
        contact=Contact(floor=floors[(case//len(frames))%len(floors)],positive_limit=13,negative_limit=-13,
            ceiling_limit=17,shift_x=rng.randint(-2147483648,2147483647),shift_y=rng.randint(-2147483648,2147483647),
            shift_z=rng.randint(-2147483648,2147483647),old_x=123,old_y=-456,old_z=789,
            facing=321,type=rng.choice([0,1,2,4,8,16,32,3,-1,32767]),flags=rng.randrange(256))
        for address,name in [(0x15f84,'tomb_contact_shift'),(0x27620,'tomb_ceiling_response'),(0x278d0,'tomb_wall_response')]:
            expected=oracle.run(address,a,contact); expected_contact=oracle.get(COLL,Contact,CONTACT)
            result=oracle.uc.reg_read(UC_X86_REG_EAX)
            for dll in libs:
                actual,coll=clone(a),clone(contact)
                returned=getattr(dll,name)(C.byref(actual),C.byref(coll))
                assert state(actual)==state(expected),(case,name,state(actual),state(expected))
                assert state(coll)==state(expected_contact)
                if name!='tomb_contact_shift': assert returned==result
            counts['collision_helpers']+=1
        oracle.vault=1 if case%7==0 else 0; oracle.slide=1 if case%5==0 else 0
        expected=oracle.run(0x26084,a,contact); expected_contact=oracle.get(COLL,Contact,CONTACT)
        expected_events=list(oracle.events); expected_angle=oracle.read(0xce9ce,2)
        for dll in libs:
            events=[]
            @QUERY
            def query(user,ptr,cp,height): events.append(('query',state(ptr.contents),state(cp.contents),height))
            @ACTION
            def vault(user,ptr,cp):
                events.append(('vault',state(ptr.contents),state(cp.contents)))
                if oracle.vault: ptr.contents.x=wrap32(ptr.contents.x+17)
                return oracle.vault
            @ACTION
            def slide(user,ptr,cp):
                events.append(('slide',state(ptr.contents),state(cp.contents)))
                if oracle.slide: ptr.contents.x=wrap32(ptr.contents.x+17)
                return oracle.slide
            ctx=WalkContext(query,vault,slide,None,0); actual,coll=clone(a),clone(contact)
            assert dll.tomb_walk_collision(C.byref(actual),C.byref(coll),C.byref(ctx))==1
            assert state(actual)==state(expected),(case,'walk',state(actual),state(expected))
            assert state(coll)==state(expected_contact)
            assert ctx.move_angle==expected_angle and events==expected_events
        counts['walk_orchestration']+=1
    print('Collision comparisons passed',flush=True)
    report=dict(cases=counts,total_per_build=sum(counts.values()),builds=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in args.dll],
        seed=19961007,seconds=round(time.monotonic()-start,2),
        original_sha256=hashlib.sha256(args.original.read_bytes()).hexdigest(),
        limits='Synthetic animation/contact data. Sound/effect callbacks and room/vault/slide services use identical controlled doubles on both sides. No PHD loader, world collision or full playable integration validated.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [ROOT/'src/animation.c',ROOT/'src/collision.c',ROOT/'src/step.h',ROOT/'src/fixed.h',Path(__file__)]})
    (ROOT/'analysis/c-step-validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
