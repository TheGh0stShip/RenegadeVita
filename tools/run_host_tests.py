#!/usr/bin/env python3
"""Classify, select and run the repository host tests (``tools/**/test_*.py``).

Every test module is statically classified (no import, no execution) into one
lane, lightest first:

  pure       stdlib Python only: no compiler, retail data, build outputs or device
  retail     Python that reads the user's retail Renegade install (most skip when absent)
  artifact   needs outputs of an earlier host or ARM build (build/..., local-builder/...)
  compiled   runs a host or Vita compiler, CMake, ninja or llvm-rc (or a script that does)
  sanitizer  compiled with -fsanitize unconditionally
  device     talks to a physical Vita, Vita3K or a device bridge

Each module runs in its own process with a private TMPDIR, a timeout and a log
file; independent modules run in parallel. ``--pure-only`` is the fast lane
for agents that may not build.

Examples:
  python3 tools/run_host_tests.py --pure-only
  python3 tools/run_host_tests.py --changed main..HEAD --pure-only
  python3 tools/run_host_tests.py --changed HEAD --list --explain   # uncommitted work
  python3 tools/run_host_tests.py --lanes compiled,sanitizer --jobs 4 --heavy-jobs 2
  python3 tools/run_host_tests.py --write-manifest                  # after adding tests

Exit codes: 0 every selected test passed (or nothing was selected);
1 a test failed, errored, timed out or ran no tests; 2 usage or environment
error (bad arguments, unknown test, unusable git range); 3 the committed
manifest is out of date (--check-manifest); 130 interrupted.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import queue
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / 'tools' / 'host_test_manifest.json'
KNOWN_FAILURES_PATH = ROOT / 'tools' / 'host_test_known_failures.json'
REGENERATE_COMMAND = 'python3 tools/run_host_tests.py --write-manifest'
MANIFEST_SCHEMA = 1
CACHE_NAME = 'host-test-manifest-cache.json'  # under build/, keyed by tools/ file stats
RUNNER_PATH = 'tools/run_host_tests.py'

LANES = ('pure', 'retail', 'artifact', 'compiled', 'sanitizer', 'device')
HEAVY_LANES = frozenset(('compiled', 'sanitizer', 'device'))
# Expected seconds when no previous duration is recorded (longest first scheduling).
DEFAULT_LANE_SECONDS = {'pure': 1.0, 'retail': 5.0, 'artifact': 5.0,
                        'compiled': 30.0, 'sanitizer': 60.0, 'device': 60.0}

# Exact executables (or basenames of paths) that compile or drive a compiler.
COMPILER_EXACT = frozenset(('cmake', 'ninja', 'make', 'gmake', 'llvm-rc', 'windres', 'cc'))
COMPILER_PATTERN = re.compile(
    r'^(?:[\w.+-]+-)?(?:g\+\+|gcc|c\+\+|clang\+\+|clang)(?:-\d+(?:\.\d+)*)?$')
BUILD_SCRIPTS = ('tools/build.sh', 'tools/build_fast_candidate.sh', 'tools/stage_sources.sh',
                 'tools/build_vitagl_demo.sh', 'tools/build_ffmpeg_bink_vita.sh',
                 'tools/build_ttfs_https_vita.sh', 'tools/build_renegade_demo_recorder_plugin.sh',
                 'tools/run_a30_host.sh', 'tools/run_a22_host.sh', 'tools/run_host_probes.py')
# Retail install: an env-var lookup such as RENEGADE_RETAIL_ROOT, an absolute
# host path into a retail tree, or the repository-local retail-pc link.
RETAIL_ENV = re.compile(r'^RENEGADE_RETAIL\w*$')
RETAIL_ABSOLUTE = ('steamapps', 'command & conquer renegade', 'renegade/retail', 'retail-pc')
# Strings that only appear when code reaches a live device or emulator process.
DEVICE_MARKERS = ('vitadevbridge', 'VitaCompanion', 'Vita3K.exe', 'RENEGADE_VITA_IP', 'VITA_IP')
DEVICE_MODULES = frozenset(('ftplib', 'telnetlib'))
ARTIFACT_PREFIXES = ('build/', 'local-builder/', 'dist/')
SHELL_COMPILER = re.compile(r'(?:^|[\s;&|(`$])(?:cmake|ninja|g\+\+|gcc|clang\+\+?|'
                            r'arm-vita-eabi-g(?:cc|\+\+))(?=\s|$)', re.M)
SUBPROCESS_FUNCS = frozenset(('run', 'Popen', 'call', 'check_call', 'check_output',
                              'getoutput', 'getstatusoutput'))
OS_PROCESS_FUNCS = frozenset(('system', 'popen', 'execv', 'execve', 'execvp', 'execvpe',
                              'execl', 'execlp', 'spawnv', 'spawnvp', 'posix_spawn',
                              'posix_spawnp'))
PATH_CALLS = frozenset(('joinpath', 'with_name', 'join', 'glob', 'rglob', 'Path', 'PurePath',
                        'PurePosixPath', 'dirname', 'abspath', 'realpath', 'cwd'))
SKIP_NAMES = frozenset(('skipTest', 'skipUnless', 'skipIf', 'SkipTest', 'skip'))
PATH_EXTENSIONS = ('cpp|cc|c|h|hpp|hh|inc|py|sh|ps1|patch|cmake|json|jsonl|txt|ini|yml|yaml|md|'
                   'csv|rc|def|tdb|xml|toml|S|s|in|cfg')
PATH_TOKEN = re.compile(r'(?<![\w.+/-])((?:[\w.+-]+/)*[\w.+-]+\.(?:%s))(?![\w])' % PATH_EXTENSIONS)
DIR_TOKEN = re.compile(r'(?<![\w.+/-])((?:port|tools|staging|cmake|upstream|docs|reports|assets|'
                       r'experiments)(?:/[\w.+-]+)+)/?')
INCLUDE_LINE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.M)
CXX_EXTENSIONS = frozenset(('.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.inc'))
BASENAME_MATCH_CAP = 8

# Build-system inputs whose change can affect any test.
ALL_TESTS_PATTERNS = ('CMakeLists.txt', 'cmake/*', 'tools/build.sh',
                      'tools/build_fast_candidate.sh', 'tools/__init__.py')
STAGE_SCRIPT = 'tools/stage_sources.sh'
# A changed stage_sources.sh line that only registers or reports a patch.
STAGE_PATCH_LINE = re.compile(
    r'^\s*(?:patch\s+--batch[^<]*\\?|-d\s+"\$rv_stage[^"]*"\s+-p\d+\s*<\s*"\$rv_root/port/patches/'
    r'[\w.+-]+\.patch"|patch\s+--batch.*port/patches/[\w.+-]+\.patch"|echo\s+"Applied:\s*'
    r'port/patches/[\w.+-]+\.patch"|#.*|)\s*$')
PATCH_NAME = re.compile(r'port/patches/([\w.+-]+\.patch)')

# Manual decisions for modules the static scan cannot judge alone. Keep each
# entry justified; the manifest records the reason next to the result.
OVERRIDES = {
    'tools/test_vita_open_source_references.py': {
        'lane': 'pure',
        'reason': 'runs tools/run_vita3k_candidate.py only with --dry-run, which writes a '
                  'receipt and returns before Vita3K is launched'},
    'tools/test_run_host_tests.py': {
        'lane': 'pure',
        'reason': 'imports this runner, whose compiler and device names are classification '
                  'data; its fixtures only start Python unittest children',
        'drop_tags': ['needs-upstream']},
    'tools/test_host_test_manifest.py': {
        'lane': 'pure',
        'reason': 'the build/ path it reaches is the runner\'s optional classification cache, '
                  'which is rebuilt when absent',
        'drop_tags': ['needs-upstream']},
}


# --------------------------------------------------------------------------
# Static module analysis
# --------------------------------------------------------------------------

class Scope:
    __slots__ = ('strings', 'cond_strings', 'names', 'calls', 'subprocess', 'path_ops')

    def __init__(self):
        self.strings = set()
        self.cond_strings = set()
        self.names = set()
        self.calls = set()
        self.subprocess = False
        self.path_ops = False


class ModuleInfo:
    """AST facts about one Python module, keyed by repository-relative path."""

    def __init__(self, rel: str, source: str):
        self.rel = rel
        self.tree = ast.parse(source, filename=rel)
        self.scopes = {'<module>': Scope()}
        self.functions = set()
        self.classes = {}
        self.const_exprs = {}
        self.const_strings = {}
        self.module_aliases = {}
        self.from_imports = {}
        self.whole_imports = set()
        self.third_party = set()
        self.device_modules = set()
        self.subprocess_aliases = {'subprocess'}
        self.subprocess_names = set()
        self.os_aliases = {'os'}
        self.patched = set()
        self.has_testcase = False
        self.test_functions = []
        self.has_main_block = False
        self.cli_required_args = False
        self.uses_skip = False
        self.bare_local_imports = False
        self.function_nodes = None
        self.path_cache = {}
        self.const_path_cache = {}
        _collect_module_facts(self)
        _ScopeVisitor(self).visit(self.tree)


def _module_candidates(name: str, importer: str):
    """Repository paths a dotted import may refer to (local modules only)."""
    parts = name.split('.')
    yield '/'.join(parts) + '.py'
    base = PurePosixPath(importer).parent
    yield str(base / ('/'.join(parts) + '.py'))
    yield 'tools/' + '/'.join(parts) + '.py'


def resolve_local_module(name: str, importer: str):
    for candidate in _module_candidates(name, importer):
        if (ROOT / candidate).is_file():
            return str(PurePosixPath(candidate))
    return None


def _is_local_package(name: str) -> bool:
    return name.split('.')[0] in ('tools',) or (ROOT / name.split('.')[0]).is_dir()


class _ImportCollector(ast.NodeVisitor):
    def __init__(self, info: ModuleInfo):
        self.info = info
        self.try_depth = 0
        self.function_depth = 0

    def visit_Try(self, node):
        guards_import = any(
            isinstance(h.type, ast.Name) and h.type.id in ('ImportError', 'ModuleNotFoundError')
            or isinstance(h.type, ast.Tuple) and any(
                isinstance(e, ast.Name) and e.id in ('ImportError', 'ModuleNotFoundError')
                for e in h.type.elts)
            for h in node.handlers)
        if guards_import:
            self.try_depth += 1
        self.generic_visit(node)
        if guards_import:
            self.try_depth -= 1

    visit_TryStar = visit_Try

    def visit_FunctionDef(self, node):
        self.function_depth += 1
        self.generic_visit(node)
        self.function_depth -= 1

    visit_AsyncFunctionDef = visit_FunctionDef

    def _third_party(self, root_name: str):
        if root_name in sys.stdlib_module_names or root_name == '__future__':
            return
        if self.try_depth or self.function_depth:
            return
        self.info.third_party.add(root_name)

    def visit_Import(self, node):
        info = self.info
        for alias in node.names:
            root_name = alias.name.split('.')[0]
            if root_name in DEVICE_MODULES:
                info.device_modules.add(root_name)
            if root_name == 'subprocess':
                info.subprocess_aliases.add(alias.asname or 'subprocess')
            if root_name == 'os' and alias.name == 'os':
                info.os_aliases.add(alias.asname or 'os')
            local = resolve_local_module(alias.name, info.rel)
            if local and root_name != 'tools':
                info.bare_local_imports = True
            if local:
                if alias.asname:
                    info.module_aliases[alias.asname] = local
                elif '.' in alias.name:
                    info.whole_imports.add(local)
                else:
                    info.module_aliases[alias.name] = local
            elif not _is_local_package(alias.name):
                self._third_party(root_name)

    def visit_ImportFrom(self, node):
        info = self.info
        if node.level or not node.module:
            return
        root_name = node.module.split('.')[0]
        if root_name in DEVICE_MODULES:
            info.device_modules.add(root_name)
        if node.module == 'subprocess':
            for alias in node.names:
                if alias.name in SUBPROCESS_FUNCS:
                    info.subprocess_names.add(alias.asname or alias.name)
        local = resolve_local_module(node.module, info.rel)
        if local and root_name != 'tools':
            info.bare_local_imports = True
        for alias in node.names:
            bound = alias.asname or alias.name
            submodule = resolve_local_module(node.module + '.' + alias.name, info.rel)
            if submodule:
                info.module_aliases[bound] = submodule
            elif local:
                info.from_imports[bound] = (local, alias.name)
        if not local and not any(resolve_local_module(node.module + '.' + a.name, info.rel)
                                 for a in node.names) and not _is_local_package(node.module):
            self._third_party(root_name)


def _collect_module_facts(self: ModuleInfo):
    """Module-level constants, the __main__ block and pytest-style test functions."""
    for statement in self.tree.body:
        targets = []
        if isinstance(statement, ast.Assign):
            targets = [t.id for t in statement.targets if isinstance(t, ast.Name)]
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) \
                and statement.value is not None:
            targets = [statement.target.id]
            value = statement.value
        for target in targets:
            self.const_exprs[target] = value
            self.const_strings[target] = {n.value for n in ast.walk(value)
                                          if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        if isinstance(statement, ast.If) and _is_main_guard(statement.test):
            self.has_main_block = True
            for node in ast.walk(statement):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and node.func.attr == 'add_argument' and node.args \
                        and isinstance(node.args[0], ast.Constant) \
                        and isinstance(node.args[0].value, str):
                    positional = not node.args[0].value.startswith('-')
                    required = any(k.arg == 'required' and isinstance(k.value, ast.Constant)
                                   and k.value.value is True for k in node.keywords)
                    optional_nargs = any(k.arg == 'nargs' and isinstance(k.value, ast.Constant)
                                         and k.value.value in ('?', '*') for k in node.keywords)
                    if (positional and not optional_nargs) or required:
                        self.cli_required_args = True
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and statement.name.startswith('test'):
            self.test_functions.append(statement.name)


def _is_main_guard(test) -> bool:
    return (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name)
            and test.left.id == '__name__' and len(test.comparators) == 1
            and isinstance(test.comparators[0], ast.Constant)
            and test.comparators[0].value == '__main__')


def _call_target(func):
    if isinstance(func, ast.Name):
        return ('', func.id)
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return (func.value.id, func.attr)
        return ('?', func.attr)
    return None


class _ScopeVisitor(_ImportCollector):
    """Single pass: imports (inherited), per-scope strings, names, calls and subprocess use."""

    def __init__(self, info: ModuleInfo):
        super().__init__(info)
        self.stack = [info.scopes['<module>']]
        self.class_stack = []
        self.cond_depth = 0

    @property
    def scope(self) -> Scope:
        return self.stack[-1]

    def visit_ClassDef(self, node):
        info = self.info
        for base in node.bases:
            name = base.attr if isinstance(base, ast.Attribute) else getattr(base, 'id', '')
            if name.endswith('TestCase'):
                info.has_testcase = True
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases + [k.value for k in node.keywords]:
            self.visit(base)
        if not self.function_depth:
            info.classes.setdefault(node.name, set())
        self.class_stack.append(node.name)
        for statement in node.body:
            self.visit(statement)
        self.class_stack.pop()

    def visit_FunctionDef(self, node):
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
            self.visit(default)
        nested = self.function_depth > 0
        if not nested:
            info = self.info
            info.functions.add(node.name)
            if self.class_stack:
                info.classes[self.class_stack[-1]].add(node.name)
            scope = info.scopes.setdefault(node.name, Scope())
            self.stack.append(scope)
        self.function_depth += 1
        saved_cond = self.cond_depth
        self.cond_depth = 0
        for statement in node.body:
            self.visit(statement)
        self.cond_depth = saved_cond
        self.function_depth -= 1
        if not nested:
            self.stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_If(self, node):
        if _is_main_guard(node.test) and not self.function_depth and len(self.stack) == 1:
            # The __main__ block only runs when the file is executed as a script,
            # so it is its own scope and importing the module does not reach it.
            self.stack.append(self.info.scopes.setdefault('<main>', Scope()))
            for statement in node.body:
                self.visit(statement)
            self.stack.pop()
            for statement in node.orelse:
                self.visit(statement)
            return
        self.visit(node.test)
        self.cond_depth += 1
        for statement in node.body + node.orelse:
            self.visit(statement)
        self.cond_depth -= 1

    def visit_IfExp(self, node):
        self.visit(node.test)
        self.cond_depth += 1
        self.visit(node.body)
        self.visit(node.orelse)
        self.cond_depth -= 1

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            self.scope.strings.add(node.value)
            if self.cond_depth:
                self.scope.cond_strings.add(node.value)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.scope.names.add(node.id)
            if node.id in SKIP_NAMES:
                self.info.uses_skip = True

    def visit_Attribute(self, node):
        if node.attr in SKIP_NAMES:
            self.info.uses_skip = True
        if isinstance(node.value, ast.Name) and node.value.id in DEVICE_MODULES:
            self.info.device_modules.add(node.value.id)
        self.generic_visit(node)

    def visit_BinOp(self, node):
        if isinstance(node.op, ast.Div):
            self.scope.path_ops = True
        self.generic_visit(node)

    def visit_Call(self, node):
        info = self.info
        func = node.func
        target = _call_target(func)
        if target:
            self.scope.calls.add(target)
            if target[1] in PATH_CALLS:
                self.scope.path_ops = True
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id in info.subprocess_aliases and func.attr in SUBPROCESS_FUNCS:
                self.scope.subprocess = True
            if func.value.id in info.os_aliases and (func.attr in OS_PROCESS_FUNCS
                                                     or func.attr.startswith('exec')):
                self.scope.subprocess = True
            if func.attr == 'create_subprocess_exec' or func.attr == 'create_subprocess_shell':
                self.scope.subprocess = True
        if isinstance(func, ast.Name) and func.id in info.subprocess_names:
            self.scope.subprocess = True
        if self.scope.subprocess:
            self.scope.path_ops = True  # evaluate the arguments for executed scripts
        self._record_patch(node)
        self.generic_visit(node)

    def _record_patch(self, node):
        func = node.func
        name = None
        if isinstance(func, ast.Name) and func.id == 'patch':
            name = 'patch'
        elif isinstance(func, ast.Attribute) and func.attr == 'patch':
            name = 'patch'
        elif isinstance(func, ast.Attribute) and func.attr == 'object' and (
                isinstance(func.value, ast.Name) and func.value.id == 'patch'
                or isinstance(func.value, ast.Attribute) and func.value.attr == 'patch'):
            name = 'object'
        if name == 'patch' and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            self.info.patched.add(node.args[0].value.rsplit('.', 1)[-1])
        elif name == 'object' and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) \
                and isinstance(node.args[1].value, str):
            self.info.patched.add(node.args[1].value)


_MODULE_CACHE = {}


def analyze(rel: str) -> ModuleInfo | None:
    try:
        return _MODULE_CACHE[rel]
    except KeyError:
        pass
    rel = str(PurePosixPath(rel))
    if rel not in _MODULE_CACHE:
        path = ROOT / rel
        try:
            _MODULE_CACHE[rel] = ModuleInfo(rel, path.read_text(encoding='utf-8'))
        except (OSError, SyntaxError, UnicodeDecodeError, ValueError):
            _MODULE_CACHE[rel] = None
    return _MODULE_CACHE[rel]


# --------------------------------------------------------------------------
# Path expression evaluation (repository-relative)
# --------------------------------------------------------------------------

def _norm(rel: str) -> str | None:
    parts = []
    for part in PurePosixPath(rel).parts:
        if part in ('', '.'):
            continue
        if part == '..':
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return '/'.join(parts)


class PathEvaluator:
    """Evaluate ROOT / "a" / "b" style expressions to repository paths."""

    def __init__(self, info: ModuleInfo):
        self.info = info
        self.local_env = {}
        self.depth = 0

    def with_locals(self, function_node):
        env = {}
        if function_node is not None:
            for node in ast.walk(function_node):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            env[target.id] = node.value
                        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) \
                                and target.value.id in ('self', 'cls'):
                            env['self.' + target.attr] = node.value
        self.local_env = env
        return self

    def eval(self, node):
        """Return ('path', rel) for a repository path, ('str', s) or None."""
        self.depth += 1
        try:
            if self.depth > 40:
                return None
            return self._eval(node)
        finally:
            self.depth -= 1

    def _join(self, base, parts):
        if base is not None and base[0] == 'str' and base[1].startswith('/'):
            base = ('abs', base[1])
        if base is not None and base[0] == 'abs':
            text = base[1]
            for part in parts:
                if part is None or part[0] != 'str':
                    return None
                text = text.rstrip('/') + '/' + part[1].lstrip('/')
            return ('abs', text)
        if base is None or base[0] != 'path':
            return None
        rel = base[1]
        for part in parts:
            if part is None or part[0] != 'str':
                return None
            if part[1].startswith('/'):
                return None
            rel = rel + '/' + part[1] if rel else part[1]
        normalized = _norm(rel)
        return None if normalized is None else ('path', normalized)

    def _eval(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return ('str', node.value)
        if isinstance(node, ast.Name):
            if node.id == '__file__':
                return ('file', self.info.rel)
            if node.id in self.local_env:
                value = self.local_env.pop(node.id)
                try:
                    return self.eval(value)
                finally:
                    self.local_env[node.id] = value
            if node.id in self.info.const_exprs:
                cache = self.info.const_path_cache
                if node.id not in cache:
                    cache[node.id] = None  # recursion guard
                    cache[node.id] = PathEvaluator(self.info).eval(self.info.const_exprs[node.id])
                return cache[node.id]
            if node.id in self.info.from_imports:
                module, name = self.info.from_imports[node.id]
                other = analyze(module)
                if other is not None and name in other.const_exprs:
                    return PathEvaluator(other).eval(other.const_exprs[name])
            return None
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in ('self', 'cls') \
                    and ('self.' + node.attr) in self.local_env:
                key = 'self.' + node.attr
                value = self.local_env.pop(key)
                try:
                    return self.eval(value)
                finally:
                    self.local_env[key] = value
            base = self.eval(node.value)
            if base is None:
                return None
            if node.attr == 'parent':
                return self._parent(base, 1)
            return None
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) \
                and node.value.attr == 'parents':
            base = self.eval(node.value.value)
            index = node.slice
            if isinstance(index, ast.Constant) and isinstance(index.value, int):
                return self._parent(base, index.value + 1)
            return None
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self._join(self._as_path(self.eval(node.left)), [self.eval(node.right)])
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self.eval(node.left), self.eval(node.right)
            if left and right and left[0] == 'str' and right[0] == 'str':
                return ('str', left[1] + right[1])
            return None
        if isinstance(node, ast.Call):
            return self._eval_call(node)
        return None

    def _as_path(self, value):
        if value is not None and value[0] == 'file':
            return ('path', value[1])
        return value

    def _parent(self, base, count):
        base = self._as_path(base)
        if base is None or base[0] != 'path':
            return None
        parts = base[1].split('/') if base[1] else []
        if count > len(parts):
            return None
        return ('path', '/'.join(parts[:len(parts) - count]))

    def _eval_call(self, node):
        func = node.func
        if isinstance(func, ast.Name) and func.id in ('Path', 'PurePath', 'PurePosixPath', 'str',
                                                      'fspath') and len(node.args) == 1:
            return self.eval(node.args[0])
        if isinstance(func, ast.Attribute):
            owner = func.value
            if func.attr in ('Path', 'PurePath', 'PurePosixPath') and len(node.args) == 1:
                return self.eval(node.args[0])
            if func.attr == 'cwd' and not node.args:
                return ('path', '')
            if func.attr in ('resolve', 'absolute', 'expanduser'):
                return self.eval(owner)
            if func.attr in ('abspath', 'realpath', 'normpath', 'fspath') and node.args:
                return self.eval(node.args[0])
            if func.attr == 'dirname' and node.args:
                return self._parent(self.eval(node.args[0]), 1)
            if func.attr == 'join' and isinstance(owner, ast.Attribute) and owner.attr == 'path' \
                    and node.args:
                return self._join(self._as_path(self.eval(node.args[0])),
                                  [self.eval(a) for a in node.args[1:]])
            if func.attr == 'joinpath':
                return self._join(self._as_path(self.eval(owner)), [self.eval(a) for a in node.args])
            if func.attr == 'with_name' and len(node.args) == 1:
                return self._join(self._parent(self.eval(owner), 1), [self.eval(node.args[0])])
            if func.attr in ('get', 'getenv') and len(node.args) >= 2:
                return self.eval(node.args[1])
        return None


def _glob_prefix(pattern: str) -> str | None:
    parts = []
    for part in PurePosixPath(pattern).parts:
        if any(ch in part for ch in '*?['):
            break
        parts.append(part)
    if len(parts) == len(PurePosixPath(pattern).parts):
        parts = parts[:-1]
    return _norm('/'.join(parts)) if parts else ''


def _function_nodes(info: ModuleInfo):
    """Top-level functions and methods by name (same keys as ModuleInfo.scopes)."""
    if info.function_nodes is None:
        nodes = {}
        for statement in info.tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                nodes.setdefault(statement.name, []).append(statement)
            elif isinstance(statement, ast.ClassDef):
                for item in statement.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nodes.setdefault(item.name, []).append(item)
        info.function_nodes = nodes
    return info.function_nodes


def _is_subprocess_call(info: ModuleInfo, node) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if func.value.id in info.subprocess_aliases and func.attr in SUBPROCESS_FUNCS:
            return True
        if func.value.id in info.os_aliases and (func.attr in OS_PROCESS_FUNCS
                                                 or func.attr.startswith('exec')):
            return True
    return isinstance(func, ast.Name) and func.id in info.subprocess_names


_EMPTY_REFS = (frozenset(), frozenset(), False, frozenset())


def _scope_path_refs(info: ModuleInfo, scope_name: str):
    """(paths, globs, repo_wide, exec_paths) evaluated from one scope; cached.

    exec_paths are the paths that appear in the arguments of a subprocess call
    (directly, through a local variable, or through a local helper function),
    i.e. scripts the scope may execute rather than merely read.
    """
    cached = info.path_cache.get(scope_name)
    if cached is not None:
        return cached
    scope = info.scopes.get(scope_name)
    if scope is not None and not scope.path_ops:
        info.path_cache[scope_name] = _EMPTY_REFS
        return _EMPTY_REFS
    info.path_cache[scope_name] = _EMPTY_REFS  # recursion guard
    paths, globs, exec_paths = set(), set(), set()
    repo_wide = False
    if scope_name in ('<module>', '<main>'):
        main_guard = [s for s in info.tree.body
                      if isinstance(s, ast.If) and _is_main_guard(s.test)]
        if scope_name == '<main>':
            groups = [(None, [b for guard in main_guard for b in guard.body])]
        else:
            groups = [(None, [s for s in info.tree.body if s not in main_guard and
                              not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))])]
    else:
        groups = [(node, [node]) for node in _function_nodes(info).get(scope_name, [])]
    for function, roots in groups:
        evaluator = PathEvaluator(info).with_locals(function)
        resolved = {}
        for root in roots:
            for node in _walk_scope(root, function is None):
                if isinstance(node, (ast.BinOp, ast.Call)) or isinstance(node, ast.Name) \
                        and node.id in info.const_exprs and isinstance(node.ctx, ast.Load):
                    value = evaluator.eval(node)
                    if value is not None and value[0] == 'path':
                        resolved[id(node)] = (node, value[1])
                    elif value is not None and value[0] == 'abs':
                        resolved[id(node)] = (node, 'abs:' + value[1])
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                        and node.func.attr in ('glob', 'rglob') and node.args:
                    base = evaluator._as_path(evaluator.eval(node.func.value))
                    pattern = evaluator.eval(node.args[0])
                    if base and base[0] == 'path' and pattern and pattern[0] == 'str':
                        prefix = _glob_prefix(pattern[1])
                        if prefix is not None:
                            joined = _norm(base[1] + '/' + prefix if base[1] else prefix)
                            if joined is not None:
                                if joined == '' and (node.func.attr == 'rglob' or '**' in pattern[1]):
                                    repo_wide = True
                                globs.add(joined)
                if isinstance(node, ast.Call) and _is_subprocess_call(info, node):
                    exec_paths |= _argument_paths(info, evaluator, node)
        # Keep only maximal resolved chains (drop a/b when a/b/c resolved from it).
        inner = set()
        for node, _ in resolved.values():
            for child in ast.iter_child_nodes(node):
                if id(child) in resolved:
                    inner.add(id(child))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and id(node.func.value) in resolved:
                inner.add(id(node.func.value))
        for key, (_, rel) in resolved.items():
            if key not in inner and rel:
                paths.add(rel)
    result = (frozenset(paths), frozenset(globs), repo_wide, frozenset(exec_paths))
    info.path_cache[scope_name] = result
    return result


def _argument_paths(info: ModuleInfo, evaluator, call):
    """Repository paths reachable from a subprocess call's arguments."""
    found = set()
    pending = list(call.args) + [k.value for k in call.keywords]
    seen_names = set()
    while pending:
        node = pending.pop()
        for child in ast.walk(node):
            if isinstance(child, (ast.BinOp, ast.Call, ast.Name, ast.Attribute)):
                value = evaluator.eval(child)
                if value is not None and value[0] == 'path' and value[1]:
                    found.add(value[1])
            if isinstance(child, ast.Name) and child.id in evaluator.local_env \
                    and child.id not in seen_names:
                seen_names.add(child.id)
                pending.append(evaluator.local_env[child.id])
            if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name) \
                    and child.value.id in ('self', 'cls'):
                key = 'self.' + child.attr
                if key in evaluator.local_env and key not in seen_names:
                    seen_names.add(key)
                    pending.append(evaluator.local_env[key])
            if isinstance(child, ast.Call):
                target = _call_target(child.func)
                if target and target[1] in info.functions and target[0] in ('', 'self', 'cls'):
                    found |= _scope_path_refs(info, target[1])[0]
    return found


