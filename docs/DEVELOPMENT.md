# Development

Use an evidence-led loop: inspect the original owner, make the smallest coherent Vita-boundary correction, run focused validation, then canonically build before a hardware handoff.

## Rules

- Preserve EA/Westwood ownership above platform boundaries.
- Keep the upstream submodule pristine and stage every upstream change through a deterministic zero-fuzz patch.
- Keep retail data, saves, raw captures/videos, dumps, credentials, and generated build output out of Git.
- Do not claim panel correctness, controls, audio quality, pacing, or lifecycle success from host logs.
- Update the concise public status and durable reports when a change affects evidence, controls, capture, or hardware instructions.

## Typical workflow

```bash
git status --short
git -C upstream/CnC_Renegade status --short
RENEGADE_INCREMENTAL_STAGE=1 bash ./tools/stage_sources.sh
python3 -m unittest tools.test_vita_indexed_state_contract
RENEGADE_CANDIDATE_LABEL=A3.5-devNN RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
RENEGADE_CANDIDATE_LABEL=A3.5-devNN bash ./tools/build.sh
python3 tools/verify_repo_hygiene.py --root .
python3 tools/verify_public_docs.py --root .
python3 -m unittest tools.test_verify_public_docs tools.test_verify_repo_hygiene
```

Choose a focused contract that matches the changed boundary; do not use the example test above as a universal gate.
Do not restage during compilation. Replace the example label with the actual
new candidate and preserve existing runtime evidence. Check the exact staged
snapshot before publication, then verify the corresponding GitHub Actions run.
Private Codex handoff notes remain local, not in source history or release assets.

After staging the intended files, run `python3 tools/verify_publication_snapshot.py`.
It exports the exact Git index to a temporary checkout and runs the same three
publication gates as GitHub Actions. `--ref COMMIT` checks an existing commit.
This prevents ignored local files from accidentally satisfying public links.

## Upstream changes

1. Decide whether the portability issue belongs in a compatibility header, Vita boundary, or staging patch.
2. Add a minimal patch under `port/patches/` when upstream code must change.
3. Register it in `tools/stage_sources.sh`.
4. Confirm deterministic application with no `.orig` or `.rej` files.
5. Run focused tests and a proportional build.
6. Preserve the candidate identity and update evidence records.

## Physical evidence

A hardware candidate needs matching VPK, ELF, map, symbols, source/patch identity, build logs, SHA manifest, runtime log, and any returned capture or dump. Test only the declared scope and release synthetic controls on completion.

Read [Evidence and capture policy](EVIDENCE.md), [Current status](CURRENT_STATUS.md), and [Contributing](../CONTRIBUTING.md) before changing the active path.
