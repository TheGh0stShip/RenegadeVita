#!/usr/bin/env python3
"""Conversation-gated objective audit (static, read-only, deterministic).

For M13 and M01..M11 this finds every mission-script gate of the shape

    Create_Conversation -> Start_Conversation(id, ACTION) -> Monitor_Conversation(obj, id)

whose completion handler (`Action_Complete`, matched on ACTION) completes an
objective, adds an objective, sends a progression custom event or calls
`Mission_Complete`.

Why it matters (ActiveConversationClass::Start_Conversation): a conversation that
is not flagged `ConversationClass::VARID_ISKEY` is stopped before it starts when a
key conversation is already in the active list.  The script's later
`Monitor_Conversation` registers on a finished conversation, so
`Notify_Monitors_On_End` never reaches it and the gated effect is never produced.
Retail behaves the same, so a non-key gate is a retail-identical hazard rather than
a port defect, but it can strand a primary objective.

Inputs
* staged scripts (`staging/scripts`, the patched sources compiled for the Vita) or
  any `--scripts` directory;
* optional retail Data directory: level `.ldd/.lsd` conversation records and the
  global `conv10.cdb`, read only for names and the is-key flag (VARID_ISKEY = 13).
  No dialogue text or audio is read or emitted.

The analysis is syntactic (see LIMITS).  Conditions on the handler's `action_id`,
`reason`, and on custom-event `type`/`param` are evaluated with a three-valued
evaluator; unknown (state) conditions are kept as guards.

Classification
* SAFE (key)       every candidate conversation is a key conversation;
* SAFE (alt path)  non-key, but every progression terminal also has an
                   independent emitter (ungated, or gated by a key conversation);
* AT RISK          non-key and a primary objective completion/addition or
                   `Mission_Complete(true)` has no independent emitter;
* REVIEW           non-key; sole emitter of a custom whose receiver did not
                   resolve, or an objective of unknown type;
* LOW              non-key; gates only secondary/tertiary objectives, failure, or
                   non-progression effects;
* NO EFFECT        handler found but no progression effect;
* NAME MISSING     conversation name resolves in neither the level nor the global
                   database, so `Create_Conversation` returns -1 (never fires).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct

from tools.audit_campaign_script_closure import (
    DEFAULT_DATA, MISSION_OWNERS, find_calls, include_closure, literal_text, scan_registrations)
from tools.audit_deep_saved_content import conversations
from tools.audit_m13_level_owners import chunks, microchunks
from tools.audit_mission_content_bindings import ROOT, masked
from tools.audit_mission_event_routes import numeric_constants
from tools.audit_mission_text_routes import constant_id
from tools.renegade_cinematic_dependency_scan import MixArchive

SCOPE = ['M13'] + ['M%02d' % n for n in range(1, 12)]
OWNER_BY_MISSION = {mission: owner for owner, mission in MISSION_OWNERS.items()}
VARID_PRIORITY, VARID_INTERRUPTABLE, VARID_ISKEY = 10, 12, 13
CLASSES = ('AT RISK', 'FIXED', 'REVIEW', 'LOW', 'SAFE (key)', 'SAFE (alt path)', 'NO EFFECT', 'NAME MISSING')
BUILTIN_CONSTANTS = {
    'OBJECTIVE_TYPE_PRIMARY': 1, 'OBJECTIVE_TYPE_SECONDARY': 2, 'OBJECTIVE_TYPE_TERTIARY': 3,
    'OBJECTIVE_STATUS_PENDING': 0, 'OBJECTIVE_STATUS_ACCOMPLISHED': 1,
    'OBJECTIVE_STATUS_FAILED': 2, 'OBJECTIVE_STATUS_HIDDEN': 3, 'true': 1, 'false': 0, 'TRUE': 1, 'FALSE': 0}
TYPE_NAMES = {1: 'primary', 2: 'secondary', 3: 'tertiary'}
STATUS_NAMES = {0: 'PENDING', 1: 'ACCOMPLISHED', 2: 'FAILED', 3: 'HIDDEN'}
EFFECT_COMMANDS = ('Set_Objective_Status', 'Mission_Complete', 'Send_Custom_Event', 'Add_Objective', 'Start_Timer')
TERMINAL_KINDS = ('objective_status', 'mission_complete', 'add_objective')
REASONS = ('ACTION_COMPLETE_CONVERSATION_ENDED', 'ACTION_COMPLETE_CONVERSATION_INTERRUPTED',
           'ACTION_COMPLETE_CONVERSATION_UNABLE_TO_INIT')
KEYWORDS = {'if', 'for', 'while', 'switch', 'return', 'sizeof', 'else', 'do', 'case', 'default', 'new', 'delete'}
EVENT_FUNCTIONS = {'Created', 'Killed', 'Custom', 'Action_Complete', 'Timer_Expired', 'Poked', 'Entered', 'Exited',
                   'Damaged', 'Enemy_Seen', 'Animation_Complete', 'Sound_Heard', 'Destroyed', 'Register_Auto_Save_Variables'}
UNKNOWN = object()


# --------------------------------------------------------------------------
# Conversation database (names, ids and flags only)
# --------------------------------------------------------------------------

def conversation_flags(payload, rows):
    """Add priority/is_key to `conversations()` rows (original ConversationClass VARIDs 10/13)."""
    result = []
    for row in rows:
        kind, size = struct.unpack_from('<II', payload, row['offset'])
        body = payload[row['offset'] + 8:row['offset'] + 8 + (size & 0x7fffffff)]
        identity = [n for n in chunks(body) if n.kind == 0x08090316]
        fields = dict(microchunks(identity[0].data)) if identity else {}
        flag = fields.get(VARID_ISKEY)
        result.append({'name': row['name'], 'id': row['id'], 'category': row['category'],
                       'is_key': None if not flag else bool(flag[0]),
                       'priority': int.from_bytes(fields[VARID_PRIORITY], 'little') if VARID_PRIORITY in fields else None,
                       'remarks': row['remark_count']})
    return result


def load_conversation_db(data, map_name):
    """{'level': {lower_name: row}, 'global': {...}, 'sources': [...]} from retail archives; read-only."""
    level, global_rows, sources = {}, {}, []
    mission = MixArchive(data / (map_name + '.mix'))
    for member in sorted(mission.entries):
        if member.endswith(('.ldd', '.lsd')):
            payload = mission.read_binary(member)
            for row in conversation_flags(payload, conversations(chunks(payload), allow_legacy_category=False)):
                level.setdefault(row['name'].lower(), {**row, 'source': f'{map_name}.mix:{member}'})
            sources.append(f'{map_name}.mix:{member}')
    for path in sorted(data.iterdir()):
        if path.name.lower().startswith('always') and path.suffix.lower() in ('.dat', '.dbs', '.mix'):
            archive = MixArchive(path)
            if 'conv10.cdb' in archive.entries:
                payload = archive.read_binary('conv10.cdb')
                for row in conversation_flags(payload, conversations(chunks(payload), allow_legacy_category=False)):
                    global_rows.setdefault(row['name'].lower(), {**row, 'source': f'{path.name}:conv10.cdb'})
                sources.append(f'{path.name}:conv10.cdb')
    return {'level': level, 'global': global_rows, 'sources': sources}


def lookup(db, name):
    return db['level'].get(name.lower()) or db['global'].get(name.lower())


# --------------------------------------------------------------------------
# Tiny C++ statement parser over masked code (strings/comments blanked)
# --------------------------------------------------------------------------

def is_word(code, i, word):
    j = i + len(word)
    return (code.startswith(word, i) and (j >= len(code) or not (code[j].isalnum() or code[j] == '_'))
            and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] == '_')))


def skip_ws(code, i):
    while i < len(code) and code[i].isspace():
        i += 1
    return i


def match_close(code, i, open_char, close_char):
    depth = 0
    for j in range(i, len(code)):
        if code[j] == open_char:
            depth += 1
        elif code[j] == close_char:
            depth -= 1
            if depth == 0:
                return j
    return len(code) - 1


def statement_end(code, i, end):
    depth = 0
    for j in range(i, end):
        if code[j] in '([{':
            depth += 1
        elif code[j] in ')]}':
            depth -= 1
        elif code[j] == ';' and depth <= 0:
            return j + 1
    return end


LABEL = re.compile(r'(case\s+([^:;]+?)|default)\s*:(?!:)')


def switch_segments(code, start, end):
    """[(labels, seg_start, seg_end)]; consecutive labels merge (fall-through)."""
    marks, depth, i = [], 0, start
    while i < end:
        char = code[i]
        if char in '({[':
            depth += 1
        elif char in ')}]':
            depth -= 1
        elif depth == 0 and (is_word(code, i, 'case') or is_word(code, i, 'default')):
            match = LABEL.match(code, i)
            if match:
                marks.append((match[2].strip() if match[2] else None, i, match.end()))
                i = match.end()
                continue
        i += 1
    segments, labels = [], []
    for index, (label, _, label_end) in enumerate(marks):
        labels.append(label)
        seg_end = marks[index + 1][1] if index + 1 < len(marks) else end
        if code[label_end:seg_end].strip():
            segments.append((labels, label_end, seg_end))
            labels = []
    return segments


def parse_statements(code, i, end, conds, out):
    while True:
        i = skip_ws(code, i)
        if i >= end:
            return
        i = parse_statement(code, i, end, conds, out)


def parse_statement(code, i, end, conds, out):
    """Appends (start, end, conds) leaves; conds = ((condition_text, negated), ...)."""
    char = code[i]
    if char == '{':
        close = match_close(code, i, '{', '}')
        parse_statements(code, i + 1, close, conds, out)
        return close + 1
    if char == ';':
        return i + 1
    if is_word(code, i, 'if') and code.find('(', i) >= 0:
        open_paren = code.find('(', i)
        close = match_close(code, open_paren, '(', ')')
        cond = code[open_paren + 1:close]
        after = parse_statement(code, skip_ws(code, close + 1), end, conds + ((cond, False),), out)
        probe = skip_ws(code, after)
        if is_word(code, probe, 'else'):
            return parse_statement(code, skip_ws(code, probe + 4), end, conds + ((cond, True),), out)
        return after
    if is_word(code, i, 'switch') and code.find('(', i) >= 0:
        open_paren = code.find('(', i)
        close = match_close(code, open_paren, '(', ')')
        expr = code[open_paren + 1:close].strip()
        brace = skip_ws(code, close + 1)
        if brace < end and code[brace] == '{':
            body_end = match_close(code, brace, '{', '}')
            for labels, seg_start, seg_end in switch_segments(code, brace + 1, body_end):
                named = [label for label in labels if label is not None]
                cond = ' || '.join(f'{expr} == {label}' for label in named)
                parse_statements(code, seg_start, seg_end, conds + (((cond or '1'), False),), out)
            return body_end + 1
    if (is_word(code, i, 'for') or is_word(code, i, 'while')) and code.find('(', i) >= 0:
        open_paren = code.find('(', i)
        close = match_close(code, open_paren, '(', ')')
        return parse_statement(code, skip_ws(code, close + 1), end, conds + (('loop', False),), out)
    if is_word(code, i, 'do'):
        after = parse_statement(code, skip_ws(code, i + 2), end, conds + (('loop', False),), out)
        return statement_end(code, skip_ws(code, after), end)
    stop = statement_end(code, i, end)
    out.append((i, stop, conds))
    return stop


def split_top(text, operator):
    if operator not in text:
        return [text]
    parts, depth, last, i = [], 0, 0, 0
    while i < len(text):
        if text[i] in '([{':
            depth += 1
        elif text[i] in ')]}':
            depth -= 1
        elif depth == 0 and text.startswith(operator, i):
            parts.append(text[last:i])
            last = i + len(operator)
            i += len(operator) - 1
        i += 1
    parts.append(text[last:])
    return parts


def strip_parens(text):
    text = text.strip()
    while text.startswith('(') and match_close(text, 0, '(', ')') == len(text) - 1:
        text = text[1:-1].strip()
    return text


COMPARISON = re.compile(r'(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+)', re.S)
ENUM_NAME = re.compile(r'ACTION_COMPLETE_\w+$')


_CONSTANT_CACHE = {}
_COND_CACHE = {}


def atom_value(text, env, constants):
    text = strip_parens(text)
    if text in env:
        return env[text]
    if ENUM_NAME.match(text):
        return text
    key = (text, id(constants))
    if key not in _CONSTANT_CACHE:
        number = constant_id(text, constants)
        _CONSTANT_CACHE[key] = UNKNOWN if number is None else number
    return _CONSTANT_CACHE[key]


def eval_cond(cond, env, constants):
    """Three-valued C++ condition evaluation: True / False / None (unknown); memoised."""
    names = set(re.findall(r'[A-Za-z_]\w*', cond)) & set(env)
    key = (cond, id(constants), tuple(sorted((name, env[name]) for name in names)))
    if key not in _COND_CACHE:
        _COND_CACHE[key] = _eval_cond(cond, env, constants)
    return _COND_CACHE[key]


def _eval_cond(cond, env, constants):
    cond = strip_parens(cond)
    for operator, short_circuit in (('||', True), ('&&', False)):
        parts = split_top(cond, operator)
        if len(parts) > 1:
            results = [eval_cond(part, env, constants) for part in parts]
            if any(r is short_circuit for r in results):
                return short_circuit
            return (not short_circuit) if all(r is (not short_circuit) for r in results) else None
    if cond.startswith('!') and not cond.startswith('!='):
        inner = eval_cond(cond[1:], env, constants)
        return None if inner is None else not inner
    match = COMPARISON.fullmatch(cond)
    if match:
        left, right = atom_value(match[1], env, constants), atom_value(match[3], env, constants)
        # A symbolic value (an unresolved Start_Conversation action such as `missionEndConv`) equals a
        # condition operand with the same spelling.
        raw_left, raw_right = ' '.join(strip_parens(match[1]).split()), ' '.join(strip_parens(match[3]).split())
        if match[2] in ('==', '!=') and ((isinstance(left, str) and left == raw_right)
                                         or (isinstance(right, str) and right == raw_left)):
            return match[2] == '=='
        if left is UNKNOWN or right is UNKNOWN:
            return None
        try:
            return {'==': left == right, '!=': left != right, '>=': left >= right, '<=': left <= right,
                    '>': left > right, '<': left < right}[match[2]]
        except TypeError:
            return None
    if re.fullmatch(r'\w+', cond) and cond in env and env[cond] is not UNKNOWN:
        return bool(env[cond])
    return None


def mentions(text, names):
    return any(re.search(r'(?<![\w.])' + re.escape(name) + r'\b', text) for name in names if name)


def path_state(conds, env, constants, anchors=()):
    """(passes, guards, anchored): anchored = a condition mentioning one of `anchors` definitely held."""
    guards, anchored = [], False
    for cond, negated in conds:
        if cond in ('loop', '1'):
            continue
        value = eval_cond(cond, env, constants)
        text = ' '.join(cond.split())
        if value is None and not negated:
            # `a == X && state` : the conjuncts are evaluated separately so the decided one can anchor the path.
            conjuncts = split_top(strip_parens(cond), '&&')
            if len(conjuncts) > 1:
                for conjunct in conjuncts:
                    part = eval_cond(conjunct, env, constants)
                    if part is False:
                        return False, guards, anchored
                    if part is None:
                        guards.append(' '.join(strip_parens(conjunct).split()))
                    elif mentions(conjunct, anchors):
                        anchored = True
                continue
        if value is None:
            guards.append(('!(' + text + ')') if negated else text)
            continue
        if negated:
            value = not value
        if not value:
            return False, guards, anchored
        if mentions(cond, anchors):
            anchored = True
    return True, guards, anchored


# --------------------------------------------------------------------------
# Script model
# --------------------------------------------------------------------------

FUNCTION = re.compile(r'\b(?:void|bool|int|float|char\s*\*|const\s+char\s*\*|Vector3|GameObject\s*\*)\s+(\w+)\s*\(([^;{}]*?)\)\s*(?:const\s*)?\{')
MEMBER = re.compile(r'^[ \t]*(?:bool|int|float|unsigned\s+int|short|char)\s+(\w+(?:\s*\[[^\]]*\])?(?:\s*,\s*\w+(?:\s*\[[^\]]*\])?)*)\s*;', re.M)


class Function:
    def __init__(self, name, params, start, end):
        self.name, self.start, self.end = name, start, end
        self.params = []
        for part in params.split(','):
            tokens = re.findall(r'\w+', part)
            self.params.append(tokens[-1] if tokens else '')


class Script:
    def __init__(self, row, constants):
        self.name, self.owner, self.line0 = row['name'], row['owner'], row['line']
        self.src = row['body']
        self.code = masked(self.src, strings=True)
        self.constants = constants
        self.functions = []
        depth_at = self.depth_map()
        for match in FUNCTION.finditer(self.code):
            if depth_at[match.start()] != 1:
                continue
            close = match_close(self.code, match.end() - 1, '{', '}')
            self.functions.append(Function(match[1], match[2], match.end(), close))
        self.members = set()
        for match in MEMBER.finditer(self.code):
            if depth_at[match.start()] == 1:
                self.members.update(re.findall(r'(\w+)(?:\s*\[[^\]]*\])?', match[1]))
        self._leaves = {}
        self._calls = {}

    def depth_map(self):
        depth, result = 0, []
        for char in self.code:
            result.append(depth)
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
        return result

    def line(self, pos):
        return self.line0 + self.src.count('\n', 0, pos)

    def function_at(self, pos):
        for function in self.functions:
            if function.start <= pos < function.end:
                return function
        return None

    def named(self, name):
        return [f for f in self.functions if f.name == name]

    def leaves(self, function):
        key = id(function)
        if key not in self._leaves:
            out = []
            parse_statements(self.code, function.start, function.end, (), out)
            self._leaves[key] = out
        return self._leaves[key]

    def calls(self, start, end, wanted):
        key = (start, end, tuple(wanted))
        if key not in self._calls:
            self._calls[key] = [{**call, 'offset': call['offset'] + start}
                                for call in find_calls(self.src[start:end], self.code[start:end], wanted)]
        return self._calls[key]

    def value(self, expression, env=None):
        text = strip_parens(expression)
        if env and text in env and env[text] is not UNKNOWN:
            return env[text]
        number = constant_id(text, self.constants)
        return number if number is not None else ' '.join(expression.split())


# --------------------------------------------------------------------------
# Gate discovery
# --------------------------------------------------------------------------

def assigned_variable(code, offset):
    start = max(code.rfind(';', 0, offset), code.rfind('{', 0, offset), code.rfind('}', 0, offset)) + 1
    match = re.search(r'(\w+)\s*=\s*$', code[start:offset])
    return match[1] if match else None


def name_candidates(script, function, expression, known):
    """Literal name, else string literals in the function/script that are known conversations."""
    literal = literal_text(expression)
    if literal is not None:
        return [literal], 'literal'
    if not known:
        return [], 'computed (no database)'
    scopes = ([('function', function.start, function.end)] if function else []) + [('script', 0, len(script.src))]
    for label, start, end in scopes:
        names = []
        for token in re.findall(r'"((?:\\.|[^"\\])*)"', script.src[start:end]):
            if token.lower() in known and token not in names:
                names.append(token)
        if names:
            return names, f'computed (candidate literals in {label})'
    return [], 'computed (unresolved)'


def discover_gates(script, known):
    create = sorted(script.calls(0, len(script.src), ('Create_Conversation',)), key=lambda c: c['offset'])
    starts = script.calls(0, len(script.src), ('Start_Conversation',))
    monitors = script.calls(0, len(script.src), ('Monitor_Conversation',))
    gates, orphans = [], []
    for call in create:
        function = script.function_at(call['offset'])
        variable = assigned_variable(script.code, call['offset'])
        if not variable or not call['arguments']:
            continue
        later = [c['offset'] for c in create if c['offset'] > call['offset'] and script.function_at(c['offset']) is function
                 and assigned_variable(script.code, c['offset']) == variable]
        limit = later[0] if later else None

        def belongs(other, position):
            names = other['arguments']
            if len(names) <= position or names[position].strip() != variable:
                return None
            if script.function_at(other['offset']) is function:
                return other['offset'] > call['offset'] and (limit is None or other['offset'] < limit)
            return 'script'

        mine_starts = [c for c in starts if belongs(c, 0) is True] or [c for c in starts if belongs(c, 0) == 'script']
        mine_mon = [c for c in monitors if belongs(c, 1) is True] or [c for c in monitors if belongs(c, 1) == 'script']
        if not mine_starts or not mine_mon:
            if mine_mon or mine_starts:
                orphans.append({'script': script.name, 'line': script.line(call['offset']),
                                'missing': 'start' if not mine_starts else 'monitor'})
            continue
        names, how = name_candidates(script, function, call['arguments'][0], known)
        actions = {script.value(c['arguments'][1]) if len(c['arguments']) > 1 else 0 for c in mine_starts}
        gates.append({
            'script': script, 'create': call, 'function': function,
            'name_expression': ' '.join(call['arguments'][0].split()), 'names': names, 'name_resolution': how,
            'actions': sorted(actions, key=lambda v: (isinstance(v, str), str(v))),
            'start_lines': sorted({script.line(c['offset']) for c in mine_starts}),
            'monitor_lines': sorted({script.line(c['offset']) for c in mine_mon}),
            'monitor_targets': sorted({' '.join(c['arguments'][0].split()) for c in mine_mon if c['arguments']}),
            # Monitor registered before Start: a key-conversation preemption inside Start_Conversation then
            # notifies the monitor synchronously (INTERRUPTED) instead of being lost.
            'monitor_before_start': min(c['offset'] for c in mine_mon) < min(c['offset'] for c in mine_starts)})
    return gates, orphans


# --------------------------------------------------------------------------
# Effects
# --------------------------------------------------------------------------

class Effect(dict):
    pass


def leaf_effects(mission, script, start, end, env, depth=0, seen=()):
    """Progression-relevant calls in one leaf; same-script helpers are inlined with bound arguments."""
    effects = []
    for call in script.calls(start, end, EFFECT_COMMANDS):
        args, line, command = call['arguments'], script.line(call['offset']), call['command']
        value = lambda index: script.value(args[index], env)
        if command == 'Set_Objective_Status' and len(args) >= 2:
            effects.append(Effect(kind='objective_status', objective=value(0), status=value(1), line=line))
        elif command == 'Mission_Complete' and args:
            effects.append(Effect(kind='mission_complete', success=value(0), line=line))
        elif command == 'Add_Objective' and len(args) >= 2:
            effects.append(Effect(kind='add_objective', objective=value(0), objective_type=value(1), line=line))
        elif command == 'Send_Custom_Event' and len(args) >= 3:
            effects.append(Effect(kind='custom', type=value(2), param=value(3) if len(args) > 3 else 0, line=line))
        elif command == 'Start_Timer' and len(args) >= 4:
            effects.append(Effect(kind='timer', timer=value(3), script=script.name, line=line))
    if depth < 3:
        code = script.code[start:end]
        for match in re.finditer(r'(?<![\w>.:])(\w+)\s*\(', code):
            name = match[1]
            if name in KEYWORDS or name in EVENT_FUNCTIONS or name in seen:
                continue
            helpers = [f for f in script.named(name)]
            if not helpers:
                continue
            open_paren = start + match.end() - 1
            close = match_close(script.code, open_paren, '(', ')')
            arguments = [part for part in split_top(script.src[open_paren + 1:close], ',')] if close > open_paren + 1 else []
            for helper in helpers:
                bound = dict(env)
                for index, param in enumerate(helper.params):
                    if index < len(arguments) and param:
                        bound[param] = script.value(arguments[index], env)
                for effect in function_effects(mission, script, helper, bound, depth + 1, seen + (name,)):
                    effects.append(Effect(effect, via=effect.get('via') or f'helper {name}()'))
    return effects


def function_effects(mission, script, function, env, depth=0, seen=(), anchors=(), need_anchor=False):
    effects = []
    for start, end, conds in script.leaves(function):
        passes, guards, anchored = path_state(conds, env, script.constants, anchors)
        if not passes or (need_anchor and not anchored):
            continue
        for effect in leaf_effects(mission, script, start, end, env, depth, seen):
            if guards:
                effect = Effect(effect, guards=sorted(set(effect.get('guards', [])) | set(guards)))
            effects.append(effect)
    return effects


def flag_assignments(script, start, end, env):
    result = []
    code = script.code[start:end]
    for match in re.finditer(r'(?<![\w.>])(\w+)\s*(?:\[[^\]]*\])?\s*=\s*([^=;][^;]*);', code):
        if match[1] in script.members:
            value = script.value(script.src[start + match.start(2):start + match.end(2)], env)
            result.append((match[1], value, script.line(start + match.start())))
    return result


class Mission:
    """All scripts of one mission translation unit plus resolved receiver tables."""

    def __init__(self, name, scripts, db=None, cinematic=None):
        self.name, self.scripts, self.db = name, scripts, db
        self.cinematic = cinematic or []
        self.objective_types = self.collect_objective_types()
        self.cache = {}

    def collect_objective_types(self):
        types = defaultdict(set)
        for script in self.scripts:
            for call in script.calls(0, len(script.src), ('Add_Objective',)):
                args = call['arguments']
                if len(args) >= 2:
                    kind = script.value(args[1])
                    types[script.value(args[0])].add(TYPE_NAMES.get(kind, str(kind)))
        return types

    # -- custom-event receivers --------------------------------------------------
    def receiver_candidates(self):
        """[(script, Custom function, integers mentioned, catch_all)] used to prefilter receivers."""
        if getattr(self, '_receivers', None) is None:
            rows = []
            for script in self.scripts:
                for function in script.named('Custom'):
                    if len(function.params) < 3:
                        continue
                    code = script.code[function.start:function.end]
                    numbers = set()
                    for token in set(re.findall(r'\b\w+\b', code)):
                        number = constant_id(token, script.constants)
                        if number is not None:
                            numbers.add(number)
                    type_var = function.params[1]
                    catch_all = bool(re.search(r'\b' + re.escape(type_var) + r'\s*(?:>=|<=|>|<|!=)', code)
                                     or re.search(r'(?:>=|<=|>|<|!=)\s*' + re.escape(type_var) + r'\b', code)
                                     or ('else' in code and mentions(code, (type_var,))))
                    rows.append((script, function, numbers, catch_all))
            self._receivers = rows
        return self._receivers

    def resolve_custom(self, custom, depth=0, seen=()):
        """Terminal effects reached by Send_Custom_Event(type, param) through Custom() receivers."""
        key = (custom['type'], custom['param'])
        if key in seen or depth > 3 or not isinstance(custom['type'], int):
            return [], False
        cache_key = (key, depth)
        if cache_key in self.cache:
            return self.cache[cache_key]
        self.cache[cache_key] = ([], False)  # cycle guard while this key is being resolved
        terminals, found = [], False
        for script, function, numbers, catch_all in self.receiver_candidates():
            if custom['type'] in numbers or catch_all:
                type_var, param_var = function.params[1], function.params[2]
                env = {type_var: custom['type'],
                       param_var: custom['param'] if isinstance(custom['param'], int) else UNKNOWN}
                for effect in function_effects(self, script, function, env, anchors=(type_var,), need_anchor=True):
                    effect = Effect(effect, via=effect.get('via') or f"receiver {script.name}:{effect['line']}")
                    for resolved in self.expand(script, effect, depth, seen + (key,), env):
                        if resolved['kind'] in TERMINAL_KINDS:
                            found = True
                            terminals.append(resolved)
                        elif resolved['kind'] == 'custom_resolved':
                            found = True
                            terminals.extend(resolved['terminals'])
        terminals = self.unique(terminals)
        self.cache[cache_key] = (terminals, found)
        return terminals, found

    def expand(self, script, effect, depth, seen, env):
        """Follow timers (same script Timer_Expired) and nested customs from one effect."""
        kind = effect['kind']
        if kind in TERMINAL_KINDS:
            return [effect]
        if kind == 'custom':
            terminals, found = self.resolve_custom(effect, depth + 1, seen)
            if found:
                return [Effect(kind='custom_resolved', terminals=[Effect(t, sent=f"custom {effect['type']}/{effect['param']}",
                                                                          guards=sorted(set(t.get('guards', [])) | set(effect.get('guards', []))))
                                                                   for t in terminals])]
            return [effect]
        if kind == 'timer' and depth <= 3:
            out = []
            for function in script.named('Timer_Expired'):
                if len(function.params) < 2:
                    continue
                var = function.params[1]
                for inner in function_effects(self, script, function, {var: effect['timer']}, anchors=(var,), need_anchor=True):
                    inner = Effect(inner, via=f"timer {effect['timer']} -> {script.name}:{inner['line']}",
                                   guards=sorted(set(inner.get('guards', [])) | set(effect.get('guards', []))))
                    if inner['kind'] != 'timer':
                        out.extend(self.expand(script, inner, depth + 1, seen, env))
            return out
        return []

    def terminals(self, script, effects, env=None):
        """Resolve direct effects to terminal progression effects (unresolved customs stay as customs)."""
        result = []
        for effect in effects:
            for item in self.expand(script, effect, 0, (), env or {}):
                if item['kind'] == 'custom_resolved':
                    result.extend(item['terminals'])
                elif item['kind'] in TERMINAL_KINDS or item['kind'] == 'custom':
                    result.append(item if item['kind'] != 'custom' else Effect(item, unresolved=True))
        return self.unique(result)

    def unique(self, effects):
        """Drop exact duplicates (same terminal, route and guards); chains otherwise multiply."""
        seen, result = set(), []
        for effect in effects:
            key = (self.signature(effect), effect.get('via'), effect.get('sent'), tuple(effect.get('guards', ())),
                   tuple(effect.get('flag') or ()))
            if key not in seen:
                seen.add(key)
                result.append(effect)
        return result

    def signature(self, terminal):
        kind = terminal['kind']
        if kind == 'objective_status':
            return ('status', terminal['objective'], terminal['status'])
        if kind == 'add_objective':
            return ('add', terminal['objective'])
        if kind == 'mission_complete':
            return ('complete', terminal['success'])
        return ('custom', terminal['type'], terminal['param'])

    def significance(self, terminal):
        """completion | critical | critical-unknown-type | secondary | failure | other | custom"""
        kind = terminal['kind']
        if kind == 'mission_complete':
            return 'completion' if terminal['success'] in (1, 'true', 'TRUE') else 'failure'
        if kind in ('objective_status', 'add_objective'):
            types = self.objective_types.get(terminal['objective'], set())
            if kind == 'objective_status':
                if terminal['status'] == 2:
                    return 'failure'
                if terminal['status'] != 1:
                    return 'other'
            if 'primary' in types:
                return 'critical'
            return 'secondary' if types else 'critical-unknown-type'
        return 'custom'


# --------------------------------------------------------------------------
# Gate resolution
# --------------------------------------------------------------------------

def branch_matches(mission, script, wanted, with_reasons=True):
    """Action_Complete leaves of `script` reachable for action id `wanted`.

    Returns [{'start','end','anchored','reasons','guards'}]; anchored means the path is
    conditioned on the action id (otherwise the leaf fires for every action).
    """
    rows = []
    for function in script.named('Action_Complete'):
        if len(function.params) < 3:
            continue
        action_var, reason_var = function.params[1], function.params[2]
        for start, end, conds in script.leaves(function):
            accepted, guards, anchored = [], [], False
            for reason in REASONS:
                env = {action_var: wanted, reason_var: reason}
                passes, g, a = path_state(conds, env, script.constants, (action_var,))
                if passes:
                    accepted.append(reason)
                    guards, anchored = g, anchored or a
            if accepted:
                rows.append({'function': function, 'start': start, 'end': end, 'anchored': anchored,
                             'reasons': accepted, 'guards': guards, 'action_var': action_var, 'reason_var': reason_var})
    return rows


def resolve_gate(mission, gate):
    script = gate['script']
    selected = []
    for action in gate['actions']:
        for row in branch_matches(mission, script, action):
            if row["anchored"]:
                selected.append({**row, 'script': script, 'action': action})
    scope = 'same script'
    if not selected:
        # Observer may be another object's script: any mission script with an anchored matching branch.
        for other in mission.scripts:
            if other is script:
                continue
            for action in gate['actions']:
                for row in branch_matches(mission, other, action):
                    if row['anchored']:
                        selected.append({**row, 'script': other, 'action': action})
        scope = 'other scripts in mission (approximate)'
    elif not all(t in ('obj', 'this') for t in gate['monitor_targets']):
        scope = 'same script; monitor target ' + ', '.join(gate['monitor_targets'])
    effects, handlers, reasons, guards, flags = [], set(), set(), [], []
    for row in selected:
        owner = row['script']
        env = {row['action_var']: row['action']}
        direct = leaf_effects(mission, owner, row['start'], row['end'], env)
        for effect in direct:
            if row['guards']:
                effect['guards'] = sorted(set(effect.get('guards', [])) | set(row['guards']))
        effects.append((owner, direct))
        handlers.add((owner.name, owner.line(row['function'].start)))
        reasons.update(row['reasons'])
        guards.extend(row['guards'])
        for name, value, line in flag_assignments(owner, row['start'], row['end'], env):
            flags.append((name, value, line, owner))
    flag_notes = []
    flag_effects = []
    for name, value, line, owner in flags:
        env = {name: value if isinstance(value, int) else UNKNOWN}
        if not isinstance(value, int):
            continue
        others = [(f, s, e, c) for f in owner.functions if f.name != 'Action_Complete' for s, e, c in owner.leaves(f)
                  if any(mentions(cond, (name,)) for cond, _ in c)]
        for function, start, end, conds in others:
            passes, g, anchored = path_state(conds, env, owner.constants, (name,))
            if not passes or not anchored:
                continue
            found = [e for e in leaf_effects(mission, owner, start, end, env) if e['kind'] != 'timer']
            for effect in found:
                flag_effects.append((owner, Effect(effect, via=f"flag {name}={value} read in {owner.name}.{function.name}:{effect['line']}",
                                                   flag=[name, value], guards=sorted(set(g)))))
        flag_notes.append(f'{name}={value}')
    reason_filter = sorted(reasons)
    return {'effects': effects, 'flag_effects': flag_effects, 'handlers': sorted(handlers),
            'reason_filter': reason_filter, 'guards': sorted(set(guards)), 'receiver_scope': scope,
            'branches': len(selected), 'flags': flag_notes}


def key_state(gate, db):
    """('key'|'non-key'|'mixed'|'unknown'|'missing', {name: bool|None|'missing'})"""
    states = {}
    for name in gate['names']:
        row = lookup(db, name) if db else None
        states[name] = 'missing' if db and row is None else (None if row is None or row['is_key'] is None else row['is_key'])
    if not states:
        return 'unknown', states
    values = set(states.values())
    if values == {'missing'}:
        return 'missing', states
    if values == {True}:
        return 'key', states
    if values == {False}:
        return 'non-key', states
    if values == {None}:
        return 'unknown', states
    return 'mixed', states


def emitter_index(mission, excluded_leaves):
    """terminal signature -> emitters (leaves outside gate ranges and outside receiver chains)."""
    index = defaultdict(list)
    for script in mission.scripts:
        for function in script.functions:
            receiver = function.name in ('Custom', 'Timer_Expired')
            for start, end, conds in script.leaves(function):
                if (script.name, function.start, start) in excluded_leaves:
                    continue
                direct = [e for e in leaf_effects(mission, script, start, end, {}, depth=2)
                          if e['kind'] in TERMINAL_KINDS or e['kind'] == 'custom']
                if receiver:
                    # A receiver terminal is reached by a custom/timer, not an independent source; relays still emit.
                    direct = [e for e in direct if e['kind'] == 'custom']
                if not direct:
                    continue
                for signature in {mission.signature(t) for t in mission.terminals(script, direct)}:
                    index[signature].append({'script': script.name, 'line': script.line(start), 'function': function.name})
    for item in mission.cinematic:
        for terminal in mission.terminals(None, [Effect(kind='custom', type=item['type'], param=item['param'], line=0)]):
            index[mission.signature(terminal)].append(
                {'script': 'cinematic ' + item['member'], 'line': item['line'], 'function': 'Send_Custom'})
    return index


def analyse_mission(name, scripts, db, cinematic=None):
    """Return gates (JSON-safe dicts) for one mission."""
    mission = Mission(name, scripts, db, cinematic)
    known = (set(db['level']) | set(db['global'])) if db else set()
    raw, orphans = [], []
    for script in scripts:
        gates, lost = discover_gates(script, known)
        orphans.extend(lost)
        raw.extend(gates)
    excluded = set()
    for gate in raw:
        gate['resolved'] = resolve_gate(mission, gate)
        script = gate['script']
        for action in gate['actions']:
            for row in branch_matches(mission, script, action):
                if row['anchored']:
                    excluded.add((script.name, row['function'].start, row['start']))
        gate['key_state'], gate['key_by_name'] = key_state(gate, db)
        terminals = []
        for owner, direct in gate['resolved']['effects']:
            terminals.extend(mission.terminals(owner, direct))
        flag_terminals = []
        for owner, effect in gate['resolved']['flag_effects']:
            flag_terminals.extend(mission.terminals(owner, [effect]))
        gate['terminals'], gate['flag_terminals'] = terminals, flag_terminals
    index = emitter_index(mission, excluded)
    key_sigs = defaultdict(list)
    for gate in raw:
        if gate['key_state'] == 'key':
            for terminal in gate['terminals'] + gate['flag_terminals']:
                key_sigs[mission.signature(terminal)].append((gate['script'].name, gate['script'].line(gate['create']['offset'])))
    flag_sources = flag_assignment_sites(raw)
    rows = []
    for gate in raw:
        script = gate['script']
        me = (script.name, script.line(gate['create']['offset']))
        progress = []
        for terminal in gate['terminals'] + gate['flag_terminals']:
            signature = mission.signature(terminal)
            base = index.get(signature, [])
            extra = [{'script': s, 'line': l, 'function': 'key-conversation gate'}
                     for s, l in key_sigs.get(signature, []) if (s, l) != me]
            alternatives, alternative_total = base[:6] + extra, len(base) + len(extra)
            flag = terminal.get('flag')
            if flag:
                others = [site for site in flag_sources.get((script.name, flag[0], flag[1]), []) if site['gate'] != me]
                alternatives = [{'script': script.name, 'line': site['line'], 'function': 'other assignment of ' + flag[0]}
                                for site in others]
                alternative_total = len(alternatives)
            progress.append({'signature': list(signature), 'significance': mission.significance(terminal),
                             'via': terminal.get('via') or terminal.get('sent') or 'direct', 'line': terminal.get('line'),
                             'guards': terminal.get('guards', []), 'flag': bool(flag),
                             'alternatives': alternatives[:6], 'alternative_count': alternative_total,
                             'unresolved': bool(terminal.get('unresolved'))})
        rows.append(finish_gate(mission, gate, dedupe(progress)))
    return {'mission': name, 'gates': rows, 'orphans': orphans,
            'key_conversations': key_conversation_inventory(scripts, known, db),
            'objective_types': {str(k): sorted(v) for k, v in sorted(mission.objective_types.items(), key=lambda kv: str(kv[0]))}}


def dedupe(progress):
    seen, result = set(), []
    for item in progress:
        key = (tuple(item['signature']), item['via'], item['flag'])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def flag_assignment_sites(gates):
    """(script, flag, value) -> assignment sites outside Action_Complete (alternative setters of a flag)."""
    sites = defaultdict(list)
    seen = set()
    for gate in gates:
        script = gate['script']
        if script.name in seen:
            continue
        seen.add(script.name)
        for function in script.functions:
            if function.name == 'Action_Complete':
                continue
            for start, end, conds in script.leaves(function):
                for name, value, line in flag_assignments(script, start, end, {}):
                    if function.name != 'Created':
                        sites[(script.name, name, value)].append({'line': line, 'gate': None})
    return sites


def key_conversation_inventory(scripts, known, db):
    rows = []
    for script in scripts:
        for call in script.calls(0, len(script.src), ('Create_Conversation',)):
            if not call['arguments']:
                continue
            names, _ = name_candidates(script, script.function_at(call['offset']), call['arguments'][0], known)
            for name in names:
                row = lookup(db, name) if db else None
                if row and row['is_key']:
                    rows.append({'name': name, 'script': script.name, 'line': script.line(call['offset'])})
    return sorted(rows, key=lambda r: (r['name'], r['script'], r['line']))


def finish_gate(mission, gate, progress):
    script, state = gate['script'], gate['key_state']
    critical = [p for p in progress if p['significance'] in ('critical', 'completion')]
    unknown = [p for p in progress if p['significance'] == 'critical-unknown-type']
    customs = [p for p in progress if p['significance'] == 'custom']
    secondary = [p for p in progress if p['significance'] in ('secondary', 'failure', 'other')]
    label = lambda items: ', '.join('/'.join(str(x) for x in p['signature']) for p in items)
    uncovered = [p for p in critical if p['alternative_count'] == 0]
    if state == 'missing':
        classification, reason = 'NAME MISSING', 'conversation name not found in level or global database: Create_Conversation returns -1'
    elif not progress:
        classification, reason = 'NO EFFECT', 'completion handler found but no objective/custom/Mission_Complete effect'
    elif state == 'key':
        classification, reason = 'SAFE (key)', 'all candidate conversations are key conversations'
    elif state == 'unknown':
        classification = 'REVIEW' if critical or unknown or customs else 'LOW'
        reason = 'conversation key flag unknown (name not resolved or no database supplied)'
    elif uncovered:
        classification = 'AT RISK'
        reason = 'non-key conversation is the only emitter of: ' + label(uncovered)
    elif [p for p in unknown if p['alternative_count'] == 0] or [p for p in customs if p['alternative_count'] == 0]:
        classification = 'REVIEW'
        reason = 'non-key sole emitter of unresolved terminal: ' + label(
            [p for p in unknown + customs if p['alternative_count'] == 0])
    elif critical or unknown or customs:
        classification, reason = 'SAFE (alt path)', 'every progression terminal has an independent emitter'
    elif secondary:
        classification, reason = 'LOW', 'gates only secondary/tertiary objectives, failure, or non-progression effects'
    else:
        classification, reason = 'NO EFFECT', 'no progression effect'
    if state == 'mixed' and classification != 'NAME MISSING':
        reason += ' (mixed key/non-key candidate names)'
    fixed_by = None
    if (classification in ('AT RISK', 'REVIEW') and gate['monitor_before_start']
            and 'ACTION_COMPLETE_CONVERSATION_INTERRUPTED' in gate['resolved']['reason_filter']):
        fixed_by = 'structure: Monitor_Conversation precedes Start_Conversation, so a key-conversation preemption reaches Action_Complete synchronously (INTERRUPTED)'
        reason = f'{classification} pattern neutralised ({reason})'
        classification = 'FIXED'
    return {
        'fixed_by': fixed_by, 'monitor_before_start': gate['monitor_before_start'],
        'body_sha256': hashlib.sha256(' '.join(script.src.split()).encode()).hexdigest(),
        'mission': mission.name, 'script': script.name, 'owner': script.owner, 'line': script.line(gate['create']['offset']),
        'start_lines': gate['start_lines'], 'monitor_lines': gate['monitor_lines'],
        'start_event': gate['function'].name if gate['function'] else None,
        'conversation': gate['names'] or [gate['name_expression']], 'name_resolution': gate['name_resolution'],
        'key_state': state, 'key_by_name': dict(gate['key_by_name']),
        'actions': gate['actions'], 'monitor_targets': gate['monitor_targets'],
        'handlers': [f'{s}:{l}' for s, l in gate['resolved']['handlers']], 'receiver_scope': gate['resolved']['receiver_scope'],
        'reason_filter': gate['resolved']['reason_filter'], 'guards': gate['resolved']['guards'],
        'progress': progress, 'classification': classification, 'reason': reason}


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------

def load_mission_scripts(scripts_dir, mission):
    owner = OWNER_BY_MISSION[mission]
    rows = [row for row in scan_registrations(scripts_dir, {owner}) if row['owner'] == owner]
    constants = {k: str(v) for k, v in BUILTIN_CONSTANTS.items()}
    inherited = numeric_constants('\n'.join(include_closure(scripts_dir, scripts_dir / owner)))
    constants.update({k: str(int(v)) for k, v in inherited.items() if str(v).lstrip('-').isdigit()})
    return [Script(row, constants) for row in rows]


def cinematic_sends(data, mission):
    """Send_Custom commands in the mission's cinematic text files: [{type, param, member, line}]."""
    from tools.audit_cinematic_command_coverage import classify, parse_payload
    archive = MixArchive(data / (mission + '.mix'))
    rows = []
    for member in sorted(archive.entries):
        if not member.endswith('.txt'):
            continue
        records, _ = parse_payload(archive.read_binary(member))
        for record in records:
            info = classify(record)
            if info['command'] == 'Send_Custom' and len(info['args']) >= 2:
                try:
                    param = int(info['args'][2]) if len(info['args']) > 2 and info['args'][2] else 0
                    rows.append({'type': int(info['args'][1]), 'param': param, 'member': member, 'line': record['line']})
                except ValueError:
                    pass
    return rows


