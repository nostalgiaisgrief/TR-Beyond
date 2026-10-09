"""Use original PHD bytes in both C and the original DOS geometry/animation code.

Object height functions remain unset: this is structural geometry, not collision
against live doors/bridges/platforms. References requiring them are reported.
"""
import ctypes as C
import hashlib
import json
from pathlib import Path
import random
import struct
import time
from compare_step import (ROOT,Actor,Anim,Change,Range,AnimContext,EVENT,Oracle,
    setup_library,state,clone,wrap32,I16,I32,U8,SZ,ITEM,COLL,STACK,RETURN,DATA,
    UC_X86_REG_EAX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_EDX,
    UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EFLAGS)

U16=C.c_uint16
class Sector(C.Structure):
    _fields_=[('floor_index',U16),('box',U16),('below',U8),('floor',C.c_int8),('above',U8),('ceiling',C.c_int8)]
class Placement(C.Structure):
    _fields_=[(n,I32) for n in ('x','y','z')]+[(n,U16) for n in ('rotation','intensity','id')]
class StaticDef(C.Structure):
    _fields_=[('id',C.c_uint32),('mesh',U16),('flags',U16),('bounds',I16*6),('draw_bounds',I16*6)]
class Item(C.Structure):
    _fields_=[(n,I32) for n in ('x','y','z')]+[(n,I16) for n in ('object','room','yaw','intensity')]+[('flags',U16),('state',I16),('state_known',U8)]
class Room(C.Structure):
    _fields_=[(n,I32) for n in ('x','z','bottom','top')]+[('nz',U16),('nx',U16),('sectors',C.POINTER(Sector)),('alternate',I16),('flags',I16),('statics',C.POINTER(Placement)),('static_count',SZ)]
class FixedCamera(C.Structure):
    _fields_=[(n,I32) for n in ('x','y','z')]+[('room',I16),('flags',U16)]
class CameraBox(C.Structure):
    _fields_=[(n,I32) for n in ('zmin','zmax','xmin','xmax')]+[('height',I16),('overlap',U16)]
class Level(C.Structure):
    _fields_=[('rooms',C.POINTER(Room)),('room_count',SZ),('floor_data',C.POINTER(U16)),('floor_count',SZ),
        ('animations',C.POINTER(Anim)),('animation_count',SZ),('changes',C.POINTER(Change)),('change_count',SZ),
        ('ranges',C.POINTER(Range)),('range_count',SZ),('commands',C.POINTER(I16)),('command_count',SZ),
        ('file_data',C.POINTER(U8)),('file_size',SZ),('parsed_bytes',SZ),
        ('static_defs',C.POINTER(StaticDef)),('static_def_count',SZ),('static_parsed_bytes',SZ),
        ('items',C.POINTER(Item)),('item_count',SZ),('item_parsed_bytes',SZ),
        ('boxes',C.POINTER(CameraBox)),('box_count',SZ),('camera_count',SZ),('cameras',C.POINTER(FixedCamera)),('overlaps',C.POINTER(U16)),('overlap_count',SZ),('zones',C.POINTER(I16))]
class Ref(C.Structure): _fields_=[('room',I32),('index',I32)]
class Heights(C.Structure):
    _fields_=[('floor',I16),('ceiling',I16),('floor_type',I32),('trigger_index',C.c_uint32),('object_references',C.c_uint32)]


