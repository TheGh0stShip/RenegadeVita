"""Inventory Scripts.dsp callback calls and generate original default bridges."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN_UNITS = ('Mission02.cpp', 'Mission03.cpp', 'Mission05.cpp', 'Mission06.cpp',
                  'Mission07.cpp', 'Mission09.cpp', 'Mission10.cpp', 'MissionDemo.cpp',
                  'Test_PDS.cpp', 'Toolkit_Objectives.cpp')
CAMPAIGN_COMMANDS = ('Add_Objective', 'Create_Explosion', 'Find_Closest_Soldier',
                     'Grant_Key', 'Modify_Action', 'Set_Innate_Soldier_Home_Location',
                     'Start_Conversation')


def strip_comments(text):
    # Strings win over comments, including //****** and comment-like literals.
    pattern = r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/'
    return re.sub(pattern, lambda m: re.sub(r'[^\n]', ' ', m[0])
                  if m[0].startswith(('//', '/*')) else m[0], text)


def arguments(text, start):
    depth = 0
    fields = []
    begin = start
    quote = None
    escaped = False
    for i in range(start, len(text)):
        c = text[i]
        if quote:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == quote: quote = None
            continue
        if c in ('"', "'"): quote = c
        elif c in '([{': depth += 1
        elif c == ')' and depth == 0:
            tail = text[begin:i].strip()
            return fields + ([tail] if tail else []), i
        elif c in ')]}': depth -= 1
        elif c == ',' and depth == 0:
            fields.append(text[begin:i].strip())
            begin = i + 1
    raise ValueError('unterminated callback arguments')


def declarations(text):
    text = strip_comments(text)
    result = {}
    for match in re.finditer(r'\(\s*\*\s*(\w+)\s*\)\s*\(', text):
        fields, _ = arguments(text, match.end())
        defaults = [f.split('=', 1)[1].strip() if '=' in f else None for f in fields]
        if any(d is not None for d in defaults): result[match[1]] = defaults
    return result


def inactive_lines(text):
    """Prove literal #if 0 exclusions; other conditions remain conservative."""
    stack = []
    excluded = set()
    for line, value in enumerate(text.splitlines(), 1):
        directive = re.match(r'\s*#\s*(if|ifdef|ifndef|else|elif|endif)\b(.*)', value)
        if directive:
            kind, expression = directive.groups()
            if kind in ('if', 'ifdef', 'ifndef'):
                stack.append(False if kind == 'if' and expression.strip() == '0' else None)
            elif kind in ('else', 'elif') and stack:
                stack[-1] = True if stack[-1] is False else None
            elif kind == 'endif' and stack:
                stack.pop()
        if False in stack: excluded.add(line)
    return excluded


def generate_header(table):
    lines = ['/* Generated from original Scripts/scriptcommands.h; do not edit. */',
             '#ifndef RENEGADE_CAMPAIGN_SCRIPT_DEFAULTS_H',
             '#define RENEGADE_CAMPAIGN_SCRIPT_DEFAULTS_H',
             '#include "renegade_script_call_defaults.h"', '']
    for name in CAMPAIGN_COMMANDS:
        defaults = table[name]
        size = len(defaults)
        minimum = next(i for i, d in enumerate(defaults) if d is not None)
        tag = 'RENEGADE_CAMPAIGN_' + name.upper()
        for count in range(minimum, size + 1):
            args = ['a' + str(i) for i in range(count)]
            forwarded = args + defaults[count:]
            lines.append(f'#define {tag}_{count}({", ".join(args)}) {name}({", ".join(forwarded)})')
        selector = ', '.join(['_a' + str(i) for i in range(size)] + ['NAME', '...'])
        lines.append(f'#define {tag}_SELECT({selector}) NAME')
        choices = ', '.join(f'{tag}_{i}' for i in range(size, minimum - 1, -1))
        lines.extend([f'#define {name}(...) {tag}_SELECT(__VA_ARGS__, {choices})(__VA_ARGS__)', ''])
    return '\n'.join(lines + ['#endif', ''])


