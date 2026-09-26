#!/usr/bin/env python3
"""Execute pinned defense export/import with synthetic DataSafe values only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def serialize(image, modern, zero):
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
    obj, packet, encoders = 0x110000, 0x160000, 0x140000
    values = {4: 0.0 if zero else (8000.0 if modern else 100.0),
              8: 9000.0, 12: 1, 16: 5000.0 if modern else 50.0, 20: 6000.0, 24: 3}
    for offset, value in values.items():
        address = 0x150000 + offset
        put(obj + offset, address)
        cpu.mem_write(address, struct.pack('<I' if offset in (12, 24) else '<f', value))
    put(0x1231ded4, 0x4099999a if modern else 0)
    put(0x1231ded0, 9000 if modern else 0)
    put(0x125fa534, 0x150410)
    cpu.mem_write(0x150410, b'\x01')
    put(0x125fa538, encoders)
    for index, maximum, bits in ((6, 2000, 11), (7, 2000, 11), (8, 31, 5),
                                  (26, 10000, 14), (27, 10000, 14)):
        cpu.mem_write(encoders + index * 32,
                      struct.pack('<dddII', 0., maximum, maximum / ((1 << bits) - 1), bits, 1))
    def hook(machine, address, size, unused):
        if address not in (0x120033d0, 0x12003600, 0x120031c0):
            return
        sp = machine.reg_read(UC_X86_REG_ESP)
        destination = machine.reg_read(UC_X86_REG_ECX)
        value_address = word(sp + 4)
        assert 0x150000 < value_address < 0x150100
        if address == 0x120031c0:
            cpu.mem_write(value_address, bytes(cpu.mem_read(destination, 4)))
        else:
            put(destination, value_address)
        machine.reg_write(UC_X86_REG_EAX, destination)
        machine.reg_write(UC_X86_REG_EIP, word(sp))
        machine.reg_write(UC_X86_REG_ESP, sp + 4)
    cpu.hook_add(UC_HOOK_CODE, hook)
    put(0x170000, 0x190000)
    put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ECX, obj)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    cpu.emu_start(0x1216f560, 0x190000, timeout=5_000_000, count=500000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = word(packet + 0x228)
    assert 0 < bits <= 548 * 8
    result = {'modern': modern, 'zero': zero, 'bits': bits,
              'hex': bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex()}
    cpu.reg_write(UC_X86_REG_ECX, obj)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    cpu.emu_start(0x1216ef10, 0x190000, timeout=5_000_000, count=500000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    assert word(packet + 0x22c) == bits
    result['decoded'] = {
        name: struct.unpack('<I' if offset in (12, 24) else '<f',
                            cpu.mem_read(0x150000 + offset, 4))[0]
        for name, offset in (('health', 4), ('health_max', 8), ('skin', 12),
                             ('shield', 16), ('shield_max', 20), ('shield_type', 24))}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'scope': 'defense export/import, synthetic DataSafe values and armor count',
                      'cases': [serialize(image, modern, zero)
                                for modern, zero in ((False, False), (True, False), (True, True))]}, indent=2))
