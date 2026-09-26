#!/usr/bin/env python3
"""Compare a completed loaded-vehicle probe log against retail client controls."""
import argparse
import json
from pathlib import Path
import re


def validate(log):
    fixture = json.loads((Path(__file__).parent / 'fixtures/tt_client_control_b9000.json').read_text())
    assert fixture['reference_sha256'] == 'd520443f5618b7d34d48a2e1d4b8348516d53d3ac9a7e201077e259f64c100db'
    found = re.findall(r'^tt_client_control.vector_(\d)=(-?\d+):(\d+):([0-9a-f]+)$', log, re.M)
    assert len(found) == 14, f'Expected seven vectors in each of two cycles, got {len(found)}'
    for offset, (profile, object_id, bits, payload) in enumerate(found):
        index = offset % 7
        assert int(profile) == index
        case = fixture['cases'][index]
        assert int(bits) == case['bits'], (index, bits, case['bits'])
        # Loaded objects have real allocated IDs. Check the exact outer ID and
        # compare every subsequent bit with the independently executed retail.
        assert payload[:8] == f'{int(object_id) & 0xffffffff:08x}'
        assert payload[8:] == case['hex'][8:], (index, payload, case['hex'])
        if index in (1, 2, 3):
            assert int(object_id) > 0
            assert case['pending_one_time'] == case['pending_continuous'] == 0
        else:
            assert payload == case['hex']
    assert log.count('tt_client_control.runtime.result=PASS') == 2
    assert 'FAIL' not in log and 'ERROR: AddressSanitizer' not in log
    assert 'PASS (two in-process cycles)' in log


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    validate(args.log.read_text())
    print('PASS: seven retail client-control vectors, two loaded runtime cycles')
