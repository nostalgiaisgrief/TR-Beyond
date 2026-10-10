"""Original LOT breadth-first search and corridor target clipping on Caves boxes."""
from compare_creatures import *
class Node(C.Structure):_fields_=[('exit',I16),('search',U16),('next',I16),('zone_box',I16)]
class Navigation(C.Structure):_fields_=[('nodes',C.POINTER(Node)),('head',I16),('tail',I16),('search',U16),('block',U16)]+[(n,I16) for n in ('step','drop','fly','zone_count','target_box','required_box')]+[(n,I32) for n in ('x','y','z')]
LOT=DOORS+256;NODES=0x7c0000;ZONES=0x7d0000;OVERLAPS=0x7e0000
NAV={n:(off,w) for n,off,w in [('head',4,2),('tail',6,2),('search',8,2),('block',10,2),('step',12,2),('drop',14,2),('fly',16,2),('zone_count',18,2),('target_box',20,2),('required_box',22,2),('x',24,4),('y',28,4),('z',32,4)]}
def install_navigation(o,lv):
    o.uc.mem_write(ZONES,C.string_at(lv.zones,lv.box_count*12));o.uc.mem_write(OVERLAPS,C.string_at(lv.overlaps,lv.overlap_count*2))
    for i,ptr in enumerate([0xcb25c,0xcb264,0xcb254]):
        o.write(ptr,ZONES+i*lv.box_count*2,4);o.write(ptr+4,ZONES+(i+3)*lv.box_count*2,4)
    o.write(0xcb26c,OVERLAPS,4);o.write(0xcb274,lv.box_count,4);o.write(0xcb3a4,0,4)
    o.allowed.update(range(NODES,NODES+lv.box_count*8));o.allowed.update(range(0xc19a4,0xc19a8));o.allowed.update(range(DATA,DATA+256))
def put_navigation(o,n,count):
    o.write(LOT,NODES,4);o.uc.mem_write(NODES,C.string_at(n.nodes,count*8))
    for name,(off,w) in NAV.items():o.write(LOT+off,getattr(n,name),w)
def check_navigation(o,n,count):
    for name,(off,w) in NAV.items():
        val=o.read(LOT+off,w);val=val&65535 if name in ('search','block') else val
        assert getattr(n,name)==val,(name,getattr(n,name),val)
    assert C.string_at(n.nodes,count*8)==bytes(o.uc.mem_read(NODES,count*8)),'nodes'
