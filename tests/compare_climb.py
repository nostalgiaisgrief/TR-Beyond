"""Hang/shimmy controls, pull-up clearance and pull-up collision against DOS."""
from compare_hang import *
class Control(C.Structure):
    _fields_=[('input',C.c_uint32),('camera_angle',I16),('camera_elevation',I16)]
class ClimbOracle(HangOracle):
    def __init__(self):
        super().__init__();self.left_ceiling=-900;self.right_ceiling=-900;self.static=0
        self.allowed.update([0xcb2bd,0xcb2be]);self.uc.hook_add(UC_HOOK_CODE,self.external,begin=0x2769c,end=0x2769c)
    def put(self,base,s,fields):
        super().put(base,s,fields)
        if base==COLL:
            self.write(COLL+28,self.left_ceiling,4);self.write(COLL+40,self.right_ceiling,4);self.write(COLL+0x65,self.static,1)
    def external(self,uc,address,size,data):
        if address==0x2769c:self.ret();return
        if address==0x151c0:return AirOracle.external(self,uc,address,size,data)
        super().external(uc,address,size,data)
def main():
    oracle=ClimbOracle();libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for d in libs:
        d.tomb_hang_control.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Control)]
        d.tomb_hang_pullup_goal.argtypes=[C.POINTER(Actor),C.POINTER(Samples),C.c_uint32,I32,I32,C.c_int]
        d.tomb_pullup_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air)]
    rng=random.Random(19961016)
    for mode,address in [(10,0x25728),(30,0x25b00),(31,0x25b38)]:
        for i in range(3000):
            a=Actor(current=mode,goal=rng.randrange(56));c=Contact(flags=rng.randrange(256));inp=rng.getrandbits(32)
            oracle.write(0xce92c,inp,4);expected=oracle.run(address,a,c);ec=oracle.get(COLL,Contact,CONTACT)
            camera=oracle.read(0xcb2b9,2);elevation=oracle.read(0xcb2bd,2)
            for d in libs:
                actual=clone(a);contact=clone(c);control=Control(inp,123,456);d.tomb_hang_control(C.byref(actual),C.byref(contact),C.byref(control))
                assert state(actual)==state(expected) and state(contact)==state(ec) and (control.camera_angle,control.camera_elevation)==(camera,elevation)
    for i in range(12000):
        a=Actor(current=10,goal=rng.choice([10,10,10,30,31]));c=Contact();inp=rng.choice([0,1,129,65,193,0xffffffff])
        floor=rng.choice([-851,-850,-849,-727,-651,-650,-649]);left=rng.choice([-2147483648,-726,2147483647]);right=rng.choice([-2147483648,-726,2147483647])
        s=Samples(-400,floor,floor+rng.choice([-1,0,1]),left,right)
        oracle.samples=s;oracle.left_ceiling=wrap32(left+rng.choice([-1,0,1,-2147483648]));oracle.right_ceiling=wrap32(right+rng.choice([-1,0,1,-2147483648]));oracle.static=rng.choice([0,0,0,1,255]);oracle.write(0xce92c,inp,4)
        expected=oracle.run(0x26800,a,c)
        for d in libs:
            actual=clone(a);d.tomb_hang_pullup_goal(C.byref(actual),C.byref(s),inp,oracle.left_ceiling,oracle.right_ceiling,oracle.static)
            assert state(actual)==state(expected)
    for i in range(6000):
        a=Actor(current=19 if i%2 else 54,x=123,y=-456,z=789,yaw=rng.randrange(-32768,32768),room=7);c=Contact(flags=rng.randrange(256),floor=123,shift_x=5,shift_y=7,shift_z=-3)
        move=rng.randrange(-32768,32768);oracle.write(0xce9ce,move,2)
        expected=oracle.run(0x26b18 if i%2 else 0x27398,a,c);ec=oracle.get(COLL,Contact,CONTACT);em=oracle.read(0xce9ce,2);ee=oracle.events[:]
        for d in libs:
            events=[]
            @QUERY
            def query(_,pa,pc,h):events.append(('query',state(pa.contents),state(pc.contents),h))
            actual=clone(a);contact=clone(c);ctx=Air(query,ACTION(),None,oracle.sine,move);d.tomb_pullup_collision(C.byref(actual),C.byref(contact),C.byref(ctx))
            assert state(actual)==state(expected) and state(contact)==state(ec) and ctx.move_angle==em and events==ee
    (ROOT/'analysis/c-climb-validation.json').write_text(json.dumps(dict(controls=9000,pullup_decisions=12000,pullup_collision=6000,builds=2,scope='Original instructions; maintenance doubled for clearance tail, query doubled for pull-up collision.'),indent=2)+'\n')
    print('PASS: 27000 hang controls/pull-up cases per build')
if __name__=='__main__':main()