def parse(path):
    data=path.read_bytes(); offset=0
    def read(fmt):
        nonlocal offset
        value=struct.unpack_from('<'+fmt,data,offset); offset+=struct.calcsize('<'+fmt); return value
    def skip(size):
        nonlocal offset
        if offset+size>len(data): raise ValueError('Truncated fixture')
        offset+=size
    assert read('I')[0]==32
    skip(read('I')[0]*65536); skip(4)
    rooms=[]
    for _ in range(read('H')[0]):
        x,z,bottom,top=read('4i'); skip(read('I')[0]*2); skip(read('H')[0]*32)
        nz,nx=read('HH'); sector_offset=offset; sectors=[read('HHBbBb') for _ in range(nx*nz)]
        skip(2); skip(read('H')[0]*18)
        static_offset=offset+2; statics=[read('iiiHHH') for _ in range(read('H')[0])]; alternate,flags=read('hh')
        rooms.append(dict(x=x,z=z,bottom=bottom,top=top,nz=nz,nx=nx,sectors=sectors,
                          sector_offset=sector_offset,alternate=alternate,flags=flags,statics=statics,static_offset=static_offset))
    sections={}
    for name,width in [('floor',2),('mesh',2),('meshptr',4),('animations',32),('changes',6),('ranges',8),('commands',2)]:
        n=read('I')[0]; sections[name]=dict(count=n,offset=offset,bytes=data[offset:offset+n*width]); skip(n*width)
    parsed_bytes=offset
    for name,width in [('trees',4),('frames',2),('models',18),('statics',32)]:
        n=read('I')[0]; sections[name]=dict(count=n,offset=offset,bytes=data[offset:offset+n*width]); skip(n*width)
    definitions=[struct.unpack_from('<IH12hH',sections['statics']['bytes'],i*32) for i in range(sections['statics']['count'])]
    static_parsed_bytes=offset
    for width in [20,16,8]: skip(read('I')[0]*width)
    cameras=[read('3ihH') for _ in range(read('I')[0])]
    skip(read('I')[0]*16)
    boxes=read('I')[0]; box_data=[read('4ihH') for _ in range(boxes)]; skip(read('I')[0]*2); skip(boxes*12)
    skip(read('I')[0]*2); item_count=read('I')[0]; item_offset=offset
    items=[read('hhiiihhH') for _ in range(item_count)]
    return dict(data=data,rooms=rooms,sections=sections,parsed_bytes=parsed_bytes,boxes=box_data,cameras=cameras,
        static_parsed_bytes=static_parsed_bytes,static_defs=definitions,items=items,
        item_offset=item_offset,item_parsed_bytes=offset)


def bind(path):
    dll=setup_library(path)
    for i,cls in [(5,Level),(6,Room),(7,Sector),(8,Heights),(10,Placement),(11,StaticDef),(13,Item)]: assert dll.tomb_test_size(i)==C.sizeof(cls)
    dll.tomb_level_load.argtypes=[C.c_char_p,C.c_char_p,SZ]; dll.tomb_level_load.restype=C.POINTER(Level)
    dll.tomb_level_free.argtypes=[C.POINTER(Level)]
    dll.tomb_find_sector.argtypes=[C.POINTER(Level),I32,I32,I32,I32,C.POINTER(Ref)]
    dll.tomb_static_heights.argtypes=[C.POINTER(Level),Ref,I32,I32,C.c_int,C.POINTER(Heights)]
    return dll


def check_decode(l,fixture):
    assert l.camera_count==len(fixture['cameras'])
    for i,camera in enumerate(fixture['cameras']): assert tuple(state(l.cameras[i]).values())==camera
    assert l.box_count==len(fixture['boxes'])
    for i,box in enumerate(fixture['boxes']): assert tuple(state(l.boxes[i]).values())==box
    assert l.room_count==len(fixture['rooms']) and l.parsed_bytes==fixture['parsed_bytes']
    for i,r in enumerate(fixture['rooms']):
        c=l.rooms[i]
        for k in ['x','z','bottom','top','nz','nx','alternate','flags']: assert getattr(c,k)==r[k]
        for j,values in enumerate(r['sectors']): assert list(state(c.sectors[j]).values())==list(values)
        assert c.static_count==len(r['statics'])
        for j,values in enumerate(r['statics']): assert list(state(c.statics[j]).values())==list(values)
    assert l.static_parsed_bytes==fixture['static_parsed_bytes'] and l.static_def_count==len(fixture['static_defs'])
    for i,v in enumerate(fixture['static_defs']):
        d=l.static_defs[i]; assert (d.id,d.mesh,d.flags,list(d.bounds))==(v[0],v[1],v[-1],list(v[8:14]))
        assert list(d.draw_bounds)==list(v[2:8])
    assert l.item_count==len(fixture['items']) and l.item_parsed_bytes==fixture['item_parsed_bytes']
    for i,v in enumerate(fixture['items']):
        c=l.items[i]
        assert (c.object,c.room,c.x,c.y,c.z,c.yaw,c.intensity,c.flags)==v
        assert not c.state_known
    for name,ctype,field in [('floor',U16,'floor_data'),('changes',Change,'changes'),('ranges',Range,'ranges'),('commands',I16,'commands')]:
        s=fixture['sections'][name]
        assert C.string_at(getattr(l,field),s['count']*C.sizeof(ctype))==s['bytes']
    for i in range(l.animation_count):
        vals=struct.unpack_from('<hii8h',fixture['sections']['animations']['bytes'],i*32+6)
        assert list(state(l.animations[i]).values())==[vals[1],vals[2],vals[0],*vals[3:]]


