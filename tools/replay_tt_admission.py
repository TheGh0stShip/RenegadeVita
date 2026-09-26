#!/usr/bin/env python3
"""Replay one public TT greeting on loopback, without contacting RenCorner."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import threading
import os
import struct
import time
import zlib

# First reply from the user-authorized 2026-09-24 original-client attempt.
# Contains transport acceptance and TT greeting/repository, no player records,
# credentials or game assets. Keep immutable so fixes see the same input.
GREETING = bytes.fromhex(
    "554f0d67e18020000000000000e187500000000001c000000033215454214099999a"
    "002668747470733a2f2f747466732e72656e636f726e65722e6e65742e636f2f6d"
    "61726174686f6e00002328610210000001000059596c11200f800001fc800000")


def transport_packet(kind, sequence, payload, bits=None):
    app = struct.pack('>IBH', (kind << 28) | sequence, 0,
                      len(payload) * 8 if bits is None else bits) + payload
    body = struct.pack('<H', (len(app) << 5) | 1) + app
    return struct.pack('>I', zlib.crc32(body)) + body


def run(binary, retail, output, debugger, synthetic_identity=False, resources=False, malformed=False):
    output.mkdir(parents=True, exist_ok=False)
    roots = []
    for name in ("user", "cache", "mods"):
        root = output / name
        root.mkdir()
        roots.append(str(root.resolve()))
    if synthetic_identity:
        config = output / "user/config"
        config.mkdir(mode=0o700)
        path = config / "tt-identity-v1.txt"
        with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as identity:
            identity.write(hashlib.md5(b"synthetic-protocol-fixture-not-a-key").hexdigest() + "\n")
    stop = threading.Event()
    result = {"evidence_class": "host_loopback_tt_greeting_replay",
              "fixture_sha256": hashlib.sha256(GREETING).hexdigest(),
              "public_server_contacted": False, "reply_sent": False,
              "synthetic_identity": synthetic_identity,
              "resource_fixture": resources,
              "malformed_resource": malformed,
              "synthetic_response_observed_on_udp": False}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.settimeout(0.25)

        def reply():
            while not stop.is_set():
                try:
                    packet, peer = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                if packet and not result["reply_sent"]:
                    sock.sendto(GREETING, peer)
                    result["reply_sent"] = True
                    if resources:
                        time.sleep(0.1)
                        # A different source port must not inject into the accepted peer.
                        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as foreign:
                            foreign.sendto(transport_packet(8, 2, struct.pack('>II', 2, 0)), peer)
                        # Both malformed headers must be dropped before type-stat indexing/copy.
                        sock.sendto(transport_packet(15, 2, b''), peer)
                        sock.sendto(transport_packet(8, 2, b'', bits=4096), peer)
                        if malformed:
                            sock.sendto(transport_packet(8, 2, struct.pack('>II', 2, 0)), peer)
                        else:
                            fixture = json.loads((Path(__file__).parent /
                                'fixtures/tt_resource_b9000.json').read_text())
                            bodies = [bytes.fromhex(p['hex']) for case in fixture['cases'][:3]
                                      for p in case['packets']]
                            bodies += [bytes.fromhex(case['remove'][0]['hex'])
                                       for case in fixture['cases'][:2]]
                            # Duplicate headers/packages must not confuse the stateful group parser.
                            for index in (5, 3, 3, 1, 0, 7, 4, 2, 6, 8, 1):
                                sock.sendto(transport_packet(8, 2 + index, bodies[index]), peer)
                elif packet and synthetic_identity:
                    # Original bitstream fields are not byte-aligned. Find the
                    # known synthetic response prefix, then independently check
                    # the complete nonce/digest. Never retain UDP payloads.
                    seed = hashlib.md5(b"synthetic-protocol-fixture-not-a-key").hexdigest()
                    prefix = hashlib.md5(seed.encode()).hexdigest()
                    bits = "".join(format(byte, "08b") for byte in packet)
                    marker = "".join(format(byte, "08b") for byte in prefix.encode())
                    offset = bits.find(marker)
                    if offset >= 0 and len(bits) >= offset + 72 * 8:
                        response = bytes(int(bits[index:index + 8], 2)
                                         for index in range(offset, offset + 72 * 8, 8))
                        try:
                            nonce = int(response[32:40], 16)
                            expected = (prefix + "%08x" % nonce +
                                hashlib.md5((seed + str(nonce % 65535)).encode()).hexdigest())
                            result["synthetic_response_observed_on_udp"] = response == expected.encode()
                        except ValueError:
                            pass

        thread = threading.Thread(target=reply)
        thread.start()
        command = [str(binary.resolve()), str(retail.resolve()), *roots,
                   "Skirmish00.mix", "REMOTE_ADMISSION_PROBE",
                   "127.0.0.1:%d" % sock.getsockname()[1]]
        if debugger:
            command = ["gdb", "-q", "-batch", "-ex", "run", "-ex", "bt full",
                       "--args", *command]
        try:
            with (output / "runtime.log").open("w") as log:
                completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                                           timeout=120)
            result["exit"] = completed.returncode
        except subprocess.TimeoutExpired:
            result["error"] = "bounded replay timed out"
        finally:
            stop.set()
            thread.join(timeout=2)
    log = (output / "runtime.log").read_text(errors="replace")
    result["controlled_protocol_failure"] = (
        result.get("exit") == 1 and result["reply_sent"] and
        "client-connect: identity unavailable or invalid; join stopped" in log and
        "joined=0" in log and "a31.campaign_catalog_shutdown=true" in log)
    result["synthetic_response_prepared"] = (
        synthetic_identity and result.get("exit") == 1 and
        result["synthetic_response_observed_on_udp"] and
        "client-connect: serial challenge response prepared (redacted)" in log and
        "unsupported network class=1017" not in log and
        "a31.campaign_catalog_shutdown=true" in log)
    result["debugger_crash"] = "Program received signal" in log
    if resources:
        result["resource_transport_passed"] = (
            "a31.campaign_catalog_shutdown=true" in log and
            "ERROR: AddressSanitizer" not in log and "LeakSanitizer:" not in log and
            ("connection: invalid TT resource subtype; session stopped" in log if malformed else
             all(text in log for text in (
                 "direct_admission.resources groups=1 generation=5 pending=0 error=none",
                 "direct_admission.resource_group id=ffffffff packages=3 name=synthetic-group",
                 "direct_admission.resource_package index=0 id=89abcdef",
                 "direct_admission.resource_package index=1 id=ffffffff",
                 "direct_admission.resource_package index=2 id=00000000"))))
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    if resources:
        return 0 if result["resource_transport_passed"] and result.get("exit") == 1 else 1
    return 0 if (result["synthetic_response_prepared"] if synthetic_identity else
                 result["controlled_protocol_failure"]) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path)
    parser.add_argument("--retail", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gdb", action="store_true")
    parser.add_argument("--synthetic-identity", action="store_true")
    parser.add_argument("--resources", action="store_true")
    parser.add_argument("--malformed-resource", action="store_true")
    args = parser.parse_args()
    if args.malformed_resource and not args.resources:
        parser.error('--malformed-resource requires --resources')
    raise SystemExit(run(args.binary, args.retail, args.output, args.gdb,
                         args.synthetic_identity or args.resources, args.resources, args.malformed_resource))
