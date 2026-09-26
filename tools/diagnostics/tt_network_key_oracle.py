#!/usr/bin/env python3
"""Execute the pinned PC compatibility-key routine on synthetic data versions.

TT hooks the data CRC (tested separately), not this original key combiner.
Only OS filename lookup, StringClass allocation and the supplied translation
version/data CRC are modeled. Original build-stamp and CRCEngine code executes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_network_crc import expected

PIN = '1325ed64b91c023caf6a96f35654156e0ef277069f6d1da580c258bb459a809e'


def reference(image, version, data_crc):
    pe = pefile.PE(data=image)
    cpu = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    cpu.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    cpu.mem_write(base, pe.get_memory_mapped_image())
    cpu.mem_map(0x100000, 0x100000)
    allocations = {}

    def put(address, value):
        cpu.mem_write(address, struct.pack('<I', value))

    def word(address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]

    def string(address):
        result = bytearray()
        for index in range(512):
            byte = cpu.mem_read(address + index, 1)[0]
            if not byte:
                return bytes(result)
            result.append(byte)
        raise RuntimeError('Unterminated reference string')

    def hook(machine, address, size, unused):
        if address not in (0x190010, 0x5dcfa0, 0x5dd230, 0x4029d0,
                           0x5dd5a0, 0x4027b0, 0x5dd410, 0x76cd10, 0x457040):
            return
        stack = machine.reg_read(UC_X86_REG_ESP)
        arg = lambda index: word(stack + 4 + 4 * index)
        ecx = machine.reg_read(UC_X86_REG_ECX)
        result = pop = 0
        if address == 0x190010:
            machine.mem_write(arg(1), b'synthetic.exe\0')
            result, pop = 13, 12
        elif address == 0x5dcfa0:
            assert arg(0) == 0 and arg(1) == 0
            allocations[ecx] = 0x110000 + 4096 * len(allocations)
            put(ecx, allocations[ecx])
            pop = 8
        elif address == 0x5dd230:
            assert arg(0) < 512 and ecx in allocations
            pop = 4
        elif address == 0x4029d0:
            pop = 4
        elif address == 0x5dd5a0:
            fmt = string(arg(1))
            assert fmt in (b'RENEGADE %u', b'strings.tdb %u')
            value = fmt.replace(b'%u', str(arg(2)).encode())
            machine.mem_write(word(arg(0)), value + b'\0')
            result = len(value)
        elif address == 0x4027b0:
            result = len(string(word(ecx)))
        elif address == 0x5dd410:
            assert ecx in allocations
        elif address == 0x76cd10:
            result = version
        elif address == 0x457040:
            result = data_crc
        machine.reg_write(UC_X86_REG_EAX, result)
        machine.reg_write(UC_X86_REG_EIP, word(stack))
        machine.reg_write(UC_X86_REG_ESP, stack + 4 + pop)

    put(0x7cd304, 0x190010)
    put(0x17f000, 0x190000)
    cpu.reg_write(UC_X86_REG_ESP, 0x17f000)
    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.emu_start(0x457450, 0x190000, timeout=5_000_000, count=100_000)
    if cpu.reg_read(UC_X86_REG_EIP) != 0x190000:
        raise RuntimeError('Reference execution exceeded budget')
    return word(0x820d78), word(0x820d7c), word(0x820d80)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('exe', type=Path)
    args = parser.parse_args()
    image = args.exe.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference executable differs from inspected retail client')
    build = struct.unpack_from('<I', image, 0x3f7cdc + 28)[0]
    count = 0
    for version in (0, 1, 12345, 0xffffffff):
        for data_crc in (0, 0x12345678, 0x80000000, 0xffffffff):
            exe = ('RENEGADE %u' % build).encode()
            strings = ('strings.tdb %u' % version).encode()
            got = reference(image, version, data_crc)
            want = (expected(exe + b' ' + strings + b' ') ^ data_crc,
                    expected(exe), expected(strings))
            assert got == want, (got, want)
            count += 1
    print(json.dumps({'reference_sha256': PIN, 'retail_wire_build': build,
                      'synthetic_vectors_passed': count,
                      'evidence_class': 'isolated_x86_function'}))


if __name__ == '__main__':
    main()