def _walk_scope(root, skip_functions):
    """ast.walk that does not descend into function bodies when skip_functions."""
    pending = [root]
    while pending:
        node = pending.pop()
        yield node
        for child in ast.iter_child_nodes(node):
            if skip_functions and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            pending.append(child)


def path_references(info: ModuleInfo, scope_names=None):
    """Union of _scope_path_refs over the chosen scopes (all when None)."""
    names = list(info.scopes) if scope_names is None else scope_names
    paths, globs = set(), set()
    repo_wide = False
    for name in names:
        if name not in info.scopes:
            continue
        found, found_globs, wide, _ = _scope_path_refs(info, name)
        paths |= found
        globs |= found_globs
        repo_wide = repo_wide or wide
    return paths, globs, repo_wide


# --------------------------------------------------------------------------
# Reachability and classification
# --------------------------------------------------------------------------

_TOKEN_CACHE = {}


def _is_compiler_token(value: str) -> bool:
    try:
        return _TOKEN_CACHE[value]
    except KeyError:
        result = _TOKEN_CACHE[value] = _is_compiler_token_uncached(value)
        return result


def _is_compiler_token_uncached(value: str) -> bool:
    text = value.strip()
    if not text or '\n' in text or len(text) > 200 or ' ' in text:
        return False
    base = text.rsplit('/', 1)[-1]
    return base in COMPILER_EXACT or bool(COMPILER_PATTERN.match(base))


