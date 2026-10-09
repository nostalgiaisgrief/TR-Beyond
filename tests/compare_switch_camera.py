"""Execute original Caves switch lists, RefreshCamera and FixedCamera timer.
Camera LOS/movement and CD playback are doubled; target identity, one-shot,
speed, timer, leaving/re-entering and switch gates use original instructions.
"""
from compare_objects import *
class CameraOracle(ObjectOracle):
    def __init__(self):
        super().__init__();self.uc.mem_map(0x900000,0x10000)
        self.allowed.update(range(0xcb3a0,0xcb3a4));self.allowed.update(range(0xcb278,0xcb2e0));self.allowed.update(range(0x900000,0x901000))
        for a in [0x18ce8,0x183c0,0x13608]:self.uc.hook_add(UC_HOOK_CODE,self.camera_service,begin=a,end=a)
    def service(self,u,a,size,data):
        if a!=0x1790c:super().service(u,a,size,data)
    def camera_service(self,u,a,size,data):self.ret(1 if a==0x183c0 else None)
    def cameras(self,f):
        self.write(0xcb2d1,0x900000,4)
        for i,c in enumerate(f['cameras']):self.uc.mem_write(0x900000+16*i,struct.pack('<3ihH',*c))
        self.write(0xcb2c1,-1,2);self.write(0xcb2c3,-1,2);self.write(0xcb2c5,0,2);self.write(0xcb2c7,0,2)
        self.write(0xcb2c9,0,4);self.write(0xcb2cd,0,4);self.write(0xcb298,0,1)
        self.write(0xce960,ITEM,4);self.uc.mem_write(ITEM,bytes(68));self.write(ITEM+0x42,32,1)
    def begin(self):
        if self.read(0xcb298,1)==1:self.call(0x14534,0,0,0,0)
        self.write(0xcb2c3,self.read(0xcb2c1,2),2);self.write(0xcb2c1,-1,2)
        self.write(0xcb2cd,self.read(0xcb2c9,4),4);self.write(0xcb2c9,0,4);self.write(0xcb298,0,1)

def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=CameraOracle();results=[]
    for suffix in ('','_debug'):
        d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256)
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p
        d.tomb_visual_free.argtypes=[C.c_void_p]
        d.tomb_objects_init.argtypes=[C.POINTER(Objects),C.POINTER(Level),C.c_void_p]
        d.tomb_objects_free.argtypes=[C.POINTER(Objects)];d.tomb_objects_reset.argtypes=[C.POINTER(Objects)]
        d.tomb_objects_camera_begin.argtypes=[C.POINTER(Objects)];d.tomb_objects_trigger.argtypes=[C.POINTER(Objects),SZ,C.c_int]
        l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);v=d.tomb_visual_load(l,err,256);w=Objects();assert d.tomb_objects_init(C.byref(w),l,v)
        cases=0
        for index,sw in [(3474,42),(4030,52)]:
            for leave in [2,40,120]:
                d.tomb_objects_reset(C.byref(w));o.install(f);o.cameras(f)
                for i in range(w.count):o.put_object(w.items[i],i)
                w.items[sw].actor.current=0;w.items[sw].actor.flags=37;w.items[sw].active=1;o.put_object(w.items[sw],sw)
                for tick in range(210):
                    d.tomb_objects_camera_begin(C.byref(w));o.begin()
                    # Leave and return without pulling again, then pull again.
                    if tick==150:
                        w.items[sw].actor.current=0;w.items[sw].actor.flags=37;w.items[sw].active=1;o.put_object(w.items[sw],sw)
                    if tick<leave or tick>=leave+10:
                        assert d.tomb_objects_trigger(C.byref(w),index,1)
                        o.call(0x17a40,FLOOR+2*index,0,0,0)
                    actual=list(w.camera);target=o.read(0xcb2c9,4)
                    expected=[o.read(0xcb2c1,2),o.read(0xcb2c3,2),(target-ITEMS)//68 if target else -1,o.read(0xcb2c5,2),o.read(0xcb2c7,2),int(o.read(0xcb298,1)==1)]
                    assert actual==expected,(suffix,index,leave,tick,actual,expected)
                    for cam in range(len(f['cameras'])):
                        assert bool(w.camera_once[cam//8]&(1<<(cam%8)))==bool(o.read(0x900000+16*cam+15,1)&1)
                    cases+=1
        d.tomb_objects_free(C.byref(w));d.tomb_visual_free(v);d.tomb_level_free(l);results.append(dict(build=suffix or 'release',camera_ticks=cases))
    (ROOT/'analysis/switch-camera-validation.json').write_text(json.dumps(dict(results=results,scope=__doc__),indent=2)+'\n')
    print('PASS: DOS switch camera requests, refresh, expiry and return',results)
if __name__=='__main__':main()
