"""Independent asset parsing checks and original Lara mesh selection oracle.
No claim of original renderer, interpolation or pixel equivalence.
"""
import ctypes as C
import hashlib
import json
import struct
import time
from pathlib import Path
from compare_level import ROOT,Level,bind,parse,GeometryOracle
from compare_step import SZ,I16,I32,STACK,RETURN,UC_X86_REG_EAX,UC_X86_REG_ESP,UC_X86_REG_EFLAGS,UC_X86_REG_EIP
U8=C.c_uint8; U16=C.c_uint16; U32=C.c_uint32; P=C.POINTER(U8)
class Mesh(C.Structure):
    _fields_=[('vertices',P),('normals',P),('lights',P),('faces',P*4),('sprites',P),
        ('vertex_count',U32),('normal_count',U32),('light_count',U32),('face_count',U32*4),('sprite_count',U32),('vertex_stride',U32),
        ('centre',I16*3),('radius',I32)]
class Visual(C.Structure):
    _fields_=[('level',C.POINTER(Level)),('rooms',C.POINTER(Mesh)),('meshes',C.POINTER(Mesh)),('room_count',SZ),('mesh_count',SZ)]+[(n,P) for n in
        ('tiles','textures','sprite_textures','models','trees','frames','animations','palette')]+[(n,SZ) for n in
        ('tile_count','texture_count','sprite_texture_count','model_count','tree_words','frame_words','animation_count')]+[('portals',C.c_void_p)]
class Model(C.Structure):
    _fields_=[('id',U32),('tree_word',U32),('frame_offset',U32),('mesh_count',U16),('mesh_start',U16),('animation',U16)]
class Pose(C.Structure):
    _fields_=[('bounds',I16*6),('root',I16*3),('count',U16),('rotation',(U16*3)*64)]

def parse_mesh(data,offset,room):
    start=offset
    def read(fmt):
        nonlocal offset
        result=struct.unpack_from('<'+fmt,data,offset); offset+=struct.calcsize('<'+fmt); return result
    def array(count,width):
        nonlocal offset
        result=data[offset:offset+count*width]; assert len(result)==count*width; offset+=count*width; return result
    centre=(0,0,0); radius=0
    if not room: centre=read('3h'); radius=read('i')[0]
    nv=read('h')[0]; assert nv>=0; stride=8 if room else 6; vertices=array(nv,stride)
    normals=lights=b''
    if not room:
        nn=read('h')[0]
        if nn>0: normals=array(nn,6)
        else: lights=array(-nn,2)
    faces=[b'']*4
    for j in range(2 if room else 4): faces[j]=array(read('h')[0],8 if j&1 else 10)
    sprites=array(read('h')[0],4) if room else b''
    return dict(vertices=vertices,normals=normals,lights=lights,faces=faces,sprites=sprites,
                centre=centre,radius=radius,stride=stride,bytes=offset-start),offset

def check_mesh(actual,expected):
    for field,count,width in [('vertices','vertex_count',expected['stride']),('normals','normal_count',6),('lights','light_count',2),('sprites','sprite_count',4)]:
        raw=expected[field]; assert getattr(actual,count)==len(raw)//width
        assert C.string_at(getattr(actual,field),len(raw))==raw
    assert actual.vertex_stride==expected['stride'] and tuple(actual.centre)==expected['centre'] and actual.radius==expected['radius']
    for j,raw in enumerate(expected['faces']):
        assert actual.face_count[j]==len(raw)//(8 if j&1 else 10)
        assert C.string_at(actual.faces[j],len(raw))==raw

