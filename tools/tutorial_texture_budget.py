#!/usr/bin/env python3
"""Tutorial texture residency/upload budget receipt (read-only diagnostics).

Enumerates the textures the tutorial's W3D closure references and models,
for each one, what the Vita DX8 boundary does with it
(port/renderer/vita/ww3d_dx8_boundary.cpp: Load_DDS_Texture,
Native_DXT_Level_Count, Load_Targa_Texture, Create_Texture_From_Surface) and
what vitaGL then allocates (glTexImage2D level>0 -> gpu_alloc_mipmaps).

The receipt carries names, dimensions, formats, counts and estimated byte
totals only. It never copies asset bytes, is never read by the game and is not
a runtime format. Static references are leads: runtime load order, script- or
definition-driven loads and the exact first-request mip count stay unverified.
"""
from __future__ import annotations

import argparse
from collections import Counter, OrderedDict
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

SCHEMA = 1

# Mount order of the Vita runtime's FileFactoryListClass
# (port/platform/vita/a31_vita_runtime.cpp, factory_list.Add_FileFactory):
# loose Data files, Always2.dat, Always.dbs, Always.dat, then the level MIX.
# FileFactoryListClass::Get_File returns the first factory that has the name.
DEFAULT_ARCHIVES = ('Always2.dat', 'always.dbs', 'always.dat')
DEFAULT_LEVEL = 'M00_Tutorial.mix'

# W3D chunk ids (staging/ww3d2/w3d_file.h).
MESH = 0x0000
PRELIT = {0x23: 'unlit', 0x24: 'vertex', 0x25: 'lightmap_multi_pass',
          0x26: 'lightmap_multi_texture'}
TEXTURE = 0x31
TEXTURE_NAME = 0x32
TEXTURE_INFO = 0x33
EMITTER_INFO = 0x503
AGGREGATE_INFO = 0x602
HLOD_SUB_OBJECT = 0x704
# Original owners open these as containers even if the exporter left the
# 0x80000000 "has sub-chunks" bit clear.
KNOWN_CONTAINERS = {0x0000, 0x0023, 0x0024, 0x0025, 0x0026, 0x0030, 0x0031,
                    0x0038, 0x0048, 0x0500, 0x0600, 0x0700, 0x0702, 0x0705,
                    0x0706}

# WW3D::PrelitMode default (staging/ww3d2/ww3d.cpp:210) and the fall-through
# order of MeshModelClass::Load_W3D (staging/ww3d2/meshmdlio.cpp:335-367).
PRELIT_FALLBACK = {
    'lightmap_multi_texture': ('lightmap_multi_texture', 'lightmap_multi_pass', 'vertex', 'unlit'),
    'lightmap_multi_pass': ('lightmap_multi_pass', 'vertex', 'unlit'),
    'vertex': ('vertex', 'unlit'),
}

# W3dTextureInfoStruct.Attributes -> TextureClass::MipCountType
# (staging/ww3d2/texture.cpp:1003-1035). 0 means MIP_LEVELS_ALL.
W3DTEXTURE_NO_LOD = 0x0004
W3DTEXTURE_MIP_LEVELS_MASK = 0x00c0
MIP_REQUEST = {0x0000: 0, 0x0040: 2, 0x0080: 3, 0x00c0: 4}

DXT_BLOCK_BYTES = {'DXT1': 8, 'DXT2': 16, 'DXT3': 16, 'DXT4': 16, 'DXT5': 16}
# Native_DXT_Level_Count / vglRenegadeUploadDXTChain accept only these.
NATIVE_FORMATS = ('DXT1', 'DXT5')
MAX_NATIVE_DIMENSION = 2048
MAX_NATIVE_LEVELS = 10
M00_PREWARM_SOFT_BUDGET = 32 * 1024 * 1024


class Provider:
    """One mounted source: loose files or a MIX1 archive index."""

    def __init__(self, label, path, entries):
        self.label = label
        self.path = path
        self.entries = entries  # lower name -> (offset, size, original name)

    def read(self, name, limit=None):
        offset, size, _ = self.entries[name.lower()]
        count = size if limit is None else min(size, limit)
        if self.path.is_dir():
            with (self.path / self.entries[name.lower()][2]).open('rb') as stream:
                return stream.read(count)
        with self.path.open('rb') as stream:
            stream.seek(offset)
            return stream.read(count)


