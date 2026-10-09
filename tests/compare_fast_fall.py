"""State 9 control/collision differential checks; audio and landing are explicit services."""
from compare_air import *
class FastOracle(AirOracle):
    def __init__(self,path):
        super().__init__(path)
        self.uc.hook_add(UC_HOOK_CODE,self.external,begin=0x2dc00,end=0x2dc00)
    def external(self,uc,address,size,data):
        if address==0x2dc00:
            self.events.append((7,uc.reg_read(UC_X86_REG_EAX),state(self.get(ITEM,Actor,ACTOR))))
            self.ret(); return
        return super().external(uc,address,size,data)
def main():
    oracle=FastOracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for dll in libs:
        dll.tomb_fast_fall_control.argtypes=[C.POINTER(Actor),EVENT,C.c_void_p]
        dll.tomb_fast_fall_deflect.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air)]
        dll.tomb_fast_fall_collision.argtypes=dll.tomb_fast_fall_deflect.argtypes
    rng=random.Random(19961010); edges=[-32768,-32767,-1,0,1,95,99,100,131,140,141,153,154,155,32767]
    for i in range(18000):
        mode=i//6000
        a=Actor(x=rng.randint(-2147483648,2147483647),y=rng.randint(-2147483648,2147483647),z=rng.randint(-2147483648,2147483647),
            current=9,goal=9,animation=32,frame=481,speed=rng.choice(edges),fall_speed=rng.choice(edges),yaw=rng.randrange(-32768,32768),room=7,flags=rng.randrange(256))
        c=Contact(floor=rng.choice([-32512,-1,0,1,200]),shift_x=8,shift_y=-5,shift_z=2,old_x=123,old_y=456,old_z=789,
            facing=rng.randrange(-32768,32768),type=rng.choice([0,1,2,3,4,8,16,32,64,-1]),flags=rng.randrange(256))
        move=rng.randrange(-32768,32768); oracle.write(0xce9ce,move,2); oracle.dead=rng.randrange(2)
        expected=oracle.run([0x256e0,0x27a74,0x2674c][mode],a,c)
        expected_c=oracle.get(COLL,Contact,CONTACT); expected_move=oracle.read(0xce9ce,2); expected_events=oracle.events[:]
        for dll in libs:
            events=[]
            @QUERY
            def query(_,pa,pc,h): events.append(('query',state(pa.contents),state(pc.contents),h))
            @ACTION
            def land(_,pa,pc):
                events.append(('land',state(pa.contents),state(pc.contents)))
                pa.contents.x=wrap32(pa.contents.x+17); return oracle.dead
            @EVENT
            def sound(_,kind,ident,pa): events.append((kind,ident,state(pa.contents)))
            ctx=Air(query,land,None,oracle.sine,move,sound); actual=clone(a); contact=clone(c)
            if mode==0: assert dll.tomb_fast_fall_control(C.byref(actual),sound,None)
            else:
                fn=dll.tomb_fast_fall_deflect if mode==1 else dll.tomb_fast_fall_collision
                fn(C.byref(actual),C.byref(contact),C.byref(ctx))
            assert state(actual)==state(expected),(i,state(actual),state(expected))
            assert state(contact)==state(expected_c) and ctx.move_angle==expected_move
            assert events==expected_events,(i,events,expected_events)
    report=dict(control=6000,deflection=6000,collision=6000,builds=2,
        scope='Original state 9 instructions, query/landing/audio service doubles; not full-frame equivalence.',
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/air.c',ROOT/'src/air.h',Path(__file__)]})
    (ROOT/'analysis/c-fast-fall-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 18000 fast-fall control/deflection/collision cases per build')
if __name__=='__main__': main()
