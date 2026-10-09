"""Standing preparation/upward jump against the original DOS instructions."""
from compare_air import *
PROBE=C.CFUNCTYPE(I16,C.c_void_p,C.POINTER(Actor),I16,I32)
JQUERY=C.CFUNCTYPE(I32,C.c_void_p,C.POINTER(Actor),C.POINTER(Contact),I32)
class JumpOracle(AirOracle):
    def __init__(self,path):
        super().__init__(path)
        self.ceiling=-100; self.floors=[0]*4; self.grab=0
        for address in [0x2828c,0x27fa0]: self.uc.hook_add(UC_HOOK_CODE,self.external,begin=address,end=address)
    def external(self,uc,address,size,data):
        if address==0x2828c:
            angle=C.c_int16(uc.reg_read(UC_X86_REG_EDX)).value
            distance=uc.reg_read(UC_X86_REG_EBX)
            self.events.append(('probe',angle,distance))
            self.ret(self.floors[len(self.events)-1]&65535); return
        if address==0x27fa0:
            self.events.append(('grab',state(self.get(ITEM,Actor,ACTOR)),state(self.get(COLL,Contact,CONTACT))))
            self.ret(self.grab); return
        if address==0x151c0:
            sp=uc.reg_read(UC_X86_REG_ESP); height=self.read(sp+8,4)
            self.events.append(('query',state(self.get(ITEM,Actor,ACTOR)),state(self.get(COLL,Contact,CONTACT)),height))
            self.write(COLL+4,self.ceiling,4); self.ret(pop=8); return
        super().external(uc,address,size,data)
def main():
    oracle=JumpOracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for d in libs:
        d.tomb_jump_prepare_control.argtypes=[C.POINTER(Actor),C.c_uint32,PROBE,C.c_void_p,C.POINTER(I16)]
        d.tomb_jump_prepare_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),JQUERY,C.c_void_p,I16]
        d.tomb_up_jump_control.argtypes=[C.POINTER(Actor)]
        d.tomb_up_jump_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air),ACTION]
    rng=random.Random(19961012)
    edges=[-32768,-32512,-385,-384,-383,-1,0,1,131,132,32767]
    for i in range(6000):
        a=Actor(current=15,goal=rng.randrange(56),yaw=rng.randrange(-32768,32768),fall_speed=rng.choice(edges))
        inp=rng.getrandbits(32); move=rng.randrange(-32768,32768);oracle.floors=[rng.choice(edges) for _ in range(4)]
        oracle.write(0xce92c,inp,4);oracle.write(0xce9ce,move,2)
        expected=oracle.run(0x2579c,a); em=oracle.read(0xce9ce,2); ee=oracle.events[:]
        for d in libs:
            events=[]
            @PROBE
            def probe(_,pa,angle,distance):
                events.append(('probe',angle,distance)); return oracle.floors[len(events)-1]
            actual=clone(a); m=I16(move);d.tomb_jump_prepare_control(C.byref(actual),inp,probe,None,C.byref(m))
            assert state(actual)==state(expected) and m.value==em and events==ee
    for i in range(6000):
        a=Actor(x=1234,y=-567,z=890,current=15,goal=3,animation=73,frame=1180,speed=rng.choice(edges),fall_speed=rng.choice(edges),flags=rng.randrange(256))
        c=Contact(old_x=123,old_y=-456,old_z=789,floor=rng.choice(edges),flags=rng.randrange(256))
        move=rng.randrange(-32768,32768); oracle.ceiling=rng.choice([-32512,-101,-100,-99,0,32767]); oracle.write(0xce9ce,move,2)
        expected=oracle.run(0x26978,a,c);ec=oracle.get(COLL,Contact,CONTACT);ee=oracle.events[:]
        for d in libs:
            events=[]
            @JQUERY
            def query(_,pa,pc,h):
                events.append(('query',state(pa.contents),state(pc.contents),h));return oracle.ceiling
            actual=clone(a);contact=clone(c)
            d.tomb_jump_prepare_collision(C.byref(actual),C.byref(contact),query,None,move)
            assert state(actual)==state(expected) and state(contact)==state(ec) and events==ee
    for i in range(6000):
        a=Actor(x=rng.randint(-2147483648,2147483647),y=-123,z=789,current=28,goal=rng.randrange(56),animation=28,frame=440,speed=rng.choice(edges),fall_speed=rng.choice(edges),yaw=rng.randrange(-32768,32768),flags=rng.randrange(256))
        expected_control=oracle.run(0x25ac8,a)
        c=Contact(floor=rng.choice(edges),shift_x=7,shift_y=-3,shift_z=4,type=rng.choice([0,1,2,4,8,16,32]),flags=rng.randrange(256))
        move=rng.randrange(-32768,32768);oracle.write(0xce9ce,move,2);oracle.grab=rng.randrange(2);oracle.dead=rng.randrange(2)
        expected=oracle.run(0x26d28,a,c);ec=oracle.get(COLL,Contact,CONTACT);em=oracle.read(0xce9ce,2);ee=oracle.events[:]
        for d in libs:
            actual=clone(a);d.tomb_up_jump_control(C.byref(actual));assert state(actual)==state(expected_control)
            events=[]
            @QUERY
            def query(_,pa,pc,h):events.append(('query',state(pa.contents),state(pc.contents),h))
            @ACTION
            def grab(_,pa,pc):
                events.append(('grab',state(pa.contents),state(pc.contents)));return oracle.grab
            @ACTION
            def land(_,pa,pc):
                events.append(('land',state(pa.contents),state(pc.contents)));pa.contents.x=wrap32(pa.contents.x+17);return oracle.dead
            ctx=Air(query,land,None,oracle.sine,move);actual=clone(a);contact=clone(c)
            assert d.tomb_up_jump_collision(C.byref(actual),C.byref(contact),C.byref(ctx),grab)
            assert state(actual)==state(expected) and state(contact)==state(ec) and ctx.move_angle==em and events==ee
    report=dict(preparation_control=6000,preparation_collision=6000,upward_control=6000,upward_collision=6000,builds=2,scope='Isolated DOS routines; floor probe, query, grab and landing services doubled. No full-frame equivalence.',sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/air.c',ROOT/'src/air.h',Path(__file__)]})
    (ROOT/'analysis/c-standing-jump-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 24000 standing-jump control/collision cases per build')
if __name__=='__main__':main()
