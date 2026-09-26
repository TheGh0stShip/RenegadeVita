#!/usr/bin/env python3
"""Execute retail b9000 C4 rare export, excluding the separately verified Physical prefix."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def serialize(image, mode):
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
    def floats(address, *values):
        cpu.mem_write(address, struct.pack('<' + 'f' * len(values), *values))
    obj, packet = 0x110008, 0x160000
    put(0x1231ded4, 0x4099999a); put(0x1231ded0, 9000)
    put(0x125fa534, 0x150000); cpu.mem_write(0x150000, b'\x01')
    put(obj + 0x7c0, 0x151000); put(0x151000, 0x151100); put(0x151124, 0x180000)
    put(obj + 0x7b4, 0x152000); put(0x152004, 0x152100); put(0x15210c, 1234)
    put(obj + 0x76c, 0x153000); put(0x153000, 0x153100)
    put(0x1531bc, 0x180010); put(0x153118, 0x180020); put(0x1531f4, 0x180030)
    floats(0x153400, 1, 0, 0, 100.125, 0, 1, 0, 200.25, 0, 0, 1, 30.5)
    cpu.mem_write(obj + 0x7c8, bytes([mode != 0, mode == 2]))
    cpu.mem_write(obj + 0x7f0, bytes([mode == 3]))
    if mode == 2:
        put(obj + 0x7d4, 0x154000); put(0x154004, 0x154100); put(0x15410c, 5678)
    floats(obj + 0x7dc, 0.25, -0.5, 0.75); put(obj + 0x7e8, 3)
    if mode == 3:
        put(obj + 0x7ec, 0x155000); put(0x155044, 42)
    def hook(uc, address, size, unused):
        cleanup = 0
        sp = uc.reg_read(UC_X86_REG_ESP)
        if address == 0x121f1120:
            cleanup = 4
        elif address == 0x180000:
            uc.reg_write(UC_X86_REG_EAX, 123456)
        elif address == 0x180010:
            uc.reg_write(UC_X86_REG_EAX, 0x153000)
        elif address == 0x180020:
            uc.reg_write(UC_X86_REG_EAX, 0x153400)
        elif address == 0x180030:
            floats(word(sp + 4), 1, 2, 3); cleanup = 4
        else:
            return
        uc.reg_write(UC_X86_REG_EIP, word(sp))
        uc.reg_write(UC_X86_REG_ESP, sp + 4 + cleanup)
    cpu.hook_add(UC_HOOK_CODE, hook)
    put(0x170000, 0x190000); put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000); cpu.reg_write(UC_X86_REG_ECX, obj)
    cpu.emu_start(0x12134b10, 0x190000, timeout=5_000_000, count=100000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = word(packet + 0x228)
    return dict(mode=mode, bits=bits, hex=bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    print(json.dumps(dict(schema=1, reference_sha256=PIN, scope=__doc__,
                         cases=[serialize(image, mode) for mode in range(4)]), indent=2))
