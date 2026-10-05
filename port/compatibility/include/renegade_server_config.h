#pragma once

#include "assets.h"
#include "ffactory.h"
#include "wwfile.h"
#include <stdio.h>
#include <string.h>

// Server settings override retail defaults, but writes belong only to user/.
inline bool Renegade_Server_Config_Path(const char *name, char (&path)[256])
{
	if (!name || !*name || strlen(name) > 240 || strpbrk(name, "/\\:") ||
		strcmp(name, ".") == 0 || strcmp(name, "..") == 0) {
		fprintf(stderr, "server-config: invalid logical filename\n");
		return false;
	}
	snprintf(path, sizeof(path), "user/%s", name);
	return true;
}

inline INIClass *Renegade_Load_Server_Config(const char *name)
{
	char path[256];
	if (!Renegade_Server_Config_Path(name, path)) return new INIClass;
	INIClass *ini = Get_INI(path);
	if (!ini) ini = Get_INI(name);
	// An absent optional config uses the original game-data defaults.
	if (!ini) ini = new INIClass;
	return ini;
}

inline bool Renegade_User_Server_Config_Is_Available(const char *name)
{
	char path[256];
	if (!Renegade_Server_Config_Path(name, path)) return false;
	FileClass *file = _TheFileFactory->Get_File(path);
	if (!file) return false;
	const bool available = file->Is_Available();
	_TheFileFactory->Return_File(file);
	return available;
}

inline bool Renegade_Server_Config_Is_Available(const char *name)
{
	if (Renegade_User_Server_Config_Is_Available(name)) return true;
	if (!name || !*name) return false;
	FileClass *file = _TheFileFactory->Get_File(name);
	if (!file) return false;
	const bool available = file->Is_Available();
	_TheFileFactory->Return_File(file);
	return available;
}

inline bool Renegade_Delete_User_Server_Config(const char *name)
{
	char path[256];
	if (!Renegade_Server_Config_Path(name, path)) return false;
	FileClass *file = _TheWritingFileFactory->Get_File(path);
	if (!file) return false;
	const bool deleted = file->Delete() != 0;
	_TheWritingFileFactory->Return_File(file);
	if (!deleted) fprintf(stderr, "server-config: delete failed: %s\n", path);
	return deleted;
}

inline bool &Renegade_Server_Config_Save_Status(void)
{
	static bool succeeded = true;
	return succeeded;
}

inline void Renegade_Reset_Server_Config_Save_Status(void)
{
	Renegade_Server_Config_Save_Status() = true;
}

inline bool Renegade_Last_Server_Config_Save_Succeeded(void)
{
	return Renegade_Server_Config_Save_Status();
}

inline bool Renegade_Save_Server_Config(INIClass *ini, const char *name)
{
	char path[256];
	if (!ini || !Renegade_Server_Config_Path(name, path)) {
		Renegade_Server_Config_Save_Status() = false;
		return false;
	}
	FileClass *file = _TheWritingFileFactory->Get_File(path);
	bool saved = false;
	if (file) {
		if (file->Open(FileClass::WRITE)) {
			saved = ini->Save(*file) > 0;
			file->Close();
			saved = saved && !file->Has_Write_Failed();
		}
		_TheWritingFileFactory->Return_File(file);
	}
	Renegade_Server_Config_Save_Status() =
		Renegade_Server_Config_Save_Status() && saved;
	if (!saved) fprintf(stderr, "server-config: write failed: %s\n", path);
	return saved;
}

inline unsigned long Renegade_Server_Config_Mod_Time(const char *name)
{
	char path[256];
	if (!Renegade_Server_Config_Path(name, path)) return 0;
	const char *candidates[] = {path, name};
	for (const char *candidate : candidates) {
		FileClass *file = _TheFileFactory->Get_File(candidate);
		if (!file) continue;
		const bool opened = file->Is_Available() && file->Open();
		const unsigned long stamp = opened ? file->Get_Date_Time() : 0;
		if (opened) file->Close();
		_TheFileFactory->Return_File(file);
		if (opened) return stamp;
	}
	return 0;
}