_REACH_CACHE = {}


def reach(entries, patched=frozenset()):
    """Closure of (module, scope) pairs reachable from the entries (cached)."""
    key = (tuple(sorted(entries)), patched)
    if key not in _REACH_CACHE:
        _REACH_CACHE[key] = frozenset(_reach(entries, patched))
    return _REACH_CACHE[key]


def _reach(entries, patched):
    seen = set()
    work = list(entries)
    while work:
        item = work.pop()
        if item in seen:
            continue
        module, scope_name = item
        info = analyze(module)
        if info is None:
            continue
        seen.add(item)
        if (module, '<module>') not in seen:
            work.append((module, '<module>'))
        if scope_name == '*':
            work.extend((module, s) for s in info.scopes)
            continue
        if scope_name in info.classes:
            work.extend((module, method) for method in info.classes[scope_name])
            continue
        scope = info.scopes.get(scope_name)
        if scope is None:
            continue
        targets = set(scope.calls) | {('', n) for n in scope.names}
        for base, attr in targets:
            if attr in patched:
                continue
            if base == '':
                if attr in info.functions or attr in info.classes:
                    work.append((module, attr))
                elif attr in info.from_imports:
                    work.append(info.from_imports[attr])
                elif attr in info.module_aliases:
                    work.append((info.module_aliases[attr], '<module>'))
            elif base in info.module_aliases:
                work.append((info.module_aliases[base], attr))
            elif base in info.from_imports:
                other_module, other_name = info.from_imports[base]
                work.append((other_module, other_name))
                work.append((other_module, attr))
            elif attr in info.functions:
                work.append((module, attr))
        for whole in info.whole_imports:
            work.append((whole, '*'))
    return seen


