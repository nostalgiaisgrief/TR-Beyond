"""Directional standing jumps compared with original DOS instructions."""
from compare_air import *
def main():
    oracle=AirOracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    oracle.allowed.update([0xcb2b9,0xcb2ba])
    libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for d in libs:
        d.tomb_directional_jump_control.argtypes=[C.POINTER(Actor),C.POINTER(I16)]
        d.tomb_directional_jump_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air)]
    rng=random.Random(19961013);edges=[-32768,-32767,-385,-384,-1,0,1,130,131,132,140,154,32767]
    for mode,control,collision in [(25,0x25a88,0x26cdc),(26,0x25aa8,0x26cf4),(27,0x25ab8,0x26d0c)]:
        for i in range(2000):
            a=Actor(current=mode,goal=rng.randrange(56),fall_speed=rng.choice(edges)); camera=rng.randrange(-32768,32768)
            oracle.write(0xcb2b9,camera,2);expected=oracle.run(control,a);ecamera=oracle.read(0xcb2b9,2)
            for d in libs:
                actual=clone(a);value=I16(camera)
                assert d.tomb_directional_jump_control(C.byref(actual),C.byref(value))
                assert state(actual)==state(expected) and value.value==ecamera
        for i in range(4000):
            a=Actor(x=rng.randint(-2147483648,2147483647),y=rng.randint(-2147483648,2147483647),z=rng.randint(-2147483648,2147483647),current=mode,goal=rng.randrange(56),animation=77,frame=123,speed=rng.choice(edges),fall_speed=rng.choice(edges),yaw=rng.randrange(-32768,32768),room=7,flags=rng.randrange(256))
            c=Contact(floor=rng.choice(edges),shift_x=8,shift_y=-5,shift_z=2,old_x=123,old_y=456,old_z=789,type=rng.choice([0,1,2,4,8,16,32,64,-1]),flags=rng.randrange(256))
            move=rng.randrange(-32768,32768);oracle.write(0xce9ce,move,2);oracle.dead=rng.randrange(2)
            expected=oracle.run(collision,a,c);ec=oracle.get(COLL,Contact,CONTACT);em=oracle.read(0xce9ce,2);ee=oracle.events[:]
            for d in libs:
                events=[]
                @QUERY
                def query(_,pa,pc,h):events.append(('query',state(pa.contents),state(pc.contents),h))
                @ACTION
                def land(_,pa,pc):
                    events.append(('land',state(pa.contents),state(pc.contents)));pa.contents.x=wrap32(pa.contents.x+17);return oracle.dead
                ctx=Air(query,land,None,oracle.sine,move);actual=clone(a);contact=clone(c)
                assert d.tomb_directional_jump_collision(C.byref(actual),C.byref(contact),C.byref(ctx))
                assert state(actual)==state(expected),(mode,i,state(actual),state(expected))
                assert state(contact)==state(ec) and ctx.move_angle==em and events==ee
    report=dict(control=6000,collision=12000,builds=2,scope='Isolated original states 25/26/27, with query and landing services doubled; no full-frame equivalence.',sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/air.c',ROOT/'src/air.h',Path(__file__)]})
    (ROOT/'analysis/c-directional-jump-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: 18000 directional-jump control/collision cases per build')
if __name__=='__main__':main()
