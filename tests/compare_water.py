"""Vault and water routines compared with hash-pinned original DOS instructions.
World queries, room changes and animation advance are explicit service doubles.
"""
from compare_ledge import *
ROOM=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Actor),I32)
HEIGHT=C.CFUNCTYPE(I16,C.c_void_p,C.POINTER(Actor))
class Water(C.Structure):
    _fields_=[('input',C.c_uint32)]+[(n,I16) for n in ('health','pitch','lean','status','dive_count','move_angle','weapon_status','air')]+[('query',QUERY),('room',ROOM),('height',HEIGHT),('user',C.c_void_p),('sine',C.POINTER(I16))]
class Vault(C.Structure):
    _fields_=[('input',C.c_uint32),('weapon_status',I16),('fall_override',I16),('left_ceiling',I32),('right_ceiling',I32),('advance',ADVANCE),('user',C.c_void_p)]
class WaterOracle(LedgeOracle):
    def __init__(self):
        super().__init__(); self.water=Water(); self.left=-1000;self.right=-1000;self.height=0;self.transition=False
        for addr in [0x28820,0x15fb8,0x17570,0x2dc00,0x1dc08]: self.uc.hook_add(UC_HOOK_CODE,self.external,begin=addr,end=addr)
        for addr,width in [(ITEM+0x3c,2),(ITEM+0x40,2),(ITEM+0x22,2),(0xce96e,2),(0xce978,2),(0xcb298,1)]:self.allowed.update(range(addr,addr+width))
    def put(self,base,s,fields):
        super().put(base,s,fields)
        if base==ITEM:
            self.write(ITEM+0x3c,self.water.pitch,2);self.write(ITEM+0x40,self.water.lean,2);self.write(ITEM+0x22,self.water.health,2)
        if base==COLL:self.write(COLL+28,self.left,4);self.write(COLL+40,self.right,4)
    def external(self,uc,address,size,data):
        if address in (0x2dc00,0x1dc08) or (self.transition and address==0x2d2b4):self.ret();return
        if address==0x27b44:return # Execute the actual vault.
        if address==0x28820:
            self.events.append(('animate',state(self.get(ITEM,Actor,ACTOR)),self.read(0xce96c,2)))
            self.write(ITEM+0x30,self.read(ITEM+0x30,4)+17,4);self.ret();return
        if address==0x15fb8:
            self.events.append(('room',state(self.get(ITEM,Actor,ACTOR)),C.c_int32(uc.reg_read(UC_X86_REG_EDX)).value))
            self.write(ITEM+0x18,8,2);self.ret();return
        if address==0x17570:self.ret(self.height&65535);return
        if address==0x151c0:
            a=self.get(ITEM,Actor,ACTOR);c=self.get(COLL,Contact,CONTACT);sp=uc.reg_read(UC_X86_REG_ESP);h=self.read(sp+8,4)
            assert h in (400,700) and self.read(sp+4,4)==a.room
            assert C.c_int32(uc.reg_read(UC_X86_REG_EBX)).value==wrap32(a.y+(200 if h==400 else 700))
            self.events.append(('query',state(a),state(c),h));self.ret(pop=8);return
        super().external(uc,address,size,data)
    def setup(self,w):
        self.water=w
        for off,n,width in [(0xce92c,'input',4),(0xce966,'weapon_status',2),(0xce96e,'status',2),(0xce978,'dive_count',2),(0xce9ce,'move_angle',2)]:self.write(off,getattr(w,n),width)
        self.write(0xcb298,0,1)
    def result_water(self):
        return (self.read(ITEM+0x3c,2),self.read(ITEM+0x40,2),self.read(0xce96e,2),self.read(0xce978,2),self.read(0xce9ce,2),self.read(0xce966,2))
