# Evidence and capture policy

A Renegade Vita claim is only as strong as the evidence class behind it.

## Evidence classes

| Evidence | Can establish | Cannot establish |
| --- | --- | --- |
| Source review / focused tests | Intended ownership, logic, and regression contracts | Vita panel output, controls, audio, pacing, or lifecycle |
| Canonical ARM build | Candidate identity, package closure, artifact contents, and retail exclusion | Hardware behavior |
| Vita3K | Fast-path iteration signals | Physical Vita acceptance |
| Physical Vita with matching artifacts | Controls, visual output, audio behavior, pacing, storage, and lifecycle for the observed scope | Unobserved scenes or later candidates |
| Screenshot / VDB frame | The recorded frame and its labelled visual state | General gameplay acceptance by itself |
| Recorder MP4 | A finalized recorded sequence | Hardware acceptance by itself, especially after a fault |

## Candidate custody

Every hardware observation must bind to the exact candidate:

1. VPK and packaged SELF SHA-256;
2. matching ELF, map, symbols, and source/patch identity;
3. runtime log and any crash dump;
4. labelled screenshots, VDB metadata, or finalized recorder MP4 when available;
5. a concise physical observation that says what was actually seen.

Do not use an older ELF to symbolicate a newer dump. Do not relabel a loading or
black frame as gameplay.

## Screenshot policy

A publishable gallery image must be a reviewed, non-retail derivative with:

- candidate label and capture reason;
- known evidence source and SHA-256;
- an honest label such as gameplay, loading diagnostic, or failed frame;
- no credentials, personal media, save data, raw dump, or retail asset bundle.

The historical gallery is not presently a controlled same-camera comparison.
Earlier engine-timed captures could occur before the panel settled. The intended
replacement is the exact-title VDB post-render framebuffer provider, which is
not yet installed on the active device. Its protocol endpoint is
`capture.screen.v1`; it is intended to complement, not replace, observed
physical Vita evidence.

## Video policy

The optional title-scoped recorder writes a local MP4 only after it finalizes.
The red recorder overlay confirms start, not file custody. A crash can leave no
MP4. Raw video stays out of Git; only a reviewed, lawful derivative may be
published after its candidate and provenance are established.

The sole current exception is the user-authorized Dev87 physical recording:
`2026-08-31_004224.mp4`, SHA-256
`e6f10ac1add71090bfa83246f4829b668d2d7629f25e5c0f3dfd1eb09ea44aaf`. A
dedicated private `gh-pages` branch contains only the player, one
non-sensitive poster derivative, and that exact MP4—not the main source tree,
retail files, VPKs, logs, saves, dumps, or device data. GitHub rejected Pages
for this private repository's current plan, so no public player is live. The
recording remains failure-context evidence, not an acceptance claim.

The user has also authorized an **unlisted YouTube** upload of the exact MP4
for a functional embedded player. It is pending a connected upload-capable
account; no copy has been uploaded or made public by this workspace.

## Repository exclusions

Never commit or upload:

- retail game assets or altered retail files;
- VPK/ELF/SELF build products, raw logs, raw captures, raw video, or PSP2 dumps,
  except the explicitly user-authorized Dev87 private player branch above;
- saves, pairing material, credentials, device configuration, or arbitrary personal media;
- memory content beyond deliberately sanitized crash metadata.

See [Current status](CURRENT_STATUS.md), [Evidence capture](DEMO_CAPTURE.md), and the [historical screenshot timeline](HISTORICAL_SCREENSHOT_TIMELINE.md).
