"""Check original frontend resource IDs against the existing generated templates."""
import argparse
import json
from pathlib import Path
import re
from tools.check_m13_script_coverage import ROOT
from tools.generate_wwui_dialog_templates import macros, CAMPAIGN_IDS, MULTIPLAYER_IDS


ROUTES = {
    'main_menu': ['IDD_MENU_MAIN'],
    'options': ['IDD_MENU_OPTIONS','IDD_MENU_CONTROLS','IDD_OPTIONS_TECH','IDD_CONFIG_AUDIO',
                'IDD_CONFIG_VIDEO','IDD_CONFIG_PERFORMANCE','IDD_OPTIONS_MOVIES','IDD_OPTIONS_CREDITS',
                'IDD_CONTROLS_BASIC_MOVMENT_TAB','IDD_CONTROLS_ADV_MOVMENT_TAB','IDD_CONTROLS_ATTACK_TAB',
                'IDD_CONTROLS_WEAPONS_TAB','IDD_CONTROLS_LOOK_TAB','IDD_CONTROLS_MISC_TAB',
                'IDD_CONTROLS_MULTIPLAYER_TAB','IDD_CONTROLS_ADVANCED_TAB'],
    'death_failure': ['IDD_DEATH_OPTIONS','IDD_FAILED_OPTIONS'],
    'multiplayer': ['IDD_MENU_CNC_REFERENCE','IDD_CNC_TEAM_INFO','IDD_CNC_BATTLE_INFO',
                    'IDD_CNC_SERVER_INFO','IDD_CNC_WINSCREEN','IDD_MULTIPLAY_OPTIONS',
                    'IDD_MP_LAN_HOST_OPTIONS','IDD_MP_LAN_HOST_OPTIONS_BASIC_TAB',
                    'IDD_MP_LAN_HOST_OPTIONS_ADVANCED_TAB','IDD_MP_LAN_HOST_OPTIONS_MAP_TAB',
                    'IDD_CNC_PURCHASE_SCREEN','IDD_CNC_PURCHASE_MAIN_SCREEN']}


def audit(build):
    root=ROOT/'upstream/CnC_Renegade/Code/Commando'
    ids=macros((root/'resource.h',root/'dialogresource.h'))
    text=(build/'generated/renegade_dialog_templates.inc').read_text()
    present={int(n) for n in re.findall(r'static const unsigned char kDialog(\d+)\[\]',text)}
    result=[]
    for area,names in ROUTES.items():
        for name in names:
            if name not in ids:
                raise ValueError('unknown original resource '+name)
            result.append({'area':area,'name':name,'id':ids[name],
                           'selected_by_full_port_generator':ids[name] in CAMPAIGN_IDS|MULTIPLAYER_IDS,
                           'present_in_existing_generated_templates':ids[name] in present})
    return {'schema':1,'generated_template_count':len(present),'routes':result,
            'limits':['Template presence alone does not establish factory routing or display.',
                      'Missing desktop/provider dialogs require scope review, not blind inclusion.']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=audit(a.build);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({'templates':r['generated_template_count'],
                      'checked':len(r['routes']),'absent':[x['name'] for x in r['routes'] if not x['present_in_existing_generated_templates']]},indent=2))
