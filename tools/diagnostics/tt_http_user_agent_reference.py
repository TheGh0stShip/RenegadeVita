#!/usr/bin/env python3
"""Extract pinned TT HTTP identity constants, not DLL startup or credentials.

WinINet initialization at 0x121c6d40 formats these constants and passes the
result to InternetOpenA at 0x121c6dd2. The build stamp is not the git commit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import pefile
from tt_identity_oracle import PIN


def inspect(image):
    if hashlib.sha256(image).hexdigest() != PIN:
        raise ValueError('Reference differs from pinned b9000')
    pe = pefile.PE(data=image)
    mapped = pe.get_memory_mapped_image()
    base = pe.OPTIONAL_HEADER.ImageBase
    def string(address):
        offset = address - base
        return mapped[offset:mapped.index(b'\0', offset)].decode('ascii')
    version, = struct.unpack_from('<d', mapped, 0x122f4eb0 - base)
    assert mapped[0x121c6d5f - base] == 0x68  # push imm32 revision argument
    revision, = struct.unpack_from('<I', mapped, 0x121c6d60 - base)
    assert string(0x122e744c) == '%s/%s' and string(0x122da718) == '%.2f.%u-%s'
    assert mapped[0x121c6dd2 - base:0x121c6dd8 - base] == bytes.fromhex('ff159c952c12')
    agent = string(0x122e744c) % (string(0x122da714),
            string(0x122da718) % (version, revision, string(0x122ccf94)))
    return {'schema': 1, 'reference_sha256': PIN, 'user_agent': agent,
            'evidence': 'pinned WinINet initializer constants and call site',
            'function': '0x121c6d40', 'credentials_read': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.dll.read_bytes()), indent=2))
