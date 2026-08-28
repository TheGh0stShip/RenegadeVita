#include "renegade_file_factory.h"

#include "assetmgr.h"
#include "ffactorylist.h"
#include "matinfo.h"
#include "mesh.h"
#include "meshmdl.h"
#include "mixfile.h"
#include "rendobj.h"
#include "texture.h"

#include <algorithm>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <map>
#include <set>
#include <string>

namespace {

const char *const kArchiveLogicalPath = "Data\\Always.dat";
const char *const kLoadingW3D = "if_lvl94load.w3d";
const char *const kRequiredTextures[] = {
	"loadscreen_cnc_1.tga",
	"loadscreen_cnc_2.tga",
	"loadscreen_cnc_3.tga",
	"loadscreen_cnc_4.tga",
};

struct TextureUse {
	unsigned polygons = 0;
	unsigned uv_vertices = 0;
	float min_u =  1000000.0f;
	float min_v =  1000000.0f;
	float max_u = -1000000.0f;
	float max_v = -1000000.0f;
};

struct Probe {
	unsigned checks = 0;
	unsigned failures = 0;
	char first_failure[128] = {};
	bool opened_w3d = false;
	bool asset_manager_loaded = false;
	unsigned prototypes = 0;
	unsigned render_objects = 0;
	unsigned mesh_count = 0;
	unsigned vertex_count = 0;
	unsigned polygon_count = 0;
	unsigned uv_array_count = 0;
	std::set<std::string> material_textures;
	std::map<std::string, TextureUse> texture_uses;
};

void Check(Probe &probe, bool condition, const char *name)
{
	++probe.checks;
	if (condition) {
		return;
	}
	++probe.failures;
	if (probe.first_failure[0] == 0) {
		std::snprintf(probe.first_failure, sizeof(probe.first_failure), "%s", name);
	}
}

std::string Lower_Basename(const char *name)
{
	std::string value = name != nullptr ? name : "";
	const std::string::size_type slash = value.find_last_of("\\/");
	if (slash != std::string::npos) {
		value.erase(0, slash + 1U);
	}
	std::transform(value.begin(), value.end(), value.begin(),
		[](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
	return value;
}

std::string Texture_Name(TextureClass *texture)
{
	if (texture == nullptr) {
		return std::string();
	}
	std::string name = Lower_Basename(texture->Get_Texture_Name());
	if (name.empty()) {
		name = Lower_Basename(texture->Get_Full_Path());
	}
	return name;
}

void Record_UV(TextureUse &use, const Vector2 &uv)
{
	use.min_u = std::min(use.min_u, uv.X);
	use.min_v = std::min(use.min_v, uv.Y);
	use.max_u = std::max(use.max_u, uv.X);
	use.max_v = std::max(use.max_v, uv.Y);
	++use.uv_vertices;
}

void Inspect_Render_Object(Probe &probe, RenderObjClass *object, unsigned depth)
{
	if (object == nullptr || depth > 32U) {
		return;
	}

	if (object->Class_ID() == RenderObjClass::CLASSID_MESH) {
		MeshClass *mesh = static_cast<MeshClass *>(object);
		MeshModelClass *model = mesh->Peek_Model();
		++probe.mesh_count;
		if (model != nullptr) {
			probe.vertex_count += static_cast<unsigned>(model->Get_Vertex_Count());
			probe.polygon_count += static_cast<unsigned>(model->Get_Polygon_Count());
			probe.uv_array_count += static_cast<unsigned>(model->Get_UV_Array_Count());

			const Vector2 *uvs = model->Get_UV_Array(0, 0);
			const TriIndex *polygons = model->Get_Polygon_Array();
			const int polygon_count = model->Get_Polygon_Count();
			const int vertex_count = model->Get_Vertex_Count();
			for (int polygon = 0; polygon < polygon_count; ++polygon) {
				TextureClass *texture = model->Peek_Texture(polygon, 0, 0);
				const std::string name = Texture_Name(texture);
				if (name.empty()) {
					continue;
				}
				TextureUse &use = probe.texture_uses[name];
				++use.polygons;
				if (uvs == nullptr || polygons == nullptr) {
					continue;
				}
				const int indices[3] = {
					polygons[polygon].I,
					polygons[polygon].J,
					polygons[polygon].K,
				};
				for (int index : indices) {
					if (index >= 0 && index < vertex_count) {
						Record_UV(use, uvs[index]);
					}
				}
			}
		}

		MaterialInfoClass *materials = mesh->Get_Material_Info();
		if (materials != nullptr) {
			for (int index = 0; index < materials->Texture_Count(); ++index) {
				TextureClass *texture = materials->Peek_Texture(index);
				const std::string name = Texture_Name(texture);
				if (!name.empty()) {
					probe.material_textures.insert(name);
				}
			}
			materials->Release_Ref();
		}
	}

	const int children = object->Get_Num_Sub_Objects();
	for (int index = 0; index < children; ++index) {
		RenderObjClass *child = object->Get_Sub_Object(index);
		Inspect_Render_Object(probe, child, depth + 1U);
		if (child != nullptr) {
			child->Release_Ref();
		}
	}
}

bool Has_Full_Tile_UV_Span(const TextureUse &use)
{
	return use.polygons > 0U &&
		use.uv_vertices >= 3U &&
		use.min_u <= 0.02f &&
		use.min_v <= 0.02f &&
		use.max_u >= 0.98f &&
		use.max_v >= 0.98f;
}

} // namespace

int main(int argc, char **argv)
{
	if (argc != 5) {
		std::fprintf(stderr, "usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT\n", argv[0]);
		return 2;
	}

	Probe probe;
	const RenegadePathRoots roots = { argv[1], argv[2], argv[3], argv[4] };
	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass mix_factory(kArchiveLogicalPath, &root_factory);
	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&mix_factory, "always.dat");
	factory_list.Add_FileFactory(&root_factory, "retail");

	FileClass *file = factory_list.Get_File(kLoadingW3D);
	probe.opened_w3d = file != nullptr && file->Is_Available() &&
		file->Open(FileClass::READ);
	Check(probe, probe.opened_w3d, "open if_lvl94load.w3d through original MIX factory");

	FileFactoryClass *previous_file_factory = _TheFileFactory;
	_TheFileFactory = &factory_list;
	if (probe.opened_w3d) {
		WW3DAssetManager asset_manager;
		probe.asset_manager_loaded = asset_manager.Load_3D_Assets(*file);
		RenderObjIterator *iterator = asset_manager.Create_Render_Obj_Iterator();
		if (iterator != nullptr) {
			for (iterator->First(); !iterator->Is_Done(); iterator->Next()) {
				++probe.prototypes;
				const char *name = iterator->Current_Item_Name();
				if (name == nullptr || name[0] == 0) {
					continue;
				}
				RenderObjClass *object = asset_manager.Create_Render_Obj(name);
				if (object != nullptr) {
					++probe.render_objects;
					Inspect_Render_Object(probe, object, 0U);
					object->Release_Ref();
				}
			}
			asset_manager.Release_Render_Obj_Iterator(iterator);
		}
	}
	_TheFileFactory = previous_file_factory;
	if (probe.opened_w3d) {
		file->Close();
	}
	if (file != nullptr) {
		factory_list.Return_File(file);
	}

	Check(probe, probe.asset_manager_loaded, "original WW3DAssetManager loaded loading W3D");
	Check(probe, probe.prototypes > 0U, "loading W3D registered render prototypes");
	Check(probe, probe.render_objects > 0U, "loading W3D render objects instantiate");
	Check(probe, probe.mesh_count >= 4U, "loading backdrop has mesh tiles");
	Check(probe, probe.vertex_count > 0U && probe.polygon_count > 0U,
		"loading backdrop has geometry");
	Check(probe, probe.uv_array_count > 0U, "loading backdrop has UV arrays");

	for (const char *texture : kRequiredTextures) {
		const auto material_it = probe.material_textures.find(texture);
		const auto use_it = probe.texture_uses.find(texture);
		Check(probe, material_it != probe.material_textures.end(),
			"required loadscreen texture is referenced by material info");
		Check(probe, use_it != probe.texture_uses.end() && use_it->second.polygons > 0U,
			"required loadscreen texture is assigned to rendered polygons");
		Check(probe, use_it != probe.texture_uses.end() &&
			Has_Full_Tile_UV_Span(use_it->second),
			"required loadscreen texture has full-tile UV coverage");
	}

	const bool passed = probe.failures == 0U;
	if (probe.first_failure[0] == 0) {
		std::snprintf(probe.first_failure, sizeof(probe.first_failure), "%s", "none");
	}

	std::printf("{\n");
	std::printf("  \"status\":\"%s\",\n", passed ? "PASS" : "FAIL");
	std::printf("  \"w3d\":\"%s\",\n", kLoadingW3D);
	std::printf("  \"checks\":%u,\n", probe.checks);
	std::printf("  \"failures\":%u,\n", probe.failures);
	std::printf("  \"first_failure\":\"%s\",\n", probe.first_failure);
	std::printf("  \"prototypes\":%u,\n", probe.prototypes);
	std::printf("  \"render_objects\":%u,\n", probe.render_objects);
	std::printf("  \"meshes\":%u,\n", probe.mesh_count);
	std::printf("  \"vertices\":%u,\n", probe.vertex_count);
	std::printf("  \"polygons\":%u,\n", probe.polygon_count);
	std::printf("  \"textures\":[");
	bool first = true;
	for (const auto &entry : probe.texture_uses) {
		if (!first) {
			std::printf(",");
		}
		first = false;
		std::printf("{\"name\":\"%s\",\"polygons\":%u,\"uv_vertices\":%u,"
			"\"min_u\":%.6f,\"min_v\":%.6f,\"max_u\":%.6f,\"max_v\":%.6f}",
			entry.first.c_str(), entry.second.polygons, entry.second.uv_vertices,
			entry.second.min_u, entry.second.min_v,
			entry.second.max_u, entry.second.max_v);
	}
	std::printf("]\n");
	std::printf("}\n");
	return passed ? 0 : 1;
}
