"""DOS target points, vector angles, weapon rays and articulated mesh spheres.
HitTarget/LOS/ricochet effects are captured at service boundaries for ray tests.
"""
from compare_dos_camera import *
from compare_door_contact import Sphere
from compare_creatures import Creature
class RayOracle(CameraOracle):
    def __init__(self):
        super().__init__();self.hit=None
        for lo,hi in [(0xc19a4,0xc19a8),(0xce9fc,0xcea08),(0x12ea54,0x12f3c4)]:self.allowed.update(range(lo,hi))
        for fn in [0x2b130,0x183c0,0x1d764]:self.uc.hook_add(UC_HOOK_CODE,self.ray,begin=fn,end=fn)
    def ray(self,u,at,size,data):
        if at!=0x183c0:self.hit=struct.unpack('<3i',self.uc.mem_read(u.reg_read(UC_X86_REG_EDX if at==0x2b130 else UC_X86_REG_EAX),12))
        self.ret(1)
def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=RayOracle();o.install(f);o.install_models(f);results=[]
    for id,joint in [(7,3),(8,14)]:
        tree=o.read(0xcc064+id*50,4);at=0x990000+4*(tree+4*(joint-1));o.write(at,o.read(at,4)|8,4)
    for suffix in ('','_debug'):
        rng=random.Random(19961018);d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256)
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p;d.tomb_visual_free.argtypes=[C.c_void_p]
        l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);v=d.tomb_visual_load(l,err,256)
        d.tomb_gun_target_point.argtypes=[C.c_void_p,C.POINTER(Actor),C.POINTER(I16),C.POINTER(Point)]
        d.tomb_gun_angles.argtypes=[I32,I32,I32,C.POINTER(I16)]
        d.tomb_object_joint.argtypes=[C.c_void_p,C.c_int,C.POINTER(Actor),I16,I16,I16,C.c_int,C.POINTER(I32),C.POINTER(I16)]
        d.tomb_pistol_ray.argtypes=[C.c_void_p,C.POINTER(Object),C.POINTER(Creature),Point,I16,I16,C.POINTER(C.c_uint32),C.POINTER(I16),C.POINTER(Point)]
        hits=0
        for case in range(2500):
            id=rng.choice([7,8,9]);anim=rng.randrange(172,197) if id==7 else rng.randrange(197,218) if id==8 else rng.randrange(218,223);an=l.contents.animations[anim]
            a=Actor(10000+rng.randrange(-3000,3001),rng.randrange(-1200,1201),20000+rng.randrange(-3000,3001),an.state,an.state,anim,rng.randint(an.first_frame,an.last_frame),20,0,rng.randrange(-32768,32768),0,35)
            ob=Object(a,0,0,id,1);c=Creature();c.head=rng.randrange(-16000,16001);c.pitch=rng.randrange(-3000,3001);c.roll=rng.randrange(-3000,3001)
            o.put_object(ob);o.write(ITEMS+0x3c,c.pitch,2);o.write(ITEMS+0x40,c.roll,2);o.write(ITEMS+0x2c,DOORS,4);o.write(DOORS,c.head,2)
            bite=(I32*3)(0,-14 if id==7 else 96 if id==8 else 16,174 if id==7 else 335 if id==8 else 45);joint=6 if id==7 else 14 if id==8 else 4
            o.uc.mem_write(DATA,bytes(bite));o.call(0x393dc,ITEMS,DATA,joint,0)
            assert d.tomb_object_joint(v,id,C.byref(a),c.pitch,c.roll,c.head,joint,bite,o.sine)
            assert bytes(bite)==bytes(o.uc.mem_read(DATA,12)),('bite',case,list(bite),struct.unpack('<3i',o.uc.mem_read(DATA,12)))
            target=Point();assert d.tomb_gun_target_point(v,C.byref(a),o.sine,C.byref(target));o.call(0x2ac1c,ITEMS,DATA,0,0)
            assert values(target)==values(o.getpoint(DATA)),('target',case,values(target),values(o.getpoint(DATA)))
            vec=[target.x-10000,target.y+650,target.z-20000];angles=(I16*2)();d.tomb_gun_angles(*vec,angles);o.call(0x3da78,*vec,DATA)
            assert bytes(angles)==bytes(o.uc.mem_read(DATA,4)),('angles',case,list(angles),struct.unpack('<2h',o.uc.mem_read(DATA,4)))
            yaw=C.c_int16(angles[0]+rng.randrange(-3000,3001)).value;pitch=C.c_int16(angles[1]+rng.randrange(-3000,3001)).value
            o.put(ITEM,Actor(10000,0,20000,2,2,11,185,0,0,0,0,32),ACTOR);o.uc.mem_write(DATA,struct.pack('<2h',yaw,pitch))
            seed=C.c_uint32(rng.getrandbits(32));o.write(0xc19a4,seed.value,4);o.hit=None
            expected=C.c_int32(o.call(0x2ada0,1,ITEMS,ITEM,DATA)).value
            point=Point();actual=d.tomb_pistol_ray(v,C.byref(ob),C.byref(c),Point(10000,-650,20000,0),yaw,pitch,C.byref(seed),o.sine,C.byref(point))
            assert actual==(expected==1),(case,'hit',id,actual,expected)
            assert (point.x,point.y,point.z)==o.hit,(case,'ray',id,(point.x,point.y,point.z),o.hit)
            assert seed.value==o.read(0xc19a4,4)&0xffffffff
            hits+=actual
        assert hits>100
        results.append(dict(build=suffix or 'release',target_angle_ray_cases=2500,hits=hits));d.tomb_visual_free(v);d.tomb_level_free(l)
    (ROOT/'analysis/combat-validation.json').write_text(json.dumps(dict(scope=__doc__,results=results),indent=2)+'\n');print('PASS: DOS weapon rays',results)
if __name__=='__main__':main()
