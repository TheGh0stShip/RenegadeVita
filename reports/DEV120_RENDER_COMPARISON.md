# Dev120 renderer comparison

Original loading bar fills in matching r1 window video. Main menu MP3 decodes
and native stream output is nonzero. Remaining sky/elevator and credits defects
need independent renderer validation; final user playthrough stays held.

R2: same Dev120 SELF, Hotwire checkpoint, OpenGL, optional render-work caches
disabled with RVRC1 0. Prior RVRC1 F backed up with hash receipt under
build/dev120-render-baseline/. Hotwire reload and interior geometry render;
bounded released right-stick/forward/strafe inputs reached the exit doorway,
but did not establish a useful sky/elevator comparison. Inconclusive; do not
adopt cache disabling as a fix. Restore original flag after stopping r2.

Runtime PNG capture setup initially used enum 0 incorrectly, disabling output.
Corrected runner to enum 2 from official Vita3K Qt settings code:
https://github.com/Vita3K/Vita3K/blob/master/vita3k/gui-qt/src/settings_dialog.cpp
The enum is None/JPEG/PNG. Dev119's actual black JPEG captures remain distinct
retained evidence. Run-owned configs only; global emulator config unchanged.

Next: original outdoor Power Plant checkpoint, same package and restored cache
mode, Vulkan backend in run-owned config; compare window and native captures.
No physical acceptance or renderer-correctness claim yet.

R2 stopped; prior RVRC1 F restored. R3 launched at Power Plant with the same
Dev120 SELF, Vulkan and screenshot PNG enum 2, 300-second bound, runner 63067.
Evidence Dev120-powerplant-vulkan-20260914-r3. Native input disabled; original
immutable Power Plant save copied to fresh dev120-powerplant-vulkan-20260914.sav.

Correction after inspection: r3 window title and emulator log prove it actually
used OpenGL despite the run-owned YAML requesting Vulkan. It is NOT Vulkan
comparison evidence. PNG capture now creates a file, but it is entirely black
while the game window is visible, matching the prior JPEG defect. Runner now
passes the explicit supported --backend-renderer argument as well; next launch
must verify the actual renderer in the window/log. Power Plant master starts
inside Petrova's room; use Gunner master for an outdoor sky comparison.

User wall return during r4: exact visible capture 20260914T194157182Z shows a
broad brown polygon across the interior left wall. Retained receipt and images
under build/dev120-wall-return/. This is an observed world geometry/depth
artifact, not a proven texture-decoder diagnosis. Native emulator PNG at
14:42:04 local is entirely black. Two posted Select attempts and a separately
focused, released RightShift scan-code press did not create a new original
game capture bundle; consumption/readiness unproven. No navigation since user
returned. R4 still actually OpenGL despite explicit backend argument; both
backend comparison attempts are inconclusive. Do not report Vulkan acceptance.
