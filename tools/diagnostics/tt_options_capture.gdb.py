"""GDB-only bounded capture of one incoming server-options body, not process RAM.

Set RENEGADE_OPTIONS_CAPTURE to a NEW file in a mode-0700 directory. Source
this script in a matching-symbol host admission probe. It never reads identity
providers, response events, arbitrary frames, outgoing packets or other objects.
The options body contains public server settings, but keep captures private.
"""
import hashlib
import json
import os
from pathlib import Path
import stat

import gdb


try:
    output = Path(os.environ['RENEGADE_OPTIONS_CAPTURE'])
    if output.exists() or output.parent.is_symlink():
        raise RuntimeError('Capture requires a new file in a private directory')
    if stat.S_IMODE(output.parent.stat().st_mode) != 0o700:
        raise RuntimeError('Capture parent must have mode 0700')
except (KeyError, OSError, RuntimeError) as error:
    gdb.write(str(error) + '\n')
    gdb.execute('quit 2')


class OptionsBreakpoint(gdb.Breakpoint):
    def stop(self):
        self.enabled = False
        packet = gdb.parse_and_eval('packet').cast(gdb.lookup_type('cBitPacker').reference())
        start, end = int(packet['BitReadPosition']), int(packet['BitWritePosition'])
        buffer = packet['Buffer']
        capacity = buffer.type.sizeof
        if not 0 <= start <= end <= capacity * 8 or end == start:
            raise RuntimeError('Invalid options bit range')
        raw = bytes(gdb.selected_inferior().read_memory(int(buffer.address), (end + 7) // 8))
        bits = ''.join(format(byte, '08b') for byte in raw)[start:end]
        payload = bytes(int(bits[index:index + 8].ljust(8, '0'), 2)
                        for index in range(0, len(bits), 8))
        binary = Path(gdb.current_progspace().filename)
        record = {'schema': 1, 'event': 'cGameOptionsEvent::Import_Creation',
                  'evidence_class': 'host_incoming_server_options_only',
                  'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                  'entry_read_bits': start, 'payload_bits': len(bits),
                  'payload_hex': payload.hex()}
        with os.fdopen(os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'w') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
        gdb.write('Bounded incoming server-options capture complete.\n')
        return False


OptionsBreakpoint('cGameOptionsEvent::Import_Creation(BitStreamClass&)', internal=True)
