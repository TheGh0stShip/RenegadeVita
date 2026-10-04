"""Count provider locks while executing the production surface raster bodies."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SurfaceLockTests(unittest.TestCase):
    def test_pitch_failure_cleanup_and_padded_raster_operations(self):
        source = (ROOT / "port/renderer/vita/surface_boundary.cpp").read_text()
        helper = source[source.index("unsigned Bytes_Per_Pixel("):
                        source.index("SurfaceStore *Find_Store(")]
        raster = source[source.index("void SurfaceClass::Clear()"):
                        source.index("bool SurfaceClass::Is_Transparent_Column(")]
        formats = (ROOT / "upstream/CnC_Renegade/Code/ww3d2/ww3dformat.h").read_text()
        enum_start = formats.index("enum WW3DFormat {")
        enum_end = formats.index("};", enum_start) + 2
        with tempfile.TemporaryDirectory(prefix="renegade-surface-lock-") as folder:
            directory = Path(folder)
            (directory / "surface-format.inc").write_text(formats[enum_start:enum_end])
            (directory / "surface-raster-production.inc").write_text(helper + raster)
            output = directory / "surface-test"
            subprocess.run(["g++", "-std=c++17", "-O1", "-g", "-Wall", "-Wextra",
                            "-Werror", "-fsanitize=address,undefined",
                            "-fno-omit-frame-pointer", "-I" + folder,
                            str(ROOT / "tools/vita_surface_lock_test.cpp"),
                            "-o", str(output)], check=True)
            subprocess.run([str(output)], check=True, env=os.environ.copy())


if __name__ == "__main__":
    unittest.main()
