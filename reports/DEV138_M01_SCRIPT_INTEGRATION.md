# Dev138 M01 script integration

The full-port profile now links the original `Mission01.cpp` script unit. The
M00 demo profile and original upstream source are unchanged. A M01-only
compatibility header supplies the callback defaults accepted by the original
MSVC script build but rejected by GCC, without changing the script ABI table.

Build: `cmake -S . -B build/vita-dev135-campaign -DRENEGADE_CANDIDATE_LABEL=A3.5-dev138 -DRENEGADE_VITA_M00_DEMO=0 -DRENEGADE_VITA_TITLE_ID=RNEGC3101 -DRENEGADE_VITA_CONTENT_ID=EP9000-RNEGC3101_00-RENEGADEVITA0110`, then `cmake --build build/vita-dev135-campaign --parallel 8`.

The ARM ELF, SELF, and VPK built. `arm-vita-eabi-nm -C` finds M01 script
registrants including `M01_Mission_Controller_JDG`. The VPK inventory contains
only `eboot.bin` and `sce_sys/param.sfo`. Repository hygiene and public-doc
checks pass. VPK SHA-256: `31f846ce145ddf2834f8d0153b8e7a48b6975e3a1debd0fcfa93535e744d5520`.

| Mission ID | Initialization | Required gameplay/objectives | Normal transition | Save/load | Build/evidence |
| --- | --- | --- | --- | --- | --- |
| M13 | passed in Dev137 Vita3K | unverified | unverified | implemented but untested | Dev137 Vita3K script registration/first frame |
| M01 | unverified | original script unit linked; untested | unverified | unverified | Dev138 ARM build and symbol inspection only |

M13 success is emitted by the original M00 end-game timer; the current Vita
loop observes mission completion and exits instead of dispatching the original
campaign continuation. This remains the immediate progression blocker. No
Dev138 Vita3K or physical-Vita gameplay claim is made.