def main():
    level_name=sys.argv[1] if len(sys.argv)>1 else 'LEVEL1';report='valley-navigation' if level_name=='LEVEL3A' else 'navigation'
    f=parse(ROOT/'work/reference-assets/DATA'/f'{level_name}.PHD');o=ObjectOracle();o.instruction_limit=100000;o.install(f);results=[]
    o.uc.hook_add(UC_HOOK_CODE,lambda u,a,size,data:o.ret(DATA+128),begin=0x1d4b8,end=0x1d4b8)
    o.write(DATA+128+4,-762,2);o.write(0xce960,ITEM,4)
    for suffix in ('','_debug'):
        rng=random.Random(19961015);d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256);l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA'/f'{level_name}.PHD').encode(),err,256);lv=l.contents;install_navigation(o,lv)
        d.tomb_navigation_init.argtypes=[C.POINTER(Navigation),C.POINTER(Level),C.POINTER(Actor),C.c_int]
        d.tomb_navigation_free.argtypes=[C.POINTER(Navigation)]
        d.tomb_navigation_target_box.argtypes=[C.POINTER(Navigation),C.POINTER(Level),C.c_int,C.POINTER(C.c_uint32)]
        d.tomb_navigation_target.argtypes=[C.POINTER(Navigation),C.POINTER(Level),C.POINTER(Actor),C.c_int,C.POINTER(C.c_uint32),C.POINTER(I32)]
        d.tomb_navigation_box.argtypes=[C.POINTER(Level),C.POINTER(Actor)]
        d.tomb_creature_info.argtypes=[C.POINTER(Info),C.POINTER(Creature),C.POINTER(Navigation),C.POINTER(Level),C.POINTER(Actor),C.c_int,C.POINTER(Actor),C.POINTER(I16)]
        d.tomb_creature_mood.argtypes=[C.POINTER(Creature),C.POINTER(Navigation),C.POINTER(Level),C.POINTER(Actor),C.c_int,C.POINTER(Info),C.POINTER(Actor),I16,C.c_int,I16,C.POINTER(C.c_uint32)]
        cases=0;moods=0
        for it in [it for it in f['items'] if it[0] in (7,8,9,18,19)]:
            a=Actor(it[2],it[3],it[4],0,0,0,0,0,0,it[5],it[1],35);n=Navigation();assert d.tomb_navigation_init(C.byref(n),l,C.byref(a),it[0])
            box=d.tomb_navigation_box(l,C.byref(a));put_navigation(o,n,lv.box_count)
            seed=C.c_uint32(0xdeadbeef);o.write(0xc19a4,seed.value,4)
            for tick in range(100):
                if tick%7==0:
                    target=rng.randrange(lv.box_count);o.call(0x11b9c,LOT,target,0,0);d.tomb_navigation_target_box(C.byref(n),l,target,C.byref(seed));check_navigation(o,n,lv.box_count)
                # Real original search and target clipping, including RNG use.
                o.put_object(Object(a,0,0,it[0],1));o.write(ITEMS+0x24,box,2);out=(I32*3)()
                expected=o.call(0x122fc,DATA,ITEMS,LOT,0)&255;actual=d.tomb_navigation_target(C.byref(n),l,C.byref(a),box,C.byref(seed),out)
                assert actual==expected and tuple(out)==struct.unpack('<3i',o.uc.mem_read(DATA,12)),(it,tick,actual,expected,tuple(out),struct.unpack('<3i',o.uc.mem_read(DATA,12)))
                check_navigation(o,n,lv.box_count);assert seed.value==o.read(0xc19a4,4)&0xffffffff;cases+=1
            for tick in range(150):
                p=rng.choice(f['items']);lara=Actor(p[2],p[3],p[4],0,0,0,0,0,0,rng.randrange(-32768,32768),p[1],32)
                if d.tomb_navigation_box(l,C.byref(lara))<0:continue
                a.yaw=rng.randrange(-32768,32768);a.flags=35|rng.choice([0,16]);c=Creature();c.mood=rng.randrange(4)
                o.put_object(Object(a,0,0,it[0],1));o.put(ITEM,lara,ACTOR);o.write(ITEM+0x22,1000,2);o.write(ITEMS+0x2c,LOT-11,4);o.write(LOT-1,c.mood,1);o.write(0xce96e,0,2)
                for off,val in [(40,{7:375,8:500,18:2000,19:400}.get(it[0],0)),(44,{7:8192,8:16384,18:32767,19:16384}.get(it[0],1024))]:o.write(0xcc060+it[0]*50+off,val,2)
                info=Info();o.call(0x11674,ITEMS,DATA,0,0);d.tomb_creature_info(C.byref(info),C.byref(c),C.byref(n),l,C.byref(a),it[0],C.byref(lara),o.sine)
                assert bytes(info)==bytes(o.uc.mem_read(DATA,20)),('info',it,tick,state(info),state(Info.from_buffer_copy(o.uc.mem_read(DATA,20))))
                o.call(0x11eb4,ITEMS,DATA,int(it[0] in (8,18,19)),0);d.tomb_creature_mood(C.byref(c),C.byref(n),l,C.byref(a),it[0],C.byref(info),C.byref(lara),1000,0,-762,C.byref(seed))
                assert c.mood==o.read(LOT-1,1),('mood',it,tick,c.mood,o.read(LOT-1,1))
                check_navigation(o,n,lv.box_count)
                assert (c.target_x,c.target_y,c.target_z)==struct.unpack('<3i',o.uc.mem_read(LOT+36,12)),('mood target',it,tick)
                assert seed.value==o.read(0xc19a4,4)&0xffffffff,('mood RNG',it,tick)
                moods+=1
            d.tomb_navigation_free(C.byref(n))
        d.tomb_level_free(l);results.append(dict(build=suffix or 'release',search_and_target_ticks=cases,info_and_mood_ticks=moods))
    (ROOT/'analysis'/f'{report}-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS LOT navigation',results)
if __name__=='__main__':main()
