# DX8 ambient render-state identifier

The Vita compatibility header now declares `D3DRS_AMBIENT` as 139 instead
of 26. The original light-environment caller in
`upstream/CnC_Renegade/Code/ww3d2/dx8wrapper.cpp` supplies this state to the
platform boundary. Both original and native state caches have 256 slots;
139 is within their bounds. The native renderer routes ambient updates into
its fixed-function color evaluation and native ambient application.

The previously retained header comparison
`reports/generated/sweeps/d3d8_enum_values.json` identified 26 versus 139
(reference SHA-256
`5d138bc5adc616be1ed29f883a50d432c6f5f3f8af5c5d6057e98c76a990cabb`).
That historical receipt remains unchanged.
[Microsoft's render-state documentation](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3drenderstatetype)
also declares ambient as 139. That page documents D3D9; it corroborates the
retained D3D8 header comparison rather than replacing it with a D3D9 API port.
No SDK implementation or third-party source was copied.

Original callers compiled against the same incorrect local declaration could
agree internally. This correction closes numeric API compatibility; it does
not establish that previously observed lighting defects were caused by it.
State 26 must not be interpreted as ambient.

## Regression evidence

The retained executable contract now sends literal API state 139 independently
of the local declaration and verifies that state 26 leaves the color untouched.
Before the correction, both checks failed. Afterward all 13 render-state checks
pass. The fast build gate now runs this executable alongside the original DDS
contract; the canonical gate already ran it. Twenty-two focused source/header
comparison tests pass. Native visual correctness and physical acceptance remain
open. No packaging, emulator launch, or physical device action is part of this
source correction.

Dev227 passes all 136 incremental ARM compile/link actions and retained ELF
identity checks. The artifact is ELF32 little-endian ARMv7/EABI5 with VFP
register arguments. The existing mixed two/four-byte wchar_t linker warnings
remain open. The fast sanitizer gate passes all 492 tests; the executable DDS
and render-state gates pass 11 and 13 checks respectively.

| Artifact | SHA-256 |
|---|---|
| Dev227 ELF | `c1e116e3aa2de2ed532754b4e7ea75639dbabc69f222e8a7a186297e1e56171b` |
| Dev227 map | `6e6150c99cd1a0ee6c83d1edec65d30918a76c1b2a98f399e0b77cf8ccd007d4` |
| Compatibility header | `c8e7b38550c76944c2c0b8eeec14cf7b457de669d5826c571bae3ea11a86a0b4` |

Managed compile log:
`local-builder/logs/a35-dev227-fast-20261004-123745-build.log`.

Adjacent D3D work was inspected read-only. The neighboring `d3dvita-demo`
compatibility header retained the same value 26 at inspection; it was not
modified. This change does not select a different rendering backend.
