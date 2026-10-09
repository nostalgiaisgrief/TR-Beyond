"""Execute original DOS movement handlers in a bounded x86 emulator.

These probes validate isolated control decisions, not full frames or gameplay.
No reconstructed game implementation or TRX implementation is executed here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from analyse_le import load
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EDX, UC_X86_REG_ESP, UC_X86_REG_EIP

EXPECTED_HASH = '99503b7c4c7d88fdc2877c071b135ef041781fd76459de6b1cbf8b887ffe0fac'
HANDLERS = {'walk': 0x2515c, 'run': 0x251ec, 'stop': 0x252f8,
            'turn_right': 0x255bc, 'turn_left': 0x25644}
STATES = {'walk': 0, 'run': 1, 'stop': 2, 'turn_right': 6, 'turn_left': 7}
ITEM, COLL, STACK, RETURN = 0x200000, 0x201000, 0x210000, 0x220000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('exe', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raw, objects, fixes, _ = load(args.exe)
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_HASH, 'Different executable revision'
    emulator = Uc(UC_ARCH_X86, UC_MODE_32)
    for obj in objects:
        assert obj['base'] % 4096 == 0
        emulator.mem_map(obj['base'], (len(obj['data'])+4095) & ~4095)
        emulator.mem_write(obj['base'], bytes(obj['data']))
    for address in (ITEM, COLL, STACK, RETURN):
        emulator.mem_map(address, 4096)
    for name, address in HANDLERS.items():
        actual = struct.unpack('<I', emulator.mem_read(0xc3884+STATES[name]*4, 4))[0]
        assert actual == address

    def write16(address, value):
        emulator.mem_write(address, struct.pack('<H', value & 65535))

    def read16(address):
        return struct.unpack('<h', emulator.mem_read(address, 2))[0]

    results = []
    def probe(name, inputs, expected, rate=0, lean=0, hp=1000, gravity=False, gun=0):
        emulator.mem_write(ITEM, bytes(4096))
        emulator.mem_write(COLL, bytes(4096))
        emulator.mem_write(0xce900, bytes(0x200))
        emulator.mem_write(0xcb298, b'\0')
        write16(ITEM+0x0e, STATES[name])
        write16(ITEM+0x10, STATES[name])
        write16(ITEM+0x22, hp)
        write16(ITEM+0x40, lean)
        emulator.mem_write(ITEM+0x42, bytes([8 if gravity else 0]))
        emulator.mem_write(0xce92c, struct.pack('<I', inputs))
        write16(0xce9cc, rate)
        write16(0xce966, gun)
        emulator.mem_write(STACK+0x800, struct.pack('<I', RETURN))
        emulator.reg_write(UC_X86_REG_ESP, STACK+0x800)
        emulator.reg_write(UC_X86_REG_EAX, ITEM)
        emulator.reg_write(UC_X86_REG_EDX, COLL)
        emulator.emu_start(HANDLERS[name], RETURN, count=1000)
        assert emulator.reg_read(UC_X86_REG_EIP) == RETURN, 'Did not return within instruction budget'
        assert emulator.reg_read(UC_X86_REG_ESP) == STACK+0x804, 'Unbalanced stack'
        actual = dict(goal=read16(ITEM+0x10), rate=read16(0xce9cc), lean=read16(ITEM+0x40),
                      current=read16(ITEM+0x0e), animation=read16(ITEM+0x14), frame=read16(ITEM+0x16))
        for field, value in expected.items():
            assert actual[field] == value, (name, hex(inputs), field, actual, expected)
        results.append(dict(handler=name, inputs=hex(inputs), initial_rate=rate, initial_lean=lean,
                            hp=hp, gravity=gravity, gun=gun, expected=expected, actual=actual))

    probe('walk', 0, {'goal':2})
    probe('walk', 0x81, {'goal':0})
    probe('walk', 1, {'goal':1})
    probe('walk', 0x85, {'goal':0, 'rate':-409})
    probe('walk', 0x89, {'goal':0, 'rate':409})
    probe('walk', 0x8d, {'rate':-409})
    probe('walk', 0x85, {'rate':-728}, rate=-600)
    probe('walk', 0x89, {'rate':728}, rate=600)
    probe('walk', 0x85, {'goal':2, 'rate':0}, hp=0)
    probe('run', 0, {'goal':2})
    probe('run', 1, {'goal':1})
    probe('run', 0x81, {'goal':0})
    probe('run', 5, {'rate':-409, 'lean':-273})
    probe('run', 9, {'rate':409, 'lean':273})
    probe('run', 5, {'rate':-1456, 'lean':-2002}, rate=-1400, lean=-1900)
    probe('run', 9, {'rate':1456, 'lean':2002}, rate=1400, lean=1900)
    probe('run', 0x11, {'goal':3})
    probe('run', 0x11, {'goal':1}, gravity=True)
    probe('run', 0x1000, {'goal':2, 'current':45, 'animation':146, 'frame':3857})
    probe('run', 1, {'goal':8}, hp=0)
    probe('stop', 0, {'goal':2})
    probe('stop', 1, {'goal':1})
    probe('stop', 0x81, {'goal':0})
    probe('stop', 4, {'goal':7})
    probe('stop', 8, {'goal':6})
    probe('stop', 0x10, {'goal':15})
    probe('stop', 0x1000, {'goal':2, 'current':45, 'animation':146, 'frame':3857})
    probe('stop', 1, {'goal':8}, hp=0)
    probe('turn_right', 8, {'goal':6, 'rate':409})
    probe('turn_left', 4, {'goal':7, 'rate':-409})
    probe('turn_right', 8, {'goal':20, 'rate':1009}, rate=600)
    probe('turn_left', 4, {'goal':20, 'rate':-1009}, rate=-600)
    probe('turn_right', 0x88, {'goal':6, 'rate':728}, rate=600)
    probe('turn_left', 0x84, {'goal':7, 'rate':-728}, rate=-600)
    probe('turn_right', 9, {'goal':1})
    probe('turn_left', 0x85, {'goal':0})
    probe('turn_right', 0, {'goal':2})
    probe('turn_left', 0, {'goal':2})
    probe('turn_right', 8, {'goal':2, 'rate':0}, hp=0)
    probe('turn_left', 4, {'goal':2, 'rate':0}, hp=0)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dict(exe_sha256=EXPECTED_HASH, passed=len(results),
        scope='Original isolated x86 handlers; no animation advancement, collision or full-frame simulation',
        results=results), indent=2))
    print(f'{len(results)} original-machine-code probes passed.')


if __name__ == '__main__':
    main()
