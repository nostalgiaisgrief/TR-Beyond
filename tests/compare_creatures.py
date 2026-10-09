"""Species controllers against original instructions. Navigation, sphere contacts,
and animation are isolated inputs/services; this does not validate navigation.
"""
from compare_objects import *
class Info(C.Structure):_fields_=[('zone',I16),('enemy_zone',I16)]+[(n,I32) for n in ('distance','ahead','bite')]+[('angle',I16),('enemy_facing',I16)]
class Creature(C.Structure):_fields_=[(n,I16) for n in ('health','required','head','maximum_turn','flags','pitch','roll')]+[('mood',U8),('touch',C.c_uint32)]+[(n,I32) for n in ('floor','target_x','target_y','target_z')]
class Decision(C.Structure):_fields_=[(n,I16) for n in ('damage','turn','tilt','blood')]
CREATURE=DOORS
class CreatureOracle(ObjectOracle):
    def __init__(self):
        super().__init__();self.info=Info();self.turn=0;self.blood=0;self.motion=None
        self.allowed.update(range(0xc19a4,0xc19a8))
        for addr in [0x11674,0x11eb4,0x133c0,0x13500,0x12910]:self.uc.hook_add(UC_HOOK_CODE,self.creature,begin=addr,end=addr)
    def creature(self,u,addr,size,data):
        if addr==0x11674:self.uc.mem_write(u.reg_read(UC_X86_REG_EDX),bytes(self.info));self.ret()
        elif addr==0x11eb4:self.ret()
        elif addr==0x133c0:self.ret(self.turn&65535)
        elif addr==0x13500:self.blood+=1;self.ret()
        else:self.motion=(C.c_int16(u.reg_read(UC_X86_REG_EDX)).value,C.c_int16(u.reg_read(UC_X86_REG_EBX)).value);self.ret(1)
def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=CreatureOracle();o.install(f);o.write(0xce960,ITEM,4);o.write(0xcc060+7*50+36,172,2);results=[]
    for suffix in ('','_debug'):
        rng=random.Random(19961014);d=bind(ROOT/'build'/f'step_test{suffix}.dll')
        d.tomb_creature_control.argtypes=[C.POINTER(Object),C.POINTER(Creature),C.POINTER(Info),I16,I16,C.POINTER(C.c_uint32),C.POINTER(AnimContext)];d.tomb_creature_control.restype=Decision
        err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);lv=l.contents
        ctx=AnimContext();ctx.animations=lv.animations;ctx.animation_count=lv.animation_count
        counts={}
        for id,fn in [(7,0x3cdc4),(8,0x111e8),(9,0x11060)]:
            for n in range(4000):
                st=rng.randrange(13 if id==7 else 10 if id==8 else 6)
                a=Actor(1000,0,2000,st,rng.randrange(13),172,96,20,0,1234,0,35|rng.choice([0,16]))
                ob=Object(a,0,0,id,1);c=Creature(rng.choice([-1,0,1,20]),rng.choice([0,0,0,1,3,5,9]),rng.randrange(-16384,16385),182,rng.randrange(2),0,rng.randrange(-3000,3001),rng.randrange(4),rng.choice([0,0,0xffffffff,rng.getrandbits(26)]),rng.choice([-100,100]),0,0,0)
                info=Info(rng.randrange(3),rng.randrange(3),rng.choice([rng.randrange(0x1000000),0x1d0f0,0x1d0f1,0x240000,0x120000,0x900000,0x400000,0x57e40]),rng.randrange(2),rng.randrange(2),rng.randrange(-32768,32768),rng.choice([-16385,-16384,-16383,16383,16384,16385]))
                health=rng.choice([-10,0,1000]);seed=C.c_uint32(rng.getrandbits(32));turn=rng.randrange(-910,911)
                o.put_object(ob);o.uc.mem_write(CREATURE,bytes(59));o.write(ITEMS+0x2c,CREATURE,4)
                for at,val,w in [(ITEMS+0x22,c.health,2),(ITEMS+0x12,c.required,2),(ITEMS+4,c.touch,4),(ITEMS,c.floor,4),(ITEMS+0x40,c.roll,2),(CREATURE,c.head,2),(CREATURE+4,c.maximum_turn,2),(CREATURE+6,c.flags,2),(CREATURE+10,c.mood,1),(ITEM+0x22,health,2),(ITEM+0x42,0,1),(0xc19a4,seed.value,4)]:o.write(at,val,w)
                o.info=info;o.turn=turn;o.blood=0;o.motion=None;o.call(fn,0,0,0,0)
                result=d.tomb_creature_control(C.byref(ob),C.byref(c),C.byref(info),turn,health,C.byref(seed),C.byref(ctx));o.compare(ob)
                for name,at,w in [('required',ITEMS+0x12,2),('head',CREATURE,2),('maximum_turn',CREATURE+4,2),('flags',CREATURE+6,2),('mood',CREATURE+10,1),('roll',ITEMS+0x40,2)]:assert getattr(c,name)==o.read(at,w),(id,n,name,getattr(c,name),o.read(at,w))
                assert (result.damage,result.turn,result.tilt,result.blood)==(health-o.read(ITEM+0x22,2),*o.motion,o.blood),(id,n,state(result),health-o.read(ITEM+0x22,2),o.motion,o.blood)
                assert seed.value==o.read(0xc19a4,4)&0xffffffff,(id,n,'random')
            counts[id]=4000
        d.tomb_level_free(l);results.append(dict(build=suffix or 'release',controller_cases=counts))
    (ROOT/'analysis/creature-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS species decisions',results)
if __name__=='__main__':main()
