#!/usr/bin/env python3
"""Run pinned retail CClientControl plus original control/aim serializers."""
import argparse
import hashlib
import json
from pathlib import Path
from tt_identity_oracle import PIN
from tt_soldier_frequent_oracle import serialize


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dll', type=Path)
    args = parser.parse_args()
    image = args.dll.read_bytes()
    if hashlib.sha256(image).hexdigest() != PIN:
        parser.error('Reference differs from pinned b9000')
    cases = [('creation', 0), ('soldier', 0), ('soldier', 1),
             ('armed', 0), ('missing', 0), ('delete_pending', 0), ('idle', 0)]
    print(json.dumps({'schema': 1, 'reference_sha256': PIN,
                      'scope': 'Retail CClientControl/Control/Soldier/Armed exports; synthetic Smart list and position accessor',
                      'cases': [serialize(image, state, client_state=True, control_mode=mode)
                                for mode, state in cases]}, indent=2))
