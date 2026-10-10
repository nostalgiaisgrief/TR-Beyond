"""Execute DOS GunControl with targeting/ray services doubled on both sides.
Draw, holster, linked-arm aim/pump and sound timing remain DOS.
Targeting and six-pellet emission are isolated service boundaries.
"""
from compare_objects import *
class Arm(C.Structure):_fields_=[(n,I16) for n in ('frame','lock','yaw','pitch','roll','flash')]
class Pistols(C.Structure):
    _fields_=[('left',Arm),('right',Arm)]+[(n,I16) for n in ('status','head_yaw','head_pitch','torso_yaw','torso_pitch','target_yaw','target_pitch')]+[('target',C.c_int),('drawn',C.c_int)]+[(n,C.c_uint32) for n in ('random','shots','hits','kills')]
FIRE=C.CFUNCTYPE(C.c_int,C.c_void_p,I16,I16)
SOUND=C.CFUNCTYPE(None,C.c_void_p,C.c_int)
class ShotgunOracle(ObjectOracle):
    def __init__(self):
        super().__init__();self.fired=[];self.target=0
        self.allowed.update(range(0xce966,0xcea28));self.allowed.add(0xcb298)
        self.allowed.update(range(0xc19a4,0xc19a8))
        for fn in (0x2a8c0,0x2aa58,0x2ada0):self.uc.hook_add(UC_HOOK_CODE,self.gun,begin=fn,end=fn)
        self.write(0xce960,ITEM,4);self.write(0xcc044,DATA,4)
        self.write(0xcc0c4,0,4);self.write(0xcc0cc,0,4);self.write(0xcc060,0,4);self.write(0xcc128,0,4)
    def gun(self,u,addr,size,data):
        if addr==0x2ada0:
            at=u.reg_read(UC_X86_REG_ECX);self.fired.append((self.read(at,2),self.read(at+2,2)));self.ret(1)
        else:self.write(0xce9c4,self.target,4);self.ret()
def main():
    o=ShotgunOracle()
    def shotgun(u,addr,size,data):
        o.fired.append((o.read(0xce9e4,2),o.read(0xce9e6,2)))
        o.events.append((5,3))
        o.ret()
    o.uc.hook_add(UC_HOOK_CODE,shotgun,begin=0x2b7d4,end=0x2b7d4)
    results=[]
    for suffix in ('','_debug'):
        rng=random.Random(19961013);d=C.CDLL(str(ROOT/'build'/f'step_test{suffix}.dll'))
        d.tomb_shotgun_tick.argtypes=[C.POINTER(Pistols),C.c_int,C.c_int,C.c_int,C.c_int,FIRE,SOUND,C.c_void_p]
        fire=[];sounds=[]
        @FIRE
        def shot(user,yaw,pitch):fire.append((yaw,pitch));return 1
        @SOUND
        def sound(user,id):sounds.append(id)
        cases=0
        for _ in range(8000):
            g=Pistols();g.target=rng.choice([-1,3]);g.status=rng.randrange(5)
            g.target_yaw=rng.randrange(-32768,32768);g.target_pitch=rng.randrange(-16000,16001)
            for arm in (g.left,g.right):
                arm.frame=rng.randrange(127);arm.lock=rng.randrange(2);arm.yaw=rng.randrange(-30000,30001);arm.pitch=rng.randrange(-14000,14001);arm.flash=rng.randrange(4)
            for name,addr in [('status',0xce966),('head_yaw',0xce9d0),('head_pitch',0xce9d2),('torso_yaw',0xce9d6),('torso_pitch',0xce9d8),('target_yaw',0xce9c8),('target_pitch',0xce9ca)]:o.write(addr,getattr(g,name),2)
            for arm,at in [(g.left,0xce9e0),(g.right,0xce9f0)]:o.uc.mem_write(at,bytes(arm))
            toggle,action,alive,water=[rng.randrange(2) for _ in range(4)]
            o.target=0 if g.target<0 else ITEMS+3*68;o.write(0xce9c4,o.target,4)
            for addr,val,w in [(ITEM+0x22,1000 if alive else 0,2),(ITEM+0x3e,0,2),(0xce968,4,2),(0xce96a,4,2),(0xce96e,water,2),(0xce92c,toggle*32+action*64,4)]:o.write(addr,val,w)
            fire.clear();sounds.clear();o.fired=[];o.events=[]
            o.call(0x2a460,0,0,0,0);d.tomb_shotgun_tick(C.byref(g),toggle,action,alive,water,shot,sound,None)
            for arm,at in [(g.left,0xce9e0),(g.right,0xce9f0)]:assert bytes(arm)==bytes(o.uc.mem_read(at,12)),(_,state(arm),state(Arm.from_buffer_copy(o.uc.mem_read(at,12))))
            for name,addr in [('status',0xce966),('head_yaw',0xce9d0),('head_pitch',0xce9d2),('torso_yaw',0xce9d6),('torso_pitch',0xce9d8)]:assert getattr(g,name)==o.read(addr,2),(_,name,getattr(g,name),o.read(addr,2))
            assert fire==o.fired and sounds==[e[1] for e in o.events],(_,fire,o.fired,sounds,o.events)
            cases+=1
        spread=ShotgunOracle();d.tomb_shotgun_spread.argtypes=[C.POINTER(C.c_uint32),I16,I16,C.POINTER(I16)]
        for case in range(1500):
            yaw=rng.randrange(-32768,32768);pitch=rng.randrange(-16000,16001);seed=C.c_uint32(rng.getrandbits(32))
            spread.write(ITEM+0x3e,0,2);spread.write(0xce9e4,yaw,2);spread.write(0xce9e6,pitch,2);spread.write(0xce9c4,0,4)
            spread.write(0xc19a4,seed.value,4);spread.fired=[];spread.events=[]
            spread.call(0x2b7d4,0,0,0,0)
            pairs=[]
            for pellet in range(6):
                angles=(I16*2)();d.tomb_shotgun_spread(C.byref(seed),yaw,pitch,angles);pairs.append(tuple(angles))
            assert pairs==spread.fired,(case,pairs,spread.fired)
            assert seed.value==spread.read(0xc19a4,4)&0xffffffff
        results.append(dict(build=suffix or 'release',shotgun_control_cases=cases,six_pellet_spread_cases=1500))
    (ROOT/'analysis/shotgun-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS shotgun draw/holster/aim/pump/sound',results)
if __name__=='__main__':main()
