"""Peru controller decisions against the original DOS instructions.

LOS and effect allocation are controlled services. Animation, room swaps and
actual level trigger chains are separately exercised by peru_test.c.
"""
from compare_creatures import *

class PeruOracle(CreatureOracle):
    def creature(self,u,addr,size,data):
        if addr==0x13500:self.blood+=1;self.ret(0xffffffff)
        else:super().creature(u,addr,size,data)

def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL3B.PHD');o=PeruOracle();o.install(f)
    bases={m[0]:m[-1] for m in struct.iter_unpack('<IHHIIH',f['sections']['models']['bytes'])}
    o.write(0xcc060+27*50+36,bases[27],2);o.write(0xce960,ITEM,4)
    target=[0]
    o.uc.hook_add(UC_HOOK_CODE,lambda u,a,n,d:o.ret(target[0]),begin=0x324e0,end=0x324e0)
    rows=[]
    for suffix in ('','_debug'):
        d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256)
        l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL3B.PHD').encode(),err,256);assert l
        ctx=AnimContext();ctx.animations=l.contents.animations;ctx.animation_count=l.contents.animation_count
        d.tomb_larson_control.argtypes=[C.POINTER(Object),C.POINTER(Creature),C.POINTER(Info),I16,C.POINTER(C.c_uint32),C.POINTER(AnimContext),C.c_int,C.c_int]
        d.tomb_larson_control.restype=Decision
        rng=random.Random(19961010)
        for n in range(8000):
            a=Actor(1000,0,2000,rng.randrange(1,8),rng.randrange(1,8),bases[27],0,20,0,1234,0,35)
            ob=Object(a,0,0,27,1);c=Creature(rng.choice([-1,0,1,50]),rng.choice([0,0,1,2,3,4,6]),rng.randrange(-16384,16385),182,0,0,rng.randrange(-3000,3001),rng.randrange(4),0,0,0,0,0)
            info=Info(0,0,rng.choice([0,0x900000,0x3100000,0x3100001,rng.randrange(0x4000000)]),rng.randrange(2),0,rng.randrange(-32768,32768),0)
            turn=rng.randrange(-1092,1093);seed=C.c_uint32(rng.getrandbits(32));target[0]=rng.randrange(2)
            o.put_object(ob);o.uc.mem_write(CREATURE,bytes(59));o.write(ITEMS+0x2c,CREATURE,4)
            for at,value,width in [(ITEMS+0x22,c.health,2),(ITEMS+0x12,c.required,2),(ITEMS+0x40,c.roll,2),(CREATURE,c.head,2),(CREATURE+4,c.maximum_turn,2),(CREATURE+10,c.mood,1),(ITEM+0x22,1000,2),(ITEM+0x42,0,1),(0xc19a4,seed.value,4)]:o.write(at,value,width)
            o.info=info;o.turn=turn;o.blood=0;o.motion=None;o.call(0x327fc,0,0,0,0)
            result=d.tomb_larson_control(C.byref(ob),C.byref(c),C.byref(info),turn,C.byref(seed),C.byref(ctx),bases[27],target[0]);o.compare(ob)
            for name,at,width in [('required',ITEMS+0x12,2),('head',CREATURE,2),('maximum_turn',CREATURE+4,2),('roll',ITEMS+0x40,2)]:assert getattr(c,name)==o.read(at,width),(n,name,getattr(c,name),o.read(at,width),state(ob),state(info),target[0],c.mood)
            # DOS passes zero tilt to CreatureAnimation after applying roll itself.
            assert (result.damage,result.turn,result.blood)==(1000-o.read(ITEM+0x22,2),o.motion[0],o.blood),(n,state(result),o.motion,o.blood)
            assert seed.value==o.read(0xc19a4,4)&0xffffffff,(n,'random')
        d.tomb_mummy_control.argtypes=[C.POINTER(Object),C.POINTER(Creature),C.POINTER(Actor)]
        hook=o.uc.hook_add(UC_HOOK_CODE,lambda u,a,n,x:o.ret(),begin=0x16ff4,end=0x16ff4)
        for n in range(2000):
            a=Actor(1200,0,2400,rng.randrange(3),0,bases[24],0,0,0,rng.randrange(-32768,32768),0,35)
            ob=Object(a,0,0,24,1);c=Creature();c.head=rng.randrange(-16384,16385);c.health=rng.choice([-1,0,18]);c.touch=rng.choice([0,0,1])
            lara=Actor(x=rng.randrange(-10000,10000),z=rng.randrange(-10000,10000))
            o.put_object(ob);o.write(ITEMS+0x2c,CREATURE,4);o.write(CREATURE,c.head,2);o.write(ITEMS+0x22,c.health,2);o.write(ITEMS+4,c.touch,4)
            o.write(ITEM+0x30,lara.x,4);o.write(ITEM+0x38,lara.z,4);o.call(0x3c384,0,0,0,0)
            d.tomb_mummy_control(C.byref(ob),C.byref(c),C.byref(lara));o.compare(ob);assert c.head==o.read(CREATURE,2),(n,'mummy head')
        o.uc.hook_del(hook)
        class Peru(C.Structure):_fields_=[('flip_flags',C.c_uint16*1024),('flipped',C.c_int),('effect',C.c_int),('effect_ticks',C.c_int),('scion_item',C.c_int)]
        w=Objects();peru=Peru();w.peru=C.addressof(peru)
        d.tomb_flip_action.argtypes=[C.POINTER(Objects),C.c_int,C.c_int,C.c_int,C.c_uint16]
        o.allowed.update(range(0xcb374,0xcb3a8));o.write(0xcb298,5,1);o.skip_switch=True
        flipped=[0]
        def flip(u,a,n,x):flipped[0]=1;o.ret()
        hook=o.uc.hook_add(UC_HOOK_CODE,flip,begin=0x18b3c,end=0x18b3c)
        for n in range(4000):
            act=rng.choice([3,4,5]);typ=rng.choice([0,2,6]);flags=rng.randrange(0x4000);before=rng.randrange(0x4000);old=rng.randrange(2)
            peru.flip_flags[0]=before;peru.flipped=old;o.write(0xcb374,before,4);o.write(0xcb3a4,old,4)
            o.write(ITEM,0,4);o.write(ITEM+0x34,0,4);o.write(ITEMS+14,0,2)
            words=[0x8004|(typ<<8),flags]+([0] if typ==2 else [])+[0x8000|(act<<10)]
            o.uc.mem_write(FLOOR,struct.pack('<'+'H'*len(words),*words));flipped[0]=0;o.call(0x17a40,FLOOR,0,0,0)
            got=d.tomb_flip_action(C.byref(w),act,0,typ,flags)
            assert (got,peru.flip_flags[0])==(flipped[0],o.read(0xcb374,4)&65535),(n,act,typ,flags,before,old)
        o.uc.hook_del(hook)
        d.tomb_level_free(l);rows.append(dict(build=suffix or 'release',larson_decisions=8000,mummy_decisions=2000,flip_triggers=4000))
    (ROOT/'analysis/peru-controller-validation.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('PASS: original DOS Larson controller',rows)
if __name__=='__main__':main()
