#!/usr/bin/env python3
"""Execute pinned retail catalog factories and availability serializers on synthetic definitions."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def reference(image, team_catalog, pattern, compressed):
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
    obj, packet, stack, stop = 0x11001c, 0x160000, 0x170000, 0x190000
    put(0x125fa534, 0x150000)
    cpu.mem_write(0x150000, bytes([compressed]))
    count = 12 if team_catalog else 33
    flags = [pattern == 'all' or (pattern == 'mixed' and i % 3 == 1) for i in range(count)]
    offsets = list(range(0x6f8, 0x704)) if team_catalog else list(range(0x75c, 0x77a)) + [0x8f0, 0x8f1, 0x8f2]
    for offset, flag in zip(offsets, flags):
        cpu.mem_write(obj + offset, bytes([flag]))
    def run(entry, args):
        put(stack, stop)
        for i, arg in enumerate(args):
            put(stack + 4 + 4 * i, arg)
        cpu.reg_write(UC_X86_REG_ESP, stack)
        cpu.reg_write(UC_X86_REG_ECX, obj)
        cpu.emu_start(entry, stop, timeout=5_000_000, count=100000)
        assert cpu.reg_read(UC_X86_REG_EIP) == stop
    run(0x1225d6f0 if team_catalog else 0x12202680, [packet])
    bits = word(packet + 0x228)
    assert bits == count * (1 if compressed else 8)
    payload = bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex()
    for offset in offsets:
        cpu.mem_write(obj + offset, b'\x00')
    run(0x1225d8c0 if team_catalog else 0x12202b40, [packet])
    assert [cpu.mem_read(obj + offset, 1)[0] != 0 for offset in offsets] == flags
    # Execute actual factory Prep_Packet and Create; lookup must preserve identity.
    cpu.mem_write(packet, bytes(0x234))
    team, page = 1, 6
    put(obj - 0x1c + 0x6d0, team)
    put(obj - 0x1c + 0x6d4, page)
    put((0x1231f948 + team * 4) if team_catalog else (0x1231e970 + (team * 7 + page) * 4), obj - 0x1c)
    run(0x1225dad0 if team_catalog else 0x12203090, [obj, packet])
    factory_bits = word(packet + 0x228)
    factory_hex = bytes(cpu.mem_read(packet + 4, factory_bits // 8)).hex()
    run(0x1225db10 if team_catalog else 0x122030e0, [packet])
    assert cpu.reg_read(UC_X86_REG_EAX) == obj
    return dict(network_class=2005 if team_catalog else 2004, pattern=pattern,
                compressed=compressed, flags=flags, bits=bits, hex=payload,
                factory_bits=factory_bits, factory_hex=factory_hex, team=team,
                page=None if team_catalog else page)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    print(json.dumps(dict(schema=1, reference_sha256=PIN, scope=__doc__,
        cases=[reference(image, team, pattern, compression) for team in (False, True)
               for pattern in ('none', 'all', 'mixed') for compression in (False, True)]), indent=2))
