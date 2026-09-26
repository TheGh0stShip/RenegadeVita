#!/usr/bin/env python3
"""Bounded, loopback-only original client/server world integration fixture."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import time


def run(binary, retail, output, map_name="Skirmish00.mix", purchases=False):
    if Path(map_name).name != map_name or not map_name.lower().endswith('.mix'):
        raise ValueError('Expected a retail MIX basename')
    output.mkdir(parents=True, exist_ok=False)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    processes = []
    streams = []
    result = {"transport": "loopback UDP", "port": port, "map": map_name, "purchases": purchases, "passed": False}
    try:
        def start(role):
            roots = []
            for name in ("user", "cache", "mods"):
                root = output / role / name
                root.mkdir(parents=True)
                roots.append(str(root.resolve()))
            log = (output / f"{role}.log").open("w")
            streams.append(log)
            mode = f"REMOTE_{role.upper()}_" + ("PURCHASE_SMOKE" if purchases else "SMOKE")
            command = [str(binary.resolve()), str(retail.resolve()), *roots, map_name, mode, str(port)]
            proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            processes.append(proc)
            return proc

        server = start("server")
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            log = (output / "server.log").read_text(errors="replace")
            if "a31.remote_server_ready=true" in log:
                break
            if server.poll() is not None:
                raise RuntimeError(f"server exited before world readiness: {server.returncode}")
            time.sleep(0.1)
        else:
            raise TimeoutError("server world initialization timed out")
        client = start("client")
        result["client_exit"] = client.wait(timeout=180)
        result["server_exit"] = server.wait(timeout=75)
        client_log = (output / "client.log").read_text(errors="replace")
        server_log = (output / "server.log").read_text(errors="replace")
        result["passed"] = (result["client_exit"] == result["server_exit"] == 0 and
                            "a31.remote_client_replicated_star=true" in client_log and
                            "a31.remote_server_observed_disconnect=true" in server_log and
                            "a31.remote_server_created_player=true" in server_log)
        if purchases:
            result["passed"] = (result["passed"] and
                                "multiplayer.remote_purchase_client=PASS" in client_log and
                                "multiplayer.remote_purchase_server=PASS" in server_log)
    except (RuntimeError, TimeoutError, subprocess.TimeoutExpired) as error:
        result["error"] = str(error)
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
        for stream in streams:
            stream.close()
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--retail", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--map", default="Skirmish00.mix")
    parser.add_argument("--purchases", action="store_true")
    args = parser.parse_args()
    raise SystemExit(run(args.binary, args.retail, args.output, args.map, args.purchases))
