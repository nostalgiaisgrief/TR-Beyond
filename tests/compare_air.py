"""Backward falling against DOS instructions, with explicit landing-service doubles."""
import ctypes as C
import hashlib,json,random
from compare_step import *
ADVANCE=C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(Actor))
class Air(C.Structure):
    _fields_=[('query',QUERY),('land',ACTION),('user',C.c_void_p),('sine_quarter',C.POINTER(I16)),('move_angle',I16),('sound',EVENT),('advance',ADVANCE)]
class AirOracle(Oracle):
    def __init__(self,path):
        super().__init__(path)
        self.dead=0
        self.uc.hook_add(UC_HOOK_CODE,self.external,begin=0x28300,end=0x28300)
    def external(self,uc,address,size,data):
        if address!=0x28300: return super().external(uc,address,size,data)
        self.events.append(('land',state(self.get(ITEM,Actor,ACTOR)),state(self.get(COLL,Contact,CONTACT))))
        self.write(ITEM+0x30,self.read(ITEM+0x30,4)+17,4)
        self.ret(self.dead)
def main():
    oracle=AirOracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for dll in libs:
        dll.tomb_back_fall_control.argtypes=[C.POINTER(Actor),C.c_uint32,I16]
        dll.tomb_air_deflect.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air)]
        dll.tomb_back_fall_collision.argtypes=dll.tomb_air_deflect.argtypes
        dll.tomb_landing_damage.argtypes=[C.POINTER(I16),I16]
    rng=random.Random(19961009)
    edges=[-32768,-32767,-32766,-1,0,1,130,131,132,139,140,141,153,154,155,32767]
    for i in range(6000):
        a=Actor(current=29,goal=rng.randrange(56),fall_speed=rng.choice(edges))
        inp=rng.getrandbits(32); weapon=rng.choice([-1,0,1,4])
        oracle.write(0xce92c,inp,4); oracle.write(0xce966,weapon,2)
        expected=oracle.run(0x25ad8,a)
        for dll in libs:
            actual=clone(a); dll.tomb_back_fall_control(C.byref(actual),inp,weapon)
            assert state(actual)==state(expected)
    for i in range(12000):
        a=Actor(x=rng.randint(-2147483648,2147483647),y=rng.randint(-2147483648,2147483647),z=rng.randint(-2147483648,2147483647),
            current=29,goal=29,animation=93,frame=1473,speed=rng.choice(edges),fall_speed=rng.choice(edges),yaw=rng.randrange(-32768,32768),room=7,flags=rng.randrange(256))
        c=Contact(floor=rng.choice([-32512,-1,0,1,200,201]),positive_limit=1,negative_limit=-1,ceiling_limit=7,
            shift_x=8,shift_y=-5,shift_z=2,old_x=123,old_y=456,old_z=789,facing=rng.randrange(-32768,32768),type=rng.choice([0,1,2,3,4,8,16,32,64,-1]),flags=rng.randrange(256))
        move=rng.randrange(-32768,32768); oracle.write(0xce9ce,move,2); oracle.dead=rng.randrange(2)
        collision=i%2==0; expected=oracle.run(0x26dc8 if collision else 0x2793c,a,c)
        expected_c=oracle.get(COLL,Contact,CONTACT); expected_move=oracle.read(0xce9ce,2); expected_events=oracle.events[:]
        for dll in libs:
            events=[]
            @QUERY
            def query(_,pa,pc,h): events.append(('query',state(pa.contents),state(pc.contents),h))
            @ACTION
            def land(_,pa,pc):
                events.append(('land',state(pa.contents),state(pc.contents)))
                pa.contents.x=wrap32(pa.contents.x+17); return oracle.dead
            ctx=Air(query,land,None,oracle.sine,move); actual=clone(a); contact=clone(c)
            fn=dll.tomb_back_fall_collision if collision else dll.tomb_air_deflect
            fn(C.byref(actual),C.byref(contact),C.byref(ctx))
            assert state(actual)==state(expected),(i,state(actual),state(expected))
            assert state(contact)==state(expected_c) and ctx.move_angle==expected_move
            assert events==expected_events
    for i in range(6000):
        speed=rng.choice(edges) if i<3000 else rng.randrange(-32768,32768)
        hp=rng.choice([-32768,-1,0,1,5,500,1000,32767])
        oracle.write(ITEM+0x20,speed,2); oracle.write(ITEM+0x22,hp,2)
        oracle.uc.reg_write(UC_X86_REG_ESI,ITEM); oracle.uc.reg_write(UC_X86_REG_EDI,123)
        oracle.uc.emu_start(0x28346,0x283a1,count=100)
        result=oracle.uc.reg_read(UC_X86_REG_EAX); expected=oracle.read(ITEM+0x22,2)
        for dll in libs:
            health=I16(hp); actual=dll.tomb_landing_damage(C.byref(health),speed)
            assert (actual,health.value)==(result,expected)
    report=dict(control=6000,air_deflection=6000,backward_collision=6000,landing_damage=6000,builds=2,
        scope='Isolated DOS instructions; query/landing services doubled. Damage tail excludes floor and trigger dispatch.',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/air.c',ROOT/'src/air.h',Path(__file__)]})
    (ROOT/'analysis/c-air-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 24000 backward-control, airborne collision and damage cases per build')
if __name__=='__main__': main()
