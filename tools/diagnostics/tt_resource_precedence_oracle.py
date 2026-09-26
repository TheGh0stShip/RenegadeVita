#!/usr/bin/env python3
"""Execute pinned TT resource index insertion/lookup on synthetic names only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def check(image):
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
    # One bucket forces ordinary hash collisions as well as duplicate names.
    table, bucket, entries = 0x110000, 0x111000, 0x112000
    for offset, value in enumerate((bucket, entries, 0, 1)):
        put(table + offset * 4, value)
    put(bucket, -1)
    empty = 0x113100
    put(0x122c96ec, 0x113000)
    put(0x113000, 0x113010)
    put(0x113010, empty)
    for i in range(3):
        put(entries + i * 12, i + 1 if i < 2 else -1)
        put(entries + i * 12 + 4, empty)
        put(entries + i * 12 + 8, empty)
    put(0x122c96f4, 0x180000)  # Imported StringClass::Uninitialised_Grow.
    allocations = [0x140000]
    def hook(machine, address, size, unused):
        if address not in (0x180000, 0x122b5244):
            return
        sp = machine.reg_read(UC_X86_REG_ESP)
        arg = lambda i: word(sp + 4 + i * 4)
        if address == 0x180000:
            assert 0 < arg(0) < 256
            allocations[0] += 512
            put(machine.reg_read(UC_X86_REG_ECX), allocations[0])
            value, pop = 0, 4
        else:
            assert arg(2) < 256
            machine.mem_write(arg(0), bytes(machine.mem_read(arg(1), arg(2))))
            value, pop = arg(0), 0
        machine.reg_write(UC_X86_REG_EAX, value)
        machine.reg_write(UC_X86_REG_EIP, word(sp))
        machine.reg_write(UC_X86_REG_ESP, sp + 4 + pop)
    cpu.hook_add(UC_HOOK_CODE, hook)
    def string(address, value):
        data = value.encode()
        put(address, address + 32)
        put(address + 28, len(data))
        cpu.mem_write(address + 32, data + b'\0')
    def call(address, *args):
        sp = 0x17f000
        put(sp, 0x190000)
        for i, value in enumerate(args):
            put(sp + 4 + 4 * i, value)
        cpu.reg_write(UC_X86_REG_ECX, table)
        cpu.reg_write(UC_X86_REG_ESP, sp)
        cpu.emu_start(address, 0x190000, timeout=2_000_000, count=100000)
        assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
        return cpu.reg_read(UC_X86_REG_EAX)
    for name, value in [('stylemgr.ini', 'first'), ('stylemgr.ini', 'last'), ('other.ini', 'collision')]:
        string(0x120000, name)
        string(0x121000, value)
        call(0x121b58d0, 0x120000, 0x121000)
    for name, expected in [('stylemgr.ini', b'last'), ('other.ini', b'collision'), ('missing.ini', None)]:
        string(0x120000, name)
        found = call(0x12006460, 0x120000)
        if expected is None:
            assert found == 0
        else:
            assert found and bytes(cpu.mem_read(word(found), len(expected) + 1)) == expected + b'\0'
    # TT's archive activation prepends factories (0x122177e0). Execute its
    # actual chain reader with that order; model only Get_File/Is_Available.
    chain, vector, vtable, file_vtable = 0x150000, 0x151000, 0x152000, 0x153000
    put(chain + 4, 0)
    put(chain + 12, vector)
    put(chain + 20, 3)
    put(vtable + 4, 0x180100)
    put(file_vtable + 20, 0x180110)
    factories = [0x154000, 0x154100, 0x154200]
    available = set(factories)
    calls = []
    for i, factory in enumerate(factories):
        put(vector + i * 4, factory)
        put(factory, vtable)
        put(factory + 32, file_vtable)
    def factory_hook(machine, address, size, unused):
        if address not in (0x180100, 0x180110):
            return
        sp = machine.reg_read(UC_X86_REG_ESP)
        owner = machine.reg_read(UC_X86_REG_ECX)
        if address == 0x180100:
            calls.append(owner)
            value = owner + 32 if owner in available else 0
        else:
            value = 1
        machine.reg_write(UC_X86_REG_EAX, value)
        machine.reg_write(UC_X86_REG_EIP, word(sp))
        machine.reg_write(UC_X86_REG_ESP, sp + 8)
    cpu.hook_add(UC_HOOK_CODE, factory_hook)
    table = chain
    for expected in factories:
        calls.clear()
        assert call(0x120076e0, 0x120020) == expected + 32
        assert calls[-1] == expected
        available.remove(expected)
    assert call(0x120076e0, 0x120020) == 0
    return {'last_inserted_duplicate_wins': True, 'collision_lookup': True, 'missing_returns_null': True,
            'original_chain_first_available_wins': True, 'archive_before_loose_from_activation': True,
            'reference_sha256': PIN, 'proprietary_code_copied': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference DLL differs from pinned b9000')
    print(json.dumps(check(image), indent=2))
