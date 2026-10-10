"""Differential tests against DOS model lighting, including real room lights."""
import argparse
import ctypes as C
import json
import random
import struct
from pathlib import Path
from compare_level import ROOT, GeometryOracle, ROOMS, bind, parse
from compare_visual import Visual, Mesh

I=C.c_int32
class Lighting(C.Structure):
    _fields_=[('adder',I),('divider',I),('direction',I*3)]
class RoomLights(C.Structure):
    _fields_=[('data',C.POINTER(C.c_ubyte)),('count',C.c_size_t),('ambient',C.c_int16)]

def main():
    p=argparse.ArgumentParser();p.add_argument('--dll',type=Path,nargs='+',required=True);args=p.parse_args()
    libs=[bind(path) for path in args.dll];o=GeometryOracle();rng=random.Random(19961010)
    for address,size in [(0x12f3d8,48),(0xd4714,32*128)]:o.allowed.update(range(address,address+size))
    matrix=0x600000;stream=0x610000;light_data=0x620000
    sine=(C.c_int16*1025).from_buffer_copy((ROOT/'work/reference-assets/sine.bin').read_bytes())
    identity=[16384,0,0,0,0,16384,0,0,0,0,16384,0]
    for dll in libs:
        dll.tomb_visual_load.argtypes=[C.c_void_p,C.c_char_p,C.c_size_t];dll.tomb_visual_load.restype=C.POINTER(Visual)
        dll.tomb_visual_free.argtypes=[C.POINTER(Visual)]
        dll.tomb_light_room.argtypes=[C.POINTER(RoomLights),C.POINTER(I),C.c_int,C.POINTER(C.c_int16),C.POINTER(Lighting)]
        dll.tomb_light_static.argtypes=[C.c_int16,C.c_int,C.POINTER(Lighting)]
        dll.tomb_light_vector.argtypes=[C.POINTER(Lighting),C.POINTER(I),C.POINTER(I)]
        dll.tomb_light_vertex.argtypes=[C.POINTER(Mesh),C.c_size_t,C.POINTER(Lighting),C.POINTER(I)]
    counts=dict(room=0,static=0,vertices=0,loaded_rooms=0)
    for name in ['GYM.PHD','LEVEL1.PHD','LEVEL2.PHD','LEVEL3A.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name;f=parse(path);o.install(f)
        for dll in libs:
            error=C.create_string_buffer(256);level=dll.tomb_level_load(str(path).encode(),error,256);assert level,error.value
            v=dll.tomb_visual_load(level,error,256);assert v,error.value
            rooms=C.cast(v.contents.lighting,C.POINTER(RoomLights))
            for i,r in enumerate(f['rooms']):
                raw=b''.join(struct.pack('<iiihi',*light) for light in r['lights'])
                assert rooms[i].ambient==r['ambient'] and rooms[i].count==len(r['lights'])
                assert C.string_at(rooms[i].data,len(raw))==raw
                counts['loaded_rooms']+=1
            dll.tomb_visual_free(v);dll.tomb_level_free(level)
        for case in range(300):
            rid=rng.randrange(len(f['rooms']));r=f['rooms'][rid]
            raw=b''.join(struct.pack('<iiihi',*light) for light in r['lights'])
            data=(C.c_ubyte*len(raw)).from_buffer_copy(raw);room=RoomLights(data,len(r['lights']),r['ambient'])
            o.write(ROOMS+rid*68+12,light_data,4);o.write(ROOMS+rid*68+44,r['ambient'],2);o.write(ROOMS+rid*68+46,len(r['lights']),2)
            if raw:o.uc.mem_write(light_data,raw)
            pos=(I*3)(r['x']+rng.randrange(max(1,r['nx']-1))*1024+512,rng.randint(r['top'],max(r['top'],r['bottom'])),r['z']+rng.randrange(max(1,r['nz']-1))*1024+512)
            depth=rng.choice([0,500,12288,12289,18000,24000]);mat=identity.copy();mat[11]=depth*16384
            o.uc.mem_write(matrix,struct.pack('<12i',*mat));o.uc.mem_write(0x12ea54,struct.pack('<12i',*identity));o.write(0x12f3c4,matrix,4)
            o.call(0x104a8,*pos,rid)
            expected=[o.read(0x12f3f0,4),o.read(0x12f3f4,4)];direction=[o.read(0x12f3d8+j*4,4) for j in range(3)]
            for dll in libs:
                actual=Lighting();dll.tomb_light_room(C.byref(room),pos,depth,sine,C.byref(actual))
                assert [actual.adder,actual.divider]==expected,(name,case,rid,expected,actual.adder,actual.divider)
                if actual.divider:assert list(actual.direction)==direction,(name,case,direction,list(actual.direction))
            counts['room']+=1
    for case in range(400):
        depth=rng.choice([0,12288,12289,20000]);intensity=rng.randrange(8192);mat=identity.copy();mat[11]=depth*16384
        o.uc.mem_write(matrix,struct.pack('<12i',*mat));o.call(0x1063c,intensity,0,0,0)
        for dll in libs:
            actual=Lighting(0,24576,(I*3)(123,456,789));dll.tomb_light_static(intensity,depth,C.byref(actual));assert actual.adder==o.read(0x12f3f0,4)
            assert actual.divider==24576 and list(actual.direction)==[123,456,789]
        counts['static']+=1
    for case in range(1000):
        # Exercise arbitrary rotations, zero divider, signed baked shades and clamps.
        rot=[rng.randint(-16384,16384) for _ in range(9)];mat=[v for row in range(3) for v in rot[3*row:3*row+3]+[0]]
        o.uc.mem_write(matrix,struct.pack('<12i',*mat))
        l=Lighting(rng.randint(-4096,12000),rng.choice([0,0x6000,rng.randrange(8192,1000000)]),(I*3)(*[rng.randint(-16384,16384) for _ in range(3)]))
        o.write(0x12f3f0,l.adder,4);o.write(0x12f3f4,l.divider,4)
        for j in range(3):o.write(0x12f3d8+j*4,l.direction[j],4)
        normals=case%2==0;n=32
        values=[rng.randint(-16384,16384) for _ in range(n*3)] if normals else [rng.randint(-4096,8191) for _ in range(n)]
        raw=struct.pack('<'+'h'*len(values),*values);o.uc.mem_write(stream,struct.pack('<h',n if normals else -n)+raw)
        data=(C.c_ubyte*len(raw)).from_buffer_copy(raw);m=Mesh();m.vertex_count=n
        if normals:m.normal_count=n;m.normals=data
        else:m.light_count=n;m.lights=data
        o.call(0x3e6a4,stream,0,0,0)
        expected=[o.read(0xd4714+32*j+26,2) for j in range(n)]
        for dll in libs:
            local=(I*3)();dll.tomb_light_vector(C.byref(l),(I*9)(*rot),local)
            actual=[dll.tomb_light_vertex(C.byref(m),j,C.byref(l),local) for j in range(n)]
            assert actual==expected,(case,actual,expected)
        counts['vertices']+=n
    result=dict(original_sha256=o.sha256 if hasattr(o,'sha256') else '99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac',checks=counts,dlls=[p.name for p in args.dll])
    (ROOT/'analysis/lighting-validation.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS',counts)
if __name__=='__main__':main()