class Facts:
    """Signals found in one scope or a closure of scopes."""
    __slots__ = ('compilers', 'sanitize_uncond', 'sanitize_cond', 'tsan', 'retail', 'device',
                 'bash', 'dash_n', 'dash_t', 'subprocess', 'paths', 'exec_paths', 'modules')

    def __init__(self):
        self.compilers = set()
        self.sanitize_uncond = False
        self.sanitize_cond = False
        self.tsan = False
        self.retail = set()
        self.device = set()
        self.bash = self.dash_n = self.dash_t = self.subprocess = False
        self.paths = set()
        self.exec_paths = set()
        self.modules = set()

    def absorb(self, other):
        self.compilers |= other.compilers
        self.sanitize_uncond |= other.sanitize_uncond
        self.sanitize_cond |= other.sanitize_cond
        self.tsan |= other.tsan
        self.retail |= other.retail
        self.device |= other.device
        self.bash |= other.bash
        self.dash_n |= other.dash_n
        self.dash_t |= other.dash_t
        self.subprocess |= other.subprocess
        self.paths |= other.paths
        self.exec_paths |= other.exec_paths
        self.modules |= other.modules


_SCOPE_FACTS = {}
_CLOSURE_FACTS = {}


def _scope_facts(module: str, scope_name: str) -> Facts:
    key = (module, scope_name)
    if key in _SCOPE_FACTS:
        return _SCOPE_FACTS[key]
    facts = Facts()
    facts.modules.add(module)
    info = analyze(module)
    scope = info.scopes.get(scope_name) if info else None
    if scope is not None:
        strings = set(scope.strings)
        for name in scope.names:
            if name in info.const_strings:
                strings |= info.const_strings[name]
            elif name in info.from_imports:
                other_module, other_name = info.from_imports[name]
                other = analyze(other_module)
                if other and other_name in other.const_strings:
                    strings |= other.const_strings[other_name]
        facts.subprocess = scope.subprocess
        facts.compilers = {v.strip() for v in strings if _is_compiler_token(v)}
        sanitizers = {v for v in strings if '-fsanitize' in v}
        conditional = {v for v in sanitizers if v in scope.cond_strings}
        facts.sanitize_uncond = bool(sanitizers - conditional)
        facts.sanitize_cond = bool(conditional)
        # '-fsanitize=thread', or '-fsanitize=' + name with 'thread' among the names.
        facts.tsan = any('sanitize=thread' in v for v in sanitizers) or bool(
            sanitizers and 'thread' in strings)
        facts.retail = {v for v in strings if RETAIL_ENV.match(v)}
        facts.retail |= {v for v in strings if v.startswith('/') and '\n' not in v
                         and any(m in v.lower() for m in RETAIL_ABSOLUTE)}
        facts.device = {m for m in DEVICE_MARKERS if any(m in v for v in strings)}
        facts.bash = 'bash' in strings
        facts.dash_n = '-n' in strings
        facts.dash_t = '-t' in strings
        refs = _scope_path_refs(info, scope_name)
        facts.paths = set(refs[0])
        facts.exec_paths = set(refs[3])
        facts.retail |= {p for p in facts.paths if p == 'retail-pc' or p.startswith('retail-pc/')
                         or p.startswith('abs:') and any(m in p.lower() for m in RETAIL_ABSOLUTE)}
    _SCOPE_FACTS[key] = facts
    return facts


def closure_facts(closure, root: str) -> Facts:
    """Union of scope facts. A helper's module-level scope contributes only its
    import-time subprocess use: its literals are mostly argparse defaults, and
    constants a reached function uses are already folded into that function."""
    key = (closure, root)
    if key not in _CLOSURE_FACTS:
        facts = Facts()
        for module, scope_name in closure:
            scope_facts = _scope_facts(module, scope_name)
            if scope_name == '<module>' and module != root:
                facts.subprocess |= scope_facts.subprocess
                facts.modules |= scope_facts.modules
            else:
                facts.absorb(scope_facts)
        _CLOSURE_FACTS[key] = facts
    return _CLOSURE_FACTS[key]


class Signals:
    def __init__(self):
        self.compile = set()
        self.sanitizer_unconditional = False
        self.sanitizer_conditional = False
        self.tsan = False
        self.retail = set()
        self.device = set()
        self.artifacts = set()
        self.build_scripts = set()
        self.ninja_query = False
        self.invoked = set()


_SCRIPT_CACHE = {}
_SIGNAL_CACHE = {}


def _script_signals(rel: str):
    """Whole-script signals for a tool executed through a subprocess (cached)."""
    if rel not in _SCRIPT_CACHE:
        _SCRIPT_CACHE[rel] = _script_signals_uncached(rel)
    return _SCRIPT_CACHE[rel]


def _script_signals_uncached(rel: str):
    result = {'compile': set(), 'sanitizer': False, 'device': set(), 'build_scripts': set()}
    path = ROOT / rel
    if rel.endswith('.sh'):
        try:
            text = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return result
        for match in SHELL_COMPILER.finditer(text):
            result['compile'].add(match.group(0).strip(' ;&|(`$\n'))
        result['sanitizer'] = '-fsanitize' in text
        for script in BUILD_SCRIPTS:
            if script != rel and PurePosixPath(script).name in text:
                result['build_scripts'].add(script)
        return result
    if not rel.endswith('.py') or rel == RUNNER_PATH:
        return result
    info = analyze(rel)
    if info is None:
        return result
    for scope_name in info.scopes:
        facts = closure_facts(reach([(rel, scope_name)]), rel)
        if facts.subprocess:
            if not (facts.compilers == {'ninja'} and facts.dash_t):
                result['compile'] |= facts.compilers
            if facts.compilers and (facts.sanitize_uncond or facts.sanitize_cond):
                result['sanitizer'] = True
            result['device'] |= facts.device
    result['device'] |= info.device_modules
    return result


def module_signals(rel: str) -> Signals:
    if rel not in _SIGNAL_CACHE:
        _SIGNAL_CACHE[rel] = _module_signals(rel)
    return _SIGNAL_CACHE[rel]


def _module_signals(rel: str) -> Signals:
    info = analyze(rel)
    signals = Signals()
    if info is None:
        return signals
    patched = frozenset(info.patched)
    for scope_name in sorted(info.scopes):
        facts = closure_facts(reach([(rel, scope_name)], patched), rel)
        if facts.subprocess:
            if facts.compilers == {'ninja'} and facts.dash_t:
                signals.ninja_query = True
            elif facts.compilers:
                signals.compile |= facts.compilers
                if facts.sanitize_uncond:
                    signals.sanitizer_unconditional = True
                elif facts.sanitize_cond:
                    signals.sanitizer_conditional = True
                signals.tsan |= facts.tsan
            for module in facts.modules:
                other = analyze(module)
                if other and other.device_modules and module != rel:
                    signals.device |= {'module:' + m for m in other.device_modules}
            signals.device |= facts.device
            syntax_only = facts.bash and facts.dash_n
            for candidate in sorted(facts.exec_paths):
                if candidate == rel or not (ROOT / candidate).is_file():
                    continue
                if candidate.endswith('.py') or candidate.endswith('.sh') and not syntax_only:
                    signals.invoked.add(candidate)
            for script in BUILD_SCRIPTS:
                if script in facts.exec_paths and not syntax_only:
                    signals.build_scripts.add(script)
        signals.retail |= facts.retail
        for module, name in reach([(rel, scope_name)], patched):
            if module != rel and name == '<module>':
                continue  # helper module constants are usually output defaults
            for p in _scope_path_refs(analyze(module), name)[0]:
                if p.startswith(ARTIFACT_PREFIXES) or p.startswith('abs:') and (
                        '/build/' in p or '/local-builder/' in p):
                    signals.artifacts.add(p)
    signals.device |= {'module:' + m for m in info.device_modules}
    for script in sorted(signals.invoked):
        extra = _script_signals(script)
        if extra['compile']:
            signals.compile |= {f'{c} (via {script})' for c in extra['compile']}
        if extra['sanitizer'] and extra['compile']:
            signals.sanitizer_conditional = True
        signals.device |= {f'{d} (via {script})' for d in extra['device']}
        signals.build_scripts |= extra['build_scripts']
    return signals


def module_kind(info: ModuleInfo) -> str:
    if info.has_testcase:
        return 'unittest'
    if info.test_functions:
        return 'functions'
    if info.has_main_block:
        return 'cli-driver' if info.cli_required_args else 'script'
    return 'empty'


def classify(rel: str) -> dict:
    info = analyze(rel)
    if info is None:
        return {'module': _dotted(rel), 'kind': 'unparsable', 'run': 'none', 'lane': 'compiled',
                'tags': ['unparsable'], 'reasons': ['module could not be parsed']}
    signals = module_signals(rel)
    tags = set()
    reasons = []
    if signals.compile:
        tags.add('compiles-host-c++')
        if any('arm-vita-eabi' in c or 'vitasdk' in c for c in signals.compile):
            tags.add('compiles-vita-arm')
        reasons.append('compiler: ' + ', '.join(sorted(signals.compile)))
    if signals.build_scripts:
        tags.add('compiles-host-c++')
        tags.add('runs-build-script')
        reasons.append('runs: ' + ', '.join(sorted(signals.build_scripts)))
    if signals.sanitizer_unconditional:
        tags.add('sanitizer')
        reasons.append('-fsanitize always on')
    elif signals.sanitizer_conditional:
        tags.add('sanitizer-optional')
        reasons.append('-fsanitize behind a condition or in an invoked script')
    if signals.tsan:
        tags.add('tsan')
    if signals.retail:
        tags.add('needs-retail-data')
        if info.uses_skip:
            tags.add('skips-without-retail')
        reasons.append('retail: ' + ', '.join(sorted({_public(v) for v in signals.retail})))
    if signals.device:
        tags.add('needs-device')
        reasons.append('device: ' + ', '.join(sorted(signals.device)))
    if signals.artifacts and info.uses_skip:
        tags.add('optional-build-artifact')
        reasons.append('reads when present (module uses skips): ' +
                       ', '.join(sorted({_public(v) for v in signals.artifacts})))
    elif signals.artifacts:
        tags.add('needs-build-artifact')
        reasons.append('reads: ' + ', '.join(sorted({_public(v) for v in signals.artifacts})))
    if signals.ninja_query:
        tags.add('needs-build-artifact')
        reasons.append('queries an existing ninja build (-t)')
    for name in sorted(info.third_party):
        tags.add('needs-module:' + name)
    paths, globs, _ = path_references(info)
    if 'build' in paths or 'build' in globs:
        tags.add('uses-repo-build-dir')
    if _reaches_upstream(rel):
        tags.add('needs-upstream')
    kind = module_kind(info)
    if kind != 'unittest':
        tags.add('kind:' + kind)
    if 'needs-device' in tags:
        lane = 'device'
    elif 'sanitizer' in tags:
        lane = 'sanitizer'
    elif 'compiles-host-c++' in tags:
        lane = 'compiled'
    elif 'needs-build-artifact' in tags:
        lane = 'artifact'
    elif 'needs-retail-data' in tags:
        lane = 'retail'
    else:
        lane = 'pure'
        tags.add('pure-python')
    override = OVERRIDES.get(rel)
    if override:
        lane = override['lane']
        reasons.append('override: ' + override['reason'])
        tags.add('override')
        tags -= set(override.get('drop_tags', ()))
        if lane == 'pure':
            tags -= {'compiles-host-c++', 'compiles-vita-arm', 'runs-build-script', 'sanitizer',
                     'sanitizer-optional', 'tsan', 'needs-device', 'needs-build-artifact',
                     'needs-retail-data'}
            tags.add('pure-python')
    if kind == 'unittest':
        # Sibling imports without the tools. prefix need the test directory on
        # sys.path, which is what "unittest discover -s <dir> -p <file>" does.
        run = 'discover' if info.bare_local_imports else 'module'
    else:
        run = {'functions': 'functions', 'script': 'script'}.get(kind, 'none')
    return {'module': _dotted(rel), 'kind': kind, 'run': run, 'lane': lane,
            'tags': sorted(tags), 'reasons': reasons}


