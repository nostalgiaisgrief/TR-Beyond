"""T. rex stomp strength and camera bounce against DOS 0x1de7c / 0x13608.
Uses actual Valley geometry, including the original negative-bounce RNG path.
"""
from compare_dos_camera import *
def main():
    o=CameraOracle();f=parse(ROOT/'work/reference-assets/DATA/LEVEL3A.PHD');o.install(f)
    o.allowed.update(range(0xc19a4,0xc19a8));results=[]
    for suffix in ('','_debug'):
        rng=random.Random(19961030);d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256)
        d.tomb_dos_camera_stomp.argtypes=[C.POINTER(Point),C.POINTER(Actor),C.c_int]
        d.tomb_dos_camera_move_effects.argtypes=[C.POINTER(Camera),C.POINTER(Level),Point,C.c_int,C.POINTER(C.c_int),C.POINTER(C.c_uint32)]
        l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL3A.PHD').encode(),err,256);assert l
        for case in range(4000):
            eye=Point(50000,0,20000,60);a=Actor();a.x=eye.x+rng.randrange(-20000,20001);a.y=eye.y+rng.randrange(-20000,20001);a.z=eye.z+rng.randrange(-20000,20001)
            before=rng.randrange(-200,101);o.point(0xcb278,eye);o.put(ITEM,a,ACTOR);o.write(0xcb2a9,before,4)
            o.call(0x1de7c,ITEM,0,0,0)
            assert d.tomb_dos_camera_stomp(C.byref(eye),C.byref(a),before)==o.read(0xcb2a9,4)
        valid=[]
        for ri,room in enumerate(f['rooms']):
            for i,s in enumerate(room['sectors']):
                if s[3]-s[5]<4 or s[1]==65535:continue
                x,z=divmod(i,room['nz']);valid.append(Point(room['x']+x*1024+512,s[3]*256-512,room['z']+z*1024+512,ri))
        for case in range(1000):
            target=clone(rng.choice(valid));eye=Point(target.x+100,target.y-400,target.z-100,target.room);dest=Point(target.x+rng.randrange(-1500,1501),target.y+rng.randrange(-1000,1001),target.z+rng.randrange(-1500,1501),target.room)
            speed=rng.choice([1,4,12,17]);c=Camera(eye,target,0,0,1);bounce=C.c_int(rng.randrange(-200,101));seed=C.c_uint32(rng.getrandbits(32))
            o.point(0xcb278,eye);o.point(0xcb288,target);o.point(DATA,dest);o.write(0xcb2a9,bounce.value,4);o.write(0xc19a4,seed.value,4)
            o.call(0x13608,DATA,speed,0,0)
            assert d.tomb_dos_camera_move_effects(C.byref(c),l,dest,speed,C.byref(bounce),C.byref(seed))
            assert values(c.eye)==values(o.getpoint(0xcb278)) and c.shift==o.read(0xcb299,4)
            assert values(c.target)==values(o.getpoint(0xcb288))
            assert bounce.value==o.read(0xcb2a9,4) and seed.value==o.read(0xc19a4,4)&0xffffffff
        d.tomb_level_free(l);results.append(dict(build=suffix or 'release',stomp_cases=4000,bounce_cases=1000))
    (ROOT/'analysis/valley-effects-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS stomp/camera bounce',results)
if __name__=='__main__':main()
