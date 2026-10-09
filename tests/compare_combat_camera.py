"""Complete DOS CalculateCamera combat branch, including retained chase radius."""
from compare_dos_camera import *
def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=CameraOracle();o.install(f);o.install_models(f);o.write(0xce960,ITEM,4);results=[]
    for suffix in ('','_debug'):
        rng=random.Random(19961017);d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256)
        d.tomb_dos_camera_tick.argtypes=[C.POINTER(Camera),C.POINTER(Level),C.POINTER(Actor),C.POINTER(I16),C.POINTER(I16),C.POINTER(Request)]
        for case in range(2000):
            it=rng.choice(f['items']);a=Actor(it[2],it[3],it[4],2,2,11,185,0,0,rng.randrange(-32768,32768),it[1],32)
            c=Camera(Point(a.x+100,a.y-600,a.z-100,a.room),Point(a.x,a.y-700,a.z,a.room),0,rng.randrange(2),1,rng.randrange(500,1600)**2)
            r=Request(2560,256,8,rng.randrange(-24000,24001),rng.randrange(-12000,12001),rng.randrange(-6000,6001),-1,0)
            o.put(ITEM,a,ACTOR);o.write(ITEM+12,0,2);o.write(ITEM+0x3c,r.pitch,2);o.write(ITEM+0x40,0,2)
            ptr=o.call(0x1d444,ITEM,0,0,0);bounds=(I16*6).from_buffer_copy(o.uc.mem_read(ptr,12))
            o.point(0xcb278,c.eye);o.point(0xcb288,c.target)
            for addr,val,w in [(0xcb298,3,1),(0xcb2a1,c.fixed,4),(0xcb29d,0,4),(0xcb2b5,c.distance_squared,4),(0xcb2c9,0,4),(0xcb2a9,0,4),(0xcb2ad,0,4),(0xce9c4,ITEMS,4),(0xce9c8,r.angle,2),(0xce9ca,r.elevation,2)]:o.write(addr,val,w)
            o.call(0x145c8,0,0,0,0);assert d.tomb_dos_camera_tick(C.byref(c),l,C.byref(a),bounds,o.sine,C.byref(r))
            assert values(c.eye)==values(o.getpoint(0xcb278)) and values(c.target)==values(o.getpoint(0xcb288)) and c.shift==o.read(0xcb299,4),(case,values(c.eye),values(o.getpoint(0xcb278)),values(c.target),values(o.getpoint(0xcb288)))
        d.tomb_level_free(l);results.append(dict(build=suffix or 'release',combat_camera_cases=2000))
    (ROOT/'analysis/combat-camera-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS combat camera',results)
if __name__=='__main__':main()
