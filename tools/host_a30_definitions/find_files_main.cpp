#include "renegade_find_files.h"
#include "win.h"

#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

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

	remove(skirmish);
	remove(city);
	remove(ignored);
	rmdir(data);
	rmdir(root);
	printf("A4 find-files contract: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}
