import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class Dev82CurrentUploadHelperTests(unittest.TestCase):
    def test_helper_verifies_current_vpk_before_upload(self):
        script = (ROOT / "tools/upload_dev82_current_vpk.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("RenegadeVita-A3.5-dev82.vpk", script)
        self.assertIn("BUILD_STATE.json", script)
        self.assertIn("vpk_sha256", script)
        self.assertIn("VPK hash mismatch", script)
        self.assertIn("upload_vpk_ftp.sh", script)

    def test_helper_records_candidate_scoped_probe_evidence(self):
        script = (ROOT / "tools/upload_dev82_current_vpk.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("build/device-evidence/a35-dev82-upload-probe-", script)
        self.assertIn("upload-probe.txt", script)
        self.assertIn("closed_or_unreachable", script)
        self.assertIn("no reachable VitaShell FTP endpoint found", script)

    def test_helper_supports_known_ips_env_and_windows_arp_scan(self):
        script = (ROOT / "tools/upload_dev82_current_vpk.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("RENEGADE_VITA_IPS", script)
        self.assertIn("10.0.0.202 10.0.0.186", script)
        self.assertIn("RENEGADE_DEV82_UPLOAD_SCAN_ARP", script)
        self.assertIn("powershell.exe", script)
        self.assertIn("Get-NetNeighbor", script)

    def test_helper_does_not_install_launch_or_touch_usb(self):
        script = (ROOT / "tools/upload_dev82_current_vpk.sh").read_text(
            encoding="utf-8"
        )
        forbidden = ("package install", "app launch", "app kill", "usb")
        for token in forbidden:
            self.assertNotIn(token, script.lower())


if __name__ == "__main__":
    unittest.main()