def audit(root=ROOT):
    source = root / 'upstream/CnC_Renegade/Code/Scripts'
    table = declarations((source / 'scriptcommands.h').read_text())
    units = re.findall(r'^SOURCE=\.\\([\w]+\.cpp)$', (source / 'Scripts.dsp').read_text(), re.M)
    if len(units) != 45: raise ValueError('Scripts.dsp denominator must be 45')
    compatibility = root / 'port/compatibility/include'
    headers = {'base': 'renegade_script_call_defaults.h', 'Mission01.cpp': 'renegade_m01_script_defaults.h',
               'Mission11.cpp': 'renegade_m01_script_defaults.h', 'Test_RAD.cpp': 'renegade_m13_area2_script_defaults.h',
               'mission08.cpp': 'renegade_m08_script_defaults.h'}
    macros = {k: set(re.findall(r'^#define\s+(\w+)\(', (compatibility / v).read_text(), re.M))
              for k, v in headers.items()}
    generated = compatibility / 'renegade_campaign_script_defaults.h'
    generated_ok = generated.exists() and generated.read_text() == generate_header(table)
    campaign_wired = True
    for build_file in ('CMakeLists.txt', 'tools/host_a30_definitions/CMakeLists.txt'):
        cmake = (root / build_file).read_text()
        loop = re.search(r'foreach\(rv_campaign_default_unit IN ITEMS\s+([^)]*)\)(.*?)endforeach\(\)', cmake, re.S)
        campaign_wired = campaign_wired and bool(loop and
            set(CAMPAIGN_UNITS).issubset(set(loop[1].split())) and
            'renegade_campaign_script_defaults.h' in loop[2] and
            'COMPILE_OPTIONS' in loop[2] and 'set_property(SOURCE' in loop[2])
    rows = []
    for unit in units:
        text = strip_comments((source / unit).read_text(encoding='latin1'))
        disabled = inactive_lines(text)
        for match in re.finditer(r'\bCommands\s*->\s*(\w+)\s*\(', text):
            name = match[1]
            if name not in table: continue
            fields, _ = arguments(text, match.end())
            maximum = len(table[name])
            minimum = next(i for i, d in enumerate(table[name]) if d is not None)
            covered = name in (macros['base'] | macros.get(unit, set())) or (
                generated_ok and campaign_wired and unit in CAMPAIGN_UNITS and name in CAMPAIGN_COMMANDS)
            status = 'full_arity' if len(fields) == maximum else (
                'invalid_arity' if not minimum <= len(fields) <= maximum else
                'bridge_covered' if covered else 'missing_bridge')
            line = text.count('\n', 0, match.start()) + 1
            if line in disabled: status = 'disabled_by_original_if0'
            rows.append({'unit': unit, 'line': line,
                         'command': name, 'arguments': len(fields), 'status': status})
    return {'dsp_units': len(units), 'default_callbacks': len(table), 'calls': rows,
            'generated_header_current': generated_ok, 'campaign_header_wired': campaign_wired}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate', type=Path)
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    if args.generate:
        table = declarations((ROOT / 'upstream/CnC_Renegade/Code/Scripts/scriptcommands.h').read_text())
        args.generate.write_text(generate_header(table))
    result = audit()
    if args.json: args.json.write_text(json.dumps(result, indent=2) + '\n')
    counts = {s: sum(r['status'] == s for r in result['calls'])
              for s in ('full_arity', 'bridge_covered', 'missing_bridge', 'invalid_arity', 'disabled_by_original_if0')}
    print(json.dumps({'dsp_units': result['dsp_units'], 'default_callbacks': result['default_callbacks'], **counts}))
    return int(args.strict and (counts['missing_bridge'] or counts['invalid_arity'] or not result['generated_header_current']))


if __name__ == '__main__':
    raise SystemExit(main())
