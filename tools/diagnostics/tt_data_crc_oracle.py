#!/usr/bin/env python3
"""Compare pinned TT data-CRC code with synthetic files, without initializing TT.

Only StringClass allocation/copy and FileClass calls are modeled. The actual x86
filename decoding, file iteration and CRC instructions execute in Unicorn.
No retail assets, credentials, OS services or network are exposed to the guest.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def reference(image, files, max_read):
    pe = pefile.PE(data=image)
    cpu = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    cpu.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    cpu.mem_write(base, pe.get_memory_mapped_image())
    cpu.mem_map(0x100000, 0x100000)

    def put(address, value):
        cpu.mem_write(address, struct.pack('<I', value))

    def word(address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]

    def string(address):
        result = bytearray()
        for index in range(256):
            byte = cpu.mem_read(address + index, 1)[0]
            if not byte:
                return bytes(result)
            result.append(byte)
        raise RuntimeError('Unterminated reference string')

    names = [bytes(byte ^ 5 for byte in string(word(address))).decode('ascii')
             for address in range(0x12312bb0, 0x12312cbc, 4)]
    # StringClass's empty string indirection and modeled allocator methods.
    put(0x122c96ec, 0x110000)
    put(0x110000, 0x110010)
    put(0x110010, 0x110100)
    put(0x122c96e8, 0x180000)
    put(0x122c96f4, 0x180010)
    put(0x122c96f8, 0x180020)
    # Factory global -> factory object -> vtable; one live file at a time.
    put(0x125fa328, 0x120000)
    put(0x120000, 0x120010)
    put(0x120010, 0x120100)
    put(0x120104, 0x180030)
    put(0x120108, 0x180040)
    put(0x130000, 0x130100)
    for offset, handler in ((0x14, 0x180050), (0x1c, 0x180060),
                            (0x24, 0x180070), (0x38, 0x180080)):
        put(0x130100 + offset, handler)
    current = None
    position = 0
    opened = False
    acquired = returned = reads = 0
    visited = []

    def hook(machine, address, size, unused):
        nonlocal current, position, opened, acquired, returned, reads
        if address not in (0x122b5244, *range(0x180000, 0x180090, 16)):
            return
        stack = machine.reg_read(UC_X86_REG_ESP)
        arg = lambda index: word(stack + 4 + 4 * index)
        ecx = machine.reg_read(UC_X86_REG_ECX)
        pop = result = 0
        if address in (0x180000, 0x180010):
            put(ecx, 0x140010)
            pop = 8 if address == 0x180000 else 4
        elif address == 0x180020:
            pass
        elif address == 0x122b5244:
            machine.mem_write(arg(0), bytes(machine.mem_read(arg(1), arg(2))))
            result = arg(0)
        elif address == 0x180030:
            assert current is None and not opened
            name = string(arg(0)).decode('ascii')
            visited.append(name)
            pop = 4
            if name in files:
                current, position = name, 0
                acquired += 1
                result = 0x130000
        elif address == 0x180040:
            assert current is not None and not opened and arg(0) == 0x130000
            returned += 1
            current = None
            pop = 4
        elif address == 0x180050:
            assert current is not None
            result, pop = int(files[current] is not None), 4
        elif address == 0x180060:
            assert current is not None and not opened and arg(0) == 1
            opened = True
            result, pop = 1, 4
        elif address == 0x180070:
            assert opened and arg(1) == 16384
            chunk = files[current][position:position + min(arg(1), max_read)]
            if chunk:
                machine.mem_write(arg(0), chunk)
            position += len(chunk)
            reads += 1
            result, pop = len(chunk), 8
        elif address == 0x180080:
            assert opened
            opened = False
        machine.reg_write(UC_X86_REG_EAX, result)
        machine.reg_write(UC_X86_REG_EIP, word(stack))
        machine.reg_write(UC_X86_REG_ESP, stack + 4 + pop)

    cpu.hook_add(UC_HOOK_CODE, hook)
    put(0x17f000, 0x190000)
    cpu.reg_write(UC_X86_REG_ESP, 0x17f000)
    cpu.emu_start(0x1214f1f0, 0x190000, timeout=10_000_000, count=5_000_000)
    if cpu.reg_read(UC_X86_REG_EIP) != 0x190000:
        raise RuntimeError('Reference execution exceeded budget')
    assert current is None and not opened and acquired == returned
    assert visited == names
    return cpu.reg_read(UC_X86_REG_EAX), names, reads


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference DLL differs from inspected b9000 revision')
    source = args.source.read_text().split('char * filelist[] = {', 1)[1].split('};', 1)[0]
    original = [bytes(ord(byte) ^ 5 for byte in name).decode('ascii')
                for name in re.findall(r'^\s*"([^"]+)"', source, re.MULTILINE)]
    patterns = ({}, {'objects.ddb': b''}, {'objects.ddb': None},
                {'objects.ddb': bytes(range(256)) * 131,
                 'armor.ini': b'123456789', 'c_gdi_syd_l0.w3d': b'repeated-entry'})
    count = 0
    for files in patterns:
        for max_read in (16384, 4096, 31):
            got, names, reads = reference(image, files, max_read)
            assert names == original, 'TT checksum file order differs from original'
            expected = 0
            for name in names:
                expected = zlib.crc32(files.get(name) or b'', expected)
            assert got == expected, (got, expected)
            count += 1
    print(json.dumps({'reference_sha256': PIN, 'file_entries': len(original),
                      'synthetic_vectors_passed': count, 'retail_assets_used': False,
                      'evidence_class': 'isolated_x86_function'}))


if __name__ == '__main__':
    main()
