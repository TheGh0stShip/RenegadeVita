#!/usr/bin/env python3
"""Inspect a bounded options-only capture using original retail C&C field order.

Diagnostic only, never supplies game state or chooses a map for a live client.
Public text fields are consumed but omitted from the report. Nonzero remaining
bits and invalid counts are evidence to investigate, not proof of TT support.
"""
import argparse
import json
from pathlib import Path
import struct
import zlib


def inspect(record, modern=False):
    if record.get('schema') != 1 or record.get('event') != 'cGameOptionsEvent::Import_Creation':
        raise ValueError('Not an options-only capture')
    raw = bytes.fromhex(record['payload_hex'])
    size = record['payload_bits']
    if not 0 < size <= len(raw) * 8 <= 548 * 8 or len(raw) != (size + 7) // 8:
        raise ValueError('Invalid bit range')
    bits = ''.join(format(byte, '08b') for byte in raw)[:size]
    cursor = 0

    def get(count):
        nonlocal cursor
        if cursor + count > size:
            raise ValueError('Truncated field at bit %d' % cursor)
        result = int(bits[cursor:cursor + count], 2)
        cursor += count
        return result

    def wide(limit):
        count = get(16)
        if count >= limit:
            raise ValueError('Oversized string at bit %d' % (cursor - 16))
        for _ in range(count):
            get(16)
        return count

    result = {'layout': 'original_retail_cnc_options', 'ip_word': get(32),
              'owner_characters': wide(256), 'title_characters': wide(256)}
    for name in ('port', 'players', 'max_players', 'exe_key', 'exe_crc', 'strings_crc'):
        result[name] = get(32)
    for name in ('dedicated', 'team_change', 'passworded', 'laddered', 'clan_game'):
        result[name] = bool(get(1))
    result['tier1_map_crc'], result['tier1_mod_crc'] = get(32), get(32)
    for name in ('time_limit_minutes', 'radar_mode', 'intermission_seconds', 'qualifying_minutes'):
        result[name] = get(32)
    for name in ('friendly_fire', 'free_weapons', 'trusted_client', 'remix_teams',
                 'repair_buildings', 'driver_gunner', 'spawn_weapons'):
        result[name] = bool(get(1))
    result['motd_characters'] = wide(2048)
    result['base_destruction_ends'], result['beacon_ends'] = bool(get(1)), bool(get(1))
    result['starting_credits'] = get(32)
    result['remaining_seconds'] = struct.unpack('>f', get(32).to_bytes(4, 'big'))[0]
    result['hosted_game'] = get(32)
    if modern:
        # b9000 options serialize a trailing flag instead of the legacy CRC pair.
        result['layout'] = 'tt_b9000_cnc_options'
        result['modern_tail_flag'] = bool(get(1))
    else:
        result['final_mod_crc'], result['final_map_crc'] = get(32), get(32)
    result['consumed_bits'], result['remaining_bits'] = cursor, size - cursor
    if not modern:
        result['map_crcs_agree'] = result['tier1_map_crc'] == result['final_map_crc']
        result['mod_crcs_agree'] = result['tier1_mod_crc'] == result['final_mod_crc']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('--modern', action='store_true', help='Inspect the verified b9000 options tail')
    parser.add_argument('--map', help='Compare a separately observed map name; never selects it')
    parser.add_argument('--replay-output', type=Path, help='Create a NEW private original-importer fixture')
    args = parser.parse_args()
    record = json.loads(args.capture.read_text())
    result = inspect(record, args.modern)
    if args.replay_output:
        import os
        import stat
        if stat.S_IMODE(args.replay_output.parent.stat().st_mode) != 0o700:
            parser.error('Replay output must be in a mode-0700 directory')
        with os.fdopen(os.open(args.replay_output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as output:
            output.write(struct.pack('<I', record['payload_bits']))
            output.write(bytes.fromhex(record['payload_hex']))
    if args.map:
        crc = zlib.crc32(args.map.upper().encode('ascii'))
        result['observed_map_crc_matches'] = crc == result['tier1_map_crc' if args.modern else 'final_map_crc']
    print(json.dumps(result, indent=2, allow_nan=False))
