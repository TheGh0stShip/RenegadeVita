"""Capture one rejected incoming object update for offline protocol diagnosis.

Use RENEGADE_REPLICATION_CAPTURE with a new file under a private 0700 directory.
No identity packets, memory dumps, function calls or gameplay mutations.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import gdb

output = Path(os.environ['RENEGADE_REPLICATION_CAPTURE'])
if output.exists() or output.parent.is_symlink() or stat.S_IMODE(output.parent.stat().st_mode) != 0o700:
    # Raising alone does not stop later batch "-ex run" commands.
    gdb.write('Capture requires a new file in a private 0700 directory\n', gdb.STDERR)
    gdb.execute('quit 2')
binary_hash = hashlib.sha256(Path(gdb.current_progspace().filename).read_bytes()).hexdigest()


class Failure(gdb.Breakpoint):
    def stop(self):
        frame = gdb.newest_frame()
        evidence = {'schema': 1, 'event': 'incoming_replication_rejected',
                    'evidence_class': 'host', 'binary_sha256': binary_hash,
                    'object_id': int(frame.read_var('object_id')),
                    'stage': frame.read_var('stage').string(length=32).split('\0')[0]}
        while frame:
            if frame.name() and 'cNetwork::Client_Packet_Handler' in frame.name():
                try:
                    packet = frame.read_var('packet').cast(gdb.lookup_type('cBitPacker').reference())
                    start, end = int(packet['BitReadPosition']), int(packet['BitWritePosition'])
                    buffer = packet['Buffer']
                    if not 0 <= start <= end <= buffer.type.sizeof * 8:
                        raise RuntimeError('Invalid packet range')
                    evidence.update(read_bits=start, packet_bits=end,
                                    packet_hex=bytes(gdb.selected_inferior().read_memory(
                                        int(buffer.address), (end + 7) // 8)).hex())
                    try:
                        evidence['object_type'] = str(frame.read_var('object').dereference().dynamic_type)
                    except gdb.error:
                        evidence['object_type'] = 'optimized out'
                    break
                except gdb.error:
                    pass
            frame = frame.older()
        if 'packet_hex' not in evidence:
            raise RuntimeError('No incoming object packet found on the rejection stack')
        with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(evidence, stream, indent=2)
            stream.write('\n')
        self.enabled = False
        return False


Failure('A31ClientConnect::Packet_Decode_Failed(int, char const*)', internal=True)
