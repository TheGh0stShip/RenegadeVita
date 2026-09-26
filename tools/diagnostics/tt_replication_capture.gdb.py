"""Capture at most 16 incoming physical rare-state packets, never identity traffic.

RENEGADE_REPLICATION_CAPTURE must name a NEW file under a private 0700 directory.
Only bounded packet bytes and read offsets are retained. No object/process dump.
Use the matching-symbol host TT_WORLD_PROBE; keep results outside the repository.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import gdb

output = Path(os.environ['RENEGADE_REPLICATION_CAPTURE'])
if output.exists() or output.parent.is_symlink() or stat.S_IMODE(output.parent.stat().st_mode) != 0o700:
    raise RuntimeError('Capture requires a new file in a private 0700 directory')
binary_hash = hashlib.sha256(Path(gdb.current_progspace().filename).read_bytes()).hexdigest()
stream = os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w')


class RareBreakpoint(gdb.Breakpoint):
    count = 0

    def stop(self):
        packet = gdb.parse_and_eval('packet').cast(gdb.lookup_type('cBitPacker').reference())
        start, end = int(packet['BitReadPosition']), int(packet['BitWritePosition'])
        buffer = packet['Buffer']
        if not 0 <= start <= end <= buffer.type.sizeof * 8:
            raise RuntimeError('Invalid packet range')
        raw = bytes(gdb.selected_inferior().read_memory(int(buffer.address), (end + 7) // 8))
        json.dump({'schema': 1, 'event': 'PhysicalGameObj::Import_Rare',
                   'evidence_class': 'host_incoming_replication_only',
                   'binary_sha256': binary_hash, 'entry_read_bits': start,
                   'packet_bits': end, 'packet_hex': raw.hex()}, stream)
        stream.write('\n')
        stream.flush()
        self.count += 1
        if self.count >= 16:
            self.enabled = False
            stream.close()
        return False


RareBreakpoint('PhysicalGameObj::Import_Rare(BitStreamClass&)', internal=True)
