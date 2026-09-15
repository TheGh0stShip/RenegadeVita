# Dev100 Vita3K candidate workflow

Vita3K is preliminary evidence only. Final release acceptance requires the
entire authentic M00 route on both PS Vita and PSTV, after the physical-test
hold is lifted. A successful process launch, host decode, or package build is
not proof of visible text, audible pacing, mission completion, or 60 FPS.

## Local prerequisites

The user's Windows installation is `D:\Vita3K\Vita3K.exe`. Its existing VFS
is `C:\Users\steve\AppData\Roaming\Vita3K\Vita3K`. Existing firmware,
`ur0/data/libshacccg.suprx`, shared retail archives, M00, and both intro movies
are already present. Reuse them without modifying or redistributing them.
Never delete other installed retail missions to create the demo.

Dev101 additionally supports a user-provided Arial font at
`ux0:data/renegade/user/fonts/arial.ttf` when the original retail font candidates
are absent. The local Windows Arial used for emulator setup is recorded in
`reports/DEV101_FONT_AND_DEMO_PROFILE.md`. Do not put proprietary fonts in the
VPK or public diagnostics. Keep original retail files unchanged.

## Install only the matching title

Use the completed candidate's VPK and retain its ELF, SELF, map, symbols,
source identity, build logs, dependency provenance, and SHA manifest first.
Do not install a partial build or infer hashes from a previous Dev100 attempt.
Close an existing Vita3K session normally before replacing the title.

```bash
python3 tools/prepare_vita3k_demo.py \
  --candidate A3.5-dev100 \
  --vpk /absolute/path/to/RenegadeVita-A3.5-dev100.vpk \
  --vfs /mnt/c/Users/steve/AppData/Roaming/Vita3K/Vita3K \
  --evidence-root /absolute/path/to/local-vita3k-evidence
```

The preparation receipt records the VPK hash, retail prerequisite hashes,
replaced title-file hashes, and title-scoped backups. Only `RNEGA3101` app
files are installed. Retail bytes, saves, and firmware are not copied into
the evidence bundle. Backups are local recovery material, not public release
contents.

## Bounded Windows launch

Invoke `tools/run_vita3k_demo_windows.ps1` through Windows PowerShell, passing
Windows paths. The installed `eboot.bin` hash must match the candidate SELF.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\path\to\run_vita3k_demo_windows.ps1 `
  -Candidate A3.5-dev100 `
  -EvidenceDirectory D:\Vita3K\RenegadeEvidence\Dev100-unique-run `
  -ExpectedEbootSha256 MATCHING_64_CHARACTER_SELF_HASH `
  -TimeoutSeconds 90
```

The runner refuses to attach to another running Vita3K instance. It creates
a run-owned config using the existing VFS, launches only `RNEGA3101`, retains
stdout/stderr and before/after runtime logs, and terminates only the child
process it created at the deadline. It sends no synthetic controller input.
Screenshots are attempted only when that emulator window is foregrounded;
they are labelled window captures, not original framebuffer captures.

The first bounded run is an intro/menu observation, not an unattended full
tutorial run. Inspect matching images and runtime breadcrumbs before choosing
any next input sequence. Keep M00 objectives, controls, scripts, and completion
owned by the original engine; do not fabricate success to pass the demo gate.

`TIMEOUT_UNASSESSED` can mean running gameplay or a hang. Likewise,
`PROCESS_EXITED_ZERO_UNASSESSED` is not a pass. Compare new versus old runtime
hashes to reject stale logs, then tie actual checkpoints to the exact package.
Do not publish raw local config or title backups as diagnostic telemetry.
