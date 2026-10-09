"""Actual DOS nearest pose / mesh spheres and local push arithmetic.
Push terrain query and room update are explicit doubles; integration exercises
the real terrain separately. No full renderer equivalence is claimed.
"""
from compare_objects import *
class Sphere(C.Structure):_fields_=[(n,I32) for n in ('x','y','z','radius')]
class ContactOracle(ObjectOracle):
    def __init__(self):
        super().__init__();self.uc.mem_map(0x900000,0x200000)
        self.allowed.update(range(0xa00000,0xa10000));self.allowed.update(range(0x12f3c4,0x12f3c8))
        self.allowed.update(range(0xce972,0xce976));self.allowed.update(range(0xcc020,0xcc02c))
        self.uc.hook_add(UC_HOOK_CODE,self.room_update,begin=0x15fb8,end=0x15fb8)
    def room_update(self,*args):self.ret()
    def install_models(self,f):
        s=f['sections'];frames=0x900000;meshes=0x960000;trees=0x990000;ptrs=0x9a0000
        for name,addr in [('frames',frames),('mesh',meshes),('trees',trees)]:self.uc.mem_write(addr,s[name]['bytes'])
        raw=bytearray(s['animations']['bytes'])
        for i in range(len(raw)//32):struct.pack_into('<I',raw,i*32,struct.unpack_from('<I',raw,i*32)[0]+frames)
        self.uc.mem_write(ANIMS,bytes(raw))
        for i in range(s['meshptr']['count']):self.write(ptrs+4*i,meshes+struct.unpack_from('<I',s['meshptr']['bytes'],4*i)[0],4)
        self.write(0xcc044,ptrs,4);self.write(0xcc040,trees,4)
        for i in range(s['models']['count']):
            id,n,start,tree,frame,anim=struct.unpack_from('<IHHIIH',s['models']['bytes'],18*i)
            self.write(0xcc060+50*id,n,2);self.write(0xcc062+50*id,start,2);self.write(0xcc064+50*id,tree,4)
        self.write(0x12f3c4,0xa01000,4)
        self.uc.mem_write(0xa01000,struct.pack('<12i',16384,0,0,0,0,16384,0,0,0,0,16384,0))

def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=ContactOracle();o.install(f);o.install_models(f)
    rng=random.Random(961010);results=[]
    for suffix in ('','_debug'):
        d=bind(ROOT/'build'/f'step_test{suffix}.dll')
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p
        d.tomb_visual_free.argtypes=[C.c_void_p]
        d.tomb_object_spheres.argtypes=[C.c_void_p,C.c_int,C.POINTER(Actor),I16,I16,C.POINTER(I16),C.POINTER(Sphere)]
        d.tomb_object_push.argtypes=[C.POINTER(Actor),C.POINTER(I16),C.POINTER(Actor),C.c_int,C.POINTER(I16)]
        d.tomb_object_angle.argtypes=[I32,I32];d.tomb_object_angle.restype=I16
        d.tomb_objects_init.argtypes=[C.POINTER(Objects),C.POINTER(Level),C.c_void_p];d.tomb_objects_free.argtypes=[C.POINTER(Objects)]
        d.tomb_doors_collide.argtypes=[C.POINTER(Objects),C.POINTER(Actor),C.POINTER(Contact),C.POINTER(AnimContext),I16,I16,QUERY,C.c_void_p,C.POINTER(C.c_int)]
        err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);v=d.tomb_visual_load(l,err,256)
        cases=0
        for anim in list(range(0,20))+list(range(233,253)):
            an=l.contents.animations[anim];object=0 if anim<233 else 55 if anim<237 else 57+(anim-237)//4
            for frame in range(an.first_frame,an.last_frame+1):
                a=Actor(49664,7680,57856,an.state,an.state,anim,frame,0,0,rng.randrange(-32768,32768),9,32)
                pitch=rng.randrange(-2000,2001);roll=rng.randrange(-2000,2001)
                obj=Object(a,0,0,object,0);o.put_object(obj);o.write(ITEMS+0x3c,pitch,2);o.write(ITEMS+0x40,roll,2)
                expected_n=o.call(0x39130,ITEMS,0xa08000,1,0)
                spheres=(Sphere*64)();n=d.tomb_object_spheres(v,object,C.byref(a),pitch,roll,o.sine,spheres)
                assert n==expected_n,(anim,frame,n,expected_n)
                expected=bytes(o.uc.mem_read(0xa08000,n*16));actual=bytes(spheres)[:n*16]
                assert actual==expected,(anim,frame,struct.unpack('<'+'i'*(n*4),actual),struct.unpack('<'+'i'*(n*4),expected))
                cases+=1
        pushes=0
        for i in range(3000):
            # Door poses provide real asymmetric bounds, including open leaves.
            anim=rng.randrange(237,253);an=l.contents.animations[anim]
            door=Actor(49664,7680,57856,an.state,an.state,anim,rng.randint(an.first_frame,an.last_frame),0,0,rng.choice([0,16384,-16384,-32768]),9,32)
            o.put_object(Object(door,0,0,57+(anim-237)//4,0));ptr=o.call(0x1d4b8,ITEMS,0,0,0)
            bounds=(I16*6).from_buffer_copy(o.uc.mem_read(ptr,12))
            a=Actor(door.x+rng.randrange(-1500,1501),door.y,door.z+rng.randrange(-1500,1501),2,2,11,185,0,0,0,9,32);actual=clone(a)
            c=Contact();c.old_x=a.x;c.old_y=a.y;c.old_z=a.z;c.flags=24
            o.put(ITEM,a,ACTOR);o.put(COLL,c,CONTACT);o.write(COLL+0x30,100,4)
            o.write(STACK+0x800,RETURN,4);o.write(STACK+0x804,1,4)
            for reg,val in [(UC_X86_REG_EAX,ITEMS),(UC_X86_REG_EDX,ITEM),(UC_X86_REG_EBX,COLL),(UC_X86_REG_ECX,0),(UC_X86_REG_ESP,STACK+0x800)]:o.uc.reg_write(reg,val)
            o.bad=[];o.uc.emu_start(0x164a4,RETURN,count=10000);assert not o.bad,o.bad
            d.tomb_object_push(C.byref(door),bounds,C.byref(actual),100,o.sine)
            expected=o.get(ITEM,Actor,ACTOR);assert state(actual)==state(expected),(i,state(actual),state(expected))
            pushes+=1
        for i in range(10000):
            z,x=rng.randrange(-100000,100001),rng.randrange(-100000,100001)
            assert d.tomb_object_angle(z,x)==C.c_int16(o.call(0x3f070,z,x,0,0)).value
        w=Objects();assert d.tomb_objects_init(C.byref(w),l,v)
        for i in range(w.count):w.items[i].actor.flags=0
        ctx=AnimContext();ctx.sine_quarter=o.sine
        @QUERY
        def query(user,actor,contact,height):assert height==762
        contacts=0;hit_cases=0
        for door_id in [9,12,13,28,35,36,43,44]:
            base=clone(w.items[door_id]);w.items[door_id].actor.flags=32
            for case in range(400):
                obj=w.items[door_id];anim=237+(obj.object-57)*4+rng.randrange(4);an=l.contents.animations[anim]
                obj.actor.animation=anim;obj.actor.frame=rng.randint(an.first_frame,an.last_frame);obj.actor.current=an.state;obj.actor.goal=rng.randrange(2)
                o.put_object(obj,door_id)
                a=Actor(obj.actor.x+rng.randrange(-800,801),obj.actor.y+rng.randrange(-100,301),obj.actor.z+rng.randrange(-800,801),2,2,11,rng.randint(l.contents.animations[11].first_frame,l.contents.animations[11].last_frame),0,0,rng.randrange(-32768,32768),obj.actor.room,32)
                c=Contact();c.old_x=a.x;c.old_y=a.y;c.old_z=a.z;c.flags=rng.choice([0,8,24]);c.type=rng.choice([0,0,1]);c.facing=a.yaw
                o.put(ITEM,a,ACTOR);o.write(ITEM+12,0,2);o.write(ITEM+0x3c,0,2);o.write(ITEM+0x40,0,2)
                o.put(COLL,c,CONTACT);o.write(COLL+0x30,100,4);o.write(0xce974,-1,2);o.write(0xce972,0,2)
                o.call(0x163dc,door_id,ITEM,COLL,0)
                hit=C.c_int();assert d.tomb_doors_collide(C.byref(w),C.byref(a),C.byref(c),C.byref(ctx),0,0,query,None,C.byref(hit))
                assert state(a)==state(o.get(ITEM,Actor,ACTOR)),(door_id,case,state(a),state(o.get(ITEM,Actor,ACTOR)))
                assert state(c)==state(o.get(COLL,Contact,CONTACT)),(door_id,case,state(c),state(o.get(COLL,Contact,CONTACT)))
                assert hit.value==o.read(0xce974,2)+1,(door_id,case,hit.value,o.read(0xce974,2))
                hit_cases+=bool(hit.value);contacts+=1
            w.items[door_id].actor.flags=0
        assert hit_cases>0
        d.tomb_objects_free(C.byref(w));d.tomb_visual_free(v);d.tomb_level_free(l)
        results.append(dict(build=suffix or 'release',sphere_poses=cases,push_cases=pushes,door_contacts=contacts,hit_reactions=hit_cases,angle_cases=10000))
    (ROOT/'analysis/door-contact-validation.json').write_text(json.dumps(dict(results=results,scope=__doc__),indent=2)+'\n')
    print('PASS: DOS door/Lara spheres and pushing',results)
if __name__=='__main__':main()