LIMITS = [
    'Static source analysis; no execution, build, emulator or device evidence.',
    'Gates are Create/Start/Monitor triples whose completion handler is an Action_Complete branch conditioned on the Start_Conversation action id; when the same script has none, any mission script with such a branch is used (approximate, action ids can collide).',
    'Send_Custom_Event receivers are matched by event type and parameter (literals/constants), not by target object id; chains (customs, helper calls with bound arguments, same-script timers) are followed to depth 3. State conditions stay as guards and are not evaluated.',
    'Alternative paths are other emitters of the same terminal signature in the same mission translation unit (plus Send_Custom lines of the mission cinematic text files); reachability and ordering are not proven.',
    'A key conversation that starts AFTER the gate conversation is registered is not a loss: ConversationMgrClass::Think stops the non-key conversation with the default ENDED reason and delivers Action_Complete. Only a key conversation already active when the non-key one calls Start_Conversation drops the callback.',
    'Which key conversations can be active at the same moment is approximated per mission by the key conversations the mission scripts create.',
    'Member-flag mediation is by name: effects in other functions whose conditions require the flag value set by the gate are listed as via-flag; their alternatives are other assignments of the flag.',
]


def new_patch_lines(patches_dir, known_dir):
    """{patch name: distinctive added lines} for script patches present in patches_dir but not in known_dir."""
    if not patches_dir or not patches_dir.is_dir():
        return {}
    known = {p.name for p in known_dir.glob('*.patch')} if known_dir and known_dir.is_dir() else set()
    result = {}
    for path in sorted(patches_dir.glob('scripts-*.patch')):
        if path.name in known:
            continue
        added = {line[1:].strip() for line in path.read_text(encoding='latin1').splitlines()
                 if line.startswith('+') and not line.startswith('+++')}
        result[path.name[:-len('.patch')]] = {line for line in added if len(line) >= 25 and not line.startswith('//')}
    return result


