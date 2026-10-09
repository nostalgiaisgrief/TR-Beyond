"""Original hanging maintenance and real animation-bounds comparisons."""
from compare_ledge import *
from compare_visual import Visual,bind,parse,Level,SZ
class Hang(C.Structure):
    _fields_=[('query',QUERY),('bounds_min_y',BOUNDS),('samples',C.POINTER(Samples)),('user',C.c_void_p),('input',C.c_uint32),('health',I16),('weapon_status',I16),('move_angle',I16)]
class HangOracle(LedgeOracle):
    def __init__(self):
        super().__init__();self.query_count=0;self.health=1000;self.query_samples=[Samples(),Samples()]
    def put(self,base,s,fields):
        super().put(base,s,fields)
        if base==ITEM:self.write(ITEM+0x22,self.health,2)
    def external(self,uc,address,size,data):
        if address==0x151c0:
            super().external(uc,address,size,data)
            sample=self.query_samples[self.query_count];self.query_count+=1
            for n,off in [('ceiling',4),('front_floor',12),('front_ceiling',16),('left_floor',24),('right_floor',36)]:self.write(COLL+off,getattr(sample,n),4)
            return
        super().external(uc,address,size,data)
def main():
    oracle=HangOracle();libs=[setup_library(ROOT/'build'/f'step_test{s}.dll') for s in ('','_debug')]
    for d in libs:
        d.tomb_hang_maintain.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Hang)]
        d.tomb_shimmy_collision.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Hang),C.c_int]
    rng=random.Random(19961015)
    for i in range(36000):
        a=Actor(x=rng.choice([-2147483648,123,2147483647]),y=-1000,z=789,current=rng.choice([10,30,31]),goal=10,animation=96,frame=1514,fall_speed=45,speed=30,yaw=rng.randrange(-32768,32768),flags=rng.randrange(256),room=7)
        c=Contact(old_x=100,old_y=-1100,old_z=800,type=rng.choice([0,1,1,1,2]),shift_x=7,shift_y=999,shift_z=-3)
        inp=rng.choice([0,64,64,64]);oracle.health=rng.choice([-1,0,1000,1000,1000]);weapon=1;move=rng.randrange(-32768,32768)
        oracle.bounds=[rng.choice([-1000,-700,-500]),-700]
        oracle.query_samples=[Samples(-600,rng.choice([199,200,201]),0,0,0),Samples(rng.choice([-1,-400,0]),rng.choice([-1100,-1000,-744,-700,-500,-444,-443]),0,0,rng.choice([-60,-59,0,59,60]))]
        oracle.query_count=0;oracle.write(0xce92c,inp,4);oracle.write(0xce966,weapon,2);oracle.write(0xce9ce,move,2)
        mode=i%3; expected=oracle.run([0x2769c,0x26e60,0x26e90][mode],a,c);ec=oracle.get(COLL,Contact,CONTACT);ew=oracle.read(0xce966,2);em=oracle.read(0xce9ce,2);ee=oracle.events[:]
        for d in libs:
            events=[];samples=Samples();count=[0]
            @QUERY
            def query(_,pa,pc,h):
                events.append(('query',state(pa.contents),state(pc.contents),h))
                C.memmove(C.byref(samples),C.byref(oracle.query_samples[count[0]]),C.sizeof(samples));count[0]+=1
            @BOUNDS
            def bounds(_,pa):events.append(('bounds',state(pa.contents)));return oracle.bounds[0]
            actual=clone(a);contact=clone(c);ctx=Hang(query,bounds,C.pointer(samples),None,inp,oracle.health,weapon,move)
            if mode: d.tomb_shimmy_collision(C.byref(actual),C.byref(contact),C.byref(ctx),mode==2)
            else: d.tomb_hang_maintain(C.byref(actual),C.byref(contact),C.byref(ctx))
            assert state(actual)==state(expected),(i,state(actual),state(expected))
            assert state(contact)==state(ec) and ctx.weapon_status==ew and ctx.move_angle==em and events==ee,(i,events,ee)
    # Actual PHD animation and frame bytes installed in original memory layout.
    original=Oracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'));original.uc.mem_map(0x400000,0x400000);original.allowed.update(range(0xcc020,0xcc02c))
    loaded=[];cases=0
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name;fixture=parse(path);sections=fixture['sections'];raw=bytearray(sections['animations']['bytes']);frames=sections['frames']['bytes']
        for n in range(len(raw)//32):struct.pack_into('<I',raw,n*32,struct.unpack_from('<I',raw,n*32)[0]+0x400000)
        original.uc.mem_write(DATA,bytes(raw));original.uc.mem_write(0x400000,frames);original.write(0xcc03c,DATA,4);original.write(0xcc060,15,2)
        for suffix in ('','_debug'):
            d=bind(ROOT/'build'/f'step_test{suffix}.dll');d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.POINTER(Visual);d.tomb_visual_free.argtypes=[C.POINTER(Visual)];d.tomb_visual_bounds.argtypes=[C.POINTER(Visual),C.POINTER(Actor),C.POINTER(I16)]
            error=C.create_string_buffer(256);l=d.tomb_level_load(str(path).encode(),error,256);v=d.tomb_visual_load(l,error,256);assert v;loaded.append((d,l,v))
        for n in range(len(raw)//32):
            off,rate=struct.unpack_from('<IH',sections['animations']['bytes'],n*32);first,last=struct.unpack_from('<hh',raw,n*32+16)
            if struct.unpack_from('<H',frames,off+18)[0]!=15:continue
            for frame in range(first,last+1):
                a=Actor(animation=n,frame=frame)
                original.put(ITEM,a,ACTOR);original.write(ITEM+0xc,0,2);original.write(STACK+0x800,RETURN,4);original.uc.reg_write(UC_X86_REG_EAX,ITEM);original.uc.reg_write(UC_X86_REG_ESP,STACK+0x800);original.bad=[]
                original.uc.emu_start(0x1d444,RETURN,count=1000);assert not original.bad
                expected=list(struct.unpack('<6h',original.uc.mem_read(original.uc.reg_read(UC_X86_REG_EAX),12)))
                for d,l,v in loaded:
                    result=(I16*6)();assert d.tomb_visual_bounds(v,C.byref(a),result),(name,n,frame);assert list(result)==expected,(name,n,frame,list(result),expected)
                cases+=1
        for d,l,v in loaded:d.tomb_visual_free(v);d.tomb_level_free(l)
        loaded=[]
    (ROOT/'analysis/c-hang-validation.json').write_text(json.dumps(dict(hanging_cases=12000,shimmy_cases=24000,bounds_frames=cases,builds=2,scope='Hang queries/bounds doubled; bounds interpolation uses actual GYM and LEVEL1 frames in DOS.'),indent=2)+'\n')
    print('PASS: 36000 hanging/release/shimmy cases and',cases,'real animation bounds per build')
if __name__=='__main__':main()
