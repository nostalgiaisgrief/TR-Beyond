"""Execute DOS text measurement/layout. Only the final sprite draw is captured.
PHD font mapping/rectangles are checked separately; no pixel equivalence claim.
"""
from compare_step import *
class Style(C.Structure):
    _fields_=[(n,I32) for n in ('x','y','scale_x','scale_y')]+[('letter_spacing',I16),('word_spacing',I16),('flags',C.c_uint16)]
class Glyph(C.Structure):_fields_=[(n,I32) for n in ('glyph','x','y','scale_x','scale_y')]
DRAW=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Glyph))
class TextOracle(Oracle):
    def __init__(self):
        super().__init__(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'));self.glyphs=[]
        self.uc.hook_add(UC_HOOK_CODE,self.sprite,begin=0x1f6e0,end=0x1f6e0)
    def sprite(self,u,addr,size,user):
        sp=u.reg_read(UC_X86_REG_ESP)
        self.glyphs.append((self.read(sp+8,4)-37,C.c_int32(u.reg_read(UC_X86_REG_EAX)).value,C.c_int32(u.reg_read(UC_X86_REG_EDX)).value,C.c_int32(u.reg_read(UC_X86_REG_ECX)).value,self.read(sp+4,4)))
        assert self.read(sp+12,4)==4096
        self.ret(pop=16)
    def call(self,fn):
        self.write(STACK+2048,RETURN,4);self.uc.reg_write(UC_X86_REG_ESP,STACK+2048);self.uc.reg_write(UC_X86_REG_EAX,DATA);self.glyphs=[];self.bad=[]
        self.uc.emu_start(fn,RETURN,count=20000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN and not self.bad,(hex(self.uc.reg_read(UC_X86_REG_EIP)),self.bad)
        return self.uc.reg_read(UC_X86_REG_EAX)
def main():
    o=TextOracle();rng=random.Random(19961016);o.write(0xce57e,37,2);o.write(0xc3f90,0,4)
    for suffix in ('','_debug'):
        d=C.CDLL(str(ROOT/'build'/f'step_test{suffix}.dll'));d.tomb_text_width.argtypes=[C.c_char_p,C.POINTER(Style)];d.tomb_text_layout.argtypes=[C.c_char_p,C.POINTER(Style),C.c_int,C.c_int,DRAW,C.c_void_p]
        texts=[b'',b'Caves',b'City of Vilcabamba',b'Small medipack  x1',b'0123456789',b'[]{}!?:;.,+-/\\',b'($~) accents',bytes(range(1,127))]
        for case in range(2000):
            text=texts[case] if case<len(texts) else bytes(rng.randrange(1,127) for _ in range(rng.randrange(1,64)))
            w,h=rng.choice([(320,200),(640,480),(1280,720),(853,641)])
            st=Style(rng.randrange(-120,121),rng.randrange(-50,100),rng.choice([32768,49152,65536,98304,131072]),rng.choice([32768,65536,98304]),rng.choice([1,1,0,2,8]),rng.choice([6,6,8,12]),rng.choice([0,16,32,128,256,48,144,384,304]))
            o.uc.mem_write(DATA,bytes(58));o.uc.mem_write(DATA+256,text+b'\0');o.write(DATA+54,DATA+256,4);o.write(DATA,1|st.flags,2)
            for offset,val,size in [(10,st.x,2),(12,st.y,2),(16,st.letter_spacing,2),(18,st.word_spacing,2),(46,st.scale_x,4),(50,st.scale_y,4)]:o.write(DATA+offset,val,size)
            o.write(0xc2054,w,2);o.write(0xc2056,h,2)
            assert d.tomb_text_width(text,C.byref(st))==o.call(0x3985c),(case,text)
            o.call(0x399bc);actual=[]
            @DRAW
            def draw(user,g):actual.append(tuple(getattr(g.contents,n) for n,_ in Glyph._fields_))
            count=d.tomb_text_layout(text,C.byref(st),w,h,draw,None)
            assert count==len(o.glyphs) and actual==o.glyphs,(case,text,actual,o.glyphs)
    (ROOT/'analysis/text-validation.json').write_text(json.dumps(dict(cases_per_build=2000,builds=2,scope=__doc__),indent=2))
    print('PASS: 2000 DOS text widths/aligned glyph streams per debug/release build')
if __name__=='__main__':main()
