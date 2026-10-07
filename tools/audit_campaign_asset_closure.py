#!/usr/bin/env python3
"""Campaign-wide asset closure audit for M13 and M01-M11 (read-only, host only).

Every name is resolved the way the Vita runtime resolves files, not by "exists
somewhere in the retail tree":

* Vita FileFactoryList order (port/platform/vita/a31_vita_runtime.cpp):
  retail-root loose, ``Data`` loose, ``Always2.dat``, ``Always.dbs``,
  ``Always.dat``, ``M00_Tutorial.mix``, then the selected mission MIX
  (M09 only: ``Set_Search_Start`` puts the mission MIX first, savegame.cpp).
  ``always3.dat`` is not mounted.
* PC order (commando/init.cpp ``Game_Init``): loose, ``Always2.dat``,
  ``Always.dbs``, ``Always.dat`` and then every ``data\\*.mix`` in directory
  order. Names that only the PC order resolves are port-side mount gaps;
  names neither order resolves are retail-data defects the PC game shares.
* MixFileFactoryClass looks names up by ``CRC_Stringi(whole name)``: case does
  not matter, but any directory component or alias CRC changes the answer.
* Loose files go through ``Renegade_Resolve_Path`` (renegade_paths.cpp), which
  is emulated here: ``:``, absolute, ``.``/``..`` names are rejected, ``\\`` is
  ``/``, components match exactly or case-insensitively, and ``user/``,
  ``cache/``, ``save/``, ``mods/`` prefixes are diverted to writable roots.
* Textures follow TextureLoadTaskClass: the last three characters become
  ``dds`` (DDSFileClass) and the original name (TGA) is the fallback; a double
  miss becomes MissingTexture.

No retail payload, extracted content or hash of content is written; only
names, sizes, archive identities and counts. Reference sets are metadata
evidence, not proof of what a mission executes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.renegade_cinematic_dependency_scan import MixArchive, scan_all_text
from tools.audit_w3d_loader_coverage import chunk_paths

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ['M13', 'M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07', 'M08', 'M09', 'M10', 'M11']
SHARED_VITA = ['Always2.dat', 'always.dbs', 'always.dat', 'M00_Tutorial.mix']
SHARED_PC = ['Always2.dat', 'always.dbs', 'always.dat']
LOADER_NAMESPACES = ('user', 'cache', 'save', 'mods', 'retail')
SCRIPT_ONLY_TEXTURE_PREFIXES = ('!',)  # procedural names (metalmap.cpp "!m%02d.tga")

# W3D chunk ids (staging/ww3d2/w3d_file.h)
W3D_MESH, W3D_MESH_HEADER3 = 0x0, 0x1F
W3D_TEXTURE_NAME = 0x32
W3D_HIERARCHY, W3D_HIERARCHY_HEADER = 0x100, 0x101
W3D_ANIMATION, W3D_ANIMATION_HEADER = 0x200, 0x201
W3D_COMPRESSED_ANIMATION, W3D_COMPRESSED_ANIMATION_HEADER = 0x280, 0x281
W3D_EMITTER, W3D_EMITTER_INFO = 0x500, 0x503
W3D_AGGREGATE, W3D_AGGREGATE_INFO = 0x600, 0x602
W3D_HLOD, W3D_HLOD_HEADER = 0x700, 0x701
W3D_HLOD_LOD_ARRAY, W3D_HLOD_AGGREGATE_ARRAY = 0x702, 0x705
W3D_HLOD_SUB_OBJECT_HEADER, W3D_HLOD_SUB_OBJECT = 0x703, 0x704


def cstr(raw: bytes) -> str:
    return raw.split(b'\0', 1)[0].decode('latin1')


def crc_stringi(name: str) -> int:
    # toupper() in the C locale only changes ASCII letters; bytes.upper() matches that.
    return zlib.crc32(name.encode('latin1').upper()) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Port path translation emulation (port/filesystem/renegade_paths.cpp)
# ---------------------------------------------------------------------------

def normalize_logical(logical: str):
    """Mirror Normalize(); returns (normalized, reason). reason None means ok."""
    if not logical:
        return None, 'empty'
    if logical[0] in '/\\':
        return None, 'absolute'
    if ':' in logical:
        return None, 'contains-colon'
    out, previous = [], False
    for ch in logical:
        ch = '/' if ch == '\\' else ch
        if ch == '/':
            if previous:
                continue
            previous = True
        else:
            previous = False
        out.append(ch)
    text = ''.join(out).rstrip('/')
    if not text:
        return None, 'empty'
    if len(text) >= 767:
        return None, 'overlong'
    for part in text.split('/'):
        if part in ('.', '..'):
            return None, 'dot-component'
    return text, None


def logical_namespace(normalized: str):
    """First-component namespace the port diverts to a writable root, if any."""
    first = normalized.split('/', 1)[0].lower()
    return first if first in LOADER_NAMESPACES and first != 'retail' else None


class LooseTree:
    """Case-insensitive directory resolution over a real retail root."""

    def __init__(self, root: Path):
        self.root = root
        self._listing = {}

    def listing(self, directory: Path):
        key = str(directory)
        if key not in self._listing:
            try:
                self._listing[key] = sorted(os.listdir(directory))
            except OSError:
                self._listing[key] = None
        return self._listing[key]

    def resolve(self, logical: str):
        """Return dict(status=..., path=Path|None, case_only=bool)."""
        normalized, reason = normalize_logical(logical)
        if normalized is None:
            return {'status': 'rejected', 'reason': reason, 'path': None, 'case_only': False}
        namespace = logical_namespace(normalized)
        if namespace:
            return {'status': 'diverted', 'reason': namespace, 'path': None, 'case_only': False}
        if normalized.lower().startswith('retail/'):
            normalized = normalized[7:]
        current, case_only = self.root, False
        for part in normalized.split('/'):
            names = self.listing(current)
            if names is None:
                return {'status': 'missing', 'path': None, 'case_only': False}
            if part in names:
                current = current / part
                continue
            fold = [n for n in names if n.lower() == part.lower()]
            if not fold:
                return {'status': 'missing', 'path': None, 'case_only': False}
            current, case_only = current / fold[0], True
        if current.is_file():
            return {'status': 'found', 'path': current, 'case_only': case_only}
        return {'status': 'missing', 'path': None, 'case_only': False}

    def case_collisions(self):
        rows = []
        for directory, names in sorted(self._listing.items()):
            if not names:
                continue
            seen = defaultdict(list)
            for name in names:
                seen[name.lower()].append(name)
            rows.extend({'directory': directory, 'names': v} for v in seen.values() if len(v) > 1)
        return rows


# ---------------------------------------------------------------------------
# Mount model
# ---------------------------------------------------------------------------

class Archive:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.name
        self.mix = MixArchive(path)
        self.by_crc = defaultdict(list)
        for stored, _crc, offset, size in self.mix.entry_records:
            self.by_crc[crc_stringi(stored)].append((stored, offset, size))

    def lookup(self, name: str):
        rows = self.by_crc.get(crc_stringi(name))
        if not rows:
            return None
        stored, offset, size = rows[0]
        return {'provider': self.name, 'kind': 'archive', 'stored_name': stored,
                'offset': offset, 'size': size, 'duplicates': len(rows),
                'crc_alias': stored.lower() != name.lower()}

    def read(self, hit):
        with self.path.open('rb') as stream:
            stream.seek(hit['offset'])
            return stream.read(hit['size'])


class Mount:
    """Ordered provider list with first-match semantics."""

    def __init__(self, ctx, mission_mix, order):
        self.ctx, self.mission_mix, self.order = ctx, mission_mix, order
        names = list(SHARED_VITA if order == 'vita' else SHARED_PC)
        if order == 'vita':
            if mission_mix and mission_mix.lower() != 'm00_tutorial.mix':
                if mission_mix.lower() == 'm09.mix':
                    names.insert(0, mission_mix)  # Set_Search_Start hack
                else:
                    names.append(mission_mix)
        else:
            names.extend(ctx.all_mix_names)
            if mission_mix and mission_mix.lower() == 'm09.mix':
                names.remove(mission_mix)
                names.insert(0, mission_mix)
        self.archive_names = names
        # Set_Search_Start(M09.mix): that factory is asked before the loose ones.
        self.search_start = names[0] if mission_mix and mission_mix.lower() == 'm09.mix' else None

    def providers(self):
        return ['loose:retail-root', 'loose:Data'] + self.archive_names

    def lookup(self, name: str):
        """First provider that serves ``name`` for a bare archive-style lookup."""
        if self.search_start:
            archive = self.ctx.archive(self.search_start)
            found = archive.lookup(name) if archive else None
            if found:
                return found
        hit = self.ctx.loose_lookup(name)
        if hit:
            return hit
        for archive_name in self.archive_names:
            archive = self.ctx.archive(archive_name)
            if archive is None:
                continue
            found = archive.lookup(name)
            if found:
                return found
        return None

    def lookup_all(self, name: str):
        hits = []
        loose = self.ctx.loose_lookup(name)
        if loose:
            hits.append(loose)
        for archive_name in self.archive_names:
            archive = self.ctx.archive(archive_name)
            found = archive.lookup(name) if archive else None
            if found:
                hits.append(found)
        return hits

    def read(self, hit):
        if hit['kind'] == 'loose':
            return Path(hit['path']).read_bytes()
        return self.ctx.archive(hit['provider']).read(hit)


class Context:
    def __init__(self, data: Path):
        self.data = data
        self.retail_root = data.parent
        self.root_tree = LooseTree(self.retail_root)
        self.data_tree = LooseTree(data)
        self._archives = {}
        self.all_mix_names = sorted(
            (p.name for p in data.iterdir() if p.is_file() and p.suffix.lower() == '.mix'),
            key=str.lower)
        self.unmounted = [p.name for p in data.iterdir()
                          if p.is_file() and p.suffix.lower() in ('.dat', '.mix', '.dbs')
                          and p.name.lower() == 'always3.dat']

    def parsed(self, mount, hit):
        cache = self.__dict__.setdefault('_parse_cache', {})
        key = (hit['provider'], hit.get('offset'), hit.get('path'), hit['size'])
        if key not in cache:
            cache[key] = parse_w3d(mount.read(hit))
        return cache[key]

    def global_declared(self):
        """lower prototype name -> ['archive:file'] over every W3D in the supplied archives."""
        index = self.__dict__.get('_global_declared')
        if index is not None:
            return index
        index = defaultdict(list)
        for archive_name in ['Always2.dat', 'always.dat'] + self.all_mix_names:
            archive = self.archive(archive_name)
            if archive is None:
                continue
            for stored, _crc, offset, size in archive.mix.entry_records:
                if not stored.lower().endswith('.w3d'):
                    continue
                hit = {'provider': archive.name, 'kind': 'archive', 'offset': offset, 'size': size}
                info = self.parsed(archive, hit)
                for name in info['declared']:
                    index[name.lower()].append(archive_name + ':' + stored)
                self.__dict__.setdefault('_global_htrees', set()).update(h.lower() for h in info['htrees'])
        self._global_declared = index
        return index

    def global_htrees(self):
        self.global_declared()
        return self.__dict__.get('_global_htrees', set())

    def archive(self, name: str):
        if name not in self._archives:
            path = self.data / name
            if not path.is_file():
                matches = [p for p in self.data.iterdir() if p.name.lower() == name.lower()]
                path = matches[0] if matches else None
            self._archives[name] = Archive(path) if path else None
        return self._archives[name]

    def loose_lookup(self, name: str):
        for label, tree in (('retail-root', self.root_tree), ('Data', self.data_tree)):
            res = tree.resolve(name)
            if res['status'] == 'found':
                return {'provider': 'loose:' + label, 'kind': 'loose', 'path': str(res['path']),
                        'stored_name': res['path'].name, 'size': res['path'].stat().st_size,
                        'case_only': res['case_only'], 'crc_alias': False}
        return None


# ---------------------------------------------------------------------------
# W3D metadata extraction
# ---------------------------------------------------------------------------

def siblings(data: bytes):
    pos = 0
    while pos + 8 <= len(data):
        kind, size = struct.unpack_from('<II', data, pos)
        end = pos + 8 + (size & 0x7FFFFFFF)
        if end > len(data):
            raise ValueError('chunk exceeds parent')
        yield kind, data[pos + 8:end]
        pos = end


def parse_w3d(data: bytes):
    """Return dict of declared names, HLOD children, textures, htrees, anims."""
    info = {'declared': [], 'hlods': [], 'aggregates': [], 'textures': [], 'htrees': [],
            'anims': [], 'parse_error': None}
    try:
        for kind, body in siblings(data):
            if kind == W3D_MESH:
                head = [b for k, b in siblings(body) if k == W3D_MESH_HEADER3]
                if head and len(head[0]) >= 40:
                    mesh, container = cstr(head[0][8:24]), cstr(head[0][24:40])
                    name = container + '.' + mesh if container else mesh
                    info['declared'].append(name)
                    owner = name
                    for path, off, size in chunk_paths(body):
                        if path[-1] == W3D_TEXTURE_NAME:
                            tex = cstr(body[off + 8:off + 8 + size]).strip()
                            if tex:
                                info['textures'].append((tex, owner))
            elif kind == W3D_HIERARCHY:
                head = [b for k, b in siblings(body) if k == W3D_HIERARCHY_HEADER]
                if head and len(head[0]) >= 20:
                    info['htrees'].append(cstr(head[0][4:20]))
            elif kind in (W3D_ANIMATION, W3D_COMPRESSED_ANIMATION):
                want = W3D_ANIMATION_HEADER if kind == W3D_ANIMATION else W3D_COMPRESSED_ANIMATION_HEADER
                head = [b for k, b in siblings(body) if k == want]
                if head and len(head[0]) >= 36:
                    info['anims'].append(cstr(head[0][20:36]) + '.' + cstr(head[0][4:20]))
            elif kind == W3D_HLOD:
                children = list(siblings(body))
                head = [b for k, b in children if k == W3D_HLOD_HEADER]
                if not head or len(head[0]) != 40:
                    raise ValueError('invalid HLOD header')
                name, hier = cstr(head[0][8:24]), cstr(head[0][24:40])
                info['declared'].append(name)
                subs = []
                for k, b in children:
                    if k in (W3D_HLOD_LOD_ARRAY, W3D_HLOD_AGGREGATE_ARRAY):
                        for k2, b2 in siblings(b):
                            if k2 == W3D_HLOD_SUB_OBJECT and len(b2) == 36:
                                subs.append((cstr(b2[4:36]), 'lod' if k == W3D_HLOD_LOD_ARRAY else 'aggregate'))
                info['hlods'].append({'name': name, 'hierarchy': hier, 'children': subs})
            elif kind == W3D_EMITTER:
                head = [b for k, b in siblings(body) if k == 0x501]
                if head and len(head[0]) >= 20:
                    name = cstr(head[0][4:20])
                    info['declared'].append(name)
                    for k, b in siblings(body):
                        if k == W3D_EMITTER_INFO and len(b) >= 260:
                            tex = cstr(b[:260]).strip()
                            if tex:
                                info['textures'].append((tex, name))
            elif kind == W3D_AGGREGATE:
                head = [b for k, b in siblings(body) if k == 0x601]
                if head and len(head[0]) >= 20:
                    name = cstr(head[0][4:20])
                    info['declared'].append(name)
                    subs = []
                    for k, b in siblings(body):
                        if k == W3D_AGGREGATE_INFO and len(b) >= 40:
                            count = struct.unpack_from('<I', b, 36)[0]
                            subs.append((cstr(b[:32]), 'aggregate-base'))
                            for i in range(min(count, 512)):
                                base = 40 + i * 64
                                if base + 32 <= len(b):
                                    subs.append((cstr(b[base:base + 32]), 'aggregate'))
                    info['aggregates'].append({'name': name, 'children': subs})
            elif kind in (0x740, 0x741, 0x742, 0x750, 0x900, 0xA00, 0x300, 0x400, 0x420):
                # Names for these kinds are handled by the reviewed declaration
                # parser in tools/audit_hlod_dependencies.py.
                pass
    except (ValueError, struct.error) as error:
        info['parse_error'] = str(error)
    try:
        from tools.audit_hlod_dependencies import declared_render_names
        extra = declared_render_names(data)
        known = {n.lower() for n in info['declared']}
        info['declared'].extend(r['name'] for r in extra if r['name'].lower() not in known)
    except Exception as error:  # noqa: BLE001 - metadata parser only
        info['parse_error'] = info['parse_error'] or str(error)
    return info


def read_dep(payload: bytes):
    """``.dep`` = chunk 0x04020527 containing micro-chunk 1 filename records."""
    names, issues = [], []
    if len(payload) < 8:
        return names, ['short dependency file']
    kind, size = struct.unpack_from('<II', payload, 0)
    if kind != 0x04020527:
        return names, ['unexpected dependency root chunk 0x%08X' % kind]
    end = min(len(payload), 8 + (size & 0x7FFFFFFF))
    pos = 8
    while pos + 2 <= end:
        micro, length = payload[pos], payload[pos + 1]
        body = payload[pos + 2:pos + 2 + length]
        pos += 2 + length
        if micro != 1:
            issues.append('unexpected micro-chunk %d' % micro)
            continue
        names.append(cstr(body))
    return names, issues


# ---------------------------------------------------------------------------
# Closure
# ---------------------------------------------------------------------------

def texture_candidates(name: str):
    """Names the Vita texture loader probes, in order."""
    lower = name.lower()
    if len(lower) < 4:
        return ['(name shorter than 4 characters: DDSFileClass writes before the buffer)']
    return [lower[:-3] + 'dds', lower]


class Closure:
    def __init__(self, ctx: Context, mission_mix: str):
        self.ctx, self.mix = ctx, mission_mix
        self.vita = Mount(ctx, mission_mix, 'vita')
        self.pc = Mount(ctx, mission_mix, 'pc')
        self.files = {}  # lower filename -> {'hit':..., 'info':...} (Vita view)
        self.declared = {}  # lower name -> [file]
        self.htrees, self.anims = set(), set()
        self.findings = defaultdict(list)
        self.stats = Counter()

    # -- file loading ------------------------------------------------------
    def load(self, filename: str, origin: str = 'on-demand'):
        key = filename.lower()
        if key in self.files:
            return self.files[key]
        hit = self.vita.lookup(filename)
        entry = None
        if hit:
            entry = {'hit': hit, 'info': self.ctx.parsed(self.vita, hit), 'filename': filename,
                     'origin': origin}
            for name in entry['info']['declared']:
                self.declared.setdefault(name.lower(), []).append(filename)
            self.htrees.update(h.lower() for h in entry['info']['htrees'])
            self.anims.update(a.lower() for a in entry['info']['anims'])
        self.files[key] = entry
        return entry

    # -- name resolution rules --------------------------------------------
    def on_demand_filename(self, robj_name: str):
        mesh = robj_name.find('.')
        return (robj_name[:mesh] if mesh >= 0 else robj_name) + '.w3d'

    def resolve_robj(self, name: str, trail=None):
        """Create_Render_Obj semantics: prototype by name, else <name>.w3d on demand."""
        lower = name.lower()
        if lower == 'null':
            return 'builtin'
        if lower in self.declared:
            return 'declared'
        filename = self.on_demand_filename(name)
        entry = self.load(filename)
        if entry:
            if lower in self.declared:
                return 'on-demand'
            return 'file-lacks-prototype'
        return 'missing'


def audit_mission(ctx: Context, mission: str, sound_context):
    mix_name = mission + '.mix'
    report = {'mission': mission, 'archive': mix_name, 'categories': {}, 'unresolved': []}
    closure = Closure(ctx, mix_name)
    mix = ctx.archive(mix_name)
    if mix is None:
        report['error'] = 'mission archive missing'
        return report

    def unresolved(category, name, referencing, **extra):
        # ``probe`` is the file name(s) the loader would ask the factory list for.
        probe = extra.pop('probe', name)
        probes = probe if isinstance(probe, list) else [probe]
        pc_hits = [h for p in probes for h in closure.pc.lookup_all(p)]
        vita_hits = [h for p in probes for h in closure.vita.lookup_all(p)]
        row = {'mission': mission, 'category': category, 'name': name, 'referenced_by': referencing,
               # PC-only means the PC order finds a provider the Vita order never mounts.
               'pc_order_resolves': bool(pc_hits) and not vita_hits,
               'pc_providers': [h['provider'] for h in pc_hits][:3],
               'vita_providers': [h['provider'] for h in vita_hits][:3]}
        row.update(extra)
        report['unresolved'].append(row)
        return row

    def count(category, checked=0, resolved=0, unresolved_n=0):
        row = report['categories'].setdefault(category, {'checked': 0, 'resolved': 0, 'unresolved': 0})
        row['checked'] += checked
        row['resolved'] += resolved
        row['unresolved'] += unresolved_n

    # 1. preload lists: always.dep (first provider wins) then <mission>.dep ------
    always_hits = closure.vita.lookup_all('always.dep')
    report['always_dep_providers'] = [h['provider'] for h in always_hits]
    dep_lists = []
    if always_hits:
        names, issues = read_dep(closure.vita.read(always_hits[0]))
        dep_lists.append(('always.dep', names, issues))
    mission_dep = mix.lookup(Path(mix_name).stem + '.dep')
    if mission_dep:
        names, issues = read_dep(mix.read(mission_dep))
        dep_lists.append(('mission.dep', names, issues))
    else:
        dep_lists.append(('mission.dep', [], ['mission .dep absent']))
    seen_dep, placeholders, record_count = set(), 0, 0
    for origin, names, issues in dep_lists:
        report.setdefault('dep_issues', []).extend(issues)
        record_count += len(names)
        for raw in names:
            base = raw.replace('\\', '/').rsplit('/', 1)[-1]
            if not base or base.lower() == '.w3d':
                placeholders += 1
                continue
            if raw.lower() in seen_dep:
                continue
            seen_dep.add(raw.lower())
            entry = closure.load(raw, origin)
            category = 'dep_w3d' if origin == 'mission.dep' else 'always_dep_w3d'
            flags = {}
            odd = sorted(set(re.findall(r'[^A-Za-z0-9_.\- ]', raw)))
            if odd:
                flags['unusual_characters'] = odd
            if entry:
                count(category, 1, 1)
                if entry['hit'].get('crc_alias'):
                    flags['crc_alias'] = entry['hit']['stored_name']
                if flags:
                    report.setdefault('dep_name_flags', []).append(
                        {'name': raw, 'list': origin, **flags, 'resolved': entry['hit']['provider']})
            else:
                count(category, 1, 0, 1)
                unresolved(category, raw, 'preload ' + origin + ' record',
                           fuzzy_candidates=fuzzy_candidates(ctx, closure, raw),
                           **({'name_flags': flags} if flags else {}))
    report['dep_record_count'] = record_count
    report['dep_placeholder_records'] = placeholders

    # mission mix W3D members: the level's own geometry, requested by name ----------
    members = [n for n, *_ in mix.mix.entry_records if n.lower().endswith('.w3d')]
    shadowed = []
    for member in members:
        entry = closure.load(member, 'mission-member')
        if entry is None:
            count('mission_w3d_member', 1, 0, 1)
            unresolved('mission_w3d_member', member, 'mission mix member')
            continue
        count('mission_w3d_member', 1, 1)
        if entry['hit']['provider'].lower() != mix_name.lower():
            own = mix.lookup(member)
            shadowed.append({'member': member, 'served_by': entry['hit']['provider'],
                             'same_size': own is not None and own['size'] == entry['hit']['size']})
    report['mission_members_shadowed_by_earlier_provider'] = shadowed

    # 2. HLOD / aggregate / hierarchy closure ----------------------------------------
    done_files, child_refs, htree_refs = set(), [], []
    while True:
        pending = [e for e in list(closure.files.values()) if e and id(e) not in done_files]
        if not pending:
            break
        for entry in pending:
            done_files.add(id(entry))
            info = entry['info']
            if info['parse_error']:
                report.setdefault('parse_errors', []).append(
                    {'file': entry['filename'], 'error': info['parse_error']})
            for hlod in info['hlods']:
                if hlod['hierarchy']:
                    htree_refs.append((hlod['hierarchy'], entry['filename'] + ':' + hlod['name']))
                for child, kind in hlod['children']:
                    child_refs.append((child, kind, entry['filename'] + ':' + hlod['name']))
            for agg in info['aggregates']:
                for child, kind in agg['children']:
                    child_refs.append((child, kind, entry['filename'] + ':' + agg['name']))
        for child, _kind, _owner in child_refs:
            closure.resolve_robj(child)
        for tree, _owner in htree_refs:
            if tree.lower() not in closure.htrees:
                closure.load(tree + '.w3d')
    seen = set()
    preload_dependent = []
    global_declared = ctx.global_declared()
    for child, kind, owner in child_refs:
        key = (child.lower(), owner)
        if key in seen:
            continue
        seen.add(key)
        verdict = closure.resolve_robj(child)
        if verdict in ('declared', 'on-demand', 'builtin'):
            count('hlod_child', 1, 1)
            if verdict == 'declared':
                origins = {closure.files[f.lower()]['origin'] for f in closure.declared[child.lower()]
                           if closure.files.get(f.lower())}
                own_file = closure.files.get(closure.on_demand_filename(child).lower())
                self_declares = bool(own_file) and child.lower() in {
                    n.lower() for n in own_file['info']['declared']}
                if not self_declares and origins <= {'always.dep', 'mission.dep'}:
                    preload_dependent.append({'name': child, 'origins': sorted(origins),
                                              'declared_by': closure.declared[child.lower()][:2]})
        else:
            count('hlod_child', 1, 0, 1)
            declared_in = global_declared.get(child.lower(), [])[:3]
            unresolved('hlod_child', child, owner, kind=kind, verdict=verdict,
                       on_demand_file=closure.on_demand_filename(child), declared_in_unloaded_files=declared_in,
                       probe=closure.on_demand_filename(child),
                       fuzzy_candidates=fuzzy_candidates(ctx, closure, closure.on_demand_filename(child)))
    seen_preload = {}
    for row in preload_dependent:
        seen_preload.setdefault(row['name'].lower(), row)
    report['preload_dependent_prototypes'] = {
        'count': len(seen_preload),
        'only_always_dep': sum(1 for r in seen_preload.values() if r['origins'] == ['always.dep']),
        'sample': sorted(seen_preload.values(), key=lambda r: r['name'].lower())[:8]}
    seen = set()
    for tree, owner in htree_refs:
        if (tree.lower(), owner) in seen:
            continue
        seen.add((tree.lower(), owner))
        if tree.lower() in closure.htrees:
            count('hlod_htree', 1, 1)
        else:
            count('hlod_htree', 1, 0, 1)
            unresolved('hlod_htree', tree, owner, on_demand_file=tree + '.w3d', probe=tree + '.w3d')

    # 3. textures ---------------------------------------------------------------------
    tex_seen = {}
    for entry in [e for e in closure.files.values() if e]:
        for tex, owner in entry['info']['textures']:
            tex_seen.setdefault(tex.lower(), (tex, entry['filename'] + ':' + owner))
    for lower, (tex, owner) in sorted(tex_seen.items()):
        if lower.startswith(SCRIPT_ONLY_TEXTURE_PREFIXES):
            count('texture', 1, 1)
            continue
        flags = {}
        if '\\' in tex or '/' in tex:
            flags['path_qualified'] = True
        if not re.search(r'\.(tga|dds)$', lower):
            flags['non_tga_dds_extension'] = True
        cands = texture_candidates(tex)
        hit_dds = closure.vita.lookup(cands[0]) if cands[0].endswith('dds') else None
        hit_tga = closure.vita.lookup(lower) if len(cands) > 1 else None
        if hit_dds:
            count('texture', 1, 1)
            if flags:
                report.setdefault('texture_name_flags', []).append(
                    {'name': tex, **flags, 'resolved': hit_dds['provider']})
        elif hit_tga:
            count('texture', 1, 1)
            report.setdefault('texture_tga_only', []).append(
                {'name': tex, 'provider': hit_tga['provider'], 'bytes': hit_tga['size']})
        else:
            count('texture', 1, 0, 1)
            unresolved('texture', tex, owner, candidates_probed=cands, probe=cands, **flags)

    # 4-7. cinematics, sounds, conversations ------------------------------------------
    sound_context(ctx, closure, mission, report, unresolved, count)
    report['w3d_files_loaded'] = len([e for e in closure.files.values() if e])
    report['declared_prototypes'] = len(closure.declared)
    report['providers_vita'] = closure.vita.providers()
    return report


def simplify(name: str):
    return re.sub(r'[^a-z0-9]', '', name.lower().replace('\\', '/').rsplit('/', 1)[-1])


def fuzzy_candidates(ctx: Context, closure: Closure, name: str):
    """Names a human would call the same asset (case/punctuation/path mangling)."""
    index = ctx.__dict__.get('_fuzzy')
    if index is None:
        index = ctx._fuzzy = defaultdict(list)
        for archive_name in ctx.all_mix_names + ['Always2.dat', 'always.dbs', 'always.dat']:
            archive = ctx.archive(archive_name)
            if archive is None:
                continue
            for stored, _crc, _o, _s in archive.mix.entry_records:
                index[simplify(stored)].append(archive_name + ':' + stored)
    own = name.replace('\\', '/').rsplit('/', 1)[-1].lower()
    return [c for c in index.get(simplify(name), []) if c.split(':', 1)[1].lower() != own][:3]


# ---------------------------------------------------------------------------
# Cinematics, sounds, conversations, movies
# ---------------------------------------------------------------------------

def audio_context(ctx: Context, closure: Closure, mission: str, report, unresolved, count):
    from tools.audit_level_static_sounds import static_sounds, dynamic_audio
    mix = ctx.archive(closure.mix)
    stem = mission.lower()

    # -- cinematic text files (create_object / play_animation / play_audio) --
    scan = scan_all_text(mix.mix)
    deps = scan['dependencies']
    report['cinematic_text_files'] = scan['text_file_count']
    for model in deps.get('cinematic_models', []):
        verdict = closure.resolve_robj(model)
        if verdict in ('declared', 'on-demand', 'builtin'):
            count('cinematic_model', 1, 1)
        else:
            count('cinematic_model', 1, 0, 1)
            unresolved('cinematic_model', model, 'cinematic text create_object', verdict=verdict,
                       on_demand_file=closure.on_demand_filename(model),
                       probe=closure.on_demand_filename(model))
    for anim in deps.get('animations', []):
        check_animation(ctx, closure, anim, 'cinematic text play_animation', unresolved, count,
                        category='cinematic_animation')
    for sound in deps.get('audio', []):
        check_sound_name(ctx, closure, sound, 'cinematic text play_audio', unresolved, count,
                         category='cinematic_audio')

    # -- level static sounds and music --------------------------------------
    for suffix in ('.lsd', '.ldd'):
        hit = mix.lookup(stem + suffix)
        if hit is None:
            unresolved('level_data', stem + suffix, 'mission mix', probe=[])
            count('level_data', 1, 0, 1)
            continue
        count('level_data', 1, 1)
        payload = mix.read(hit)
        if suffix == '.lsd':
            records, findings = static_sounds(payload)
            report['static_sound_records'] = len(records)
            for record in records:
                name = record.get('filename')
                if not name:
                    continue
                check_sound_file(ctx, closure, name, 'level .lsd static sound', unresolved, count,
                                 category='static_sound')
        else:
            music = dynamic_audio(payload).get('background_music')
            if music:
                check_sound_file(ctx, closure, music, 'level .ldd background music', unresolved, count,
                                 category='background_music')

    # -- sound presets and conversations ------------------------------------
    presets = ctx.sound_presets_for(closure, mission)
    for preset in presets['sound_files']:
        check_sound_file(ctx, closure, preset['filename'], 'sound preset ' + preset['name'],
                         unresolved, count, category='preset_sound')
    for anim in presets.get('animations', []):
        check_animation(ctx, closure, anim, 'preset string (heuristic scan of reached definitions)',
                        unresolved, count, category='preset_animation')
    for item in presets['conversation_text']:
        count('conversation_text', 1, 1 if item['present'] else 0, 0 if item['present'] else 1)
        if not item['present']:
            unresolved('conversation_text', 'text id %d' % item['text_id'],
                       'conversation ' + item['conversation'], probe=[])
    for leaf in presets['conversation_sounds']:
        check_sound_file(ctx, closure, leaf['filename'], 'conversation voice (text id %d)' % leaf['text_id'],
                         unresolved, count, category='conversation_voice')
    report['preset_summary'] = presets['summary']


def check_animation(ctx, closure, anim, owner, unresolved, count, category):
    lower = anim.lower()
    if '.' not in anim:
        count(category, 1, 0, 1)
        unresolved(category, anim, owner, verdict='bare-name-no-hierarchy-prefix', probe=[])
        return
    if lower in closure.anims:
        count(category, 1, 1)
        return
    filename = anim.split('.', 1)[1] + '.w3d'
    entry = closure.load(filename)
    if entry and lower in closure.anims:
        count(category, 1, 1)
        return
    count(category, 1, 0, 1)
    unresolved(category, anim, owner, on_demand_file=filename, probe=filename,
               verdict='file-lacks-animation' if entry else 'missing')


def sound_basename(name: str):
    return name.replace('\\', '/').rsplit('/', 1)[-1]


def check_sound_file(ctx, closure, filename, owner, unresolved, count, category):
    if not filename or filename.strip().lower() in ('null', 'none'):
        return  # sentinel for "no file", not a lookup
    base = sound_basename(filename)  # WWAudio Strip_Path_From_Filename
    hit = closure.vita.lookup(base)
    if hit:
        count(category, 1, 1)
        return
    count(category, 1, 0, 1)
    unresolved(category, filename, owner, probed=base, probe=base,
               in_unmounted_always3=bool(ctx.archive('always3.dat') and ctx.archive('always3.dat').lookup(base)))


def check_sound_name(ctx, closure, name, owner, unresolved, count, category):
    """Cinematic play_audio names are preset names or raw file names."""
    if name.lower() in ctx.sound_preset_names():
        preset = ctx.sound_preset_names()[name.lower()]
        if preset.get('filename'):
            check_sound_file(ctx, closure, preset['filename'], owner + ' -> preset ' + name,
                             unresolved, count, category)
        else:
            count(category, 1, 1)  # twiddler or folder preset without a file of its own
        return
    for candidate in (name, name + '.wav', name + '.mp3'):
        if closure.vita.lookup(sound_basename(candidate)):
            count(category, 1, 1)
            return
    count(category, 1, 0, 1)
    unresolved(category, name, owner, verdict='neither preset name nor file',
               probe=[name + '.wav', name + '.mp3'])


def movie_checks(ctx: Context, report):
    """campaign.ini Movie directives resolved through the port path emulation."""
    always = ctx.archive('always.dat')
    hit = always.lookup('campaign.ini')
    rows = []
    if not hit:
        return [{'error': 'campaign.ini not found in always.dat'}]
    text = always.read(hit).decode('latin1')
    section = None
    flow = []
    for raw in text.splitlines():
        line = raw.split(';', 1)[0].strip()
        if line.startswith('['):
            section = line[1:line.index(']')]
        elif section == 'Campaign' and '=' in line:
            flow.append(line.split('=', 1)[1].strip())
    level = None
    for directive in flow:
        if directive.startswith('Level '):
            level = directive[6:].split()[0]
        elif directive.startswith('Movie '):
            parts = directive[6:].split()
            movie = parts[0]
            res = ctx.root_tree.resolve(movie)
            if res['status'] == 'missing':
                # BINKMovie boundary also accepts Data\Movies\<name>[.bik] forms.
                for candidate in ('Data\\Movies\\' + movie, 'Data\\Movies\\' + movie + '.bik'):
                    res = ctx.root_tree.resolve(candidate)
                    if res['status'] == 'found':
                        break
            rows.append({'directive': directive, 'movie': movie, 'next_level': None,
                         'status': res['status'], 'case_only': res.get('case_only', False),
                         'on_disk': str(res['path'].relative_to(ctx.retail_root)) if res.get('path') else None,
                         'size': res['path'].stat().st_size if res.get('path') else None})
            rows[-1]['_pending'] = True
        elif directive.startswith('Level '):
            pass
    # attach the mission each movie precedes
    pending = None
    flow_levels = []
    for directive in flow:
        if directive.startswith('Movie '):
            pending = directive
        elif directive.startswith('Level '):
            flow_levels.append(directive[6:].split()[0])
            if pending:
                for row in rows:
                    if row['directive'] == pending and row.get('_pending'):
                        row['next_level'] = directive[6:].split()[0]
                        row['_pending'] = False
                pending = None
    for row in rows:
        row.pop('_pending', None)
    return rows


# ---------------------------------------------------------------------------
# Presets (definitions) and conversations -- shared across missions
# ---------------------------------------------------------------------------

def attach_presets(ctx: Context):
    from tools.audit_m13_level_owners import chunks, definitions, level_records, microchunks, reference_fields
    from tools.audit_mission_conversations import sound_definitions, translations
    from tools.audit_deep_saved_content import conversations
    from tools.audit_definition_instance_references import graph

    always_dbs = ctx.archive('always.dbs')
    ddb = always_dbs.mix.read_binary('objects.ddb')
    nodes = chunks(ddb)
    schema = reference_fields(ROOT)
    base_defs = definitions(nodes, schema)
    sounds = sound_definitions(nodes)
    tdb_nodes = chunks(always_dbs.mix.read_binary('strings.tdb'))
    trans, _issues = translations(tdb_nodes)
    ctx._sounds, ctx._trans = sounds, trans
    by_offset = {row['offset']: key for key, row in base_defs.items()}
    preset_strings = defaultdict(set)
    for manager in nodes:
        if manager.kind != 0x101:
            continue
        for group in manager.children:
            if group.kind != 0x101:
                continue
            for factory in group.children:
                key = by_offset.get(factory.offset)
                if key is None:
                    continue
                stack = list(factory.children)
                while stack:
                    node = stack.pop()
                    stack.extend(node.children)
                    if node.children or not node.data:
                        continue
                    try:
                        for _kind, value in microchunks(node.data):
                            if value.endswith(b'\0') and 4 < len(value) < 64 and b'.' in value:
                                text = value[:-1].decode('latin1')
                                if re.fullmatch(r'[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+', text):
                                    preset_strings[key].add(text)
                    except ValueError:
                        continue
    by_name = {}
    for key, row in sounds.items():
        by_name[row['name'].lower()] = {'id': key, 'filename': row.get('filename'), 'name': row['name']}
    ctx._sound_names = by_name

    def sound_presets_for(closure: Closure, mission: str):
        mix = ctx.archive(closure.mix)
        defs = dict(base_defs)
        roots = set()
        convs = []
        for member in sorted(mix.mix.entries):
            payload = mix.mix.read_binary(member)
            if member.endswith('.ddb'):
                defs.update(definitions(chunks(payload), schema))
            elif member.endswith(('.ldd', '.lsd')):
                record = level_records(chunks(payload))
                roots.update(r['definition_id'] for r in record['objects'] + record['spawners'] + record['physics']
                             if r['definition_id'])
                if member.endswith('.ldd'):
                    try:
                        convs.extend(conversations(chunks(payload), allow_legacy_category=False))
                    except ValueError:
                        pass
        roots.update(key for key, row in defs.items()
                     if row['factory'] in ('0x00040602', '0x00040603') or
                     (row['factory'] == '0x00040601' and row['name'].lower() == 'loiter'))
        reached = graph(defs, roots)
        edge_targets = {e['target_id'] if 'target_id' in e else e['id'] for e in reached['edges']}
        edge_targets.update(roots)
        reached_ids = set(edge_targets) | {e['owner_definition_id'] for e in reached['edges']}
        htrees = ctx.global_htrees()
        animations = sorted({text for key in reached_ids for text in preset_strings.get(key, ())
                             if text.split('.', 1)[0].lower() in htrees})
        files = []
        seen = set()
        for target in sorted(edge_targets):
            row = sounds.get(target)
            if row and row.get('filename') and target not in seen:
                seen.add(target)
                files.append({'id': target, 'name': row['name'], 'filename': row['filename']})
        conv_text, conv_sound = [], []
        for conv in convs:
            for remark in conv['remarks']:
                text_id = remark['text_id']
                present = text_id in trans
                conv_text.append({'conversation': conv['name'], 'text_id': text_id, 'present': present})
                row = trans.get(text_id)
                if row and row.get('sound_id'):
                    sound = sounds.get(row['sound_id'])
                    if sound and sound.get('filename'):
                        conv_sound.append({'text_id': text_id, 'filename': sound['filename']})
        return {'sound_files': files, 'animations': animations,
                'conversation_text': conv_text, 'conversation_sounds': conv_sound,
                'summary': {'definition_roots': len(roots), 'reached_definitions': reached['reached_definitions'],
                            'typed_reference_fields': reached['typed_reference_fields'],
                            'missing_definition_ids': len(reached['missing_ids']),
                            'sound_presets_with_files': len(files), 'preset_animation_strings': len(animations),
                            'conversations': len(convs),
                            'conversation_remarks': len(conv_text)}}

    ctx.sound_presets_for = sound_presets_for
    ctx.sound_preset_names = lambda: ctx._sound_names


def retail_name_hazards(ctx: Context):
    """Retail-tree name hazards for the port path translation (global)."""
    findings = []
    for tree in (ctx.root_tree, ctx.data_tree):
        for directory in [tree.root] + [p for p in tree.root.iterdir() if p.is_dir()]:
            tree.listing(directory)
    findings.extend(ctx.root_tree.case_collisions() + ctx.data_tree.case_collisions())
    return findings


def archive_name_hazards(ctx: Context, missions):
    """Archive member names the loose-file translation would reject or divert.

    The FileFactoryList asks the loose factories first for every name, so a name
    that Renegade_Resolve_Path rejects only skips the loose probe (harmless) but a
    name that it diverts to a writable root is probed there before the archives.
    """
    rows = {'rejected': Counter(), 'diverted': Counter(), 'non_ascii': 0, 'whitespace': 0,
            'examples': defaultdict(list), 'members': 0}
    for archive_name in SHARED_VITA + [m + '.mix' for m in missions]:
        archive = ctx.archive(archive_name)
        if archive is None:
            continue
        for stored, _crc, _offset, _size in archive.mix.entry_records:
            rows['members'] += 1
            normalized, reason = normalize_logical(stored)
            if normalized is None:
                rows['rejected'][reason] += 1
                kind = 'rejected:' + str(reason)
            elif logical_namespace(normalized):
                rows['diverted'][logical_namespace(normalized)] += 1
                kind = 'diverted:' + logical_namespace(normalized)
            else:
                kind = None
            if any(ord(c) > 127 for c in stored):
                rows['non_ascii'] += 1
                kind = kind or 'non-ascii'
            if stored != stored.strip() or ' ' in stored:
                rows['whitespace'] += 1
                kind = kind or 'whitespace'
            if kind and len(rows['examples'][kind]) < 4:
                rows['examples'][kind].append(archive_name + ':' + stored)
    return {'members_scanned': rows['members'], 'rejected_by_loose_translation': dict(rows['rejected']),
            'diverted_to_writable_namespace': dict(rows['diverted']), 'non_ascii_names': rows['non_ascii'],
            'names_with_whitespace': rows['whitespace'], 'examples': dict(rows['examples'])}


def run(data: Path, missions, detail_path: Path | None):
    ctx = Context(data)
    attach_presets(ctx)
    results = []
    for mission in missions:
        results.append(audit_mission(ctx, mission, audio_context))
        print('audited %s: %d unresolved' % (mission, len(results[-1]['unresolved'])),
              file=sys.stderr, flush=True)
    movies = movie_checks(ctx, {})
    hazards = retail_name_hazards(ctx)
    ctx.archive_hazards = archive_name_hazards(ctx, missions)
    return ctx, results, movies, hazards


def public_summary(ctx, results, movies, hazards):
    rows = []
    totals = Counter()
    for report in results:
        for category, c in report['categories'].items():
            totals[(category, 'checked')] += c['checked']
            totals[(category, 'unresolved')] += c['unresolved']
        rows.append({'mission': report['mission'], 'archive': report['archive'],
                     'categories': report['categories'], 'unresolved': report['unresolved'],
                     'w3d_files_loaded': report.get('w3d_files_loaded'),
                     'dep_record_count': report.get('dep_record_count'),
                     'dep_placeholder_records': report.get('dep_placeholder_records'),
                     'texture_tga_only': report.get('texture_tga_only', []),
                     'texture_name_flags': report.get('texture_name_flags', []),
                     'dep_name_flags': report.get('dep_name_flags', []),
                     'always_dep_providers': report.get('always_dep_providers'),
                     'preload_dependent_prototypes': report.get('preload_dependent_prototypes'),
                     'mission_members_shadowed_by_earlier_provider':
                         report.get('mission_members_shadowed_by_earlier_provider', []),
                     'parse_errors': report.get('parse_errors', []),
                     'preset_summary': report.get('preset_summary'),
                     'static_sound_records': report.get('static_sound_records')})
    return {'schema': 1, 'evidence_class': 'host_retail_name_and_header_metadata',
            'order_vita': ['loose:retail-root', 'loose:Data'] + SHARED_VITA + ['<mission>.mix (first for M09)'],
            'order_pc': ['loose'] + SHARED_PC + ['data/*.mix in directory order'],
            'unmounted_by_original_game_init': ctx.unmounted,
            'missions': rows, 'movies': movies, 'retail_case_collisions': hazards,
            'archive_name_hazards': getattr(ctx, 'archive_hazards', None),
            'complete': False}


VITA_HANDLING = [
    ('dep_w3d / always_dep_w3d', 'Preload record whose file cannot be opened',
     'AssetDependencyManager::Load_Assets -> WW3DAssetManager::Load_3D_Assets returns false '
     '(staging/combat/assetdep.cpp, staging/ww3d2/assetmgr.cpp:522); the combined result is ignored at '
     'staging/combat/combat.cpp:448/454 and only WWDEBUG_SAY logs it', 'graceful (preload skipped)'),
    ('hlod_child / hlod_htree', 'HLOD or aggregate sub-object with no prototype',
     'WW3DAssetManager::Create_Render_Obj returns NULL after the on-demand `<name>.w3d` attempt '
     '(assetmgr.cpp:689-760); HLodClass construction skips NULL children (staging/ww3d2/hlod.cpp:1146-1165, 1232); '
     'a missing hierarchy name only fails Get_HTree', 'graceful (sub-object omitted, no crash)'),
    ('texture', 'Neither `.dds` nor original name resolves',
     'TextureLoadTaskClass::Begin_Load fails -> Apply_Missing_Texture (staging/ww3d2/textureloader.cpp:893, '
     '1168, 1184) uses MissingTexture created in DX8Wrapper init (dx8wrapper.cpp:337)',
     'graceful (placeholder texture)'),
    ('*_animation', 'Animation name that never registers',
     'WW3DAssetManager::Get_HAnim returns NULL and caches the miss via HAnimManager.Register_Missing '
     '(assetmgr.cpp:920-955); AnimCollisionManager and the other callers test for NULL '
     '(animcollisionmanager.cpp:525). A name without a `.` hits WWASSERT(0) then returns NULL',
     'graceful (pose/animation skipped)'),
    ('*_sound / static_sound / preset_sound / conversation_voice', 'Sound file that cannot be opened',
     'WWAudioClass::Get_Sound_Buffer / Create_Sound_Effect check `file->Is_Available()` and log '
     '"Sound ... not found" (staging/wwaudio/WWAudio.cpp:481-493, 812-824); the sound object is NULL/empty',
     'graceful (silence)'),
    ('conversation_text', 'Text id absent from strings.tdb',
     'TranslateDBClass::Get_String returns STRING_NOT_FOUND for an unknown id and NULL for id 0 '
     '(staging/wwtranslatedb/translatedb.h:250-262)', 'graceful (placeholder text)'),
    ('cinematic_model', 'Cinematic `create_object` model with no prototype',
     'Test_Cinematic Command_Create_Object makes a Generic_Cinematic and calls Commands->Set_Model '
     '(staging/scripts/Test_Cinematic.cpp:472-513, staging/combat/scriptcommands.cpp:757-785) -> '
     'PhysClass::Set_Model_By_Name (staging/wwphys/phys.cpp:206-228): Create_Render_Obj returns NULL, '
     'WWDEBUG_SAY logs it, WWASSERT(model) compiles out without WWDEBUG, and PhysClass::Set_Model(NULL) is '
     'NULL-safe (phys.cpp:181-204). The object is left model-less; later per-frame use of a model-less '
     'physics object was not traced', 'not fully proven (same code and data as the shipped PC game)'),
    ('movie', 'Campaign movie that does not resolve',
     'BINKMovie boundary resolves through Renegade_Resolve_Path and calls Mark_Failed, so '
     'BINKMovie::Is_Complete() becomes true and MovieGameModeClass::Movie_Done continues the chain '
     '(port/platform/a4_binkmovie_boundary.cpp:1115-1144; staging/commando/movie.cpp:286-330)',
     'graceful (movie skipped)'),
]


def group_unresolved(results):
    groups = {}
    for report in results:
        for row in report['unresolved']:
            key = (row['category'], row['name'].lower())
            group = groups.setdefault(key, {'category': row['category'], 'name': row['name'],
                                            'missions': [], 'referenced_by': [], 'pc': row['pc_order_resolves'],
                                            'pc_providers': row.get('pc_providers', []), 'rows': []})
            if report['mission'] not in group['missions']:
                group['missions'].append(report['mission'])
            if row['referenced_by'] not in group['referenced_by']:
                group['referenced_by'].append(row['referenced_by'])
            group['rows'].append(row)
    return groups


def handling_index(category):
    if category in ('dep_w3d', 'always_dep_w3d', 'mission_w3d_member'):
        return 0
    if category == 'cinematic_model':
        return 6
    if category in ('hlod_child', 'hlod_htree'):
        return 1
    if category == 'texture':
        return 2
    if category.endswith('animation'):
        return 3
    if category == 'conversation_text':
        return 5
    return 4


def render_markdown(summary):
    missions = summary['missions']
    groups = group_unresolved([{'mission': m['mission'], 'unresolved': m['unresolved']} for m in missions])
    gap = [g for g in groups.values() if g['pc']]
    shared = [g for g in groups.values() if not g['pc']]
    occurrences = sum(len(g['rows']) for g in groups.values())
    lines = ['# Campaign asset closure (M13, M01-M11)', '',
             'Generated by `tools/audit_campaign_asset_closure.py`; host-only, read-only, names/sizes/counts only.',
             'Evidence class: retail archive index + header metadata. It is not a runtime pass, and a name present',
             'in the data is not proof that a mission executes the path that wants it.', '',
             'Reproduce (Python only, read-only on the retail Data directory):', '',
             '```sh',
             'python3 tools/audit_campaign_asset_closure.py --data "$RENEGADE_RETAIL_ROOT/Data" \\',
             '    --output reports/generated/campaign_asset_closure.json \\',
             '    --markdown reports/campaign/ASSET_CLOSURE.md',
             'python3 -m unittest tools.test_audit_campaign_asset_closure',
             '```', '',
             '## Verdict', '',
             '%d mission-level misses (%d distinct name/category pairs) across %d missions.' % (
                 occurrences, len(groups), len(missions)),
             'Port-side gaps (the PC order resolves them through another mission MIX, the Vita order does not): **%d**.'
             % len(gap),
             'Retail-data defects that the PC game has too (no mounted provider has the name): **%d**.' % len(shared),
             'Every miss class degrades on a traced Vita code path (see the handling table): a missing sub-object,',
             'placeholder texture, skipped animation, silence or skipped preload. The one class not fully proven is a',
             'missing cinematic model, which leaves a model-less decoration physics object (the PC runs identical',
             'code on identical data).', ''
             ,
             'Categories with zero unresolved references in every mission: ' + (', '.join(sorted(
                 c for c in {c for m in missions for c in m['categories']}
                 if not any(m['categories'].get(c, {}).get('unresolved') for m in missions))) or 'none') + '.',
             'Campaign movies not found: %d of %d.' % (
                 sum(1 for r in summary['movies'] if r.get('status') != 'found'), len(summary['movies'])), '',
             '## Method', '',
             '* **Vita lookup order**: ' + ' -> '.join(summary['order_vita']) + '.',
             '* **PC lookup order**: ' + ' -> '.join(summary['order_pc']) + '.',
             '* Archive lookups are by `CRC_Stringi(whole name)`: case never matters, but a directory component,',
             '  a trailing space or a different spelling does. Loose lookups use `Renegade_Resolve_Path`',
             '  (`:`/absolute/`..` rejected, backslash = `/`, per-component case-insensitive match, `user/ cache/ save/ mods/`',
             '  diverted to writable roots).',
             '* Closure roots: `always.dep` (first provider wins) + `<mission>.dep` + the mission MIX `.w3d` members,',
             '  expanded through HLOD/aggregate children, hierarchy names, on-demand `<name>.w3d` loads, mesh and',
             '  emitter textures. Textures follow the Vita loader: last three characters -> `dds`, then the',
             '  original name (TGA), then MissingTexture.',
             '* Sound references: level `.lsd` static sounds, `.ldd` background music, cinematic `play_audio`,',
             '  sound presets reachable from the mission definition graph, and conversation voice leaves',
             '  (`.ldd` conversation -> `strings.tdb` text id -> sound preset -> file, basename only as WWAudio does).',
             '* `always3.dat` (' + ', '.join(summary['unmounted_by_original_game_init']) + ') is not mounted by the',
             '  original `Game_Init` and is only reported as an alternative provider.', '',
             '## Per-mission summary (checked / unresolved)', '']
    categories = sorted({c for m in missions for c in m['categories']})
    lines.append('| Mission | ' + ' | '.join(categories) + ' |')
    lines.append('|---|' + '---|' * len(categories))
    for m in missions:
        cells = []
        for c in categories:
            row = m['categories'].get(c)
            cells.append('%d / %d' % (row['checked'], row['unresolved']) if row else '-')
        lines.append('| %s | %s |' % (m['mission'], ' | '.join(cells)))
    lines += ['', 'Loaded W3D files per mission (closure): ' +
              ', '.join('%s %s' % (m['mission'], m['w3d_files_loaded']) for m in missions) + '.', '']
    lines += ['## Port-side gaps: the PC order resolves, the Vita order does not', '']
    if not gap:
        lines.append('None.')
    else:
        lines += ['| Category | Name | Missions | Referenced by | PC provider |', '|---|---|---|---|---|']
        for g in sorted(gap, key=lambda g: (g['category'], g['name'].lower())):
            lines.append('| %s | `%s` | %s | %s | %s |' % (
                g['category'], g['name'], ', '.join(g['missions']),
                '; '.join('`%s`' % r for r in g['referenced_by'][:2]), ', '.join(g['pc_providers'])))
    if gap:
        lines += ['', 'Suggested follow-up (not applied here: it needs a compile and a Vita3K or hardware check):',
                  'mount each listed PC provider as a lowest-priority supplement for the listed missions, the way the',
                  'Glacier retail-texture fallback does (`glacier_retail_texture_factory` and the supplement slot of',
                  'the factory swap in port/platform/vita/a31_vita_runtime.cpp). Until then the Vita draws the',
                  'MissingTexture placeholder (or omits the sub-object) where the PC shows the real asset.']
    lines += ['', '## Unresolved in both orders (retail-data defects the PC game shares)', '']
    by_category = defaultdict(list)
    for g in shared:
        by_category[g['category']].append(g)
    lines.append('| Category | Distinct names | Mission-occurrences | Vita handling |')
    lines.append('|---|---|---|---|')
    for category in sorted(by_category):
        items = by_category[category]
        lines.append('| %s | %d | %d | %s |' % (category, len(items), sum(len(g['missions']) for g in items),
                                                VITA_HANDLING[handling_index(category)][3]))
    for category in sorted(by_category):
        items = sorted(by_category[category], key=lambda g: g['name'].lower())
        lines += ['', '### ' + category, '']
        lines.append('| Name | Missions | Referencing object (first) | Detail |')
        lines.append('|---|---|---|---|')
        for g in items:
            row = g['rows'][0]
            detail = []
            for key in ('verdict', 'on_demand_file', 'probed'):
                if row.get(key):
                    detail.append('%s=`%s`' % (key, row[key]))
            if row.get('declared_in_unloaded_files'):
                detail.append('declared in unloaded `%s`' % '`, `'.join(row['declared_in_unloaded_files'][:2]))
            if row.get('fuzzy_candidates'):
                detail.append('look-alike `%s`' % '`, `'.join(row['fuzzy_candidates'][:2]))
            if row.get('in_unmounted_always3'):
                detail.append('only in unmounted always3.dat')
            lines.append('| `%s` | %s | `%s` | %s |' % (
                g['name'].replace('|', '/'), ', '.join(g['missions']),
                g['referenced_by'][0].replace('|', '/'), '; '.join(detail)))
    lines += ['', '## Name-mangling and path-translation hazards', '']
    lookalikes = [g for g in groups.values()
                  if any(r.get('fuzzy_candidates') or r.get('declared_in_unloaded_files') for r in g['rows'])]
    lines.append('* Unresolved names that have a case/punctuation/path-insensitive look-alike archive member, or '
                 'whose prototype is declared by an unloaded W3D: %d of %d. %s' % (
                     len(lookalikes), len(groups),
                     'Every unresolved name is genuinely absent, so no case-only or mangling mismatch hides here.'
                     if not lookalikes else 'Listed in the detail columns above.'))
    flagged = [(m['mission'], f) for m in missions for f in m['dep_name_flags']]
    lines.append('* Preload-list names with unusual characters or CRC aliases: %d occurrences.' % len(flagged))
    for mission, flag in flagged[:12]:
        lines.append('  * %s `%s` (%s) -> %s' % (mission, flag['name'], flag['list'], flag['resolved']))
    tflags = [(m['mission'], f) for m in missions for f in m['texture_name_flags']]
    lines.append('* Textures whose name carries a path separator or a non-`.tga/.dds` extension: %d occurrences'
                 % len(tflags) + ' (archive lookups hash the literal string, so these resolve as stored).')
    tga_only = Counter()
    for m in missions:
        for row in m['texture_tga_only']:
            tga_only[row['name'].lower()] += 1
    lines.append('* Textures served only as TGA (no `.dds` sibling in any mounted provider): %d distinct names.'
                 % len(tga_only))
    shadow = sum(len(m['mission_members_shadowed_by_earlier_provider']) for m in missions)
    lines.append('* Mission-MIX `.w3d` members served by an earlier provider instead (same lookup order as the PC):'
                 ' %d across the campaign.' % shadow)
    lines.append('* `always.dep` exists in both Always2.dat and always.dat; only the first provider (%s) is read.'
                 % ', '.join(sorted({str((m['always_dep_providers'] or ['none'])[:1]) for m in missions})))
    hazards = summary.get('archive_name_hazards')
    if hazards:
        lines.append('* Archive member names scanned against the loose-path translation (%d members in the mounted '
                     'archives): rejected %s, diverted to writable roots %s, non-ASCII %d, with whitespace %d.'
                     % (hazards['members_scanned'], hazards['rejected_by_loose_translation'] or 'none',
                        hazards['diverted_to_writable_namespace'] or 'none', hazards['non_ascii_names'],
                        hazards['names_with_whitespace']))
        for kind, names in sorted(hazards['examples'].items()):
            lines.append('  * %s: %s' % (kind, ', '.join('`%s`' % n for n in names)))
    collisions = summary['retail_case_collisions']
    lines.append('* Case-colliding names in the retail tree (port picks exact, then first case-insensitive): %d.'
                 % len(collisions))
    lines += ['', '## Prototypes that resolve only through the `.dep` preload', '',
              'HLOD/aggregate children whose prototype is declared only by a preloaded file and not by their own',
              '`<name>.w3d`. They resolve on the original path (preload on) and would be missing if a performance',
              'experiment dropped the preload.', '']
    pre_rows = [(m['mission'], m['preload_dependent_prototypes'] or {'count': 0, 'only_always_dep': 0,
                                                                     'sample': []}) for m in missions]
    if not any(row['count'] for _mission, row in pre_rows):
        lines.append('None in any mission: every preload-declared child is also served by its own `<name>.w3d`, so')
        lines.append('dropping `always.dep`/`<mission>.dep` moves load cost to first use but cannot leave a prototype')
        lines.append('unresolved.')
    else:
        lines += ['| Mission | Preload-dependent prototypes | of which always.dep only | Sample |', '|---|---|---|---|']
        for mission, row in pre_rows:
            sample = ', '.join('`%s`' % r['name'] for r in row.get('sample', [])[:4])
            lines.append('| %s | %d | %d | %s |' % (mission, row['count'], row['only_always_dep'], sample))
    lines += ['', '## Campaign movies (campaign.ini through the port path translation)', '',
              '| Movie directive | Precedes | Result | On disk | Bytes |', '|---|---|---|---|---|']
    for row in summary['movies']:
        lines.append('| `%s` | %s | %s%s | `%s` | %s |' % (
            row.get('movie'), row.get('next_level') or 'end', row.get('status'),
            ' (case-only)' if row.get('case_only') else '', row.get('on_disk'), row.get('size')))
    lines += ['', '## How the Vita code handles each miss', '',
              '| Asset kind | Miss | Code path | Verdict |', '|---|---|---|---|']
    for kind, miss, path, verdict in VITA_HANDLING:
        lines.append('| %s | %s | %s | %s |' % (kind, miss, path, verdict))
    lines += ['', '## Limits', '',
              '* Closure roots are the original preload lists and mission members; level `.lsd` object model names',
              '  and script-created objects add roots this audit does not enumerate.',
              '* Sound preset coverage follows typed definition references only; script-chosen presets are open.',
              '* `preset_animation` is a heuristic: every `<known hierarchy>.<name>` string in a reached definition,',
              '  not a typed-field walk, so animation names without a known hierarchy prefix are not examined.',
              '* Bare cinematic animation names (no `hierarchy.` prefix) reach `Get_HAnim` unchanged:',
              '  `Command_Play_Animation` in staging/scripts/Test_Cinematic.cpp:639-660 forwards the text to',
              '  `Commands->Set_Animation` (staging/combat/scriptcommands.cpp:796-850), which tests for NULL, so the',
              '  PC and the Vita both skip those animations.',
              '* No decode, render, load or playback was performed; physical Vita behavior is unverified.', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data', type=Path, help='retail Data directory (read-only)')
    parser.add_argument('--missions', nargs='*', default=CAMPAIGN)
    parser.add_argument('--output', type=Path, help='sanitized JSON summary')
    parser.add_argument('--markdown', type=Path, help='write the human report')
    parser.add_argument('--render-json', type=Path,
                        help='render --markdown from a previous sanitized --output JSON without re-auditing')
    args = parser.parse_args(argv)
    if args.render_json:
        if not args.markdown:
            parser.error('--render-json requires --markdown')
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(json.loads(args.render_json.read_text())))
        return 0
    if args.data is None:
        parser.error('--data is required unless --render-json is used')
    ctx, results, movies, hazards = run(args.data, args.missions, None)
    summary = public_summary(ctx, results, movies, hazards)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(summary))
    for report in results:
        unresolved_n = sum(c['unresolved'] for c in report['categories'].values())
        print(json.dumps({'mission': report['mission'], 'unresolved': unresolved_n,
                          'categories': {k: [v['checked'], v['unresolved']]
                                         for k, v in sorted(report['categories'].items())}}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
