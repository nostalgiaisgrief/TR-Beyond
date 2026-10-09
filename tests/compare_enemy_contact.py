"""DOS CreatureCollision: articulated spheres, touch masks and pushes.
Terrain correction and room update are doubled; native routes use real terrain.
"""
from compare_door_contact import *
from compare_navigation import Navigation,Creature
from compare_dos_camera import CameraOracle
class Enemies(C.Structure):
    _fields_=[('items',C.POINTER(Creature)),('navigation',Navigation*8),('slots',C.c_int*8),('head',C.c_int),('next',C.POINTER(C.c_int)),('random',C.c_uint32),('camera',I32*3)]+[(n,C.POINTER(C.c_int)) for n in ('room_head','room_next','room_id')]
def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=CameraOracle();o.install(f);o.install_models(f);results=[]
    for id,joint in [(7,3),(8,14)]:
        tree=o.read(0xcc064+id*50,4);at=0x990000+4*(tree+4*(joint-1));o.write(at,o.read(at,4)|8,4)
    for suffix in ('','_debug'):
        rng=random.Random(19961020);d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256)
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p;d.tomb_visual_free.argtypes=[C.c_void_p]
        l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);v=d.tomb_visual_load(l,err,256)
        d.tomb_objects_init.argtypes=[C.POINTER(Objects),C.POINTER(Level),C.c_void_p];d.tomb_objects_free.argtypes=[C.POINTER(Objects)]
        d.tomb_doors_collide.argtypes=[C.POINTER(Objects),C.POINTER(Actor),C.POINTER(Contact),C.POINTER(AnimContext),I16,I16,QUERY,C.c_void_p,C.POINTER(C.c_int)]
        w=Objects();assert d.tomb_objects_init(C.byref(w),l,v);e=C.cast(w.enemies,C.POINTER(Enemies)).contents
        for j in range(w.count):w.items[j].actor.flags=0
        ctx=AnimContext();ctx.sine_quarter=o.sine
        @QUERY
        def query(user,actor,contact,height):assert height==762
        touches=0
        for id in [26,30,31]:
            ob=w.items[id];species=ob.object
            for case in range(1200):
                anim=rng.randrange(172,197) if species==7 else rng.randrange(197,218) if species==8 else rng.randrange(218,223);an=l.contents.animations[anim]
                ob.actor.animation=anim;ob.actor.frame=rng.randint(an.first_frame,an.last_frame);ob.actor.current=an.state;ob.actor.flags=35;ob.actor.yaw=rng.randrange(-32768,32768)
                cr=e.items[id];cr.head=rng.randrange(-15000,15001);cr.pitch=rng.randrange(-3000,3001);cr.roll=rng.randrange(-1000,1001);cr.health=rng.choice([0,6]);cr.touch=0
                o.put_object(ob,id);at=ITEMS+68*id;o.write(at+0x2c,DOORS,4);o.write(DOORS,cr.head,2);o.write(at+0x22,cr.health,2);o.write(at+0x3c,cr.pitch,2);o.write(at+0x40,cr.roll,2)
                a=Actor(ob.actor.x+rng.randrange(-600,601),ob.actor.y+rng.randrange(-200,801),ob.actor.z+rng.randrange(-600,601),2,2,11,rng.randint(l.contents.animations[11].first_frame,l.contents.animations[11].last_frame),0,0,rng.randrange(-32768,32768),ob.actor.room,32)
                c=Contact();c.old_x=a.x;c.old_y=a.y;c.old_z=a.z;c.flags=rng.choice([0,8,24]);c.type=rng.choice([0,0,1]);c.facing=a.yaw
                o.put(ITEM,a,ACTOR);o.write(ITEM+12,0,2);o.write(ITEM+0x3c,0,2);o.write(ITEM+0x40,0,2)
                o.put(COLL,c,CONTACT);o.write(COLL+0x30,100,4);o.write(0xce974,-1,2);o.write(0xce972,0,2)
                o.call(0x16314,id,ITEM,COLL,0);hit=C.c_int();assert d.tomb_doors_collide(C.byref(w),C.byref(a),C.byref(c),C.byref(ctx),0,0,query,None,C.byref(hit))
                assert state(a)==state(o.get(ITEM,Actor,ACTOR)),(species,case,'actor',state(a),state(o.get(ITEM,Actor,ACTOR)))
                assert state(c)==state(o.get(COLL,Contact,CONTACT)),(species,case,'contact')
                assert cr.touch==o.read(at+4,4)&0xffffffff,(species,case,'touch',cr.touch,o.read(at+4,4))
                assert hit.value==o.read(0xce974,2)+1,(species,case,'hit',hit.value,o.read(0xce974,2))
                touches+=bool(cr.touch)
            ob.actor.flags=0
        assert touches>100
        d.tomb_objects_free(C.byref(w));d.tomb_visual_free(v);d.tomb_level_free(l);results.append(dict(build=suffix or 'release',contact_cases=3600,touches=touches))
    (ROOT/'analysis/enemy-contact-validation.json').write_text(json.dumps(dict(scope=__doc__,results=results),indent=2)+'\n');print('PASS: DOS enemy contact',results)
if __name__=='__main__':main()
