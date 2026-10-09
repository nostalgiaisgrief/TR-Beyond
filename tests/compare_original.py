"""Differential test: compiled C executable versus original DOS x86 instructions.

No second implementation of the movement rules is used as the oracle. The
reference is loaded directly from the hash-pinned TOMB.EXE and run with Unicorn.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyse_le import load
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_MEM_WRITE
from unicorn.x86_const import (UC_X86_REG_EAX, UC_X86_REG_EBX, UC_X86_REG_ECX,
    UC_X86_REG_EDX, UC_X86_REG_ESI, UC_X86_REG_EDI, UC_X86_REG_EBP,
    UC_X86_REG_ESP, UC_X86_REG_EIP, UC_X86_REG_EFLAGS)

HASH = '99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'
HANDLERS = {21:0x25974,22:0x259ec,0: 0x2515c, 1: 0x251ec, 2: 0x252f8, 5: 0x2555c, 6: 0x255bc, 7: 0x25644, 12: 0x25798, 16: 0x258a0, 20: 0x25928}
FIELDS = ['handler', 'input', 'health', 'current', 'goal', 'animation', 'frame',
          'turn_rate', 'lean', 'item_flags', 'weapon_status', 'head_yaw',
          'head_pitch', 'torso_yaw', 'torso_pitch', 'camera_mode']
ITEM, COLL, STACK, RETURN = 0x200000, 0x201000, 0x210000, 0x220000
# Record word index -> original address and original width.
MEMBERS = {1:(0xce92c,4), 2:(ITEM+0x22,2), 3:(ITEM+0x0e,2),
    4:(ITEM+0x10,2), 5:(ITEM+0x14,2), 6:(ITEM+0x16,2),
    7:(0xce9cc,2), 8:(ITEM+0x40,2), 9:(ITEM+0x42,1),
    10:(0xce966,2), 11:(0xce9d0,2), 12:(0xce9d2,2),
    13:(0xce9d6,2), 14:(0xce9d8,2), 15:(0xcb298,1)}
RECORD = struct.Struct('<16I')


def pack(case):
    return RECORD.pack(*(n & 0xffffffff for n in case))


def baseline(handler, inputs):
    return [handler, inputs, 1000, handler, handler, 7, 23, 0, 0, 0, 0, 0, 0, 19, -31, 0]


def generate():
    # Every combination of the low 13 input bits, including ignored bits.
    for handler in HANDLERS:
        for inputs in range(8192):
            yield 'all_input_masks', baseline(handler, inputs)
    edges = [-32768,-32767,-32360,-32359,-2003,-2002,-2001,-1457,-1456,
             -1455,-729,-728,-727,-409,-1,0,1,409,727,728,729,1455,1456,
             1457,2001,2002,2003,32358,32359,32766,32767]
    for handler in HANDLERS:
        for rate in edges:
            for inputs in [0,1,4,8,12,0x85,0x89,0x8d,0x82,0x84,0x88,0x1000]:
                case = baseline(handler, inputs)
                case[7] = rate
                case[8] = rate
                yield 'arithmetic_edges', case
    for yaw in [-32768,-8009,-8008,-8007,-1,0,1,8007,8008,8009,32767]:
        for pitch in [-32768,-7645,-7644,-7643,-1,0,1,4003,4004,4005,32767]:
            for direction in range(16):
                case = baseline(2, 0x200 | direction)
                case[11:13] = [yaw,pitch]
                case[15] = 7
                yield 'look_thresholds', case
    for handler in HANDLERS:
        for hp in [-32768,-1,0,1,32767]:
            for status in [-32768,-1,0,3,4,5,32767]:
                for inputs in [0,1,4,8,0x84,0x88,0x11,0x1000,0x120f]:
                    case = baseline(handler,inputs)
                    case[2] = hp
                    case[10] = status
                    case[7] = 728
                    case[9] = 0xff
                    case[15] = 2
                    yield 'health_weapon_flags', case
    rng = random.Random(19961105)
    for _ in range(12000):
        handler = rng.choice(list(HANDLERS))
        case = [handler, rng.getrandbits(32)] + [rng.randint(-32768,32767) for _ in range(14)]
        case[9] = rng.randrange(256)
        case[15] = rng.randrange(256)
        yield 'seeded_random', case


class Original:
    def __init__(self, exe):
        raw, objects, _, _ = load(exe)
        assert hashlib.sha256(raw).hexdigest() == HASH, 'Unexpected DOS binary'
        self.uc = Uc(UC_ARCH_X86, UC_MODE_32)
        for obj in objects:
            self.uc.mem_map(obj['base'], (len(obj['data'])+4095) & ~4095)
            self.uc.mem_write(obj['base'], bytes(obj['data']))
        for address in (ITEM,COLL,STACK,RETURN):
            self.uc.mem_map(address,4096)
        for state, address in HANDLERS.items():
            assert struct.unpack('<I',self.uc.mem_read(0xc3884+state*4,4))[0] == address
        self.allowed = set()
        # Detect previously unmodelled writes anywhere, not just compared fields.
        for index in (3,4,5,6,7,8,11,12,13,14,15):
            address,width = MEMBERS[index]
            self.allowed.update(range(address,address+width))
        self.bad_writes = []
        self.uc.hook_add(UC_HOOK_MEM_WRITE,self.check_write)
        self.registers = [UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_ESI,
                          UC_X86_REG_EDI,UC_X86_REG_EBP]

    def check_write(self, uc, access, address, size, value, data):
        if STACK <= address and address+size <= STACK+4096:
            return
        if any(a not in self.allowed for a in range(address,address+size)):
            self.bad_writes.append((address,size))

    def execute(self, case):
        # Nonzero neighbouring fields expose accidental dependencies on padding.
        self.uc.mem_write(ITEM, bytes([0xa5])*256)
        self.uc.mem_write(COLL, bytes([0x5a])*256)
        self.uc.mem_write(0xce900, bytes([0x96])*512)
        for index,(address,width) in MEMBERS.items():
            self.uc.mem_write(address,(case[index] & ((1 << (width*8))-1)).to_bytes(width,'little'))
        self.uc.mem_write(STACK+0x800,struct.pack('<I',RETURN))
        for i,register in enumerate(self.registers):
            self.uc.reg_write(register,0x12345678+i*0x11111111)
        self.uc.reg_write(UC_X86_REG_EFLAGS,2)
        self.uc.reg_write(UC_X86_REG_ESP,STACK+0x800)
        self.uc.reg_write(UC_X86_REG_EAX,ITEM)
        self.uc.reg_write(UC_X86_REG_EDX,COLL)
        self.bad_writes.clear()
        self.uc.emu_start(HANDLERS[case[0]],RETURN,count=1000)
        assert self.uc.reg_read(UC_X86_REG_EIP)==RETURN, 'Instruction budget exhausted'
        assert self.uc.reg_read(UC_X86_REG_ESP)==STACK+0x804, 'Stack mismatch'
        assert not self.bad_writes, ('Unmodelled writes', self.bad_writes)
        result = list(case)
        for index,(address,width) in MEMBERS.items():
            result[index] = int.from_bytes(self.uc.mem_read(address,width),'little',signed=width==2)
        return pack(result)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--original',type=Path,default=Path(r'F:\TombRaiG\TOMBRAID\TOMB.EXE'))
    parser.add_argument('--exe',type=Path,nargs='+',required=True)
    parser.add_argument('--out',type=Path,default=ROOT/'analysis/c-movement-validation.json')
    args=parser.parse_args()
    started=time.monotonic()
    cases=list(generate())
    scratch=ROOT/'work/differential'
    scratch.mkdir(parents=True,exist_ok=True)
    inputs=scratch/'inputs.bin'
    inputs.write_bytes(b''.join(pack(c) for _,c in cases))
    outputs=[]
    for executable in args.exe:
        output=scratch/(executable.stem+'-output.bin')
        subprocess.run([str(executable.resolve()),'--batch',str(inputs),str(output)],check=True)
        data=output.read_bytes()
        assert len(data)==len(cases)*64, 'Missing/extra C output records'
        outputs.append((executable,data))
    original=Original(args.original)
    for i,(category,case) in enumerate(cases):
        expected=original.execute(case)
        for executable,data in outputs:
            actual=data[i*64:(i+1)*64]
            if actual != expected:
                failure=dict(index=i,category=category,executable=str(executable),
                    initial=dict(zip(FIELDS,case)),
                    expected=dict(zip(FIELDS,RECORD.unpack(expected))),
                    actual=dict(zip(FIELDS,RECORD.unpack(actual))))
                (scratch/'failure.json').write_text(json.dumps(failure,indent=2))
                raise AssertionError(f'Mismatch at case {i}: {scratch / "failure.json"}')
        if (i+1)%10000==0:
            print(f'Compared {i+1}/{len(cases)} cases',flush=True)
    report=dict(original_sha256=HASH,cases=len(cases),
        per_category=dict(Counter(category for category,_ in cases)),
        per_handler=dict(Counter(str(case[0]) for _,case in cases)),
        executables=[dict(path=str(exe),sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                         matched=len(cases)) for exe,_ in outputs],
        seed=19961105,elapsed_seconds=round(time.monotonic()-started,2),
        scope='Isolated control handlers and all represented fields; original memory writes checked. No full gameplay, animation, damping, collision, renderer or audio.',
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [ROOT/'src/movement.c',ROOT/'src/movement.h',ROOT/'tests/movement_runner.c',Path(__file__)]})
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2))
    print(f'PASS: {len(cases)} cases matched in {len(outputs)} C build(s). Report: {args.out}',flush=True)


if __name__=='__main__':
    main()
