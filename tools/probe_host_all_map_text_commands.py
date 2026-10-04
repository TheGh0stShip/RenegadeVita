"""Inventory every local retail map and verify nonempty text transport scopes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tools.renegade_cinematic_dependency_scan import MixArchive


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('binary','retail-root','work','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--reuse-matching',action='store_true')
    args=parser.parse_args()
    args.work.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    binary_hash=digest(args.binary)
    probe_hash=digest(root/'tools/probe_host_mix_text_commands.py')
    rows=[]
    maps=sorted(p for p in (args.retail_root/'Data').iterdir() if p.suffix.lower()=='.mix')
    for path in maps:
        archive=MixArchive(path)
        names=[name for name in archive.entries if name.endswith('.txt')]
        archive_hash=digest(path)
        row={'map':path.name,'archive_sha256':archive_hash,'text_members':len(names),
             'transport_executed':False,'status':'unknown'}
        if names:
            receipt=args.work/(path.stem+'.json')
            data=json.loads(receipt.read_text()) if args.reuse_matching and receipt.exists() else None
            reusable=data and data.get('binary_sha256')==binary_hash and data.get('probe_sha256')==probe_hash \
                and data.get('archive_sha256')=={path.name.lower():archive_hash} \
                and data.get('level_only') is True and data.get('level_mix')==path.name \
                and data.get('total')==len(names) and data.get('matched')==len(names)
            if not reusable:
                result=subprocess.run([sys.executable,'-m','tools.probe_host_mix_text_commands',
                    '--binary',str(args.binary.resolve()),'--retail-root',str(args.retail_root.resolve()),
                    '--work',str((args.work/path.stem).resolve()),'--output',str(receipt.resolve()),
                    '--level-mix',path.name,'--level-only'],cwd=root,capture_output=True,text=True)
                (args.work/(path.stem+'.driver.log')).write_text(result.stdout+result.stderr)
                if result.returncode: raise SystemExit(path.name+' transport failed; inspect private logs')
                data=json.loads(receipt.read_text())
            row.update(transport_executed=True,matched=data['matched'],rows=data['rows'],
                       receipt_sha256=digest(receipt))
        rows.append(row)
        print(path.name,row.get('matched',0),len(names),flush=True)
    result={'schema_version':1,'evidence_class':'all_map_archive_text_inventory_and_host_transport',
        'total_maps':len(rows),'text_members':sum(r['text_members'] for r in rows),
        'matched':sum(r.get('matched',0) for r in rows),'rows':rows,
        'binary_sha256':binary_hash,'probe_sha256':probe_hash,'driver_sha256':digest(Path(__file__)),
        'limits':['Zero-member maps are inventoried, not runtime-tested.',
                  'No world, callbacks, dispatch, playback or physical acceptance.',
                  'Shared archive transport is separate; all-map text names do not enumerate every cinematic dependency.']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    return 0


if __name__=='__main__': raise SystemExit(main())
