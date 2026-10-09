"""DOS Caves hazard control/animation and original horizontal projection.
Original animation/geometry run in floor traces; allocation/particle/list services
are isolated doubles. Emitter tests capture its spawn before InitialiseItem.
"""
from compare_objects import *
class Effect(C.Structure):
    _fields_=[('x',I32),('y',I32),('z',I32)]+[(k,I16) for k in ['room','id','frame','counter','speed','yaw']]+[('active',C.c_int)]
class Dart(C.Structure):_fields_=[('item',Object),('touching',C.c_int)]
class Hazards(C.Structure):_fields_=[('effects',Effect*256),('random',C.c_uint32),('darts',Dart*256),('spawned',C.c_uint),('hits',C.c_uint),('impacts',C.c_uint)]
class HazardOracle(ObjectOracle):
    def __init__(self):
        super().__init__();self.spawn=None;self.noanimate=False;self.killed=False
        self.allowed.update(range(0x12f388,0x12f3d8))
        for addr in [0x24838,0x24870,0x24db8,0x24bc4,0x16ff4,0x24e28,0x24754,0x1d5f4]:self.uc.hook_add(UC_HOOK_CODE,self.hazard,begin=addr,end=addr)
    def hazard(self,u,addr,size,data):
        if addr==0x1d5f4:self.ret(pop=8)
        elif addr in [0x24e28,0x24754]:self.killed=True;self.ret()
        elif addr==0x24838:self.ret(900)
        elif addr==0x24870:
            self.spawn=self.get(ITEMS+900*68,Actor,ACTOR);self.ret()
        elif addr==0x24db8:self.ret(0xffffffff)
        elif addr==0x24bc4:
            at=ITEMS+68*u.reg_read(UC_X86_REG_EAX);self.write(at+0x18,u.reg_read(UC_X86_REG_EDX),2);self.ret()
        elif self.noanimate:self.ret()