def _public(value: str) -> str:
    """Manifest-safe form of a path signal: no absolute host or user paths."""
    if value.startswith('abs:'):
        value = value[4:]
    if not value.startswith('/'):
        return value
    for anchor in ('/build/', '/local-builder/', '/retail/', '/Data'):
        if anchor in value:
            return '<absolute>' + value[value.index(anchor):]
    return '<absolute path>'


def _reaches_upstream(rel: str) -> bool:
    """Whether the module or a helper it reaches names upstream/ (the EA checkout)."""
    info = analyze(rel)
    for module, scope_name in reach([(rel, '*')], frozenset(info.patched)):
        other = analyze(module)
        if other is None or scope_name not in other.scopes:
            continue
        if any(p == 'upstream' or p.startswith('upstream/')
               for p in _scope_path_refs(other, scope_name)[0]):
            return True
    return False


def _dotted(rel: str) -> str:
    return '.'.join(PurePosixPath(rel).with_suffix('').parts)


def set_root(root: Path):
    """Point the runner at another repository root (used by the runner's own tests)."""
    global ROOT, MANIFEST_PATH, KNOWN_FAILURES_PATH
    ROOT = Path(root).resolve()
    MANIFEST_PATH = ROOT / 'tools' / 'host_test_manifest.json'
    KNOWN_FAILURES_PATH = ROOT / 'tools' / 'host_test_known_failures.json'
    for cache in (_MODULE_CACHE, _REACH_CACHE, _SCOPE_FACTS, _CLOSURE_FACTS, _SCRIPT_CACHE,
                  _SIGNAL_CACHE):
        cache.clear()


def discover_tests():
    tests = []
    for path in sorted((ROOT / 'tools').rglob('test_*.py')):
        if '__pycache__' in path.parts:
            continue
        tests.append(path.relative_to(ROOT).as_posix())
    return tests


def build_manifest() -> dict:
    tests = {rel: classify(rel) for rel in discover_tests()}
    lanes = {lane: 0 for lane in LANES}
    tag_counts = {}
    kinds = {}
    for entry in tests.values():
        lanes[entry['lane']] += 1
        kinds[entry['kind']] = kinds.get(entry['kind'], 0) + 1
        for tag in entry['tags']:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    return {
        'schema': MANIFEST_SCHEMA,
        'generated_by': RUNNER_PATH,
        'regenerate': REGENERATE_COMMAND,
        'note': 'Static classification only; lanes: ' + ', '.join(LANES) + '.',
        'counts': {'modules': len(tests), 'lanes': lanes,
                   'kinds': dict(sorted(kinds.items())),
                   'tags': dict(sorted(tag_counts.items()))},
        'tests': tests,
    }


def manifest_text(manifest: dict) -> str:
    return json.dumps(manifest, indent=1, sort_keys=False) + '\n'


def _source_fingerprint() -> str:
    """Stat fingerprint of every input the classifier reads (tools/ Python and
    shell sources, including this runner, plus top-level Python modules)."""
    digest = hashlib.sha256()
    paths = list((ROOT / 'tools').rglob('*.py')) + list((ROOT / 'tools').rglob('*.sh'))
    paths += list(ROOT.glob('*.py'))
    for path in sorted(paths):
        if '__pycache__' in path.parts:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        digest.update(f'{path.relative_to(ROOT).as_posix()}\0{stat.st_size}\0'
                      f'{stat.st_mtime_ns}\n'.encode())
    return digest.hexdigest()


def current_manifest(use_cache: bool = True) -> dict:
    """Live classification, reused from build/ while no classifier input changed."""
    cache_path = ROOT / 'build' / CACHE_NAME
    fingerprint = _source_fingerprint() if use_cache else None
    if use_cache:
        try:
            cached = json.loads(cache_path.read_text())
            if cached.get('fingerprint') == fingerprint:
                return cached['manifest']
        except (OSError, ValueError, KeyError, TypeError):
            pass
    manifest = build_manifest()
    if use_cache:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_path.with_suffix('.tmp')
            temporary.write_text(json.dumps({'fingerprint': fingerprint, 'manifest': manifest}))
            temporary.replace(cache_path)
        except OSError:
            pass
    return manifest


# --------------------------------------------------------------------------
# Change impact mapping
# --------------------------------------------------------------------------

def tracked_files():
    try:
        output = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True,
                                check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {p for p in output.decode('utf-8', 'replace').split('\0') if p}


class RepoIndex:
    def __init__(self, files):
        self.files = set(files)
        self.by_basename = {}
        self.dirs = set()
        for path in self.files:
            self.by_basename.setdefault(PurePosixPath(path).name.lower(), set()).add(path)
            parts = path.split('/')
            for i in range(1, len(parts)):
                self.dirs.add('/'.join(parts[:i]))

    def resolve_token(self, token: str):
        token = token.strip('/')
        if token in self.files:
            return {token}, set()
        if token in self.dirs:
            return set(), {token}
        if '/' in token:
            suffix = '/' + token
            matches = {p for p in self.files if p.endswith(suffix)}
            if matches:
                return matches, set()
            dir_matches = {d for d in self.dirs if d.endswith(suffix)}
            return set(), dir_matches
        matches = self.by_basename.get(token.lower(), set())
        if 0 < len(matches) <= BASENAME_MATCH_CAP:
            return set(matches), set()
        return set(), set()


def _string_tokens(strings):
    tokens = set()
    for value in strings:
        if len(value) > 20000:
            value = value[:20000]
        for match in PATH_TOKEN.finditer(value):
            tokens.add(match.group(1))
        for match in DIR_TOKEN.finditer(value):
            tokens.add(match.group(1))
    return tokens


def dependencies_of(rel: str, index: RepoIndex, entry: dict):
    """Files and directory prefixes a test depends on, with a reason for each."""
    info = analyze(rel)
    files, prefixes = {rel: 'test module'}, {}
    if info is None:
        return files, prefixes, False
    closure = reach([(rel, '*')], frozenset(info.patched))
    modules = {m for m, _ in closure}
    for module in sorted(modules - {rel}):
        files.setdefault(module, 'imported helper')
    strings = set()
    include_dirs = set()
    repo_wide = False
    for module in sorted(modules):
        other = analyze(module)
        if other is None:
            continue
        names = None if module == rel else {s for m, s in closure if m == module}
        found, globs, wide = path_references(other, names)
        repo_wide = repo_wide or (wide and module == rel)
        for path in found:
            if path.startswith('abs:'):
                continue
            hit_files, hit_dirs = index.resolve_token(path)
            if path in index.files:
                hit_files = {path}
            for f in hit_files:
                files.setdefault(f, f'path in {module}')
            for d in hit_dirs:
                include_dirs.add(d)
                if '/' in d:  # a top-level directory alone is a join root or -I path
                    prefixes.setdefault(d, f'directory in {module}')
        for glob_prefix in globs:
            if glob_prefix and glob_prefix in index.dirs:
                prefixes.setdefault(glob_prefix, f'glob in {module}')
        if module == rel:
            for scope in other.scopes.values():
                strings |= scope.strings
            for values in other.const_strings.values():
                strings |= values
        else:
            for m, s in closure:
                if m == module and s in other.scopes:
                    strings |= other.scopes[s].strings
    for token in _string_tokens(strings):
        hit_files, hit_dirs = index.resolve_token(token)
        for f in hit_files:
            files.setdefault(f, 'named in source')
        for d in hit_dirs:
            include_dirs.add(d)
            if '/' in d:
                prefixes.setdefault(d, 'directory named in source')
    for script in module_signals(rel).invoked:
        files.setdefault(script, 'executed script')
    if 'compiles-host-c++' in entry.get('tags', ()):
        for include in _include_closure(files, include_dirs | set(prefixes), index):
            files.setdefault(include, 'included by a compiled harness')
    return files, prefixes, repo_wide


def _include_closure(files, include_dirs, index: RepoIndex, depth_limit=6, cap=600):
    pending = [(f, 0) for f in files if PurePosixPath(f).suffix in CXX_EXTENSIONS]
    seen = {f for f, _ in pending}
    include_dirs = sorted(include_dirs)
    found = set()
    while pending and len(found) < cap:
        current, depth = pending.pop()
        if depth >= depth_limit:
            continue
        try:
            text = (ROOT / current).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        for name in INCLUDE_LINE.findall(text):
            candidates = [_norm(str(PurePosixPath(current).parent / name))]
            candidates += [_norm(d + '/' + name) for d in include_dirs]
            candidates.append(_norm(name))
            for candidate in candidates:
                if candidate and candidate in index.files:
                    if candidate not in seen:
                        seen.add(candidate)
                        found.add(candidate)
                        pending.append((candidate, depth + 1))
                    break
    return found


def stage_patch_map(index: RepoIndex):
    """port/patches/<name>.patch -> staged files it rewrites."""
    mapping = {}
    try:
        stage = (ROOT / STAGE_SCRIPT).read_text(encoding='utf-8', errors='replace')
    except OSError:
        stage = ''
    joined = stage.replace('\\\n', ' ')
    applied = {}
    for match in re.finditer(r'-d\s+"\$rv_stage(?:/([\w.+-]+))?"\s+-p(\d+)\s*<\s*'
                             r'"\$rv_root/port/patches/([\w.+-]+\.patch)"', joined):
        applied.setdefault(match.group(3), []).append((match.group(1) or '', int(match.group(2))))
    for path in index.files:
        if not (path.startswith('port/patches/') and path.endswith('.patch')):
            continue
        name = PurePosixPath(path).name
        try:
            text = (ROOT / path).read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        targets = set()
        for line in text.splitlines():
            if line.startswith('+++ ') or line.startswith('--- '):
                target = line[4:].split('\t')[0].strip()
                if target != '/dev/null':
                    targets.add(target)
        staged = set()
        for pool, strip in applied.get(name, []):
            for target in targets:
                parts = target.split('/')[strip:]
                if parts:
                    candidate = _norm('/'.join(['staging', pool] + parts if pool else
                                               ['staging'] + parts))
                    if candidate in index.files:
                        staged.add(candidate)
        if not staged:
            # Fall back to basename matches inside staging/ (conservative).
            for target in targets:
                for hit in index.by_basename.get(PurePosixPath(target).name.lower(), ()):
                    if hit.startswith('staging/'):
                        staged.add(hit)
        mapping[path] = staged
    return mapping


