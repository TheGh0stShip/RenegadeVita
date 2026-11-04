# Independent review of active port-closure tools

Claude was consulted through the `claude` skill's isolated, tool-less `ask`
mode. DeepSeek was consulted through `deepseek-orchestrator` review; it had
only supplied source/facts, no repository or web access. Both received the
ARMv7 little-endian ILP32/VFP contract, host ABI distinction and play-test hold.
Their answers are advisory; local inspection decides integration.

## Claude — FFmpeg installed reuse

Raw response: local-builder/logs/claude-ffmpeg-install-review.log.

- Adopted fresh extraction: the old shared extracted source could diverge from
  the verified archive. Each rebuild now extracts inside its managed build tree.
- Adopted target-flagged GCC queries, separate status-checked assignments and
  rejection of unresolved relative/missing paths. A controlled-driver test
  exercises all four outcomes and requires the actual ARM flags.
- Expanded identity to GCC implementation/header/startup files, SDK headers
  and libraries, and binutils including nm/strip. Pinned FFmpeg configure
  actually selects cross-prefix nm and uses it for symbol-prefix admission.
- Adopted cache-restored receipt failure falling back to source build.
- Rejected the conditional claim that existing cache store failures abort the
  build: dependency_cache.sh explicitly contains failures and returns success.
  Restore delegates to verified manifest/copy admission in dependency_cache.py;
  retained corruption/restore tests cover that existing behavior.
- Added installed-file addition, symlink, malformed identity and direct record
  rejection checks. The former malformed-JSON assertion alone did not exercise
  symlink rejection. Existing cache key-mutation tests already cover changed
  file/tree inputs; they remain in the focused suite.
- No dependency writer was started while the native consumer build was live.
  A lock protocol spanning all consumers would require a separate build-system
  change; a writer-only lock would not protect current unlocked consumers.

Focused verification: 27 tests PASS across receipt, production query block and
dependency cache; bash syntax check PASS. A real installed-toolchain identity
probe is retained separately. Revised FFmpeg build/reuse still pending until
the current consumer reaches a terminal result.

## DeepSeek — full original-source inventory

Raw response: local-builder/logs/deepseek-source-inventory-review.txt.

- Adopted fail-closed case collision detection and actual staged input hashes.
  Current released source tree: zero casefold collisions. Among 632 directly
  mapped selected originals, 336 staged inputs differ from released bytes.
- Kept explicit mapping rather than speculative basename aliases. The one
  unmatched staged source was locally traced through the deterministic
  shared-loadingscreen patch to the original CombatGameMode loading-screen
  owner. That extraction now has a separate reviewed derived-source record.
- Rejected the claimed target-name substring bug: Python membership in
  output.parts compares complete path components. A GameExtra.dir fixture
  verifies it cannot satisfy a Game target query.
- Kept missing-output/target failure as deliberate fail-closed behavior for the
  selected CMake database. This tool is not a generic compile database parser.
- Kept literal manifest mentions explicitly lexical, including comments;
  configured selection comes only from the chosen target's compile database.
  Suggested alternate DSP syntaxes were not adopted without an actual input
  demonstrating them. No linked or functional closure was inferred.

Focused inventory tests PASS; generated local report includes database/review
hashes, staged source hashes, derived owner and zero unmapped staged inputs.
The 1,490-file inventory remains OPEN pending complete classification and
final linked-owner evidence.
