#include "renegade_file_factory.h"

#include "definition.h"
#include "definitionclassids.h"
#include "definitionfactorymgr.h"
#include "definitionmgr.h"
#include "chunkio.h"
#include "ffactory.h"
#include "ffactorylist.h"
#include "mixfile.h"
#include "saveload.h"
#include "saveloadids.h"
#include "wwphysids.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#if defined(RENEGADE_A30_FULL_WWPHYS)
extern "C" unsigned Renegade_A30_Host_Unsupported_GPU_Call_Count();
#endif

namespace {

struct DefinitionFingerprint
{
	uint32_t total;
	uint32_t twiddlers;
};

DefinitionFingerprint Count_Definitions()
{
	DefinitionFingerprint result = {};
	for (DefinitionClass *definition = DefinitionMgrClass::Get_First();
		definition != NULL;
		definition = DefinitionMgrClass::Get_Next(definition)) {
		++result.total;
		if (definition->Get_Class_ID() == CLASSID_TWIDDLERS) {
			++result.twiddlers;
		}
	}
	return result;
}

uint32_t Count_Definition_Class(uint32 class_id)
{
	uint32_t count = 0;
	for (DefinitionClass *definition = DefinitionMgrClass::Get_First();
		definition != NULL;
		definition = DefinitionMgrClass::Get_Next(definition)) {
		if (definition->Get_Class_ID() == class_id) {
			++count;
		}
	}
	return count;
}

bool Core_WWPhys_Factories_Registered()
{
	const uint32_t ids[] = {
		PHYSICS_CHUNKID_DECOPHYSDEF,
		PHYSICS_CHUNKID_HUMANPHYSDEF,
		PHYSICS_CHUNKID_MOTORCYCLEDEF,
		PHYSICS_CHUNKID_MOTORVEHICLEDEF,
		PHYSICS_CHUNKID_PHYS3DEF,
		PHYSICS_CHUNKID_PROJECTILEDEF,
		PHYSICS_CHUNKID_RIGIDBODYDEF,
		PHYSICS_CHUNKID_STATICPHYSDEF,
		PHYSICS_CHUNKID_WHEELEDVEHICLEDEF,
		PHYSICS_CHUNKID_STATICANIMPHYSDEF,
		PHYSICS_CHUNKID_TIMEDDECOPHYSDEF,
		PHYSICS_CHUNKID_VEHICLEPHYSDEF,
		PHYSICS_CHUNKID_TRACKEDVEHICLEDEF,
		PHYSICS_CHUNKID_VTOLVEHICLEDEF,
		PHYSICS_CHUNKID_DYNAMICANIMPHYSDEF,
		PHYSICS_CHUNKID_SHAKEABLESTATICPHYSDEF,
		PHYSICS_CHUNKID_ACCESSIBLEPHYSDEF,
	};

	for (unsigned index = 0; index < sizeof(ids) / sizeof(ids[0]); ++index) {
		if (SaveLoadSystemClass::Find_Persist_Factory(ids[index]) == NULL) {
			return false;
		}
	}
	return true;
}

bool Check(bool condition, const char *name, unsigned &checks,
	unsigned &failures)
{
	++checks;
	printf("%s: %s\n", name, condition ? "PASS" : "FAIL");
	if (!condition) {
		++failures;
	}
	return condition;
}

bool Invoke_Original_Definition_Load_Core(const char *filename)
{
	FileClass *file = _TheFileFactory->Get_File(filename);
	if (file == NULL) {
		return false;
	}

	// This is exactly the engine-level core selected by
	// SaveGameManager::Load_Save_Load_System: original FileFactoryClass,
	// ChunkLoadClass and SaveLoadSystemClass.  The host harness owns no DDB
	// parser and performs no record construction itself.
	file->Open(FileClass::READ);
	ChunkLoadClass loader(file);
	const bool result = SaveLoadSystemClass::Load(loader, true);
	file->Close();
	_TheFileFactory->Return_File(file);
	return result;
}

} // namespace

