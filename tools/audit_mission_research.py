#!/usr/bin/env python3
"""Reconcile the supplied mission overview's source-owner and count claims.

This is a source review, not execution or an asset/mission-completion proof.
All supplied sections have an explicit review record; unverified claims remain
open rather than inheriting a passing source-manifest status.
"""
from __future__ import annotations

import argparse
from collections import Counter
import fnmatch
import hashlib
import json
from pathlib import Path

from tools.audit_campaign_source_surface import MISSIONS, COMMAND_CALL, audit
from tools.check_m13_script_coverage import without_comments

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = {
    'script_runtime': ['Combat/scripts.cpp', 'Combat/scriptcommands.cpp', 'Combat/scriptzone.cpp',
                       'Scripts/ScriptRegistrar.cpp', 'Scripts/ScriptFactory.cpp', 'Scripts/DLLmain.cpp'],
    'shared_scripts': ['Scripts/Toolkit*.cpp', 'Scripts/scripts.cpp', 'Scripts/Test_Cinematic.cpp'],
    'innate_behavior': ['Combat/soldierobserver.cpp', 'Combat/soldier.cpp', 'Combat/smartgameobj.cpp'],
    'scripted_actions': ['Combat/action.cpp', 'Combat/pathaction.cpp', 'Combat/vehicledriver.cpp'],
    'pathfinding': ['wwphys/Pathfind.cpp', 'wwphys/Path.cpp', 'wwphys/PathObject.cpp', 'wwphys/PathfindPortal.cpp'],
    'conversation_voice': ['Combat/conversationmgr.cpp', 'Combat/activeconversation.cpp',
                           'Combat/conversation.cpp', 'Combat/viseme.cpp'],
    'cinematics': ['Scripts/Test_Cinematic.cpp', 'Combat/cinematicgameobj.cpp', 'Combat/ccamera.cpp'],
    'bosses': ['Combat/sakurabossgameobj.cpp', 'Combat/mendozabossgameobj.cpp', 'Combat/raveshawbossgameobj.cpp'],
    'objectives_hud_radar': ['Combat/objectives.cpp', 'Combat/hud.cpp', 'Combat/radar.cpp', 'Combat/encyclopediamgr.cpp'],
    'buildings_defenses': ['Combat/building*.cpp', 'Combat/airstripgameobj.cpp', 'Combat/vehiclefactorygameobj.cpp',
                           'Combat/harvester.cpp', 'Combat/beacongameobj.cpp'],
    'weapons_damage': ['Combat/weapons.cpp', 'Combat/weaponmanager.cpp', 'Combat/bullet.cpp',
                       'Combat/explosion.cpp', 'Combat/damage.cpp', 'Combat/c4.cpp'],
    'renderer': ['ww3d2/dx8wrapper.cpp', 'ww3d2/dx8renderer.cpp', 'ww3d2/dx8texman.cpp',
                 'ww3d2/*vertexbuffer*.cpp', 'ww3d2/*indexbuffer*.cpp'],
    'audio': ['WWAudio/Sound3D.cpp', 'WWAudio/sound2dhandle.cpp', 'WWAudio/AudibleSound.cpp'],
    'movies': ['BinkMovie/*', 'Commando/movie.cpp'],
    'weather': ['Combat/scriptcommands.cpp', 'Combat/weathermgr.cpp', 'Combat/backgroundmgr.cpp'],
    'platform': ['Combat/directinput.cpp', 'Commando/WINMAIN.CPP', 'wwlib/thread.cpp', 'wwlib/wwfile.cpp'],
}
EXTRA_FILES = ['Scripts/Mission12.h', 'Scripts/MissionDemo.cpp', 'Scripts/MissionS04.cpp',
               'Scripts/PRDemo.cpp', 'Scripts/DrMobius.cpp', 'Scripts/Common.cpp', 'Scripts/Group.cpp',
               'Scripts/GroupControl.cpp', 'Scripts/GroupScript.cpp', 'Scripts/unitcombat.cpp',
               'Scripts/Test_DEL.cpp', 'Scripts/Test_DLS_M03.cpp', 'Scripts/Scripts.dsp']
TOP_CALLS = {'Find_Object': 3478, 'Send_Custom_Event': 2991, 'Create_Object': 872,
             'Attach_Script': 732, 'Join_Conversation': 712, 'Action_Goto': 661, 'Start_Timer': 614,
             'Debug_Message': 150}
ASSETS = ('level_geometry_ids_pathfind_vis', 'object_presets', 'models_animations', 'textures_objective_images',
          'cinematic_controls', 'conversations_voice', 'sound_effects_logical_sounds', 'music',
          'text_subtitles', 'campaign_movies')
