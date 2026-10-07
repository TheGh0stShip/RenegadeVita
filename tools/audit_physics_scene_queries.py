#!/usr/bin/env python3
"""Static audit of physics-scene collision and visibility queries added by the port.

TUT-R1 PHYSICS_COLLISION_COST.  Original Westwood callers (Combat, WWPhys,
WW3D) own every gameplay collision query and are out of scope here.  This
audit covers what the Vita port itself adds: port-owned sources under
port/ and the *added* lines of port/patches/*.patch.  Every query found
must be registered in REGISTERED with its cadence and purpose, so an
always-on diagnostic raycast cannot reach a per-frame path unnoticed (a new
per-frame diagnostic query belongs behind
ux0:data/renegade/user/config/physics-cost-v1.flag, prefix RVPH1).

Reads files only.  Never invokes a compiler or the game.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Scene/culling-system queries.  Each one walks an AABTree, the dynamic grid
# or a cached collision region (Find_Vis_Tile casts a box and a ray down).
QUERY_APIS = (
    'Cast_Ray', 'Cast_AABox', 'Cast_OBBox', 'Cast_Semi_Ray',
    'Intersection_Test', 'Collect_Objects', 'Collect_Collideable_Objects',
    'Set_Collision_Region', 'Find_Vis_Tile', 'Get_Vis_Table_For_Rendering',
    'Get_Vis_Table', 'Get_Dynamic_Object_Vis_ID', 'Get_Vis_Sector_ID',
)
# Pure geometry helpers with the same method names; no scene traversal.
PURE_QUALIFIERS = ('CollisionMath::',)
# Called with no argument these are stored-value accessors
# (VisTableClass/StaticPhysClass::Get_Vis_Sector_ID), not lookups.
ACCESSOR_WHEN_EMPTY = frozenset({'Get_Vis_Sector_ID'})

QUERY_RE = re.compile(r'(?<!\w)(' + '|'.join(sorted(QUERY_APIS, key=len, reverse=True)) +
                      r')\s*\(\s*(\))?')
SOURCE_SUFFIXES = frozenset({'.c', '.cc', '.cpp', '.h', '.hpp', '.inl', '.inc'})
# Not runtime C++: vitaGL dependency patches live under the renderer tree.
SKIPPED_DIRS = ('port/patches', 'port/renderer/vita/dependency-patches')

REGISTERED = (
    {
        'path': 'port/platform/a31_gameplay_boundary.cpp',
        'api': 'Get_Vis_Table_For_Rendering',
        'count': 1,
        'kind': 'diagnostic',
        'per_frame': False,
        'flag': None,
        'cadence': 'every 120th render frame, at most 1024 samples per run',
        'note': ('A3.6 vis-census (Sample_Original_Visibility_Census). Repeats '
                 'the PVS lookup PhysicsSceneClass::Pre_Render_Processing made '
                 'for the same camera this frame: one StaticAABTreeCullClass::'
                 'Find_Vis_Tile (one AABox and one ray cast against the static '
                 'tree) plus a cached table fetch. Sampled; no per-frame cost.'),
    },
)


def strip_comments_and_strings(text: str) -> str:
    """Blank C/C++ comments and literal contents, keeping newlines and columns."""
    out = []
    i = 0
    n = len(text)
    state = 'code'
    while i < n:
        c = text[i]
        nxt = text[i + 1] if i + 1 < n else ''
        if state == 'code':
            if c == '/' and nxt == '/':
                state = 'line'
                out.append('  ')
                i += 2
                continue
            if c == '/' and nxt == '*':
                state = 'block'
                out.append('  ')
                i += 2
                continue
            if c in '"\'':
                state = c
                out.append(c)
                i += 1
                continue
            out.append(c)
        elif state == 'line':
            if c == '\n':
                state = 'code'
                out.append(c)
            else:
                out.append(' ')
        elif state == 'block':
            if c == '*' and nxt == '/':
                state = 'code'
                out.append('  ')
                i += 2
                continue
            out.append('\n' if c == '\n' else ' ')
        else:  # inside a string or character literal
            if c == '\\' and nxt:
                out.append('  ')
                i += 2
                continue
            if c == state:
                state = 'code'
                out.append(c)
            elif c == '\n':  # unterminated literal: recover at line end
                state = 'code'
                out.append(c)
            else:
                out.append(' ')
        i += 1
    return ''.join(out)


def find_queries(code: str) -> list[tuple[int, str]]:
    """Return (1-based line, api) for each scene query call in comment-free code."""
    hits = []
    for match in QUERY_RE.finditer(code):
        api = match.group(1)
        start = match.start(1)
        prefix = re.sub(r'\s+', '', code[max(0, start - 48):start])
        if prefix.endswith(PURE_QUALIFIERS):
            continue
        if api in ACCESSOR_WHEN_EMPTY and match.group(2):
            continue
        hits.append((code.count('\n', 0, start) + 1, api))
    return hits


def scan_source(path: Path, rel: str) -> list[dict]:
    code = strip_comments_and_strings(path.read_text(encoding='utf-8', errors='replace'))
    return [{'path': rel, 'line': line, 'api': api, 'origin': 'port-source'}
            for line, api in find_queries(code)]


HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')


def patch_new_side(text: str) -> list[dict]:
    """Split a unified diff into per-hunk new-side text with added-line markers."""
    hunks = []
    target = None
    current = None
    for raw in text.splitlines():
        if raw.startswith('+++ '):
            name = raw[4:].split('\t', 1)[0].strip()
            target = name[2:] if name.startswith(('a/', 'b/')) else name
            current = None
            continue
        if raw.startswith('--- '):
            current = None
            continue
        match = HUNK_RE.match(raw)
        if match:
            current = {'target': target, 'start': int(match.group(1)), 'lines': [], 'added': []}
            hunks.append(current)
            continue
        if current is None or raw.startswith('\\'):
            continue
        if raw.startswith('+'):
            current['lines'].append(raw[1:])
            current['added'].append(True)
        elif raw.startswith(' ') or raw == '':
            current['lines'].append(raw[1:] if raw else '')
            current['added'].append(False)
        # '-' lines belong to the old side only.
    return hunks


def scan_patch(path: Path, rel: str) -> list[dict]:
    hits = []
    for hunk in patch_new_side(path.read_text(encoding='utf-8', errors='replace')):
        code = strip_comments_and_strings('\n'.join(hunk['lines']))
        for line, api in find_queries(code):
            if hunk['added'][line - 1]:
                hits.append({'path': rel, 'line': hunk['start'] + line - 1, 'api': api,
                             'origin': 'port-patch', 'target': hunk['target']})
    return hits


def collect(root: Path = ROOT) -> list[dict]:
    hits = []
    port = root / 'port'
    for path in sorted(port.rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith('port/patches/') and path.suffix == '.patch':
            hits.extend(scan_patch(path, rel))
        elif path.suffix.lower() in SOURCE_SUFFIXES and not rel.startswith(SKIPPED_DIRS):
            hits.extend(scan_source(path, rel))
    return hits


def classify(hits: list[dict], registered=REGISTERED) -> dict:
    """Match hits to REGISTERED by (path, api); report extras and stale entries."""
    counts: dict[tuple[str, str], list[dict]] = {}
    for hit in hits:
        counts.setdefault((hit['path'], hit['api']), []).append(hit)
    known = {(entry['path'], entry['api']): entry for entry in registered}
    unregistered = [hit for key, group in counts.items() if key not in known for hit in group]
    mismatched = []
    stale = []
    for key, entry in known.items():
        found = len(counts.get(key, []))
        if found == 0:
            stale.append(entry)
        elif found != entry['count']:
            mismatched.append({'path': key[0], 'api': key[1], 'expected': entry['count'],
                               'found': found})
    # A per-frame diagnostic query must be switchable (RVPH1 flag file).
    policy = [entry for entry in registered
              if entry.get('kind') == 'diagnostic' and entry.get('per_frame', True)
              and not entry.get('flag')]
    return {'hits': hits, 'unregistered': unregistered, 'count_mismatch': mismatched,
            'stale_registrations': stale, 'policy_violations': policy,
            'registered': list(registered),
            'passed': not unregistered and not mismatched and not stale and not policy}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--json', action='store_true', help='print the full JSON result')
    args = parser.parse_args(argv)
    result = classify(collect(args.root))
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for hit in result['hits']:
            print(f"{hit['origin']:<11} {hit['path']}:{hit['line']} {hit['api']}")
        for hit in result['unregistered']:
            print(f"UNREGISTERED {hit['path']}:{hit['line']} {hit['api']}")
        for item in result['count_mismatch']:
            print(f"COUNT {item['path']} {item['api']} expected={item['expected']} found={item['found']}")
        for entry in result['stale_registrations']:
            print(f"STALE {entry['path']} {entry['api']}")
        for entry in result['policy_violations']:
            print(f"POLICY per-frame diagnostic without flag: {entry['path']} {entry['api']}")
        print('physics-scene query audit:', 'PASS' if result['passed'] else 'FAIL',
              f"hits={len(result['hits'])} registered={len(result['registered'])}")
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
