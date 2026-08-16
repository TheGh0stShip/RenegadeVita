#include "a30_world_selftest.h"

#include "renegade_file_factory.h"

#include "chunkio.h"
#include "ffactorylist.h"
#include "mixfile.h"
#include "wwfile.h"
#include "wwstring.h"

#include <stdio.h>
#include <string.h>

namespace {

const char *const kM00Archive = "Data\\M00_Tutorial.mix";
const char *const kAlwaysDbsArchive = "Data\\always.dbs";
const char *const kObjectsDdb = "Objects.DDB";
const char *const kLevelLdd = "m00_tutorial.ldd";
const char *const kLevelLsd = "M00_Tutorial.lsd";
const char *const kLevelDep = "m00_tutorial.dep";

const uint32_t kExpectedM00EntryCount = 84U;
const uint32_t kExpectedObjectsDdbSize = 5157396U;
const uint32_t kExpectedLddSize = 148616U;
const uint32_t kExpectedLsdSize = 526835U;
const uint32_t kExpectedDepSize = 4619U;

/* Values and load shape used by original Combat/savegame.cpp. */
const uint32_t kChunkIdLevelInfo = 1011991648U;
const uint32_t kChunkIdLevelData = 1011991649U;
const uint32_t kMicroChunkIdMapFilename = 1U;

struct FileProbe
{
	bool available;
	bool opened;
	uint32_t size;
};

void Check(A30WorldSelfTestResult &result, bool condition, const char *name)
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

FileProbe Probe_Read_Only_File(FileFactoryClass &factory, const char *name)
{
	FileProbe probe = {};
	FileClass *file = factory.Get_File(name);
	if (file != NULL) {
		probe.available = file->Is_Available();
		if (probe.available && file->Open(FileClass::READ)) {
			probe.opened = true;
			const int size = file->Size();
			probe.size = size > 0 ? (uint32_t)size : 0U;
			file->Close();
		}
		factory.Return_File(file);
	}
	return probe;
}

bool Filename_List_Contains(const DynamicVectorClass<StringClass> &names,
	const char *wanted)
{
	for (int index = 0; index < names.Count(); ++index) {
		if (names[index].Compare_No_Case(wanted) == 0) {
			return true;
		}
	}
	return false;
}

bool Inspect_Level_Ldd(FileFactoryClass &factory,
	A30WorldPreflightFingerprint &fingerprint)
{
	FileClass *file = factory.Get_File(kLevelLdd);
	if (file == NULL || !file->Is_Available() || !file->Open(FileClass::READ)) {
		if (file != NULL) {
			factory.Return_File(file);
		}
		return false;
	}

	bool traversal_ok = true;
	ChunkLoadClass loader(file);
	while (loader.Open_Chunk()) {
		const uint32_t chunk_id = loader.Cur_Chunk_ID();
		const uint32_t chunk_length = loader.Cur_Chunk_Length();
		const uint32_t chunk_index = fingerprint.ldd_top_level_chunk_count++;
		if (chunk_index < 4U) {
			fingerprint.ldd_top_level_ids[chunk_index] = chunk_id;
			fingerprint.ldd_top_level_lengths[chunk_index] = chunk_length;
		}

		if (chunk_id == kChunkIdLevelInfo) {
			fingerprint.level_info_chunk_found = true;
			while (loader.Open_Micro_Chunk()) {
				if (loader.Cur_Micro_Chunk_ID() == kMicroChunkIdMapFilename) {
					StringClass map_filename(0, true);
					const uint32_t length = loader.Cur_Micro_Chunk_Length();
					const uint32_t bytes_read = loader.Read(
						map_filename.Get_Buffer((int)length), length);
					fingerprint.map_filename_read = bytes_read == length;
					if (fingerprint.map_filename_read) {
						snprintf(fingerprint.map_filename,
							sizeof(fingerprint.map_filename), "%s",
							(const char *)map_filename);
						fingerprint.map_filename_exact =
							map_filename.Compare_No_Case(kLevelLsd) == 0;
					}
				}
				if (!loader.Close_Micro_Chunk()) {
					traversal_ok = false;
					break;
				}
			}
		} else if (chunk_id == kChunkIdLevelData) {
			fingerprint.level_data_chunk_found = true;
		}

		if (!loader.Close_Chunk()) {
			traversal_ok = false;
			break;
		}
	}

	file->Close();
	factory.Return_File(file);
	return traversal_ok && fingerprint.ldd_top_level_chunk_count > 0U;
}

} // namespace

