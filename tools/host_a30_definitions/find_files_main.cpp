#include "renegade_find_files.h"
#include "win.h"

#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include <initializer_list>

namespace {

void Check(bool condition, const char *name, unsigned &checks, unsigned &failures)
{
	++checks;
	if (!condition) {
		++failures;
		fprintf(stderr, "find-files check failed: %s\n", name);
	}
}

bool Write_File(const char *path)
{
	FILE *file = fopen(path, "wb");
	if (file == NULL) return false;
	const bool wrote = fputs("fixture", file) >= 0;
	return fclose(file) == 0 && wrote;
}

} // namespace

int main()
{
	unsigned checks = 0U;
	unsigned failures = 0U;
	char root[] = "/tmp/renegade-find-files-XXXXXX";
	Check(mkdtemp(root) != NULL, "temporary retail root", checks, failures);
	char data[512];
	strcpy(data, root);
	strcat(data, "/Data");
	Check(mkdir(data, 0700) == 0, "Data directory", checks, failures);
	char skirmish[512];
	char city[512];
	char ignored[512];
	strcpy(skirmish, data);
	strcat(skirmish, "/SKIRMISH01.MIX");
	strcpy(city, data);
	strcat(city, "/C&C_City.mix");
	strcpy(ignored, data);
	strcat(ignored, "/readme.txt");
	Check(Write_File(skirmish) && Write_File(city) && Write_File(ignored),
		"fixture files", checks, failures);

	const RenegadePathRoots roots = {root, root, root, root};
	Renegade_Set_Find_Roots(roots);
	uint64_t available = 0;
	Check(Renegade_Get_User_Free_Space(available) && available > 0,
		"save volume reports actual free bytes", checks, failures);
	Renegade_Set_Find_Roots({root, "/path/that/does/not/exist", root, root});
	available = UINT64_MAX;
	Check(!Renegade_Get_User_Free_Space(available) && available == 0,
		"missing save volume fails closed", checks, failures);
	Renegade_Set_Find_Roots(roots);
	WIN32_FIND_DATA entry = {};
	HANDLE handle = FindFirstFile("data\\skirmish*.mix", &entry);
	Check(handle != INVALID_HANDLE_VALUE && strcmp(entry.cFileName, "SKIRMISH01.MIX") == 0,
		"case-insensitive skirmish enumeration", checks, failures);
	SYSTEMTIME stamp = {};
	Check(FileTimeToSystemTime(&entry.ftLastWriteTime, &stamp) != 0 && stamp.wYear >= 2020,
		"enumerated modification timestamp", checks, failures);
	Check(FindNextFile(handle, &entry) == 0, "single matched file end", checks, failures);
	Check(FindClose(handle) != 0, "close enumeration", checks, failures);
	handle = FindFirstFile("DATA\\c&c_????.MIX", &entry);
	Check(handle != INVALID_HANDLE_VALUE && strcmp(entry.cFileName, "C&C_City.mix") == 0,
		"question-mark and case-fold enumeration", checks, failures);
	Check(FindClose(handle) != 0, "close question-mark enumeration", checks, failures);
	Check(FindFirstFile("Data\\none*.mix", &entry) == INVALID_HANDLE_VALUE,
		"no-match rejection", checks, failures);
	Check(FindFirstFile("Data\\..\\*.mix", &entry) == INVALID_HANDLE_VALUE,
		"traversal rejection", checks, failures);
	char save_dir[512], save_file[512];
	snprintf(save_dir, sizeof(save_dir), "%s/save", root);
	snprintf(save_file, sizeof(save_file), "%s/save/SLOT01.SAV", root);
	Check(mkdir(save_dir, 0700) == 0 && Write_File(save_file),
		"original save fixture", checks, failures);
	handle = FindFirstFile("data\\save\\*.sav", &entry);
	Check(handle != INVALID_HANDLE_VALUE && strcmp(entry.cFileName, "SLOT01.SAV") == 0,
		"original save menu enumeration resolves user volume", checks, failures);
	Check(FindClose(handle) != 0, "close save enumeration", checks, failures);
	for (const char *name : {"slot01.sav", "save/slot01.sav", "Data\\Save\\slot01.sav"}) {
		const RenegadeResolvedPath resolved = Renegade_Resolve_Path(roots, name, RENEGADE_PATH_READ);
		Check(resolved.success && resolved.writable_namespace && strcmp(resolved.physical, save_file) == 0,
			"original save description and reload resolve the same user file", checks, failures);
	}
	Check(!Renegade_Delete_User_Save("data/SKIRMISH01.MIX"),
		"save deletion cannot remove retail content", checks, failures);
	Check(!Renegade_Delete_User_Save("save/../Data/SKIRMISH01.MIX"),
		"save deletion rejects traversal", checks, failures);
	Check(Renegade_Delete_User_Save("Data\\Save\\slot01.sav") && access(save_file, F_OK) != 0,
		"original save deletion uses the enumerated user file", checks, failures);
	rmdir(save_dir);

	remove(skirmish);
	remove(city);
	remove(ignored);
	rmdir(data);
	rmdir(root);
	printf("A4 find-files contract: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}
