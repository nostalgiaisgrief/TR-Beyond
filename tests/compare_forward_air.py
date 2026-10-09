"""State 3 against DOS; query, landing and landing-time animation use explicit doubles."""
from compare_air import *
class ForwardOracle(AirOracle):
    def __init__(self,path):
        super().__init__(path)
        self.allowed.update([0xce9cc,0xce9cd])
        self.uc.hook_add(UC_HOOK_CODE,self.external,begin=0x28820,end=0x28820)
    def external(self,uc,address,size,data):
        if address==0x28820:
            a=self.get(ITEM,Actor,ACTOR); self.events.append(('advance',state(a)))
            self.write(ITEM+0x30,a.x-13,4); self.write(ITEM+0x16,a.frame+1,2); self.write(ITEM+0xe,a.goal,2)
            self.ret(); return
        return super().external(uc,address,size,data)
def main():
    oracle=ForwardOracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for dll in libs:
        dll.tomb_forward_air_control.argtypes=[C.POINTER(Actor),C.c_uint32,I16,C.POINTER(I16)]
        dll.tomb_forward_air_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air),C.c_uint32]
    rng=random.Random(19961011); edges=[-32768,-32767,-1,0,1,130,131,132,32767]
    for i in range(12000):
        inp=i if i<8192 else rng.getrandbits(32); weapon=rng.choice([-1,0,1,4]); rate=rng.choice([-32768,-32360,-547,-546,-545,-1,0,1,545,546,547,32359,32767])
        a=Actor(current=3,goal=rng.choice([2,3,8,9,11,52]),fall_speed=rng.choice(edges))
        oracle.write(0xce92c,inp,4); oracle.write(0xce966,weapon,2); oracle.write(0xce9cc,rate,2)
        expected=oracle.run(0x25494,a); expected_rate=oracle.read(0xce9cc,2)
        for dll in libs:
            actual=clone(a); turn=I16(rate)
            dll.tomb_forward_air_control(C.byref(actual),inp,weapon,C.byref(turn))
            assert state(actual)==state(expected) and turn.value==expected_rate
    for i in range(6000):
        a=Actor(x=rng.randint(-2147483648,2147483647),y=rng.randint(-2147483648,2147483647),z=rng.randint(-2147483648,2147483647),
            current=3,goal=3,animation=77,frame=rng.choice(edges),speed=rng.choice(edges),fall_speed=rng.choice(edges),yaw=rng.randrange(-32768,32768),room=7,flags=rng.randrange(256))
        c=Contact(floor=rng.choice([-32512,-1,0,1,384]),shift_x=8,shift_y=-5,shift_z=2,old_x=123,old_y=456,old_z=789,
            facing=rng.randrange(-32768,32768),type=rng.choice([0,1,2,4,8,16,32,64,-1]),flags=rng.randrange(256))
        inp=rng.choice([0,1,128,129,0xffffffff]); move=rng.randrange(-32768,32768)
        oracle.write(0xce9ce,move,2); oracle.write(0xce92c,inp,4); oracle.dead=rng.randrange(2)
        expected=oracle.run(0x26484,a,c); expected_c=oracle.get(COLL,Contact,CONTACT)
        expected_move=oracle.read(0xce9ce,2); expected_events=oracle.events[:]
        for dll in libs:
            events=[]
            @QUERY
            def query(_,pa,pc,h): events.append(('query',state(pa.contents),state(pc.contents),h))
            @ACTION
            def land(_,pa,pc):
                events.append(('land',state(pa.contents),state(pc.contents)))
                pa.contents.x=wrap32(pa.contents.x+17); return oracle.dead
            @ADVANCE
            def advance(_,pa):
                events.append(('advance',state(pa.contents)))
                pa.contents.x=wrap32(pa.contents.x-13); pa.contents.frame=C.c_int16(pa.contents.frame+1).value; pa.contents.current=pa.contents.goal
                return 1
            ctx=Air(query,land,None,oracle.sine,move,EVENT(),advance); actual=clone(a); contact=clone(c)
            assert dll.tomb_forward_air_collision(C.byref(actual),C.byref(contact),C.byref(ctx),inp)
            assert state(actual)==state(expected),(i,state(actual),state(expected))
            assert state(contact)==state(expected_c) and ctx.move_angle==expected_move
            assert events==expected_events
    report=dict(control=12000,collision=6000,builds=2,
        scope='Original state 3 routines; query, landing and landing-time animation doubled. No full-frame equivalence.',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/air.c',ROOT/'src/air.h',Path(__file__)]})
    (ROOT/'analysis/c-forward-air-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 18000 forward-air control/collision cases per build')
if __name__=='__main__': main()
