"""Compare tutorial conditions/latches/completion against DOS 0x18ce8.
Only physical playback/stop services are replaced, identically on both sides.
"""
import ctypes as C,struct,sys,random,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from compare_step import ROOT,Oracle,ITEM,STACK,RETURN
from unicorn import UC_HOOK_CODE
from unicorn.x86_const import *
class Gym(C.Structure):
    _fields_=[('tracks',C.c_uint16*64)]+[(n,C.c_int) for n in ('current_track','completion_ticks','complete')]+[('audio_serial',C.c_uint)]+[(n,C.c_int) for n in ('camera','camera_timer','camera_speed','last_camera')]+[('camera_once',C.c_uint64)]
o=Oracle(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'));u=o.uc;events=[]
def service(u,address,size,user):
    events.append(address)
    o.write(0xc17ac,u.reg_read(UC_X86_REG_EAX)&65535 if address==0x38f70 else 0,2)
    sp=u.reg_read(UC_X86_REG_ESP);ret=o.read(sp,4)
    u.reg_write(UC_X86_REG_ESP,sp+4);u.reg_write(UC_X86_REG_EIP,ret)
for address in (0x38f70,0x38d48):u.hook_add(UC_HOOK_CODE,service,begin=address,end=address)
dlls=[C.CDLL(str(ROOT/'build'/f'step_test{s}.dll')) for s in ('','_debug')]
for d in dlls:d.tomb_gym_audio.argtypes=[C.POINTER(Gym),C.c_int,C.c_uint16,C.c_int,C.c_int]
rng=random.Random(19961010)
for case in range(10000):
    g=Gym();g.current_track=rng.randrange(64);g.completion_ticks=rng.randrange(120)
    for i in range(64):g.tracks[i]=rng.choice([0,0x100,0x200,0x1e00,0x3e00,0x3f00])
    track=rng.choice([28,37,41,42,49,50,rng.randrange(64)]);flags=rng.choice([0x3f00,0x3e00,0,0x200,0x1000]);kind=rng.choice([0,2,6]);state=rng.choice([2,10,28,33,55])
    u.mem_write(0xcb2f4,bytes(g.tracks));o.write(0xc17ac,g.current_track,2);o.write(0xc17d0,g.completion_ticks,2);o.write(0xc192c,0,4)
    o.write(0xce960,ITEM,4);o.write(ITEM+0xe,state,2);o.write(STACK+4000,RETURN,4)
    for reg,v in [(UC_X86_REG_ESP,STACK+4000),(UC_X86_REG_EAX,track),(UC_X86_REG_EDX,flags),(UC_X86_REG_EBX,kind)]:u.reg_write(reg,v)
    events.clear();u.emu_start(0x18ce8,RETURN,count=1000)
    expected=(bytes(u.mem_read(0xcb2f4,128)),o.read(0xc17ac,2),o.read(0xc17d0,2),o.read(0xc192c,4),len(events))
    for d in dlls:
        actual=Gym.from_buffer_copy(g);d.tomb_gym_audio(C.byref(actual),track,flags,kind,state)
        result=(bytes(actual.tracks),actual.current_track,actual.completion_ticks,actual.complete,actual.audio_serial)
        assert result==expected,(case,track,flags,kind,state,result,expected)
(ROOT/'analysis/gym-audio-validation.json').write_text(json.dumps(dict(cases=10000,builds=2,scope=__doc__),indent=2)+'\n')
print('PASS: 10000 DOS tutorial condition/latch/completion cases per build')
