"""TUT-R1 AI_PATHFIND_COST (RVPF1): unghosted soldier personal-space probe skip.

Pure-Python contract and equivalence checks; nothing here compiles C++.

SoldierGameObj::Think (staging/combat/soldier.cpp) runs, for every awake
soldier every frame,

    if (Is_Unit_In_Zone(pos)) Enable_Ghost_Collision(true);
    else if (Is_Safe_To_Disable_Ghost_Collision(pos)) Enable_Ghost_Collision(false);

Enable_Ghost_Collision(false) returns at once unless the soldier is in
SOLDIER_GHOST_COLLISION_GROUP, so the Collect_Objects probe is wasted for an
unghosted soldier. RVPF1 bit 0 skips the probe exactly then. These tests pin
the facts that make the skip state-identical.
"""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH_NAME = 'combat-tut1-pathfind-cost.patch'
PATCH = ROOT / 'port/patches' / PATCH_NAME
SOLDIER = ROOT / 'staging/combat/soldier.cpp'
SOLDIER_H = ROOT / 'staging/combat/soldier.h'
HEADER = ROOT / 'port/compatibility/include/renegade_vita_pathfind_cost.h'
STAGE = ROOT / 'tools/stage_sources.sh'
GHOST_TEST = 'Peek_Physical_Object ()->Get_Collision_Group() == SOLDIER_GHOST_COLLISION_GROUP'

DEFINITION = re.compile(
    r'^(?:[A-Za-z_][\w<>,:\s\*&]*?\s+|)(?P<name>[A-Za-z_]\w*::~?[A-Za-z_]\w*)\s*\(', re.M)


def function_bodies(text):
    """(qualified name, full text) for each out-of-line member definition."""
    bodies = []
    for match in DEFINITION.finditer(text):
        brace = text.find('{', match.end())
        semicolon = text.find(';', match.end())
        if brace < 0 or (0 <= semicolon < brace):
            continue  # declaration, not a definition
        depth = 0
        index = brace
        while index < len(text):
            if text[index] == '{':
                depth += 1
            elif text[index] == '}':
                depth -= 1
                if depth == 0:
                    break
            index += 1
        bodies.append((match.group('name'), text[match.start():index + 1]))
    return bodies


def body_of(text, name):
    matches = [body for found, body in function_bodies(text) if found == name]
    if len(matches) != 1:
        raise AssertionError('%s: %d definitions' % (name, len(matches)))
    return matches[0]


def strip_comments(text):
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    return re.sub(r'//[^\n]*', '', text)


def parse_flag(value):
    """Python mirror of Renegade_Vita_Pathfind_Cost_Parse."""
    if len(value) != 8 or not value.startswith(b'RVPF1 ') or value[7:8] != b'\n':
        return -1
    digit = value[6:7].decode('latin-1')
    if digit not in '0123456789abcdefABCDEF':
        return -1
    return int(digit, 16) & 1


