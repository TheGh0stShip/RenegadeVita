"""Content-addressed dependency cache: keys, verified hits, misses, rejection.

Synthetic inputs only; nothing here fetches, configures or compiles.
"""

import contextlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from tools import dependency_cache as dc

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        status = dc.main(list(argv))
    return status, out.getvalue(), err.getvalue()


def write(path, data, mode=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    if mode is not None:
        os.chmod(path, mode)
    return path


def snapshot(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        result[relative] = path.read_bytes() if path.is_file() else None
    return result


class InputFixture:
    """A synthetic dependency: archive, two patches, script, toolchain, tree."""

    def __init__(self, base):
        self.base = Path(base)
        self.source = write(self.base / 'source.tar.gz', b'pinned archive bytes')
        self.patch_a = write(self.base / 'patches/a.patch', '--- a\n+++ b\n@@ a @@\n')
        self.patch_b = write(self.base / 'patches/b.patch', '--- c\n+++ d\n@@ b @@\n')
        self.script = write(self.base / 'tools/build_dep.sh', '#!/bin/sh\nmake\n')
        self.gcc = write(self.base / 'sdk/bin/arm-vita-eabi-gcc', b'\x7fELF driver')
        write(self.base / 'tree/source/ffp.c', 'int f(void) { return 1; }\n')
        write(self.base / 'tree/source/shaders/ffp_v.h', '#define V 1\n')
        self.tree = self.base / 'tree'

    def entries(self, patch_order=('a', 'b'), flags='-O3 -mtune=cortex-a9',
                gcc_version='arm-vita-eabi-gcc 15.2.0'):
        patches = {'a': self.patch_a, 'b': self.patch_b}
        entries = [('script', str(self.script)), ('source', str(self.source))]
        entries += [('patch', str(patches[name])) for name in patch_order]
        entries += [('tree', f'compiled_tree={self.tree}'),
                    ('file', f'gcc_driver={self.gcc}'),
                    ('value', f'gcc_version={gcc_version}'),
                    ('flags', flags)]
        return entries

    def relocated(self, base):
        """The same inputs copied below another root (another worktree)."""
        clone = InputFixture.__new__(InputFixture)
        clone.base = Path(base)
        for attribute in ('source', 'patch_a', 'patch_b', 'script', 'gcc', 'tree'):
            setattr(clone, attribute, clone.base / getattr(self, attribute).relative_to(self.base))
        return clone

    def key(self, name='vitagl-demo', **options):
        components = dc.build_components(self.entries(**options), ['*.o', '*.a'])
        return dc.compute_key(name, components)[0]


class KeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='renegade-depcache-key-')
        self.fixture = InputFixture(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_same_content_gives_same_key_in_another_worktree(self):
        other = Path(self.temp.name) / 'other-worktree'
        shutil.copytree(self.fixture.base, other, ignore=shutil.ignore_patterns('other-worktree'))
        relocated = self.fixture.relocated(other)
        self.assertNotEqual(relocated.source, self.fixture.source)
        self.assertEqual(relocated.key(), self.fixture.key())
        self.assertRegex(self.fixture.key(), r'^[0-9a-f]{64}$')

    def test_every_input_change_misses(self):
        base = self.fixture.key()
        keys = {'base': base}

        def mutate(label, path, data):
            original = Path(path).read_bytes()
            write(path, data)
            keys[label] = self.fixture.key()
            write(path, original)

        mutate('source', self.fixture.source, b'different archive bytes')
        mutate('patch', self.fixture.patch_b, '--- c\n+++ d\n@@ changed @@\n')
        mutate('script', self.fixture.script, '#!/bin/sh\nmake -j9\n')
        mutate('toolchain_file', self.fixture.gcc, b'\x7fELF other driver')
        mutate('tree_content', self.fixture.tree / 'source/ffp.c', 'int f(void) { return 2; }\n')
        keys['patch_order'] = self.fixture.key(patch_order=('b', 'a'))
        keys['toolchain_value'] = self.fixture.key(gcc_version='arm-vita-eabi-gcc 15.3.0')
        keys['flags'] = self.fixture.key(flags='-O2 -mtune=cortex-a9')
        keys['name'] = self.fixture.key(name='vitagl-other')
        added = write(self.fixture.tree / 'source/new.c', 'int g;\n')
        keys['tree_new_file'] = self.fixture.key()
        added.unlink()
        self.assertEqual(self.fixture.key(), base, 'restoring every input restores the key')
        self.assertEqual(len(set(keys.values())), len(keys), keys)

    def test_build_products_in_tree_do_not_change_key(self):
        base = self.fixture.key()
        write(self.fixture.tree / 'source/ffp.o', b'object')
        write(self.fixture.tree / 'source/libvitaGL.a', b'archive')
        self.assertEqual(self.fixture.key(), base)

    def test_missing_input_cannot_produce_a_key(self):
        with self.assertRaises(dc.CacheError):
            dc.build_components([('source', str(Path(self.temp.name) / 'absent.tar.gz'))], [])
        with self.assertRaises(dc.CacheError):
            dc.build_components([('file', 'no-label-separator')], [])

    def test_cli_key_writes_matching_explain_document(self):
        explain = Path(self.temp.name) / 'explain.json'
        status, out, _ = run_cli('key', '--name', 'ffmpeg-bink-vita',
                                 '--script', str(self.fixture.script),
                                 '--source', str(self.fixture.source),
                                 '--value', 'config_id=v3', '--flags=-O3',
                                 '--explain-out', str(explain))
        self.assertEqual(status, dc.EXIT_OK)
        key = out.strip()
        document = explain.read_text().strip()
        self.assertEqual(dc.sha256_text(document), key)
        parsed = json.loads(document)
        self.assertEqual([c[0] for c in parsed['components']], ['script', 'source', 'value', 'flags'])
        self.assertEqual(parsed['components'][-1], ['flags', '', '-O3'])
        status, out, _ = run_cli('key', '--name', 'x', '--flags=-g -Wl,-q -O3')
        self.assertEqual((status, len(out.strip())), (dc.EXIT_OK, 64))
        self.assertNotIn(self.temp.name, document, 'keys must not depend on paths')


class StoreRestoreTests(unittest.TestCase):
    KEY = 'a' * 64

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='renegade-depcache-store-')
        self.base = Path(self.temp.name)
        self.cache = self.base / 'cache'
        self.prefix = self.base / 'producer/build/deps/ffmpeg-bink-vita'
        write(self.prefix / 'include/libavcodec/avcodec.h', '#define AVCODEC 1\n')
        write(self.prefix / 'lib/libavcodec.a', b'!<arch>\nmembers', 0o644)
        write(self.prefix / 'lib/pkgconfig/libavcodec.pc', f'prefix={self.prefix}\n')
        write(self.prefix / 'share/tool.sh', '#!/bin/sh\n', 0o755)
        (self.prefix / 'share/ffmpeg/examples').mkdir(parents=True)
        write(self.prefix / '.renegade-bink-build', 'ffmpeg-9.0.1-v3\n')
        self.outputs = ['include', 'lib', 'share']

    def tearDown(self):
        self.temp.cleanup()

    def store(self, key=None, **options):
        return dc.store(self.cache, 'ffmpeg-bink-vita', key or self.KEY, self.prefix,
                        self.outputs, **options)

    def restore_cli(self, dest, key=None, outputs=None, replace=True):
        argv = ['restore', '--cache-dir', str(self.cache), '--name', 'ffmpeg-bink-vita',
                '--key', key or self.KEY, '--dest', str(dest)]
        if replace:
            argv.append('--replace-dest')
        return run_cli(*argv, *(outputs or self.outputs))

    def entry(self, key=None):
        return self.cache / 'ffmpeg-bink-vita' / (key or self.KEY)

    def test_verified_hit_restores_identical_bytes_modes_and_fresh_mtimes(self):
        for path in self.prefix.rglob('*'):
            os.utime(path, (1_000_000, 1_000_000))
        self.assertEqual(self.store(), 'stored')
        dest = self.base / 'consumer/build/deps/ffmpeg-bink-vita'
        started = time.time() - 2
        status, out, _ = self.restore_cli(dest)
        self.assertEqual(status, dc.EXIT_OK, out)
        self.assertIn('verified hit', out)
        expected = {k: v for k, v in snapshot(self.prefix).items() if k != '.renegade-bink-build'}
        self.assertEqual(snapshot(dest), expected)
        self.assertTrue((dest / 'share/ffmpeg/examples').is_dir(), 'empty directories survive')
        self.assertEqual(os.stat(dest / 'share/tool.sh').st_mode & 0o777, 0o755)
        self.assertEqual(os.stat(dest / 'lib/libavcodec.a').st_mode & 0o777, 0o644)
        # Fresh mtimes force ninja to relink against a restored library.
        self.assertGreaterEqual(os.stat(dest / 'lib/libavcodec.a').st_mtime, started)
        self.assertEqual(list(dest.parent.glob('.*depcache*')), [], 'no staging debris')

    def test_miss_reports_exit_3_and_leaves_destination_untouched(self):
        dest = self.base / 'consumer'
        write(dest / 'keep.txt', 'unchanged')
        before = snapshot(dest)
        status, out, _ = self.restore_cli(dest)
        self.assertEqual(status, dc.EXIT_MISS)
        self.assertIn('miss', out)
        self.assertEqual(snapshot(dest), before)

    def test_replace_dest_drops_stale_prefix_content(self):
        self.store()
        dest = self.base / 'consumer'
        write(dest / 'lib/libstale.a', b'old')
        write(dest / '.renegade-bink-build', 'stale-config\n')
        self.assertEqual(self.restore_cli(dest)[0], dc.EXIT_OK)
        self.assertFalse((dest / 'lib/libstale.a').exists())
        self.assertFalse((dest / '.renegade-bink-build').exists(), 'the script rewrites its stamp')

    def test_per_output_restore_preserves_unrelated_files(self):
        work = self.base / 'producer/vitagl-demo'
        write(work / 'libvitaGL.a', b'new library')
        dc.store(self.cache, 'vitagl-demo', self.KEY, work, ['libvitaGL.a'])
        dest = self.base / 'consumer/vitagl-demo'
        write(dest / 'libvitaGL.a', b'previous library')
        write(dest / 'source.tar.gz', b'archive')
        status, _, _ = run_cli('restore', '--cache-dir', str(self.cache), '--name', 'vitagl-demo',
                               '--key', self.KEY, '--dest', str(dest), 'libvitaGL.a')
        self.assertEqual(status, dc.EXIT_OK)
        self.assertEqual((dest / 'libvitaGL.a').read_bytes(), b'new library')
        self.assertEqual((dest / 'source.tar.gz').read_bytes(), b'archive')
        self.assertEqual(sorted(p.name for p in dest.iterdir()), ['libvitaGL.a', 'source.tar.gz'])

    def assert_rejected_without_touching(self, label):
        dest = self.base / f'consumer-{label}'
        write(dest / 'lib/libavcodec.a', b'current')
        before = snapshot(dest)
        status, _, err = self.restore_cli(dest)
        self.assertEqual(status, dc.EXIT_REJECTED, f'{label}: {err}')
        self.assertIn('rejected', err)
        self.assertEqual(snapshot(dest), before, label)

    def test_corrupted_entries_are_rejected(self):
        payload_lib = self.entry() / 'payload/lib/libavcodec.a'

        def fresh():
            if self.entry().exists():
                shutil.rmtree(self.entry())
            self.store()

        fresh()
        data = bytearray(payload_lib.read_bytes())
        data[0] ^= 0xFF
        payload_lib.write_bytes(bytes(data))
        self.assert_rejected_without_touching('byte-flip')

        fresh()
        payload_lib.write_bytes(payload_lib.read_bytes()[:-3])
        self.assert_rejected_without_touching('truncated-payload')

        fresh()
        manifest = self.entry() / 'manifest.json'
        manifest.write_text(manifest.read_text()[:40])
        self.assert_rejected_without_touching('truncated-manifest')

        fresh()
        payload_lib.unlink()
        self.assert_rejected_without_touching('missing-file')

        fresh()
        write(self.entry() / 'payload/lib/injected.a', b'extra')
        self.assert_rejected_without_touching('extra-file')

        fresh()
        document = json.loads(manifest.read_text())
        document['key_components'] = [['value', 'gcc_version', 'tampered']]
        manifest.write_text(json.dumps(document))
        self.assert_rejected_without_touching('components-do-not-hash-to-key')

        fresh()
        other = self.cache / 'ffmpeg-bink-vita' / ('b' * 64)
        shutil.copytree(self.entry(), other)
        dest = self.base / 'consumer-moved'
        self.assertEqual(self.restore_cli(dest, key='b' * 64)[0], dc.EXIT_REJECTED)

        fresh()
        dest = self.base / 'consumer-outputs'
        self.assertEqual(self.restore_cli(dest, outputs=['include', 'lib'])[0], dc.EXIT_REJECTED)

    def test_store_replaces_a_corrupt_entry_and_skips_a_valid_one(self):
        self.assertEqual(self.store(), 'stored')
        self.assertEqual(self.store(), 'present')
        write(self.entry() / 'payload/include/libavcodec/avcodec.h', '#define AVCODEC 2\n')
        self.assertEqual(self.store(), 'replaced')
        self.assertEqual(self.restore_cli(self.base / 'consumer')[0], dc.EXIT_OK)
        self.assertEqual([p.name for p in self.entry().parent.iterdir()], [self.KEY],
                         'no temporary or rejected directories remain')

    def test_store_requires_consistent_key_document(self):
        components = [['value', 'config_id', 'v3']]
        key = dc.compute_key('ffmpeg-bink-vita', components)[0]
        self.assertEqual(self.store(key=key, key_components=components), 'stored')
        manifest = json.loads((self.entry(key) / 'manifest.json').read_text())
        self.assertEqual(manifest['key_components'], components)
        self.assertEqual(manifest['producer']['root'], str(self.prefix))
        with self.assertRaises(dc.CacheError):
            self.store(key='c' * 64, key_components=components)

    def test_require_complete_refuses_unlisted_top_level_entries(self):
        with self.assertRaises(dc.CacheError):
            self.store(require_complete=True)
        self.assertEqual(self.store(require_complete=True, ignore=['.renegade-bink-build']), 'stored')
        write(self.prefix / 'bin/ffmpeg', b'new top-level output')
        with self.assertRaises(dc.CacheError):
            self.store(key='d' * 64, require_complete=True, ignore=['.renegade-bink-build'])

    def test_paths_and_names_are_validated(self):
        for bad in ('../escape', '/absolute', 'a/../b', './lib', 'lib/', '.depcache-x'):
            with self.assertRaises(dc.CacheError, msg=bad):
                dc.validate_relative(bad)
        with self.assertRaises(dc.CacheError):
            dc.entry_dir(self.cache, 'Bad Name', self.KEY)
        with self.assertRaises(dc.CacheError):
            dc.entry_dir(self.cache, 'ffmpeg-bink-vita', 'not-a-key')
        status, _, _ = run_cli('store', '--cache-dir', str(self.cache), '--name', 'x',
                               '--key', self.KEY, '--src', str(self.prefix), '../lib')
        self.assertEqual(status, dc.EXIT_USAGE)

    def test_verify_reports_every_entry(self):
        self.store()
        dc.store(self.cache, 'ffmpeg-bink-vita', 'e' * 64, self.prefix, self.outputs)
        status, out, _ = run_cli('verify', '--cache-dir', str(self.cache))
        self.assertEqual(status, dc.EXIT_OK)
        self.assertEqual(out.count('\tok'), 2)
        write(self.entry('e' * 64) / 'payload/lib/libavcodec.a', b'tampered')
        status, out, _ = run_cli('verify', '--cache-dir', str(self.cache))
        self.assertEqual(status, dc.EXIT_REJECTED)
        self.assertIn('rejected', out)


class ShellLibraryTests(unittest.TestCase):
    """Exercise tools/dependency_cache.sh with a fake dependency build."""

    FAKE_BUILD = r'''#!/usr/bin/env bash
set -Eeuo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
work="$root/build/deps/fake"
mkdir -p "$work"
source "$root/tools/dependency_cache.sh"
if rv_depcache_enabled && rv_depcache_compute_key fake-dep \
        --script "$root/tools/fake_build.sh" --source "$root/input.txt" &&
    rv_depcache_restore fake-dep "$work" libfake.a; then
    echo "fake restored"
else
    echo built >> "$root/build-count.txt"
    { cat "$root/input.txt"; echo compiled; } > "$work/libfake.a"
    rv_depcache_store fake-dep "$work" libfake.a
fi
'''

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='renegade-depcache-shell-')
        self.base = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def worktree(self, name):
        root = self.base / name
        (root / 'tools').mkdir(parents=True)
        for tool in ('dependency_cache.sh', 'dependency_cache.py'):
            shutil.copy2(ROOT / 'tools' / tool, root / 'tools' / tool)
        write(root / 'tools/fake_build.sh', self.FAKE_BUILD, 0o755)
        write(root / 'input.txt', 'pinned input v1\n')
        return root

    def run_build(self, root, **env_overrides):
        env = {k: v for k, v in os.environ.items() if not k.startswith('RENEGADE_DEPENDENCY_CACHE')}
        env.update(env_overrides)
        result = subprocess.run(['bash', str(root / 'tools/fake_build.sh')], env=env,
                                capture_output=True, text=True, check=True)
        return result.stdout + result.stderr

    @staticmethod
    def builds(root):
        path = root / 'build-count.txt'
        return len(path.read_text().splitlines()) if path.exists() else 0

    def test_disabled_by_default_runs_original_path_without_python(self):
        root = self.worktree('tree')
        output = self.run_build(root)
        self.run_build(root)
        self.assertEqual(self.builds(root), 2)
        self.assertNotIn('Dependency cache', output)
        self.assertFalse((root / 'build/dependency-cache').exists())

    def test_explicit_zero_and_invalid_values_disable(self):
        root = self.worktree('tree')
        shared = self.base / 'shared'
        self.run_build(root, RENEGADE_DEPENDENCY_CACHE='0', RENEGADE_DEPENDENCY_CACHE_DIR=str(shared))
        output = self.run_build(root, RENEGADE_DEPENDENCY_CACHE='yes')
        self.assertIn('invalid RENEGADE_DEPENDENCY_CACHE', output)
        self.assertEqual(self.builds(root), 2)
        self.assertFalse(shared.exists())

    def test_in_tree_default_location(self):
        root = self.worktree('tree')
        self.run_build(root, RENEGADE_DEPENDENCY_CACHE='1')
        (root / 'build/deps/fake/libfake.a').unlink()
        output = self.run_build(root, RENEGADE_DEPENDENCY_CACHE='1')
        self.assertIn('fake restored', output)
        self.assertEqual(self.builds(root), 1)
        self.assertTrue((root / 'build/dependency-cache/fake-dep').is_dir())

    def test_shared_cache_across_worktrees_hit_miss_and_corruption(self):
        shared = self.base / 'shared-cache'
        first, second = self.worktree('worktree-a'), self.worktree('worktree-b')
        output_first = self.run_build(first, RENEGADE_DEPENDENCY_CACHE_DIR=str(shared))
        self.assertIn('stored', output_first)
        output = self.run_build(second, RENEGADE_DEPENDENCY_CACHE_DIR=str(shared))
        self.assertIn('verified hit', output)
        self.assertEqual((self.builds(first), self.builds(second)), (1, 0))
        self.assertEqual((first / 'build/deps/fake/libfake.a').read_bytes(),
                         (second / 'build/deps/fake/libfake.a').read_bytes())

        write(second / 'input.txt', 'pinned input v2\n')
        output = self.run_build(second, RENEGADE_DEPENDENCY_CACHE_DIR=str(shared))
        self.assertIn('miss', output)
        self.assertEqual(self.builds(second), 1)

        third = self.worktree('worktree-c')
        v1_key = re.search(r'fake-dep key ([0-9a-f]{64})', output_first).group(1)
        payload = shared / 'fake-dep' / v1_key / 'payload/libfake.a'
        payload.write_bytes(b'corrupted')
        output = self.run_build(third, RENEGADE_DEPENDENCY_CACHE_DIR=str(shared))
        self.assertIn('rejected', output)
        self.assertIn('replaced', output)
        self.assertEqual(self.builds(third), 1, 'a rejected entry falls back to the real build')
        self.assertEqual((third / 'build/deps/fake/libfake.a').read_text(),
                         'pinned input v1\ncompiled\n')
        status, out, _ = run_cli('verify', '--cache-dir', str(shared))
        self.assertEqual(status, dc.EXIT_OK, out)
        self.assertEqual(out.count('\tok'), 2, 'v1 entry replaced, v2 entry untouched')
        self.assertEqual(list(shared.glob('.pending/*')), [], 'no leftover key documents')


