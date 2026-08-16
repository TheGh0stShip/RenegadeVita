# Contributing

This repository accepts changes through normal Git branches and pull requests.
Please keep each change narrow, reviewable, and reproducible.

## Before changing code

1. Initialize the EA source submodule:
   `git submodule update --init --recursive`.
2. Check both working trees:
   `git status --short` and `git -C upstream/CnC_Renegade status --short`.
3. Read `AGENTS.md` and the relevant records in `reports/`.

The upstream submodule is canonical and should remain pristine. Add portability
and behavior changes as explicit files in `port/patches/`, then register them
in `tools/stage_sources.sh`. Regenerate `staging/` with:

```bash
bash ./tools/stage_sources.sh
```

Every patch must apply with `--fuzz=0`; do not leave `.orig` or `.rej` files.

## Validation expectations

Run the smallest relevant host target first. For changes affecting a physical
candidate, complete the project’s canonical build and preserve its logs,
hashes, ELF/map/symbol files, VPK inventory, and report updates. Host results
are never a substitute for physical Vita evidence.

Do not automatically deploy to a Vita. Do not commit any of the following:

- retail `Data/` content or extracts;
- save files, user configuration, dumps, screenshots, credentials, or logs;
- generated VPKs, SELF/ELF release artifacts, or build directories;
- unreviewed changes inside the upstream submodule.

Before opening a change for review, run the repository hygiene verifier:

```bash
python3 tools/verify_repo_hygiene.py
```

## Commit conventions

Use imperative, scoped messages such as:

```text
Add observer loader diagnostics contract
Fix Vita controller Y-axis mapping
Document A3.5 hardware evidence
```

Update durable reports when a change affects status, decisions, validation, or
hardware evidence. Do not mark an internal developer build as a milestone or
release without the required physical acceptance evidence.
