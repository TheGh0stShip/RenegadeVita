#pragma once

#include "basegameobj.h"
#include "definition.h"
#include "definitionmgr.h"
#include "ffactory.h"
#include "gameobjmanager.h"
#include "gameobjobserver.h"
#include "mixfile.h"
#include "physicalgameobj.h"
#include "rendobj.h"
#include "scriptablegameobj.h"
#include "w3d_dep.h"
#include "wwfile.h"

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <set>
#include <string>
#include <vector>

extern int Get_Script_Count(void);
extern const char *Get_Script_Name(int index);

inline void Dump_M13_Linked_Scripts()
{
	const int count = Get_Script_Count();
	for (int i = 0; i < count; ++i) {
		const char *name = Get_Script_Name(i);
		std::printf("m13.linked_script\t%s\n", name != NULL ? name : "");
	}
	std::printf("m13.script_registry_summary\t%d\n", count);
}

inline bool M13_Is_W3D(const char *name)
{
	const size_t length = std::strlen(name);
	return length >= 4 && stricmp(name + length - 4, ".w3d") == 0;
}

inline std::string M13_Lower_Name(const char *name)
{
	std::string result(name);
	std::transform(result.begin(), result.end(), result.begin(),
		[](unsigned char c) { return static_cast<char>(std::tolower(c)); });
	return result;
}

inline bool M13_File_Available(const char *name)
{
	FileClass *file = _TheFileFactory->Get_File(name);
	const bool available = file != NULL && file->Is_Available();
	if (file != NULL) _TheFileFactory->Return_File(file);
	return available;
}

inline bool Dump_M13_Cinematic_Preset_Definitions()
{
	const char *manifest = std::getenv("RENEGADE_M13_PRESET_LIST");
	if (manifest == NULL || *manifest == 0) {
		std::printf("m13.preset_inventory_unavailable\n");
		return false;
	}
	std::ifstream input(manifest);
	if (!input) return false;
	unsigned count = 0;
	unsigned missing = 0;
	std::string name;
	while (std::getline(input, name) && count < 256U) {
		if (name.empty()) continue;
		DefinitionClass *definition =
			DefinitionMgrClass::Find_Named_Definition(name.c_str(), false);
		std::printf("m13.cinematic_preset\t%s\t%u\t%u\n", name.c_str(),
			definition != NULL ? definition->Get_ID() : 0U,
			definition != NULL ? definition->Get_Class_ID() : 0U);
		++count;
		if (definition == NULL) ++missing;
	}
	std::printf("m13.preset_summary\t%u\t%u\n", count, missing);
	return input.eof() && count != 0U && missing == 0U;
}

