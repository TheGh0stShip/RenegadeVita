"""Reject partial/all-green claims from the cross-system discovery receipts.

Read-only audit gate, not currently wired into build scripts. A pass still
cannot establish execution, UI correctness, networking compatibility or Vita
acceptance. Reviewed optional exclusions need explicit future scope policy.
"""
import argparse
import json
from pathlib import Path

REQUIRED_MAPS={'M00_Tutorial.mix','Skirmish00.mix','M13.mix','M01.mix'}


def blockers(maps,frontend,owners,w3d=None):
    result=[]
    missing=REQUIRED_MAPS-{m['map'] for m in maps}
    if missing:
        result.append({'kind':'missing_map_receipts','items':sorted(missing)})
    for m in maps:
        for key in ('missing_owners','missing_linked_scripts','unresolved_scripts','missing_factory_owners',
                    'missing_factory_load_methods','unmapped_factory_types','missing_commands','unresolved_texts'):
            if key not in m:
                result.append({'kind':'incomplete_receipt','map':m['map'],'field':key})
                continue
            value=m[key]
            bad=any(value.values()) if isinstance(value,dict) else bool(value)
            if bad:
                result.append({'kind':key,'map':m['map'],'items':value})
    for r in frontend['routes']:
        if not r['selected_by_full_port_generator'] or not r['present_in_existing_generated_templates']:
            result.append({'kind':'missing_ui_template','area':r['area'],'name':r['name']})
    for r in owners['network_factories']['factories']:
        if not r['source_compiled'] or not r['defined_vtable_in_existing_elf']:
            result.append({'kind':'network_factory_requires_review','source':r['source'],'class':r['class']})
    if w3d is not None:
        for r in w3d['registration_census']['original_bootstrap_loaders']:
            if not r['configured'] or not r['direct_registration_in_configured_sources']:
                result.append({'kind':'missing_w3d_bootstrap_loader','owner':r['owner'],'symbol':r['symbol']})
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--maps',type=Path,required=True);p.add_argument('--frontend',type=Path,required=True)
    p.add_argument('--owners',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--w3d',type=Path,required=True)
    a=p.parse_args();b=blockers(json.loads(a.maps.read_text()),json.loads(a.frontend.read_text()),json.loads(a.owners.read_text()),json.loads(a.w3d.read_text()))
    a.output.write_text(json.dumps({'status':'INCOMPLETE' if b else 'STATIC_RECEIPTS_CLEAR','blockers':b,
                                    'runtime_verified':False},indent=2)+'\n')
    print('Deep discovery coverage: '+('INCOMPLETE' if b else 'static receipts clear')+'; findings='+str(len(b)))
    raise SystemExit(1 if b else 0)
