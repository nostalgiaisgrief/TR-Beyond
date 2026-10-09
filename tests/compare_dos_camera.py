"""DOS LOS, box adjustment, movement and complete chase/fixed camera update.
Original geometry/LOS/box/movement/bounds instructions execute on PHD assets.
Only audio and final view-matrix generation are stubbed in full camera tests.
"""
from compare_door_contact import ContactOracle
from compare_objects import *
class Point(C.Structure):_fields_=[('x',I32),('y',I32),('z',I32),('room',I16)]
class Camera(C.Structure):_fields_=[('eye',Point),('target',Point),('shift',I32),('fixed',I32),('ready',I32),('distance_squared',I32)]
class Request(C.Structure):_fields_=[('distance',I32),('flags',I32),('speed',I32),('angle',I16),('elevation',I16),('pitch',I16),('fixed_index',I16),('item_target',I16)]
class CameraOracle(ContactOracle):
    def __init__(self):
        super().__init__();self.allowed.update(range(0xcb278,0xcb2e0));self.allowed.update(range(0xc17b0,0xc17b8));self.allowed.update(range(DATA,DATA+512))
        for a in [0x3da1c,0x38fa4,0x2dc00]:self.uc.hook_add(UC_HOOK_CODE,self.service_camera,begin=a,end=a)
    def service_camera(self,u,a,size,data):self.ret(pop=12 if a==0x3da1c else 0)
    def call(self,fn,eax,edx,ebx,ecx):
        self.write(STACK+0x800,RETURN,4)
        for reg,val in [(UC_X86_REG_EAX,eax),(UC_X86_REG_EDX,edx),(UC_X86_REG_EBX,ebx),(UC_X86_REG_ECX,ecx),(UC_X86_REG_ESP,STACK+0x800),(UC_X86_REG_EFLAGS,2)]:self.uc.reg_write(reg,val&0xffffffff)
        self.bad=[];self.uc.emu_start(fn,RETURN,count=100000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN,(hex(fn),hex(self.uc.reg_read(UC_X86_REG_EIP)))
        assert self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x804
        assert not self.bad,self.bad
        return self.uc.reg_read(UC_X86_REG_EAX)
    def point(self,addr,p):self.uc.mem_write(addr,struct.pack('<3ih',p.x,p.y,p.z,p.room))
    def getpoint(self,addr):return Point(*struct.unpack('<3ih',self.uc.mem_read(addr,14)))
def values(p):return p.x,p.y,p.z,p.room
def main():
    rng=random.Random(19961011);o=CameraOracle();results=[]
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name;f=parse(path);o.install(f);o.install_models(f)
        for suffix in ('','_debug'):
            d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256)
            d.tomb_dos_camera_los.argtypes=[C.POINTER(Level),C.POINTER(Point),C.POINTER(Point),C.c_int]
            d.tomb_dos_camera_adjust.argtypes=[C.POINTER(Level),C.POINTER(Point),C.POINTER(Point),I32,C.c_int]
            d.tomb_dos_camera_move.argtypes=[C.POINTER(Camera),C.POINTER(Level),Point,C.c_int]
            d.tomb_dos_camera_tick.argtypes=[C.POINTER(Camera),C.POINTER(Level),C.POINTER(Actor),C.POINTER(I16),C.POINTER(I16),C.POINTER(Request)]
            l=d.tomb_level_load(str(path).encode(),err,256);assert l
            valid=[]
            for ri,room in enumerate(f['rooms']):
                for i,s in enumerate(room['sectors']):
                    if s[3]-s[5]<4 or s[1]==65535:continue
                    x,z=divmod(i,room['nz']);valid.append(Point(room['x']+x*1024+512,s[3]*256-512,room['z']+z*1024+512,ri))
            for case in range(2500):
                start=clone(rng.choice(valid));end=Point(start.x+rng.randrange(-2500,2501),start.y+rng.randrange(-1500,1501),start.z+rng.randrange(-2500,2501),start.room)
                heavy=rng.randrange(2);o.write(0xc17b0,heavy,4);o.point(DATA,start);o.point(DATA+32,end)
                expected=o.call(0x183c0,DATA,DATA+32,0,0);actual=d.tomb_dos_camera_los(l,C.byref(start),C.byref(end),heavy)
                assert actual==expected and values(end)==values(o.getpoint(DATA+32)),('los',name,case,actual,expected,values(start),values(end),values(o.getpoint(DATA+32)))
            for case in range(2500):
                target=clone(rng.choice(valid));ideal=Point(target.x+rng.randrange(-1536,1537),target.y+rng.randrange(-700,701),target.z+rng.randrange(-1536,1537),target.room)
                heavy=rng.randrange(2);r2=1536**2
                o.write(0xc17b0,heavy,4);o.write(0xcb2b5,r2,4);o.point(0xcb288,target);o.point(DATA,ideal)
                o.call(0x13af0,DATA,0x13978,0,0)
                ok=d.tomb_dos_camera_adjust(l,C.byref(target),C.byref(ideal),r2,heavy)
                assert ok and values(ideal)==values(o.getpoint(DATA)),('adjust',name,case,values(target),values(ideal),values(o.getpoint(DATA)))
            for case in range(2000):
                target=clone(rng.choice(valid));eye=Point(target.x+100,target.y-400,target.z-100,target.room);dest=Point(target.x+rng.randrange(-1500,1501),target.y+rng.randrange(-1000,1001),target.z+rng.randrange(-1500,1501),target.room)
                speed=rng.choice([1,4,12,17]);c=Camera(eye,target,0,0,1)
                o.point(0xcb278,eye);o.point(0xcb288,target);o.point(DATA,dest);o.write(0xcb2a9,0,4)
                o.call(0x13608,DATA,speed,0,0)
                assert d.tomb_dos_camera_move(C.byref(c),l,dest,speed)
                assert values(c.eye)==values(o.getpoint(0xcb278)) and c.shift==o.read(0xcb299,4),('move',name,case,values(c.eye),values(o.getpoint(0xcb278)),c.shift,o.read(0xcb299,4))
            # Entire normal/fixed update, real bounds and geometry; maintained
            # history captures integer truncation and room transitions.
            for i,cam in enumerate(f['cameras']):o.uc.mem_write(0x9b0000+16*i,struct.pack('<3ihH',*cam))
            o.write(0xcb2d1,0x9b0000,4);o.write(0xce960,ITEM,4);o.write(0xcb2ad,0,4);o.write(0xcb2a9,0,4)
            full=0
            for sequence in range(80):
                p=clone(rng.choice(valid));a=Actor(p.x,p.y+512,p.z,2,2,11,185,0,0,rng.randrange(-32768,32768),p.room,32)
                c=Camera();o.point(0xcb278,Point(a.x,a.y-1024,a.z-100,a.room));o.point(0xcb288,Point(a.x,a.y-1024,a.z,a.room));o.write(0xcb2a1,0,4)
                for tick in range(30):
                    request=Request(1536,rng.choice([0,1,2]),12,rng.choice([0,14560,15470]),rng.choice([0,-4004,-8190]),rng.randrange(-6000,6001),-1,0)
                    if tick>=10 and tick<20 and f['cameras']:request.fixed_index=sequence%len(f['cameras']);request.speed=17
                    looking=sequence%3==0 and 5<=tick<25
                    if looking:request=Request(1536,512,4,rng.randrange(-8008,8009)*2,rng.randrange(-7644,4005)*2,0,-1,0)
                    o.put(ITEM,a,ACTOR);o.write(ITEM+12,0,2);o.write(ITEM+0x3c,request.pitch,2);o.write(ITEM+0x40,0,2)
                    ptr=o.call(0x1d444,ITEM,0,0,0);bounds=(I16*6).from_buffer_copy(o.uc.mem_read(ptr,12))
                    for addr,val,width in [(0xcb298,1 if request.fixed_index>=0 else 0,1),(0xcb29d,request.flags,4),(0xcb2b1,request.distance,4),(0xcb2b9,request.angle,2),(0xcb2bd,request.elevation,2),(0xcb2c7,request.speed,2),(0xcb2c1,request.fixed_index,2),(0xcb2c9,0,4),(0xcb2c5,90,2)]:o.write(addr,val,width)
                    if looking:
                        o.write(0xcb298,2,1);o.write(0xcb29d,0,4)
                        for addr,val in [(0xce9d0,request.angle//2),(0xce9d6,request.angle//2),(0xce9d2,request.elevation//2),(0xce9d8,request.elevation//2)]:o.write(addr,val,2)
                    focus=a
                    if request.fixed_index>=0 and sequence%2:
                        focus=clone(a);focus.x+=100;focus.z-=100
                        o.put_object(Object(focus,0,0,0,0),41);o.write(0xcb2c9,ITEMS+41*68,4);request.item_target=1
                    o.call(0x145c8,0,0,0,0)
                    assert d.tomb_dos_camera_tick(C.byref(c),l,C.byref(focus),bounds,o.sine,C.byref(request)),('tick failed',name,sequence,tick)
                    assert values(c.eye)==values(o.getpoint(0xcb278)) and values(c.target)==values(o.getpoint(0xcb288)) and c.shift==o.read(0xcb299,4),('tick',name,sequence,tick,values(c.eye),values(o.getpoint(0xcb278)),values(c.target),values(o.getpoint(0xcb288)),c.shift,o.read(0xcb299,4))
                    full+=1
            d.tomb_level_free(l);results.append(dict(level=name,build=suffix or 'release',los=2500,adjust=2500,move=2000,full_updates=full))
    # Real gameplay trace from native integration, compared against the entire
    # DOS CalculateCamera path with original bounds/LOS/geometry active.
    import csv
    f=parse(ROOT/'work/reference-assets/DATA/GYM.PHD');o.install(f);o.install_models(f);o.write(0xce960,ITEM,4)
    routes=0
    route=ROOT/'build/dos-camera-route.csv'
    if not route.exists():
        print('NOTE: native route comparison skipped; run build-preview.ps1 to generate its trace.')
    with route.open() if route.exists() else __import__('io').StringIO('') as trace:
        for line in csv.DictReader(trace):
            row={k:int(v) for k,v in line.items()};a=Actor(row['x'],row['y'],row['z'],2,2,row['animation'],row['frame'],0,0,row['yaw'],row['room'],32)
            if row['tick']==0:
                o.point(0xcb278,Point(a.x,a.y-1024,a.z-100,a.room));o.point(0xcb288,Point(a.x,a.y-1024,a.z,a.room));o.write(0xcb2a1,0,4)
            o.put(ITEM,a,ACTOR);o.write(ITEM+12,0,2);o.write(ITEM+0x3c,row['pitch'],2);o.write(ITEM+0x40,0,2)
            for addr,val,width in [(0xcb298,0,1),(0xcb29d,row['flags'],4),(0xcb2b1,row['distance'],4),(0xcb2b9,row['angle'],2),(0xcb2bd,row['elevation'],2),(0xcb2c7,12,2),(0xcb2c1,-1,2),(0xcb2c9,0,4),(0xcb2a9,0,4)]:o.write(addr,val,width)
            o.call(0x145c8,0,0,0,0)
            assert values(o.getpoint(0xcb278))==tuple(row[k] for k in ['eye_x','eye_y','eye_z','eye_room']),('route eye',row,values(o.getpoint(0xcb278)))
            assert values(o.getpoint(0xcb288))==tuple(row[k] for k in ['target_x','target_y','target_z','target_room']),('route target',row,values(o.getpoint(0xcb288)))
            assert o.read(0xcb299,4)==row['shift'];routes+=1
    (ROOT/'analysis/dos-camera-validation.json').write_text(json.dumps(dict(results=results,gameplay_route_ticks=routes,scope=__doc__),indent=2)+'\n');print('PASS: DOS camera',results,'gameplay route ticks',routes)
if __name__=='__main__':main()
