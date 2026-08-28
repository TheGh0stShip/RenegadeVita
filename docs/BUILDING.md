# Building

`tools/build.sh` is the canonical build. It is the only build path that should
be used for a hardware-test candidate or a milestone candidate.

## Canonical Build

```bash
bash ./tools/build.sh
```

The script checks:

- required host tools and VitaSDK files;
- pinned upstream submodule revision and clean upstream state;
- retained host semantic fingerprints;
- focused host contracts;
- deterministic zero-fuzz staging;
- source-integration report fields;
- Vita ARM ELF, SELF, and VPK identity;
- VPK contents, confirming no retail assets are packaged;
- candidate diagnostics and SHA-256 manifests.

## Fast Iteration

Use the fast builder only for local iteration:

```bash
RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
RENEGADE_FAST_SCOPE=package bash ./tools/build_fast_candidate.sh
```

Fast builds do not replace canonical evidence. Run `tools/build.sh` before
handing a VPK to a physical tester.

## Environment Variables

- `RENEGADE_VITASDK`: VitaSDK root. Defaults to `/usr/local/vitasdk`.
- `RENEGADE_BUILDER_ROOT`: managed output root. Defaults to the checkout when
  no writable managed root exists.
- `RENEGADE_DIST_ROOT`: override artifact lookup/output for helper scripts.
- `RENEGADE_BUILD_JOBS`: parallel build jobs. Canonical default is conservative.
- `RENEGADE_CANDIDATE_LABEL`: candidate label such as `A3.5-dev79`.
- `RENEGADE_RETAIL_ROOT`: host retail Renegade root used by host validation.
- `RENEGADE_REUSE_HOST_VALIDATION_LOG`: explicit retained host-validation log
  when host retail data is unavailable.

## Outputs

Successful canonical builds publish:

- `RenegadeVita-<candidate>.vpk`
- `RenegadeVita-<candidate>.elf`
- `RenegadeVita-<candidate>.map`
- `RenegadeVita-<candidate>.symbols.txt`
- `<candidate>-BUILD_REPORT.txt`
- `<candidate>-COMPILER_LOG.txt`
- `<candidate>-HOST-VALIDATION.log`
- `<candidate>-SOURCE_INTEGRATION_REPORT.json`
- `<candidate>-IDENTITY-VERIFICATION.json`
- `<candidate>-BUILD-DIAGNOSTICS-<timestamp>.zip`
- `<candidate>-SHA256SUMS.txt`

Generated artifacts stay out of Git.

## Windows Wrapper

`RenegadeVita_BUILD.ps1` is optional. It calls the Bash script through WSL and
does not contain an embedded payload:

```powershell
.\RenegadeVita_BUILD.ps1
.\RenegadeVita_BUILD.ps1 -CandidateLabel A3.5-dev79 -BuildJobs 8
```

When in doubt, run the Bash script directly from WSL.