def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=HazardOracle();rng=random.Random(19961012);results=[]
    for suffix in ('','_debug'):
        d=bind(ROOT/'build'/f'step_test{suffix}.dll')
        d.tomb_object_animate.argtypes=[C.POINTER(Object),C.POINTER(AnimContext)]
        d.tomb_dart_emit.argtypes=[C.POINTER(Object),C.POINTER(AnimContext),C.POINTER(Actor)]
        d.tomb_floor_control.argtypes=[C.POINTER(Object),I32]
        d.tomb_preview_focal.argtypes=[C.c_int]
        err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);lv=l.contents
        @EVENT
        def event(*args):pass
        ctx=AnimContext(lv.animations,lv.animation_count,lv.changes,lv.change_count,lv.ranges,lv.range_count,lv.commands,lv.command_count,o.sine,0,0,0,event,None)
        o.install(f);o.write(0xce960,ITEM,4)
        # Original FOV setup independently evaluates original sine/cos tables.
        for width in range(160,4097):
            o.write(0x12f3ac,width,4);o.call(0x3f01c,14560,0,0,0)
            assert d.tomb_preview_focal(width)==o.read(0x12f3a0,4),width
        d.tomb_hazard_effect_tick.argtypes=[C.POINTER(Effect),C.c_int,C.POINTER(I16)]
        o.allowed.update(range(FX,FX+36));o.write(0xce954,FX,4);effects=0
        for id,fn,frames in [(158,0x1d660,6),(160,0x3af54,6),(164,0x1d7dc,3)]:
            o.write(0xcc060+50*id,-frames,2)
            for case in range(100):
                e=Effect(74752,2560,22016,6,id,rng.randrange(frames),rng.randrange(1,7) if id==164 else rng.randrange(3 if id==160 else 4),rng.randrange(150),rng.randrange(-32768,32768),1)
                o.uc.mem_write(FX,bytes(36))
                for offset,value,width in [(0,e.x,4),(4,e.y,4),(8,e.z,4),(14,e.yaw,2),(20,id,2),(26,e.speed,2),(30,-e.frame,2),(32,e.counter,2)]:o.write(FX+offset,value,width)
                o.killed=False;o.call(fn,0,0,0,0);d.tomb_hazard_effect_tick(C.byref(e),frames,o.sine)
                assert (e.x,e.y,e.z,e.frame,e.counter,bool(e.active))==(o.read(FX,4),o.read(FX+4,4),o.read(FX+8,4),-o.read(FX+30,2),o.read(FX+32,2),not o.killed)
                effects+=1
        animation=0
        for index in list(range(223,227))+[230,231,232]:
            an=lv.animations[index]
            for frame in range(an.first_frame,an.last_frame+1):
                for flags in [35,43]:
                    a=Actor(36352,2560,74240,an.state,rng.randrange(4) if index<227 else an.state,index,frame,130,rng.choice([0,120,128,200]),rng.randrange(-32768,32768),32,flags)
                    obj=Object(a,0,0,35 if index<227 else 39,1);o.put_object(obj);o.call(0x16ff4,ITEMS,0,0,0)
                    assert d.tomb_object_animate(C.byref(obj),C.byref(ctx));o.compare(obj);animation+=1
        # Isolated decisions: stop at AnimateItem, before later geometry work.
        o.noanimate=True
        for n in range(1200):
            current=rng.randrange(2);an=lv.animations[231+current]
            a=Actor(76288,3072,22016,current,current,231+current,rng.randrange(an.first_frame,an.last_frame+1),0,0,rng.choice([0,16364,16384,-32768,-16384]),6,35)
            obj=Object(a,rng.choice([0,0x3e00,0x4000,0x7e00]),rng.choice([-1,0,1,2,30]),40,1);o.put_object(obj);o.spawn=None
            o.call(0x3ac80,0,0,0,0);spawn=Actor();got=d.tomb_dart_emit(C.byref(obj),C.byref(ctx),C.byref(spawn));o.compare(obj)
            assert bool(got)==bool(o.spawn)
            if got:
                for k in ['x','y','z','yaw','room']:assert getattr(spawn,k)==getattr(o.spawn,k),(n,k,state(spawn),state(o.spawn))
        o.noanimate=False
        # Complete falling-floor trajectories with actual room geometry.
        floor_ticks=0
        for start in [50,51]:
            for stay in [False,True]:
                o.install(f);o.write(0xce960,ITEM,4)
                it=f['items'][start];a=Actor(it[2],it[3],it[4],0,0,223,0,0,0,it[5],it[1],35);obj=Object(a,0,0,35,1)
                for tick in range(130):
                    y=it[3]-512 if stay else it[3]-600
                    o.write(ITEM+0x34,y,4);o.put_object(obj,start);o.call(0x3a728,start,0,0,0)
                    if d.tomb_floor_control(C.byref(obj),y):
                        assert d.tomb_object_animate(C.byref(obj),C.byref(ctx))
                        if obj.actor.flags&6==4:obj.active=0;obj.actor.flags &=~1
                        else:
                            ref=Ref();h=Heights();a=obj.actor
                            assert d.tomb_find_sector(l,a.x,a.y,a.z,a.room,C.byref(ref));a.room=ref.room
                            assert d.tomb_static_heights(l,ref,a.x,a.z,0,C.byref(h))
                            if a.current==2 and a.y>=h.floor:a.goal=3;a.y=h.floor;a.fall_speed=0;a.flags &=~8
                    o.compare(obj,start);floor_ticks+=1
                    if not obj.active:break
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p
        d.tomb_visual_free.argtypes=[C.c_void_p]
        d.tomb_hazards_tick.argtypes=[C.POINTER(Objects),C.POINTER(AnimContext),C.POINTER(Actor),C.POINTER(I16)]
        v=d.tomb_visual_load(l,err,256);items=(Object*lv.item_count)();haz=Hazards();world=Objects();world.level=l;world.visual=v;world.items=items;world.count=lv.item_count;world.hazards=C.addressof(haz)
        dart_ticks=0
        for item in [i for i in f['items'] if i[0]==40]:
            o.install(f);o.write(0xce960,ITEM,4);o.uc.mem_write(ITEM,bytes(68));health=I16(1000);lara=Actor();o.write(ITEM+0x22,1000,2)
            C.memset(C.byref(haz),0,C.sizeof(haz));haz.darts[0].item=Object(Actor(item[2],item[3]-512,item[4],0,0,230,0,130,0,item[5],item[1],35),0,0,39,1)
            for tick in range(100):
                dart=haz.darts[0];dart.touching=int(tick%5==0);o.put_object(dart.item,900);o.write(ITEMS+900*68+4,dart.touching,4);o.killed=False
                o.call(0x3ae20,900,0,0,0)
                assert d.tomb_hazards_tick(C.byref(world),C.byref(ctx),C.byref(lara),C.byref(health))
                assert state(dart.item.actor)==state(o.get(ITEMS+900*68,Actor,ACTOR)),('dart',item,tick,state(dart.item.actor),state(o.get(ITEMS+900*68,Actor,ACTOR)))
                assert health.value==o.read(ITEM+0x22,2) and lara.flags==o.read(ITEM+0x42,1)
                assert bool(dart.item.active)==(not o.killed);dart_ticks+=1
                if o.killed:break
        d.tomb_visual_free(v)
        d.tomb_level_free(l);results.append(dict(build=suffix or 'release',projection_widths=3937,effect_updates=effects,dart_ticks=dart_ticks,animation_cases=animation,emitter_cases=1200,falling_floor_ticks=floor_ticks))
    (ROOT/'analysis/hazard-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS hazards and projection',results)
if __name__=='__main__':main()
