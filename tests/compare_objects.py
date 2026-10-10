"""Original DOS triggers, timer, switch consumption, stationary object animation
and real Caves door-sector initialization. OS/audio/list services are doubles.
"""
import ctypes as C,random,json,struct
from compare_level import *
from compare_step import *
from unicorn import UC_HOOK_CODE
class Object(C.Structure):
    _fields_=[('actor',Actor),('flags',C.c_uint16),('timer',I16),('object',I16),('active',C.c_int)]
class DoorPart(C.Structure):
    _fields_=[('ref',Ref),('saved',Sector),('box',C.c_int)]
class Door(C.Structure):
    _fields_=[('parts',DoorPart*4),('count',C.c_uint),('open',C.c_int)]
class Objects(C.Structure):
    _fields_=[('level',C.POINTER(Level)),('visual',C.c_void_p),('items',C.POINTER(Object)),('doors',C.POINTER(Door)),('box_overlap',C.POINTER(C.c_uint16)),('count',SZ),('deferred_actions',C.c_uint),('camera',C.c_int*6),('camera_once',U8*128),('hazards',C.c_void_p),('enemies',C.c_void_p),('progress',C.c_void_p),('last_target',C.c_int),('peru',C.c_void_p)]
BOXES=0x7a0000
DOORS=0x7b0000
class ObjectOracle(GeometryOracle):
    def __init__(self):
        super().__init__();self.heap=DOORS;self.skip_switch=False
        for a in [0x20e64,0x24b3c,0x24a30,0x1790c,0x34bd8]:self.uc.hook_add(UC_HOOK_CODE,self.service,begin=a,end=a)
        self.allowed.update(range(ITEMS,ITEMS+1024*68));self.allowed.update(range(DOORS,DOORS+65536))
        self.allowed.update(range(BOXES,BOXES+65536));self.allowed.update(range(ITEM,ITEM+68))
    def service(self,u,a,size,data):
        if a==0x20e64:
            result=self.heap;self.heap+=u.reg_read(UC_X86_REG_EAX);self.ret(result)
        elif a==0x1790c:self.ret()
        elif a==0x34bd8:
            if self.skip_switch:self.ret(1)
        else:
            at=ITEMS+68*C.c_int32(u.reg_read(UC_X86_REG_EAX)).value
            flags=self.read(at+0x42,1)
            self.write(at+0x42,flags|1 if a==0x24b3c else flags&~1,1);self.ret()
    def install(self,f):
        super().install(f);self.heap=DOORS
        for i,r in enumerate(f['rooms']):
            self.write(ROOMS+i*68+0x40,r['alternate'],2)
            self.write(ROOMS+i*68+0x42,r['flags'],2)
        self.write(0xcb270,BOXES,4)
        for i,b in enumerate(f['boxes']):self.uc.mem_write(BOXES+20*i,struct.pack('<4ihH',*b))
        for at,n in self.sectors:self.allowed.update(range(at,at+8*n))
    def put_object(self,o,index=0):
        at=ITEMS+index*68;self.uc.mem_write(at,bytes(68))
        for name,(off,width) in ACTOR.items():self.write(at+off,getattr(o.actor,name),width)
        self.write(at+0x28,o.flags,2);self.write(at+0x26,o.timer,2);self.write(at+12,o.object,2)
    def compare(self,o,index=0):
        at=ITEMS+68*index
        expected=state(self.get(at,Actor,ACTOR))
        assert state(o.actor)==expected,(state(o.actor),expected)
        assert o.flags==(self.read(at+0x28,2)&65535)
        assert o.timer==self.read(at+0x26,2)
        assert bool(o.active)==bool(self.read(at+0x42,1)&1)

