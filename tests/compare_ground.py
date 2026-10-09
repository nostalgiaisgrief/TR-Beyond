"""Ground handler/damping differential checks against the supplied DOS code."""
import ctypes as C
import json,random,time
from compare_step import *
class Movement(C.Structure):
    _fields_=[('input',C.c_uint32)]+[(n,I16) for n in ('health','current_state','goal_state','animation','frame','turn_rate','lean')]+[('item_flags',U8),('weapon_status',I16)]+[(n,I16) for n in ('head_yaw','head_pitch','torso_yaw','torso_pitch')]+[('camera_mode',U8)]
class Ground(C.Structure):
    _fields_=[('walk',WalkContext),('front_floor',I32),('front_type',I32),('lean',I16)]
def main():
    oracle=Oracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    oracle.allowed.update([ITEM+0x40,ITEM+0x41,0xce9cc,0xce9cd])
    libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for dll in libs:
        dll.tomb_ground_collision.argtypes=[C.c_int,C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Ground)]
        dll.tomb_ground_damping.argtypes=[C.POINTER(Movement),C.POINTER(Actor)]
    rng=random.Random(19961008); edges=[-32768,-2002,-365,-364,-363,-183,-182,-181,-1,0,1,181,182,183,363,364,365,2002,32767]
    for i in range(6000):
        rate=rng.choice(edges) if i<3000 else rng.randrange(-32768,32768)
        lean=rng.choice(edges) if i<3000 else rng.randrange(-32768,32768)
        yaw=rng.randrange(-32768,32768)
        oracle.write(ITEM+0x3e,yaw,2); oracle.write(ITEM+0x40,lean,2); oracle.write(0xce9cc,rate,2)
        oracle.uc.reg_write(UC_X86_REG_EBX,ITEM); oracle.bad=[]
        oracle.uc.emu_start(0x25089,0x2511b,count=200)
        assert not oracle.bad
        expected=(oracle.read(ITEM+0x3e,2),oracle.read(ITEM+0x40,2),oracle.read(0xce9cc,2))
        for dll in libs:
            a=Actor(yaw=yaw); m=Movement(turn_rate=rate,lean=lean)
            dll.tomb_ground_damping(C.byref(m),C.byref(a))
            assert (a.yaw,m.lean,m.turn_rate)==expected
    functions={21:0x26b4c,22:0x26c08,45:0x27070,23:0x27140,1:0x26234,2:0x263b8,6:0x26618,7:0x26618,20:0x263b8,12:0x26918,16:0x26a28,5:0x26540}
    for i in range(18000):
        mode=rng.choice(list(functions)); initial_lean=rng.randrange(-32768,32768)
        a=Actor(x=rng.randrange(-100000,100000),y=rng.randrange(-100000,100000),z=rng.randrange(-100000,100000),
                current=mode,goal=mode,animation=0,frame=rng.choice([-1,0,3,9,10,14,21,22,100,963,964,993,994]),speed=47,fall_speed=55,yaw=rng.randrange(-32768,32768),room=7,flags=rng.randrange(256))
        c=Contact(floor=rng.choice([-32512,-641,-384,-129,-128,0,49,50,100,101,128,129,199,200,201,383,384,385]),positive_limit=99,negative_limit=-99,ceiling_limit=3,
                  shift_x=8,shift_y=-5,shift_z=2,old_x=123,old_y=456,old_z=789,facing=42,type=rng.choice([0,1,2,4,8,16,32]),flags=rng.randrange(256))
        front=rng.choice([-641,-640,-639,0]); typ=rng.choice([0,1,2]); move=rng.randrange(-32768,32768)
        oracle.vault=rng.randrange(2); oracle.slide=rng.randrange(2)
        # Oracle.put initializes unrepresented bytes: supply front sample/lean after it.
        original_put=oracle.put
        def put(base,value,fields):
            original_put(base,value,fields)
            if base==ITEM: oracle.write(ITEM+0x40,initial_lean,2)
            if base==COLL: oracle.write(COLL+0xc,front,4); oracle.write(COLL+0x14,typ,4)
        oracle.put=put; oracle.write(0xce9ce,move,2)
        expected=oracle.run(functions[mode],a,c)
        expected_c=oracle.get(COLL,Contact,CONTACT); expected_lean=oracle.read(ITEM+0x40,2)
        expected_move=oracle.read(0xce9ce,2); expected_events=oracle.events[:]
        oracle.put=original_put
        for dll in libs:
            events=[]
            @QUERY
            def query(_,pa,pc,height): events.append(('query',state(pa.contents),state(pc.contents),height))
            def action(label,result):
                @ACTION
                def call(_,pa,pc):
                    events.append((label,state(pa.contents),state(pc.contents)))
                    if result: pa.contents.x=wrap32(pa.contents.x+17)
                    return result
                return call
            vault=action('vault',oracle.vault); slide=action('slide',oracle.slide)
            context=Ground(WalkContext(query,vault,slide,None,move),front,typ,initial_lean)
            actual=clone(a); contact=clone(c)
            assert dll.tomb_ground_collision(mode,C.byref(actual),C.byref(contact),C.byref(context))
            assert state(actual)==state(expected),(i,mode,state(actual),state(expected))
            assert state(contact)==state(expected_c)
            assert (context.lean,context.walk.move_angle)==(expected_lean,expected_move)
            assert events==expected_events
    (ROOT/'analysis/c-ground-validation.json').write_text(json.dumps(dict(damping_cases_per_build=6000,collision_cases_per_build=18000,builds=2,
        scope='Original damping block and ground collision routines. Query, vault and slide are controlled doubles; no full-frame equivalence.'),indent=2)+'\n')
    print('PASS: 6000 original damping + 18000 original ground collision cases per build')
if __name__=='__main__': main()
