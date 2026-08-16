#pragma once

#include "wwbitpack_selftest.h"
#include "a21_filesystem_selftest.h"
#include "a22_w3d_selftest.h"

struct VitaBootstrapStatus
{
	bool user_tree_ready;
	bool retail_root_found;
	bool data_directory_found;
	bool always_dat_found;
	bool always2_dat_found;
	bool always_dbs_found;
	int directory_errors;
	int log_result;
};

VitaBootstrapStatus Vita_Initialize_Filesystem();
int Vita_Write_A22_Startup_Log(const VitaBootstrapStatus &status,
	const WestwoodSelfTestResult &self_test,
	const A21FilesystemSelfTestResult &filesystem,
	int framebuffer_result);
int Vita_Append_A22_Result_Log(const A22W3DSelfTestResult &w3d);

const char *Vita_Pass_Fail(bool value);
