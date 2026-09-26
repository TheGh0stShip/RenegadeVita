#!/usr/bin/env python3
"""Execute pinned TT physical rare export with synthetic object/model providers.

Real field selection and serialization execute. No DLL startup, game assets,
network, identity or user state. Animation-controller absence is modeled.
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


def serialize(image, modern):
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
    obj, table, phys, model, model_table, packet = 0x110000, 0x120000, 0x130000, 0x140000, 0x150000, 0x160000
    put(obj, table)
    put(table + 0x28, 0x180000)  # As_VehicleGameObj: no vehicle
    put(table + 0x68, 0x180010)  # Player type: GDI
    put(obj + 8 + 0x76c, phys)
    put(phys + 0x38, 3)
    put(phys + 0x3c, model)
    put(model, model_table)
    put(model_table + 0x10, 0x180020)  # Model name
    put(model_table + 0x17c, 0x180030)  # Hidden
    cpu.mem_write(0x150400, b'VITA_MODEL\0')
    put(obj + 8 + 0x798, 2)  # Radar color
    put(obj + 8 + 0x794, 1)  # Radar shape
    put(obj + 8 + 0x790, 5)  # Host bone
    cpu.mem_write(obj + 8 + 0x7a4, b'\x01')  # HUD indicator
    put(0x1231ded4, 0x4099999a if modern else 0)
    put(0x1231ded0, 9000 if modern else 0)
    put(0x125fa534, 0x150410)
    cpu.mem_write(0x150410, b'\x01')
    put(0x125fa434, 0x150420)  # No local star
    def hook(machine, address, size, unused):
        values = {0x180000: 0, 0x180010: 1, 0x180020: 0x150400, 0x180030: 1}
        if address not in values:
            return
        sp = machine.reg_read(UC_X86_REG_ESP)
        machine.reg_write(UC_X86_REG_EAX, values[address])
        machine.reg_write(UC_X86_REG_EIP, word(sp))
        machine.reg_write(UC_X86_REG_ESP, sp + 4)
    cpu.hook_add(UC_HOOK_CODE, hook)
    put(0x170000, 0x190000)
    put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ECX, obj + 8)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    cpu.emu_start(0x121f1120, 0x190000, timeout=5_000_000, count=500000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = word(packet + 0x228)
    assert 0 < bits <= 548 * 8
    return {'modern': modern, 'bits': bits,
            'hex': bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'scope': 'physical rare export, synthetic providers, no animation controller',
                      'cases': [serialize(image, modern) for modern in (False, True)]}, indent=2))
