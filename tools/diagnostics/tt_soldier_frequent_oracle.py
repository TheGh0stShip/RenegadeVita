#!/usr/bin/env python3
"""Execute retail b9000 Soldier frequent export with synthetic accessor seams."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_ECX, UC_X86_REG_EIP, UC_X86_REG_ESP
from tt_identity_oracle import PIN


def serialize(image, state, weapon=False, damage=False, client_state=False, control_mode=None):
    pe = pefile.PE(data=image)
    cpu = Uc(UC_ARCH_X86, UC_MODE_32)
    base = pe.OPTIONAL_HEADER.ImageBase
    cpu.mem_map(base, (pe.OPTIONAL_HEADER.SizeOfImage + 4095) & ~4095)
    cpu.mem_write(base, pe.get_memory_mapped_image())
    cpu.mem_map(0x100000, 0x100000)
    # Implement the imported x87 atan2 primitive, not a packet-writing hook.
    cpu.mem_write(0x180040, b'\xd9\xf3\xc3')  # fpatan; ret
    atan_imports = [symbol for entry in pe.DIRECTORY_ENTRY_IMPORT for symbol in entry.imports
                    if symbol.name == b'_CIatan2']
    assert len(atan_imports) == 1
    cpu.mem_write(atan_imports[0].address, struct.pack('<I', 0x180040))
    def put(address, value):
        cpu.mem_write(address, struct.pack('<I', value & 0xffffffff))
    def get(address):
        return struct.unpack('<I', cpu.mem_read(address, 4))[0]
    obj, packet, encoders = 0x110008, 0x160000, 0x140000
    put(0x1231ded4, 0x4099999a)
    put(0x1231ded0, 9000)
    put(0x125fa534, 0x150410)
    cpu.mem_write(0x150410, b'\x01')
    put(0x125fa538, encoders)
    for index, values in {3: (0., 8388607., 1., 23),
                          4: (0., 15., 1., 4), 5: (-1., 1., 2. / 255, 8),
                          10: (0., 19., 19. / 31, 5),
                          11: (0., 511., 1., 9)}.items():
        cpu.mem_write(encoders + index * 32, struct.pack('<dddII', *values, 1))
    put(obj - 8, 0x151000)
    put(0x151038, 0x180000)  # Get_Position
    put(0x1510d4, 0x180010)  # Get_Velocity
    put(obj + 0x7a8, 0x152000)
    put(0x152008, 0x152100)
    if weapon:
        put(0x152100, 0x152200)
        put(0x152200, 0x152300)
        put(0x152300, 0x152400)
        put(0x152424, 0x180020)  # Definition Get_ID
    put(obj + 0x76c, 0x153000)
    put(0x153000, 0x153100)
    put(0x153118, 0x180030)  # Physics Get_Transform for ladder heading
    cpu.mem_write(0x153200, struct.pack('<12f', 0, -1, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0))
    put(obj + 0x98c, state)
    put(obj - 8 + 0x99c, 2 if state == 1 else 0)
    put(obj + 0x998, 1)
    put(obj + 0x980, 0x154000)
    cpu.mem_write(0x154000, b'S_A_HUMAN.H_A_422A\0')
    put(obj + 0xcc8, 1 if damage else 0)
    cpu.mem_write(obj + 0xd60, b'\x01')
    cpu.mem_write(obj + 0x7ac, struct.pack('<fff', 12.5, -20.25, 31.125))
    cpu.mem_write(obj + 0x835, b'\x00\x01')
    cpu.mem_write(obj + 0x810, b'\x05')
    cpu.mem_write(obj + 0x814, struct.pack('<ffff', 1., -1., 0., .5))
    if control_mode:
        # Original CClientControl walks the real-shaped Smart object list and
        # invokes the retail control/state serializers, without packet hooks.
        client = 0x158000
        put(client + 0x6b4, -1)
        put(client + 0x6b8, -1 if control_mode == 'idle' else 1234)
        put(0x123207dc, 0x159000)
        put(0x159004, 0 if control_mode == 'missing' else 0x159100)
        put(0x159104, obj - 8)
        put(obj - 8 + 0x0c, 1234)
        cpu.mem_write(obj - 8 + 0x4a4, bytes([control_mode == 'delete_pending']))
        put(0x1510ac, 0x12120310 if control_mode == 'armed' else 0x12245160)
        put(obj - 8 + 0x814, (1 << 22) | (1 << 9) | 1)
        cpu.mem_write(obj - 8 + 0x819, b'\x05')
        cpu.mem_write(obj - 8 + 0x81c, struct.pack('<ffff', 1., -1., 0., .5))
    hits = []
    def hook(uc, address, size, data):
        sp = uc.reg_read(UC_X86_REG_ESP)
        cleanup = 0
        if address in (0x180000, 0x180010):
            values = (100.125, 200.25, 30.5) if address == 0x180000 else (1., 2., 3.)
            uc.mem_write(get(sp + 4), struct.pack('<fff', *values))
            cleanup = 4
        elif address == 0x180020:
            uc.reg_write(UC_X86_REG_EAX, 123456)
        elif address == 0x180030:
            uc.reg_write(UC_X86_REG_EAX, 0x153200)
        else:
            return
        hits.append(hex(address))
        uc.reg_write(UC_X86_REG_EIP, get(sp))
        uc.reg_write(UC_X86_REG_ESP, sp + 4 + cleanup)
    cpu.hook_add(UC_HOOK_CODE, hook, begin=0x180000, end=0x180030)
    put(0x170000, 0x190000)
    put(0x170004, packet)
    cpu.reg_write(UC_X86_REG_ECX, client if control_mode else obj - 8 if client_state else obj)
    cpu.reg_write(UC_X86_REG_ESP, 0x170000)
    try:
        entry = (0x12138550 if control_mode == 'creation' else 0x12138c10) if control_mode else (
            0x12245160 if client_state else 0x12244120)
        cpu.emu_start(entry, 0x190000,
                      timeout=5_000_000, count=500000)
    except Exception as error:
        raise RuntimeError(f'state={state} weapon={weapon} pc={cpu.reg_read(UC_X86_REG_EIP):08x} accessor_hits={hits}') from error
    assert cpu.reg_read(UC_X86_REG_EIP) == 0x190000
    bits = get(packet + 0x228)
    assert 0 < bits <= 548 * 8
    result = {'state': state, 'weapon': weapon, 'damage': damage, 'client_state': client_state, 'bits': bits,
            'hex': bytes(cpu.mem_read(packet + 4, (bits + 7) // 8)).hex(),
            'accessor_hooks': hits}
    if control_mode:
        result.update(mode=control_mode, pending_one_time=get(obj - 8 + 0x814),
                      pending_continuous=cpu.mem_read(obj - 8 + 0x819, 1)[0],
                      next_object_id=get(client + 0x6b8))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    cases = [(state, False, False) for state in (0, 2, 5, 6, 8, 9, 10)]
    cases += [(0, True, False), (0, False, True)]
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'scope': 'modern Soldier/Smart/Armed/Control export; synthetic position, velocity, transform and weapon ID accessors',
                      'cases': [serialize(image, *case) for case in cases],
                      'client_state_cases': [serialize(image, state, client_state=True)
                                             for state in (0, 1)]}, indent=2))
