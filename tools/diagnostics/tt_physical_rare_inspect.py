#!/usr/bin/env python3
"""Inspect bounded incoming physical rare captures without exposing payload text.

The physical portion is confirmed by pinned b9000 export/import functions.
Remaining bits belong to subclasses and/or later dirty-state groups; never
interpret successful physical decoding as complete object compatibility.
"""
import argparse
import json
import struct
from pathlib import Path


def inspect(record, creation=False, soldier=False):
    if record.get('schema') != 1 or record.get('event') != 'PhysicalGameObj::Import_Rare':
        raise ValueError('Not a physical rare capture')
    data = bytes.fromhex(record['packet_hex'])
    end, cursor = record['packet_bits'], record['entry_read_bits']
    if not 0 <= cursor <= end <= len(data) * 8 <= 548 * 8 or len(data) != (end + 7) // 8:
        raise ValueError('Invalid packet bounds')
    bits = ''.join(f'{byte:08b}' for byte in data)[:end]
    def get(count):
        nonlocal cursor
        if cursor + count > end:
            raise ValueError(f'Truncated field at {cursor}')
        value = int(bits[cursor:cursor + count], 2)
        cursor += count
        return value
    def text_length():
        count = get(16)
        if count >= 1024:
            raise ValueError('Oversized model/animation name')
        for _ in range(count):
            get(8)
        return count
    creation_fields = {}
    if creation:
        cursor = 0
        object_id, dirty, deleted, class_id, definition = get(32), get(8), get(1), get(32), get(32)
        if class_id != 1000 or deleted or dirty & 3 != 3:
            raise ValueError('Expected game-object creation plus rare state')
        position = [struct.unpack('>f', get(32).to_bytes(4, 'big'))[0] for _ in range(4)]
        owner, weapons = get(32), get(32)
        if weapons > (end - cursor) // 64:
            raise ValueError('Invalid initial weapon count')
        for _ in range(weapons):
            get(32); get(16); get(16)
        creation_fields = {'object_id': object_id, 'definition_id': definition,
                           'position_and_heading': position, 'control_owner': owner,
                           'initial_weapon_count': weapons, 'tt_physical_start': cursor,
                           'original_decoder_start': record['entry_read_bits']}
    start = cursor
    result = {**creation_fields, 'radar_color': get(32), 'radar_shape': get(32),
              'team_visibility': get(8), 'collision_group': get(32),
              'clear_animation': bool(get(1)), 'model_characters': text_length(),
              'animation_characters': text_length()}
    for field in ('current_frame', 'target_frame', 'animation_mode', 'host_id', 'host_bone', 'team'):
        result[field] = get(32)
    result['hud_pokable'], result['hidden'] = bool(get(1)), bool(get(1))
    result['physical_bits'] = cursor - start
    if soldier:
        suffix = {'definition_id': get(32)}
        for field in ('can_steal_vehicles', 'can_drive_vehicles', 'block_action',
                      'freeze', 'damage_animations'):
            suffix[field] = bool(get(1))
        def number():
            return struct.unpack('>f', get(32).to_bytes(4, 'big'))[0]
        suffix['network_scale'] = number()
        suffix['movement_loiters'] = bool(get(1))
        suffix['max_speed'] = number()
        suffix['override_muzzle'] = bool(get(1))
        suffix['skeleton_height'], suffix['skeleton_width'] = number(), number()
        style = get(32)
        suffix['hold_style'] = style if style < 0x80000000 else style - 0x100000000
        suffix['human_animation_override'] = bool(get(1))
        suffix['bot_tag_characters'] = get(16)
        if suffix['bot_tag_characters'] >= 256:
            raise ValueError('Oversized bot tag')
        for _ in range(suffix['bot_tag_characters']):
            get(16)
        suffix['footsteps'] = bool(get(1))
        for field in ('target_height', 'target_width', 'height_speed', 'width_speed'):
            suffix[field] = number()
        result['soldier_suffix'] = suffix
    result['subclass_or_later_state_bits'] = end - cursor
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--smart-creation', action='store_true',
                        help='Decode the verified modern smart-object creation before rare fields')
    parser.add_argument('--soldier', action='store_true', help='Decode the b9000 soldier rare suffix')
    args = parser.parse_args()
    with args.capture.open() as stream:
        for index, line in enumerate(stream):
            if index >= 16:
                raise ValueError('Capture exceeds bounded record count')
            print(json.dumps(inspect(json.loads(line), args.smart_creation, args.soldier)))