A30WorldSelfTestResult Run_A30_World_Self_Test(
	const RenegadePathRoots &roots)
{
	A30WorldSelfTestResult result = {};
	A30WorldPreflightFingerprint &preflight = result.preflight;

	RenegadeRootedFileFactoryClass root_factory(roots);
	const FileProbe raw_m00 = Probe_Read_Only_File(root_factory, kM00Archive);
	preflight.m00_archive_file_available = raw_m00.available;
	preflight.m00_archive_file_opened = raw_m00.opened;
	preflight.m00_archive_size = raw_m00.size;
	Check(result,
		preflight.m00_archive_file_available && preflight.m00_archive_file_opened,
		"original FileClass opens M00_Tutorial.mix");

	MixFileFactoryClass m00_factory(kM00Archive, &root_factory);
	preflight.m00_mix_valid = m00_factory.Is_Valid();
	Check(result, preflight.m00_mix_valid,
		"original MixFileFactory recognizes M00_Tutorial.mix");

	DynamicVectorClass<StringClass> m00_names;
	preflight.m00_mix_enumerated = m00_factory.Build_Filename_List(m00_names);
	preflight.m00_archive_entries =
		m00_names.Count() > 0 ? (uint32_t)m00_names.Count() : 0U;
	preflight.m00_entry_count_exact = preflight.m00_mix_enumerated &&
		preflight.m00_archive_entries == kExpectedM00EntryCount;
	Check(result, preflight.m00_entry_count_exact,
		"original M00_Tutorial.mix enumeration is exactly 84 entries");

	preflight.ldd_name_enumerated = Filename_List_Contains(m00_names, kLevelLdd);
	preflight.lsd_name_enumerated = Filename_List_Contains(m00_names, kLevelLsd);
	preflight.dep_name_enumerated = Filename_List_Contains(m00_names, kLevelDep);
	Check(result, preflight.ldd_name_enumerated,
		"M00 LDD name enumerated by original MIX code");
	Check(result, preflight.lsd_name_enumerated,
		"M00 LSD name enumerated by original MIX code");
	Check(result, preflight.dep_name_enumerated,
		"M00 DEP name enumerated by original MIX code");

	MixFileFactoryClass always_dbs_factory(kAlwaysDbsArchive, &root_factory);
	preflight.always_dbs_mix_valid = always_dbs_factory.Is_Valid();
	Check(result, preflight.always_dbs_mix_valid,
		"original MixFileFactory recognizes always.dbs");

	DynamicVectorClass<StringClass> always_dbs_names;
	const bool always_dbs_enumerated =
		always_dbs_factory.Build_Filename_List(always_dbs_names);
	preflight.always_dbs_entries = always_dbs_names.Count() > 0 ?
		(uint32_t)always_dbs_names.Count() : 0U;
	preflight.objects_ddb_enumerated_in_always_dbs = always_dbs_enumerated &&
		Filename_List_Contains(always_dbs_names, kObjectsDdb);
	Check(result, preflight.objects_ddb_enumerated_in_always_dbs,
		"Objects.DDB source enumerated in always.dbs");

	const FileProbe direct_objects =
		Probe_Read_Only_File(always_dbs_factory, kObjectsDdb);
	preflight.objects_ddb_source_is_always_dbs = direct_objects.available &&
		direct_objects.opened && direct_objects.size == kExpectedObjectsDdbSize;
	if (preflight.objects_ddb_source_is_always_dbs) {
		snprintf(preflight.objects_ddb_provider,
			sizeof(preflight.objects_ddb_provider), "%s", "always.dbs");
	}
	Check(result, preflight.objects_ddb_source_is_always_dbs,
		"Objects.DDB read directly from always.dbs");

	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&m00_factory, "M00_Tutorial.mix");
	factory_list.Add_FileFactory(&always_dbs_factory, "always.dbs");
	factory_list.Add_FileFactory(&root_factory, "retail");

	const FileProbe objects = Probe_Read_Only_File(factory_list, kObjectsDdb);
	preflight.objects_ddb_available = objects.available;
	preflight.objects_ddb_opened = objects.opened;
	preflight.objects_ddb_size = objects.size;
	preflight.objects_ddb_size_exact = objects.size == kExpectedObjectsDdbSize;
	Check(result,
		preflight.objects_ddb_available && preflight.objects_ddb_opened &&
			preflight.objects_ddb_size_exact,
		"FileFactoryList reads exact Objects.DDB");

	const FileProbe ldd = Probe_Read_Only_File(factory_list, kLevelLdd);
	preflight.ldd_available = ldd.available;
	preflight.ldd_opened = ldd.opened;
	preflight.ldd_size = ldd.size;
	preflight.ldd_size_exact = ldd.size == kExpectedLddSize;
	Check(result, preflight.ldd_available && preflight.ldd_opened &&
		preflight.ldd_size_exact, "FileFactoryList reads exact M00 LDD");

	const FileProbe lsd = Probe_Read_Only_File(factory_list, kLevelLsd);
	preflight.lsd_available = lsd.available;
	preflight.lsd_opened = lsd.opened;
	preflight.lsd_size = lsd.size;
	preflight.lsd_size_exact = lsd.size == kExpectedLsdSize;
	Check(result, preflight.lsd_available && preflight.lsd_opened &&
		preflight.lsd_size_exact, "FileFactoryList reads exact M00 LSD");

	const FileProbe dep = Probe_Read_Only_File(factory_list, kLevelDep);
	preflight.dep_available = dep.available;
	preflight.dep_opened = dep.opened;
	preflight.dep_size = dep.size;
	preflight.dep_size_exact = dep.size == kExpectedDepSize;
	Check(result, preflight.dep_available && preflight.dep_opened &&
		preflight.dep_size_exact, "FileFactoryList reads exact M00 DEP");

	preflight.original_chunk_loader = Inspect_Level_Ldd(factory_list, preflight);
	Check(result, preflight.original_chunk_loader,
		"original ChunkLoadClass traverses M00 LDD");
	Check(result, preflight.level_info_chunk_found,
		"original LDD level-info chunk found");
	Check(result, preflight.level_data_chunk_found,
		"original LDD level-data chunk found");
	Check(result, preflight.map_filename_read && preflight.map_filename_exact,
		"original LDD level-info maps to M00_Tutorial.lsd");

	result.preflight_passed = result.failures == 0;
	result.passed = result.preflight_passed;
	if (result.passed) {
		strcpy(result.first_failure, "none");
	}
	return result;
}
