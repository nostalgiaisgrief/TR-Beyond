"""Execute original DOS sliding; collision queries are controlled identically.
Entry selection, contact shifts, wall/ceiling responses and controls run unmodified.
"""
import ctypes as C
import json, random, sys
from pathlib import Path
from compare_step import *
class Slide(C.Structure):
    _fields_=[('query',QUERY),('user',C.c_void_p),('move_angle',I16),('last_angle',I16),('tilt_x',C.c_int8),('tilt_z',C.c_int8)]
class SlideOracle(Oracle):
    def __init__(self):
        super().__init__(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
        for addr,width in [(0xc3880,2),(0xcb29d,4),(0xcb2bd,2)]:self.allowed.update(range(addr,addr+width))
        self.tx=self.tz=0
    def put(self,base,s,fields):
        super().put(base,s,fields)
        if base==COLL:
            self.write(COLL+0x62,self.tx,1);self.write(COLL+0x63,self.tz,1)
    def external(self,uc,address,size,data):
        if address!=0x28128:super().external(uc,address,size,data)

def main():
    oracle=SlideOracle();results=[]
    for name in ['step_test.dll','step_test_debug.dll']:
        lib=C.CDLL(str((ROOT/'build'/name).resolve()))
        lib.tomb_slide_start.argtypes=[C.POINTER(Actor),C.POINTER(Contact),C.POINTER(Slide)]
        lib.tomb_slide_collision.argtypes=lib.tomb_slide_start.argtypes
        lib.tomb_slide_control.argtypes=[C.POINTER(Actor),C.c_uint32,C.POINTER(I32),C.POINTER(I16)]
        rng=random.Random(1996);counts={}
        for kind,count in [('start',6000),('collision',6000),('control',1000)]:
            for i in range(count):
                tx=rng.choice([-128,-8,-3,-2,0,2,3,8,127]);tz=rng.choice([-128,-8,-3,-2,0,2,3,8,127])
                current=rng.choice([2,24,32]) if kind=='start' else rng.choice([24,32])
                a=Actor(40000,1024,30000,current,rng.choice([2,3,24,25,32]),70,1140,50,0,rng.choice([-32768,-16385,-16384,-1,0,16384,16385,32767]),4,0)
                c=Contact(floor=rng.choice([-512,-1,0,100,200,201,500]),positive_limit=384,negative_limit=-384,ceiling_limit=0,
                    shift_x=17,shift_y=-3,shift_z=29,old_x=39950,old_y=1000,old_z=30030,facing=0,type=rng.choice([0,1,2,4,8,16,32]),flags=24)
                original=clone(a);contact=clone(c);events=[]
                @QUERY
                def query(user,ap,cp,height):events.append(('query',state(ap.contents),state(cp.contents),height))
                s=Slide(query,None,rng.randint(-32768,32767),rng.choice([-32768,-16384,0,16384]),tx,tz)
                oracle.tx,oracle.tz=tx,tz
                oracle.write(0xce9ce,s.move_angle,2);oracle.write(0xc3880,s.last_angle,2)
                mode=I32(7);elevation=I16(1234);input=rng.getrandbits(12)
                oracle.write(0xcb29d,mode.value,4);oracle.write(0xcb2bd,elevation.value,2);oracle.write(0xce92c,input,4)
                addr=0x28128 if kind=='start' else (0x26cc8 if current==24 else 0x26eb8) if kind=='collision' else (0x25a64 if current==24 else 0x25b70)
                expected=oracle.run(addr,original,contact)
                if kind=='start':
                    result=lib.tomb_slide_start(C.byref(a),C.byref(c),C.byref(s))
                    assert result==oracle.uc.reg_read(UC_X86_REG_EAX)
                elif kind=='collision':lib.tomb_slide_collision(C.byref(a),C.byref(c),C.byref(s))
                else:
                    lib.tomb_slide_control(C.byref(a),input,C.byref(mode),C.byref(elevation))
                    assert mode.value==oracle.read(0xcb29d,4) and elevation.value==oracle.read(0xcb2bd,2)
                assert state(a)==state(expected),(kind,i,tx,tz,state(a),state(expected))
                assert state(c)==state(oracle.get(COLL,Contact,CONTACT)),(kind,i,'contact')
                assert s.move_angle==oracle.read(0xce9ce,2) and s.last_angle==oracle.read(0xc3880,2),(kind,i,'angles')
                assert events==oracle.events,(kind,i,'query')
            counts[kind]=count
        results.append({'build':name,'cases':counts})
    (ROOT/'analysis/slide-comparison.json').write_text(json.dumps(results,indent=2)+'\n')
    print('DOS slide comparison passed:',results)
if __name__=='__main__':main()
