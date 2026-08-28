/*
 * Device-specific lock-screen compatibility helper.
 *
 * The probe mode records the exact SceShell fingerprint and instruction
 * windows without patching. The normal build accepts only the matching retail
 * 3.65 module and the two exact physical-device byte windows before applying
 * either bounded injection. Partial or unverifiable application is rolled
 * back. The offsets are public compatibility facts from TheOfficialFloW's
 * GPL-3.0 VitaTweaks/NoLockScreen project; no upstream implementation code is
 * copied here.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <psp2/io/fcntl.h>
#include <psp2/kernel/clib.h>
#include <psp2/kernel/modulemgr.h>
#include <psp2/types.h>
#include <taihen.h>

#include <stdint.h>

#if defined(RNV_NOLOCK_PROBE_ONLY)
#define STATUS_LOG_PATH "ur0:tai/renegade-nolockscreen-probe.log"
#else
#define STATUS_LOG_PATH "ur0:tai/renegade-nolockscreen.log"
#endif
#define SCESHELL_365_RETAIL_NID 0x5549BF1FU
#define LOCKSCREEN_RESUME_OFFSET 0x23556EU
#define LOCKSCREEN_BOOT_OFFSET 0x23626EU
#define WINDOW_BYTES 12U
#define FINGERPRINT_BYTES 8U

static SceUID g_injections[2] = {-1, -1};
static const uint8_t kResumeExpected[FINGERPRINT_BYTES] = {
	0x26, 0xF2, 0xC4, 0xEA, 0x01, 0x28, 0x17, 0xD0
};
static const uint8_t kBootExpected[FINGERPRINT_BYTES] = {
	0x25, 0xF2, 0x44, 0xEC, 0x01, 0x28, 0x09, 0xD1
};
static const uint8_t kBypassOpcode[4] = {0x01, 0x20, 0x00, 0xBF};

static SceSize line_length(const char *line)
{
	SceSize length = 0;
	while (line[length] != '\0' && length < 255U) {
		++length;
	}
	return length;
}

static int append_line(const char *line)
{
	SceUID file = sceIoOpen(STATUS_LOG_PATH,
		SCE_O_WRONLY | SCE_O_CREAT | SCE_O_APPEND, 0666);
	if (file < 0) {
		return file;
	}

	const SceSize length = line_length(line);
	const int write_result = sceIoWrite(file, line, length);
	int result = write_result == (int)length ? 0 :
		(write_result < 0 ? write_result : -1);
	const int sync_result = sceIoSyncByFd(file, 0);
	if (result >= 0 && sync_result < 0) {
		result = sync_result;
	}
	const int close_result = sceIoClose(file);
	if (result >= 0 && close_result < 0) {
		result = close_result;
	}
	return result;
}

static int bytes_match(const uint8_t *text, SceSize text_size,
	uint32_t offset, const uint8_t *expected, SceSize expected_size)
{
	if (offset > text_size || expected_size > text_size - offset) {
		return 0;
	}
	for (SceSize index = 0; index < expected_size; ++index) {
		if (text[offset + index] != expected[index]) {
			return 0;
		}
	}
	return 1;
}

static void release_injections(void)
{
	if (g_injections[1] >= 0) {
		taiInjectRelease(g_injections[1]);
		g_injections[1] = -1;
	}
	if (g_injections[0] >= 0) {
		taiInjectRelease(g_injections[0]);
		g_injections[0] = -1;
	}
}

static void append_window(const char *label, const uint8_t *text,
	SceSize text_size, uint32_t offset)
{
	char line[256];
	if (offset > text_size || WINDOW_BYTES > text_size - offset) {
		sceClibSnprintf(line, sizeof(line),
			"site=%s offset=%08X status=OUT_OF_BOUNDS text_size=%08X\n",
			label, (unsigned)offset, (unsigned)text_size);
		append_line(line);
		return;
	}

	const uint8_t *site = text + offset;
	sceClibSnprintf(line, sizeof(line),
		"site=%s offset=%08X status=OBSERVED bytes=%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X%02X\n",
		label, (unsigned)offset,
		site[0], site[1], site[2], site[3], site[4], site[5],
		site[6], site[7], site[8], site[9], site[10], site[11]);
	append_line(line);
}

int module_start(SceSize args, void *argp);
int _start(SceSize args, void *argp)
	__attribute__((weak, alias("module_start")));

int module_start(SceSize args, void *argp)
{
	(void)args;
	(void)argp;
#if defined(RNV_NOLOCK_PROBE_ONLY)
	append_line("renegade_nolockscreen schema=2 mode=READ_ONLY_PROBE\n");
#else
	append_line("renegade_nolockscreen schema=2 mode=VALIDATED_PATCH\n");
#endif

	SceKernelSystemSwVersion firmware = {0};
	firmware.size = sizeof(firmware);
	const int firmware_result = sceKernelGetSystemSwVersion(&firmware);

	tai_module_info_t tai_info = {0};
	tai_info.size = sizeof(tai_info);
	const int tai_result = taiGetModuleInfo("SceShell", &tai_info);

	char line[256];
	sceClibSnprintf(line, sizeof(line),
		"firmware_rc=%08X firmware=%08X version=%.27s tai_rc=%08X module_nid=%08X modid=%08X\n",
		(unsigned)firmware_result, (unsigned)firmware.version,
		firmware.versionString, (unsigned)tai_result,
		(unsigned)tai_info.module_nid, (unsigned)tai_info.modid);
	append_line(line);
	if (tai_result < 0) {
		append_line("probe_status=REFUSED reason=SCESHELL_NOT_FOUND\n");
		return SCE_KERNEL_START_SUCCESS;
	}

	SceKernelModuleInfo kernel_info = {0};
	kernel_info.size = sizeof(kernel_info);
	const int module_result = sceKernelGetModuleInfo(tai_info.modid,
		&kernel_info);
	sceClibSnprintf(line, sizeof(line),
		"module_info_rc=%08X text_base=%08X text_size=%08X text_filesz=%08X\n",
		(unsigned)module_result,
		module_result >= 0 ? (unsigned)(uintptr_t)kernel_info.segments[0].vaddr : 0U,
		module_result >= 0 ? (unsigned)kernel_info.segments[0].memsz : 0U,
		module_result >= 0 ? (unsigned)kernel_info.segments[0].filesz : 0U);
	append_line(line);
	if (module_result < 0) {
		append_line("probe_status=REFUSED reason=MODULE_INFO_FAILED\n");
		return SCE_KERNEL_START_SUCCESS;
	}
	if (tai_info.module_nid != SCESHELL_365_RETAIL_NID) {
		append_line("probe_status=REFUSED reason=UNSUPPORTED_SCESHELL_NID\n");
		return SCE_KERNEL_START_SUCCESS;
	}

	const uint8_t *text = (const uint8_t *)kernel_info.segments[0].vaddr;
	append_window("resume", text, kernel_info.segments[0].filesz,
		LOCKSCREEN_RESUME_OFFSET);
	append_window("boot", text, kernel_info.segments[0].filesz,
		LOCKSCREEN_BOOT_OFFSET);
	if (!bytes_match(text, kernel_info.segments[0].filesz,
			LOCKSCREEN_RESUME_OFFSET, kResumeExpected, FINGERPRINT_BYTES) ||
		!bytes_match(text, kernel_info.segments[0].filesz,
			LOCKSCREEN_BOOT_OFFSET, kBootExpected, FINGERPRINT_BYTES)) {
		append_line("patch_status=REFUSED reason=INSTRUCTION_FINGERPRINT_MISMATCH patches_applied=0\n");
		return SCE_KERNEL_START_SUCCESS;
	}

#if defined(RNV_NOLOCK_PROBE_ONLY)
	append_line("probe_status=COMPLETE patches_applied=0\n");
	return SCE_KERNEL_START_SUCCESS;
#else
	g_injections[0] = taiInjectData(tai_info.modid, 0,
		LOCKSCREEN_RESUME_OFFSET, kBypassOpcode, sizeof(kBypassOpcode));
	if (g_injections[0] < 0) {
		sceClibSnprintf(line, sizeof(line),
			"patch_status=REFUSED reason=RESUME_INJECTION_FAILED rc=%08X patches_applied=0\n",
			(unsigned)g_injections[0]);
		append_line(line);
		g_injections[0] = -1;
		return SCE_KERNEL_START_SUCCESS;
	}

	g_injections[1] = taiInjectData(tai_info.modid, 0,
		LOCKSCREEN_BOOT_OFFSET, kBypassOpcode, sizeof(kBypassOpcode));
	if (g_injections[1] < 0) {
		const SceUID failure = g_injections[1];
		g_injections[1] = -1;
		release_injections();
		sceClibSnprintf(line, sizeof(line),
			"patch_status=ROLLED_BACK reason=BOOT_INJECTION_FAILED rc=%08X patches_applied=0\n",
			(unsigned)failure);
		append_line(line);
		return SCE_KERNEL_START_SUCCESS;
	}

	if (!bytes_match(text, kernel_info.segments[0].filesz,
			LOCKSCREEN_RESUME_OFFSET, kBypassOpcode, sizeof(kBypassOpcode)) ||
		!bytes_match(text, kernel_info.segments[0].filesz,
			LOCKSCREEN_BOOT_OFFSET, kBypassOpcode, sizeof(kBypassOpcode))) {
		release_injections();
		append_line("patch_status=ROLLED_BACK reason=POST_INJECTION_VERIFICATION_FAILED patches_applied=0\n");
		return SCE_KERNEL_START_SUCCESS;
	}

	sceClibSnprintf(line, sizeof(line),
		"patch_status=APPLIED resume_injection=%08X boot_injection=%08X patches_applied=2\n",
		(unsigned)g_injections[0], (unsigned)g_injections[1]);
	append_line(line);
#endif
	return SCE_KERNEL_START_SUCCESS;
}

int module_stop(SceSize args, void *argp)
{
	(void)args;
	(void)argp;
	release_injections();
	return SCE_KERNEL_STOP_SUCCESS;
}
