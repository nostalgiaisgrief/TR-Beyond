"""Ledge catches/reach against DOS, with animation-bound and world services doubled."""
from compare_air import *
BOUNDS=C.CFUNCTYPE(I16,C.c_void_p,C.POINTER(Actor))
SWING=C.CFUNCTYPE(C.c_int,C.c_void_p,C.POINTER(Actor),I16)
class Samples(C.Structure):
    _fields_=[(n,I32) for n in ('ceiling','front_floor','front_ceiling','left_floor','right_floor')]
class Grab(C.Structure):
    _fields_=[('input',C.c_uint32),('weapon_status',I16),('bounds_min_y',BOUNDS),('swing_space',SWING),('user',C.c_void_p)]
class LedgeOracle(AirOracle):
    def __init__(self):
        super().__init__(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
        self.allowed.update([0xcb2b9,0xcb2ba]);self.samples=Samples();self.bounds=[-700,-720];self.swing=0;self.catch_double=False;self.catch=0
        for a in [0x1d444,0x27ee4,0x27d4c]:self.uc.hook_add(UC_HOOK_CODE,self.external,begin=a,end=a)
    def put(self,base,s,fields):
        super().put(base,s,fields)
        if base==COLL:
            for n,off in [('ceiling',4),('front_floor',12),('front_ceiling',16),('left_floor',24),('right_floor',36)]:self.write(base+off,getattr(self.samples,n),4)
    def external(self,uc,address,size,data):
        if address==0x27d4c:
            if self.catch_double:
                self.events.append(('grab',state(self.get(ITEM,Actor,ACTOR)),state(self.get(COLL,Contact,CONTACT))));self.ret(self.catch)
            return
        if address==0x1d444:
            count=sum(e[0]=='bounds' for e in self.events)
            self.events.append(('bounds',state(self.get(ITEM,Actor,ACTOR))))
            self.write(DATA+4,self.bounds[min(count,1)],2);self.ret(DATA);return
        if address==0x27ee4:
            self.events.append(('swing',state(self.get(ITEM,Actor,ACTOR)),C.c_int16(uc.reg_read(UC_X86_REG_EDX)).value));self.ret(self.swing);return
        super().external(uc,address,size,data)
def main():
    oracle=LedgeOracle();libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for d in libs:
        d.tomb_ledge_grab.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Samples),C.POINTER(Grab),C.c_int]
        d.tomb_reach_control.argtypes=[C.POINTER(Actor),C.POINTER(I16)]
        d.tomb_reach_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Air),ACTION]
    rng=random.Random(19961014);angles=[-32768,-26398,-26397,-26396,-22755,-22754,-16384,-10014,-10013,-6371,-6370,0,6370,6371,10013,10014,16384,22754,22755,26396,26397,26398,32767]
    passed=[0,0]
    for forward in [0,1]:
        for i in range(12000):
            a=Actor(x=rng.choice([-2147483648,0,2147483647]),y=rng.choice([-2147483648,-1000,2147483647]),z=789,current=11 if forward else 28,goal=3,animation=91,frame=1461,speed=40,fall_speed=rng.choice([-32768,-100,-1,0,1,100,32767]),yaw=rng.choice(angles),flags=rng.randrange(256))
            c=Contact(floor=rng.choice([199,200,201,1000]),type=rng.choice([1,1,1,1,0,2]),shift_x=7,shift_y=123,shift_z=-9)
            oracle.bounds=[rng.choice([-32768,-700,0,32767]),rng.choice([-32768,-720,0,32767])]
            front=wrap32(oracle.bounds[0]+rng.choice([-100,-1,0,0,0,1,100]));left=rng.choice([-2147483648,-1000,0,2147483647])
            s=Samples(rng.choice([-385,-384,-384,-383]),front,rng.choice([-1,0,0,1]),left,wrap32(left+rng.choice([-60,-59,0,59,60,-2147483648])))
            inp=rng.choice([0,64,64,64,0xffffffff]);weapon=rng.choice([0,0,0,1,4]);oracle.samples=s;oracle.swing=rng.randrange(2)
            oracle.write(0xce92c,inp,4);oracle.write(0xce966,weapon,2)
            expected=oracle.run(0x27d4c if forward else 0x27fa0,a,c);result=oracle.uc.reg_read(UC_X86_REG_EAX);ew=oracle.read(0xce966,2);ee=oracle.events[:];passed[forward]+=result
            for d in libs:
                events=[]
                @BOUNDS
                def bounds(_,pa):
                    count=sum(e[0]=='bounds' for e in events);events.append(('bounds',state(pa.contents)));return oracle.bounds[min(count,1)]
                @SWING
                def swing(_,pa,yaw):events.append(('swing',state(pa.contents),yaw));return oracle.swing
                ctx=Grab(inp,weapon,bounds,swing,None);actual=clone(a);contact=clone(c)
                actual_result=d.tomb_ledge_grab(C.byref(actual),C.byref(contact),C.byref(s),C.byref(ctx),forward)
                assert actual_result==result and state(actual)==state(expected),(forward,i,state(actual),state(expected),actual_result,result)
                assert ctx.weapon_status==ew and events==ee and state(contact)==state(c),(forward,i,events,ee)
    assert min(passed)>100,passed
    oracle.catch_double=True
    for i in range(6000):
        a=Actor(x=2147483640,y=-1000,z=-2147483648,current=11,goal=rng.randrange(56),animation=77,frame=123,speed=rng.choice([-32768,-1,0,1,32767]),fall_speed=rng.choice([-32768,0,1,131,132,154,32767]),yaw=rng.randrange(-32768,32768),room=7,flags=rng.randrange(256))
        expected_control=oracle.run(0x25778,a);camera=oracle.read(0xcb2b9,2)
        c=Contact(floor=rng.choice([-1,0,1]),shift_x=9,shift_y=-3,shift_z=7,type=rng.choice([0,1,2,4,8,16,32]),flags=rng.randrange(256))
        oracle.catch=rng.randrange(2);oracle.dead=rng.randrange(2);move=rng.randrange(-32768,32768);oracle.write(0xce9ce,move,2)
        expected=oracle.run(0x2686c,a,c);ec=oracle.get(COLL,Contact,CONTACT);em=oracle.read(0xce9ce,2);ee=oracle.events[:]
        for d in libs:
            actual=clone(a);cam=I16();d.tomb_reach_control(C.byref(actual),C.byref(cam));assert state(actual)==state(expected_control) and cam.value==camera
            events=[]
            @QUERY
            def query(_,pa,pc,h):events.append(('query',state(pa.contents),state(pc.contents),h))
            @ACTION
            def grab(_,pa,pc):events.append(('grab',state(pa.contents),state(pc.contents)));return oracle.catch
            @ACTION
            def land(_,pa,pc):
                events.append(('land',state(pa.contents),state(pc.contents)));pa.contents.x=wrap32(pa.contents.x+17);return oracle.dead
            actual=clone(a);contact=clone(c);ctx=Air(query,land,None,oracle.sine,move)
            assert d.tomb_reach_collision(C.byref(actual),C.byref(contact),C.byref(ctx),grab)
            assert state(actual)==state(expected) and state(contact)==state(ec) and ctx.move_angle==em and events==ee
    report=dict(grab_cases=24000,successful_grabs=passed,reach_control=6000,reach_collision=6000,builds=2,scope='Isolated DOS comparisons with animation bounds, swing-space, world query and landing service doubles. Action/grabbing is not enabled in preview.',sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/ledge.c',ROOT/'src/ledge.h',Path(__file__)]})
    (ROOT/'analysis/c-ledge-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS: 36000 ledge/reach cases per build; successful catches:',passed)
if __name__=='__main__':main()