ROOMS,FLOOR,ANIMS,CHANGES,RANGES,COMMANDS,ITEMS=0x400000,0x700000,0x710000,0x720000,0x730000,0x740000,0x780000
class GeometryOracle(Oracle):
    def __init__(self):
        super().__init__(Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
        self.uc.mem_map(ROOMS,0x400000)
        for addr,size in [(RETURN+0x100,2),(0xc17b4,4),(0xcb39c,4)]: self.allowed.update(range(addr,addr+size))
    def install(self,f):
        self.sectors=[]; at=ROOMS+0x10000
        for i,r in enumerate(f['rooms']):
            record=bytearray(68)
            struct.pack_into('<I',record,8,at); struct.pack_into('<i',record,0x14,r['x'])
            struct.pack_into('<i',record,0x1c,r['z']); struct.pack_into('<HH',record,0x28,r['nz'],r['nx'])
            self.uc.mem_write(ROOMS+i*68,bytes(record))
            data=b''.join(struct.pack('<HHBbBb',*s) for s in r['sectors'])
            self.uc.mem_write(at,data); self.sectors.append((at,len(r['sectors']))); at+=len(data)
        assert at<FLOOR
        for name,address,globalptr in [('floor',FLOOR,0xce5c8),('animations',ANIMS,0xcc03c),
            ('changes',CHANGES,0xcc054),('ranges',RANGES,0xcc04c),('commands',COMMANDS,0xcc048)]:
            b=f['sections'][name]['bytes']; assert len(b)<65536
            self.uc.mem_write(address,b); self.write(globalptr,address,4)
        self.write(0xcc058,ROOMS,4); self.write(0xcb3a0,ITEMS,4)
        # All uninstantiated items use object 0 and both its height callbacks are null.
        self.uc.mem_write(ITEMS,bytes(1024*68)); self.write(0xcc074,0,4); self.write(0xcc078,0,4)
    def call(self,fn,eax,edx,ebx,ecx):
        self.write(STACK+0x800,RETURN,4)
        for reg,value in [(UC_X86_REG_EAX,eax),(UC_X86_REG_EDX,edx),(UC_X86_REG_EBX,ebx),
                          (UC_X86_REG_ECX,ecx),(UC_X86_REG_ESP,STACK+0x800),(UC_X86_REG_EFLAGS,2)]:
            self.uc.reg_write(reg,value&0xffffffff)
        self.bad=[]; self.uc.emu_start(fn,RETURN,count=10000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN and self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x804
        assert not self.bad,self.bad
        return self.uc.reg_read(UC_X86_REG_EAX)
    def find(self,x,y,z,room):
        self.write(RETURN+0x100,room,2)
        address=self.call(0x173bc,x,y,z,RETURN+0x100)
        final_room=self.read(RETURN+0x100,2)
        base,count=self.sectors[final_room]
        assert base<=address<base+count*8 and (address-base)%8==0
        return Ref(final_room,(address-base)//8),address


def main():
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--dll',nargs='+',type=Path,required=True); args=p.parse_args()
    dlls=[bind(path) for path in args.dll]; oracle=GeometryOracle(); results=[]
    t=time.monotonic(); scratch=ROOT/'work/level-tests'; scratch.mkdir(exist_ok=True)
    for name in ['GYM.PHD','LEVEL1.PHD']:
        path=ROOT/'work/reference-assets/DATA'/name; fixture=parse(path); oracle.install(fixture)
        loaded=[]; err=C.create_string_buffer(256)
        for dll in dlls:
            ptr=dll.tomb_level_load(str(path).encode(),err,len(err)); assert ptr,err.value
            loaded.append((dll,ptr)); check_decode(ptr.contents,fixture)
        cases=0; pending=0; declined=0; changed_rooms=0; slopes={}; rng=random.Random(19961105)
        for room,r in enumerate(fixture['rooms']):
            for index,s in enumerate(r['sectors']):
                ix,iz=divmod(index,r['nz'])
                for dx,dz,y in [(512,512,s[3]*256-1),(0,0,s[3]*256),(1023,1023,s[5]*256-1),
                                 (1,1023,s[5]*256),(1023,1,(s[3]+s[5])*128)]:
                    x,z=r['x']+ix*1024+dx,r['z']+iz*1024+dz
                    c_ref=Ref(); status=loaded[0][0].tomb_find_sector(loaded[0][1],x,y,z,room,C.byref(c_ref))
                    if not status:
                        declined+=1; continue # Original may index outside a room on invalid vertical links.
                    ref,address=oracle.find(x,y,z,room)
                    assert state(c_ref)==state(ref),(name,room,index,x,y,z,state(c_ref),state(ref))
                    changed_rooms+=ref.room!=room
                    for heavy in (0,1):
                        oracle.write(0xc17b0,heavy,4)
                        floor=C.c_int16(oracle.call(0x1767c,address,x,y,z)).value
                        kind=oracle.read(0xc17b4,4); trigger=oracle.read(0xcb39c,4)
                        trigger=0 if not trigger else (trigger-FLOOR)//2
                        ceiling=C.c_int16(oracle.call(0x180e8,address,x,y,z)).value
                        for dll,ptr in loaded:
                            actual_ref=Ref(); assert dll.tomb_find_sector(ptr,x,y,z,room,C.byref(actual_ref))
                            assert state(actual_ref)==state(ref)
                            h=Heights(); assert dll.tomb_static_heights(ptr,ref,x,z,heavy,C.byref(h)),(name,room,index)
                            assert (h.floor,h.ceiling,h.floor_type,h.trigger_index)==(floor,ceiling,kind,trigger),(
                                name,room,index,x,y,z,heavy,state(h),(floor,ceiling,kind,trigger))
                        pending+=bool(h.object_references); slopes[kind]=slopes.get(kind,0)+1; cases+=1
        # Real animation data: all loaded animation records at boundary frames,
        # using goals from actual state-change records where available.
        animation_cases=0
        l=loaded[0][1].contents
        for index in range(l.animation_count):
            anim=l.animations[index]
            goals={anim.state}
            for j in range(max(0,anim.change_count)): goals.add(l.changes[anim.change_index+j].goal)
            for goal in sorted(goals):
                for frame in [anim.first_frame-1,anim.first_frame,anim.last_frame-1,anim.last_frame]:
                    a=Actor(x=12345,y=-456,z=12345,current=anim.state,goal=goal,animation=index,
                        frame=C.c_int16(frame).value,speed=22,fall_speed=127,yaw=1234,flags=8 if animation_cases%2 else 0)
                    move=rng.randint(-32768,32767); override=-50 if animation_cases%3==0 else 0
                    oracle.write(0xce9ce,move,2); oracle.write(0xce96c,override,2); oracle.write(0xce966,4,2)
                    expected=oracle.run(0x28820,a); events_expected=list(oracle.events)
                    globals_expected=(oracle.read(0xce96c,2),oracle.read(0xce966,2))
                    for dll,ptr in loaded:
                        events=[]
                        @EVENT
                        def event(user,kind,ident,ap):
                            events.append((kind,ident,state(ap.contents)))
                            if kind==6: ap.contents.x=wrap32(ap.contents.x+ident)
                        q=ptr.contents
                        ctx=AnimContext(q.animations,q.animation_count,q.changes,q.change_count,q.ranges,q.range_count,
                            q.commands,q.command_count,oracle.sine,move,override,4,event,None)
                        actual=clone(a); assert dll.tomb_animate(C.byref(actual),C.byref(ctx))
                        assert state(actual)==state(expected),(name,index,frame,goal,state(actual),state(expected))
                        assert events==events_expected and (ctx.fall_override,ctx.weapon_status)==globals_expected
                    animation_cases+=1
        # Reject byte truncations within the supported prefix and unreasonable counts.
        malformed=[]
        for end in [0,7,fixture['rooms'][0]['sector_offset']+1,fixture['sections']['floor']['offset']+1,
                    fixture['sections']['animations']['offset']+1,fixture['parsed_bytes']-1]:
            malformed.append(fixture['data'][:end])
        corrupt=bytearray(fixture['data']); struct.pack_into('<I',corrupt,4,0xffffffff); malformed.append(corrupt)
        # Extended loader: truncate the new prefix, overflow its count, duplicate
        # a definition ID and reference an undefined mesh from a room placement.
        malformed.append(fixture['data'][:fixture['static_parsed_bytes']-1])
        pos=fixture['sections']['statics']['offset']
        malformed.append(fixture['data'][:pos+1])
        corrupt=bytearray(fixture['data']); struct.pack_into('<I',corrupt,pos-4,0xffffffff); malformed.append(corrupt)
        corrupt=bytearray(fixture['data']); corrupt[pos+32:pos+36]=corrupt[pos:pos+4]; malformed.append(corrupt)
        r=next(r for r in fixture['rooms'] if r['statics'])
        corrupt=bytearray(fixture['data']); struct.pack_into('<H',corrupt,r['static_offset']+16,65535); malformed.append(corrupt)
        pos=fixture['item_offset']
        malformed.append(fixture['data'][:fixture['item_parsed_bytes']-1])
        corrupt=bytearray(fixture['data']); struct.pack_into('<I',corrupt,pos-4,0xffffffff); malformed.append(corrupt)
        corrupt=bytearray(fixture['data']); struct.pack_into('<h',corrupt,pos+2,-1); malformed.append(corrupt)
        corrupt=bytearray(fixture['data']); struct.pack_into('<h',corrupt,pos,-1); malformed.append(corrupt)
        for j,data in enumerate(malformed):
            bad=scratch/f'{name}-{j}.phd'; bad.write_bytes(data)
            for dll in dlls:
                ptr=dll.tomb_level_load(str(bad).encode(),err,len(err))
                if ptr: dll.tomb_level_free(ptr); raise AssertionError('Accepted malformed prefix')
                assert err.value
        results.append(dict(level=name,sha256=hashlib.sha256(fixture['data']).hexdigest(),rooms=len(fixture['rooms']),
            sectors=sum(len(r['sectors']) for r in fixture['rooms']),animations=l.animation_count,
            geometry_comparisons_per_build=cases,room_changes=changed_rooms,geometry_declined=declined,
            queries_with_deferred_objects=pending,slope_categories=slopes,real_animation_cases_per_build=animation_cases,
            rejected_malformed_prefixes=len(malformed)))
        for dll,ptr in loaded: dll.tomb_level_free(ptr)
        print(json.dumps(results[-1]),flush=True)
    report=dict(levels=results,seconds=round(time.monotonic()-t,2),
        dlls=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in args.dll],
        limits='Structural geometry without instantiated object height callbacks; pending object references explicitly flagged. Real animation data with controlled sound/effect services. Full contact classifier, vault, slide and gameplay integration remain pending.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [ROOT/'src/level.h',ROOT/'src/level.c',ROOT/'src/geometry.c',Path(__file__)]})
    (ROOT/'analysis/c-level-validation.json').write_text(json.dumps(report,indent=2))
    print('PASS: real-level queries, animations and malformed-prefix checks')

if __name__=='__main__': main()
