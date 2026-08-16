#include "vita_platform.h"
#include "wwbitpack_selftest.h"
#include "a22_w3d_selftest.h"

#include <psp2/ctrl.h>
#include <psp2/kernel/processmgr.h>
#include <psp2/kernel/threadmgr.h>

#include <debugScreen.h>

namespace {

void Print_Status(const VitaBootstrapStatus &status,
	const WestwoodSelfTestResult &self_test,
	const A21FilesystemSelfTestResult &filesystem, int screen_result)
{
	psvDebugScreenClear(0x102030);
	psvDebugScreenSetFgColor(0xFFFFFF);
	psvDebugScreenPrintf("Renegade Vita A2.2 - Original Visible Runtime\n\n");

	psvDebugScreenPrintf("A2.0 REGRESSION\n");
	psvDebugScreenPrintf("Framebuffer:               %s (%08X)\n",
		Vita_Pass_Fail(screen_result >= 0), static_cast<unsigned>(screen_result));
	psvDebugScreenPrintf("Westwood/wwbitpack:        %s (%u checks)\n",
		Vita_Pass_Fail(self_test.passed), self_test.checks);
	psvDebugScreenPrintf("Retail root/Data:          %s/%s\n",
		Vita_Pass_Fail(status.retail_root_found), Vita_Pass_Fail(status.data_directory_found));
	psvDebugScreenPrintf("always/Always2/always.dbs: %s/%s/%s\n",
		Vita_Pass_Fail(status.always_dat_found), Vita_Pass_Fail(status.always2_dat_found),
		Vita_Pass_Fail(status.always_dbs_found));
	psvDebugScreenPrintf("Writable user tree:        %s\n\n", Vita_Pass_Fail(status.user_tree_ready));

	psvDebugScreenPrintf("A2.1 ORIGINAL WESTWOOD I/O\n");
	psvDebugScreenPrintf("Path translation:          %s\n", Vita_Pass_Fail(filesystem.path_translation));
	psvDebugScreenPrintf("FileClass read:             %s\n", Vita_Pass_Fail(filesystem.original_file_read));
	psvDebugScreenPrintf("MixFileFactory archive:     %s\n", Vita_Pass_Fail(filesystem.archive_valid));
	psvDebugScreenPrintf("Archive enumeration:        %s (%u entries)\n",
		Vita_Pass_Fail(filesystem.archive_enumerated), filesystem.archive_entries);
	psvDebugScreenPrintf("dsp_o2tank.w3d lookup/read: %s/%s\n",
		Vita_Pass_Fail(filesystem.known_entry_found), Vita_Pass_Fail(filesystem.known_entry_read));
	psvDebugScreenPrintf("Entry size/read/prefix:     %u/%u/%08X\n",
		filesystem.known_entry_size, filesystem.known_entry_bytes_read,
		filesystem.known_entry_prefix);
	psvDebugScreenPrintf("FileFactoryList read:       %s\n\n",
		Vita_Pass_Fail(filesystem.factory_list_read));
	psvDebugScreenPrintf("A2.2 startup log:           %s (%08X)\n",
		Vita_Pass_Fail(status.log_result >= 0), static_cast<unsigned>(status.log_result));
	psvDebugScreenPrintf("Original/port TUs:          %d/%d\n",
		RENEGADE_VITA_A22_ORIGINAL_SOURCES, RENEGADE_VITA_A22_PORT_SOURCES);
	psvDebugScreenPrintf("Log: ux0:data/renegade/user/logs/a22-runtime.log\n\n");
	psvDebugScreenSetFgColor(0x80FF80);
	psvDebugScreenPrintf("Starting original DSP_O2TANK scene...\n");
	psvDebugScreenPrintf("Right stick = orbit, left stick Y = zoom\n");
	psvDebugScreenPrintf("START = clean exit\n");
}

float Analog_Axis(unsigned char value)
{
	const int offset = static_cast<int>(value) - 128;
	if (offset > -18 && offset < 18) {
		return 0.0f;
	}
	return static_cast<float>(offset) / (offset < 0 ? 128.0f : 127.0f);
}

bool Update_Camera(void *, A22CameraControlState &camera)
{
	SceCtrlData controller = {};
	if (sceCtrlPeekBufferPositive(0, &controller, 1) > 0) {
		if ((controller.buttons & SCE_CTRL_START) != 0) {
			return false;
		}

		float yaw_input = Analog_Axis(controller.rx);
		float pitch_input = Analog_Axis(controller.ry);
		float distance_input = Analog_Axis(controller.ly);
		if ((controller.buttons & SCE_CTRL_LEFT) != 0) {
			yaw_input -= 1.0f;
		}
		if ((controller.buttons & SCE_CTRL_RIGHT) != 0) {
			yaw_input += 1.0f;
		}
		if ((controller.buttons & SCE_CTRL_UP) != 0) {
			pitch_input -= 1.0f;
		}
		if ((controller.buttons & SCE_CTRL_DOWN) != 0) {
			pitch_input += 1.0f;
		}

		camera.yaw += yaw_input * 0.035f;
		camera.pitch -= pitch_input * 0.025f;
		camera.distance += distance_input * 0.045f;
		if (camera.yaw > 3.14159265f) {
			camera.yaw -= 6.28318531f;
		} else if (camera.yaw < -3.14159265f) {
			camera.yaw += 6.28318531f;
		}
		if (camera.pitch > 1.2f) {
			camera.pitch = 1.2f;
		} else if (camera.pitch < -1.2f) {
			camera.pitch = -1.2f;
		}
		if (camera.distance < 2.0f) {
			camera.distance = 2.0f;
		} else if (camera.distance > 8.0f) {
			camera.distance = 8.0f;
		}
	}

	sceKernelDelayThread(16 * 1000);
	return true;
}

} // namespace

int main()
{
	const int screen_result = psvDebugScreenInit();
	if (screen_result >= 0) {
		psvDebugScreenPrintf("Renegade Vita A2.2\nRunning original Westwood regressions...\n");
	}
	const WestwoodSelfTestResult self_test = Run_Westwood_Bitpack_Self_Test();
	VitaBootstrapStatus status = Vita_Initialize_Filesystem();
	const RenegadePathRoots roots = {
		"ux0:data/renegade/retail",
		"ux0:data/renegade/user",
		"ux0:data/renegade/cache",
		"ux0:data/renegade/mods"
	};
	const A21FilesystemSelfTestResult filesystem = Run_A21_Filesystem_Self_Test(roots);
	status.log_result = Vita_Write_A22_Startup_Log(status, self_test, filesystem, screen_result);
	if (screen_result >= 0) {
		Print_Status(status, self_test, filesystem, screen_result);
		sceKernelDelayThread(1200 * 1000);
		psvDebugScreenFinish();
	}

	sceCtrlSetSamplingMode(SCE_CTRL_MODE_ANALOG);
	const A22W3DRenderOptions render_options = {
		true,
		0,
		Update_Camera,
		NULL
	};
	const A22W3DSelfTestResult w3d = Run_A22_W3D_Self_Test(roots, &render_options);
	Vita_Append_A22_Result_Log(w3d);

	sceKernelExitProcess(0);
	return 0;
}
