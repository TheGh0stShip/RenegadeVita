#include "a30_world_runtime.h"

#include "renegade_file_factory.h"

#include "assetmgr.h"
#include "chunkio.h"
#include "damage.h"
#include "definition.h"
#include "definitionclassids.h"
#include "definitionmgr.h"
#include "ffactory.h"
#include "ffactorylist.h"
#include "mesh.h"
#include "meshmdl.h"
#include "mixfile.h"
#include "pathfind.h"
#include "persistfactory.h"
#include "phys.h"
#include "physlist.h"
#include "physstaticsavesystem.h"
#include "pscene.h"
#include "renegadeterrainpatch.h"
#include "rendobj.h"
#include "saveload.h"
#include "saveloadids.h"
#include "ww3d.h"
#include "wwaudio.h"
#include "ww3dids.h"
#include "wwmath.h"
#include "wwphys.h"
#include "wwphysids.h"
#include "wwsaveload.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

namespace {

const char *const kAlways2Archive = "Data\\Always2.dat";
const char *const kAlwaysDbsArchive = "Data\\always.dbs";
const char *const kAlwaysArchive = "Data\\Always.dat";
const char *const kM00Archive = "Data\\M00_Tutorial.mix";
const char *const kObjectsDdb = "Objects.DDB";
const char *const kOptionalLevelDdb = "m00_tutorial.ddb";
const char *const kM00StaticWorld = "M00_Tutorial.lsd";

// A3.0 intentionally carries the static-world factory subset.  The A3.1
// gameplay-owner closure admits additional legitimate retail Objects.DDB
// classes, so retain separate evidence fingerprints rather than treating the
// A3.0 partial registry as an A3.1 failure.
#if defined(RENEGADE_VITA_A31)
const uint32_t kExpectedDefinitionCount = 3648U;
const uint32_t kExpectedDefinitionChecksum = 0xFE798749U;
const bool kExpectedOptionalLevelDdbMissing = true;
#else
const uint32_t kExpectedDefinitionCount = 2157U;
const uint32_t kExpectedDefinitionChecksum = 0x90DB91BEU;
const bool kExpectedOptionalLevelDdbMissing = true;
#endif
const uint32_t kExpectedTwiddlerCount = 260U;
const uint32_t kExpectedStaticObjectCount = 495U;
const uint32_t kExpectedStaticLightCount = 192U;
const uint32_t kExpectedDefinitionBackedCount = 93U;
const uint32_t kExpectedDefinitionlessCount = 594U;

const uint32_t kFnvOffset = 2166136261U;
const uint32_t kFnvPrime = 16777619U;

class SaveLoadRegistryProbe : public SaveLoadSystemClass
{
public:
	static SaveLoadSubSystemClass *Find_Subsystem(uint32 id)
	{
		return Find_Sub_System(id);
	}
};

void Notify_Stage(const A30WorldRuntimeOptions *options, const char *stage)
{
	if (options != NULL && options->stage_callback != NULL) {
		options->stage_callback(options->stage_context, stage);
	}
}

void Check(A30WorldRuntimeResult &result, bool condition, const char *name)
{
	++result.checks;
	if (condition) {
		return;
	}

	++result.failures;
	if (result.first_failure[0] == 0) {
		snprintf(result.first_failure, sizeof(result.first_failure), "%s", name);
	}
}

uint32_t Hash_Byte(uint32_t hash, uint8_t value)
{
	return (hash ^ value) * kFnvPrime;
}

uint32_t Hash_U32(uint32_t hash, uint32_t value)
{
	for (unsigned shift = 0; shift < 32; shift += 8) {
		hash = Hash_Byte(hash, static_cast<uint8_t>(value >> shift));
	}
	return hash;
}

uint32_t Hash_String(uint32_t hash, const char *text)
{
	if (text == NULL) {
		return Hash_Byte(hash, 0U);
	}
	while (*text != 0) {
		hash = Hash_Byte(hash, static_cast<uint8_t>(*text));
		++text;
	}
	return Hash_Byte(hash, 0U);
}

bool Nearly_Equal(float lhs, float rhs)
{
	return fabsf(lhs - rhs) <= 0.0001f;
}

uint32_t Count_Definitions(A30WorldRuntimeFingerprint &world)
{
	uint32_t count = 0;
	uint32_t checksum = kFnvOffset;
	world.twiddler_definition_count = 0;
	world.static_phys_definition_count = 0;
	world.static_anim_phys_definition_count = 0;
	world.accessible_phys_definition_count = 0;
	world.door_phys_definition_count = 0;
	world.elevator_phys_definition_count = 0;
	world.damageable_static_phys_definition_count = 0;
	world.building_aggregate_definition_count = 0;
	world.m00_required_definition_count = 0;
	for (DefinitionClass *definition = DefinitionMgrClass::Get_First();
		definition != NULL;
		definition = DefinitionMgrClass::Get_Next(definition)) {
		++count;
		if (definition->Get_Class_ID() == CLASSID_TWIDDLERS) {
			++world.twiddler_definition_count;
		}
		switch (definition->Get_Class_ID()) {
			case CLASSID_STATICPHYSDEF:
				++world.static_phys_definition_count;
				break;
			case CLASSID_STATICANIMPHYSDEF:
				++world.static_anim_phys_definition_count;
				break;
			case CLASSID_ACCESSIBLEPHYSDEF:
				++world.accessible_phys_definition_count;
				break;
			case CLASSID_DOORPHYSDEF:
				++world.door_phys_definition_count;
				break;
			case CLASSID_ELEVATORPHYSDEF:
				++world.elevator_phys_definition_count;
				break;
			case CLASSID_DAMAGEABLESTATICPHYSDEF:
				++world.damageable_static_phys_definition_count;
				break;
			case CLASSID_BUILDINGAGGREGATEDEF:
				++world.building_aggregate_definition_count;
				break;
			default:
				break;
		}
		checksum = Hash_U32(checksum, definition->Get_ID());
		checksum = Hash_U32(checksum, definition->Get_Class_ID());
		checksum = Hash_String(checksum, definition->Get_Name());
	}
	world.definition_checksum = checksum;
	world.m00_required_definition_count =
		world.static_phys_definition_count +
		world.static_anim_phys_definition_count +
		world.accessible_phys_definition_count +
		world.door_phys_definition_count +
		world.elevator_phys_definition_count +
		world.damageable_static_phys_definition_count +
		world.building_aggregate_definition_count;
	return count;
}

bool Probe_Required_Subsystems(A30WorldRuntimeFingerprint &world)
{
	struct RequiredSubsystem {
		uint32_t id;
		SaveLoadSubSystemClass *expected;
	};
	const RequiredSubsystem required[] = {
		{ CHUNKID_SAVELOAD_DEFMGR, &_TheDefinitionMgr },
		{ PHYSICS_CHUNKID_STATIC_DATA_SUBSYSTEM, &_PhysStaticDataSaveSystem },
		{ PHYSICS_CHUNKID_STATIC_OBJECTS_SUBSYSTEM,
			&_PhysStaticObjectsSaveSystem },
	};

	world.required_subsystem_count =
		static_cast<uint32_t>(sizeof(required) / sizeof(required[0]));
	for (unsigned index = 0; index < sizeof(required) / sizeof(required[0]);
		++index) {
		if (SaveLoadRegistryProbe::Find_Subsystem(required[index].id) ==
			required[index].expected) {
			++world.registered_subsystem_count;
		}
	}
	return world.registered_subsystem_count == world.required_subsystem_count;
}

bool Probe_Required_Persist_Factories(A30WorldRuntimeFingerprint &world)
{
	/*
	** This is the complete factory closure consumed by Objects.DDB and the M00
	** static physics payload: Twiddlers, all genuine WWPhys definitions, the
	** four Combat-owned external definitions/objects, the seven serialized
	** static object types, and every WW3D persist representation used by them.
	** LIGHTPHYSDEF is intentionally absent: the canonical table has no concrete
	** persisted retail class or factory for that zero-record slot.
	*/
	const uint32_t required[] = {
		CHUNKID_TWIDDLER,

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
		PHYSICS_CHUNKID_DOORPHYSDEF,
		PHYSICS_CHUNKID_ELEVATORPHYSDEF,
		PHYSICS_CHUNKID_DAMAGEABLESTATICPHYSDEF,
		PHYSICS_CHUNKID_BUILDINGAGGREGATEDEF,

		PHYSICS_CHUNKID_LIGHTPHYS,
		PHYSICS_CHUNKID_STATICPHYS,
		PHYSICS_CHUNKID_STATICANIMPHYS,
		PHYSICS_CHUNKID_DOORPHYS,
		PHYSICS_CHUNKID_ELEVATORPHYS,
		PHYSICS_CHUNKID_DAMAGEABLESTATICPHYS,
		PHYSICS_CHUNKID_BUILDINGAGGREGATE,

		WW3D_PERSIST_CHUNKID_RENDEROBJ,
		WW3D_PERSIST_CHUNKID_LIGHT,
		WW3D_PERSIST_CHUNKID_DAZZLE,
		WW3D_PERSIST_CHUNKID_RENEGADE_TERRAIN,
	};

	world.required_persist_factory_count =
		static_cast<uint32_t>(sizeof(required) / sizeof(required[0]));
	for (unsigned index = 0; index < sizeof(required) / sizeof(required[0]);
		++index) {
		if (SaveLoadSystemClass::Find_Persist_Factory(required[index]) != NULL) {
			++world.registered_persist_factory_count;
		} else if (world.first_missing_persist_factory == 0U) {
			world.first_missing_persist_factory = required[index];
		}
	}
	return world.registered_persist_factory_count ==
		world.required_persist_factory_count;
}

bool Load_Required_SaveLoad_File(FileFactoryClass &factory,
	const char *filename, bool auto_post_load)
{
	FileClass *file = factory.Get_File(filename);
	if (file == NULL) {
		return false;
	}

	const bool opened = file->Is_Available() && file->Open(FileClass::READ);
	bool loaded = false;
	if (opened) {
		ChunkLoadClass loader(file);
		loaded = SaveLoadSystemClass::Load(loader, auto_post_load);
		file->Close();
	}
	factory.Return_File(file);
	return opened && loaded;
}

bool Load_Original_Optional_Miss(FileFactoryClass &factory,
	const char *filename, bool &missing)
{
	FileClass *file = factory.Get_File(filename);
	if (file == NULL) {
		missing = true;
		return false;
	}

	missing = !file->Is_Available();
	/* Match SaveGameManager::Load_Save_Load_System: Open is deliberately not
	** used as a gate, so an absent optional DDB is an original empty load. */
	file->Open(FileClass::READ);
	ChunkLoadClass loader(file);
	const bool loaded = SaveLoadSystemClass::Load(loader, true);
	file->Close();
	factory.Return_File(file);
	return loaded;
}

void Fingerprint_Render_Object(A30WorldRuntimeFingerprint &world,
	RenderObjClass *object, unsigned depth)
{
	if (object == NULL || depth > 64U) {
		world.render_graph_complete = false;
		return;
	}

	++world.render_object_node_count;
	world.render_graph_checksum = Hash_U32(world.render_graph_checksum,
		static_cast<uint32_t>(object->Class_ID()));
	world.render_graph_checksum = Hash_String(world.render_graph_checksum,
		object->Get_Name());

	if (object->Class_ID() == RenderObjClass::CLASSID_MESH) {
		MeshClass *mesh = static_cast<MeshClass *>(object);
		MeshModelClass *model = mesh->Peek_Model();
		++world.mesh_count;
		if (model != NULL) {
			world.mesh_vertex_count +=
				static_cast<uint64_t>(model->Get_Vertex_Count());
			world.mesh_polygon_count +=
				static_cast<uint64_t>(model->Get_Polygon_Count());
			world.render_graph_checksum = Hash_U32(world.render_graph_checksum,
				static_cast<uint32_t>(model->Get_Vertex_Count()));
			world.render_graph_checksum = Hash_U32(world.render_graph_checksum,
				static_cast<uint32_t>(model->Get_Polygon_Count()));
		}
	} else if (object->Class_ID() == RenderObjClass::CLASSID_RENEGADE_TERRAIN) {
		RenegadeTerrainPatchClass *terrain =
			static_cast<RenegadeTerrainPatchClass *>(object);
		++world.terrain_patch_count;
		world.terrain_vertex_count +=
			static_cast<uint64_t>(terrain->Get_Vertex_Count());
		world.terrain_material_count +=
			static_cast<uint64_t>(terrain->Get_Material_Count());
		world.render_graph_checksum = Hash_U32(world.render_graph_checksum,
			static_cast<uint32_t>(terrain->Get_Vertex_Count()));
		world.render_graph_checksum = Hash_U32(world.render_graph_checksum,
			static_cast<uint32_t>(terrain->Get_Material_Count()));
	}

	const int child_count = object->Get_Num_Sub_Objects();
	for (int index = 0; index < child_count; ++index) {
		RenderObjClass *child = object->Get_Sub_Object(index);
		Fingerprint_Render_Object(world, child, depth + 1U);
		if (child != NULL) {
			child->Release_Ref();
		}
	}
}

void Fingerprint_Physics_Object(A30WorldRuntimeFingerprint &world,
	PhysClass *object, bool is_static_light)
{
	if (object == NULL) {
		return;
	}

	const uint32_t factory_id = object->Get_Factory().Chunk_ID();
	world.object_identity_checksum = Hash_U32(world.object_identity_checksum,
		factory_id);
	world.object_identity_checksum = Hash_U32(world.object_identity_checksum,
		object->Get_ID());
	world.object_identity_checksum = Hash_String(world.object_identity_checksum,
		object->Get_Name());

	const PhysDefClass *definition = object->Get_Definition();
	if (definition != NULL) {
		++world.definition_backed_object_count;
		world.object_identity_checksum = Hash_U32(world.object_identity_checksum,
			definition->Get_ID());
		world.object_identity_checksum = Hash_U32(world.object_identity_checksum,
			definition->Get_Class_ID());
	} else {
		++world.definitionless_object_count;
		world.object_identity_checksum = Hash_U32(world.object_identity_checksum, 0U);
	}

	RenderObjClass *model = object->Peek_Model();
	if (model != NULL) {
		++world.render_model_count;
		const char *model_name = model->Get_Name();
		if (model_name != NULL && strcmp(model_name, "NULL") == 0) {
			++world.null_render_model_count;
		}
		Fingerprint_Render_Object(world, model, 0U);
	}

	if (is_static_light) {
		return;
	}

	switch (factory_id) {
		case PHYSICS_CHUNKID_STATICPHYS:
			++world.static_phys_count;
			break;
		case PHYSICS_CHUNKID_STATICANIMPHYS:
			++world.static_anim_phys_count;
			break;
		case PHYSICS_CHUNKID_DOORPHYS:
			++world.door_phys_count;
			break;
		case PHYSICS_CHUNKID_ELEVATORPHYS:
			++world.elevator_phys_count;
			break;
		case PHYSICS_CHUNKID_DAMAGEABLESTATICPHYS:
			++world.damageable_static_phys_count;
			break;
		case PHYSICS_CHUNKID_BUILDINGAGGREGATE:
			++world.building_aggregate_count;
			break;
		default:
			++world.unclassified_static_object_count;
			break;
	}
}

void Fingerprint_Physics_Scene(A30WorldRuntimeFingerprint &world,
	PhysicsSceneClass &scene)
{
	world.object_identity_checksum = kFnvOffset;
	world.render_graph_checksum = kFnvOffset;
	world.render_graph_complete = true;

	RefPhysListIterator static_objects = scene.Get_Static_Object_Iterator();
	for (static_objects.First(); !static_objects.Is_Done();
		static_objects.Next()) {
		++world.static_object_count;
		Fingerprint_Physics_Object(world, static_objects.Peek_Obj(), false);
	}

	RefPhysListIterator static_lights = scene.Get_Static_Light_Iterator();
	for (static_lights.First(); !static_lights.Is_Done(); static_lights.Next()) {
		++world.static_light_count;
		Fingerprint_Physics_Object(world, static_lights.Peek_Obj(), true);
	}

	RefPhysListIterator static_anim = scene.Get_Static_Anim_Object_Iterator();
	for (static_anim.First(); !static_anim.Is_Done(); static_anim.Next()) {
		++world.static_anim_iterator_count;
	}

	RefPhysListIterator dynamic_objects = scene.Get_Dynamic_Object_Iterator();
	for (dynamic_objects.First(); !dynamic_objects.Is_Done();
		dynamic_objects.Next()) {
		++world.dynamic_object_count;
	}

	Vector3 level_min;
	Vector3 level_max;
	scene.Get_Level_Extents(level_min, level_max);
	world.level_min[0] = level_min.X;
	world.level_min[1] = level_min.Y;
	world.level_min[2] = level_min.Z;
	world.level_max[0] = level_max.X;
	world.level_max[1] = level_max.Y;
	world.level_max[2] = level_max.Z;
	world.vis_object_count = static_cast<uint32_t>(scene.Get_Vis_Table_Size());
	world.vis_sector_count = static_cast<uint32_t>(scene.Get_Vis_Table_Count());
	world.pathfind_data_loaded =
		PathfindClass::Get_Instance() != NULL &&
		PathfindClass::Get_Instance()->Does_Pathfind_Data_Exist();
}

void Fingerprint_Prototypes(A30WorldRuntimeFingerprint &world,
	WW3DAssetManager &asset_manager)
{
	world.prototype_checksum = kFnvOffset;
	RenderObjIterator *iterator = asset_manager.Create_Render_Obj_Iterator();
	if (iterator == NULL) {
		return;
	}
	for (iterator->First(); !iterator->Is_Done(); iterator->Next()) {
		++world.loaded_prototype_count;
		world.prototype_checksum = Hash_U32(world.prototype_checksum,
			static_cast<uint32_t>(iterator->Current_Item_Class_ID()));
		world.prototype_checksum = Hash_String(world.prototype_checksum,
			iterator->Current_Item_Name());
	}
	asset_manager.Release_Render_Obj_Iterator(iterator);
}

} // namespace