class DependencyScriptContractTests(unittest.TestCase):
    """The real scripts consult the cache only after their in-tree checks."""

    @staticmethod
    def read(name):
        return (ROOT / 'tools' / name).read_text()

    @staticmethod
    def outputs(script, function):
        """Map dependency name -> output list for each call of function."""
        result = []
        for line in script.replace('\\\n', ' ').splitlines():
            index = line.find(function + ' ')
            if index < 0:
                continue
            tokens = shlex.split(line[index:].split(';')[0])
            outputs, skip = [], False
            for token in tokens[3:]:
                if skip:
                    skip = False
                elif token == '--ignore':
                    skip = True
                elif not token.startswith('--'):
                    outputs.append(token)
            result.append((tokens[1], outputs))
        return sorted(result)

    def assert_order(self, script, *needles):
        positions = [script.index(needle) for needle in needles]
        self.assertEqual(positions, sorted(positions), needles)

    def assert_restore_matches_store(self, script):
        restores = self.outputs(script, 'rv_depcache_restore')
        stores = self.outputs(script, 'rv_depcache_store')
        self.assertTrue(restores)
        self.assertEqual(restores, stores)

    def assert_identity_inputs(self, script, script_name):
        self.assertIn(f'tools/{script_name}"', script[script.index('rv_depcache_compute_key'):])
        for token in ('sdk_root=', 'gcc_driver=', 'sdk_version_info='):
            self.assertIn(token, script)

    def test_vitagl_key_covers_every_patch_in_application_order(self):
        script = self.read('build_vitagl_demo.sh')
        applied = re.findall(r'^patch --batch --fuzz=0 --no-backup-if-mismatch '
                             r'-d "\$work/source" -p1 < "\$(\w+_patch)"$', script, re.M)
        keyed = re.findall(r'--patch "\$(\w+_patch)"', script)
        self.assertEqual(keyed, applied)
        self.assertEqual(len(applied), 8)
        self.assert_order(script, 'Pinned demo vitaGL already built',
                          f'< "${applied[-1]}"', 'ffp_cache_digest=$(',
                          'rv_depcache_enabled && rv_depcache_compute_key vitagl-demo',
                          'make -C "$work/source" -B', 'cp "$work/source/libvitaGL.a"',
                          'rv_depcache_store vitagl-demo', '> "$work/provenance.txt"',
                          '> "$work/build.identity"')
        self.assertIn('--tree "compiled_tree=$work/source"', script)
        # --flags=VALUE: the value starts with '-', which argparse would
        # otherwise read as an option.
        self.assertIn('--flags="$flags" --value "ffp_cache_digest=$ffp_cache_digest"', script)
        self.assert_identity_inputs(script, 'build_vitagl_demo.sh')
        self.assert_restore_matches_store(script)

    def test_ffmpeg_cache_follows_stamp_check_and_precedes_configure(self):
        script = self.read('build_ffmpeg_bink_vita.sh')
        self.assert_order(script, 'sha256sum --check', 'already available at',
                          'source "$rv_root/tools/dependency_cache.sh"',
                          'rv_depcache_restore ffmpeg-bink-vita', '"$rv_source/configure"',
                          'make install', '> "$rv_stamp"\nrv_depcache_store ffmpeg-bink-vita')
        self.assertIn('--replace-dest include lib share', script)
        self.assertIn('--require-complete --ignore .renegade-bink-build', script)
        self.assert_identity_inputs(script, 'build_ffmpeg_bink_vita.sh')
        self.assert_restore_matches_store(script)

    def test_https_cache_follows_inputs_check_and_precedes_downloads(self):
        script = self.read('build_ttfs_https_vita.sh')
        self.assert_order(script, 'Verified project-local HTTPS dependencies are unchanged',
                          'rv_depcache_restore ttfs-https-vita', 'fetch mbedtls-3.6.5.tar.bz2',
                          'cmake --build "$rv_work/curl-build"', 'record_stamps\nrv_depcache_store')
        for path in ('renegade_mbedtls_platform.c', 'vita.toolchain.cmake', 'libz.a', 'libpthread.a'):
            self.assertIn(path, script[script.index('rv_depcache_compute_key'):
                                       script.index('rv_depcache_restore')])
        self.assert_identity_inputs(script, 'build_ttfs_https_vita.sh')
        self.assert_restore_matches_store(script)

    def test_every_cache_lookup_is_guarded_by_the_opt_in(self):
        for name in ('build_vitagl_demo.sh', 'build_ffmpeg_bink_vita.sh', 'build_ttfs_https_vita.sh'):
            script = self.read(name)
            self.assertIn('source "$', script)
            for match in re.finditer(r'rv_depcache_compute_key ([\w-]+)', script):
                if match.group(1) == 'vitagl-source-archive':
                    continue  # no command substitutions in its arguments
                prefix = script[max(0, match.start() - 24):match.start()]
                self.assertIn('rv_depcache_enabled && ', prefix, (name, match.group(1)))
        library = self.read('dependency_cache.sh')
        self.assertIn('rv_depcache_enabled || return 1', library)
        self.assertIn('[[ -n "$rv_depcache_key" ]] || return 0', library)


if __name__ == '__main__':
    unittest.main()
