"""Native TTFS contract against asset-free output from official b9000 editor."""
import functools
import http.server
import json
import os
from pathlib import Path
import struct
import ssl
import subprocess
import tempfile
import threading
import unittest
import zlib

from tools.make_ttfs_fixture import FIXTURE_FILES, EDGE_FILES, make_mix

ROOT = Path(__file__).resolve().parents[1]
# Exact official PackageEditor 4.8.4 output for make_ttfs_fixture.py inputs.
ORACLE = bytes.fromhex(
    "4441454808000000bdb71c2b0200000041544144240000000c00766974615f66"
    "6978747572650300312e300b00566974614669787475726502000000454c4946"
    "18000000ff7258fc290000000e00766974615f70726f62652e747874454c4946"
    "180000002adfc0b0000300000e00766974615f62797465732e62696e")
EDGE_ORACLE = bytes.fromhex(
    "4441454808000000d5ca41fb0300000041544144220000000a00766974615f65"
    "646765730300322e300b00566974614669787475726502000000454c49461300"
    "000000000000000000000900656d7074792e646174454c4946150000005ef326"
    "cd0f0000000b00612073706163652e747874454c49461400000038eb1c090852"
    "00000a007265706561742e62696e")


class QuietServer(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class RedirectServer(QuietServer):
    def do_GET(self):
        self.send_response(302)
        self.send_header("Location", "file:///etc/passwd")
        self.end_headers()


class TTFSNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix="ttfs-native-")
        cls.probe = Path(cls.build.name) / "ttfs_probe"
        sdk = Path(os.environ.get("VITASDK", "/usr/local/vitasdk"))
        command = ["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-g",
                   "-I" + str(ROOT / "port/filesystem"),
                   "-idirafter", str(sdk / "arm-vita-eabi/include"),
                   str(ROOT / "tools/ttfs_probe.cpp"),
                   str(ROOT / "port/filesystem/renegade_ttfs.cpp"),
                   str(ROOT / "port/filesystem/renegade_ttfs_cache.cpp"),
                   str(ROOT / "port/filesystem/renegade_ttfs_download.cpp"),
                   str(ROOT / "port/filesystem/renegade_ttfs_prepare.cpp"),
                   "-l:libcurl.so.4", "-lz", "-o", str(cls.probe)]
        if os.environ.get("TTFS_SANITIZE") == "1":
            command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-no-pie"]
        subprocess.run(command, check=True, timeout=90)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ttfs-case-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def invoke(self, *args):
        return subprocess.run([str(self.probe), *map(str, args)], capture_output=True,
                              text=True, timeout=25)

    def inspect(self, data, package="2b1cb7bd"):
        path = self.root / "input.tpi"
        path.write_bytes(data)
        return self.invoke("inspect", path, package)

    def repository(self, data=ORACLE, package="2b1cb7bd", files=FIXTURE_FILES, handler=QuietServer, tls=False):
        repo = self.root / "repository"
        (repo / "packages").mkdir(parents=True)
        (repo / "files").mkdir()
        (repo / "packages" / (package + ".tpi")).write_bytes(data)
        for name, content in files.items():
            (repo / "files" / f"{zlib.crc32(content):08X}.{name.lower()}").write_bytes(content)
        server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(handler, directory=str(repo)))
        if tls:
            cert, key = self.root / "fixture.pem", self.root / "fixture.key"
            subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                            "-days", "1", "-subj", "/CN=localhost",
                            "-addext", "subjectAltName=DNS:localhost,IP:127.0.0.1",
                            "-keyout", str(key), "-out", str(cert)],
                           check=True, capture_output=True, timeout=30)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def stop():
            server.shutdown()
            server.server_close()
            thread.join()
        self.addCleanup(stop)
        scheme = "https" if tls else "http"
        return repo, f"{scheme}://127.0.0.1:{server.server_port}"

    def test_official_editor_oracles(self):
        result = self.inspect(ORACLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("vita_fixture 1.0 VitaFixture files=2", result.stdout)
        result = self.inspect(EDGE_ORACLE, "fb41cad5")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("00000000.empty.dat 0", result.stdout)
        self.assertIn("CD26F35E.a space.txt 15", result.stdout)

    def test_every_truncation_rejected(self):
        for data, package in [(ORACLE, "2b1cb7bd"), (EDGE_ORACLE, "fb41cad5")]:
            for length in range(len(data)):
                result = self.inspect(data[:length], package)
                self.assertEqual(result.returncode, 1, (length, result.stderr))

    def test_wrong_id_lengths_unknown_metadata_and_trailing_data(self):
        bad_count = bytearray(ORACLE)
        struct.pack_into("<I", bad_count, 12, 0xffffffff)
        bad_length = bytearray(ORACLE)
        struct.pack_into("<I", bad_length, 20, 0xffffffff)
        bad_metadata = bytearray(ORACLE)
        struct.pack_into("<I", bad_metadata, 56, 99)
        for data in [bad_count, bad_length, bad_metadata, ORACLE + b"junk"]:
            self.assertEqual(self.inspect(data).returncode, 1)
        self.assertEqual(self.inspect(ORACLE, "00000000").returncode, 1)

    def test_unsafe_duplicate_and_executable_names(self):
        for name in [b"../a_probe.txt", b"vita_probe.exe", b"vita:probe.txt",
                     b"vita\\robe.txt ", b"VITA_BYTES.BIN"]:
            self.assertEqual(len(name), len(b"vita_probe.txt"))
            result = self.inspect(ORACLE.replace(b"vita_probe.txt", name))
            self.assertEqual(result.returncode, 1, (name, result.stderr))

    def test_download_commit_and_existing_cache_preserved(self):
        _, url = self.repository()
        target = self.root / "cache"
        result = self.invoke("download", url, "2b1cb7bd", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((target / "manifest.tpi").read_bytes(), ORACLE)
        self.assertEqual(self.invoke("cache", target, "2b1cb7bd").returncode, 0)
        if os.environ.get("TTFS_ENGINE_PROBE"):
            result = subprocess.run([os.environ["TTFS_ENGINE_PROBE"], "--ttfs-cache-selftest", str(target)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name, content in FIXTURE_FILES.items():
            self.assertEqual((target / f"{zlib.crc32(content):08X}.{name}").read_bytes(), content)
        before = {p.name: p.read_bytes() for p in target.iterdir()}
        self.assertEqual(self.invoke("download", url, "2b1cb7bd", target).returncode, 1)
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
        (target / "B0C0DF2A.vita_bytes.bin").write_bytes(b"x" * 768)
        self.assertEqual(self.invoke("cache", target, "2b1cb7bd").returncode, 1)

    def test_reference_user_agent_for_manifest_and_payloads(self):
        reference = json.loads((ROOT / 'tools/fixtures/tt_http_b9000.json').read_text())
        self.assertEqual(reference['reference_sha256'],
                         'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db')
        requests = []
        class AgentRestrictedServer(QuietServer):
            def do_GET(handler):
                requests.append((handler.path, handler.headers.get('User-Agent')))
                if handler.headers.get('User-Agent') != reference['user_agent']:
                    handler.send_error(403)
                    return
                super().do_GET()
        _, url = self.repository(handler=AgentRestrictedServer)
        target = self.root / 'cache'
        result = self.invoke('download', url, '2b1cb7bd', target)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(requests), 3)
        self.assertTrue(requests[0][0].startswith('/packages/'))
        self.assertTrue(all(path.startswith('/files/') for path, _ in requests[1:]))
        self.assertTrue(all(agent == reference['user_agent'] for _, agent in requests))
        self.assertEqual(self.invoke('cache', target, '2b1cb7bd').returncode, 0)

    def test_edge_download_empty_spaces_and_no_compression(self):
        _, url = self.repository(EDGE_ORACLE, "fb41cad5", EDGE_FILES)
        target = self.root / "cache"
        result = self.invoke("download", url, "fb41cad5", target)
        self.assertEqual(result.returncode, 0, result.stderr)
        for name, content in EDGE_FILES.items():
            self.assertEqual((target / f"{zlib.crc32(content):08X}.{name.lower()}").read_bytes(), content)

    def test_corrupt_short_oversized_and_missing_payload_rollback(self):
        repo, url = self.repository()
        original = FIXTURE_FILES["vita_bytes.bin"]
        payload = repo / "files" / f"{zlib.crc32(original):08X}.vita_bytes.bin"
        for content in [b"x" * len(original), original[:-1], original + b"x", None]:
            if content is None:
                payload.unlink()
            else:
                payload.write_bytes(content)
            target = self.root / "cache"
            result = self.invoke("download", url, "2b1cb7bd", target)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse(target.exists())

    def test_wrong_manifest_does_not_install(self):
        _, url = self.repository(ORACLE.replace(b"vita_probe.txt", b"../a_probe.txt"))
        target = self.root / "cache"
        self.assertEqual(self.invoke("download", url, "2b1cb7bd", target).returncode, 1)
        self.assertFalse(target.exists())

    def test_non_http_and_credential_urls_rejected(self):
        target = self.root / "cache"
        for url in ["file:///etc", "ftp://host", "http://user:pass@host", "https://host/?q=1"]:
            self.assertEqual(self.invoke("download", url, "2b1cb7bd", target).returncode, 1)
            self.assertFalse(target.exists())

    def test_redirect_rejected_without_cache_commit(self):
        _, url = self.repository(handler=RedirectServer)
        target = self.root / "cache"
        result = self.invoke("download", url, "2b1cb7bd", target)
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTTP 302", result.stderr)
        self.assertFalse(target.exists())

    def test_https_requires_trusted_certificate(self):
        _, url = self.repository(tls=True)
        target = self.root / "cache"
        result = self.invoke("download", url, "2b1cb7bd", target)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(target.exists())
        result = self.invoke("download", url, "2b1cb7bd", target, self.root / "fixture.pem")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.invoke("cache", target, "2b1cb7bd").returncode, 0)

    def test_prepare_set_cache_reuse_deduplicate_and_failure(self):
        repo, url = self.repository()
        (repo / 'packages/fb41cad5.tpi').write_bytes(EDGE_ORACLE)
        for name, content in EDGE_FILES.items():
            (repo / 'files' / f'{zlib.crc32(content):08X}.{name.lower()}').write_bytes(content)
        target = self.root / 'prepared'
        result = self.invoke('prepare', url, '2b1cb7bd', target, 'fb41cad5', '2b1cb7bd')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('prepared=2', result.stdout)
        before = {str(p.relative_to(target)): (p.stat().st_mtime_ns, p.read_bytes())
                  for p in target.rglob('*') if p.is_file()}
        # Validated cache hits must not need the repository or rewrite files.
        result = self.invoke('prepare', 'http://127.0.0.1:1', '2b1cb7bd', target, 'fb41cad5')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {str(p.relative_to(target)): (p.stat().st_mtime_ns, p.read_bytes())
                                 for p in target.rglob('*') if p.is_file()})
        damaged = target / 'fb41cad5/00000000.empty.dat'
        damaged.write_bytes(b'corrupt')
        result = self.invoke('prepare', url, '2b1cb7bd', target, 'fb41cad5')
        self.assertEqual(result.returncode, 1)
        self.assertIn('prepared=0', result.stdout)
        self.assertEqual(damaged.read_bytes(), b'corrupt')

    def test_prepare_cancellation_never_publishes_partial_set(self):
        _, url = self.repository()
        for cancel_at in (1, 4, 10):
            target = self.root / ('cancel-' + str(cancel_at))
            result = subprocess.run([str(self.probe), 'prepare', url, '2b1cb7bd', str(target)],
                capture_output=True, text=True, timeout=25,
                env={**os.environ, 'TTFS_PROBE_CANCEL_AT': str(cancel_at)})
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn('prepared=0', result.stdout)
            self.assertFalse((target / '2b1cb7bd').exists())

    def test_prepare_preserves_existing_nondirectory(self):
        _, url = self.repository()
        root = self.root / 'cache'
        root.mkdir()
        outside = self.root / 'unrelated'
        outside.mkdir()
        (root / '2b1cb7bd').symlink_to(outside, target_is_directory=True)
        result = self.invoke('prepare', url, '2b1cb7bd', root)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(list(outside.iterdir()), [])

    @unittest.skipUnless(os.environ.get('TTFS_ENGINE_PROBE'), 'requires original engine factory')
    def test_original_mix_members_and_untrusted_index(self):
        def package(files):
            def text(value):
                data = value.encode('ascii')
                return struct.pack('<H', len(data)) + data
            def chunk(tag, data):
                return tag + struct.pack('<I', len(data)) + data
            data = chunk(b'DAEH', struct.pack('<II', 0x2b1cb7bd, len(files)))
            data += chunk(b'ATAD', text('archive-fixture') + text('1') + text('test') + struct.pack('<I', 2))
            for name, content in files.items():
                data += chunk(b'ELIF', struct.pack('<II', zlib.crc32(content), len(content)) + text(name))
            return data

        good = make_mix(FIXTURE_FILES)
        index, = struct.unpack_from('<I', good, 4)
        mutations = {'bad-signature': (0, 0), 'negative-index': (4, 0xffffffff),
                     'negative-names': (8, 0xffffffff), 'excess-count': (index, 65537),
                     'outside-offset': (index + 8, len(good) + 1),
                     'outside-size': (index + 12, 0xffffffff)}
        variants = [(suffix, good, True) for suffix in ('mix', 'dat', 'pkg')]
        shuffled = bytearray(good)
        first = index + 4
        shuffled[first:first + 24] = good[first + 12:first + 24] + good[first:first + 12]
        variants.append(('unsorted-index', bytes(shuffled), True))
        for label, (offset, value) in mutations.items():
            bad = bytearray(good)
            struct.pack_into('<I', bad, offset, value)
            variants.append((label, bytes(bad), False))
        # The normal engine probe checks read/seek/bias/read-only/remount.
        # TT prepends nested archives before its loose resource factory.
        stale = make_mix({**FIXTURE_FILES, 'vita_bytes.bin': b'x' * 768})
        for label, archive, passed in variants + [('archive-priority', good, True),
                                                 ('last-archive-priority', stale, True)]:
            files = {'fixture.' + (label if label in ('dat', 'pkg') else 'mix'): archive}
            if label == 'archive-priority':
                files['vita_bytes.bin'] = b'x' * 768
            if label == 'last-archive-priority':
                files['last.mix'] = good
            cache = self.root / label
            cache.mkdir()
            (cache / 'manifest.tpi').write_bytes(package(files))
            for name, content in files.items():
                (cache / f'{zlib.crc32(content):08X}.{name}').write_bytes(content)
            result = subprocess.run([os.environ['TTFS_ENGINE_PROBE'], '--ttfs-cache-selftest', str(cache)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0 if passed else 1, (label, result.stdout, result.stderr))
            self.assertNotIn('AddressSanitizer', result.stderr)
            for name, content in files.items():
                self.assertEqual((cache / f'{zlib.crc32(content):08X}.{name}').read_bytes(), content)
            if not passed:
                self.assertIn('invalid or oversized MIX index', result.stderr)


if __name__ == "__main__":
    unittest.main()
