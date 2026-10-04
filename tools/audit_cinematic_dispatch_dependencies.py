"""Enumerate every original cinematic dispatch branch and command dependency."""
import argparse
import hashlib
import json
from pathlib import Path
import re
from tools.audit_missing_definition_callers import body
from tools.audit_mission_content_bindings import masked
from tools.audit_mission_text_routes import command_calls


def inventory(source):
    dispatch,line=body(source,'Parse_Command')
    branches=list(re.finditer(r'Title_Match\s*\(\s*&command\s*,\s*"([^"]+)"\s*\)\s*\)\s*(\w+)\s*\(\s*command\s*\)',
                            masked(dispatch)))
    if not branches:raise ValueError('No cinematic dispatch branches found')
    if len({match[1].lower() for match in branches})!=len(branches):
        raise ValueError('Duplicate cinematic dispatch title')
    rows=[]
    for match in branches:
        implementation,owner_line=body(source,match[2])
        calls=command_calls(implementation)
        rows.append({'title':match[1],'method':match[2],'dispatch_line':line+dispatch.count('\n',0,match.start()),
            'method_line':owner_line,'body_sha256':hashlib.sha256(implementation.encode('latin1')).hexdigest(),
            'command_calls':[{'name':call['command'],'line':owner_line+implementation.count('\n',0,call['offset'])}
                             for call in calls],
            'status':'unknown','evidence_class':'original_dispatch_source_metadata'})
    return {'schema_version':1,'total':len(rows),'counts':{'unknown':len(rows)},'rows':rows,
        'unique_engine_commands':sorted({call['name'] for row in rows for call in row['command_calls']}),
        'complete':False,'limits':['Branches and calls are lexical; platform conditions are not evaluated.',
            'No dispatch, slot validity, object lifetime or downstream effects are proven.',
            'Title_Match accepts case-insensitive title prefixes; full dispatch semantics need execution.']}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    owner=Path(__file__).resolve().parents[1]/'staging/scripts/Test_Cinematic.cpp'
    result=inventory(owner.read_text(encoding='latin1'))
    result['source_sha256']=hashlib.sha256(owner.read_bytes()).hexdigest()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['total'],len(result['unique_engine_commands']))


if __name__=='__main__':main()
