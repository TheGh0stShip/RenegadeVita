import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DemoRecorderWorkflowTests(unittest.TestCase):
    def test_build_script_pins_external_recorder_and_does_not_touch_vita(self):
        script = (ROOT / "tools/build_renegade_demo_recorder_plugin.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("60c966a75356ea9a95f79479a3e647283586cf11", script)
        self.assertIn("Vita-MP4-Recorder.git", script)
        self.assertIn("psp2/mp4rec.h", script)
        self.assertIn("renegade_demo_recorder/include", script)
        self.assertIn("-include psp2/mp4rec.h", script)
        self.assertIn("libSceLibMp4Recorder_stub_weak.a", script)
        self.assertIn("vita-mp4-recorder-renegade-autostart.patch", script)
        self.assertIn("SceIofilemgrForDriver_stub", script)
        self.assertIn('rv_out_stem="RenegadeDemoRecorder-$rv_candidate_label"', script)
        self.assertIn('"$rv_out_stem.suprx"', script)
        self.assertIn('"$rv_out_stem.skprx"', script)
        self.assertIn("*RNEGA3101", script)
        self.assertIn("Manual install only", script)
        self.assertNotIn("upload_vpk_ftp", script)
        self.assertNotIn("curl -T", script)
        self.assertNotIn("fs push", script)
        self.assertNotIn("package install", script)

    def test_patch_is_title_scoped_autostart_and_null_framebuffer_safe(self):
        patch = (
            ROOT
            / "tools/vita_plugins/renegade_demo_recorder/vita-mp4-recorder-renegade-autostart.patch"
        ).read_text(encoding="utf-8")

        self.assertIn('#define RENEGADE_DEMO_TITLE_ID "RNEGA3101"', patch)
        self.assertIn("#define RENEGADE_DEMO_AUTO_START 1", patch)
        self.assertIn("static uint8_t has_audio = 1;", patch)
        self.assertIn("sceAppMgrAppParamGetString(0, 12, titleid, sizeof(titleid));", patch)
        self.assertIn('strcmp(titleid, RENEGADE_DEMO_TITLE_ID) != 0', patch)
        self.assertIn("if (!pParam || !pParam->base", patch)
        self.assertIn("return TAI_CONTINUE(int, ref[0], pParam, sync);", patch)
        self.assertNotIn("is_recording && (ctrl->buttons & SCE_CTRL_START)", patch)
        self.assertIn("alterRecordingState();", patch)
        self.assertIn("sceMp4RecTerm(&r, &params);", patch)
        self.assertIn("params.discard = 0;", patch)

    def test_recorded_session_runner_is_launch_wait_and_log_pull_only(self):
        script = (ROOT / "tools/run_dev82_recorded_demo_session.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("app launch", script)
        self.assertIn("app wait", script)
        self.assertIn("--exit-or-crash", script)
        self.assertIn("logs --vdb1 pull", script)
        self.assertIn("a35-dev86-runtime.log", script)
        self.assertIn("video_output=ux0:video", script)
        self.assertNotIn("fs push", script)
        self.assertNotIn("package install", script)
        self.assertNotIn("ux0:/data/renegade/retail", script)

    def test_documentation_rejects_usb_default_and_records_known_limits(self):
        doc = (ROOT / "docs/DEMO_CAPTURE.md").read_text(encoding="utf-8")

        self.assertIn("USB capture is not the default", doc)
        self.assertIn("PSTV", doc)
        self.assertIn("ux0:video", doc)
        self.assertIn("VitaShell FTP", doc)
        self.assertNotIn("USB/FTP", doc)
        self.assertIn("starts recording when the Renegade process loads", doc)
        self.assertIn("finalize the MP4", doc)
        self.assertIn("use L+Start to finalize the MP4", doc)
        self.assertIn("Plain Start\nremains available to Renegade", doc)
        self.assertIn("not physical acceptance", doc)
        self.assertIn("audio availability/desync", doc)
        self.assertIn("30 FPS slowdown", doc)
        self.assertIn("https://github.com/Rinnegatamante/Vita-MP4-Recorder", doc)

    def test_local_mp4rec_compat_header_is_narrow_and_not_app_runtime(self):
        header = (
            ROOT
            / "tools/vita_plugins/renegade_demo_recorder/include/psp2/mp4rec.h"
        ).read_text(encoding="utf-8")

        self.assertIn("SCE_MP4REC_AUDIO_BUFFER_SIZE 4096", header)
        self.assertIn("SCE_MP4REC_PIXELFORMAT_A8B8G8R8 = 0x00000000", header)
        self.assertIn("SCE_MP4REC_PIXELFORMAT_YUV420_PACKED = 0x00000020", header)
        self.assertIn("SceMp4RecRecorder", header)
        self.assertIn("SceMp4RecInitParam", header)
        self.assertIn("SceMp4RecFrame", header)
        self.assertIn("SceMp4RecTermParam", header)
        self.assertIn("sceMp4RecCreateRecorder", header)
        self.assertIn("sceMp4RecAddVideoSample", header)
        self.assertIn("sceMp4RecAddAudioSample", header)
        self.assertNotIn("RNEGA3101", header)


if __name__ == "__main__":
    unittest.main()
