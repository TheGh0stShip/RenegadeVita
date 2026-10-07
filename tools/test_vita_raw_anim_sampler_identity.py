"""Prove the a36 raw-animation sampler patches are bit-identical.

Builds tools/vita_raw_anim_sampler_identity_test.cpp twice: once against the
staged ww3d2/wwmath sources and once against private copies with the a36
raw-animation sampler and quaternion/matrix single-precision patches reversed (the unmodified implementation).  Both runs drive the real
HRawAnimClass samplers, HTreeClass::Anim_Update/Blend_Update and
Build_Matrix3D over the same random animations, frames and special values and
write every output float as raw bytes.  The streams must match exactly.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SAMPLER_PATCH = ROOT / "port/patches/ww3d2-a36-raw-anim-sampler-inline.patch"
# Build_Matrix3D single precision comes from the WWMath ARM patch (quat/matrix3d/matrix3).
MATRIX_PATCH = ROOT / "port/patches/wwmath-a36-quat-matrix-single-precision.patch"
WW3D2_FILES = ("motchan.h", "motchan.cpp", "hrawanim.cpp")
WWMATH_FILES = ("quat.cpp", "matrix3d.cpp", "matrix3.cpp")


def _build_and_run(directory, variant, label, sanitize):
    executable = Path(directory) / f"identity-{label}"
    command = ["c++", "-std=gnu++17", "-O2", "-g", "-fpermissive", "-w",
               "-ffunction-sections", "-fdata-sections", "-DNDEBUG=1",
               "-D_UNIX=1", "-DRENEGADE_HOST_ABI_TEST=1", "-DRENEGADE_VITA_PORT=1",
               f'-DRAW_ANIMATION_SOURCE="{variant / "hrawanim.cpp"}"',
               "-include", str(ROOT / "port/compatibility/include/msvc_compat.h")]
    if sanitize:
        command += ["-fsanitize=address,undefined", "-fno-sanitize=vptr",
                    "-fno-sanitize-recover=all"]
    command += ["-I", str(variant)]
    for relative in ("port/compatibility/include", "staging/ww3d2", "staging/wwmath",
                     "staging/wwlib", "staging/wwsaveload", "staging/wwdebug"):
        command += ["-I", str(ROOT / relative)]
    command += [str(ROOT / "tools/vita_raw_anim_sampler_identity_test.cpp"),
                str(variant / "motchan.cpp"), str(variant / "quat.cpp"),
                str(ROOT / "staging/wwmath/wwmath.cpp"),
                str(variant / "matrix3d.cpp"),
                str(ROOT / "staging/ww3d2/htree.cpp"),
                str(ROOT / "staging/ww3d2/pivot.cpp"),
                "-Wl,--gc-sections", "-o", str(executable)]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    output = Path(directory) / f"stream-{label}.bin"
    result = subprocess.run([str(executable), str(output)], cwd=ROOT,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return result.stdout, output.read_bytes()


def _variant(directory, name, reverse):
    variant = Path(directory) / name
    variant.mkdir()
    for module, files in (("ww3d2", WW3D2_FILES), ("wwmath", WWMATH_FILES)):
        for file_name in files:
            shutil.copy(ROOT / "staging" / module / file_name, variant / file_name)
    if reverse:
        for patch in (SAMPLER_PATCH, MATRIX_PATCH):
            result = subprocess.run(
                ["patch", "--batch", "-R", "--fuzz=0", "--no-backup-if-mismatch",
                 "-p1", "-d", str(variant), "-i", str(patch)],
                capture_output=True, text=True)
            if result.returncode != 0:
                raise AssertionError(result.stdout + result.stderr)
    return variant


class RawAnimSamplerIdentityTests(unittest.TestCase):
    def test_patched_sampler_matches_unmodified_bytes(self):
        with tempfile.TemporaryDirectory(prefix="renegade-anim-identity-") as directory:
            current = _variant(directory, "current", reverse=False)
            reference = _variant(directory, "reference", reverse=True)
            # The reference really is the pre-patch implementation.
            self.assertNotIn("Raw_Anim_Frame_Floor", (reference / "hrawanim.cpp").read_text())
            self.assertIn("MotionChannelClass::\nGet_Vector",
                          (reference / "motchan.cpp").read_text())
            self.assertIn("(1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2]))",
                          (reference / "quat.cpp").read_text())
            self.assertIn("Raw_Anim_Frame_Floor(frame);", (current / "hrawanim.cpp").read_text())

            for sanitize in (False, True):
                label = "asan" if sanitize else "plain"
                ref_stdout, ref_bytes = _build_and_run(directory, reference, "ref-" + label, sanitize)
                cur_stdout, cur_bytes = _build_and_run(directory, current, "cur-" + label, sanitize)
                self.assertIn("PASS samples=24000", ref_stdout)
                self.assertEqual(ref_stdout, cur_stdout)
                self.assertGreater(len(ref_bytes), 5_000_000)
                if ref_bytes != cur_bytes:
                    first = next(i for i, (x, y) in enumerate(zip(ref_bytes, cur_bytes)) if x != y)
                    self.fail(f"{label}: output differs at byte {first} of {len(ref_bytes)}")


if __name__ == "__main__":
    unittest.main()
