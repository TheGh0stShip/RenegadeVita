# A3.5-dev5 identity and evidence candidate

## Decision

`A3.5-dev5` is the first candidate after the invalid dev4 return whose runtime
identity is compiled into the ARM target and verified after link and packaging.
It is ready for manual physical testing, but it is not an accepted milestone.

## Canonical identity

- Display/startup: `Renegade Vita A3.5-dev5`
- Runtime log: `ux0:data/renegade/user/logs/a35-dev5-runtime.log`
- Capture label: `A3.5-dev5 CAPTURE`
- Capture schema: 3, including candidate identity and explicit phase

One generated header supplies these values to the executable. The canonical
build uses a fresh ARM directory so every consuming translation unit is
compiled with the intended identity.

## Final artifacts

- VPK SHA-256:
  `e69919b557b8b2a807ac6437310d4c62072635ce1a493e63eee604a0c935287c`
- ELF SHA-256:
  `bf1a250554f0666fbc3814f0a47b784cd399a410bd823bf12885c8a92ebd2e05`
- map SHA-256:
  `c291b4ee313041885fdf08609dcc054308faff7482359efb57a65f75c5d4f6f5`
- symbols SHA-256:
  `365e09574d118c0d32c4b9d81f7a4ebf5f2a55147a2849078369ee7b0f303681`
- ELF-header SHA-256:
  `70c283d55b64e4e587fde592db97bc66b3ccd954f6a6e0beb87f20aaae5ca5f5`
- identity report SHA-256:
  `eb35b11f9aedf5be229cb0039cbbda5531b270880a62f4b0a23d63f483b6f780`
- diagnostics archive SHA-256:
  `674e1314984c944f7d60585ff953b63e5c9d1d03cfaaff4686682b7bdb55a790`

The VPK contains exactly `sce_sys/param.sfo` and `eboot.bin`. It contains no
retail data, save, log, dump, credential, or arbitrary user file.

## Post-link identity and lineage gate

All 15 checks passed on the final artifacts:

- intended candidate, display label, runtime-log path, and capture label found;
- `A3.5-dev1`, `a35-dev1-runtime.log`,
  `Renegade Vita A3.1 development`, and `A31 CAPTURE` absent;
- VPK readable and limited to the two expected entries;
- packaged `eboot.bin` SHA-256 exactly matches the verified SELF;
- SELF generated from the current ELF lineage.

## Build and test result

- Canonical command: `RENEGADE_CANDIDATE_LABEL=A3.5-dev5 bash tools/build.sh`
- Fresh ARM build: PASS, 456 Ninja actions
- Selected source: 424 original plus 21 port translation units
- Capture/evidence contract: 24/24 PASS
- Observer-loader contract: 46/46 PASS
- Input contract: 22/22 PASS
- Renderer state: 4/4 PASS
- Renderer lifecycle: 11/11 PASS
- Normal, AddressSanitizer, LeakSanitizer, and targeted Undefined Behavior
  Sanitizer routes: PASS
- Deterministic staging: PASS with zero fuzz and no reject/original residue
- Automatic deployment: not attempted

## Evidence lifecycle changes

- Important phase transitions use one candidate-specific append-only session
  log and are flushed rather than truncated or silently redirected to an
  independent path.
- The first static-world and first player-owned interactive captures are
  explicitly distinct phases.
- Manual Select capture remains available.
- Pre-clean-exit and best-effort fatal metadata bundles are emitted.
- Each capture artifact is closed, stat-checked, checked nonempty, and minimally
  validated before success is reported. Failed bundles write an external
  failure marker.
- Overlay counters use matching fixed-width integer format macros. Tests cover
  zero, ordinary, and maximum values without mismatched variadic formatting.

## Physical gate and unresolved observations

The first physical check is identity. Stop the test immediately unless the
startup label is dev5 and the dev5 runtime log is created. Only after that gate
passes may the returned evidence be used.

The invalid dev4 return suggested these issues, which remain observations to
verify rather than accepted diagnoses:

- invisible player body;
- invisible NPC bodies;
- incorrect first-person weapon;
- upside-down doors;
- vertically inverted static overhead/world camera while first-person view is
  correct.

No claim is made that dev5 repairs those visual issues. The observer and axis
repairs remain linked and host-tested, but require coherent physical evidence.