def read_mix_index(path):
    """MIX1 index (same validation as tools/renegade_cinematic_dependency_scan)."""
    size = path.stat().st_size
    entries = {}
    with path.open('rb') as stream:
        magic, index_offset, names_offset = struct.unpack('<4sII', stream.read(12))
        if magic != b'MIX1':
            raise ValueError(f'{path.name}: unsupported MIX magic')
        if not (12 <= index_offset <= size - 4 and 12 <= names_offset <= size - 4):
            raise ValueError(f'{path.name}: invalid MIX offsets')
        stream.seek(index_offset)
        count = struct.unpack('<I', stream.read(4))[0]
        if count > 1000000 or index_offset + 4 + count * 12 > size:
            raise ValueError(f'{path.name}: invalid MIX index bounds')
        index = list(struct.iter_unpack('<III', stream.read(count * 12)))
        stream.seek(names_offset)
        if struct.unpack('<I', stream.read(4))[0] != count:
            raise ValueError(f'{path.name}: name count differs from index count')
        for crc, offset, length in index:
            name_length = stream.read(1)
            if not name_length:
                raise ValueError(f'{path.name}: truncated name table')
            raw = stream.read(name_length[0])
            if not raw.endswith(b'\0'):
                raise ValueError(f'{path.name}: invalid name table entry')
            name = raw[:-1].decode('ascii')
            if offset < 12 or offset + length > size:
                raise ValueError(f'{path.name}: invalid payload bounds')
            if crc != zlib.crc32(name.upper().encode('ascii')):
                raise ValueError(f'{path.name}: CRC/name mismatch')
            # Duplicate names inside one MIX: the first index record wins here;
            # MixFileFactoryClass uses a sorted CRC search, so flag instead.
            entries.setdefault(name.lower(), (offset, length, name))
    return entries