def main():
    fixture=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');rng=random.Random(19961010)
    oracle=ObjectOracle();results=[]
    # Execute DOS setup itself: known switch/door IDs have no height callbacks.
    oracle.uc.mem_write(0xcc060,bytes(191*50))
    oracle.allowed.update(range(0xcc060,0xcc060+191*50));oracle.allowed.update(range(0xcc040,0xcc044))
    for ident in [55,57,58,59,60,61,62,63,64]:oracle.write(0xcc090+ident*50,1,1)
    oracle.call(0x38488,0,0,0,0)
    for ident in [55,57,58,59,60,61,62,63,64]:
        assert oracle.read(0xcc074+ident*50,4)==0 and oracle.read(0xcc078+ident*50,4)==0
    for filename in ['step_test.dll','step_test_debug.dll']:
        d=bind(ROOT/'build'/filename)
        for name in ['tomb_trigger_active','tomb_door_control']:
            getattr(d,name).argtypes=[C.POINTER(Object)]
        d.tomb_switch_trigger.argtypes=[C.POINTER(Object),I16]
        d.tomb_object_trigger.argtypes=[C.POINTER(Object),C.c_int,C.c_uint16]
        d.tomb_object_animate.argtypes=[C.POINTER(Object),C.POINTER(AnimContext)]
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p
        d.tomb_visual_free.argtypes=[C.c_void_p]
        d.tomb_objects_init.argtypes=[C.POINTER(Objects),C.POINTER(Level),C.c_void_p]
        d.tomb_objects_free.argtypes=[C.POINTER(Objects)]
        d.tomb_objects_tick.argtypes=[C.POINTER(Objects),C.POINTER(AnimContext)]
        oracle.install(fixture)
        for mode in ['timer','switch','activation']:
            for i in range(6000):
                current=rng.randrange(2);active=rng.randrange(2)
                a=Actor(100,200,300,current,current,233,0,0,0,0,9,32|rng.choice([0,2,4,6])|active)
                o=Object(a,rng.choice([0,0x3e00,0x4000,0x7e00,rng.randrange(65536)]),rng.choice([-32768,-2,-1,0,1,2,30,660,32767]),55,active)
                oracle.put_object(o)
                if mode=='timer':
                    expected=oracle.call(0x18060,ITEMS,0,0,0);actual=d.tomb_trigger_active(C.byref(o));assert actual==expected
                elif mode=='switch':
                    timer=rng.choice([-1,0,1,2,22,255,32767]);expected=oracle.call(0x34bd8,0,timer,0,0)
                    actual=d.tomb_switch_trigger(C.byref(o),timer);assert actual==expected
                else:
                    kind=rng.choice([0,1,2,6]);flags=rng.randrange(65536)
                    # Non-intelligent activation path. Camera refresh and switch gate are explicit doubles.
                    oracle.write(0xcc090+55*50,0,1);oracle.write(0xcb298,0,1)
                    oracle.write(0xce960,ITEM,4);oracle.write(ITEM,0,4);oracle.write(ITEM+0x34,0,4)
                    words=[0x8004|(kind<<8),flags]+([1] if kind==2 else [])+[0x8000]
                    oracle.uc.mem_write(DATA,struct.pack('<'+'H'*len(words),*words));oracle.skip_switch=True
                    oracle.call(0x17a40,DATA,0,0,0);oracle.skip_switch=False
                    d.tomb_object_trigger(C.byref(o),kind,flags)
                oracle.compare(o)
        err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);assert l
        v=d.tomb_visual_load(l,err,256);assert v
        # Original initialization on actual sector data, including both sides of each door.
        oracle.install(fixture);w=Objects();assert d.tomb_objects_init(C.byref(w),l,v)
        doors=0
        for i in range(w.count):
            o=w.items[i]
            if not 57<=o.object<=64:continue
            oracle.put_object(o,i);oracle.call(0x2f5bc,i,0,0,0);doors+=1
            ptr=oracle.read(ITEMS+68*i+0x2c,4);parts=w.doors[i].parts
            j=0
            for k in range(4):
                sp=oracle.read(ptr+14*k,4)
                if not sp:continue
                cp=parts[j];j+=1;base,_=oracle.sectors[cp.ref.room]
                assert sp==base+8*cp.ref.index,(i,k,sp,cp.ref.room,cp.ref.index)
                assert bytes(cp.saved)==bytes(oracle.uc.mem_read(ptr+14*k+4,8)),(i,k,'saved')
                assert cp.box==oracle.read(ptr+14*k+12,2),(i,k,'box')
            assert j==w.doors[i].count
        for ri,(base,n) in enumerate(oracle.sectors):
            assert C.string_at(l.contents.rooms[ri].sectors,n*8)==bytes(oracle.uc.mem_read(base,n*8)),('closed sectors',ri)
        for i in range(l.contents.box_count):assert l.contents.boxes[i].overlap==(oracle.read(BOXES+20*i+18,2)&65535)
        @EVENT
        def silent(user,kind,ident,a):pass
        lv=l.contents;doorctx=AnimContext(lv.animations,lv.animation_count,lv.changes,lv.change_count,lv.ranges,lv.range_count,lv.commands,lv.command_count,oracle.sine,0,0,0,silent,None)
        for i in range(w.count):
            o=w.items[i]
            if not 57<=o.object<=64:continue
            o.active=1;o.actor.flags|=3;o.flags=0x3e00;o.timer=90
            oracle.write(ITEMS+68*i+0x42,o.actor.flags,1);oracle.write(ITEMS+68*i+0x28,o.flags,2);oracle.write(ITEMS+68*i+0x26,o.timer,2)
        for tick in range(300):
            if tick==200:
                for i in range(w.count):
                    o=w.items[i]
                    if not 57<=o.object<=64:continue
                    o.timer=0;oracle.write(ITEMS+68*i+0x26,0,2)
            for i in range(w.count):
                if 57<=w.items[i].object<=64:oracle.call(0x2fb30,i,0,0,0)
            assert d.tomb_objects_tick(C.byref(w),C.byref(doorctx))
            for i in range(w.count):
                if 57<=w.items[i].object<=64:oracle.compare(w.items[i],i)
            for ri,(base,n) in enumerate(oracle.sectors):
                assert C.string_at(l.contents.rooms[ri].sectors,n*8)==bytes(oracle.uc.mem_read(base,n*8)),('door tick',tick,ri)
            for i in range(l.contents.box_count):assert l.contents.boxes[i].overlap==(oracle.read(BOXES+20*i+18,2)&65535)
        # Unmodified original stationary AnimateItem with real switch/door animations.
        oracle.install(fixture);events=[]
        @EVENT
        def event(user,kind,ident,a):events.append((kind,ident,state(a.contents)))
        lv=l.contents;ctx=AnimContext(lv.animations,lv.animation_count,lv.changes,lv.change_count,lv.ranges,lv.range_count,lv.commands,lv.command_count,oracle.sine,0,0,0,event,None)
        cases=0
        for anim in range(233,253):
            an=lv.animations[anim]
            for frame in range(an.first_frame,an.last_frame+1):
                for goal in [0,1]:
                    a=Actor(100,200,300,an.state,goal,anim,frame,0,0,0,9,35);o=Object(a,0,0,55 if anim<237 else 57,1)
                    oracle.put_object(o);oracle.events=[];events.clear();oracle.call(0x16ff4,ITEMS,0,0,0)
                    assert d.tomb_object_animate(C.byref(o),C.byref(ctx));oracle.compare(o)
                    # Parent oracle sound actor reads ITEM; compare kind/id plus actor separately.
                    assert [(e[0],e[1]) for e in events]==[(e[0],e[1]) for e in oracle.events]
                    cases+=1
        d.tomb_objects_free(C.byref(w))
        for ri,r in enumerate(fixture['rooms']):
            expected=b''.join(struct.pack('<HHBbBb',*sec) for sec in r['sectors'])
            assert C.string_at(l.contents.rooms[ri].sectors,len(expected))==expected,('restore',ri)
        d.tomb_visual_free(v);d.tomb_level_free(l)
        results.append({'build':filename,'timer_switch_activation_cases':18000,'doors_initialized':doors,'animation_cases':cases,'door_control_ticks':2400})
    (ROOT/'analysis/object-validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print('PASS: DOS object validation',results)
if __name__=='__main__':main()