def attribute_patches(patch_lines, script):
    body = {' '.join(line.split()) for line in script.src.splitlines()}
    body = {line for line in body if line}
    return sorted(name for name, lines in patch_lines.items()
                  if len({' '.join(x.split()) for x in lines} & body) >= 2)


def gate_key(gate):
    return (gate['script'], tuple(gate['conversation']), tuple(str(a) for a in gate['actions']))


def annotate_against_baseline(entry, baseline, patched_scripts, baseline_scripts, patch_lines):
    """Mark gates whose risk was removed since the baseline staging (FIXED) and gates patched but still at risk."""
    old = {gate_key(g): g for g in baseline['gates']}
    new_keys = {gate_key(g) for g in entry['gates']}
    by_name = {s.name: s for s in patched_scripts}
    base_by_name = {s.name: s for s in baseline_scripts}
    for gate in entry['gates']:
        base = old.get(gate_key(gate))
        gate['baseline_class'] = base['classification'] if base else None
        gate['script_changed'] = bool(base) and base['body_sha256'] != gate['body_sha256']
        gate['patches'] = attribute_patches(patch_lines, by_name[gate['script']]) if gate['script_changed'] and gate['script'] in by_name else []
        if not base or base['classification'] not in ('AT RISK', 'REVIEW'):
            continue
        # A risk can also be removed by an independent emitter added in another script of the unit.
        involved = {a['script'] for p in gate['progress'] for a in p['alternatives'] if a['script'] in by_name}
        changed_helpers = sorted(name for name in involved if name != gate['script'] and name in base_by_name
                                 and ' '.join(by_name[name].src.split()) != ' '.join(base_by_name[name].src.split()))
        changed_helpers += sorted(name for name in involved if name != gate['script'] and name not in base_by_name)
        if not gate['script_changed'] and not changed_helpers:
            continue
        for name in changed_helpers:
            gate['patches'] = sorted(set(gate['patches']) | set(attribute_patches(patch_lines, by_name[name])))
        if gate['classification'] in ('SAFE (alt path)', 'SAFE (key)', 'LOW', 'NO EFFECT'):
            gate['fixed_by'] = ('patch ' + ', '.join(gate['patches'])) if gate['patches'] else 'script changed since baseline staging'
            gate['reason'] = f"was {base['classification']} in baseline ({base['reason']}); now {gate['classification']}"
            gate['classification'] = 'FIXED'
        elif gate['classification'] == 'FIXED' and gate['patches']:
            gate['fixed_by'] = 'patch ' + ', '.join(gate['patches']) + '; ' + gate['fixed_by']
    entry['baseline_gates_gone'] = []
    for key, base in old.items():
        if key in new_keys or base['classification'] not in ('AT RISK', 'REVIEW'):
            continue
        current = by_name.get(base['script'])
        changed = current is None or ' '.join(current.src.split()) != ' '.join(base_by_name[base['script']].src.split())
        entry['baseline_gates_gone'].append({
            'script': base['script'], 'conversation': base['conversation'], 'actions': base['actions'],
            'baseline_class': base['classification'], 'script_changed': changed,
            'patches': attribute_patches(patch_lines, current) if current is not None and changed else []})


