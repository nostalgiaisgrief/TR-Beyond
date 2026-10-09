"""DOS floor completion/secrets and real PC music dispatch; device calls stubbed."""
from compare_dos_camera import *
class Gym(C.Structure):
    _fields_=[('tracks',C.c_uint16*64)]+[(n,C.c_int) for n in ('current_track','completion_ticks','complete')]+[('audio_serial',C.c_uint)]+[(n,C.c_int) for n in ('camera','camera_timer','camera_speed','last_camera')]+[('camera_once',C.c_uint64)]
class Progress(C.Structure):
    _fields_=[('music',Gym),('secrets',C.c_uint16),('secret_serial',C.c_uint),('complete',C.c_int),('lara_state',C.c_int)]
def main():
    o=CameraOracle();o.install(parse(ROOT/'work/reference-assets/DATA/LEVEL1.PHD'));rng=random.Random(19961015)
    for a,b in [(0xcb2f4,0xcb374),(0xc17ac,0xc17ae),(0xc17d0,0xc17d2),(0xc192c,0xc1930),(0xcefb6,0xcefb8)]:o.allowed.update(range(a,b))
    for a in [0x47530,0x47790]:o.uc.hook_add(UC_HOOK_CODE,lambda *args:o.ret(),begin=a,end=a)
    o.write(0xc381c,1,2);o.write(0xce960,ITEM,4);o.write(ITEM+0x34,0,4);o.write(0xcb298,0,1)
    for suffix in ('','_debug'):
        d=bind(ROOT/'build'/f'step_test{suffix}.dll');d.tomb_progress_action.argtypes=[C.POINTER(Progress),C.c_int,C.c_int,C.c_uint16,C.c_int]
        d.tomb_music_level_track.argtypes=[C.c_int];d.tomb_music_source.argtypes=[C.c_int]
        for level in range(16):
            track=o.read(0xc3e0c+2*level,2)
            assert d.tomb_music_level_track(level)==track
            if level:assert d.tomb_music_source(track) in (3,4,5,6)
        assert d.tomb_music_level_track(-1)==0 and d.tomb_music_level_track(16)==0
        for case in range(3500):
            p=Progress();p.music.current_track=rng.choice([0,2,22,28,57]);p.secrets=rng.randrange(65536);p.lara_state=rng.choice([2,10,28,33,55])
            for i in range(64):p.music.tracks[i]=rng.choice([0,0x100,0x200,0x3e00,0x3f00])
            action=rng.choice([7,8,8,8,10]);value=rng.randrange(16) if action==10 else rng.randrange(2,64);flags=rng.choice([0x3f00,0x3e00,0x200,0]);kind=0
            o.uc.mem_write(0xcb2f4,bytes(p.music.tracks));o.write(0xc17ac,p.music.current_track,2);o.write(0xc17d0,0,2);o.write(0xc192c,0,4);o.write(0xcefb6,p.secrets,2);o.write(ITEM+0xe,p.lara_state,2)
            words=[0x8004,flags,0x8000|(action<<10)|value];o.uc.mem_write(DATA,struct.pack('<3H',*words));o.events.clear()
            o.call(0x17a40,DATA,0,0,0);d.tomb_progress_action(C.byref(p),action,value,flags,kind)
            assert bytes(p.music.tracks)==bytes(o.uc.mem_read(0xcb2f4,128))
            assert p.music.current_track==o.read(0xc17ac,2),(case,action,value,p.music.current_track,o.read(0xc17ac,2))
            assert p.secrets==(o.read(0xcefb6,2)&65535) and p.complete==o.read(0xc192c,4)
            assert p.secret_serial==sum(e[1]==173 for e in o.events),(case,action,value,p.secret_serial,o.events)
    (ROOT/'analysis/progression-validation.json').write_text(json.dumps(dict(cases_per_build=3500,builds=2,scope=__doc__),indent=2))
    print('PASS: 16 DOS level-start tracks and 3500 completion/secret/music dispatch cases per build')
if __name__=='__main__':main()
