"""Audit requested campaign/Practice maps and installed retail C&C maps without running the game."""
import argparse
import json
from pathlib import Path
from tools.audit_m13_level_owners import ROOT, audit
from tools.discover_m13_indirect_owners import discover

MAPS = [('M00_Tutorial.mix', ('mtu_',), ('GDI_Orca','GDI_Transport_Helicopter')),
        ('Skirmish00.mix', ('msk_',), ()), ('M13.mix', ('mx0_','dak_mx0_'), ()),
        ('M01.mix', ('m01_',), ())]


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output-directory',type=Path,required=True)
    p.add_argument('--multiplayer',action='store_true')
    a=p.parse_args();a.output_directory.mkdir(parents=True,exist_ok=True)
    maps=list(MAPS)
    if a.multiplayer:
        maps.extend((p.name, (), ()) for p in sorted(a.data.iterdir()) if p.name.lower().startswith('c&c_') and p.suffix.lower()=='.mix')
    summary=[]
    for name,prefixes,presets in maps:
        r=audit(ROOT,a.data/name,a.data/'always.dbs',a.build,
                Path('/usr/local/vitasdk/bin/arm-vita-eabi-nm'),prefixes,presets,deep=True)
        key=Path(name).stem.lower().replace('&','and')
        (a.output_directory/(key+'-typed.json')).write_text(json.dumps(r,indent=2)+'\n')
        d=discover(r,a.data)
        (a.output_directory/(key+'-discovery.json')).write_text(json.dumps(d,indent=2)+'\n')
        row={'map':name,'presets':len(r['selected_definitions']), 'scripts':len(r['scripts']['required_scripts']),
             'missing_owners':r['scripts']['missing_owners'], 'missing_linked_scripts':r['scripts']['missing_linked_factories'],
             'unresolved_scripts':r['scripts']['unresolved_literal_scripts'],
             'factory_types':len(r['persist_factory_owners']),
             'missing_factory_owners':[x for x in r['persist_factory_owners'] if not x['in_existing_native_compile_graph']],
             'missing_factory_load_methods':[x for x in r['persist_factory_owners'] if not x['defined_load_method_in_existing_elf']],
             'unmapped_factory_types':r['unmapped_persist_factories'],
             'commands':len(d['typed_script_commands_used']), 'missing_commands':d['typed_script_commands_without_source_binding'],
             'global_or_source_text_members':len(r['deep_content']['text_members']),
             'unresolved_texts':r['deep_content']['missing_text_names'],
             'envelope_presets':d['definition_count'], 'envelope_scripts':d['script_count']}
        summary.append(row)
        (a.output_directory/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(row),flush=True)
