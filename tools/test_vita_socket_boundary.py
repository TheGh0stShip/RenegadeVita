"""Host descriptor model and source contracts; not native socket execution."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SocketBoundaryTests(unittest.TestCase):
    def test_native_branch_preserves_libc_descriptor_ownership(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = str(Path(directory) / "socket-test")
            subprocess.run(["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
                            "-I" + str(ROOT / "port/compatibility/include"),
                            str(ROOT / "tools/host_a35_winsock_descriptor_test.cpp"),
                            "-o", binary], check=True, timeout=30)
            subprocess.run([binary], check=True, timeout=5)

    def test_original_packet_manager_uses_portable_nonblocking_receive(self):
        source = (ROOT / "staging/wwnet/packetmgr.cpp").read_text()
        self.assertIn("#if defined(RENEGADE_VITA_PORT)\n\t\t// libc sockets", source)
        self.assertIn("MSG_DONTWAIT, (LPSOCKADDR) &addr, &address_size", source)
        self.assertIn("wwnet-a35-vita-libc-receive.patch",
                      (ROOT / "tools/stage_sources.sh").read_text())

    def test_native_remote_session_never_creates_local_player(self):
        source = (ROOT / "port/platform/vita/a31_vita_runtime.cpp").read_text()
        self.assertIn("remote_join.Begin_World_Load()", source)
        remote = source.split("if (remote_client) {\n\t\t\t\tif (!remote_join.Complete_World_Load", 1)[1]
        remote = remote.split("} else if (loading_checkpoint)", 1)[0]
        self.assertIn("cNetwork::Get_My_Player_Object()", remote)
        self.assertNotIn("cGod::Create_Player", remote)
        self.assertIn("if (!remote_client) cGod::Think();", source)
        self.assertIn("remote_network_initialized) The_Game()->On_Game_End();", source)


if __name__ == "__main__":
    unittest.main()
