#!/usr/bin/env python3
"""Run pinned TT resource serializers on synthetic groups in isolated x86.

Actual packet construction and bit/string serialization execute. Only memset
and the final transport send are modeled. No DLL startup, network, identity,
retail data or proprietary code is emitted. Output is synthetic wire fixtures.
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


def serialize(image, group_id, name, packages, remove=False):
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

    # Synthetic remote host, resource group, strings/vector and local peer ID.
    put(0x110000 + 0x3cc, 9000)
    put(0x120000, group_id)
    put(0x120004, 0x121000)
    cpu.mem_write(0x121000, name.encode('ascii') + b'\0')
    put(0x120010, 0x122000)
    put(0x120014, len(packages))
    for index, package in enumerate(packages):
        put(0x122000 + 4 * index, package)
    put(0x125f8278, 0x130000)
    put(0x130000, 0x130010)
    put(0x130010, 0)
    cpu.mem_write(0x123095f5, b'\0')  # No optional packet statistics provider.
    packets = []

    def hook(machine, address, size, unused):
        if address not in (0x122b4ecc, 0x121651d0):
            return
        stack = machine.reg_read(UC_X86_REG_ESP)
        arg = lambda index: word(stack + 4 + 4 * index)
        if address == 0x122b4ecc:
            assert arg(2) == 0x224 and arg(1) == 0
            machine.mem_write(arg(0), bytes(arg(2)))
            result, pop = arg(0), 0
        else:
            assert machine.reg_read(UC_X86_REG_ECX) == 0x110000 and arg(1) == 0
            packet = arg(0)
            bits = word(packet + 0x228)
            assert 0 < bits <= 548 * 8 and word(packet + 0x22c) == 0
            packets.append({'type': machine.mem_read(packet + 0x244, 1)[0],
                            'sequence': word(packet + 0x248), 'bits': bits,
                            'hex': bytes(machine.mem_read(packet + 4, (bits + 7) // 8)).hex()})
            result, pop = 0, 8
        machine.reg_write(UC_X86_REG_EAX, result)
        machine.reg_write(UC_X86_REG_EIP, word(stack))
        machine.reg_write(UC_X86_REG_ESP, stack + 4 + pop)

    put(0x17f000, 0x190000)
    put(0x17f004, 0x110000)
    put(0x17f008, group_id if remove else 0x120000)
    cpu.reg_write(UC_X86_REG_ESP, 0x17f000)
    cpu.reg_write(UC_X86_REG_ECX, 0)
    cpu.hook_add(UC_HOOK_CODE, hook)
    cpu.emu_start(0x12217d40 if remove else 0x12217ae0, 0x190000,
                  timeout=5_000_000, count=500_000)
    if cpu.reg_read(UC_X86_REG_EIP) != 0x190000:
        raise RuntimeError('Reference execution exceeded budget')
    return packets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference DLL differs from inspected b9000 revision')
    cases = []
    for group, name, packages in ((0, '', []), (1, 'C&C_Fixture.mix', [0x12345678]),
                                   (0xffffffff, 'synthetic-group', [0, 0xffffffff, 0x89abcdef]),
                                   (17, 'x' * 255, list(range(64)))):
        packets = serialize(image, group, name, packages)
        payloads = [struct.pack('>IIH', 0, group, len(name)) + name.encode('ascii') +
                    struct.pack('>I', len(packages))]
        payloads += [struct.pack('>II', 0, package) for package in reversed(packages)]
        for index, (packet, payload) in enumerate(zip(packets, payloads)):
            assert packet == {'type': 8, 'sequence': index, 'bits': len(payload) * 8,
                              'hex': payload.hex()}, packet
        assert len(packets) == len(payloads)
        remove = serialize(image, group, name, [], remove=True)
        assert remove == [{'type': 8, 'sequence': 0, 'bits': 64,
                           'hex': struct.pack('>II', 1, group).hex()}]
        cases.append({'id': group, 'name': name, 'packages': packages,
                      'packets': packets, 'remove': remove})
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'evidence_class': 'isolated_x86_serializer', 'cases': cases}, indent=2))


if __name__ == '__main__':
    main()
