# Contributing

Renegade Vita is an active source port, not a clean-room reimplementation. Keep original EA/Westwood ownership above the Vita boundary and make each change small enough to review against evidence.

## Before changing code

1. Initialize the pinned source and verify both trees:

   ```bash
   git submodule update --init --recursive
   git status --short
   git -C upstream/CnC_Renegade status --short
   ```

2. Read the [program charter](reports/PROGRAM_CHARTER.md), [Current status](docs/CURRENT_STATUS.md), [Evidence policy](docs/EVIDENCE.md), and the current durable reports.
3. Keep `upstream/CnC_Renegade/` pristine. Use a compatibility header, Vita-boundary source, or a deterministic zero-fuzz patch under `port/patches/`.

## Validation and evidence

Run the smallest relevant contract first, then build in proportion to the change:

```bash
python3 -m unittest tools.test_vita_indexed_state_contract
RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
bash ./tools/build.sh
python3 tools/verify_repo_hygiene.py --root .
python3 tools/verify_public_docs.py --root .
```

Host, Vita3K, and physical Vita are separate evidence classes. A canonical build does not prove visible output, controller behavior, audio quality, frame pacing, or lifecycle behavior.

## What not to commit

Do not commit retail data, saves, generated build products, raw logs, raw captures/videos, PSP2 dumps, credentials, pairing material, private device configuration, or unrelated personal media.

A reviewed, non-retail PNG derivative may be added to the historical gallery only with a candidate label, source/provenance record, hash, and honest diagnostic/gameplay classification.

## Pull requests

Use an imperative, scoped subject. State the original owner preserved, the changed boundary, focused validation, canonical build status, and whether any physical result is actually returned. Never mark a developer candidate accepted without matching physical evidence.

See [Development](docs/DEVELOPMENT.md), [Versioning](VERSIONING.md), and [Security](SECURITY.md).
