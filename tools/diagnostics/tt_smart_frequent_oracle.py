#!/usr/bin/env python3
"""Execute pinned Smart/Armed/Control serializers on synthetic state only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def serialize(image, modern, alternate):
    pe = pefile.PE(data=image)
    cpu = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    cpu.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    cpu.mem_write(base, pe.get_memory_mapped_image())
    cpu.mem_map(0x100000, 0x100000)
    def put(address, value):
        cpu.mem_write(address, struct.pack('<I', value))
    obj, packet, encoders = 0x110008, 0x160000, 0x140000
    put(0x1231ded4, 0x4099999a if modern else 0)
    put(0x1231ded0, 9000 if modern else 0)
    put(0x125fa534, 0x150410)
    cpu.mem_write(0x150410, b'\x01')
    put(0x125fa538, encoders)
    # Original encoder expands precision to the complete representable range.
    for index, values in {0: (-1000., 1000., 2000. / 262143, 18),
                          1: (-1000., 1000., 2000. / 262143, 18),
                          2: (-1000., 1000., 2000. / 262143, 18),
                          4: (0., 15., 1., 4),
                          5: (-1., 1., 2. / 255, 8)}.items():
        cpu.mem_write(encoders + index * 32, struct.pack('<dddII', *values, 1))
    cpu.mem_write(obj + 0x7ac, struct.pack('<fff', 12.5, -20.25, 31.125))
    cpu.mem_write(obj + 0x835, bytes([alternate, not alternate]))
    cpu.mem_write(obj + 0x808 + 8, b'\x05')
    cpu.mem_write(obj + 0x808 + 12, struct.pack('<ffff', 1., -1., 0., .5))
    put(0x170000, 0x190000)
    put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ECX, obj)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    cpu.emu_start(0x122405b0, 0x190000, timeout=5_000_000, count=500000)
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = struct.unpack('<I', cpu.mem_read(packet + 0x228, 4))[0]
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
                      'scope': 'complete Smart/Armed/Control frequent export, synthetic state and encoder ranges',
                      'cases': [serialize(image, modern, alternate)
                                for modern, alternate in ((False, False), (True, False), (True, True))]}, indent=2))
