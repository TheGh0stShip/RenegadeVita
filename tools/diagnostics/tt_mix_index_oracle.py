#!/usr/bin/env python3
"""Execute retail's MIX index-order check/sort using synthetic entries only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EDI, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def check(image, entries):
    pe = pefile.PE(data=image)
    cpu = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    cpu.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    cpu.mem_write(base, pe.get_memory_mapped_image())
    cpu.mem_map(0x100000, 0x100000)
    obj, vector = 0x110000, 0x120000
    cpu.mem_write(obj + 12, struct.pack('<I', vector))
    cpu.mem_write(obj + 24, struct.pack('<I', len(entries)))
    if entries:
        cpu.mem_write(vector, b''.join(struct.pack('<III', *e) for e in entries))
    stopped = []
    def stop(machine, address, size, unused):
        if address in (0x12009a90, 0x12009ac6):
            stopped.append(address)
            machine.emu_stop()
    cpu.hook_add(UC_HOOK_CODE, stop)
    cpu.reg_write(UC_X86_REG_EDI, obj)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    cpu.emu_start(0x12009a66, 0x190000, timeout=5_000_000, count=1000000)
    assert stopped, 'Retail index sorting did not reach constructor continuation'
    actual = list(struct.iter_unpack('<III', cpu.mem_read(vector, 12 * len(entries)))) if entries else []
    assert sorted(actual) == sorted(entries), 'Sort changed a CRC/member range'
    assert all(actual[i - 1][0] <= actual[i][0] for i in range(1, len(actual)))
    return {'entries': len(entries), 'sorted': True, 'ranges_preserved': True,
            'input_unchanged': actual == entries}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    ordered = [(i * 1234567, 16 + i * 512, i + 1) for i in range(201)]
    cases = [[], ordered[:1], ordered, list(reversed(ordered)),
             ordered[10:] + list(reversed(ordered[:10]))]
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'owner_check': '0x12009a66', 'owner_sort': '0x1200a7c0',
                      'cases': [check(image, case) for case in cases]}, indent=2))
