#!/usr/bin/env python3
"""Execute the pinned b9000 options suffix with synthetic game providers.

Tier-one/tier-two virtual calls are omitted; this tests only the event suffix.
Actual branch selection and bit serialization execute. No network or identity.
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


def serialize(image, flag):
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
    game, table, event, packet = 0x110000, 0x120000, 0x130000, 0x140000
    put(game, table)
    put(table + 0x70, 0x180020)
    put(table + 0x7c, 0x180020)
    put(game + 0x228, 0x43a08000)  # 321 seconds
    put(event + 0x6b4, 42)
    put(0x1231ded4, 0x4099999a)
    put(0x1231ded0, 1)
    put(0x125fa534, 0x150000)
    cpu.mem_write(0x150000, b'\x01')
    cpu.mem_write(0x12320783, bytes([flag]))
    def hook(machine, address, size, unused):
        if address not in (0x12003840, 0x180020):
            return
        sp = machine.reg_read(UC_X86_REG_ESP)
        machine.reg_write(UC_X86_REG_EAX, game)
        machine.reg_write(UC_X86_REG_EIP, word(sp))
        machine.reg_write(UC_X86_REG_ESP, sp + (8 if address == 0x180020 else 4))
    cpu.hook_add(UC_HOOK_CODE, hook)
    put(0x170000, 0x190000)
    put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ECX, event)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    cpu.emu_start(0x1213fa30, 0x190000, timeout=5_000_000, count=500000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = word(packet + 0x228)
    payload = bytes(cpu.mem_read(packet + 4, (bits + 7) // 8))
    assert bits == 65 and payload == struct.pack('>II', 0x43a08000, 42) + bytes([flag << 7])
    return {'flag': bool(flag), 'bits': bits, 'hex': payload.hex()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'scope': 'options event suffix, tier serializers excluded',
                      'cases': [serialize(image, flag) for flag in (0, 1)]}, indent=2))