class Mount:
    def __init__(self, data_dir, archives, level):
        self.providers = []
        loose = {}
        for item in sorted(data_dir.iterdir()):
            if item.is_file():
                loose.setdefault(item.name.lower(), (0, item.stat().st_size, item.name))
        self.providers.append(Provider('Data/', data_dir, loose))
        self.missing_archives = []
        for name in tuple(archives) + (level,):
            path = self._find(data_dir, name)
            if path is None:
                self.missing_archives.append(name)
                continue
            self.providers.append(Provider(path.name, path, read_mix_index(path)))
        self.level = level

    @staticmethod
    def _find(data_dir, name):
        for item in data_dir.iterdir():
            if item.name.lower() == name.lower() and item.is_file():
                return item
        return None

    def resolve(self, name):
        key = name.lower()
        for provider in self.providers:
            if key in provider.entries:
                return provider
        return None

    def level_provider(self):
        for provider in self.providers:
            if provider.label.lower() == self.level.lower():
                return provider
        return None

    def receipt(self):
        rows = []
        for provider in self.providers:
            row = {'source': provider.label, 'entries': len(provider.entries)}
            if provider.path.is_file():
                row['bytes'] = provider.path.stat().st_size
                with provider.path.open('rb') as stream:
                    row['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
            rows.append(row)
        return rows


def iter_chunks(data, start=0, end=None, depth=0):
    """Yield (chunk_id, body_start, body_end, depth) bounded by the parent."""
    end = len(data) if end is None else end
    if depth > 64:
        raise ValueError('W3D nesting exceeds limit')
    pos = start
    while pos < end:
        if end - pos < 8:
            raise ValueError('truncated W3D chunk header')
        kind, size = struct.unpack_from('<II', data, pos)
        stop = pos + 8 + (size & 0x7fffffff)
        if stop > end:
            raise ValueError('W3D chunk exceeds parent')
        yield kind, pos + 8, stop, size & 0x80000000 != 0
        pos = stop


def c_string(raw):
    return raw.split(b'\0', 1)[0].decode('latin1').strip()


def mip_request(attributes):
    if attributes is None:
        return 0
    if attributes & W3DTEXTURE_NO_LOD:
        return 1
    return MIP_REQUEST[attributes & W3DTEXTURE_MIP_LEVELS_MASK]


def w3d_references(data, prelit_mode='lightmap_multi_pass'):
    """Texture and render-object references of one W3D file.

    Returns (textures, objects): textures as (name, mip_request, origin)
    tuples, objects as referenced render-object names. Only the prelit
    wrapper MeshModelClass would select for each mesh is followed.
    """
    textures, objects = [], []

    def texture_chunk(start, end, origin):
        name, attributes = None, None
        for kind, body, stop, _ in iter_chunks(data, start, end):
            if kind == TEXTURE_NAME:
                name = c_string(data[body:stop])
            elif kind == TEXTURE_INFO and stop - body >= 2:
                attributes = struct.unpack_from('<H', data, body)[0]
        if name:
            textures.append((name.lower(), mip_request(attributes), origin))

    def walk(start, end, depth, origin, selected_prelit):
        for kind, body, stop, nested in iter_chunks(data, start, end, depth):
            if kind == TEXTURE:
                texture_chunk(body, stop, origin)
                continue
            if kind == EMITTER_INFO and stop - body >= 260:
                name = c_string(data[body:body + 260])
                if name:
                    textures.append((name.lower(), 0, 'emitter'))
                continue
            if kind == HLOD_SUB_OBJECT and stop - body >= 36:
                name = c_string(data[body + 4:body + 36])
                if name:
                    objects.append(name.lower())
                continue
            if kind == AGGREGATE_INFO and stop - body >= 36:
                base = c_string(data[body:body + 32])
                if base:
                    objects.append(base.lower())
                count = struct.unpack_from('<I', data, body + 32)[0]
                cursor = body + 36
                for _ in range(min(count, 1024)):
                    if cursor + 64 > stop:
                        break
                    sub = c_string(data[cursor:cursor + 32])
                    if sub:
                        objects.append(sub.lower())
                    cursor += 64
                continue
            if kind in PRELIT:
                if PRELIT[kind] != selected_prelit:
                    continue
                walk(body, stop, depth + 1, 'prelit_' + PRELIT[kind], selected_prelit)
                continue
            if kind == MESH:
                present = [PRELIT[k] for k, _, _, _ in iter_chunks(data, body, stop, depth + 1)
                           if k in PRELIT]
                chosen = None
                for candidate in PRELIT_FALLBACK[prelit_mode]:
                    if candidate in present:
                        chosen = candidate
                        break
                walk(body, stop, depth + 1, 'mesh', chosen)
                continue
            if nested or kind in KNOWN_CONTAINERS:
                try:
                    walk(body, stop, depth + 1, origin, selected_prelit)
                except ValueError:
                    if nested:
                        raise
    walk(0, len(data), 0, 'model', None)
    return textures, objects


def level_dep_names(payload):
    """Filenames of the level .dep chunk (0x04020527 + microchunks)."""
    if len(payload) < 8:
        raise ValueError('truncated .dep header')
    kind, size = struct.unpack_from('<II', payload, 0)
    if kind != 0x04020527 or size != len(payload) - 8:
        raise ValueError('invalid Westwood asset dependency chunk')
    names, pos = [], 8
    while pos < len(payload):
        micro, length = struct.unpack_from('<BB', payload, pos)
        pos += 2
        if micro != 1 or pos + length > len(payload):
            raise ValueError('invalid .dep filename microchunk')
        names.append(c_string(payload[pos:pos + length]))
        pos += length
    return names


def parse_dds_header(header):
    if len(header) < 128 or header[:4] != b'DDS ':
        raise ValueError('short or invalid DDS header')
    if struct.unpack_from('<I', header, 4)[0] != 124:
        raise ValueError('invalid DDS descriptor size')
    height, width = struct.unpack_from('<II', header, 12)
    mip_map_count = struct.unpack_from('<I', header, 28)[0]
    pixel_flags = struct.unpack_from('<I', header, 80)[0]
    fourcc = header[84:88].decode('ascii', errors='replace')
    fmt = fourcc if (pixel_flags & 4) and fourcc in DXT_BLOCK_BYTES else (
        'fourcc:' + fourcc if pixel_flags & 4 else 'uncompressed')
    return {'width': width, 'height': height, 'mip_map_count': mip_map_count,
            'format': fmt}


def parse_tga_header(header):
    if len(header) < 18:
        raise ValueError('short TGA header')
    colormap_type, image_type = header[1], header[2]
    width, height = struct.unpack_from('<HH', header, 12)
    depth = header[16]
    source = {32: 'A8R8G8B8', 24: 'R8G8B8', 16: 'A1R5G5B5'}.get(depth)
    if depth == 8:
        source = 'P8' if colormap_type == 1 else ('L8' if image_type in (3, 11) else 'A8')
    return {'width': width, 'height': height, 'bits_per_pixel': depth,
            'format': source or f'unsupported_{depth}bpp', 'rle': image_type >= 9}


def align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def nearest_po2(value):
    result = 1
    while result < value:
        result <<= 1
    return result


def is_po2(value):
    return value > 0 and value & (value - 1) == 0


def ddsfile_mip_levels(mip_map_count):
    """DDSFileClass constructor, reduction factor 0 (ddsfile.cpp:76-85)."""
    levels = mip_map_count or 1
    return levels - 2 if levels > 2 else 1


def ddsfile_chain_bytes(width, height, fmt, levels):
    """Sum of DDSFileClass LevelSizes (ddsfile.cpp:92-110), as checked by
    DDS_Chain_Fits_Loaded_Data before any upload."""
    size = (width // 4) * (height // 4) * DXT_BLOCK_BYTES.get(fmt, 1)
    total = 0
    for _ in range(levels):
        total += size
        if size > 16:
            size //= 4
    return total


def vitagl_linear_bytes(width, height):
    """vitaGL gpu_alloc_texture: linear RGBA8888 rows aligned to 8 texels."""
    return align(width, 8) * height * 4


def vitagl_generated_chain_bytes(width, height):
    """vitaGL gpu_alloc_mipmaps size when the first level>0 call arrives."""
    w, h = nearest_po2(width), nearest_po2(height)
    total = 0
    while w > 1 and h > 1:
        total += max(w, 8) * h * 4
        w //= 2
        h //= 2
    return total + max(w, 8) * h * 4


def dxt_level_bytes(width, height, block_bytes):
    """Block-rounded DXT level size (vitaGL gpu_get_compressed_mip_size)."""
    return ((width + 3) // 4) * ((height + 3) // 4) * block_bytes


def model_dds(header, requested, source_bytes=None):
    """Port DDS upload path for one TextureClass request."""
    fmt = header['format']
    width, height = header['width'], header['height']
    result = {'source_kind': 'dds', 'format': fmt, 'width': width, 'height': height,
              'file_mip_count': header['mip_map_count']}
    available = ddsfile_mip_levels(header['mip_map_count'])
    if source_bytes is not None and (source_bytes < 128 or source_bytes - 128 <
                                     ddsfile_chain_bytes(width, height, fmt, available)):
        result.update(path='fallback_truncated_dds', gpu_bytes=16,
                      cpu_decode_texels=0, retained_cpu_bytes=0, upload_levels=0)
        return result
    if fmt not in DXT_BLOCK_BYTES:
        result.update(path='fallback_unsupported_dds_format', gpu_bytes=16,
                      cpu_decode_texels=0, retained_cpu_bytes=0, upload_levels=0)
        return result
    mip_count = available if requested == 0 else min(requested, available)
    block = DXT_BLOCK_BYTES[fmt]
    clamped = [(max(4, width >> level), max(4, height >> level)) for level in range(mip_count)]
    full_blocks = []  # levels that are at least one whole block in both axes
    for level in range(min(mip_count, MAX_NATIVE_LEVELS)):
        w, h = width >> level, height >> level
        if w < 4 or h < 4:
            break
        full_blocks.append((w, h))
    native_shape = (fmt in NATIVE_FORMATS and is_po2(width) and is_po2(height) and
                    width <= MAX_NATIVE_DIMENSION and height <= MAX_NATIVE_DIMENSION)
    compressed_chain = sum(dxt_level_bytes(w, h, block) for w, h in
                           ((max(1, width >> level), max(1, height >> level))
                            for level in range(mip_count)))
    result.update(requested_mips=requested, upload_levels=mip_count,
                  compressed_chain_bytes=compressed_chain)
    if native_shape and len(full_blocks) == mip_count:
        result.update(path='native_compressed', cpu_decode_texels=0, retained_cpu_bytes=0,
                      gpu_bytes=sum(w // 4 * (h // 4) * block for w, h in full_blocks))
        return result
    reasons = []
    if fmt not in NATIVE_FORMATS:
        reasons.append('format_' + fmt.lower())
    if not (is_po2(width) and is_po2(height)):
        reasons.append('npot')
    if width > MAX_NATIVE_DIMENSION or height > MAX_NATIVE_DIMENSION:
        reasons.append('over_2048')
    if mip_count > MAX_NATIVE_LEVELS:
        reasons.append('over_10_levels')
    if len(full_blocks) < min(mip_count, MAX_NATIVE_LEVELS):
        reasons.append('sub_block_tail_levels')
    texels = sum(w * h for w, h in clamped)
    # Decode path: level 0 -> gpu_alloc_texture; every level>0 glTexImage2D is
    # discarded by vitaGL and replaced by gpu_alloc_mipmaps downscales.
    gpu = (vitagl_generated_chain_bytes(width, height) if mip_count > 1
           else vitagl_linear_bytes(clamped[0][0], clamped[0][1]))
    result.update(path='cpu_decode_rgba8888', decode_reasons=reasons,
                  per_pixel_decode=fmt not in NATIVE_FORMATS,
                  cpu_decode_texels=texels, retained_cpu_bytes=texels * 4,
                  gpu_bytes=gpu, vitagl_generated_mip_levels=max(0, mip_count - 1),
                  authored_levels_discarded_by_gl=max(0, mip_count - 1),
                  full_block_levels=len(full_blocks))
    return result


def model_tga(header):
    width, height = header['width'], header['height']
    result = {'source_kind': 'tga', 'format': header['format'], 'width': width,
              'height': height, 'bits_per_pixel': header['bits_per_pixel'],
              'upload_levels': 1}
    if header['format'] in ('A8R8G8B8', 'R8G8B8', 'A1R5G5B5', 'L8', 'A8'):
        # Create_Texture_From_Surface: level 0 only, per-pixel RGBA8888 convert.
        result.update(path='cpu_convert_rgba8888_level0', cpu_decode_texels=width * height,
                      retained_cpu_bytes=0, gpu_bytes=vitagl_linear_bytes(width, height),
                      source_bytes_per_pixel=header['bits_per_pixel'] // 8)
        if header['format'] == 'A1R5G5B5':
            # RVTX1 bit 0: RGBA5551 fast_store, rows still padded to 8 texels.
            result['gpu_bytes_rvtx1_pack16'] = vitagl_linear_bytes(width, height) // 2
    else:
        result.update(path='fallback_unsupported_tga_format', cpu_decode_texels=0,
                      retained_cpu_bytes=0, gpu_bytes=16)
    return result


def swap_extension(name, extension):
    stem = name[:-3] if len(name) > 3 else name
    return stem + extension


def collect(mount, prelit_mode, seed_w3d=(), seed_textures=()):
    level = mount.level_provider()
    if level is None:
        raise ValueError(f'level archive {mount.level} not mounted')
    seeds = OrderedDict()
    for name in sorted(level.entries):
        if name.endswith('.w3d'):
            seeds.setdefault(name, 'level_mix_member')
    dep_name = Path(mount.level).stem.lower() + '.dep'
    dep_entries = []
    if dep_name in level.entries:
        dep_entries = level_dep_names(level.read(dep_name))
        for name in dep_entries:
            if name.lower().endswith('.w3d') and len(name) > 4:
                seeds.setdefault(name.lower(), 'level_dep')
    for name in seed_w3d:
        seeds.setdefault(name.lower(), 'cli_seed')

    textures = OrderedDict()  # asset-manager key -> reference record
    queue = list(seeds.items())
    visited, unresolved_models, parse_errors = {}, [], []
    while queue:
        name, why = queue.pop(0)
        if name in visited:
            continue
        provider = mount.resolve(name)
        visited[name] = provider.label if provider else None
        if provider is None:
            unresolved_models.append(name)
            continue
        try:
            refs, objects = w3d_references(provider.read(name), prelit_mode)
        except (ValueError, struct.error) as error:
            parse_errors.append({'model': name, 'error': str(error)})
            continue
        for texture, request, origin in refs:
            row = textures.setdefault(texture, {'requests': Counter(), 'origins': Counter(),
                                                'models': set()})
            row['requests'][request] += 1
            row['origins'][origin] += 1
            row['models'].add(name)
        stem = Path(name).stem
        for obj in objects:
            container = obj.split('.', 1)[0]
            if container and container != stem:
                queue.append((container + '.w3d', 'render_object_reference'))
    for name in seed_textures:
        row = textures.setdefault(name.lower(), {'requests': Counter(), 'origins': Counter(),
                                                 'models': set()})
        row['requests'][0] += 1
        row['origins']['cli_seed'] += 1
    return {'seeds': seeds, 'dep_entries': len(dep_entries), 'visited': visited,
            'unresolved_models': unresolved_models, 'parse_errors': parse_errors,
            'textures': textures}


def resolve_texture(mount, key, requests):
    """Mirror DX8Wrapper::_Create_DX8_Texture(filename, mips)."""
    # Asset-manager keys are distinct per spelling; the first request's mip
    # count wins. Statically use the largest request (0 = all) as the bound.
    requested = 0 if 0 in requests else max(requests)
    dds_name = swap_extension(key, 'dds')
    provider = mount.resolve(dds_name)
    if provider is not None:
        source_bytes = provider.entries[dds_name][1]
        row = model_dds(parse_dds_header(provider.read(dds_name, 128)), requested, source_bytes)
        row.update(source=provider.label, source_member=dds_name, source_bytes=source_bytes)
        return row
    if key.endswith('.tga'):
        provider = mount.resolve(key)
        if provider is not None:
            row = model_tga(parse_tga_header(provider.read(key, 18)))
            row.update(source=provider.label, source_member=key,
                       source_bytes=provider.entries[key][1])
            return row
    return {'source_kind': 'missing', 'path': 'fallback_missing', 'gpu_bytes': 0,
            'cpu_decode_texels': 0, 'retained_cpu_bytes': 0, 'upload_levels': 0}


def content_groups(mount, rows):
    """Distinct sources whose payloads are byte-identical (hash kept internal)."""
    by_digest = {}
    for row in rows:
        if row.get('source_member') is None:
            continue
        provider = next(p for p in mount.providers if p.label == row['source'])
        digest = hashlib.sha256(provider.read(row['source_member'])).hexdigest()
        by_digest.setdefault(digest, set()).add((row['source'], row['source_member']))
    groups = []
    for members in by_digest.values():
        if len(members) > 1:
            groups.append(sorted(f'{s}:{m}' for s, m in members))
    return sorted(groups)


def savings(rows, groups):
    """Ranked, estimated upload/residency savings (no measurement implied)."""
    def total(items, field):
        return sum(r.get(field, 0) for r in items)

    def tail(r):
        return 'sub_block_tail_levels' in r.get('decode_reasons', ())

    decoded = [r for r in rows if r['path'] == 'cpu_decode_rgba8888']
    dxt_tail = [r for r in decoded if r['format'] in NATIVE_FORMATS and tail(r)
                and len(r['decode_reasons']) == 1]
    dxt3 = [r for r in decoded if r['format'] == 'DXT3' and r['decode_reasons'] == ['format_dxt3']]
    dxt3_tail = [r for r in decoded if r['format'] == 'DXT3' and tail(r)
                 and set(r['decode_reasons']) == {'format_dxt3', 'sub_block_tail_levels'}]
    tga = [r for r in rows if r['path'] == 'cpu_convert_rgba8888_level0']
    tga16 = [r for r in tga if r.get('bits_per_pixel') == 16]
    other = [r for r in decoded if r not in dxt_tail and r not in dxt3 and r not in dxt3_tail]
    by_source = Counter((r.get('source'), r.get('source_member')) for r in rows
                        if r.get('source_member'))
    duplicate_keys = [r for r in rows if r.get('source_member') and
                      by_source[(r['source'], r['source_member'])] > 1]

    def compressed_gain(items, truncate):
        gpu = 0
        for r in items:
            if truncate:
                kept = r['full_block_levels']
                block = DXT_BLOCK_BYTES[r['format']]
                after = sum(dxt_level_bytes(max(1, r['width'] >> l), max(1, r['height'] >> l),
                                            block) for l in range(kept))
            else:
                after = r['compressed_chain_bytes']
            gpu += r['gpu_bytes'] - after
        return gpu

    candidates = [
        {'id': 'dxt_sub_block_tail_keep_compressed', 'textures': len(dxt_tail),
         'gpu_bytes_saved_estimate': compressed_gain(dxt_tail, False),
         'cpu_decode_texels_avoided': total(dxt_tail, 'cpu_decode_texels'),
         'retained_cpu_bytes_avoided': total(dxt_tail, 'retained_cpu_bytes'),
         'note': 'DXT1/DXT5 decoded to RGBA8888 only because the requested chain has '
                 'levels under 4 texels; upload the archive blocks with block-rounded tails'},
        {'id': 'dxt3_native_ubc2', 'textures': len(dxt3) + len(dxt3_tail),
         'gpu_bytes_saved_estimate': compressed_gain(dxt3 + dxt3_tail, False),
         'cpu_decode_texels_avoided': total(dxt3 + dxt3_tail, 'cpu_decode_texels'),
         'retained_cpu_bytes_avoided': total(dxt3 + dxt3_tail, 'retained_cpu_bytes'),
         'note': 'DXT3 is decoded per pixel (DDSFileClass::Get_Pixel) although GXM '
                 'samples UBC2 natively'},
        {'id': 'tga16_keep_16bit', 'textures': len(tga16),
         'gpu_bytes_saved_estimate': sum(r['gpu_bytes'] - r['gpu_bytes_rvtx1_pack16'] for r in tga16),
         'cpu_decode_texels_avoided': 0, 'retained_cpu_bytes_avoided': 0,
         'implemented_behind': 'RVTX1 bit 0 (tutorial-texture-v1.flag), default off',
         'note': 'A1R5G5B5 TGA expanded to RGBA8888; RGBA5551 keeps the same fields at '
                 '16 bits and replaces the per-texel expansion with a field move'},
        {'id': 'duplicate_name_variants', 'textures': len(duplicate_keys),
         'gpu_bytes_saved_estimate': sum(r['gpu_bytes'] for r in duplicate_keys) -
         sum(max(r['gpu_bytes'] for r in duplicate_keys if (r['source'], r['source_member']) == key)
             for key in {(r['source'], r['source_member']) for r in duplicate_keys}),
         'cpu_decode_texels_avoided': 0, 'retained_cpu_bytes_avoided': 0,
         'note': 'distinct TextureClass keys (e.g. .tga and .dds spellings) loading the same '
                 'archive member; original asset-manager ownership, report only'},
        {'id': 'other_decoded', 'textures': len(other),
         'gpu_bytes_saved_estimate': 0,
         'cpu_decode_texels_avoided': 0, 'retained_cpu_bytes_avoided': 0,
         'note': 'NPOT/oversize/non-native decode reasons; no safe compressed target'},
        {'id': 'byte_identical_sources', 'textures': sum(len(g) for g in groups),
         'gpu_bytes_saved_estimate': 0, 'cpu_decode_texels_avoided': 0,
         'retained_cpu_bytes_avoided': 0,
         'note': 'different archive members with identical bytes; data-level, report only'},
    ]
    candidates.sort(key=lambda c: (c['gpu_bytes_saved_estimate'] + c['retained_cpu_bytes_avoided'],
                                   c['cpu_decode_texels_avoided']), reverse=True)
    for rank, candidate in enumerate(candidates, 1):
        candidate['rank'] = rank
    return candidates


def build_receipt(data_dir, level=DEFAULT_LEVEL, archives=DEFAULT_ARCHIVES,
                  prelit_mode='lightmap_multi_pass', seed_w3d=(), seed_textures=()):
    mount = Mount(Path(data_dir), archives, level)
    closure = collect(mount, prelit_mode, seed_w3d, seed_textures)
    rows, errors = [], []
    for key, ref in closure['textures'].items():
        try:
            row = resolve_texture(mount, key, ref['requests'])
        except (ValueError, struct.error) as error:
            errors.append({'texture': key, 'error': str(error)})
            continue
        row['name'] = key
        row['requests'] = {('all' if k == 0 else str(k)): v for k, v in sorted(ref['requests'].items())}
        row['mixed_mip_requests'] = len(ref['requests']) > 1
        row['referenced_by_models'] = len(ref['models'])
        row['origins'] = dict(sorted(ref['origins'].items()))
        row['max_dimension_over_1024'] = max(row.get('width', 0), row.get('height', 0)) > 1024
        rows.append(row)
    rows.sort(key=lambda r: (-r.get('gpu_bytes', 0), r['name']))
    groups = content_groups(mount, rows)
    paths = Counter(r['path'] for r in rows)

    def sum_by(field, path=None):
        return sum(r.get(field, 0) for r in rows if path is None or r['path'] == path)

    totals = {
        'texture_keys': len(rows),
        'by_path': dict(sorted(paths.items())),
        'by_format': dict(sorted(Counter(r.get('format', 'missing') for r in rows).items())),
        'by_source': dict(sorted(Counter(r.get('source', 'missing') for r in rows).items())),
        'gpu_bytes_estimate': sum_by('gpu_bytes'),
        'gpu_bytes_estimate_rvtx1_pack16': sum(r.get('gpu_bytes_rvtx1_pack16', r.get('gpu_bytes', 0))
                                               for r in rows),
        'gpu_bytes_by_path': {p: sum_by('gpu_bytes', p) for p in sorted(paths)},
        # Warm_Original_M00_Referenced_Textures (a31_vita_runtime.cpp): 32 MiB
        # soft extra residency, 24 MiB vitaGL free-memory floor.
        'm00_prewarm_soft_budget_bytes': M00_PREWARM_SOFT_BUDGET,
        'fits_m00_prewarm_soft_budget': sum_by('gpu_bytes') < M00_PREWARM_SOFT_BUDGET,
        'cpu_decode_texels': sum_by('cpu_decode_texels'),
        'retained_cpu_bytes': sum_by('retained_cpu_bytes'),
        'decode_reasons': dict(sorted(Counter(reason for r in rows
                                              for reason in r.get('decode_reasons', ())).items())),
        'mixed_mip_request_keys': sum(1 for r in rows if r['mixed_mip_requests']),
        'over_1024_keys': sum(1 for r in rows if r['max_dimension_over_1024']),
        'byte_identical_source_groups': len(groups),
    }
    tool = Path(__file__).resolve()
    return {
        'schema': SCHEMA,
        'tool': {'name': tool.name, 'sha256': hashlib.sha256(tool.read_bytes()).hexdigest()},
        'evidence_class': 'retail_header_metadata_static_model',
        'runtime_verified': False,
        'level': level,
        'prelit_mode': prelit_mode,
        'mount_order': mount.receipt(),
        'missing_archives': mount.missing_archives,
        'closure': {
            'seed_models': len(closure['seeds']),
            'seed_sources': dict(Counter(closure['seeds'].values())),
            'level_dep_entries': closure['dep_entries'],
            'models_visited': len(closure['visited']),
            'models_resolved': sum(1 for v in closure['visited'].values() if v),
            'models_unresolved': len(closure['unresolved_models']),
            'unresolved_model_names': sorted(closure['unresolved_models']),
            'model_parse_errors': closure['parse_errors'],
        },
        'totals': totals,
        'savings_ranked': savings(rows, groups),
        'byte_identical_source_groups': groups,
        'texture_errors': errors,
        'textures': rows,
        'model': {
            'boundary': 'port/renderer/vita/ww3d_dx8_boundary.cpp Load_DDS_Texture/Load_Targa_Texture',
            'dds_levels': 'DDSFileClass drops the two smallest file levels (ddsfile.cpp:83-85)',
            'native_compressed': 'DXT1/DXT5, power-of-two, <=2048, every requested level >=4x4',
            'cpu_decode_gpu_bytes': 'vitaGL level 0 linear RGBA8888 plus gpu_alloc_mipmaps chain',
            'tga': 'level 0 only, RGBA8888, no mip chain (Create_Texture_From_Surface)',
            'missing': 'shared 2x2 checkerboard fallback',
        },
        'limits': [
            'Static W3D/.dep closure; definition-, script-, HUD- and INI-driven loads need --seed-*.',
            'First-request mip count is load-order dependent; the largest request is modelled.',
            'vitaGL allocator alignment beyond 8-texel rows and pool placement are not modelled.',
            'No asset bytes are emitted; byte-identical groups list names only.',
        ],
    }


def summary_lines(receipt, top=15):
    t = receipt['totals']
    lines = [f"texture keys: {t['texture_keys']}  paths: {t['by_path']}",
             f"formats: {t['by_format']}",
             f"gpu bytes (est): {t['gpu_bytes_estimate']}  with RVTX1 pack16: "
             f"{t['gpu_bytes_estimate_rvtx1_pack16']}  by path: {t['gpu_bytes_by_path']}",
             f"cpu decode texels: {t['cpu_decode_texels']}  retained cpu bytes: {t['retained_cpu_bytes']}",
             f"decode reasons: {t['decode_reasons']}",
             'ranked savings:']
    for c in receipt['savings_ranked']:
        lines.append(f"  {c['rank']}. {c['id']}: textures={c['textures']} gpu_saved={c['gpu_bytes_saved_estimate']} "
                     f"texels_avoided={c['cpu_decode_texels_avoided']} cpu_bytes_avoided={c['retained_cpu_bytes_avoided']}")
    lines.append(f'top {top} by estimated GPU bytes:')
    for r in receipt['textures'][:top]:
        lines.append(f"  {r['name']}: {r.get('format')} {r.get('width')}x{r.get('height')} "
                     f"levels={r.get('upload_levels')} path={r['path']} gpu={r.get('gpu_bytes')}")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--data', type=Path, required=True, help='retail Data directory (read only)')
    parser.add_argument('--level', default=DEFAULT_LEVEL)
    parser.add_argument('--prelit-mode', default='lightmap_multi_pass', choices=sorted(PRELIT_FALLBACK))
    parser.add_argument('--seed-w3d', action='append', default=[])
    parser.add_argument('--seed-texture', action='append', default=[])
    parser.add_argument('--output', type=Path, help='JSON receipt path (keep under build/)')
    parser.add_argument('--top', type=int, default=15)
    args = parser.parse_args(argv)
    receipt = build_receipt(args.data, args.level, DEFAULT_ARCHIVES, args.prelit_mode,
                            args.seed_w3d, args.seed_texture)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=1, sort_keys=False) + '\n')
    print('\n'.join(summary_lines(receipt, args.top)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
