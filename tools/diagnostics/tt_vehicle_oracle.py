#!/usr/bin/env python3
"""Execute pinned b9000 vehicle exports against synthetic objects/accessors.

Rare excludes its separately verified physical prefix. Frequent executes the
complete shared tail. Occasional excludes Defense, but executes the original
weapon ID-list serializer. No retail initialization, assets or network access.
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


def serialize(image, mode, alternate=False, turret=False):
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
    obj, packet, encoders = 0x110008, 0x160000, 0x140000
    put(0x1231ded4, 0x4099999a)
    put(0x1231ded0, 9000)
    put(0x125fa534, 0x150410)
    cpu.mem_write(0x150410, b'\x01')
    put(0x125fa538, encoders)
    for index, values in {4: (0., 15., 1., 4), 5: (-1., 1., 2. / 255, 8),
                          12: (-90., 90., 180. / 32767, 15),
                          13: (-20., 20., 40. / 4095, 12),
                          14: (-1., 1., 2. / 4095, 12)}.items():
        cpu.mem_write(encoders + index * 32, struct.pack('<dddII', *values, 1))
    put(obj - 8, 0x151000)
    put(0x1510c4, 0x180000)  # Apply_Control: exclude simulation from serialization.
    put(obj + 0x6b4, 0x152000)
    put(0x1520e0, 4 if turret else 1)
    put(obj + 0x76c, 0x153000)
    put(0x153000, 0x153400)
    put(0x15347c, 0x180010)  # As_VehiclePhysClass
    put(0x153418, 0x180020)  # Get_Transform
    put(0x1534f4, 0x180030)  # Get_Velocity
    put(0x153504, 0x180040)  # Get_Angular_Velocity
    floats(0x153600, 1, 0, 0, 100.125, 0, 1, 0, 200.25, 0, 0, 1, 30.5)
    floats(0x153124, 0, 0, 0, 1)
    put(0x153038, 0x100 if alternate else 0)
    cpu.mem_write(0x1532b0, b'\x01')
    flags = {0x98b: alternate, 0x98c: not alternate, 0x9e4: not alternate,
             0x9e5: alternate, 0x9e7: alternate, 0x9fc: True,
             0x9fd: not alternate, 0x9fe: alternate, 0x9ff: alternate}
    for offset, value in flags.items():
        cpu.mem_write(obj + offset, bytes([value]))
    cpu.mem_write(obj + 0x9e6, bytes([1 if alternate else 2]))
    floats(obj + 0xa04, 0.75, -0.25)
    put(obj + 0x9a8, 0x154000)
    put(obj + 0x9ac, 2)
    if alternate:
        put(0x154000, 0x154100)
        put(0x15410c, 1234)
        put(obj + 0x9f4, 0x154200)
        put(0x154204, 0x154100)
        put(obj + 0x9e8, 0x154300)
        floats(0x154330, 0.25, 0.5, 0.75)
    floats(obj + 0x7ac, 12.5, -20.25, 31.125)
    cpu.mem_write(obj + 0x835, b'\x00\x01')
    cpu.mem_write(obj + 0x810, b'\x05')
    floats(obj + 0x814, 1, -1, 0, 0.5)
    put(obj + 0x724, 0x155000)
    put(0x155004, 0x180050)  # Defense export independently tested.
    put(obj + 0x7a8, 0x156000)
    put(0x156014, 2 if alternate else 1)
    put(0x15601c, 1 if alternate else 0)
    put(0x156008, 0x156100)
    put(0x156104, 0x156200)
    put(0x156200, 0x156300)
    put(0x156300, 0x156400)
    put(0x156424, 0x180060)  # Weapon definition ID
    if mode == 'soldier_occasional':
        put(obj + 0x994, 2 if alternate else 0)
        cpu.mem_write(obj + 0xd1c, bytes([alternate]))
    hits = []
    def hook(uc, address, size, unused):
        cleanup = 0
        sp = uc.reg_read(UC_X86_REG_ESP)
        if address == 0x121f1120:  # Physical rare prefix excluded.
            cleanup = 4
        elif address == 0x180000:
            pass
        elif address == 0x180010:
            uc.reg_write(UC_X86_REG_EAX, 0x153000)
        elif address == 0x180020:
            uc.reg_write(UC_X86_REG_EAX, 0x153600)
        elif address in (0x180030, 0x180040):
            floats(word(sp + 4), *((1, 2, 3) if address == 0x180030 else (0.1, -0.2, 0.3)))
            cleanup = 4
        elif address == 0x180050:
            cleanup = 4
        elif address == 0x180060:
            uc.reg_write(UC_X86_REG_EAX, 123456)
        else:
            return
        hits.append(hex(address))
        uc.reg_write(UC_X86_REG_EIP, word(sp))
        uc.reg_write(UC_X86_REG_ESP, sp + 4 + cleanup)
    cpu.hook_add(UC_HOOK_CODE, hook)
    put(0x170000, 0x190000)
    put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ECX, obj)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    try:
        cpu.emu_start({'rare': 0x12275e30, 'frequent': 0x12272040,
                       'occasional': 0x12277320, 'soldier_occasional': 0x12243fa0}[mode], 0x190000,
                      timeout=5_000_000, count=500000)
    except Exception as error:
        raise RuntimeError(f'{mode=} {alternate=} {turret=} pc={cpu.reg_read(UC_X86_REG_EIP):08x} {hits=}') from error
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = word(packet + 0x228)
    assert 0 < bits <= 548 * 8
    return {'mode': mode, 'alternate': alternate, 'turret': turret, 'bits': bits,
            'hex': bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex(),
            'excluded_owners_or_accessors': hits}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    cases = [(mode, alt, False) for mode in ('rare', 'occasional') for alt in (False, True)]
    cases += [('frequent', alt, turret) for turret in (False, True) for alt in (False, True)]
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'scope': __doc__, 'cases': [serialize(image, *case) for case in cases],
                      'soldier_occasional_cases': [serialize(image, 'soldier_occasional', alt)
                                                   for alt in (False, True)]}, indent=2))
