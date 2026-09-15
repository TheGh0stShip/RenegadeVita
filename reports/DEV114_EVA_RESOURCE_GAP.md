# Dev114 continuation: confirmed EVA resource omission

## Current plan

1. Finish the already-running checkpoint-enabled Dev114 canonical build
   without changing its build inputs.
2. Use that matching candidate to distinguish which restored player/star
   identity check fails; do not fabricate a replacement checkpoint player.
3. Integrate the isolated EVA resource and regression-contract patches after
   the build exits. Validate and retain a corrected candidate's pause/resume
   captures before claiming the missing controls are visually resolved.
4. Continue original M00 through its scripts and the implemented ending.
   Complete-demo, performance and physical acceptance remain unproven.

## Confirmed source defect

The active original-frontend CMake target generates only dialog IDs 128,
130, 131, 255 and 256. The native resource provider returns null for EVA
153 and every original encyclopedia child dialog, 146 through 152.
The original pause route therefore has no generated control templates.

Those child resources also expose an existing generator defect: captionless
`EDITTEXT` declarations are parsed as captioned controls, shifting their ID,
rectangle and style fields. The correction covers both issues and supplies
the original EVA style constants, preserving original WWUI ownership.

## Isolated implementation and evidence

- `experiments/eva-dialog-resources/generator.patch`: resource and parser fix.
- `experiments/eva-dialog-resources/contract.patch`: original C++ resource
  contract expanded to require all eight EVA records and original dimensions.
- `experiments/eva-dialog-resources/validate.py`: zero-fuzz application and
  binary decoding in a temporary tree. Passed for all 13 generated templates;
  EVA has 10 shell controls and all five captionless edits match original IDs,
  rectangles and styles. Output: sibling `host-validation.log`.
- `build/eva-resources-PfDANJ/`: retained generated include, ARM provider object,
  SHA-256 manifest and compiler logs. ARM provider compilation passed.
- `build/eva-resources-PfDANJ/host-contract-abi.log`: expanded original C++
  resource contract passed with `RENEGADE_HOST_ABI_TEST=1` and short wchar.
  The first standalone invocation omitted the host ABI define and failed the
  existing main-menu ID assertion; that failed invocation is retained rather
  than presented as a runtime regression.

These are isolated results, not changes incorporated in Dev114 and not
emulator visual proof. No retail data or original engine source was modified.
Unrelated options and save/load dialog resources are outside this correction.