class PatchRegistrationTests(unittest.TestCase):
    def test_registered_once_after_last_combat_patch(self):
        stage = STAGE.read_text()
        lines = [line for line in stage.splitlines() if PATCH_NAME in line]
        self.assertEqual(len(lines), 1)
        self.assertIn('-d "$rv_stage/combat" -p1 <', lines[0])
        self.assertGreater(stage.index(PATCH_NAME),
                           stage.index('combat-a37-face-action-stale-end-time-clamp.patch'))
        command = stage[:stage.index(PATCH_NAME)].rsplit('patch --batch', 1)[1]
        for flag in ('--forward', '--fuzz=0', '--no-backup-if-mismatch'):
            self.assertIn(flag, command)

    def test_patch_reproduces_tracked_staging_at_zero_fuzz(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            shutil.copy(SOLDIER, work / 'soldier.cpp')
            subprocess.run(['patch', '--batch', '-R', '--fuzz=0', '--no-backup-if-mismatch',
                            '-p1', '-d', str(work), '-i', str(PATCH)],
                           check=True, capture_output=True, text=True)
            pre_image = (work / 'soldier.cpp').read_text()
            self.assertNotIn('renegade_vita_pathfind_cost.h', pre_image)
            subprocess.run(['patch', '--batch', '--forward', '--fuzz=0',
                            '--no-backup-if-mismatch', '-p1', '-d', str(work),
                            '-i', str(PATCH)], check=True, capture_output=True, text=True)
            self.assertEqual((work / 'soldier.cpp').read_bytes(), SOLDIER.read_bytes())
            self.assertEqual(sorted(p.name for p in work.iterdir()), ['soldier.cpp'])

    def test_patch_touches_only_soldier_cpp_and_is_vita_only(self):
        patch = PATCH.read_text()
        self.assertEqual(re.findall(r'^\+\+\+ (\S+)', patch, re.M), ['b/soldier.cpp'])
        added = [line[1:] for line in patch.splitlines()
                 if line.startswith('+') and not line.startswith('+++')]
        self.assertEqual(added[0], '#if defined(__vita__)')
        self.assertEqual(sum(1 for line in added if line == '#if defined(__vita__)'), 2)
        self.assertEqual(sum(1 for line in added if line == '#endif'), 2)
        self.assertFalse(re.search(r'^-(?!--)', patch, re.M), 'patch removes original lines')


class HeaderContractTests(unittest.TestCase):
    def setUp(self):
        self.header = HEADER.read_text()

    def test_flag_file_prefix_and_default(self):
        self.assertIn('"ux0:data/renegade/user/config/pathfind-cost-v1.flag"', self.header)
        self.assertIn('memcmp(value, "RVPF1 ", 6U)', self.header)
        self.assertIn('size != 8U', self.header)
        self.assertIn("value[7] != '\\n'", self.header)
        self.assertRegex(self.header, r'RENEGADE_VITA_PATHFIND_COST_DEFAULT = 1U')
        self.assertRegex(self.header, r'RENEGADE_VITA_PATHFIND_COST_KNOWN_BITS = 1U')
        self.assertRegex(self.header, r'RENEGADE_VITA_PATHFIND_COST_SKIP_UNGHOSTED_PROBE = 1U')
        configure = self.header[self.header.index('inline void Renegade_Vita_Pathfind_Cost_Configure'):]
        self.assertLess(configure.index('state.mask = RENEGADE_VITA_PATHFIND_COST_DEFAULT;'),
                        configure.index('fopen('))

    def test_parse_model(self):
        cases = {b'RVPF1 0\n': 0, b'RVPF1 1\n': 1, b'RVPF1 f\n': 1, b'RVPF1 E\n': 0,
                 b'RVPF1 1': -1, b'RVPF1 1\r\n': -1, b'RVPF2 1\n': -1, b'RVPF1 g\n': -1,
                 b'rvpf1 1\n': -1, b'': -1}
        for value, expected in cases.items():
            self.assertEqual(parse_flag(value), expected, value)

    def test_state_is_constant_initialised_and_census_bounded(self):
        self.assertRegex(self.header,
                         r'static RenegadeVitaPathfindCostState state = \{ 0U, 0U, 0U, 0U, 0U, 0U, false \};')
        self.assertIn('kRenegadeVitaPathfindCostCensusPeriod = 16384U', self.header)
        self.assertRegex(self.header, r'#if defined\(RENEGADE_VITA_M00_DEMO\) && RENEGADE_VITA_M00_DEMO\n'
                         r'(?://[^\n]*\n)*static const unsigned kRenegadeVitaPathfindCostCensusLines = 0U;\n'
                         r'#else\nstatic const unsigned kRenegadeVitaPathfindCostCensusLines = 128U;\n#endif')
        census = self.header[self.header.index('inline void Renegade_Vita_Pathfind_Cost_Census'):]
        census = census[:census.index('\n}\n')]
        self.assertLess(census.index('return;'), census.index('A30_Vita_Log'))
        self.assertIn('state.census_lines >= kRenegadeVitaPathfindCostCensusLines', census)

    def test_skip_requires_unghosted_and_bit0(self):
        skip = self.header[self.header.index('inline bool Renegade_Vita_Pathfind_Cost_Skip_Probe'):]
        skip = skip[:skip.index('\n}\n')]
        self.assertIn('const bool skip = !ghosted &&', skip)
        self.assertIn('(state.mask & RENEGADE_VITA_PATHFIND_COST_SKIP_UNGHOSTED_PROBE) != 0U;', skip)
        self.assertIn('return skip;', skip)


class EquivalenceTests(unittest.TestCase):
    def setUp(self):
        self.soldier = SOLDIER.read_text()

    def test_guard_matches_enable_ghost_collision_noop_condition(self):
        think = body_of(self.soldier, 'SoldierGameObj::Think')
        block = think[think.index('WWPROFILE("Coordination Zone");'):]
        block = block[:block.index('WWPROFILE("Add_Debug_AABox")')]
        self.assertIn('Renegade_Vita_Pathfind_Cost_Skip_Probe(\n\t\t\t\t\t' + GHOST_TEST + ' ) ) {', block)
        # The skip branch runs nothing; the original probe branch follows it.
        opening = block.index(GHOST_TEST + ' ) ) {') + len(GHOST_TEST + ' ) ) {')
        skip_branch = block[opening:block.index('#endif')]
        self.assertEqual(re.findall(r'\w+\s*\(', strip_comments(skip_branch)), [])
        self.assertLess(block.index('#endif'),
                        block.index('} else if ( Is_Safe_To_Disable_Ghost_Collision( position ) ) {'))
        self.assertIn('Enable_Ghost_Collision( false );', block)
        enable = body_of(self.soldier, 'SoldierGameObj::Enable_Ghost_Collision')
        self.assertIn('bool is_using_ghost_collision = (' + GHOST_TEST + ');', enable)
        self.assertRegex(enable, r'if \( onoff == is_using_ghost_collision \) \{\s*return ;\s*\}')
        self.assertLess(enable.index('return ;'), enable.index('Set_Collision_Group'))

    def test_physical_object_already_dereferenced_before_guard(self):
        think = body_of(self.soldier, 'SoldierGameObj::Think')
        block = think[think.index('WWPROFILE("Coordination Zone");'):]
        self.assertLess(block.index('Get_Position( &position );'), block.index(GHOST_TEST))
        position = body_of((ROOT / 'staging/combat/physicalgameobj.cpp').read_text(),
                           'PhysicalGameObj::Get_Position')
        self.assertIn('Peek_Physical_Object()->Get_Position(set_pos);', position)

    def test_probe_and_enable_are_non_virtual_and_probe_has_one_caller(self):
        header = SOLDIER_H.read_text()
        for name in ('Enable_Ghost_Collision', 'Is_Safe_To_Disable_Ghost_Collision'):
            declaration = [line for line in header.splitlines() if name + '(' in line]
            self.assertEqual(len(declaration), 1, name)
            self.assertNotIn('virtual', declaration[0])
        callers = []
        for path in list((ROOT / 'staging').rglob('*.cpp')) + list((ROOT / 'staging').rglob('*.h')):
            text = path.read_text(errors='replace')
            callers += [path.name for _ in re.finditer(r'Is_Safe_To_Disable_Ghost_Collision\s*\(\s*position', text)]
        self.assertEqual(callers, ['soldier.cpp'])

    def test_probe_body_calls_only_readers_and_its_scratch_list(self):
        probe = strip_comments(body_of(self.soldier, 'SoldierGameObj::Is_Safe_To_Disable_Ghost_Collision'))
        body = probe[probe.index('{') + 1:]
        calls = set(re.findall(r'([A-Za-z_]\w*)\s*\(', body))
        # Local constructors (Vector3, AABoxClass box/block_box, list, iterator) and readers.
        allowed = {'Vector3', 'PERSONAL_SPACE_BOX_SIZE', 'box', 'obj_list', 'it', 'block_box',
                   'Get_Instance', 'Collect_Objects',
                   'First', 'Is_Done', 'Next', 'Peek_Obj', 'As_HumanPhysClass', 'Get_Observer',
                   'As_PhysicalGameObj', 'As_SoldierGameObj', 'Is_Destroyed', 'Get_Position',
                   'Overlap_Test', 'if', 'for'}
        self.assertLessEqual(calls, allowed, sorted(calls - allowed))
        self.assertIn('Collect_Objects (box, false, true, &obj_list);', body)
        self.assertNotRegex(body, r'\b(?:delete|new)\b')

    def test_dynamic_collection_readers_reset_first(self):
        # PhysicsSceneClass::DynamicCullingSystem is the one PhysGridCullClass.
        scene = (ROOT / 'staging/wwphys/pscene.cpp').read_text()
        self.assertEqual(re.findall(r'DynamicCullingSystem\s*=\s*new\s+(\w+)', scene),
                         ['PhysGridCullClass'])
        readers = sorted(path.relative_to(ROOT).as_posix()
                         for path in (ROOT / 'staging').rglob('*')
                         if path.suffix in ('.cpp', '.h') and
                         'Get_First_Collected_Object' in path.read_text(errors='replace'))
        self.assertEqual(readers, [
            'staging/wwaudio/SoundScene.cpp', 'staging/wwmath/aabtreecull.h',
            'staging/wwmath/cullsys.cpp', 'staging/wwmath/cullsys.h',
            'staging/wwmath/gridcull.cpp', 'staging/wwmath/gridcull.h',
            'staging/wwphys/Pathfind.cpp', 'staging/wwphys/PathfindSectorBuilder.cpp',
            'staging/wwphys/dynamicaabtreecull.cpp', 'staging/wwphys/physaabtreecull.cpp',
            'staging/wwphys/physgridcull.cpp', 'staging/wwphys/pscene_collision.cpp',
            'staging/wwphys/pscene_lighting.cpp', 'staging/wwphys/pscene_projectors.cpp',
            'staging/wwphys/staticaabtreecull.cpp'])
        # Files whose code can read the PhysGridCullClass collection.
        helpers = {'PhysicsSceneClass::Add_Collected_Objects_To_List',
                   'PhysicsSceneClass::Add_Collected_Collideable_Objects_To_List',
                   'PhysicsSceneClass::Add_Collected_Lights_To_List'}
        accessor = 'CullSystemClass::Get_First_Collected_Object_Internal'
        gridcull = (ROOT / 'staging/wwmath/gridcull.cpp').read_text()
        unlink = body_of(gridcull, 'GridCullSystemClass::Collect_And_Unlink_All')
        self.assertLess(unlink.index('Reset_Collection();'), unlink.index('Add_To_Collection'))
        seen = set()
        for relative in ('staging/wwphys/pscene_collision.cpp', 'staging/wwphys/pscene_projectors.cpp',
                         'staging/wwphys/pscene_lighting.cpp', 'staging/wwphys/physgridcull.cpp',
                         'staging/wwmath/gridcull.cpp', 'staging/wwmath/cullsys.cpp'):
            for name, body in function_bodies((ROOT / relative).read_text()):
                code = strip_comments(body)
                for helper in helpers:
                    short = helper.split('::')[1]
                    if name != helper and short + '(' in code:
                        reset = code.find('Reset_Collection')
                        self.assertTrue(0 <= reset < code.index(short + '('), (name, short))
                if 'Get_First_Collected_Object' not in code or name in helpers | {accessor}:
                    seen.add(name)
                    continue
                read = code.index('Get_First_Collected_Object')
                reset = min([i for i in (code.find('Reset_Collection'),
                                         code.find('Collect_And_Unlink_All')) if i >= 0] or [len(code)])
                self.assertLess(reset, read, (relative, name))
                seen.add(name)
        self.assertLessEqual(helpers, seen)

    def test_gridcull_statistics_compiled_out(self):
        # GRIDCULL_NODE_* only bump debug Stats under WWDEBUG; the build never defines it.
        self.assertNotIn('WWDEBUG', (ROOT / 'CMakeLists.txt').read_text())
        gridcull_h = (ROOT / 'staging/wwmath/gridcull.h').read_text()
        self.assertRegex(gridcull_h, r'#ifdef WWDEBUG\s+#define GRIDCULL_NODE_ACCEPTED')


class ControlFlowModelTests(unittest.TestCase):
    """Exhaustive model of the original and RVPF1 branch structure."""

    @staticmethod
    def original(in_zone, group, safe):
        probes = 0
        if in_zone:
            group = 'ghost'
        else:
            probes += 1
            if safe and group == 'ghost':
                group = 'soldier'
        return group, probes

    @staticmethod
    def patched(in_zone, group, safe, mask):
        probes = 0
        if in_zone:
            group = 'ghost'
        elif not (group == 'ghost') and (mask & 1):
            pass
        else:
            probes += 1
            if safe and group == 'ghost':
                group = 'soldier'
        return group, probes

    def test_final_collision_group_identical_for_every_state(self):
        for in_zone in (False, True):
            for group in ('soldier', 'ghost', 'other'):
                for safe in (False, True):
                    for mask in (0, 1):
                        before = self.original(in_zone, group, safe)
                        after = self.patched(in_zone, group, safe, mask)
                        self.assertEqual(after[0], before[0], (in_zone, group, safe, mask))
                        if mask == 0 or group == 'ghost' or in_zone:
                            self.assertEqual(after[1], before[1])
                        else:
                            self.assertEqual(after[1], 0)


if __name__ == '__main__':
    unittest.main()
