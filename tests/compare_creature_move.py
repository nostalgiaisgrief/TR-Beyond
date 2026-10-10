"""Original CreatureAnimation with real Caves animations and geometry.
The other-creature contact/list services are isolated in this component test.
"""
from compare_navigation import *
from compare_dos_camera import CameraOracle
class MotionOracle(CameraOracle):
    def __init__(self):
        super().__init__()
        for addr in [0x1275c,0x2ccfc,0x24bc4]:self.uc.hook_add(UC_HOOK_CODE,self.motion,begin=addr,end=addr)
    def motion(self,u,addr,size,data):
        if addr==0x24bc4:self.write(ITEMS+68*u.reg_read(UC_X86_REG_EAX)+0x18,u.reg_read(UC_X86_REG_EDX),2)
        self.ret(0)
def main():
    level_name=sys.argv[1] if len(sys.argv)>1 else 'LEVEL1';report='valley-creature-move' if level_name=='LEVEL3A' else 'creature-move'
    f=parse(ROOT/'work/reference-assets/DATA'/f'{level_name}.PHD');o=MotionOracle();o.install(f);o.install_models(f);results=[]
    for id in [7,8,9,18,19]:o.write(0xcc060+id*50+42,102 if id==9 else 341,2)
    bases={m[0]:m[-1] for m in struct.iter_unpack('<IHHIIH',f['sections']['models']['bytes'])}
    for suffix in ('','_debug'):
        rng=random.Random(19961016);d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA'/f'{level_name}.PHD').encode(),err,256);lv=l.contents;install_navigation(o,lv)
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p;v=d.tomb_visual_load(l,err,256);assert v
        d.tomb_visual_free.argtypes=[C.c_void_p]
        d.tomb_navigation_init.argtypes=[C.POINTER(Navigation),C.POINTER(Level),C.POINTER(Actor),C.c_int];d.tomb_navigation_free.argtypes=[C.POINTER(Navigation)]
        d.tomb_creature_move.argtypes=[C.POINTER(Object),C.POINTER(Creature),C.POINTER(Navigation),C.POINTER(Objects),C.POINTER(AnimContext),I16,I16]
        @EVENT
        def event(*args):pass
        ctx=AnimContext(lv.animations,lv.animation_count,lv.changes,lv.change_count,lv.ranges,lv.range_count,lv.commands,lv.command_count,o.sine,0,0,0,event,None)
        w=Objects();w.level=l;w.visual=v;w.count=1;cases=0
        for it in [it for it in f['items'] if it[0] in (7,8,9,18,19)]:
            for case in range(200):
                id=it[0];anim=bases[id]+rng.randrange({7:25,8:21,9:5,18:12,19:13}[id]);an=lv.animations[anim]
                ob=Object(Actor(it[2]+rng.randrange(-400,401),it[3],it[4]+rng.randrange(-400,401),an.state,rng.randrange(13) if id==7 else rng.randrange(10) if id==8 else rng.randrange(6),anim,rng.randrange(an.first_frame,an.last_frame+1),rng.randrange(80),rng.randrange(100),rng.randrange(-32768,32768),it[1],35),0,0,id,1)
                n=Navigation();assert d.tomb_navigation_init(C.byref(n),l,C.byref(ob.actor),id)
                a=ob.actor;c=Creature();c.health=10;c.required=rng.randrange(13);c.floor=it[3];c.target_y=it[3]+rng.randrange(-1000,1001);c.roll=rng.randrange(-2000,2001);c.pitch=rng.randrange(-1000,1001)
                turn=rng.randrange(-910,911);tilt=turn if id==7 else 0;w.items=C.pointer(ob)
                put_navigation(o,n,lv.box_count);o.put_object(ob);o.write(ITEMS+0x2c,LOT-11,4)
                for at,value,width in [(ITEMS+0x24,tomb_box(d,l,a),2),(ITEMS,c.floor,4),(ITEMS+0x22,c.health,2),(ITEMS+0x12,c.required,2),(ITEMS+0x40,c.roll,2),(ITEMS+0x3c,c.pitch,2),(LOT+40,c.target_y,4)]:o.write(at,value,width)
                expected=o.call(0x12910,0,turn,tilt,0);actual=d.tomb_creature_move(C.byref(ob),C.byref(c),C.byref(n),C.byref(w),C.byref(ctx),turn,tilt)
                assert actual==expected,('return',id,case,anim,actual,expected,state(ob.actor),state(o.get(ITEMS,Actor,ACTOR)))
                try:o.compare(ob)
                except AssertionError as e:raise AssertionError((id,case,anim,str(e)))
                for name,offset,width in [('required',0x12,2),('health',0x22,2),('roll',0x40,2),('pitch',0x3c,2),('floor',0,4)]:assert getattr(c,name)==o.read(ITEMS+offset,width),(id,case,anim,name,getattr(c,name),o.read(ITEMS+offset,width))
                d.tomb_navigation_free(C.byref(n));cases+=1
        d.tomb_visual_free(v);d.tomb_level_free(l);results.append(dict(build=suffix or 'release',movement_cases=cases))
    (ROOT/'analysis'/f'{report}-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS creature movement',results)
def tomb_box(d,l,a):
    d.tomb_navigation_box.argtypes=[C.POINTER(Level),C.POINTER(Actor)];return d.tomb_navigation_box(l,C.byref(a))
if __name__=='__main__':main()
