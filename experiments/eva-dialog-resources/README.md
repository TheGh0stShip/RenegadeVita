# EVA dialog resource correction awaiting integration

The active CMake frontend target invokes
`tools/generate_wwui_dialog_templates.py`. Its resource allowlist contains
only 128, 130, 131, 255 and 256. The sole native `FindResource` provider
returns null for every other dialog ID. Original EVA uses ID 153 and its
seven original child tabs use IDs 146 through 152. Thus the native pause
route cannot obtain these original control templates.

The original objectives and viewer tabs also use captionless `EDITTEXT`
statements. The existing generator treats these as captioned statements,
shifting the control ID, rectangle and style fields. Adding the missing
IDs alone would therefore introduce malformed controls.

`generator.patch` is an isolated proposed correction for both defects,
including the style constants needed by the original EVA resources.
No original engine dialog, retail file or active build input is changed.
Dev114's checkpoint-enabled canonical build was confirmed running when
this correction was prepared, so integration is deferred until it exits.

Next: apply with zero fuzz after canonical completion; generate and decode
all eight templates, checking original IDs, rectangles, styles and captions;
then retain an emulator pause/resume capture with the corrected candidate.
Resource completeness is not proof of visual correctness. Save/load and
options dialogs outside this resource family are not fixed by this patch.

## Retained host result

`python3 experiments/eva-dialog-resources/validate.py` passed in an isolated
temporary tree. Zero-fuzz patch application succeeded. The binary decoder
consumed all 13 generated templates with correct record alignment; all eight
EVA records are nonempty. The original EVA shell has 10 controls; its tab
rectangle, back-button rectangle and caption match. The objectives edit and
four viewer-description edits retain their original IDs, rectangles and
multiline/auto-horizontal-scroll flags. Output is retained in
`host-validation.log`. No emulator result is claimed for this correction.
