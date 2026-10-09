"""Strict LE mapper for this DOS executable, using preferred analysis addresses.

Not an executable loader: selector relocations cannot be assigned without DOS/4G.
Unsupported relocation forms fail explicitly. Binary outputs are private research.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'work/python-deps'))
from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def load(path):
    raw = path.read_bytes()
    def word(at):
        return struct.unpack_from('<I', raw, at)[0]
    le = word(60)
    assert raw[:2] == b'MZ' and raw[le:le+4] == b'LE\0\0'
    pages, page_size, last_size = word(le+20), word(le+40), word(le+44)
    objects = []
    page_owner = {}
    for n in range(word(le+68)):
        values = struct.unpack_from('<6I', raw, le+word(le+64)+24*n)
        obj = dict(zip(('size', 'base', 'flags', 'first_page', 'pages', 'reserved'), values))
        obj['number'] = n+1
        obj['data'] = bytearray(max(obj['size'], obj['pages']*page_size))
        obj['file_pages'] = []
        for j in range(obj['pages']):
            index = obj['first_page']-1+j
            entry = raw[le+word(le+72)+4*index:le+word(le+72)+4*index+4]
            physical = int.from_bytes(entry[:3], 'big')
            assert entry[3] == 0 and physical > 0, ('Unsupported page', index, entry)
            count = last_size if physical == pages and last_size else page_size
            offset = word(le+128)+(physical-1)*page_size
            assert offset+count <= len(raw)
            obj['data'][j*page_size:j*page_size+count] = raw[offset:offset+count]
            obj['file_pages'].append(dict(index=index, offset=offset, size=count))
            assert index not in page_owner
            page_owner[index] = (obj, j*page_size)
        objects.append(obj)
    assert len(page_owner) == pages
    fix_pages, fix_records = le+word(le+104), le+word(le+108)
    fixes = []
    for index in range(pages):
        pos, end = fix_records+word(fix_pages+4*index), fix_records+word(fix_pages+4*(index+1))
        obj, page_offset = page_owner[index]
        while pos < end:
            start = pos
            source_type, flags = raw[pos:pos+2]
            pos += 2
            assert source_type in (2, 6, 7, 8), ('Unsupported source', hex(pos), source_type)
            assert flags in (0, 0x10), ('Unsupported flags', hex(pos), flags)
            source_offset = struct.unpack_from('<h', raw, pos)[0]
            pos += 2
            target_obj = raw[pos]
            pos += 1
            target_offset = 0
            if source_type != 2:
                length = 4 if flags & 0x10 else 2
                target_offset = int.from_bytes(raw[pos:pos+length], 'little')
                pos += length
            assert 1 <= target_obj <= len(objects)
            target = objects[target_obj-1]
            at = page_offset+source_offset
            assert 0 <= at < len(obj['data'])
            address = target['base']+target_offset
            source = obj['base']+at
            if source_type in (7, 8):
                assert at+4 <= len(obj['data'])
                value = address if source_type == 7 else address-source-4
                struct.pack_into('<I', obj['data'], at, value & 0xffffffff)
            fixes.append(dict(record_file_offset=start, source=source, source_object=obj['number'],
                              source_type=source_type, target_object=target_obj,
                              target_offset=target_offset, target=address,
                              applied=source_type in (7, 8)))
        assert pos == end, (index, pos, end)
    entry_obj = objects[word(le+24)-1]
    # Page-crossing records may occur twice. Both must resolve identically.
    for fix in fixes:
        if fix['applied']:
            obj = objects[fix['source_object']-1]
            at = fix['source']-obj['base']
            expected = fix['target'] if fix['source_type']==7 else fix['target']-fix['source']-4
            assert struct.unpack_from('<I', obj['data'], at)[0] == expected & 0xffffffff
    return raw, objects, fixes, entry_obj['base']+word(le+28)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raw, objects, fixes, entry = load(args.exe)
    args.out.mkdir(parents=True, exist_ok=True)
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.skipdata = True
    summary = dict(sha256=hashlib.sha256(raw).hexdigest(), entry=entry,
                   address_convention='LE preferred base + object offset; not observed runtime addresses',
                   fixup_counts=dict(Counter(str(x['source_type']) for x in fixes)),
                   objects=[{k:v for k,v in o.items() if k != 'data'} for o in objects])
    (args.out/'map.json').write_text(json.dumps(summary, indent=2))
    (args.out/'fixups.json').write_text(json.dumps(fixes, indent=2))
    for obj in objects:
        data = bytes(obj['data'][:obj['size']])
        (args.out/f"object-{obj['number']}.bin").write_bytes(data)
        if obj['flags'] & 4 and obj['flags'] & 0x2000:
            with (args.out/f"object-{obj['number']}.asm").open('w') as output:
                output.write('; Linear sweep: may decode embedded data as instructions.\n')
                for at, size, mnemonic, operands in decoder.disasm_lite(data, obj['base']):
                    output.write(f'{at:08x}  {mnemonic:10s} {operands}\n')
    # Relocation-backed runs of pointers into executable objects are potential dispatch tables.
    pointers = {f['source']: f for f in fixes if f['source_type']==7 and objects[f['target_object']-1]['flags'] & 4}
    runs = []
    for address in sorted(pointers):
        if address-4 in pointers:
            continue
        row = []
        cursor = address
        while cursor in pointers:
            row.append(pointers[cursor]['target'])
            cursor += 4
        if len(row) >= 8:
            runs.append(dict(address=address, count=len(row), targets=row))
    (args.out/'pointer-tables.json').write_text(json.dumps(runs, indent=2))
    print(json.dumps({k:v for k,v in summary.items() if k != 'objects'}, indent=2))
    print('Pointer table candidates:', [(hex(r['address']),r['count']) for r in runs])


if __name__ == '__main__':
    main()
