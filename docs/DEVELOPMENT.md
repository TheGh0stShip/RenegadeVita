# Development

The productive loop is inspect, change the narrowest owner, run focused
validation, then run the canonical build before handing a candidate to hardware
testing.

## Working Rules

- Preserve original EA/Westwood ownership above platform boundaries.
- Keep the upstream submodule pristine.
- Make portability edits through `port/patches/` and `tools/stage_sources.sh`.
- Put Vita-specific code under `port/`.
- Keep generated artifacts out of Git.
- Do not claim physical correctness from host logs.

## Common Workflows

Stage deterministic upstream copies:

```bash
bash ./tools/stage_sources.sh
```

Run focused Python contracts:

```bash
python3 -m unittest tools.test_vita_camera_input_contract
python3 -m unittest tools.test_vita_loading_screen_contract
python3 -m unittest tools.test_vita_skin_submission_contract
```

Run a fast compile/link iteration:

```bash
RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
```

Run a package-producing fast build:

```bash
RENEGADE_FAST_SCOPE=package bash ./tools/build_fast_candidate.sh
```

Run the full candidate build:

```bash
bash ./tools/build.sh
```

Check source-control hygiene:

```bash
python3 tools/verify_repo_hygiene.py --root .
```

## Updating Candidate Labels

The default candidate label lives in:

- `CMakeLists.txt`
- `tools/build.sh`
- `tools/build_fast_candidate.sh`

The integration report and build checks may also pin expected source and patch
counts. Update those together when adding/removing selected source files or
patches.

## Adding A Portability Patch

1. Inspect the upstream source and decide whether the issue belongs in a
   compatibility header, a Vita boundary, or a deterministic patch.
2. Add a small patch under `port/patches/`.
3. Register the patch in `tools/stage_sources.sh`.
4. Run staging and confirm no `.orig` or `.rej` files appear.
5. Run focused tests and the relevant build.
6. Update reports if status, evidence, or behavior changed.

## Hardware Evidence

A hardware candidate needs the matching VPK, ELF, map, symbols, source
integration report, compiler log, identity report, SHA manifest, runtime log,
and any returned captures or dumps.

Do not overwrite retail data on the Vita. Do not treat an old route recording
as acceptance when dialogue timing, mission state, input mapping, or lifecycle
behavior changed.
