"""Read-only original source, substitution and registration census.

Lists candidates rather than treating every absent desktop unit as required.
Does not compile, preprocess, execute game code, or contact a device/server.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from tools.check_m13_script_coverage import ROOT, without_comments, TOKEN
from tools.audit_multiplayer_linkage import inventory


def census(build):
    db = json.loads(subprocess.check_output(['ninja', '-C', str(build), '-t', 'compdb'], text=True))
    rows = [r for r in db if r['output'].startswith('CMakeFiles/RenegadeVitaA31.dir/')]
    compiled = {(Path(r['directory']) / r['file']).resolve() for r in rows}
    definitions = sorted(set(re.findall(r'(?:^|\s)-D([^\s]+)', rows[0]['command'])))
    sources = []
    for module in ('combat', 'commando', 'wwui', 'wwnet', 'wwsaveload', 'wwaudio', 'wwphys', 'ww3d2'):
        # Linux staging contains case aliases. Count the actual canonical path.
        seen = set()
        for p in sorted((ROOT / 'staging' / module).glob('*.cpp')):
            if p.resolve() in seen:
                continue
            seen.add(p.resolve())
            sources.append({'path': str(p.relative_to(ROOT)), 'configured': p.resolve() in compiled,
                            'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
    substitutions = []
    empty_methods = []
    for p in sorted(compiled):
        if p.suffix not in ('.cpp', '.c') or not p.exists():
            continue
        source = p.read_text(encoding='latin1')
        for m in re.finditer(r'^\s*#\s*include\s*"([^"\n]*(?:stub|boundary)[^"\n]*)"', source, re.M):
            substitutions.append({'caller': str(p.relative_to(ROOT)), 'line': source.count('\n',0,m.start())+1,
                                  'include': m[1], 'conditional_status': 'requires guard review'})
        if ROOT / 'port' in p.parents:
            code = TOKEN.sub(lambda m: ('\n' * m[0].count('\n') + ' ') if m[0].startswith(('//','/*')) else m[0],source)
            for m in re.finditer(r'\b([A-Za-z_]\w*::[~A-Za-z_]\w*)\s*\([^{};]*\)\s*(?:const\s*)?\{\s*(?:return\s+(?:false|true|NULL|0)\s*;\s*)?\}', code):
                empty_methods.append({'source': str(p.relative_to(ROOT)), 'method': m[1],
                                      'line': code.count('\n',0,m.start())+1,
                                      'classification': 'constant/empty body; platform legitimacy requires review'})
    binary = build / 'RenegadeVitaA31'
    symbols = subprocess.check_output(['/usr/local/vitasdk/bin/arm-vita-eabi-nm','-C',str(binary)],text=True)
    net = inventory(build, 'RenegadeVitaA31')
    for r in net['factories']:
        # Factory constructors may inline; the derived network class vtable is
        # a useful separate retention signal, not proof of registry execution.
        r['defined_vtable_in_existing_elf'] = bool(re.search(r'^\s*[0-9a-fA-F]+\s+[VvDdRr]\s+vtable for '+re.escape(r['class'])+r'$', symbols, re.M))
    return {'schema':1,'scope':'configured full-port target; candidate omissions and substitutions need semantic review',
            'elf_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
            'configured_translation_units':len(compiled),'compile_definitions':definitions,
            'original_sources':sources,'substitute_include_edges':substitutions,
            'port_constant_or_empty_methods':empty_methods,'network_factories':net}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); r=census(a.build)
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'translation_units':r['configured_translation_units'],
        'original_units':len(r['original_sources']),
        'unselected_original_units':sum(not s['configured'] for s in r['original_sources']),
        'substitute_edges':len(r['substitute_include_edges']),
        'constant_or_empty_methods':len(r['port_constant_or_empty_methods']),
        'network_factory_count':len(r['network_factories']['factories']),
        'missing_network_owners':r['network_factories']['missing_count']},indent=2))
