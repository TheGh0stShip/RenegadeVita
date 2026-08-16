#include "a21_filesystem_selftest.h"

#include "renegade_file_factory.h"

#include "ffactorylist.h"
#include "mixfile.h"
#include "wwfile.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

namespace {

const char *const kArchiveLogicalPath = "Data\\Always.dat";
const char *const kKnownEntry = "dsp_o2tank.w3d";

void Check(A21FilesystemSelfTestResult &result, bool condition, const char *name)
{
	++result.checks;
	if (condition) {
		return;
	}
	++result.failures;
	if (result.first_failure[0] == 0) {
		strncpy(result.first_failure, name, sizeof(result.first_failure) - 1);
		result.first_failure[sizeof(result.first_failure) - 1] = 0;
	}
}

bool Read_Entry(FileClass *file, A21FilesystemSelfTestResult &result)
{
	if (file == NULL || !file->Is_Available() || !file->Open(FileClass::READ)) {
		return false;
	}
	result.known_entry_size = (unsigned)file->Size();
	uint8_t prefix[32] = {};
	const int bytes_read = file->Read(prefix, sizeof(prefix));
	result.known_entry_bytes_read = bytes_read > 0 ? (unsigned)bytes_read : 0;
	if (bytes_read >= 4) {
		result.known_entry_prefix = (unsigned)prefix[0] |
			((unsigned)prefix[1] << 8) | ((unsigned)prefix[2] << 16) |
			((unsigned)prefix[3] << 24);
	}
	file->Close();
	return result.known_entry_size > 0 && bytes_read > 0;
}

} // namespace

A21FilesystemSelfTestResult Run_A21_Filesystem_Self_Test(
	const RenegadePathRoots &roots)
{
	A21FilesystemSelfTestResult result = {};

	const RenegadeResolvedPath archive_path =
		Renegade_Resolve_Path(roots, "data\\ALWAYS.DAT", RENEGADE_PATH_READ);
	result.path_translation = archive_path.success && archive_path.existing_case_matched &&
		strstr(archive_path.physical, "/Data/always.dat") != NULL;
	if (archive_path.success) {
		snprintf(result.resolved_archive_path, sizeof(result.resolved_archive_path),
			"%s", archive_path.physical);
	}
	Check(result, result.path_translation, "case-aware retail path translation");

	const RenegadeResolvedPath traversal =
		Renegade_Resolve_Path(roots, "Data/../user/logs", RENEGADE_PATH_READ);
	result.traversal_rejected = !traversal.success;
	Check(result, result.traversal_rejected, "path traversal rejection");

	const RenegadeResolvedPath write_path =
		Renegade_Resolve_Path(roots, "logs/a21-probe.log", RENEGADE_PATH_WRITE);
	result.write_routed_outside_retail = write_path.success && write_path.writable_namespace &&
		strncmp(write_path.physical, roots.user, strlen(roots.user)) == 0 &&
		strncmp(write_path.physical, roots.retail, strlen(roots.retail)) != 0;
	Check(result, result.write_routed_outside_retail, "write routing outside retail");

	RenegadeRootedFileFactoryClass root_factory(roots);
	FileClass *raw_archive = root_factory.Get_File(kArchiveLogicalPath);
	result.original_file_available = raw_archive != NULL && raw_archive->Is_Available();
	Check(result, result.original_file_available, "original FileClass availability");
	char signature[4] = {};
	if (result.original_file_available && raw_archive->Open(FileClass::READ)) {
		result.original_file_read =
			raw_archive->Read(signature, sizeof(signature)) == (int)sizeof(signature) &&
			memcmp(signature, "MIX1", sizeof(signature)) == 0;
		raw_archive->Close();
	}
	root_factory.Return_File(raw_archive);
	Check(result, result.original_file_read, "original FileClass MIX1 read");

	MixFileFactoryClass mix_factory(kArchiveLogicalPath, &root_factory);
	result.archive_valid = mix_factory.Is_Valid();
	Check(result, result.archive_valid, "original MixFileFactory archive recognition");

	DynamicVectorClass<StringClass> names;
	result.archive_enumerated = mix_factory.Build_Filename_List(names);
	result.archive_entries = names.Count() > 0 ? (unsigned)names.Count() : 0;
	result.archive_enumerated = result.archive_enumerated && result.archive_entries == 15161;
	Check(result, result.archive_enumerated,
		"original MIX filename enumeration");
	for (int index = 0; index < names.Count(); ++index) {
		if (names[index].Compare_No_Case(kKnownEntry) == 0) {
			result.known_entry_found = true;
			break;
		}
	}
	Check(result, result.known_entry_found, "known MIX entry enumeration");

	FileClass *entry = mix_factory.Get_File(kKnownEntry);
	result.known_entry_read = Read_Entry(entry, result);
	mix_factory.Return_File(entry);
	result.known_entry_read = result.known_entry_read &&
		result.known_entry_size > 0 && result.known_entry_size < 16U * 1024U * 1024U &&
		result.known_entry_prefix != 0x3158494DU;
	Check(result, result.known_entry_read, "known biased MIX entry read");

	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&mix_factory, "always.dat");
	factory_list.Add_FileFactory(&root_factory, "retail");
	FileClass *listed_entry = factory_list.Get_File(kKnownEntry);
	result.factory_list_read = Read_Entry(listed_entry, result);
	if (listed_entry != NULL) {
		factory_list.Return_File(listed_entry);
	}
	Check(result, result.factory_list_read, "original FileFactoryList archive read");

	result.passed = result.failures == 0;
	if (result.passed) {
		strcpy(result.first_failure, "none");
	}
	return result;
}