def ws(w):return (w.pitch,w.lean,w.status,w.dive_count,w.move_angle,w.weapon_status)
def main():
    o=WaterOracle();ds=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for d in ds:
        d.tomb_water_control.argtypes=[C.POINTER(Actor),C.POINTER(Water),C.c_int]
        d.tomb_underwater_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Water)]
        d.tomb_water_exit.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Samples),C.POINTER(Water)]
        d.tomb_surface_collision.argtypes=d.tomb_water_exit.argtypes
        d.tomb_vault.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Samples),C.POINTER(Vault)]
    rng=random.Random(19961018);cases=0
    for state_id,addr in [(13,0x2975c),(17,0x295f8),(18,0x296a4),(35,0x29804),(33,0x29f64),(34,0x29dc4),(47,0x29e38),(48,0x29e9c),(49,0x29f00)]:
        for i in range(1500):
            a=Actor(current=state_id,goal=rng.randrange(56),fall_speed=rng.choice([-32768,-1,0,59,60,132,133,199,200,32767]),yaw=rng.randrange(-32768,32768))
            w=Water(input=rng.getrandbits(12)&~512,health=rng.choice([-1,0,1000]),pitch=rng.randrange(-32768,32768),lean=rng.randrange(-32768,32768),status=2 if state_id>=33 and state_id!=35 else 1,dive_count=rng.choice([0,9,10,11,32767]),move_angle=123)
            o.setup(w);expected=o.run(addr,a);ew=o.result_water()
            for d in ds:
                ac=clone(a);wc=clone(w);assert d.tomb_water_control(C.byref(ac),C.byref(wc),state_id in (33,34,47,48,49));assert state(ac)==state(expected) and ws(wc)==ew,(state_id,i,state(ac),state(expected),ws(wc),ew)
            cases+=1
    for mode in range(3):
        for i in range(4000):
            a=Actor(x=rng.choice([-2147483648,123,2147483647]),y=1000,z=789,current=17 if mode==0 else 33,goal=33,fall_speed=140,yaw=rng.choice([-32768,-16384,-6371,-6370,0,6370,6371,16384,27300]),room=7,flags=8)
            c=Contact(floor=rng.choice([-1,0,100]),type=rng.choice([0,1,1,1,2,4,8,16,32]),shift_x=7,shift_y=9,shift_z=-3,old_x=100,old_y=1010,old_z=800)
            s=Samples(rng.choice([-385,-384,-383]),rng.choice([-1212,-1211,-700,-600,-599]),rng.choice([-1,0,1]),-700,rng.choice([-760,-759,-700,-641,-640]))
            w=Water(input=rng.choice([0,64,64]),health=1000,pitch=rng.choice([-32768,-16385,-16384,-8191,-8190,-6371,0,6371,16384,16385,32767]),lean=123,status=1 if mode==0 else 2,move_angle=a.yaw if i%5 else 5000,weapon_status=0)
            o.samples=s;o.height=rng.choice([900,901,1000,1001]);o.setup(w)
            expected=o.run([0x298d4,0x2a27c,0x2a19c][mode],a,c);ew=o.result_water();ec=o.get(COLL,Contact,CONTACT);ee=o.events[:];result=o.uc.reg_read(UC_X86_REG_EAX)
            for d in ds:
                events=[]
                @QUERY
                def query(_,pa,pc,h):events.append(('query',state(pa.contents),state(pc.contents),h))
                @ROOM
                def room(_,pa,off):events.append(('room',state(pa.contents),off));pa.contents.room=8
                @HEIGHT
                def height(_,pa):return o.height
                ac=clone(a);cc=clone(c);wc=clone(w);wc.query=query;wc.room=room;wc.height=height
                if mode==0:d.tomb_underwater_collision(C.byref(ac),C.byref(cc),C.byref(wc))
                elif mode==1:assert d.tomb_water_exit(C.byref(ac),C.byref(cc),C.byref(s),C.byref(wc))==result
                else:d.tomb_surface_collision(C.byref(ac),C.byref(cc),C.byref(s),C.byref(wc))
                assert state(ac)==state(expected) and ws(wc)==ew and state(cc)==state(ec) and events==ee,(mode,i,state(ac),state(expected),ws(wc),ew,events,ee)
            cases+=1
    # Fixed-point motion and pitch/lean damping: execute exact original instruction spans.
    for d in ds:
        d.tomb_water_motion.argtypes=[C.POINTER(Actor),C.POINTER(Water),C.c_int]
        d.tomb_water_damping.argtypes=[C.POINTER(Water),C.c_int]
    for surface in (0,1):
        for i in range(4000):
            a=Actor(x=rng.randrange(-2147483648,2147483648),y=rng.randrange(-2147483648,2147483648),z=rng.randrange(-2147483648,2147483648),yaw=rng.randrange(-32768,32768),fall_speed=rng.randrange(-32768,32768))
            w=Water(pitch=rng.randrange(-32768,32768),lean=rng.randrange(-32768,32768),move_angle=rng.randrange(-32768,32768),sine=o.sine)
            o.setup(w);o.put(ITEM,a,ACTOR);o.uc.reg_write(UC_X86_REG_EBX,ITEM);o.uc.reg_write(UC_X86_REG_ESP,STACK+0x800);o.bad=[]
            begin,end=(0x29d45,0x29d86) if surface else (0x29532,0x295b3)
            o.uc.emu_start(begin,end,count=1000);assert not o.bad
            expected=o.get(ITEM,Actor,ACTOR)
            for d in ds:
                ac=clone(a);d.tomb_water_motion(C.byref(ac),C.byref(w),surface);assert state(ac)==state(expected),(surface,i,state(ac),state(expected))
            o.put(ITEM,a,ACTOR);o.uc.reg_write(UC_X86_REG_EBX,ITEM);o.bad=[]
            begin,end=(0x29c29,0x29c69) if surface else (0x2948b,0x29510)
            o.uc.emu_start(begin,end,count=1000);assert not o.bad
            ep,el=o.read(ITEM+0x3c,2),o.read(ITEM+0x40,2)
            for d in ds:
                wc=clone(w);d.tomb_water_damping(C.byref(wc),surface);assert (wc.pitch,wc.lean)==(ep,el)
            cases+=2
    # Main Lara water-state transition span; cosmetic splash/music services doubled.
    o.transition=True
    o.allowed.update(range(0xce9d0,0xce9da));o.allowed.update(range(0xce976,0xce978))
    o.write(0xce960,ITEM,4);o.write(0xcc058,DATA,4)
    for d in ds:d.tomb_water_transition.argtypes=[C.POINTER(Actor),C.POINTER(Water),C.c_int,I16]
    for i in range(6000):
        a=Actor(x=123,y=1000,z=789,current=3,goal=3,animation=34,frame=492,speed=30,fall_speed=rng.randrange(-32768,32768),yaw=1200,room=7,flags=8)
        w=Water(health=1000,pitch=123,lean=456,status=rng.randrange(3),air=777,dive_count=5,weapon_status=1)
        wet=rng.randrange(2);h=rng.choice([-32512,743,744,745,1000,1255,1256,1257]);o.height=h;o.setup(w);o.write(0xce976,w.air,2)
        o.put(ITEM,a,ACTOR);o.write(DATA+7*68+66,wet,2);o.uc.reg_write(UC_X86_REG_ESI,ITEM);o.uc.reg_write(UC_X86_REG_ESP,STACK+0x800);o.events=[];o.bad=[]
        o.uc.emu_start(0x283be,0x286db,count=2000);assert not o.bad,o.bad
        expected=o.get(ITEM,Actor,ACTOR);ew=o.result_water();ea=o.read(0xce976,2);ee=o.events[:]
        for d in ds:
            events=[]
            @ROOM
            def room(_,pa,off):events.append(('room',state(pa.contents),off));pa.contents.room=8
            ac=clone(a);wc=clone(w);wc.room=room
            d.tomb_water_transition(C.byref(ac),C.byref(wc),wet,h)
            assert state(ac)==state(expected) and ws(wc)==ew and wc.air==ea and events==ee,(i,state(ac),state(expected),ws(wc),ew,events,ee)
        cases+=1
    o.transition=False
    passed=0
    for i in range(12000):
        a=Actor(x=2147483640,y=-1000,z=789,current=1,goal=1,animation=0,frame=12,yaw=rng.choice([-32768,-27307,-27306,-21844,-16384,-10924,-5461,-5460,0,5460,5461,10924,16384,21844,27306,27307]))
        c=Contact(type=rng.choice([0,1,1,1]),shift_x=10,shift_y=3,shift_z=-8)
        f=rng.choice([-1921,-1920,-1500,-897,-896,-895,-641,-640,-639,-512,-384,-383])
        s=Samples(-1000,f,f+rng.choice([-1,0,0,1]),-700,rng.choice([-760,-759,-700,-641,-640]))
        w=Water(input=rng.choice([0,64,64,64]),weapon_status=rng.choice([0,0,0,1]));o.setup(w);o.samples=s;o.left=rng.choice([-701,-700,-699]);o.right=rng.choice([-761,-760,-641,-640]);fall=-123;o.write(0xce96c,fall,2)
        expected=o.run(0x27b44,a,c);result=o.uc.reg_read(UC_X86_REG_EAX);ew=o.read(0xce966,2);ef=o.read(0xce96c,2);ee=o.events[:];passed+=result;ec=o.get(COLL,Contact,CONTACT)
        for d in ds:
            events=[]
            @ADVANCE
            def advance(_,pa):events.append(('animate',state(pa.contents),v.fall_override));pa.contents.x=wrap32(pa.contents.x+17);return 1
            v=Vault(w.input,w.weapon_status,fall,o.left,o.right,advance,None);ac=clone(a);cc=clone(c)
            ar=d.tomb_vault(C.byref(ac),C.byref(cc),C.byref(s),C.byref(v));assert ar==result and state(ac)==state(expected) and (v.weapon_status,v.fall_override)==(ew,ef) and events==ee and state(cc)==state(ec),(i,state(ac),state(expected),events,ee)
        cases+=1
    assert passed>500
    (ROOT/'analysis/c-water-vault-validation.json').write_text(json.dumps(dict(cases=cases,builds=2,successful_vaults=passed,scope=__doc__),indent=2)+'\n')
    print('PASS:',cases,'water control/collision/exit and vault cases per build; successful vaults',passed)
if __name__=='__main__':main()