def git_changed_files(spec: str):
    """Changed paths for A..B / A...B ranges, or a single revision vs the work tree."""
    base = ['git', '-C', str(ROOT)]
    if '..' in spec:
        commands = [base + ['diff', '--name-only', '--no-renames', spec]]
    else:
        commands = [base + ['diff', '--name-only', '--no-renames', spec],
                    base + ['ls-files', '--others', '--exclude-standard']]
    changed = set()
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f'git failed ({" ".join(command[3:])}): {result.stderr.strip()}')
        changed |= {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return changed


def stage_script_patch_changes(spec: str):
    """Patches named by a stage_sources.sh diff, or None when other lines changed."""
    command = ['git', '-C', str(ROOT), 'diff', '-U0', '--no-renames', spec, '--', STAGE_SCRIPT]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        return None
    patches = set()
    for line in result.stdout.splitlines():
        if line.startswith(('+++', '---', '@@', 'diff ', 'index ')):
            continue
        if line.startswith(('+', '-')):
            body = line[1:]
            if not STAGE_PATCH_LINE.match(body):
                return None
            patches |= set(PATCH_NAME.findall(body))
    return {'port/patches/' + p for p in patches}


def impacted_tests(changed, manifest_tests, spec=None, unmapped_fallback='compiled', files=None):
    """Map changed paths to test modules. Returns (selected {test: [reasons]}, notes).

    files is the repository file list (default: git ls-files)."""
    index = RepoIndex((tracked_files() if files is None else set(files)) | set(changed))
    notes = []
    selected = {}

    def add(test, reason):
        selected.setdefault(test, [])
        if reason not in selected[test] and len(selected[test]) < 6:
            selected[test].append(reason)

    all_reasons = []
    expanded = set(changed)
    for path in sorted(changed):
        if any(fnmatch.fnmatch(path, pattern) for pattern in ALL_TESTS_PATTERNS) \
                or PurePosixPath(path).name == 'CMakeLists.txt' and '/' not in path:
            all_reasons.append(path)
        elif path == STAGE_SCRIPT:
            patches = stage_script_patch_changes(spec) if spec else None
            if patches is None:
                all_reasons.append(path + ' (non-registration change)')
            else:
                expanded |= patches
                notes.append(f'{path}: patch registration only -> {len(patches)} patch(es)')
    if all_reasons:
        for test in manifest_tests:
            add(test, 'build-system change: ' + ', '.join(all_reasons[:3]))
        return selected, notes + ['build-system change selects every test']
    patch_map = stage_patch_map(index)
    for path in sorted(expanded):
        if path in patch_map:
            for staged in patch_map[path]:
                if staged not in expanded:
                    expanded.add(staged)
        if path.startswith('upstream/'):
            for hit in index.by_basename.get(PurePosixPath(path).name.lower(), ()):
                if hit.startswith('staging/'):
                    expanded.add(hit)
    origin = {path: path for path in changed}
    for patch, staged in patch_map.items():
        if patch in expanded:
            for s in staged:
                origin.setdefault(s, patch)
    for path in expanded:
        origin.setdefault(path, path)
    mapped = set()
    for test, entry in manifest_tests.items():
        files, prefixes, repo_wide = dependencies_of(test, index, entry)
        if repo_wide and changed:
            add(test, 'globs the whole repository')
        for path in expanded:
            hit = None
            if path in files:
                hit = f'{path} ({files[path]})'
            else:
                for prefix, why in prefixes.items():
                    if path.startswith(prefix + '/'):
                        hit = f'{path} under {prefix} ({why})'
                        break
            if hit:
                source = origin.get(path, path)
                if source != path:
                    hit += f' <- {source}'
                add(test, hit)
                mapped.add(path)
                mapped.add(origin.get(path, path))
    unmapped = sorted(p for p in changed if p not in mapped)
    if unmapped:
        notes.append('unmapped changed files: ' + ', '.join(unmapped[:20]) +
                     (' ...' if len(unmapped) > 20 else ''))
        source_like = [p for p in unmapped if PurePosixPath(p).suffix in CXX_EXTENSIONS
                       or p.startswith(('port/', 'staging/', 'upstream/'))]
        if unmapped_fallback == 'all':
            for test in manifest_tests:
                add(test, 'fallback for unmapped change: ' + unmapped[0])
        elif unmapped_fallback == 'compiled' and source_like:
            for test, entry in manifest_tests.items():
                if entry['lane'] in HEAVY_LANES:
                    add(test, 'fallback for unmapped source change: ' + source_like[0])
            notes.append('unmapped C/C++ or port/staging change selects every compiled test')
    return selected, notes


# --------------------------------------------------------------------------
# Execution
# --------------------------------------------------------------------------

RAN_LINE = re.compile(r'^Ran (\d+) tests? in ([\d.]+)s', re.M)
RESULT_LINE = re.compile(r'^(OK|FAILED)(?: \((.*)\))?\s*$', re.M)
FAILED_ID = re.compile(r'^(FAIL|ERROR|UNEXPECTED SUCCESS): (\S+) \(([^)]*)\)', re.M)


def parse_unittest_output(text: str):
    counts = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0,
              'expected_failures': 0, 'unexpected_successes': 0}
    ran = RAN_LINE.findall(text)
    if ran:
        counts['tests'] = int(ran[-1][0])
    results = RESULT_LINE.findall(text)
    verdict = results[-1][0] if results else None
    if results and results[-1][1]:
        for part in results[-1][1].split(','):
            key, _, value = part.strip().partition('=')
            key = key.replace(' ', '_')
            if key in counts and value.isdigit():
                counts[key] = int(value)
    failing = []
    seen = set()
    for kind, method, where in FAILED_ID.findall(text):
        identifier = where if where.endswith('.' + method) else f'{where}.{method}'
        if (kind, identifier) not in seen:  # one entry per test, not per subTest
            seen.add((kind, identifier))
            failing.append({'kind': kind, 'id': identifier})
    return verdict, counts, failing


def load_known_failures():
    try:
        data = json.loads(KNOWN_FAILURES_PATH.read_text())
    except (OSError, ValueError):
        return {}
    return {item['id']: item.get('reason', '') for item in data.get('known_failures', [])}


def _short_module(dotted: str) -> str:
    parts = [p for p in dotted.split('.') if p not in ('tools', 'diagnostics')]
    return parts[0] if parts else dotted


def _module_known(module: str, known) -> bool:
    return module in known or _short_module(module) in known


def is_known_failure(identifier: str, module: str, known) -> bool:
    """Match a failing test id against known entries, with or without the
    package prefix and the class name (test_x.test_method is accepted)."""
    if _module_known(module, known):
        return True
    for key in known:
        if identifier == key or identifier.endswith('.' + key):
            return True
        key_parts = key.split('.')
        id_parts = identifier.split('.')
        if len(key_parts) >= 2 and _short_module(key) == _short_module(identifier) \
                and key_parts[-1] == id_parts[-1]:
            return True
    return False


DURATION_LINE = re.compile(r'^\s*([\d.]+)s\s+(\S+) \(([^)]*)\)', re.M)
STATUS_ORDER = ('pass', 'no-tests', 'fail', 'error', 'timeout')


def load_durations(path: Path):
    """{test: {'seconds': s, 'cases': {test id: s}}} from earlier runs (any schema)."""
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    modules = raw.get('modules', raw) if isinstance(raw, dict) else {}
    durations = {}
    for test, value in modules.items():
        if isinstance(value, (int, float)):
            durations[test] = {'seconds': float(value), 'cases': {}}
        elif isinstance(value, dict) and isinstance(value.get('seconds'), (int, float)):
            durations[test] = {'seconds': float(value['seconds']),
                               'cases': dict(value.get('cases') or {})}
    return durations


def parse_case_durations(text: str, package: str):
    """Per-test seconds from unittest --durations 0 output."""
    _, _, tail = text.partition('Slowest test durations')
    cases = {}
    for seconds, method, where in DURATION_LINE.findall(tail):
        identifier = where if where.endswith('.' + method) else f'{where}.{method}'
        cases[_qualify(identifier, package)] = float(seconds)
    return cases


def _qualify(identifier: str, package: str) -> str:
    # discover mode reports test_x.Class.method; name it like build.sh does.
    if package and not identifier.startswith(package + '.') and not identifier.startswith('unittest.'):
        return package + '.' + identifier
    return identifier


def static_test_ids(rel: str):
    """module.Class.method for every test method defined directly on a TestCase
    subclass, or None when the module cannot be split safely (load_tests,
    mixins, inherited or generated tests)."""
    info = analyze(rel)
    if info is None or 'load_tests' in info.functions:
        return None
    module = _dotted(rel)
    ids = []
    for statement in info.tree.body:
        if not isinstance(statement, ast.ClassDef):
            continue
        methods = [item.name for item in statement.body
                   if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and item.name.startswith('test')]
        bases = [b.attr if isinstance(b, ast.Attribute) else getattr(b, 'id', '')
                 for b in statement.bases]
        direct = any(name.endswith('TestCase') for name in bases) and len(bases) == 1
        if methods and not direct:
            return None
        if direct and not methods:
            return None
        ids += [f'{module}.{statement.name}.{name}' for name in methods]
    return ids or None