def mission_entry(job):
    scripts_dir, baseline_dir, data, mission, patch_lines = job
    db = load_conversation_db(data, mission) if data else None
    scripts = load_mission_scripts(scripts_dir, mission)
    cinematic = cinematic_sends(data, mission) if data else []
    entry = analyse_mission(mission, scripts, db, cinematic)
    entry['database_sources'] = db['sources'] if db else []
    entry['database_conversations'] = ({'level': len(db['level']), 'global': len(db['global']),
                                        'key_level': sum(1 for r in db['level'].values() if r['is_key'])} if db else None)
    entry['baseline_compared'] = False
    if baseline_dir:
        owner = OWNER_BY_MISSION[mission]
        same = (scripts_dir / owner).read_bytes() == (baseline_dir / owner).read_bytes()
        if same:
            for gate in entry['gates']:
                gate.update({'baseline_class': gate['classification'], 'script_changed': False, 'patches': []})
            entry['baseline_gates_gone'] = []
        else:
            baseline_scripts = load_mission_scripts(baseline_dir, mission)
            baseline = analyse_mission(mission, baseline_scripts, db, cinematic)
            annotate_against_baseline(entry, baseline, scripts, baseline_scripts, patch_lines)
        entry['baseline_compared'] = True
        entry['unit_changed_since_baseline'] = not same
    return mission, entry


