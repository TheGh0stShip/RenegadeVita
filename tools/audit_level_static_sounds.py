"""Read-only audit of level-data audio (static sounds and background music).

Parses the original WWAudio static-sound chunks (StaticAudioSaveLoadClass,
chunk 0x30005) out of a mission ``.lsd`` and the dynamic-audio variables
(chunk 0x30006, background music name) out of the ``.ldd``, resolves every
referenced file through the same archive mount order the Vita runtime uses
(Always2.dat, always.dbs, always.dat, then the mission MIX) and checks each
resolved file against the current Vita provider admission rules:

* container: RIFF/WAVE PCM(1), MS ADPCM(2), IMA ADPCM(17), or MPEG audio;
* channels 1..2, sample rate 8000..192000 (WAVE) or <=48000 (MPEG);
* original WWAudioClass::Create_Sound_Buffer preload threshold
  (``DEF_MAX_3D_BUFFER_SIZE`` doubled in ``WWAudioClass::Initialize``): a 3D
  file larger than that becomes a StreamSoundBufferClass, which has no raw
  buffer and cannot be handed to ``AIL_set_3D_sample_file_bounded``.

No audio is decoded, exported or modified; retail bytes are never written.
This is metadata evidence only, not a playback or audibility claim.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audit_mission_wave_headers import inspect_wave
from tools.renegade_cinematic_dependency_scan import MixArchive

# soundchunkids.h (CHUNKID_WWAUDIO_BEGIN = 0x30000)
CHUNKID_AUDIBLE_SOUND = 0x30001
CHUNKID_FILTERED_SOUND = 0x30002
CHUNKID_SOUND3D = 0x30003
CHUNKID_PSEUDO_SOUND3D = 0x30004
CHUNKID_STATIC_SAVELOAD = 0x30005
CHUNKID_DYNAMIC_SAVELOAD = 0x30006
# audiosaveload.cpp
CHUNKID_STATIC_SCENE = 0x10291220
CHUNKID_DYNAMIC_SCENE = 0x10291221
CHUNKID_DYNAMIC_VARIABLES = 0x10291222
# soundscene.cpp
CHUNKID_SCENE_VARIABLES = 0x100
CHUNKID_STATIC_SOUNDS = 0x101
# audiblesound.cpp (AUDIBLE_SOUND_SAVELOAD) and Sound3D (VARID_*)
CHUNKID_AUDIBLE_VARIABLES = 0x100
CHUNKID_SOUND3D_VARIABLES = 0x11090955

AUDIBLE_VARIDS = {1: 'state', 2: 'type', 3: 'priority', 4: 'volume', 5: 'pan', 6: 'loop_count',
                  7: 'loops_left', 8: 'length_ms', 9: 'current_position', 10: 'transform',
                  11: 'prev_transform', 12: 'is_culled', 13: 'is_dirty', 14: 'drop_off',
                  15: 'filename', 16: 'this_ptr', 17: 'start_offset', 18: 'listener_transform',
                  19: 'pitch_factor', 22: 'virtual_channel'}
SOUND3D_VARIDS = {1: 'auto_calc_vel', 2: 'curr_vel', 5: 'max_vol_radius', 6: 'is_static'}
# AudibleSoundClass::SOUND_TYPE
SOUND_TYPES = {0: 'music', 1: 'effect', 2: 'dialog', 3: 'cinematic'}
CLASS_NAMES = {CHUNKID_AUDIBLE_SOUND: 'AudibleSoundClass', CHUNKID_FILTERED_SOUND: 'FilteredSoundClass',
               CHUNKID_SOUND3D: 'Sound3DClass', CHUNKID_PSEUDO_SOUND3D: 'SoundPseudo3DClass'}

# WWAudio.h DEF_MAX_3D_BUFFER_SIZE / DEF_MAX_2D_BUFFER_SIZE, with the doubling in
# WWAudioClass::Initialize (m_Max3DBufferSize = m_Max3DBufferSize * 2.0F).
MAX_3D_PRELOAD_BYTES = 100000 * 2
MAX_2D_PRELOAD_BYTES = 20000
# Provider constants (renegade_miles_provider.cpp / renegade_wave_decoder.cpp).
PROVIDER_MAX_WAVE_BYTES = 64 * 1024 * 1024
PROVIDER_MAX_DECODED_SAMPLES = 16 * 1024 * 1024
PROVIDER_MPEG_MAX_RATE = 48000

# Vita runtime mount order (a31_vita_runtime.cpp): loose Data, Always2.dat,
# Always.dbs, Always.dat, selected mission MIX. always3.dat is not mounted by the
# original Game_Init (it only adds Always2.dat, Always.dbs, Always.dat and *.mix).
ARCHIVE_ORDER = ('Always2.dat', 'always.dbs', 'always.dat')


def walk_chunks(data, start, end):
    """Yield (id, has_children, payload_start, payload_end) for sibling chunks."""
    offset = start
    while offset + 8 <= end:
        chunk_id, raw = struct.unpack_from('<II', data, offset)
        size = raw & 0x7FFFFFFF
        payload_end = offset + 8 + size
        if payload_end > end:
            return
        yield chunk_id, bool(raw & 0x80000000), offset + 8, payload_end
        offset = payload_end


def micro_chunks(data, start, end):
    offset = start
    while offset + 2 <= end:
        micro_id, size = data[offset], data[offset + 1]
        if offset + 2 + size > end:
            return
        yield micro_id, data[offset + 2:offset + 2 + size]
        offset += 2 + size


def c_string(raw):
    return raw.split(b'\0', 1)[0].decode('latin1')


def decode_micro(table, micro_id, raw, out):
    name = table.get(micro_id)
    if name is None:
        return
    if name == 'filename':
        out[name] = c_string(raw)
    elif name in ('volume', 'pan', 'priority', 'drop_off', 'max_vol_radius', 'start_offset',
                  'pitch_factor') and len(raw) == 4:
        out[name] = struct.unpack('<f', raw)[0]
    elif name in ('state', 'type', 'loop_count', 'loops_left', 'length_ms', 'virtual_channel',
                  'is_culled', 'is_dirty', 'current_position') and len(raw) == 4:
        out[name] = struct.unpack('<i', raw)[0]
    elif name == 'is_static' and len(raw) == 1:
        out[name] = raw[0]
    elif name == 'transform' and len(raw) == 48:
        matrix = struct.unpack('<12f', raw)  # Matrix3D row-major 3x4, translation in column 3
        out['position'] = (matrix[3], matrix[7], matrix[11])


def collect_sound(data, start, end, out):
    """Recursively decode one persisted sound object."""
    for chunk_id, has_children, p_start, p_end in walk_chunks(data, start, end):
        if has_children:
            collect_sound(data, p_start, p_end, out)
        elif chunk_id == CHUNKID_AUDIBLE_VARIABLES:
            for micro_id, raw in micro_chunks(data, p_start, p_end):
                decode_micro(AUDIBLE_VARIDS, micro_id, raw, out)
        elif chunk_id == CHUNKID_SOUND3D_VARIABLES:
            for micro_id, raw in micro_chunks(data, p_start, p_end):
                decode_micro(SOUND3D_VARIDS, micro_id, raw, out)


def static_sounds(lsd):
    """Return (records, structure_findings) for the static audio subsystem of an LSD."""
    records, findings = [], []
    seen_subsystem = False
    for top_id, _, top_start, top_end in walk_chunks(lsd, 0, len(lsd)):
        if top_id != CHUNKID_STATIC_SAVELOAD:
            continue
        seen_subsystem = True
        for scene_id, _, scene_start, scene_end in walk_chunks(lsd, top_start, top_end):
            if scene_id != CHUNKID_STATIC_SCENE:
                findings.append('unexpected_chunk_under_static_audio_0x%X' % scene_id)
                continue
            for sub_id, _, sub_start, sub_end in walk_chunks(lsd, scene_start, scene_end):
                if sub_id != CHUNKID_STATIC_SOUNDS:
                    continue
                for sound_id, _, s_start, s_end in walk_chunks(lsd, sub_start, sub_end):
                    record = {'chunk_id': '0x%05X' % sound_id,
                              'class': CLASS_NAMES.get(sound_id, 'unknown')}
                    if sound_id not in CLASS_NAMES:
                        findings.append('unregistered_static_sound_factory_0x%X' % sound_id)
                    collect_sound(lsd, s_start, s_end, record)
                    if 'filename' not in record:
                        record['no_filename'] = True
                    records.append(record)
    if not seen_subsystem:
        findings.append('static_audio_subsystem_chunk_absent')
    return records, findings


def find_chunks(data, start, end, wanted, depth=0, max_depth=3):
    """Yield (id, payload_start, payload_end) for chunks with an id in ``wanted``."""
    for chunk_id, has_children, p_start, p_end in walk_chunks(data, start, end):
        if chunk_id in wanted:
            yield chunk_id, p_start, p_end
        elif has_children and depth < max_depth:
            yield from find_chunks(data, p_start, p_end, wanted, depth + 1, max_depth)


def dynamic_audio(ldd):
    """Return the dynamic-audio variables (background music name, logical scale).

    The LDD wraps its subsystems in an outer level-data chunk (0x3C51C461), so the
    DynamicAudioSaveLoadClass chunk is searched for below the top level.
    """
    result = {'subsystem_present': False, 'background_music': None, 'logical_global_scale': None,
              'dynamic_scene_bytes': None}
    for _, top_start, top_end in find_chunks(ldd, 0, len(ldd), {CHUNKID_DYNAMIC_SAVELOAD}):
        result['subsystem_present'] = True
        for sub_id, _, s_start, s_end in walk_chunks(ldd, top_start, top_end):
            if sub_id == CHUNKID_DYNAMIC_VARIABLES:
                for micro_id, raw in micro_chunks(ldd, s_start, s_end):
                    if micro_id == 4 and len(raw) == 4:
                        result['logical_global_scale'] = struct.unpack('<f', raw)[0]
                    elif micro_id == 5:
                        result['background_music'] = c_string(raw)
            elif sub_id == CHUNKID_DYNAMIC_SCENE:
                result['dynamic_scene_bytes'] = s_end - s_start
    return result


def is_mpeg(data):
    if data[:3] == b'ID3':
        return True
    return len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0


MPEG_BITRATES = {
    (1, 1): (0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448),
    (1, 2): (0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384),
    (1, 3): (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320),
    (2, 1): (0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256),
    (2, 2): (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
    (2, 3): (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160),
}
MPEG_RATES = {1: (44100, 48000, 32000), 2: (22050, 24000, 16000), 25: (11025, 12000, 8000)}


def mpeg_header(data, offset):
    """Decode one MPEG audio frame header or return None."""
    if offset + 4 > len(data) or data[offset] != 0xFF or (data[offset + 1] & 0xE0) != 0xE0:
        return None
    version_bits = (data[offset + 1] >> 3) & 3
    layer = 4 - ((data[offset + 1] >> 1) & 3)
    bitrate_index = data[offset + 2] >> 4
    rate_index = (data[offset + 2] >> 2) & 3
    padding = (data[offset + 2] >> 1) & 1
    mode = data[offset + 3] >> 6
    if version_bits == 1 or layer == 4 or bitrate_index in (0, 15) or rate_index == 3:
        return None
    version = {3: 1, 2: 2, 0: 25}[version_bits]
    table = MPEG_BITRATES.get((1 if version == 1 else 2, layer))
    if table is None:
        return None
    bitrate = table[bitrate_index] * 1000
    rate = MPEG_RATES[version][rate_index]
    if layer == 1:
        size, samples = (12 * bitrate // rate + padding) * 4, 384
    elif layer == 3 and version != 1:
        size, samples = 72 * bitrate // rate + padding, 576
    else:
        size, samples = 144 * bitrate // rate + padding, 1152
    return {'version': version, 'layer': layer, 'bitrate': bitrate, 'sample_rate': rate,
            'channels': 1 if mode == 3 else 2, 'frame_bytes': size, 'frame_samples': samples}


def mpeg_summary(data):
    """Walk the MPEG frame chain (header-only; no decode)."""
    offset = 0
    id3_bytes = 0
    if data[:3] == b'ID3' and len(data) >= 10:
        id3_bytes = 10 + ((data[6] & 0x7F) << 21 | (data[7] & 0x7F) << 14 | (data[8] & 0x7F) << 7 | (data[9] & 0x7F))
        offset = id3_bytes
    first = None
    scan_limit = min(len(data), offset + 65536)
    while offset < scan_limit and first is None:
        first = mpeg_header(data, offset)
        if first is None:
            offset += 1
    if first is None:
        return {'frames': 0}, ['mpeg_no_valid_frame_header_found']
    findings = []
    frames = samples = resyncs = 0
    rates, bitrates = Counter(), Counter()
    while offset + 4 <= len(data):
        header = mpeg_header(data, offset)
        if header is None or header['sample_rate'] != first['sample_rate'] or \
                header['channels'] != first['channels']:
            if data[offset:offset + 3] == b'TAG':
                break
            resyncs += 1
            offset += 1
            continue
        frames += 1
        samples += header['frame_samples']
        bitrates[header['bitrate']] += 1
        offset += header['frame_bytes']
    summary = {'id3v2_bytes': id3_bytes, 'version': first['version'], 'layer': first['layer'],
               'sample_rate': first['sample_rate'], 'channels': first['channels'], 'frames': frames,
               'duration_seconds': round(samples / first['sample_rate'], 1),
               'distinct_bitrates': len(bitrates), 'resync_bytes': resyncs,
               'xing_or_vbri': any(tag in data[id3_bytes:id3_bytes + 512] for tag in (b'Xing', b'Info', b'VBRI'))}
    if first['layer'] != 3:
        findings.append('mpeg_not_layer3')
    if first['sample_rate'] > PROVIDER_MPEG_MAX_RATE:
        findings.append('mpeg_sample_rate_above_provider_limit')
    if resyncs > 4096:
        findings.append('mpeg_many_resync_bytes')
    return summary, findings


def basename(name):
    return name.replace('\\', '/').rsplit('/', 1)[-1]


def load_archives(data_root, mission):
    archives = []
    for name in (*ARCHIVE_ORDER, mission + '.mix'):
        path = data_root / name
        if path.exists():
            archives.append((name, MixArchive(path)))
    return archives


def resolve(name, archives, data_root):
    """Mimic MixFileFactory lookup: first mounted archive containing the basename wins."""
    key = basename(name).lower()
    hits = [archive_name for archive_name, archive in archives if key in archive.entries]
    for archive_name, archive in archives:
        if key in archive.entries:
            return archive_name, hits, archive.read_binary(key)
    loose = data_root / basename(name)
    if loose.is_file():
        return 'loose', ['loose'], loose.read_bytes()
    return None, [], None


def check_file(record, data):
    """Provider and preload-policy findings for one resolved file."""
    findings = []
    info = {'bytes': len(data)}
    is_3d = record['class'] in ('Sound3DClass', 'SoundPseudo3DClass')
    limit = MAX_3D_PRELOAD_BYTES if is_3d else MAX_2D_PRELOAD_BYTES
    info['streaming_buffer'] = len(data) > limit
    if is_3d and len(data) > limit:
        findings.append('3d_file_exceeds_preload_threshold_stream_buffer_has_no_raw_buffer')
    if len(data) > PROVIDER_MAX_WAVE_BYTES:
        findings.append('exceeds_provider_wave_byte_ceiling')
    if is_mpeg(data):
        info['container'] = 'mpeg'
        summary, mpeg_findings = mpeg_summary(data)
        info['mpeg'] = summary
        info.update(channels=summary.get('channels'), sample_rate=summary.get('sample_rate'))
        findings.extend(mpeg_findings)
        return info, findings
    wave = inspect_wave(data)
    fmt = wave.get('format') or {}
    info.update(container='riff_wave', tag=fmt.get('tag'), channels=fmt.get('channels'),
                sample_rate=fmt.get('sample_rate'), bits=fmt.get('bits_per_sample'),
                estimated_frames=wave.get('estimated_frames'))
    findings.extend(wave['header_findings'])
    for block in wave.get('block_findings', []):
        findings.append('block_' + block['kind'])
    if wave.get('estimated_samples_exceed_provider_ceiling'):
        findings.append('estimated_samples_exceed_provider_decode_ceiling')
    if fmt.get('channels') == 2 and is_3d:
        findings.append('stereo_3d_source_provider_mixes_channels_review')
    return info, findings


def audit_mission(data_root, mission):
    archive_path = data_root / (mission + '.mix')
    mission_archive = MixArchive(archive_path)
    lsd_name = next(n for n in mission_archive.entries if n.endswith('.lsd'))
    ldd_name = next(n for n in mission_archive.entries if n.endswith('.ldd'))
    sounds, structure = static_sounds(mission_archive.read_binary(lsd_name))
    dynamic = dynamic_audio(mission_archive.read_binary(ldd_name))
    archives = load_archives(data_root, mission)
    always3 = data_root / 'always3.dat'
    always3_archive = MixArchive(always3) if always3.exists() else None

    rows, class_counts, finding_counts = [], Counter(), Counter()
    unique = {}
    for record in sounds:
        class_counts[record['class']] += 1
        name = record.get('filename')
        if not name:
            finding_counts['record_without_filename'] += 1
            continue
        key = basename(name).lower()
        if key in unique:
            unique[key]['instances'] += 1
            continue
        mounted_in, hits, data = resolve(name, archives, data_root)
        row = {'file': basename(name), 'saved_name': name, 'class': record['class'], 'instances': 1,
               'type': SOUND_TYPES.get(record.get('type'), record.get('type')),
               'drop_off': record.get('drop_off'), 'volume': record.get('volume'),
               'loop_count': record.get('loop_count'), 'resolved_in': mounted_in, 'also_in': hits[1:]}
        findings = []
        if name != basename(name):
            findings.append('saved_name_contains_path_component')
        if data is None:
            in_always3 = always3_archive is not None and key in always3_archive.entries
            findings.append('present_only_in_unmounted_always3_dat' if in_always3
                            else 'not_found_in_mounted_archives')
        else:
            info, more = check_file(record, data)
            row.update(info)
            findings.extend(more)
        row['findings'] = findings
        unique[key] = row
        rows.append(row)
    for row in rows:
        for finding in row['findings']:
            finding_counts[finding] += 1

    music = None
    if dynamic['background_music']:
        mounted_in, hits, data = resolve(dynamic['background_music'], archives, data_root)
        music = {'file': dynamic['background_music'], 'resolved_in': mounted_in}
        if data is not None:
            record = {'class': 'AudibleSoundClass'}
            info, findings = check_file(record, data)
            music.update(info)
            music['findings'] = findings
        else:
            music['findings'] = ['not_found_in_mounted_archives']
    return {'mission': mission, 'lsd': lsd_name, 'ldd': ldd_name, 'static_sound_instances': len(sounds),
            'unique_files': len(rows), 'class_counts': dict(class_counts), 'structure_findings': structure,
            'finding_counts': dict(sorted(finding_counts.items())), 'dynamic_audio': dynamic,
            'background_music': music, 'files': sorted(rows, key=lambda r: r['file'].lower())}


def read_header(archive, key, count=128):
    """Return (size, first bytes) of an archive member without reading the payload."""
    _, offset, size = archive.entries[key]
    with archive.path.open('rb') as stream:
        stream.seek(offset)
        return size, stream.read(min(count, size))


def wave_format_from_header(head):
    """Parse the fmt chunk from the first bytes of a RIFF/WAVE member, or None."""
    if head[:4] != b'RIFF' or head[8:12] != b'WAVE':
        return None
    offset = 12
    while offset + 8 <= len(head):
        kind, size = struct.unpack_from('<4sI', head, offset)
        if kind == b'fmt ' and offset + 8 + 16 <= len(head):
            tag, channels, rate, _, _, bits = struct.unpack_from('<HHIIHH', head, offset + 8)
            return {'tag': tag, 'channels': channels, 'sample_rate': rate, 'bits': bits}
        offset += 8 + size + (size & 1)
    return None


def sound_definitions(data_root):
    """Header-level scan of every AudibleSoundDefinitionClass in always.dbs/objects.ddb.

    Definition chunk 0x30000 holds the file name (VARID_FILENAME=11), IS3D (10) and
    the DefinitionClass name (base-class chunk 0x200 > 0x100 micro 3). Only member
    sizes and the first 128 bytes of each file are read.
    """
    dbs = MixArchive(data_root / 'always.dbs')
    archives = [(name, MixArchive(data_root / name)) for name in ('Always2.dat', 'always.dat')]
    ddb = dbs.read_binary('objects.ddb')
    rows = []
    for _, p_start, p_end in find_chunks(ddb, 0, len(ddb), {0x30000}, max_depth=3):
        inner = [c for c in walk_chunks(ddb, p_start, p_end) if c[0] == 0x100101]
        if not inner:
            continue
        row = {}
        for chunk_id, _, c_start, c_end in walk_chunks(ddb, inner[0][2], inner[0][3]):
            if chunk_id == 0x100:
                for micro_id, raw in micro_chunks(ddb, c_start, c_end):
                    if micro_id == 11:
                        row['file'] = c_string(raw)
                    elif micro_id == 10 and raw:
                        row['is_3d'] = bool(raw[0])
            elif chunk_id == 0x200:
                for _, _, b_start, b_end in walk_chunks(ddb, c_start, c_end):
                    for micro_id, raw in micro_chunks(ddb, b_start, b_end):
                        if micro_id == 3:
                            row['name'] = c_string(raw)
        rows.append(row)
    summary = {'definitions': len(rows), 'with_file': 0, 'folder_or_empty': 0, 'missing_file': [],
               'oversize_3d': [], 'formats': Counter(), 'mpeg': 0}
    for row in rows:
        name = row.get('file', '')
        if not name or not name.lower().endswith(('.wav', '.mp3')):
            summary['folder_or_empty'] += 1
            continue
        summary['with_file'] += 1
        key = basename(name).lower()
        member = next(((n, a) for n, a in archives if key in a.entries), None)
        if member is None:
            summary['missing_file'].append({'definition': row.get('name'), 'file': name})
            continue
        size, head = read_header(member[1], key)
        if is_mpeg(head):
            summary['mpeg'] += 1
        else:
            fmt = wave_format_from_header(head) or {}
            summary['formats'][(fmt.get('tag'), fmt.get('channels'), fmt.get('sample_rate'))] += 1
        if row.get('is_3d') and size > MAX_3D_PRELOAD_BYTES:
            summary['oversize_3d'].append({'definition': row.get('name', '').strip(), 'file': basename(name),
                                           'bytes': size, 'archive': member[0]})
    summary['formats'] = {'tag=%s,ch=%s,rate=%s' % k: v for k, v in sorted(
        summary['formats'].items(), key=lambda kv: -kv[1])}
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True, help='retail Data directory (read-only)')
    parser.add_argument('--missions', nargs='+', default=['M04', 'M09', 'M10', 'M11'])
    parser.add_argument('--output', type=Path, help='optional JSON receipt path')
    parser.add_argument('--definitions', action='store_true',
                        help='also scan AudibleSoundDefinitionClass entries in always.dbs')
    args = parser.parse_args(argv)
    result = {'schema': 'renegade-vita-level-static-sounds-1', 'evidence_class': 'host_retail_metadata',
              'missions': [audit_mission(args.data, mission) for mission in args.missions]}
    if args.definitions:
        result['sound_definitions'] = sound_definitions(args.data)
    text = json.dumps(result, indent=1, sort_keys=True)
    if args.output:
        args.output.write_text(text + '\n')
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
