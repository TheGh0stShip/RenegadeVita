# A3.5-dev4 identity and evidence correction

## Decision

`A3.5-dev4` is not an accepted physical candidate. Its VPK filename and
reports used the dev4 label, but the shipped executable retained dev1/A3.1
runtime identity strings. The physical return therefore cannot establish which
candidate code paths ran.

## Verified returned evidence

- VPK SHA-256: `f879336ae2ea13fbbad0b7eaef0dd0a80b0e40014549c76b073a703904c5b5a8`.
- ELF SHA-256: `cabcfd9f10499e02715877b7bf442783825a18fd3422fea7a40d46387411f03e`.
- The ELF contained stale executable strings: `A3.5-dev1`,
  `a35-dev1-runtime.log`, `Renegade Vita A3.1 development`, and `A31 CAPTURE`.
- The returned runtime log retained two identical dev1 startup lines only.
- The returned static-world screenshot is a valid 960x544 BMP, but its state
  records no player, no game or physics updates, no input actions, and no
  player-owned camera. It is not interactive gameplay evidence.
- The clean-exit bundle directory was empty, and no new PSP2 core dump was
  returned.
- The capture overlay rendered a corrupt draw count while its state JSON
  recorded 634 draw calls. The production formatter used an invalid `%.2F`
  conversion; it is replaced with fixed-width `PRIu64` fields and `%.2f`.

## Corrected gate

The build now generates one identity header before configuration and compile.
It supplies the candidate label, display label, runtime-log path, and capture
overlay label to the ARM target. A fresh candidate build directory is required.
The post-link verifier rejects an ELF unless the expected label, runtime-log
path, and capture label are present, the prohibited stale strings are absent,
and packaged `eboot.bin` matches the generated SELF by SHA-256. Its deterministic
JSON report is retained in the candidate diagnostics archive.

## Evidence and capture safeguards

Runtime and renderer breadcrumbs use the same generated runtime-log path.
Session startup appends a synchronized lifecycle boundary instead of
truncating the only retained evidence.
Capture bundles now record candidate, runtime log path, and explicit phase;
each artifact is closed, stat-checked, and minimally format-checked before the
bundle reports success. A failed bundle writes a failure marker outside the
bundle directory. A first static-world frame is labelled `static-world`, never
gameplay evidence.

## Physical gate

No VPK is hardware-ready until a fresh ARM build passes the identity verifier,
the packaged executable lineage check, logging/capture host contracts, and
artifact verification. The next physical tester instruction must first confirm
the candidate-specific startup identity and candidate-specific runtime log; if
either is missing, the test stops and is reported as contaminated evidence.

## Fresh canonical A3.5-dev5 candidate

A clean `A3.5-dev5` ARM build directory was configured after the identity
change. Its final verifier passed with ELF SHA-256
`bf1a250554f0666fbc3814f0a47b784cd399a410bd823bf12885c8a92ebd2e05`,
SELF SHA-256 `6d38d56cae433b5a1b4524056f31301174d1a6df603bb0c3103c146bcfc09e24`,
and VPK SHA-256 `e69919b557b8b2a807ac6437310d4c62072635ce1a493e63eee604a0c935287c`.
The ELF contains the expected dev5 display label, candidate-specific log path,
and capture label, and contains none of the four prohibited stale strings.

The capture self-test passes 24/24 in normal, AddressSanitizer, and Undefined
Behavior Sanitizer configurations. It verifies valid static and simulated
interactive-player-owned BMP bundles with matching state metadata. The fresh
dev5 VPK is now a coherent physical candidate, not an accepted milestone;
device interactive capture and verified clean-exit evidence remain required.

The ARM interactive runtime now requests its first automatic screenshot only
after the original Combat render trace reports both the player object and the
original camera. That bundle is labelled `interactive-player-owned` and records
the observed player/camera/world/render fields. It does not infer first-person
weapon, NPC, attachment, or door correctness; those remain separate evidence
phases for a later renderer investigation.