def build_report(root, scripts_dir, data, missions, baseline_dir=None, patches_dir=None, jobs=1):
    result = {'schema_version': 1, 'evidence_class': 'static source + read-only authored conversation flags',
              'scripts_directory': str(scripts_dir.relative_to(root)) if scripts_dir.is_relative_to(root) else str(scripts_dir),
              'baseline_directory': str(baseline_dir) if baseline_dir else None,
              'runtime_or_physical_acceptance': False, 'missions': {}}
    patch_lines = new_patch_lines(patches_dir, root / 'port/patches') if baseline_dir else {}
    result['patches_since_baseline'] = sorted(patch_lines)
    work = [(scripts_dir, baseline_dir, data, mission, patch_lines) for mission in missions]
    if jobs > 1:
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            rows = list(pool.map(mission_entry, work))
    else:
        rows = [mission_entry(job) for job in work]
    for mission, entry in rows:
        result['missions'][mission] = entry
    result['limits'] = LIMITS
    result['tool_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def describe_progress(item):
    signature = item['signature']
    if signature[0] == 'status':
        text = f'objective {signature[1]} -> {STATUS_NAMES.get(signature[2], signature[2])}'
    elif signature[0] == 'add':
        text = f'Add_Objective {signature[1]}'
    elif signature[0] == 'complete':
        text = f'Mission_Complete({"true" if signature[1] in (1, "true") else signature[1]})'
    else:
        text = f'custom {signature[1]}/{signature[2]} (receiver unresolved)'
    via = '' if item['via'] == 'direct' else f" via {item['via']}"
    return f"{text} [{item['significance']}]{via}" + (' (flag-mediated)' if item['flag'] else '')


def class_cell(gate):
    text = f"**{gate['classification']}**"
    if gate['classification'] == 'FIXED':
        text += f" ({gate.get('fixed_by')}; baseline {gate.get('baseline_class') or 'n/a'})"
    elif gate.get('script_changed'):
        text += f" (script patched: {', '.join(gate.get('patches') or ['unattributed'])})"
    return text


def gate_table(gates):
    header = ['Mission', 'Script:line', 'Conversation', 'Key', 'Action', 'Gated effect', 'Alternative path', 'Class']
    rows = ['| ' + ' | '.join(header) + ' |', '| ' + ' | '.join('---' for _ in header) + ' |']
    for gate in gates:
        names = ', '.join(f'`{n}`' for n in gate['conversation'])
        if len(gate['conversation']) > 1 or gate['key_state'] in ('mixed', 'unknown'):
            names += ' (' + gate['name_resolution'] + ')'
        if gate['key_state'] == 'mixed':
            key = 'mixed: ' + ', '.join(f"{n}={'key' if v is True else 'non-key' if v is False else v}"
                                        for n, v in gate['key_by_name'].items())
        else:
            key = gate['key_state']
        effects = '<br>'.join(describe_progress(p) for p in gate['progress']) or '-'
        extra = ''
        if gate['reason_filter'] and len(gate['reason_filter']) < 3:
            extra += ' reason=' + '/'.join(r.replace('ACTION_COMPLETE_CONVERSATION_', '') for r in gate['reason_filter'])
        if gate['guards']:
            extra += ' guard: `' + '; '.join(gate['guards'][:2]).replace('|', '\\|') + '`'
        if gate['receiver_scope'] != 'same script':
            extra += ' [' + gate['receiver_scope'] + ']'
        alternatives = []
        for item in gate['progress']:
            if item['alternative_count']:
                sample = ', '.join(f"{a['script']}:{a['line']}" for a in item['alternatives'][:3])
                alternatives.append(f"{item['alternative_count']} ({sample})")
            else:
                alternatives.append('none')
        rows.append(f"| {gate['mission']} | `{gate['script']}`:{gate['line']} (start {','.join(map(str, gate['start_lines']))} in {gate.get('start_event')}; "
                    f"handler {', '.join(gate['handlers'])}) | {names} | {key} | {', '.join(str(a) for a in gate['actions'])} | "
                    f"{effects}{extra} | {'<br>'.join(alternatives) or '-'} | {class_cell(gate)} |")
    return rows


def render_markdown(report):
    lines = ['# Conversation-gated objectives', '',
             'Generated by `python3 -m tools.audit_conversation_gated_objectives --markdown reports/campaign/CONVERSATION_GATED_OBJECTIVES.md` '
             '(static, read-only; no build, launch or retail modification).',
             f"Sources: patched script sources `{report['scripts_directory']}`"
             + (f" compared with the older baseline staging `{report['baseline_directory']}`" if report.get('baseline_directory') else '')
             + '; level `.ldd/.lsd` and global `conv10.cdb` conversation names and the '
             'VARID_ISKEY flag only (no dialogue text or audio). Run `python3 -m tools.audit_conversation_gated_objectives --scripts <patched staging/scripts> '
             '--baseline-scripts <older staging/scripts> --patches <patched port/patches> --jobs 8 --json build/cgo.json --markdown <this file>`.', '',
             '**Reading the classes.** The tool proves structural exposure, not that a key conversation will overlap in play: a gate started from '
             '`Created`/an early zone is much less likely to meet an active key conversation than one started from a kill or poke during a briefing. '
             'The `start in <event>` text and the per-mission key-conversation lists below are the cross-check inputs for mission owners. '
             '`FIXED` means the baseline staging classified the gate AT RISK/REVIEW and the patched staging no longer does (a patch added an independent '
             'emitter or registered the monitor before `Start_Conversation`); patch names are attributed by matching added lines against the changed '
             'script bodies and are indicative, not authoritative. A gate whose script was patched but is still AT RISK is listed separately and needs a manual read of that patch.', '',
             '## Why this matters', '',
             'A script that does `Create_Conversation` -> `Start_Conversation(id, ACTION)` -> `Monitor_Conversation(obj, id)` and then '
             'advances the mission from `Action_Complete(ACTION)` depends on `Notify_Monitors_On_End`. '
             '`ActiveConversationClass::Start_Conversation` (activeconversation.cpp:399) stops a **non-key** conversation with INTERRUPTED '
             'before the script reaches `Monitor_Conversation` when any key conversation is already in the active list, so the late '
             '`Register_Monitor` never fires and the gated effect is lost. A key conversation that starts later does not lose the callback '
             '(`ConversationMgrClass::Think` stops non-key conversations with ENDED and still notifies monitors). Priority and the '
             'interruptable flag are not consulted. This is retail behaviour, not a port defect; the report lets mission owners decide '
             'which gates need a design decision.', '',
             '## Summary per mission', '',
             '| Mission | Gates | ' + ' | '.join(CLASSES) + ' |', '| --- | --- | ' + ' | '.join('---' for _ in CLASSES) + ' |']
    totals = Counter()
    for mission, data in report['missions'].items():
        counts = Counter(g['classification'] for g in data['gates'])
        totals.update(counts)
        lines.append(f"| {mission} | {len(data['gates'])} | " + ' | '.join(str(counts.get(c, 0)) for c in CLASSES) + ' |')
    lines.append(f"| **Total** | **{sum(totals.values())}** | " + ' | '.join(f'**{totals.get(c, 0)}**' for c in CLASSES) + ' |')
    lines += ['', 'Classes: **FIXED** was AT RISK/REVIEW in the baseline staging and a later patch (or Monitor-before-Start structure) removes the hazard; **AT RISK** non-key and sole emitter of a primary objective completion/addition or `Mission_Complete(true)`; '
              '**REVIEW** non-key sole emitter of a custom whose receiver did not resolve, or of an objective of unknown type, or key flag unknown; '
              '**LOW** secondary/tertiary/failure/other only; **SAFE (key)** every candidate name is a key conversation; '
              '**SAFE (alt path)** each progression terminal has another emitter; **NO EFFECT** handler without a progression effect; '
              '**NAME MISSING** name absent from the level and global databases (retail-identical `Create_Conversation` = -1).', '']
    at_risk = [g for m in report['missions'].values() for g in m['gates'] if g['classification'] == 'AT RISK']
    untouched = [g for g in at_risk if not g.get('script_changed')]
    touched = [g for g in at_risk if g.get('script_changed')]
    lines += ['## AT RISK gates (unfixed)', '']
    lines += gate_table(untouched) if untouched else ['None.']
    if touched:
        lines += ['', '## AT RISK gates whose script was patched since the baseline (cross-check: the tool still sees a non-key sole emitter)', '']
        lines += gate_table(touched)
    fixed = [g for m in report['missions'].values() for g in m['gates'] if g['classification'] == 'FIXED']
    gone = [(m, g) for m, v in report['missions'].items() for g in v.get('baseline_gates_gone', [])]
    lines += ['', '## FIXED gates', '']
    lines += gate_table(fixed) if fixed else ['None.']
    if gone:
        lines += ['', 'Baseline AT RISK/REVIEW gates that no longer exist in the patched script (restructured by a patch): '
                  + '; '.join(f"{m} `{g['script']}` {', '.join(g['conversation'])} was {g['baseline_class']}"
                               + (f" ({', '.join(g['patches'])})" if g['patches'] else '') for m, g in gone)]
    if report.get('patches_since_baseline'):
        lines += ['', 'Script patches merged since the baseline staging (used for attribution): '
                  + ', '.join(f'`{n}`' for n in report['patches_since_baseline'])]
    review = [g for m in report['missions'].values() for g in m['gates'] if g['classification'] in ('REVIEW', 'NAME MISSING')]
    lines += ['', '## REVIEW and NAME MISSING gates', '']
    lines += gate_table(review) if review else ['None.']
    for mission, data in report['missions'].items():
        lines += ['', f'## {mission} gates (all classes except NO EFFECT)', '']
        shown = [g for g in data['gates'] if g['classification'] != 'NO EFFECT']
        silent = len(data['gates']) - len(shown)
        lines += gate_table(shown) if shown else ['No gate with a progression effect.']
        if silent:
            lines += ['', f'{silent} further gate(s) have a handler with no objective/custom/Mission_Complete effect (NO EFFECT, omitted here; present in the JSON).']
        keys = data['key_conversations']
        if keys:
            lines += ['', f'Key conversations created by {mission} scripts (candidates that can be active when a gate above starts): '
                      + ', '.join(f"`{k['name']}` ({k['script']}:{k['line']})" for k in keys[:80]) + (' ...' if len(keys) > 80 else '')]
        if data['orphans']:
            lines += ['', 'Create_Conversation with only a Start or only a Monitor (not a gate): '
                      + ', '.join(f"{o['script']}:{o['line']} (no {o['missing']})" for o in data['orphans'])]
    lines += ['', '## Limits', ''] + [f'- {text}' for text in report['limits']]
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--scripts', type=Path, help='script source directory (default: <root>/staging/scripts)')
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA, help='retail Data directory (read-only)')
    parser.add_argument('--no-data', action='store_true', help='skip retail conversation flags (all keys unknown)')
    parser.add_argument('--baseline-scripts', type=Path,
                        help='older staging/scripts; gates whose AT RISK/REVIEW status was removed by a later script change become FIXED')
    parser.add_argument('--patches', type=Path,
                        help='port/patches of the patched tree; patches absent from <root>/port/patches are attributed to changed scripts')
    parser.add_argument('--jobs', type=int, default=1, help='missions analysed in parallel')
    parser.add_argument('--mission', action='append', dest='missions')
    parser.add_argument('--json', type=Path)
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--render-json', type=Path, help='render --markdown from a saved --json without rescanning')
    args = parser.parse_args()
    if args.render_json:
        args.markdown.write_text(render_markdown(json.loads(args.render_json.read_text())))
        return 0
    scripts_dir = args.scripts or args.root / 'staging/scripts'
    report = build_report(args.root, scripts_dir, None if args.no_data else args.data, args.missions or SCOPE,
                          args.baseline_scripts, args.patches, args.jobs)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + '\n')
    if args.markdown:
        args.markdown.write_text(render_markdown(report))
    print(json.dumps({m: dict(Counter(g['classification'] for g in d['gates'])) for m, d in report['missions'].items()}, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