int main(int argc, char **argv)
{
	if (argc != 5) {
		fprintf(stderr,
			"usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT\n", argv[0]);
		return 2;
	}

	const RenegadePathRoots roots = { argv[1], argv[2], argv[3], argv[4] };

	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass always2_factory("Data\\Always2.dat", &root_factory);
	MixFileFactoryClass always_dbs_factory("Data\\always.dbs", &root_factory);
	MixFileFactoryClass always_factory("Data\\Always.dat", &root_factory);

	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&root_factory, "");
	factory_list.Add_FileFactory(&always2_factory, "Always2.dat");
	factory_list.Add_FileFactory(&always_dbs_factory, "Always.dbs");
	factory_list.Add_FileFactory(&always_factory, "Always.dat");
	_TheFileFactory = &factory_list;

	unsigned checks = 0;
	unsigned failures = 0;
	Check(always2_factory.Is_Valid(), "Always2 original MIX factory", checks,
		failures);
	Check(always_dbs_factory.Is_Valid(), "always.dbs original MIX factory",
		checks, failures);
	Check(always_factory.Is_Valid(), "Always.dat original MIX factory", checks,
		failures);
	Check(_TheDefinitionMgr.Chunk_ID() == CHUNKID_SAVELOAD_DEFMGR,
		"DefinitionMgr subsystem identity is 0x101", checks, failures);
	Check(SaveLoadSystemClass::Find_Persist_Factory(CHUNKID_TWIDDLER) != NULL,
		"Twiddler persist factory 0x102 registered", checks, failures);
	Check(DefinitionFactoryMgrClass::Find_Factory(CLASSID_TWIDDLERS) != NULL,
		"Twiddler definition factory registered", checks, failures);

	FileClass *objects = factory_list.Get_File("Objects.DDB");
	const bool objects_available = objects != NULL && objects->Is_Available();
	const bool objects_opened = objects_available && objects->Open(FileClass::READ);
	const int objects_size = objects_opened ? objects->Size() : -1;
	if (objects != NULL) {
		if (objects_opened) {
			objects->Close();
		}
		factory_list.Return_File(objects);
	}
	Check(objects_available && objects_opened && objects_size == 5157396,
		"Objects.DDB original biased FileClass 5157396 bytes", checks, failures);

	// This invokes the real engine core below the Combat SaveGameManager
	// filename facade.  All DDB parsing, factory dispatch, object allocation,
	// sorting and ownership are original WWSaveLoad/DefinitionMgr behavior.
	Check(Invoke_Original_Definition_Load_Core("Objects.DDB"),
		"original SaveLoadSystem loads Objects.DDB", checks, failures);
	const DefinitionFingerprint loaded = Count_Definitions();
	printf("definitions.total=%u\n", loaded.total);
	printf("definitions.twiddlers=%u\n", loaded.twiddlers);
	Check(loaded.twiddlers == 260U,
		"original DefinitionMgr loaded 260 Twiddlers", checks, failures);
	const bool wwphys_factories = Core_WWPhys_Factories_Registered();
	printf("definitions.wwphys_factories_registered=%s\n",
		wwphys_factories ? "true" : "false");
	if (wwphys_factories) {
		struct DefinitionClassProbe {
			uint32_t class_id;
			const char *name;
			uint32_t expected_count;
		};
		const DefinitionClassProbe probes[] = {
			{ CLASSID_DECOPHYSDEF, "decoration", 405U },
			{ CLASSID_HUMANPHYSDEF, "human", 219U },
			{ CLASSID_MOTORCYCLEDEF, "motorcycle", 8U },
			{ CLASSID_MOTORVEHICLEDEF, "motor_vehicle", 0U },
			{ CLASSID_PHYS3DEF, "phys3", 97U },
			{ CLASSID_PROJECTILEDEF, "projectile", 5U },
			{ CLASSID_RIGIDBODYDEF, "rigid_body", 0U },
			{ CLASSID_STATICPHYSDEF, "static", 44U },
			{ CLASSID_WHEELEDVEHICLEDEF, "wheeled_vehicle", 23U },
			{ CLASSID_STATICANIMPHYSDEF, "static_anim", 101U },
			{ CLASSID_TIMEDDECOPHYSDEF, "timed_decoration", 102U },
			{ CLASSID_VEHICLEPHYSDEF, "vehicle", 0U },
			{ CLASSID_TRACKEDVEHICLEDEF, "tracked_vehicle", 47U },
			{ CLASSID_VTOLVEHICLEDEF, "vtol_vehicle", 26U },
			{ CLASSID_DYNAMICANIMPHYSDEF, "dynamic_anim", 49U },
			{ CLASSID_SHAKEABLESTATICPHYSDEF, "shakeable_static", 0U },
			{ CLASSID_ACCESSIBLEPHYSDEF, "accessible", 25U },
		};
		Check(wwphys_factories,
			"all 17 original core WWPhys definition factories registered", checks,
			failures);
		uint32_t wwphys_definition_count = 0;
		for (unsigned index = 0;
			index < sizeof(probes) / sizeof(probes[0]); ++index) {
			const uint32_t observed =
				Count_Definition_Class(probes[index].class_id);
			printf("definitions.%s=%u\n", probes[index].name, observed);
			char check_name[128];
			snprintf(check_name, sizeof(check_name),
				"original DefinitionMgr %s count matches retail fingerprint",
				probes[index].name);
			Check(observed == probes[index].expected_count, check_name, checks,
				failures);
			wwphys_definition_count += observed;
		}
		printf("definitions.wwphys_total=%u\n", wwphys_definition_count);
		Check(wwphys_definition_count == 1151U,
			"original DefinitionMgr loaded 1151 core WWPhys definitions", checks,
			failures);
		Check(loaded.total == 1411U,
			"original DefinitionMgr loaded 1411 Twiddler plus WWPhys definitions",
			checks, failures);
		Check(loaded.total == loaded.twiddlers + wwphys_definition_count,
			"DefinitionMgr total equals observed Twiddler plus WWPhys counts",
			checks, failures);
	} else {
		Check(loaded.total == 260U,
			"partial-factory frontier skips unregistered definition chunks",
			checks, failures);
	}

	FileClass *optional = factory_list.Get_File("m00_tutorial.ddb");
	const bool optional_available = optional != NULL && optional->Is_Available();
	const bool optional_opened = optional != NULL && optional->Open(FileClass::READ);
	if (optional != NULL) {
		if (optional_opened) {
			optional->Close();
		}
		factory_list.Return_File(optional);
	}
	Check(!optional_available && !optional_opened,
		"missing M00 optional DDB preserves original miss", checks, failures);

	Check(Invoke_Original_Definition_Load_Core("m00_tutorial.ddb"),
		"original SaveLoadSystem accepts missing optional DDB as no-op", checks,
		failures);
	const DefinitionFingerprint after_optional = Count_Definitions();
	printf("definitions.after_optional_ddb=%u\n", after_optional.total);
	Check(after_optional.total == loaded.total &&
		after_optional.twiddlers == loaded.twiddlers,
		"missing optional DDB leaves DefinitionMgr unchanged", checks, failures);

#if defined(RENEGADE_A30_FULL_WWPHYS)
	const unsigned unsupported_gpu_calls =
		Renegade_A30_Host_Unsupported_GPU_Call_Count();
	printf("definition_runtime.unsupported_gpu_calls=%u\n",
		unsupported_gpu_calls);
	Check(unsupported_gpu_calls == 0U,
		"definition loading never crosses the fail-fast host DX8 boundary",
		checks, failures);
#endif

	printf("A3.0 definition runtime: %u checks, %u failures\n", checks,
		failures);

	DefinitionMgrClass::Free_Definitions();
	_TheFileFactory = NULL;
	return failures == 0 ? 0 : 1;
}