A30WorldRuntimeResult Run_A30_World_Runtime(
	const RenegadePathRoots &roots,
	const A30WorldRuntimeOptions *options)
{
	A30WorldRuntimeResult result = {};
	A30WorldRuntimeFingerprint &world = result.world;
	world.attempted = true;

	/* FileFactoryListClass is itself an original process singleton.  Test all
	** singleton preconditions before constructing our local list: its VC6-era
	** constructor asserts and then overwrites Instance, which would otherwise
	** corrupt an already-running Commando owner even though this harness later
	** reports a clean-entry failure. */
	world.clean_engine_entry_state =
		FileFactoryListClass::Get_Instance() == NULL &&
		WW3DAssetManager::Get_Instance() == NULL &&
		PhysicsSceneClass::Get_Instance() == NULL &&
		!WW3D::Is_Initted() && DefinitionMgrClass::Get_First() == NULL &&
		ArmorWarheadManager::Get_Num_Armor_Types() == 0 &&
		ArmorWarheadManager::Get_Num_Warhead_Types() == 0;
	Check(result, world.clean_engine_entry_state,
		"clean original engine singleton entry state");
	if (!world.clean_engine_entry_state) {
		world.teardown_completed = true; /* this invocation acquired nothing */
		result.passed = false;
		return result;
	}

#if defined(RENEGADE_VITA_A31)
	WWAudioClass *audio = WWAudioClass::Get_Instance();
	world.audio_boundary_ready = audio != NULL;
	world.audio_sound_scene_available =
		audio != NULL && audio->Get_Sound_Scene() != NULL;
	/* AudioSaveLoad is registered by the A3.1 closure and dereferences this
	** singleton while loading the M00 static-audio chunk.  Fail before any
	** serialized world work if the application has violated the original
	** startup order; never turn this into a silent chunk skip. */
	if (!world.audio_boundary_ready) {
		++result.failures;
		if (result.first_failure[0] == 0) {
			snprintf(result.first_failure, sizeof(result.first_failure),
				"WWAudio boundary must exist before M00 world load");
		}
		world.teardown_completed = true;
		result.passed = false;
		return result;
	}
#endif

	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass always2_factory(kAlways2Archive, &root_factory);
	MixFileFactoryClass always_dbs_factory(kAlwaysDbsArchive, &root_factory);
	MixFileFactoryClass always_factory(kAlwaysArchive, &root_factory);
	MixFileFactoryClass m00_factory(kM00Archive, &root_factory);

	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&root_factory, "");
	factory_list.Add_FileFactory(&always2_factory, "Always2.dat");
	factory_list.Add_FileFactory(&always_dbs_factory, "Always.dbs");
	factory_list.Add_FileFactory(&always_factory, "Always.dat");
	factory_list.Add_FileFactory(&m00_factory, "M00_Tutorial.mix");

	FileFactoryClass *previous_file_factory = _TheFileFactory;
	_TheFileFactory = &factory_list;

	bool math_initialized = false;
	bool ww3d_initialized = false;
	bool wwphys_initialized = false;
	bool wwsaveload_initialized = false;
	bool armor_warhead_initialized = false;
	bool post_load_pending = false;
	WW3DAssetManager *asset_manager = NULL;
	PhysicsSceneClass *scene = NULL;

	do {
		world.factory_chain_ready = always2_factory.Is_Valid() &&
			always_dbs_factory.Is_Valid() && always_factory.Is_Valid() &&
			m00_factory.Is_Valid();
		Check(result, world.factory_chain_ready,
			"original retail FileFactoryList/MIX chain ready");

		world.required_subsystems_registered = Probe_Required_Subsystems(world);
		Check(result, world.required_subsystems_registered,
			"original definition and WWPhys static subsystems registered");
		world.required_persist_factories_registered =
			Probe_Required_Persist_Factories(world);
		Check(result, world.required_persist_factories_registered,
			"complete original M00 persist-factory closure registered");

		if (!world.factory_chain_ready || !world.clean_engine_entry_state ||
			!world.required_subsystems_registered ||
			!world.required_persist_factories_registered) {
			break;
		}

		WWMath::Init();
		math_initialized = true;
		asset_manager = new WW3DAssetManager;
		asset_manager->Set_WW3D_Load_On_Demand(true);
		asset_manager->Set_Activate_Fog_On_Load(true);
		world.asset_manager_load_on_demand =
			asset_manager->Get_WW3D_Load_On_Demand();
		Check(result, world.asset_manager_load_on_demand,
			"original WW3DAssetManager load-on-demand enabled");
		if (!world.asset_manager_load_on_demand) {
			break;
		}

		ww3d_initialized = WW3D::Init(NULL, NULL, true) == WW3D_ERROR_OK;
		world.ww3d_initialized = ww3d_initialized;
		Check(result, world.ww3d_initialized, "original WW3D initialized");
		if (!ww3d_initialized) {
			break;
		}

		WWPhys::Init();
		wwphys_initialized = true;
		world.wwphys_initialized = true;
		WWSaveLoad::Init();
		wwsaveload_initialized = true;
		world.wwsaveload_initialized = true;

		scene = new PhysicsSceneClass;
		world.physics_scene_initialized =
			PhysicsSceneClass::Get_Instance() == scene;
		Check(result, world.physics_scene_initialized,
			"original PhysicsScene singleton initialized");
		if (!world.physics_scene_initialized) {
			break;
		}

		/* CombatManager::Init establishes this original database before any
		** DefenseObject-bearing definitions or static objects are restored. */
		ArmorWarheadManager::Init();
		armor_warhead_initialized = true;
		world.armor_type_count = static_cast<uint32_t>(
			ArmorWarheadManager::Get_Num_Armor_Types());
		world.warhead_type_count = static_cast<uint32_t>(
			ArmorWarheadManager::Get_Num_Warhead_Types());
		world.armor_warhead_initialized =
			world.armor_type_count > 0U && world.warhead_type_count > 0U;
		Check(result, world.armor_warhead_initialized,
			"original ArmorWarheadManager database initialized");
		if (!world.armor_warhead_initialized) {
			break;
		}

		world.objects_ddb_loaded = Load_Required_SaveLoad_File(factory_list,
			kObjectsDdb, true);
		Check(result, world.objects_ddb_loaded,
			"original SaveLoadSystem loads Objects.DDB");
		if (!world.objects_ddb_loaded) {
			break;
		}

		world.definition_count = Count_Definitions(world);
		Check(result, world.definition_count == kExpectedDefinitionCount,
			"original DefinitionMgr contains exact Objects.DDB definition count");
		Check(result,
			world.twiddler_definition_count == kExpectedTwiddlerCount,
			"original DefinitionMgr contains exact Twiddler count");
		Check(result,
			world.static_phys_definition_count == 44U &&
			world.static_anim_phys_definition_count == 101U &&
			world.accessible_phys_definition_count == 25U &&
			world.door_phys_definition_count == 102U &&
			world.elevator_phys_definition_count == 64U &&
			world.damageable_static_phys_definition_count == 331U &&
			world.building_aggregate_definition_count == 249U &&
			world.m00_required_definition_count == 916U,
			"original M00 definition-class fingerprint");
		const bool definitions_valid =
			world.definition_count == kExpectedDefinitionCount &&
			world.twiddler_definition_count == kExpectedTwiddlerCount &&
			world.static_phys_definition_count == 44U &&
			world.static_anim_phys_definition_count == 101U &&
			world.accessible_phys_definition_count == 25U &&
			world.door_phys_definition_count == 102U &&
			world.elevator_phys_definition_count == 64U &&
			world.damageable_static_phys_definition_count == 331U &&
			world.building_aggregate_definition_count == 249U &&
			world.m00_required_definition_count == 916U;
		if (!definitions_valid) {
			break;
		}

		const bool optional_loaded = Load_Original_Optional_Miss(factory_list,
			kOptionalLevelDdb, world.optional_level_ddb_missing);
		const uint32_t definitions_before_optional_checksum =
			world.definition_checksum;
		world.definition_count_after_optional_ddb =
			Count_Definitions(world);
		world.definition_checksum_after_optional_ddb =
			world.definition_checksum;
		world.definition_checksum = definitions_before_optional_checksum;
		world.optional_level_ddb_noop = optional_loaded &&
			(kExpectedOptionalLevelDdbMissing
				? (world.optional_level_ddb_missing &&
					world.definition_count_after_optional_ddb == world.definition_count &&
					world.definition_checksum_after_optional_ddb == world.definition_checksum)
				: !world.optional_level_ddb_missing);
		Check(result, world.optional_level_ddb_noop,
			kExpectedOptionalLevelDdbMissing
				? "missing M00 optional DDB is original no-op"
				: "A3.1 original M00 gameplay DDB is available");
		if (!world.optional_level_ddb_noop) {
			break;
		}

		Notify_Stage(options, "required M00 static-world SaveLoad entry");
		world.m00_static_world_loaded = Load_Required_SaveLoad_File(factory_list,
			kM00StaticWorld, false);
		Notify_Stage(options, "required M00 static-world SaveLoad complete");
		/* auto_post_load=false intentionally matches SaveGameManager::Load_Level.
		** Even a failing subsystem may have registered callbacks for objects it
		** restored before reporting failure, so teardown must drain the original
		** callback list while those objects are still owned by the scene. */
		post_load_pending = true;
		Check(result, world.m00_static_world_loaded,
			"original SaveLoadSystem loads M00 static world");
		if (!world.m00_static_world_loaded) {
			break;
		}

		world.post_load_completed =
			SaveLoadSystemClass::Post_Load_Processing(NULL);
		post_load_pending = false;
		Check(result, world.post_load_completed,
			"original SaveLoad post-load processing completed");
		if (!world.post_load_completed) {
			break;
		}

		Fingerprint_Physics_Scene(world, *scene);
		Fingerprint_Prototypes(world, *asset_manager);
		Check(result, world.static_object_count == kExpectedStaticObjectCount,
			"original PhysicsScene contains exact M00 static object count");
		Check(result, world.static_light_count == kExpectedStaticLightCount,
			"original PhysicsScene contains exact M00 static light count");
		Check(result,
			world.static_phys_count == 424U &&
			world.static_anim_phys_count == 5U &&
			world.door_phys_count == 10U &&
			world.elevator_phys_count == 4U &&
			world.damageable_static_phys_count == 5U &&
			world.building_aggregate_count == 47U &&
			world.unclassified_static_object_count == 0U,
			"original M00 concrete static object factory fingerprint");
		Check(result,
			world.definition_backed_object_count ==
				kExpectedDefinitionBackedCount,
			"original M00 definition-backed object count");
		Check(result,
			world.definitionless_object_count == kExpectedDefinitionlessCount,
			"original M00 valid definitionless object count");
		Check(result,
			world.definition_backed_object_count +
				world.definitionless_object_count ==
				world.static_object_count + world.static_light_count,
			"all original M00 physics objects fingerprinted");
		Check(result, world.dynamic_object_count == 0U,
			"static M00 load creates no dynamic physics objects");
		Check(result,
			world.static_anim_iterator_count ==
				world.static_anim_phys_count + world.door_phys_count +
				world.elevator_phys_count +
				world.damageable_static_phys_count +
				world.building_aggregate_count,
			"original PhysicsScene static-animation index is coherent");
		Check(result,
			world.render_model_count ==
				world.static_object_count + world.static_light_count &&
				world.null_render_model_count == 0U,
			"all original M00 physics objects own non-null retail models");
		Check(result,
			world.render_graph_complete &&
				world.render_object_node_count > 0U &&
				world.loaded_prototype_count > 0U,
			"original M00 RenderObj graph and asset prototypes populated");
		Check(result, world.pathfind_data_loaded,
			"original M00 pathfind data populated");
		Check(result,
			world.vis_object_count > 0U && world.vis_sector_count > 0U,
			"original M00 visibility tables populated");

		/* These semantic values were derived only after the first successful
		** unchanged-retail run of the complete original loader. They turn that
		** observation into a deterministic regression fingerprint; none are
		** used to construct or alter engine objects. */
		Check(result,
			world.armor_type_count == 31U && world.warhead_type_count == 29U,
			"original ArmorWarheadManager retail fingerprint");
		Check(result, world.definition_checksum == kExpectedDefinitionChecksum,
			"original DefinitionMgr identity checksum");
		Check(result,
			world.render_object_node_count == 1615U &&
			world.mesh_count == 1288U &&
			world.mesh_vertex_count == 38158U &&
			world.mesh_polygon_count == 21537U &&
			world.terrain_patch_count == 0U,
			"original M00 RenderObj graph geometry fingerprint");
		Check(result,
			world.loaded_prototype_count == 1177U &&
			world.prototype_checksum == 0xE835A45FU,
			"original M00 asset prototype fingerprint");
		Check(result,
			world.object_identity_checksum == 0x4A930F8AU &&
			world.render_graph_checksum == 0xBFA9C255U,
			"original M00 object and RenderObj identity checksums");
		Check(result,
			world.vis_object_count == 1684U &&
			world.vis_sector_count == 347U,
			"original M00 visibility-table fingerprint");
		Check(result,
			Nearly_Equal(world.level_min[0], -109.983284f) &&
			Nearly_Equal(world.level_min[1], -109.420731f) &&
			Nearly_Equal(world.level_min[2], -18.072906f) &&
			Nearly_Equal(world.level_max[0], 121.511314f) &&
			Nearly_Equal(world.level_max[1], 118.983627f) &&
			Nearly_Equal(world.level_max[2], 39.252510f),
			"original M00 world-extents fingerprint");
		if (result.failures != 0U) {
			break;
		}

		if (options != NULL && options->world_loaded_callback != NULL) {
			world.world_callback_invoked = true;
			world.world_callback_completed =
				options->world_loaded_callback(options->callback_context,
					*scene, *asset_manager, world);
			Check(result, world.world_callback_completed,
				"loaded-world continuation completed");
		}
	} while (false);

	/* Release the live world before definitions and assets, matching original
	** ownership.  Keep the file-factory chain installed until every subsystem
	** has completed shutdown. */
	if (post_load_pending) {
		SaveLoadSystemClass::Post_Load_Processing(NULL);
		post_load_pending = false;
	}
	if (scene != NULL) {
		scene->Release_Ref();
		scene = NULL;
	}
	if (armor_warhead_initialized) {
		ArmorWarheadManager::Shutdown();
	}
	if (asset_manager != NULL) {
		WW3DAssetManager::Delete_This();
		asset_manager = NULL;
	}
	if (math_initialized) {
		WWMath::Shutdown();
	}
	if (wwsaveload_initialized) {
		WWSaveLoad::Shutdown();
	}
	if (ww3d_initialized) {
		WW3D::Shutdown();
	}
	if (wwphys_initialized) {
		WWPhys::Shutdown();
	}

	_TheFileFactory = previous_file_factory;
	world.teardown_completed =
		PhysicsSceneClass::Get_Instance() == NULL &&
		WW3DAssetManager::Get_Instance() == NULL &&
		DefinitionMgrClass::Get_First() == NULL && !WW3D::Is_Initted() &&
		ArmorWarheadManager::Get_Num_Armor_Types() == 0 &&
		ArmorWarheadManager::Get_Num_Warhead_Types() == 0 &&
		FileFactoryListClass::Get_Instance() == &factory_list &&
		_TheFileFactory == previous_file_factory;
	Check(result, world.teardown_completed,
		"original world ownership tears down cleanly");

	result.passed = result.failures == 0;
	if (result.passed) {
		snprintf(result.first_failure, sizeof(result.first_failure), "%s", "none");
	}
	return result;
}
