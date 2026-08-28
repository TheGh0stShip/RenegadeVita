# Contributing

This repository is an active source port, not a clean-room reimplementation.
Changes should preserve original EA/Westwood ownership above the Vita platform
boundary and should be small enough to review against evidence.

## Before Changing Code

1. Initialize the upstream source submodule.

   ```bash
   git submodule update --init --recursive
   ```

2. Check both working trees.

   ```bash
   git status --short
   git -C upstream/CnC_Renegade status --short
   ```

3. Read the current context:
   `AGENTS.md`, `docs/CURRENT_STATUS.md`, `reports/BUILD_STATE.json`, and
   `reports/LIVE_PROGRESS.md`.

The upstream submodule is canonical and should remain pristine. If upstream
source needs portability changes, add or update a deterministic patch under
`port/patches/`, register it in `tools/stage_sources.sh`, and regenerate
`staging/`:

```bash
bash ./tools/stage_sources.sh
```

Every staging patch must apply with zero fuzz. Do not leave `.orig` or `.rej`
files in `staging/`.

## Validation

Use the smallest relevant test first, then expand based on risk:

```bash
python3 -m unittest tools.test_vita_camera_input_contract
RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
bash ./tools/build.sh
```

Host tests, Vita3K, and physical Vita runs are separate evidence classes. Host
validation never proves physical visual correctness, controls, audio output,
or frame pacing.

Before a review or commit, run:

```bash
python3 tools/verify_repo_hygiene.py --root .
```

Do not commit retail data, generated build products, logs, screenshots, crash
dumps, credentials, local `.agents/` automation, or unreviewed submodule
changes.

## Commit Expectations

Use imperative, scoped commit messages:

```text
Document Vita installation workflow
Fix M00 action button mapping
Add transition diagnostics contract
```

Update durable docs or reports when a change affects runtime status, evidence,
controls, build workflow, or hardware-test instructions. Do not mark a dev
candidate as a milestone until matching physical evidence exists.

See [Development](docs/DEVELOPMENT.md) for the full modification workflow.