def plan_jobs(tests, manifest_tests, args, durations):
    """One job per module, except slow pure/retail modules, which are sharded by
    their recorded per-test durations (longest-processing-time bin packing)."""
    jobs = []
    for test in tests:
        entry = manifest_tests[test]
        record = durations.get(test)
        expected = record['seconds'] if record else DEFAULT_LANE_SECONDS[entry['lane']]
        shards = None
        if args.split_over > 0 and record and record['seconds'] > args.split_over \
                and entry['run'] == 'module' and entry['lane'] in ('pure', 'retail'):
            ids = static_test_ids(test)
            if ids and set(ids) == set(record['cases']) and len(ids) > 1:
                count = min(len(ids), args.jobs,
                            max(2, -(-int(sum(record['cases'].values())) // int(args.split_over))))
                bins = [[0.0, []] for _ in range(count)]
                for identifier in sorted(ids, key=lambda i: (-record['cases'][i], i)):
                    target = min(bins, key=lambda b: b[0])
                    target[0] += record['cases'][identifier]
                    target[1].append(identifier)
                shards = [(load, sorted(group)) for load, group in bins if group]
        if shards and len(shards) > 1:
            for index, (load, group) in enumerate(shards, 1):
                jobs.append({'test': test, 'entry': entry, 'ids': group,
                             'label': f'{entry["module"]} [{index}/{len(shards)}]',
                             'log_name': f'{entry["module"]}.shard{index}', 'expected': load})
        else:
            jobs.append({'test': test, 'entry': entry, 'ids': None, 'label': entry['module'],
                         'log_name': entry['module'], 'expected': expected})
    return jobs


def run_job(job, args, temp_root, log_dir, aslr_wrap):
    test, entry = job['test'], job['entry']
    module = entry['module']
    kind = entry['kind']
    python = args.python
    timing = ['--durations', '0'] if sys.version_info >= (3, 12) else []
    if entry['run'] == 'module':
        command = [python, '-m', 'unittest', '-v', *timing, *(job['ids'] or [module])]
    elif entry['run'] == 'discover':
        directory = str(PurePosixPath(test).parent)
        command = [python, '-m', 'unittest', 'discover', '-v', *timing, '-s', directory,
                   '-t', directory, '-p', PurePosixPath(test).name]
    elif entry['run'] == 'functions':
        command = [python, str(ROOT / RUNNER_PATH), '--run-function-tests', test]
    else:
        command = [python, str(ROOT / test)]
    if aslr_wrap and 'tsan' in entry['tags']:
        command = ['setarch', platform.machine(), '-R'] + command
    temp = Path(tempfile.mkdtemp(prefix=job['log_name'].replace('.', '_') + '-', dir=temp_root))
    environment = os.environ.copy()
    environment.update({'TMPDIR': str(temp), 'TEMP': str(temp), 'TMP': str(temp),
                        'PYTHONUNBUFFERED': '1', 'RENEGADE_HOST_TEST_LANE': entry['lane']})
    log_path = log_dir / (job['log_name'] + '.log')
    begin = time.monotonic()
    status = None
    try:
        with log_path.open('wb') as log:
            log.write(('$ ' + ' '.join(command) + '\n').encode())
            log.flush()
            process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                       env=environment, start_new_session=True)
            with _LIVE_LOCK:
                _LIVE.add(process)
            try:
                code = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                _kill_group(process)
                code = None
                status = 'timeout'
            finally:
                with _LIVE_LOCK:
                    _LIVE.discard(process)
    except OSError as error:
        code = None
        status = 'error'
        log_path.write_text(f'runner could not start {command}: {error}\n')
    seconds = time.monotonic() - begin
    if not args.keep_temp:
        shutil.rmtree(temp, ignore_errors=True)
    text = log_path.read_text(encoding='utf-8', errors='replace')
    verdict, counts, failing = parse_unittest_output(text)
    package = module.rpartition('.')[0]
    for item in failing:
        item['id'] = _qualify(item['id'], package)
    if status is None:
        if code == 0 and kind in ('unittest', 'functions') and counts['tests'] == 0:
            status = 'no-tests'
        elif code == 0:
            status = 'pass'
        elif code == 5 and counts['tests'] == 0:
            status = 'no-tests'
        elif verdict == 'FAILED':
            status = 'fail'
        else:
            status = 'error'
    return {'test': test, 'module': module, 'lane': entry['lane'], 'kind': kind,
            'status': status, 'exit_code': code, 'seconds': round(seconds, 3), **counts,
            'failing': failing, 'log': str(log_path), 'label': job['label'],
            'cases': parse_case_durations(text, package)}


def merge_results(job_results):
    """Combine shard results into one record per test module."""
    merged = {}
    for result in job_results:
        current = merged.get(result['test'])
        if current is None:
            merged[result['test']] = dict(result, logs=[result['log']], shards=1,
                                          wall=result['seconds'])
            continue
        current['shards'] += 1
        current['logs'].append(result['log'])
        current['wall'] = max(current['wall'], result['seconds'])
        current['seconds'] = round(current['seconds'] + result['seconds'], 3)
        for key in ('tests', 'failures', 'errors', 'skipped', 'expected_failures',
                    'unexpected_successes'):
            current[key] += result[key]
        current['failing'] = current['failing'] + result['failing']
        current['cases'] = {**current['cases'], **result['cases']}
        if STATUS_ORDER.index(result['status']) > STATUS_ORDER.index(current['status']):
            current['status'] = result['status']
            current['exit_code'] = result['exit_code']
    for record in merged.values():
        record['log'] = record['logs'][0] if len(record['logs']) == 1 else \
            ', '.join(record['logs'])
    return list(merged.values())


_LIVE = set()
_LIVE_LOCK = threading.Lock()


def _kill_live_processes():
    with _LIVE_LOCK:
        live = list(_LIVE)
    for process in live:
        _kill_group(process)


def _kill_group(process):
    for sig, wait in ((signal.SIGTERM, 5), (signal.SIGKILL, 5)):
        try:
            os.killpg(process.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            process.wait(timeout=wait)
            return
        except subprocess.TimeoutExpired:
            continue


def run_function_tests(rel: str) -> int:
    """Child mode: run module-level test_* functions (pytest style) without pytest."""
    import importlib.util
    import inspect
    sys.path.insert(0, str(ROOT))
    sys.path.insert(1, str((ROOT / rel).parent))
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(_dotted(rel), path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    begin = time.monotonic()
    try:
        spec.loader.exec_module(module)
    except Exception:
        traceback.print_exc()
        print(f'\nERROR: module import ({_dotted(rel)}.module_import)')
        print('\nRan 0 tests in 0.000s\n\nFAILED (errors=1)')
        return 1
    names = sorted(n for n, v in vars(module).items()
                   if n.startswith('test') and inspect.isfunction(v) and v.__module__ == spec.name)
    failures = errors = 0
    reports = []
    for name in names:
        function = getattr(module, name)
        if inspect.signature(function).parameters:
            errors += 1
            reports.append(('ERROR', name, 'requires pytest fixtures; not runnable without pytest'))
            print(f'{name} ({spec.name}.{name}) ... ERROR')
            continue
        try:
            function()
            print(f'{name} ({spec.name}.{name}) ... ok')
        except AssertionError:
            failures += 1
            reports.append(('FAIL', name, traceback.format_exc()))
            print(f'{name} ({spec.name}.{name}) ... FAIL')
        except Exception:
            errors += 1
            reports.append(('ERROR', name, traceback.format_exc()))
            print(f'{name} ({spec.name}.{name}) ... ERROR')
    for kind, name, detail in reports:
        print('=' * 70)
        print(f'{kind}: {name} ({spec.name}.{name})')
        print('-' * 70)
        print(detail)
    print('-' * 70)
    print(f'Ran {len(names)} tests in {time.monotonic() - begin:.3f}s\n')
    if failures or errors:
        parts = [f'failures={failures}'] if failures else []
        parts += [f'errors={errors}'] if errors else []
        print(f'FAILED ({", ".join(parts)})')
        return 1
    print('OK')
    return 0 if names else 5


def schedule(jobs, args):
    """Run jobs in parallel, longest expected first, limiting heavy lanes."""
    pending = sorted(jobs, key=lambda j: (-j['expected'], j['label']))
    temp_root = Path(tempfile.mkdtemp(prefix='renegade-host-tests-'))
    stamp = time.strftime('%Y%m%d-%H%M%S')
    log_dir = Path(args.log_dir) if args.log_dir else ROOT / 'build' / 'host-test-logs' / stamp
    log_dir.mkdir(parents=True, exist_ok=True)
    aslr_wrap = not args.no_aslr_wrap and shutil.which('setarch') is not None \
        and sys.platform.startswith('linux')
    done = queue.Queue()
    running = {}
    results = []
    heavy_running = 0
    total = len(pending)
    try:
        while pending or running:
            started = True
            while started and pending and len(running) < args.jobs:
                started = False
                for i, job in enumerate(pending):
                    heavy = job['entry']['lane'] in HEAVY_LANES
                    if heavy and heavy_running >= args.heavy_jobs:
                        continue
                    pending.pop(i)
                    heavy_running += heavy

                    def worker(job=job):
                        try:
                            result = run_job(job, args, temp_root, log_dir, aslr_wrap)
                        except Exception as error:  # keep the scheduler alive
                            entry = job['entry']
                            result = {'test': job['test'], 'module': entry['module'],
                                      'lane': entry['lane'], 'kind': entry['kind'],
                                      'status': 'error', 'exit_code': None, 'seconds': 0.0,
                                      'tests': 0, 'failures': 0, 'errors': 1, 'skipped': 0,
                                      'expected_failures': 0, 'unexpected_successes': 0,
                                      'failing': [], 'log': f'runner exception: {error}',
                                      'label': job['label'], 'cases': {}}
                        done.put((job['label'], result))

                    thread = threading.Thread(target=worker, daemon=True)
                    running[job['label']] = heavy
                    thread.start()
                    started = True
                    break
            try:
                label, result = done.get()
            except KeyboardInterrupt:
                _kill_live_processes()
                raise
            heavy_running -= running.pop(label)
            results.append(result)
            print(f'[{len(results):>3}/{total}] {result["status"].upper():<8} '
                  f'{result["seconds"]:>7.2f}s {result["lane"]:<9} {label} '
                  f'({result["tests"]} tests)', flush=True)
    finally:
        if not args.keep_temp:
            shutil.rmtree(temp_root, ignore_errors=True)
    return merge_results(results), log_dir


def print_summary(results, wall, args, known, selection_note):
    serial = sum(r['seconds'] for r in results)
    tests_run = sum(r['tests'] for r in results)
    print('\n' + '=' * 78)
    print(f'Host test summary ({selection_note})')
    print('=' * 78)
    header = f'{"lane":<10}{"modules":>8}{"pass":>6}{"fail":>6}{"other":>7}{"cases":>7}{"seconds":>10}'
    print(header)
    for lane in LANES:
        rows = [r for r in results if r['lane'] == lane]
        if not rows:
            continue
        passed = sum(r['status'] == 'pass' for r in rows)
        failed = sum(r['status'] in ('fail', 'error', 'timeout', 'no-tests') for r in rows)
        other = len(rows) - passed - failed
        print(f'{lane:<10}{len(rows):>8}{passed:>6}{failed:>6}{other:>7}'
              f'{sum(r["tests"] for r in rows):>7}{sum(r["seconds"] for r in rows):>10.1f}')
    print('-' * 78)
    print(f'modules {len(results)}, test cases {tests_run}, wall {wall:.1f}s, '
          f'sum of module time {serial:.1f}s, parallel speedup x{(serial / wall) if wall else 0:.2f} '
          f'(jobs {args.jobs}, heavy {args.heavy_jobs})')
    slowest = sorted(results, key=lambda r: -r['seconds'])[:args.slowest]
    if slowest:
        print(f'\nSlowest {len(slowest)} modules:')
        for r in slowest:
            shards = (f'  ({r["shards"]} shards, longest {r["wall"]:.2f}s)'
                      if r.get('shards', 1) > 1 else '')
            print(f'  {r["seconds"]:>8.2f}s  {r["lane"]:<9} {r["status"]:<8} {r["module"]}{shards}')
    bad = [r for r in results if r['status'] in ('fail', 'error', 'timeout', 'no-tests')]
    unknown_bad = []
    if bad:
        print('\nProblems:')
        for r in sorted(bad, key=lambda r: r['module']):
            ids = [f['id'] for f in r['failing']]
            known_ids = [i for i in ids if is_known_failure(i, r['module'], known)]
            is_known = _module_known(r['module'], known) or bool(ids and len(known_ids) == len(ids))
            if not is_known:
                unknown_bad.append(r)
            label = 'KNOWN ' if is_known else ''
            print(f'  {label}{r["status"].upper()} {r["module"]}  log: {r["log"]}')
            for item in r['failing'][:8]:
                mark = ' (known)' if is_known_failure(item['id'], r['module'], known) else ''
                print(f'      {item["kind"]}: {item["id"]}{mark}')
            if not r['failing']:
                tail = _log_tail(r['log'])
                for line in tail:
                    print('      | ' + line)
    return bad, unknown_bad


def _log_tail(path, lines=12):
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return []
    return text[-lines:]


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('patterns', nargs='*',
                        help='test modules or fnmatch patterns (tools.test_x, tools/test_x.py, '
                             '"*sampler*")')
    parser.add_argument('--lanes', default=None,
                        help='comma-separated lanes to run (default: every lane)')
    parser.add_argument('--pure-only', action='store_true',
                        help='run only the pure lane (no compiler, retail, artifact or device)')
    parser.add_argument('--changed', metavar='GIT_RANGE',
                        help='select tests impacted by A..B, A...B, or one revision versus the '
                             'work tree (includes untracked files)')
    parser.add_argument('--unmapped-fallback', choices=('none', 'compiled', 'all'),
                        default='compiled',
                        help='what an unmapped changed file selects (default: compiled lanes '
                             'for unmapped C/C++ or port/staging/upstream files)')
    parser.add_argument('--jobs', '-j', type=int, default=os.cpu_count() or 2)
    parser.add_argument('--heavy-jobs', type=int, default=None,
                        help='concurrent compiled/sanitizer/device modules (default: jobs // 2)')
    parser.add_argument('--timeout', type=float, default=900.0, help='seconds per module')
    parser.add_argument('--python', default=sys.executable, help='interpreter for the tests')
    parser.add_argument('--list', action='store_true', help='print the selection and exit')
    parser.add_argument('--explain', action='store_true', help='show why each test was selected')
    parser.add_argument('--summary', type=Path, default=None,
                        help='JSON summary path (default build/host-test-summary.json)')
    parser.add_argument('--log-dir', default=None, help='per-module logs (default build/host-test-logs/<time>)')
    parser.add_argument('--durations', type=Path, default=ROOT / 'build' / 'host-test-durations.json',
                        help='duration history used for longest-first scheduling')
    parser.add_argument('--slowest', type=int, default=15)
    parser.add_argument('--split-over', type=float, default=0.0, metavar='SECONDS',
                        help='shard a pure/retail module whose last run took longer than this '
                             'across workers by recorded per-test time (default 0: off; on the '
                             '4-core reference laptop it did not shorten the pure lane)')
    parser.add_argument('--keep-temp', action='store_true')
    parser.add_argument('--no-cache', action='store_true',
                        help='reclassify instead of reusing build/' + CACHE_NAME)
    parser.add_argument('--no-aslr-wrap', action='store_true',
                        help='do not run tsan-tagged modules under setarch -R')
    parser.add_argument('--include-cli-drivers', action='store_true',
                        help='also run test_* files that are argparse drivers (normally excluded)')
    parser.add_argument('--allow-known-failures', action='store_true',
                        help='exit 0 when every problem is listed in tools/host_test_known_failures.json')
    parser.add_argument('--strict', action='store_true',
                        help='treat missing third-party modules as failures instead of skips')
    parser.add_argument('--write-manifest', action='store_true',
                        help='regenerate tools/host_test_manifest.json and exit')
    parser.add_argument('--check-manifest', action='store_true',
                        help='exit 3 if tools/host_test_manifest.json is out of date')
    parser.add_argument('--run-function-tests', metavar='TEST', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error('--jobs must be at least 1')
    if args.heavy_jobs is None:
        args.heavy_jobs = max(1, args.jobs // 2)
    if args.heavy_jobs < 1:
        parser.error('--heavy-jobs must be at least 1')
    if args.pure_only and args.lanes:
        parser.error('--pure-only and --lanes are exclusive')
    lanes = ['pure'] if args.pure_only else (
        [lane.strip() for lane in args.lanes.split(',') if lane.strip()] if args.lanes else list(LANES))
    unknown = [lane for lane in lanes if lane not in LANES]
    if unknown:
        parser.error('unknown lane(s): ' + ', '.join(unknown) + '; choose from ' + ', '.join(LANES))
    args.lane_set = set(lanes)
    return args


def _match(patterns, test, entry):
    for pattern in patterns:
        candidates = (test, entry['module'], PurePosixPath(test).name, PurePosixPath(test).stem)
        if any(fnmatch.fnmatch(c, pattern) for c in candidates):
            return True
    return False


def main(argv=None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exit_request:
        return 2 if exit_request.code not in (0, None) else 0
    if args.run_function_tests:
        return run_function_tests(args.run_function_tests)
    fresh = args.write_manifest or args.check_manifest or args.no_cache
    manifest = build_manifest() if fresh else current_manifest()
    if args.write_manifest:
        MANIFEST_PATH.write_text(manifest_text(manifest))
        counts = manifest['counts']
        print(f'Wrote {MANIFEST_PATH.relative_to(ROOT)}: {counts["modules"]} modules; '
              + ', '.join(f'{k} {v}' for k, v in counts['lanes'].items()))
        return 0
    if args.check_manifest:
        try:
            current = MANIFEST_PATH.read_text()
        except OSError:
            current = ''
        if current != manifest_text(manifest):
            print(f'{MANIFEST_PATH.relative_to(ROOT)} is out of date; run: {REGENERATE_COMMAND}')
            return 3
        print('Host test manifest is up to date.')
        return 0
    tests = manifest['tests']
    selection = dict.fromkeys(tests, None)
    reasons = {}
    note = 'all modules'
    if args.patterns:
        selection = {t: None for t, e in tests.items() if _match(args.patterns, t, e)}
        if not selection:
            print('No test module matches: ' + ' '.join(args.patterns), file=sys.stderr)
            return 2
        note = 'pattern selection'
    if args.changed:
        try:
            changed = git_changed_files(args.changed)
        except RuntimeError as error:
            print(error, file=sys.stderr)
            return 2
        impacted, notes = impacted_tests(changed, tests, args.changed, args.unmapped_fallback)
        for line in notes:
            print('note: ' + line)
        reasons = impacted
        selection = {t: None for t in selection if t in impacted}
        note = f'changed {args.changed}: {len(changed)} files'
    excluded = {}
    chosen = []
    for test in selection:
        entry = tests[test]
        if entry['lane'] not in args.lane_set:
            continue
        if entry['run'] == 'none' and not (args.include_cli_drivers
                                           and entry['kind'] == 'cli-driver'):
            excluded[test] = f'{entry["kind"]} (not a runnable unit test)'
            continue
        chosen.append(test)
    note += '; lanes ' + ','.join(lane for lane in LANES if lane in args.lane_set)
    unavailable = {}
    for test in list(chosen):
        missing = [tag.split(':', 1)[1] for tag in tests[test]['tags']
                   if tag.startswith('needs-module:') and not _module_available(tag.split(':', 1)[1],
                                                                                 args.python)]
        if missing and not args.strict:
            unavailable[test] = 'missing Python module(s): ' + ', '.join(missing)
            chosen.remove(test)
    if args.list:
        for test in sorted(chosen):
            entry = tests[test]
            print(f'{entry["lane"]:<10}{entry["module"]:<64}{",".join(entry["tags"])}')
            if args.explain:
                for line in entry['reasons']:
                    print('    class: ' + line)
                for line in reasons.get(test, []):
                    print('    because: ' + line)
        for test, why in sorted({**excluded, **unavailable}.items()):
            print(f'{"skipped":<10}{tests[test]["module"]:<64}{why}')
        print(f'{len(chosen)} module(s) selected ({note})')
        return 0
    upstream = ROOT / 'upstream' / 'CnC_Renegade' / 'Code'
    needing = [t for t in chosen if 'needs-upstream' in tests[t]['tags']]
    if needing and not upstream.is_dir():
        print(f'warning: {len(needing)} selected module(s) read upstream/CnC_Renegade, which is '
              'missing here; link the canonical checkout (e.g. ln -s <main>/upstream/CnC_Renegade '
              'upstream/CnC_Renegade) or expect failures.', file=sys.stderr)
    for test, why in sorted(unavailable.items()):
        print(f'unavailable: {tests[test]["module"]}: {why}')
    if not chosen:
        print(f'No test modules selected ({note}).')
        return 0
    (ROOT / 'build').mkdir(exist_ok=True)
    durations = load_durations(args.durations)
    jobs = plan_jobs(chosen, tests, args, durations)
    shards = len(jobs) - len(chosen)
    print(f'Running {len(chosen)} module(s) as {len(jobs)} job(s) with {args.jobs} worker(s)'
          f'{f" ({shards} extra shard(s) for slow modules)" if shards else ""} ({note})',
          flush=True)
    begin = time.monotonic()
    try:
        results, log_dir = schedule(jobs, args)
    except KeyboardInterrupt:
        _kill_live_processes()
        print('\ninterrupted', file=sys.stderr)
        return 130
    wall = time.monotonic() - begin
    known = load_known_failures()
    bad, unknown_bad = print_summary(results, wall, args, known, note)
    for result in results:
        if result['status'] in ('pass', 'fail'):
            durations[result['test']] = {'seconds': result['seconds'],
                                         'cases': result['cases']}
    try:
        args.durations.parent.mkdir(parents=True, exist_ok=True)
        args.durations.write_text(json.dumps({'schema': 2, 'modules': dict(sorted(
            durations.items()))}, indent=1) + '\n')
    except OSError:
        pass
    if bad and args.allow_known_failures and not unknown_bad:
        exit_code = 0
    else:
        exit_code = 1 if bad else 0
    summary_path = args.summary or ROOT / 'build' / 'host-test-summary.json'
    summary = {
        'evidence_class': 'host', 'runner': RUNNER_PATH, 'selection': note,
        'lanes': sorted(args.lane_set), 'jobs': args.jobs, 'heavy_jobs': args.heavy_jobs,
        'timeout_seconds': args.timeout, 'python': args.python,
        'wall_seconds': round(wall, 3),
        'sum_module_seconds': round(sum(r['seconds'] for r in results), 3),
        'modules': len(results), 'tests_run': sum(r['tests'] for r in results),
        'status_counts': {s: sum(r['status'] == s for r in results)
                          for s in sorted({r['status'] for r in results})},
        'excluded': excluded, 'unavailable': unavailable,
        'known_failures_matched': sorted({f['id'] for r in bad for f in r['failing']
                                          if is_known_failure(f['id'], r['module'], known)}),
        'exit_code': exit_code, 'log_dir': str(log_dir),
        'results': sorted(results, key=lambda r: r['module']),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=1) + '\n')
    print(f'\nSummary: {summary_path}   logs: {log_dir}')
    print('RESULT: ' + ('PASS' if exit_code == 0 else 'FAIL') +
          (f' ({len(bad)} known problem(s) allowed)' if bad and exit_code == 0 else ''))
    return exit_code


_MODULE_AVAILABILITY = {}


def _module_available(name: str, python: str) -> bool:
    key = (name, python)
    if key not in _MODULE_AVAILABILITY:
        if python == sys.executable:
            import importlib.util
            _MODULE_AVAILABILITY[key] = importlib.util.find_spec(name) is not None
        else:
            result = subprocess.run([python, '-c', f'import importlib.util,sys;'
                                     f'sys.exit(importlib.util.find_spec({name!r}) is None)'],
                                    capture_output=True)
            _MODULE_AVAILABILITY[key] = result.returncode == 0
    return _MODULE_AVAILABILITY[key]


if __name__ == '__main__':
    raise SystemExit(main())
