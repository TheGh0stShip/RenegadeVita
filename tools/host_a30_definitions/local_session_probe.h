#pragma once

#include "a4_frontend_lifecycle_boundary.h"
#include "renegade_server_config.h"
#include "renegade_file_factory.h"
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>

inline int Validate_Local_Session_Boundaries()
{
	char archive[96];
	bool passed = true;
	for (const char *name : {"Skirmish00.mix", "skirmish00.MIX", "C&C_Field.mix"})
		passed = A4_Frontend_Resolve_Skirmish_Archive(name, archive, sizeof(archive)) && passed;
	for (const char *name : {"M13.mix", "C&C_../evil.mix", "Skirmish\\bad.mix",
		"Skirmish:bad.mix", "Skirmish00.mix\n", "C&C_Field.pkg", ""})
		passed = !A4_Frontend_Resolve_Skirmish_Archive(name, archive, sizeof(archive)) && passed;
	passed = !A4_Frontend_Resolve_Skirmish_Archive("Skirmish00.mix", archive, 3) && passed;

	char directory[] = "/tmp/renegade-server-config-XXXXXX";
	if (!mkdtemp(directory)) return 1;
	char user[256], retail[256];
	snprintf(user, sizeof(user), "%s/user", directory);
	snprintf(retail, sizeof(retail), "%s/retail", directory);
	if (mkdir(user, 0700) || mkdir(retail, 0700)) return 1;
	const RenegadePathRoots roots = {retail, user, user, user};
	RenegadeRootedFileFactoryClass factory(roots);
	FileFactoryClass *old_read = _TheFileFactory;
	FileFactoryClass *old_write = _TheWritingFileFactory;
	_TheFileFactory = _TheWritingFileFactory = &factory;
	INIClass *ini = Renegade_Load_Server_Config("svrcfg_probe.ini");
	passed = ini->Get_Int("Settings", "StartingCredits", 400) == 400 && passed;
	ini->Put_Int("Settings", "StartingCredits", 725);
	Renegade_Save_Server_Config(ini, "svrcfg_probe.ini");
	Release_INI(ini);
	ini = Renegade_Load_Server_Config("svrcfg_probe.ini");
	passed = ini->Get_Int("Settings", "StartingCredits", 0) == 725 && passed;
	Release_INI(ini);
	FileClass *retail_file = factory.Get_File("svrcfg_probe.ini");
	passed = !retail_file->Is_Available() && passed;
	factory.Return_File(retail_file);
	passed = Renegade_Server_Config_Mod_Time("svrcfg_probe.ini") != 0 && passed;
	char path[256];
	passed = !Renegade_Server_Config_Path("../svrcfg.ini", path) && passed;
	_TheFileFactory = old_read;
	_TheWritingFileFactory = old_write;
	snprintf(path, sizeof(path), "%s/user/svrcfg_probe.ini", directory);
	unlink(path);
	rmdir(user);
	rmdir(retail);
	rmdir(directory);
	printf("local_session.map_validation_and_user_config=%s\n", passed ? "PASS" : "FAIL");
	return passed ? 0 : 1;
}
