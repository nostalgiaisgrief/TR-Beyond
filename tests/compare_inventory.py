"""Execute original DOS add/use and pickup instructions; OS/UI list services are doubles."""
from compare_dos_camera import *
class Inventory(C.Structure):
    _fields_=[('counts',I16*11),('scion',I16),('ammo',I32*4),('pickups',C.c_uint),('ticks',C.c_uint),('last_pickup',C.c_int),('pickup_ticks',C.c_int),('quest',I16*8),('chosen',C.c_int)]
def main():
    o=CameraOracle();f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o.install(f);o.install_models(f)
    for a,b in [(0xc2c00,0xc3500),(0xcea00,0xcea30),(0xcefba,0xcefbb),(ITEM,ITEM+68)]:o.allowed.update(range(a,b))
    o.uc.hook_add(UC_HOOK_CODE,lambda *args:o.ret(),begin=0x24d00,end=0x24d00)
    rng=random.Random(961014);results=[]
    for suffix in ('','_debug'):
        d=bind(ROOT/'build'/f'step_test{suffix}.dll');d.tomb_inventory_init.argtypes=[C.POINTER(Inventory)];d.tomb_inventory_add.argtypes=[C.POINTER(Inventory),C.c_int];d.tomb_inventory_use.argtypes=[C.POINTER(Inventory),C.c_int,C.POINTER(I16)]
        for trial in range(40):
            inv=Inventory();d.tomb_inventory_init(C.byref(inv));o.call(0x23d3c,0,0,0,0);o.call(0x2371c,84,0,0,0)
            for addr in [0xcea20,0xcea08,0xcea14]:o.write(addr,0,4)
            for t in range(70):
                id=rng.choice([84,85,86,87,89,90,91,93,94]);expected=o.call(0x2371c,id,0,0,0);actual=d.tomb_inventory_add(C.byref(inv),id);assert expected==actual,(id,expected,actual)
                for item in [84,85,86,87,89,90,91,93,94]:assert inv.counts[item-84]==o.call(0x23cc0,item,0,0,0),(item,list(inv.counts))
                assert list(inv.ammo)[1:]==[o.read(a,4) for a in [0xcea20,0xcea08,0xcea14]]
                if id in [93,94]:
                    hp=I16(rng.choice([-1,0,1,200,499,500,999,1000]));o.write(0xce960,ITEM,4);o.write(ITEM+0x22,hp.value,2)
                    o.call(0x28afc,id,0,0,0);d.tomb_inventory_use(C.byref(inv),id,C.byref(hp));assert hp.value==o.read(ITEM+0x22,2);assert inv.counts[id-84]==o.call(0x23cc0,id,0,0,0)
        for _ in range(3):
            assert o.call(0x2371c,143,0,0,0)==d.tomb_inventory_add(C.byref(inv),143)
            assert inv.scion==o.call(0x23cc0,143,0,0,0)
        results.append(dict(build=suffix or 'release',inventory_operations=2803))
    # Ground/underwater pickup bounds, alignment and exact collection frames.
    for a in [0x20ce4,0x2371c,0x24ac8]:o.uc.hook_add(UC_HOOK_CODE,lambda *args:o.ret(),begin=a,end=a)
    for suffix in ('','_debug'):
        d=bind(ROOT/'build'/f'step_test{suffix}.dll');d.tomb_pickup_contact.argtypes=[C.POINTER(Object),C.POINTER(Actor),C.POINTER(AnimContext),C.c_uint32,C.c_int,C.POINTER(I16),C.POINTER(I16)]
        err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);q=l.contents
        @EVENT
        def event(*args):pass
        for case in range(2500):
            water=rng.randrange(2);collect=case%3==0;an=130 if water and collect else 108 if water else 135 if collect else 11
            anim=q.animations[an];frame=(2970 if water else 3443)+rng.choice([-1,0,0,0,1]) if collect else anim.first_frame
            stateid=39 if collect else 13 if water else 2
            a=Actor(50000+rng.randrange(-300,301),1000+rng.randrange(-120,121),50000+rng.randrange(-300,201),stateid,stateid,an,frame,0,0,rng.randrange(-32768,32768),0,32)
            obj=Object(Actor(50000,1000,50000,0,0,0,0,0,0,0,0,32),0,0,93,0)
            pitch=I16(rng.choice([0,-4550,2000]));roll=I16(rng.choice([0,0,0,500]));inp=rng.choice([0,64,64]);weapon=rng.choice([0,0,1])
            ctx=AnimContext(q.animations,q.animation_count,q.changes,q.change_count,q.ranges,q.range_count,q.commands,q.command_count,o.sine,a.yaw,0,weapon,event,None)
            o.put_object(obj);o.put(ITEM,a,ACTOR);o.write(ITEM+0x3c,pitch.value,2);o.write(ITEM+0x40,roll.value,2)
            for addr,val,width in [(0xce96e,water,2),(0xce966,weapon,2),(0xce9ce,a.yaw,2),(0xce96c,0,2),(0xce92c,inp,4),(0xcefba,0,1)]:o.write(addr,val,width)
            o.call(0x33e80,0,ITEM,0,0);result=d.tomb_pickup_contact(C.byref(obj),C.byref(a),C.byref(ctx),inp,water,C.byref(pitch),C.byref(roll))
            assert result>=0
            assert state(a)==state(o.get(ITEM,Actor,ACTOR)),(case,water,state(a),state(o.get(ITEM,Actor,ACTOR)))
            assert pitch.value==o.read(ITEM+0x3c,2) and roll.value==o.read(ITEM+0x40,2),(case,pitch.value,o.read(ITEM+0x3c,2),roll.value,o.read(ITEM+0x40,2))
            assert ctx.weapon_status==o.read(0xce966,2)
            assert (result==2)==bool(o.read(0xcefba,1))
        d.tomb_level_free(l)
    (ROOT/'analysis/inventory-validation.json').write_text(json.dumps(dict(results=results,pickup_cases_per_build=2500,scope=__doc__),indent=2))
    print('PASS: DOS inventory/add/use 2800 sequences and 2500 ground/water pickup contacts per build')
if __name__=='__main__':main()
