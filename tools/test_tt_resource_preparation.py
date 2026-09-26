#!/usr/bin/env python3
"""Original UDP options/resource receipt -> HTTP cache -> original start latch.

Loopback-only, synthetic files, no world/player or public-server success claim.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import socket
import struct
import subprocess
import threading
import time
import zlib

from tools.replay_tt_admission import transport_packet
from tools.make_ttfs_fixture import make_mix


def text(value):
    data = value.encode('ascii')
    return struct.pack('<H', len(data)) + data


def chunk(name, data):
    return name + struct.pack('<I', len(data)) + data


def run(binary, retail, output, mode):
    output.mkdir(parents=True, exist_ok=False)
    for name in ('user', 'cache', 'mods', 'repository/packages', 'repository/files'):
        (output / name).mkdir(parents=True)
    map_name = 'C&C_ResourceFixture.mix'
    if mode == 'wrong-map':
        map_name = 'C&C_WrongFixture.mix'
    if mode == 'retail-overlay':
        map_name = 'Skirmish00.mix'
    modern = mode in ('modern-stem', 'modern-truncated')
    group_name = map_name[:-4] if modern or mode in ('stem', 'stem-archive', 'prefetch-first') else map_name
    if modern:
        (output / 'user/config').mkdir()
        (output / 'user/config/tt-identity-v1.txt').write_text('a' * 32 + '\n')
    package_id = 0xABCDEF01
    files = {'c&c_resourcefixture.ldd': b'synthetic-level-not-a-world' * 8192,
             'c&c_resourcefixture.lsd': b'synthetic-save-not-a-world',
             'stylemgr.ini': b'lower-priority-package'}
    if mode == 'missing-level':
        del files['c&c_resourcefixture.ldd']
    if mode == 'retail-overlay':
        files = {'stylemgr.ini': b'lower-priority-package'}
    if mode.startswith('archive-') or mode == 'stem-archive':
        del files['stylemgr.ini']
        extension = mode.removeprefix('archive-')
        if extension not in ('mix', 'dat', 'pkg'):
            extension = 'mix'
        archive = bytearray(make_mix(files))
        if mode == 'archive-bad-index':
            index, = struct.unpack_from('<I', archive, 4)
            struct.pack_into('<I', archive, index + 8, 0xfffffff0)
        files = {'nested.' + extension: bytes(archive)}
    for id_value, entries in ((package_id, files), (package_id + 1, {'stylemgr.ini': b'synthetic-sentinel'})):
        manifest = chunk(b'DAEH', struct.pack('<II', id_value, len(entries)))
        manifest += chunk(b'ATAD', text('resource-fixture') + text('1') + text('test') + struct.pack('<I', 2))
        for name, data in entries.items():
            crc = zlib.crc32(data)
            manifest += chunk(b'ELIF', struct.pack('<II', crc, len(data)) + text(name))
            (output / 'repository/files' / f'{crc:08X}.{name}').write_bytes(data)
        (output / 'repository/packages' / f'{id_value:08x}.tpi').write_bytes(manifest)
    if mode == 'corrupt':
        payload = next((output / 'repository/files').glob('*.ldd'))
        payload.write_bytes(b'corrupt payload')
    fixture = output / 'options.bin'
    export = [str(binary), '--export-resource-options', str(fixture)]
    if mode == 'retail-overlay':
        export.append(map_name)
    subprocess.run(export, check=True, timeout=30)
    options = fixture.read_bytes()
    option_bits, = struct.unpack('<I', options[:4])
    option_payload = options[4:]
    if modern:
        bits = ''.join(f'{byte:08b}' for byte in option_payload)[:option_bits - 64] + '1'
        option_bits = len(bits) - (1 if mode == 'modern-truncated' else 0)
        option_payload = bytes(int(bits[i:i + 8].ljust(8, '0'), 2) for i in range(0, len(bits), 8))
    started = threading.Event()
    stop = threading.Event()
    result = {'evidence_class': 'host_original_udp_resource_preparation', 'mode': mode,
              'public_server_contacted': False, 'world_loaded': False, 'passed': False}

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def copyfile(self, source, target):
            if '/files/' in self.path:
                started.set()
            try:
                while data := source.read(8192):
                    target.write(data)
                    target.flush()
                    time.sleep(0.02)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Expected when the original client cancels a stale group.

    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
        functools.partial(Handler, directory=str(output / 'repository')))
    http_thread = threading.Thread(target=httpd.serve_forever)
    http_thread.start()
    repository = f'http://127.0.0.1:{httpd.server_port}'.encode()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(('127.0.0.1', 0))
            sock.settimeout(0.1)
            endpoint = f'127.0.0.1:{sock.getsockname()[1]}'

            def server():
                peer = None
                removed = False
                while not stop.is_set():
                    if peer and mode in ('removed', 'prefetch') and started.is_set() and not removed:
                        if mode == 'removed':
                            payload = struct.pack('>II', 1, 73)
                        else:
                            next_name = b'C&C_NextFixture.mix'
                            payload = struct.pack('>IIH', 0, 74, len(next_name)) + next_name + struct.pack('>I', 0)
                        sock.sendto(transport_packet(8, 5, payload), peer)
                        removed = True
                        result['update_sent_during_transfer'] = True
                    try:
                        _, sender = sock.recvfrom(2048)
                    except socket.timeout:
                        continue
                    if peer is None:
                        peer = sender
                        accept = struct.pack('>IIIH', 1, 0x21545421, 0x4099999a, len(repository))
                        accept += repository + struct.pack('>I', 9000)
                        group = struct.pack('>IIH', 0, 73, len(group_name)) + group_name.encode() + struct.pack('>I', 2)
                        packets = [transport_packet(5, 0, accept), transport_packet(8, 1, group),
                            transport_packet(8, 2, struct.pack('>II', 0, package_id)),
                            transport_packet(8, 3, struct.pack('>II', 0, package_id + 1)),
                            transport_packet(1, 4, option_payload, option_bits)]
                        if mode == 'options-first':
                            packets = [transport_packet(5, 0, accept),
                                transport_packet(1, 1, option_payload, option_bits),
                                transport_packet(8, 2, group),
                                transport_packet(8, 3, struct.pack('>II', 0, package_id)),
                                transport_packet(8, 4, struct.pack('>II', 0, package_id + 1))]
                        if mode == 'prefetch-first':
                            future = b'C&C_Future'
                            future_group = struct.pack('>IIH', 0, 74, len(future)) + future + struct.pack('>I', 0)
                            packets = [transport_packet(5, 0, accept),
                                transport_packet(8, 1, future_group), transport_packet(8, 2, group),
                                transport_packet(8, 3, struct.pack('>II', 0, package_id)),
                                transport_packet(8, 4, struct.pack('>II', 0, package_id + 1)),
                                transport_packet(1, 5, option_payload, option_bits)]
                        for packet in packets:
                            sock.sendto(packet, peer)

            thread = threading.Thread(target=server)
            thread.start()
            command = [str(binary), str(retail), *[str(output / p) for p in ('user', 'cache', 'mods')],
                       'Skirmish00.mix', 'TT_ADMISSION_PROBE' if modern else 'RESOURCE_ADMISSION_FIXTURE', endpoint]
            try:
                with (output / 'runtime.log').open('w') as log:
                    proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=90)
                result['exit'] = proc.returncode
            finally:
                stop.set()
                thread.join(timeout=3)
    finally:
        httpd.shutdown()
        httpd.server_close()
        http_thread.join()
    log = (output / 'runtime.log').read_text(errors='replace')
    clean = ('a31.campaign_catalog_shutdown=true' in log and
             'AddressSanitizer' not in log and 'LeakSanitizer' not in log)
    if mode == 'modern-stem':
        result['passed'] = clean and result.get('exit') == 0 and all(marker in log for marker in (
            'experimental TT greeting prepared',
            f'resource set mounted map={map_name} packages=2; world not loaded',
            'direct_admission.accepted=1 refusal=0 options=1 state=2 joined=0'))
    elif mode == 'modern-truncated':
        result['passed'] = clean and result.get('exit') == 1 and (
            'invalid game options layout; session stopped' in log and 'resource set mounted' not in log)
    elif mode in ('good', 'prefetch', 'options-first', 'retail-overlay', 'stem', 'stem-archive', 'prefetch-first',
                'archive-mix', 'archive-dat', 'archive-pkg'):
        result['passed'] = clean and result.get('exit') == 0 and all(marker in log for marker in (
            f'resource set mounted map={map_name} packages=2; world not loaded',
            'direct_admission.prepared_overrides_retail_after_search_reset=1',
            'direct_admission.prepared_original_start=1', 'direct_admission.prepared_cleanup=1'))
        if mode == 'prefetch':
            result['passed'] &= bool(result.get('update_sent_during_transfer'))
    else:
        reason = ('client-connect: resource group does not match map options' if mode == 'wrong-map'
                  else 'client-connect: resource preparation failed:')
        result['passed'] = clean and result.get('exit') == 1 and (
            reason in log and
            'resource set mounted' not in log)
        if mode == 'removed':
            result['passed'] &= bool(result.get('update_sent_during_transfer'))
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--retail', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--mode', choices=['good', 'removed', 'missing-level', 'prefetch',
                                         'options-first', 'wrong-map', 'corrupt', 'retail-overlay',
                                         'archive-mix', 'archive-dat', 'archive-pkg',
                                         'archive-bad-index', 'stem', 'stem-archive', 'prefetch-first',
                                         'modern-stem', 'modern-truncated'], default='good')
    args = parser.parse_args()
    raise SystemExit(run(args.binary.resolve(), args.retail.resolve(), args.output.resolve(), args.mode))