def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--dll',nargs='+',type=Path,required=True); args=p.parse_args()
    dlls=[bind(path) for path in args.dll]; oracle=GeometryOracle(); results=[]; begun=time.monotonic()
    oracle.allowed.update(range(0xce988,0xce9c4)); oracle.allowed.update(range(0xcc044,0xcc048))
    for dll in dlls:
        for i,cls in [(15,Visual),(16,Mesh),(17,Pose),(18,Model)]: assert dll.tomb_test_size(i)==C.sizeof(cls),(i,dll.tomb_test_size(i),C.sizeof(cls))
        dll.tomb_visual_load.argtypes=[C.POINTER(Level),C.c_char_p,SZ]; dll.tomb_visual_load.restype=C.POINTER(Visual)
        dll.tomb_visual_free.argtypes=[C.POINTER(Visual)]
        dll.tomb_visual_model.argtypes=[C.POINTER(Visual),U32,C.POINTER(Model)]
        dll.tomb_visual_key.argtypes=[C.POINTER(Visual),SZ,SZ,C.POINTER(Pose)]
        dll.tomb_visual_lara_meshes.argtypes=[C.POINTER(Visual),C.c_int,C.POINTER(U16)]
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name; f=parse(path); d=f['data']; s=f['sections']; loaded=[]; oracle.install(f)
        for dll in dlls:
            error=C.create_string_buffer(256); level=dll.tomb_level_load(str(path).encode(),error,len(error)); assert level,error.value
            visual=dll.tomb_visual_load(level,error,len(error)); assert visual,(name,error.value)
            loaded.append((dll,level,visual))
        rooms=[]; tiles=struct.unpack_from('<I',d,4)[0]; at=12+tiles*65536+2
        room_data_offsets=[]
        for r in f['rooms']:
            words=struct.unpack_from('<I',d,at+16)[0]; begin=at+20; room_data_offsets.append(begin)
            m,end=parse_mesh(d,begin,True); assert end==begin+words*2; rooms.append(m)
            # Room tail is independently located from source sector/static arrays.
            at=r['static_offset']+18*len(r['statics'])+4
        mesh_offsets=[v[0] for v in struct.iter_unpack('<I',s['meshptr']['bytes'])]
        meshes=[parse_mesh(s['mesh']['bytes'],off,False)[0] for off in mesh_offsets]
        tex_start=f['static_parsed_bytes']; tex_count=struct.unpack_from('<I',d,tex_start)[0]
        tex=d[tex_start+4:tex_start+4+tex_count*20]; sprite_start=tex_start+4+len(tex)
        sprite_count=struct.unpack_from('<I',d,sprite_start)[0]; sprite=d[sprite_start+4:sprite_start+4+sprite_count*16]
        palette=d[f['item_parsed_bytes']+8192:f['item_parsed_bytes']+8960]
        for dll,level,vp in loaded:
            v=vp.contents
            assert (v.room_count,v.mesh_count,v.tile_count,v.texture_count,v.sprite_texture_count)==(len(rooms),len(meshes),tiles,tex_count,sprite_count)
            for i,m in enumerate(rooms): check_mesh(v.rooms[i],m)
            for i,m in enumerate(meshes): check_mesh(v.meshes[i],m)
            for field,raw in [('tiles',d[8:8+tiles*65536]),('textures',tex),('sprite_textures',sprite),('palette',palette)]+[(k,s[k]['bytes']) for k in ('models','trees','frames','animations')]:
                assert C.string_at(getattr(v,field),len(raw))==raw,(name,field)
            for model in struct.iter_unpack('<IHHIIH',s['models']['bytes']):
                output=Model(); assert dll.tomb_visual_model(vp,model[0],C.byref(output))
                assert (output.id,output.mesh_count,output.mesh_start,output.tree_word,output.frame_offset,output.animation)==model
        keys=0
        for i in range(s['animations']['count']):
            off,rate=struct.unpack_from('<IB',s['animations']['bytes'],i*32)
            first,last=struct.unpack_from('<hh',s['animations']['bytes'],i*32+16)
            n=struct.unpack_from('<H',s['frames']['bytes'],off+18)[0]; stride=20+n*4
            for k in range((last-first+rate-1)//rate+1):
                raw=s['frames']['bytes'][off+k*stride:off+(k+1)*stride]
                expected=struct.unpack_from('<9hH',raw)
                rotations=[]
                for low,high in struct.iter_unpack('<HH',raw[20:]):
                    rotations.append(((high>>4)&1023,((high&15)<<6)|(low>>10),low&1023))
                for dll,level,vp in loaded:
                    pose=Pose(); assert dll.tomb_visual_key(vp,i,k,C.byref(pose)),(name,i,k)
                    assert tuple(pose.bounds)==expected[:6] and tuple(pose.root)==expected[6:9] and pose.count==n
                    assert [tuple(v) for v in pose.rotation[:n]]==[tuple(v*64 for v in row) for row in rotations]
                keys+=1
        # Execute original mesh selection with unarmed regular/gym profiles.
        selected=[]
        for gym in (0,1):
            models={v[0]:v for v in struct.iter_unpack('<IHHIIH',s['models']['bytes'])}
            for ident in (0,5): oracle.write(0xcc062+ident*50,models[ident][2],2)
            table=0x790000
            for i in range(len(meshes)): oracle.write(table+4*i,0x500000+i*16,4)
            oracle.write(0xcc044,table,4); oracle.uc.mem_write(0xcee64,bytes(15)); oracle.write(0xcee71,gym*32,1)
            oracle.write(STACK+0x800,RETURN,4); oracle.uc.reg_write(UC_X86_REG_ESP,STACK+0x800)
            oracle.uc.reg_write(UC_X86_REG_EAX,0); oracle.uc.reg_write(UC_X86_REG_EFLAGS,2); oracle.bad=[]
            oracle.uc.emu_start(0x29070,RETURN,count=10000)
            assert not oracle.bad and oracle.uc.reg_read(UC_X86_REG_EIP)==RETURN and oracle.uc.reg_read(UC_X86_REG_ESP)==STACK+0x804
            expected=[(oracle.read(0xce988+i*4,4)-0x500000)//16 for i in range(15)]
            for dll,level,vp in loaded:
                indices=(U16*15)(); assert dll.tomb_visual_lara_meshes(vp,gym,indices)
                assert list(indices)==expected,(list(indices),expected)
            selected.append(expected)
        # Corrupt borrowed data only within each private loaded copy, restore it
        # after checking failure, and keep accepted visual views out of use here.
        rejected=0
        for dll,level,vp in loaded:
            dll.tomb_visual_free(vp)
            positions=[(room_data_offsets[0],b'\xff\x7f'),
                       (s['meshptr']['offset'],b'\xff'*4),
                       (tex_start+4+2,b'\xff\x7f'),
                       (s['animations']['offset']+4,b'\x00'),
                       (s['frames']['offset']+18,b'\xff\x7f')]
            base=C.cast(level.contents.file_data,C.c_void_p).value
            for offset,replacement in positions:
                old=C.string_at(base+offset,len(replacement)); C.memmove(base+offset,replacement,len(replacement))
                error=C.create_string_buffer(256); bad=dll.tomb_visual_load(level,error,len(error))
                C.memmove(base+offset,old,len(old))
                if bad: dll.tomb_visual_free(bad); raise AssertionError(('Accepted corrupt asset',offset))
                assert error.value; rejected+=1
            dll.tomb_level_free(level)
        result=dict(level=name,rooms=len(rooms),meshes=len(meshes),tiles=tiles,textures=tex_count,
            room_vertices=sum(len(m['vertices'])//8 for m in rooms),room_faces=sum(sum(len(b)//(8 if j&1 else 10) for j,b in enumerate(m['faces'])) for m in rooms),
            decoded_keys_per_build=keys,models=s['models']['count'],lara_mesh_selections=selected,rejections_across_builds=rejected,
            sha256=hashlib.sha256(d).hexdigest())
        results.append(result); print(json.dumps(result),flush=True)
    report=dict(levels=results,seconds=round(time.monotonic()-begun,2),
        limits='Visual views and local pose keys, not interpolated skeletons or rendered pixels. Mesh selection checked against original 0x29070 for unarmed standard/gym profiles only.',
        builds=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in args.dll],
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'src/visual.c',ROOT/'src/visual.h',Path(__file__)]})
    (ROOT/'analysis/c-visual-validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: visual data, animation keys and original Lara mesh selection')

if __name__=='__main__': main()
