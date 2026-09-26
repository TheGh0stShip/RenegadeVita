#!/usr/bin/env python3
"""Execute pinned TT soldier rare suffix export with synthetic state only.

The physical prefix is deliberately excluded; its separate oracle verifies it.
Original suffix field/version selection and bit serialization execute unchanged.
No DLL initialization, retail assets, credentials or network access.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def serialize(image, modern, alternate):
    pe = pefile.PE(data=image)
    cpu = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    cpu.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    cpu.mem_write(base, pe.get_memory_mapped_image())
    cpu.mem_map(0x100000, 0x100000)
    def put(address, value):
        cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))
    def word(address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]
    obj, table, definition, packet = 0x110000, 0x120000, 0x130000, 0x160000
    put(obj, table)
    put(table + 0xc8, 0x180010)
    cpu.mem_write(0x180010, b'\xd9\x05' + struct.pack('<I', 0x180100) + b'\xc3')
    cpu.mem_write(0x180100, struct.pack('<f', 1.75 if alternate else 1.0))
    put(obj + 8 + 0x6b4, definition)
    put(definition, 0x130100)
    put(0x130100 + 0x24, 0x180000)
    flags = {0xd25: not alternate, 0xd26: True, 0xd44: alternate,
             0xd45: alternate, 0xd50: not alternate, 0xd5c: not alternate,
             0xd5e: alternate, 0xd78: alternate, 0xd84: not alternate}
    for offset, value in flags.items():
        cpu.mem_write(obj + 8 + offset, bytes([value]))
    for offset, value in {0xd54: 1.25 if alternate else 1.0,
                          0xd64: 0.2 if alternate else 0.0,
                          0xd68: -0.1 if alternate else 0.0,
                          0xd88: 0.4 if alternate else 0.0,
                          0xd8c: 0.3 if alternate else 0.0,
                          0xd90: 0.05 if alternate else 0.0,
                          0xd94: 0.1 if alternate else 0.0}.items():
        cpu.mem_write(obj + 8 + offset, struct.pack('<f', value))
    put(obj + 8 + 0xd74, 2 if alternate else -1)
    tag = 'VitaBot' if alternate else ''
    put(obj + 8 + 0xd7c, 0x150008)
    put(0x150000, len(tag) + 1)
    put(0x150004, len(tag))
    cpu.mem_write(0x150008, tag.encode('utf-16le') + b'\0\0')
    put(0x1231ded4, 0x4099999a if modern else 0)
    put(0x1231ded0, 9000 if modern else 0)
    put(0x125fa534, 0x150410)
    cpu.mem_write(0x150410, b'\x01')
    def hook(machine, address, size, unused):
        if address not in (0x121f1120, 0x180000):
            return
        sp = machine.reg_read(UC_X86_REG_ESP)
        if address == 0x180000:
            machine.reg_write(UC_X86_REG_EAX, 0x30010001)
        machine.reg_write(UC_X86_REG_EIP, word(sp))
        machine.reg_write(UC_X86_REG_ESP, sp + (8 if address == 0x121f1120 else 4))
    cpu.hook_add(UC_HOOK_CODE, hook)
    put(0x170000, 0x190000)
    put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ECX, obj + 8)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    cpu.emu_start(0x1224b5a0, 0x190000, timeout=5_000_000, count=500000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = word(packet + 0x228)
    assert 0 < bits <= 548 * 8
    return {'modern': modern, 'alternate': alternate, 'bits': bits,
            'hex': bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'scope': 'soldier rare suffix, synthetic state, physical prefix excluded',
                      'cases': [serialize(image, modern, alternate)
                                for modern, alternate in ((False, False), (True, False), (True, True))]}, indent=2))