inline bool Dump_M13_W3D_Dependencies(MixFileFactoryClass &archive)
{
	DynamicVectorClass<StringClass> filenames;
	if (!archive.Build_Filename_List(filenames)) {
		std::printf("m13.w3d_inventory_unavailable\n");
		return false;
	}
	std::vector<std::string> pending;
	std::set<std::string> seen;
	unsigned archive_w3d_files = 0;
	for (int i = 0; i < filenames.Count(); ++i) {
		const char *name = filenames[i];
		if (!M13_Is_W3D(name)) continue;
		++archive_w3d_files;
		if (seen.insert(M13_Lower_Name(name)).second) pending.push_back(name);
	}
	const char *asset_manifest = std::getenv("RENEGADE_M13_ASSET_LIST");
	if (asset_manifest == NULL || *asset_manifest == 0) {
		std::printf("m13.level_asset_inventory_unavailable\n");
		return false;
	}
	std::ifstream asset_input(asset_manifest);
	if (!asset_input) return false;
	unsigned level_w3d_records = 0;
	unsigned placeholder_records = 0;
	std::string asset_name;
	while (std::getline(asset_input, asset_name)) {
		if (!M13_Is_W3D(asset_name.c_str())) continue;
		++level_w3d_records;
		if (stricmp(asset_name.c_str(), ".w3d") == 0) {
			++placeholder_records;
			continue;
		}
		if (seen.insert(M13_Lower_Name(asset_name.c_str())).second) {
			pending.push_back(asset_name);
		}
	}
	unsigned dependencies = 0;
	unsigned failed = 0;
	unsigned dds_aliases = 0;
	unsigned unresolved_dependencies = 0;
	for (size_t i = 0; i < pending.size() && i < 4096U; ++i) {
		// Enqueuing child files can reallocate pending during this iteration.
		const std::string current_name = pending[i];
		const char *name = current_name.c_str();
		StringList files;
		const bool opened = Get_W3D_Dependencies(name, files);
		std::printf("m13.w3d\t%s\t%d\t%zu\n", name, opened ? 1 : 0, files.size());
		if (!opened) ++failed;
		for (const std::string &dependency : files) {
			const bool raw_available = M13_File_Available(dependency.c_str());
			bool dds_alias = false;
			if (!raw_available && dependency.size() >= 4U &&
				stricmp(dependency.c_str() + dependency.size() - 4U, ".tga") == 0) {
				std::string dds_name = dependency;
				dds_name.replace(dds_name.size() - 3U, 3U, "dds");
				dds_alias = M13_File_Available(dds_name.c_str());
			}
			const char *status = raw_available ? "raw" :
				(dds_alias ? "dds_alias" : "unresolved");
			std::printf("m13.w3d_dep\t%s\t%s\t%s\n", name,
				dependency.c_str(), status);
			++dependencies;
			if (dds_alias) ++dds_aliases;
			if (!raw_available && !dds_alias) ++unresolved_dependencies;
			if (M13_Is_W3D(dependency.c_str()) &&
				seen.insert(M13_Lower_Name(dependency.c_str())).second) {
				pending.push_back(dependency);
			}
		}
	}
	std::printf("m13.w3d_summary\t%u\t%u\t%u\t%zu\t%u\t%u\t%u\t%u\n",
		archive_w3d_files, level_w3d_records, placeholder_records,
		pending.size(), dependencies, failed, dds_aliases,
		unresolved_dependencies);
	return archive_w3d_files != 0U && level_w3d_records != 0U &&
		asset_input.eof() && pending.size() <= 4096U;
}

inline void Dump_M13_Runtime_Inventory()
{
	unsigned objects = 0;
	unsigned physical_objects = 0;
	unsigned observers = 0;
	for (SLNode<BaseGameObj> *node = GameObjManager::Get_Game_Obj_List()->Head();
		node != NULL; node = node->Next()) {
		BaseGameObj *object = node->Data();
		const DefinitionClass &definition = object->Get_Definition();
		PhysicalGameObj *physical = object->As_PhysicalGameObj();
		ScriptableGameObj *scriptable = object->As_ScriptableGameObj();
		const RenderObjClass *model = physical != NULL ? physical->Peek_Model() : NULL;
		const int killed_explosion = physical != NULL ?
			physical->Get_Definition().Get_Killed_Explosion_ID() : 0;
		const GameObjObserverList *object_observers = scriptable != NULL ?
			&scriptable->Get_Observers() : NULL;
		std::printf("m13.object\t%d\t%u\t%u\t%s\t%s\t%d\t%d\n",
			object->Get_ID(), definition.Get_ID(), definition.Get_Class_ID(),
			definition.Get_Name() != NULL ? definition.Get_Name() : "",
			model != NULL ? model->Get_Name() : "",
			killed_explosion,
			object_observers != NULL ? object_observers->Count() : 0);
		++objects;
		if (physical != NULL) ++physical_objects;
		if (object_observers != NULL) {
			for (int i = 0; i < object_observers->Count(); ++i) {
				GameObjObserverClass *observer = (*object_observers)[i];
				if (observer == NULL) continue;
				std::printf("m13.observer\t%d\t%d\t%s\n",
					object->Get_ID(), observer->Get_ID(),
					observer->Get_Name() != NULL ? observer->Get_Name() : "");
				++observers;
			}
		}
	}
	std::printf("m13.inventory_summary\t%u\t%u\t%u\n",
		objects, physical_objects, observers);
}
