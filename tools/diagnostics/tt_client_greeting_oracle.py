#!/usr/bin/env python3
"""Pinned TT greeting serialization with synthetic identity, no DLL startup.

Execute only the packet-building span of Init_Client. Model name/password/ID
providers and string cleanup, not the serializer. No registry, network or user
credentials are available. Output contains synthetic fixtures only.
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


def serialize(image, name, password, key, bandwidth, serial_hash, hardware):
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
    put(0x125f8278, 0x110000)
    put(0x110000, 0)
    put(0x125f8258, 0x110010)
    put(0x110010, key)
    put(0x120000, 0x120100)
    cpu.mem_write(0x120100, name.encode('utf-16le') + b'\0\0')
    put(0x121024, 0x121100)
    cpu.mem_write(0x121100, password.encode('utf-16le') + b'\0\0')
    put(0x122000, 0x122100)
    cpu.mem_write(0x122100, serial_hash.encode() + b'\0')
    put(0x12320e2c, 0x123100)
    cpu.mem_write(0x123100, hardware.encode() + b'\0')
    cpu.mem_write(0x123095f5, b'\0')
    put(0x122c96d4, 0x180000)  # WideStringClass::Free_String
    put(0x122c96f8, 0x180000)  # StringClass::Free_String
    def hook(machine, address, size, unused):
        if address not in (0x122b4ecc, 0x1214b3c0, 0x12003840, 0x121382a0, 0x180000):
            return
        sp = machine.reg_read(UC_X86_REG_ESP)
        if address == 0x122b4ecc:
            assert word(sp + 12) == 0x224 and word(sp + 8) == 0
            machine.mem_write(word(sp + 4), bytes(0x224))
            value, pop = word(sp + 4), 0
        elif address == 0x1214b3c0:
            value, pop = 0x120000, 0  # Caller removes the temporary return slot.
        elif address == 0x12003840:
            value, pop = 0x121000, 0
        elif address == 0x121382a0:
            value, pop = 0x122000, 0
        else:
            value, pop = 0, 0
        machine.reg_write(UC_X86_REG_EAX, value)
        machine.reg_write(UC_X86_REG_EIP, word(sp))
        machine.reg_write(UC_X86_REG_ESP, sp + 4 + pop)
    cpu.hook_add(UC_HOOK_CODE, hook)
    sp = 0x170000
    put(sp + 12, bandwidth)
    cpu.reg_write(UC_X86_REG_ESP, sp)
    cpu.emu_start(0x1214b9d2, 0x1214babb, timeout=5_000_000, count=500000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x1214babb
    packet = sp + 32
    bits = word(packet + 0x228)
    assert 0 < bits <= 548 * 8 and word(packet + 0x22c) == 0
    return {'bits': bits, 'hex': bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference DLL differs from pinned b9000')
    cases = []
    for name, password, key, bandwidth, hardware in (
            ('PS Vita', '', 0x12345678, 2000000, 'synthetic-vita-identity'),
            ('N' * 35, 'password', 0xffffffff, 100000000, ''),
            ('Fixture', 'P\u00e4ss', 0, 10000, 'a' * 64)):
        serial = hashlib.md5(b'synthetic-identity-not-a-retail-key').hexdigest()
        packet = serialize(image, name, password, key, bandwidth, serial, hardware)
        def text(value, wide=False):
            data = value.encode('utf-16be' if wide else 'ascii')
            return struct.pack('>H', len(value)) + data
        expected = text(name, True) + text(password, True) + struct.pack('>IIII', key, bandwidth, 0x21545421, 0x4099999a)
        expected += text(serial) + struct.pack('>I', 9000) + text(hardware)
        assert packet == {'bits': len(expected) * 8, 'hex': expected.hex()}, packet
        cases.append(dict(name=name, password=password, key=key, bandwidth=bandwidth,
                          serial_hash=serial, hardware=hardware, **packet))
    print(json.dumps({'schema': 1, 'reference_sha256': PIN, 'cases': cases,
                      'real_credentials_used': False, 'public_server_contacted': False}, indent=2))


if __name__ == '__main__':
    main()
