#!/usr/bin/env python3
"""S6 frontend denominator: every original Commando RC dialog declaration.

Resource and reference presence do not prove factory routing or display.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from tools.audit_mission_content_bindings import masked
from tools.generate_wwui_dialog_templates import macros, CAMPAIGN_IDS, MULTIPLAYER_IDS


def dialogs(code):
    clean = masked(code, strings=True)
    rows = []
    for match in re.finditer(r'^[ \t]*(\w+)[ \t]+DIALOG(?:EX)?\b[^\n]*', clean, re.M):
        rows.append({'name': match[1], 'line': clean.count('\n', 0, match.start()) + 1})
    return rows


def inventory(root, template_path):
    original = root / 'upstream/CnC_Renegade/Code/Commando'
    ids = macros((original / 'resource.h', original / 'dialogresource.h'))
    template_bytes = template_path.read_bytes()
    present = {int(n) for n in re.findall(rb'static const unsigned char kDialog(\d+)\[\]', template_bytes)}
    references = {}
    for source in sorted((root / 'staging/commando').iterdir()):
        if source.suffix.lower() not in ('.cpp', '.h', '.hpp'):
            continue
        code = masked(source.read_text(encoding='latin1'), strings=True)
        for match in re.finditer(r'\bIDD_\w+\b', code):
            references.setdefault(match[0], []).append(
                {'source': source.relative_to(root).as_posix(),
                 'line': code.count('\n', 0, match.start()) + 1})
    rows, inputs = [], []
    for resource in sorted(original.glob('*.rc')):
        source = resource.relative_to(root).as_posix()
        inputs.append({'source': source, 'sha256': hashlib.sha256(resource.read_bytes()).hexdigest()})
        for declaration in dialogs(resource.read_text(encoding='latin1')):
            numeric = ids.get(declaration['name'])
            rows.append(dict(declaration, id=hashlib.sha256(
                f'{source}:{declaration["line"]}:{declaration["name"]}'.encode()).hexdigest(),
                source=source, resource_id=numeric,
                selected_by_full_port_generator=numeric in CAMPAIGN_IDS | MULTIPLAYER_IDS,
                present_in_retained_templates=numeric in present,
                source_reference_candidates=references.get(declaration['name'], []),
                status='unknown', evidence_class='source_and_generated_resource_metadata'))
    return {'schema': 1, 'sweep': 'S6', 'complete': False,
            'scope': 'All original Commando/*.rc dialog declarations; staged Commando token references',
            'inputs': inputs, 'template_sha256': hashlib.sha256(template_bytes).hexdigest(),
            'total': len(rows), 'counts': {'unknown': len(rows)},
            'present_in_retained_templates': sum(r['present_in_retained_templates'] for r in rows),
            'absent_from_retained_templates': sum(not r['present_in_retained_templates'] for r in rows),
            'open_risks': ['Conditional resource branches and duplicate declarations',
                           'Dynamic/numeric resource routing and other source directories',
                           'Alternate resource providers', 'Controls/styles and factory callback behavior',
                           'Remaining S6 gameplay/platform/audio/system owners'], 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--templates', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inventory(Path(__file__).resolve().parents[1], args.templates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result[key] for key in ('total', 'present_in_retained_templates', 'absent_from_retained_templates')}))


if __name__ == '__main__':
    main()
