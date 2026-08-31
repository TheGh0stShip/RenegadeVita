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
bash ./tools/stage_sources.sh
python3 -m unittest tools.test_vita_indexed_state_contract
RENEGADE_FAST_SCOPE=compile bash ./tools/build_fast_candidate.sh
bash ./tools/build.sh
python3 tools/verify_repo_hygiene.py --root .
```

Choose a focused contract that matches the changed boundary; do not use the example test above as a universal gate.

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
