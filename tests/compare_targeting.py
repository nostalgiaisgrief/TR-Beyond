"""Original target acquisition/retention with real Caves geometry and LOS."""
from compare_enemy_contact import *
from compare_pistols import Pistols
from compare_start import Start
def main():
    f=parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD');o=CameraOracle();o.install(f);o.install_models(f);results=[]
    o.allowed.update(range(0xce9c4,0xce9ca+2));o.allowed.update(range(0xce9e0,0xcea00));o.write(0xce960,ITEM,4)
    for suffix in ('','_debug'):
        rng=random.Random(19961021);d=bind(ROOT/'build'/f'step_test{suffix}.dll');err=C.create_string_buffer(256)
        d.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ];d.tomb_visual_load.restype=C.c_void_p;d.tomb_visual_free.argtypes=[C.c_void_p]
        l=d.tomb_level_load(str(ROOT/'work/reference-assets/DATA/LEVEL1.PHD').encode(),err,256);v=d.tomb_visual_load(l,err,256)
        d.tomb_objects_init.argtypes=[C.POINTER(Objects),C.POINTER(Level),C.c_void_p];d.tomb_objects_free.argtypes=[C.POINTER(Objects)]
        d.tomb_test_target.argtypes=[C.POINTER(Objects),C.POINTER(Start),C.POINTER(Pistols),C.POINTER(I16),C.c_int]
        w=Objects();assert d.tomb_objects_init(C.byref(w),l,v);e=C.cast(w.enemies,C.POINTER(Enemies)).contents
        ids=[i for i in range(w.count) if w.items[i].object in [7,8,9]];e.head=ids[0];o.write(0xce95e,ids[0],2)
        for at,id in enumerate(ids):e.next[id]=ids[at+1] if at+1<len(ids) else -1
        acquired=retained=0
        for case in range(2400):
            for id in ids:
                o.put_object(w.items[id],id);o.write(ITEMS+68*id+28,e.next[id],2);e.items[id].health=rng.choice([-1,6,6,6]);o.write(ITEMS+68*id+34,e.items[id].health,2)
            base=w.items[rng.choice(ids)].actor
            lara=Start();lara.actor=Actor(base.x+rng.randrange(-1500,1501),base.y+rng.randrange(-600,601),base.z+rng.randrange(-1500,1501),2,2,11,185,0,0,rng.randrange(-32768,32768),base.room,32);lara.pitch=rng.randrange(-5000,5001)
            g=Pistols();g.target=rng.choice([-1,*ids]);g.left.lock=rng.randrange(2);g.right.lock=rng.randrange(2);g.torso_yaw=rng.randrange(-6000,6001);g.torso_pitch=rng.randrange(-3000,3001)
            action=rng.randrange(2);o.put(ITEM,lara.actor,ACTOR);o.write(ITEM+0x3c,lara.pitch,2)
            for addr,value in [(0xce9d6,g.torso_yaw),(0xce9d8,g.torso_pitch),(0xce9e2,g.left.lock),(0xce9f2,g.right.lock)]:o.write(addr,value,2)
            o.write(0xce9c4,0 if g.target<0 or not action else ITEMS+68*g.target,4)
            if action:o.call(0x2a8c0,0xc3a44+46,0,0,0)
            if not o.read(0xce9c4,4):o.call(0x2aa58,0xc3a44+46,0,0,0)
            d.tomb_test_target(C.byref(w),C.byref(lara),C.byref(g),o.sine,action)
            expected=(o.read(0xce9c4,4)-ITEMS)//68 if o.read(0xce9c4,4) else -1
            assert g.target==expected,(case,'target',g.target,expected)
            for name,addr in [('target_yaw',0xce9c8),('target_pitch',0xce9ca)]:assert getattr(g,name)==o.read(addr,2),(case,name,getattr(g,name),o.read(addr,2))
            assert (g.left.lock,g.right.lock)==(o.read(0xce9e2,2),o.read(0xce9f2,2)),(case,'locks')
            acquired+=g.target>=0 and not action;retained+=g.target>=0 and action
        assert acquired>50 and retained>50
        d.tomb_objects_free(C.byref(w));d.tomb_visual_free(v);d.tomb_level_free(l);results.append(dict(build=suffix or 'release',cases=2400,acquired=acquired,retained=retained))
    (ROOT/'analysis/targeting-validation.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS: DOS target locks',results)
if __name__=='__main__':main()
