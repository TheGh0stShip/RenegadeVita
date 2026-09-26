#!/usr/bin/env python3
"""One bounded GameSpy info query; does not join or request player records."""

import argparse
import ipaddress
import json
import socket
import time


FIELDS = {"hostname", "hostport", "gamename", "gamever", "mapname",
          "gametype", "numplayers", "maxplayers", "gamemode", "password"}


def parse_info(data):
    if not data or len(data) > 8192 or not data.startswith(b"\\"):
        raise ValueError("invalid info packet size or prefix")
    tokens = data.rstrip(b"\0").decode("ascii", errors="strict").split("\\")[1:]
    if len(tokens) % 2:
        raise ValueError("incomplete key/value pair")
    result = {}
    for key, value in zip(tokens[::2], tokens[1::2]):
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in key + value):
            raise ValueError("control character in info packet")
        if key in FIELDS:
            if key in result and result[key] != value:
                raise ValueError("conflicting info field")
            result[key] = value
    if "hostport" in result:
        port = int(result["hostport"])
        if not 1 <= port <= 65535:
            raise ValueError("invalid advertised game port")
    return result


def query(address, port, timeout):
    endpoint = (str(ipaddress.IPv4Address(address)), port)
    result = {"query_endpoint": "%s:%d" % endpoint, "joined": False,
              "evidence_class": "public_info_query", "info": {}}
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        # Connected UDP filters datagrams from other addresses and ports.
        sock.connect(endpoint)
        sock.send(b"\\info\\")
        for _ in range(8):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                packet = sock.recv(8193)
            except socket.timeout:
                break
            fields = parse_info(packet)
            for key, value in fields.items():
                if key in result["info"] and result["info"][key] != value:
                    raise ValueError("inconsistent split response")
                result["info"][key] = value
            if b"\\final\\" in packet:
                break
    result["responded"] = bool(result["info"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", type=ipaddress.IPv4Address)
    parser.add_argument("query_port", type=int)
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()
    if not 1 <= args.query_port <= 65535 or not 0 < args.timeout <= 10:
        parser.error("port must be 1..65535; timeout must be >0 and <=10 seconds")
    try:
        result = query(args.address, args.query_port, args.timeout)
    except (OSError, ValueError) as error:
        print(json.dumps({"joined": False, "error": str(error)}, indent=2))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["responded"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