RECOMMENDATIONS = ('static_dsp_manifest', 'original_script_commands', 'object_ids_chunked_saves',
                   'innate_actions_pathfinding_hibernation', 'conversations_cinematic_parser',
                   'audio_and_logical_stimuli', 'renderer_fog_stealth_beams', 'controls_hud_touch',
                   'boss_classes', 'movie_provider_campaign_data', 'difficulty_playthroughs')
CAVEATS = ('retail_and_sdk_absence', 'lower_bound_counts', 'm13_identity', 'damage_parameter_typo',
           'serialized_misspellings', 'stricmp_parameters_case', 'inline_assembly_and_float_behavior',
           'debug_messages', 'licensing_data_separation')
PERFORMANCE = ('mission05_town_square', 'mission10_open_base', 'mission06_collapse', 'mission08_canyon')


def owners(patterns, files):
    rows = []
    for pattern in patterns:
        matches = sorted(path for path in files if fnmatch.fnmatchcase(path.lower(), pattern.lower()))
        rows.append({'reference': pattern, 'canonical_source_paths': matches,
                     'status': 'source_located' if matches else 'source_not_located',
                     'runtime_verified': False})
    return rows


def review(root=ROOT):
    root = Path(root)
    code = root / 'upstream/CnC_Renegade/Code'
    files = {path.relative_to(code).as_posix(): path for path in code.rglob('*') if path.is_file()}
    manifest = audit(root)
    counts = Counter()
    for _, name, _ in MISSIONS:
        counts.update(COMMAND_CALL.findall(without_comments((code / 'Scripts' / name).read_text(encoding='latin1'))))
    metrics = [{'command': name, 'supplied_count': expected, 'current_parser_count': counts[name],
                'status': 'matches' if counts[name] == expected else 'count_discrepancy_open'}
               for name, expected in TOP_CALLS.items()]
    systems = [{'id': name, 'owners': owners(patterns, files), 'runtime_verified': False}
               for name, patterns in SYSTEMS.items()]
    def section(name, items):
        return {'section': name, 'review_items': [{'id': item, 'accounted_for_in_review_scope': True,
                                                  'runtime_or_complete_content_verified': False} for item in items]}
    return {
        'schema_version': 1, 'evidence_class': 'supplied overview reconciled with original source',
        'systems': systems, 'mission_sections': manifest['missions'], 'other_source_files': owners(EXTRA_FILES, files),
        'source_call_counts': metrics,
        'overview_sections': [section('overview_architecture', ('mission_logic_vs_retail_data', 'static_provider',
                                                             'numeric_object_ids', 'campaign_ini_order')),
                              section('campaign_asset_inventory', ASSETS), section('port_checklist', RECOMMENDATIONS),
                              section('profile_priorities', PERFORMANCE), section('gaps_caveats', CAVEATS)],
        'source_inventory': {name: manifest[name] for name in (
            'campaign_mission_source_count', 'campaign_source_lines', 'declared_script_count',
            'distinct_script_command_methods_used', 'script_command_table_entries',
            'original_dsp_source_count', 'static_original_dsp_source_count', 'cpp_source_names_outside_dsp',
            'static_source_gate_passed')},
        'source_hashes': {path: hashlib.sha256(files[path].read_bytes()).hexdigest()
                          for row in systems for owner in row['owners'] for path in owner['canonical_source_paths']},
        'uncertified_inventory_counts': {'conversations': 436, 'string_ids': 367, 'objective_images': 101,
                                         'preset_names': 119, 'sound_names': 104, 'inline_assembly_files': 34},
        'runtime_or_physical_acceptance': False, 'complete_mission_closure': False,
        'limits': ['Every supplied section has a review record; this is not certification of every numeric or semantic claim.',
                   'Source owners, names and declarations do not establish compilation, registration, behavior or hardware correctness.',
                   'Per-mission beats, dynamic names and asset links need authored-data and runtime evidence, especially beyond Tutorial/M13/M01.',
                   'Counts from different parsers are not silently normalized; unresolved differences remain open.',
                   'Performance and presentation suggestions require measured correctness/visual evidence before adoption.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = review(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    missing = [owner['reference'] for row in result['systems'] for owner in row['owners']
               if owner['status'] != 'source_located']
    print(json.dumps({'systems': len(result['systems']), 'missions': len(result['mission_sections']),
                      'unlocated_owner_references': missing,
                      'count_discrepancies': [row for row in result['source_call_counts'] if row['status'] != 'matches'],
                      'runtime_verified': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
