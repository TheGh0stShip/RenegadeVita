# Dev109 loading animation failure return

Latest retained source evidence: installed always.dat contains if_lvl94load.w3d,
SHA-256 422df0bb80df10720d0576308f41269af0681d3e7765b1623759d0d8a4fe1596,
with original uncompressed IF_LVL94LOAD animation/hierarchy, 61 frames at 30 FPS.
The original loading parser requests IF_LVL94LOAD.IF_LVL94LOAD, matching those
headers. See build/dev110-host-evidence/loading-w3d-animation.json. This closes
neither native binding nor visible animation; it rules out an absent animation
in this archived model as an unsupported explanation.

Prepared wwui-loading-animation-evidence.patch under build/dev110-host-evidence
records up to 16 changed percentage buckets with animation name/frame count and
requested manual frame, or one missing-binding report. Hunk counts are generated
from the before/after blocks, not manually maintained. It remains unregistered
and unapplied while Dev109 compiles. This is diagnostic evidence plumbing, not
a claimed loading-bar fix.

User reports the loading progress bar is not visibly updating. This supersedes
any inference of visual animation from milestone logs or a still capture.

Matching runtime reaches original Combat progress 0 through 7, with repeated
LoadingScreenClass draws and status callbacks during object loading. Existing
LoadingScreenClass computes a percentage and calls the original backdrop's
Set_Animation_Percentage. That method changes a W3D animation frame only when
both Model and Anim are non-null. Current readiness evidence checks the model
only: IF_LVL94LOAD exists, but no matching animation-binding/frame evidence was
retained. Therefore adding more callbacks or claiming the bar works from the
progress integers would not resolve this return.

Next: establish selected backdrop animation name, successful original Get_HAnim,
frame count and manual frame changes against sequential captures. Preserve the
original LoadingScreenClass/MenuBackDropClass/W3D animation ownership. Do not
replace the retail animation with an invented progress renderer, extend waits
to conceal a broken binding, or claim a fix before visible updates occur.

Other prepared Dev110 work is the Data Disc texture-readiness correction and
original quicksave dispatch. Numeric HUD Font3D investigation found that native
SurfaceClass::Copy rejects mixed formats while desktop uses D3DX conversion;
that compatibility gap is not yet proven to cause the captured digits. No
numeric-font or loading-animation source fix has been applied. Dev109 canonical
source remains unchanged while compiling; physical testing remains held.
