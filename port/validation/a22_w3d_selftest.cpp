#include "a22_w3d_selftest.h"

#include "renegade_file_factory.h"

#include "chunkio.h"
#include "ffactorylist.h"
#include "mixfile.h"
#include "w3d_file.h"

#include "aabox.h"
#include "assetmgr.h"
#include "camera.h"
#include "htree.h"
#include "matinfo.h"
#include "matrix3d.h"
#include "mesh.h"
#include "meshmdl.h"
#include "rendobj.h"
#include "scene.h"
#include "sphere.h"
#include "ww3d.h"
#include "ww3d_vita_renderer.h"

#include <stdio.h>
#include <string.h>
#include <math.h>

namespace {

const char *const kArchiveLogicalPath = "Data\\Always.dat";
const char *const kKnownEntry = "dsp_o2tank.w3d";

void Check(A22W3DSelfTestResult &result, bool condition, const char *name)
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

void Fingerprint_Render_Object(A22W3DSelfTestResult &result, RenderObjClass *object,
	unsigned depth)
{
	if (object == NULL || depth > 32) {
		return;
	}

	++result.render_object_subobjects;
	if (object->Class_ID() == RenderObjClass::CLASSID_MESH) {
		MeshClass *mesh = static_cast<MeshClass *>(object);
		MeshModelClass *model = mesh->Peek_Model();
		++result.mesh_count;
		if (model != NULL) {
			result.vertex_count += static_cast<unsigned>(model->Get_Vertex_Count());
			result.polygon_count += model->Get_Polygon_Count();
		}
		MaterialInfoClass *materials = mesh->Get_Material_Info();
		if (materials != NULL) {
			result.material_count += static_cast<unsigned>(materials->Vertex_Material_Count());
			result.texture_count += static_cast<unsigned>(materials->Texture_Count());
			materials->Release_Ref();
		}
	}

	const int child_count = object->Get_Num_Sub_Objects();
	for (int index = 0; index < child_count; ++index) {
		RenderObjClass *child = object->Get_Sub_Object(index);
		Fingerprint_Render_Object(result, child, depth + 1);
		if (child != NULL) {
			child->Release_Ref();
		}
	}
}

} // namespace

A22W3DSelfTestResult Run_A22_W3D_Self_Test(const RenegadePathRoots &roots,
	const A22W3DRenderOptions *render_options)
{
	A22W3DSelfTestResult result = {};
	static_assert(sizeof(W3dChunkHeader) == 8, "W3D chunk header disk ABI must be 8 bytes");
	static_assert(sizeof(W3dHierarchyStruct) == 36,
		"W3D hierarchy header disk ABI must be 36 bytes");

	RenegadeRootedFileFactoryClass root_factory(roots);
	MixFileFactoryClass mix_factory(kArchiveLogicalPath, &root_factory);
	FileFactoryListClass factory_list;
	factory_list.Add_FileFactory(&mix_factory, "always.dat");
	factory_list.Add_FileFactory(&root_factory, "retail");

	FileClass *file = factory_list.Get_File(kKnownEntry);
	const bool opened = file != NULL && file->Is_Available() && file->Open(FileClass::READ);
	Check(result, opened, "open W3D through original factory chain");
	if (opened) {
		ChunkLoadClass loader(file);
		while (loader.Open_Chunk()) {
			const unsigned index = result.top_level_chunk_count++;
			if (index < 16) {
				result.top_level_ids[index] = loader.Cur_Chunk_ID();
				result.top_level_lengths[index] = loader.Cur_Chunk_Length();
			}
			result.original_chunk_loader = true;

			if (loader.Cur_Chunk_ID() == W3D_CHUNK_HIERARCHY) {
				result.hierarchy_found = true;
				if (loader.Open_Chunk()) {
					if (loader.Cur_Chunk_ID() == W3D_CHUNK_HIERARCHY_HEADER) {
						W3dHierarchyStruct header = {};
						if (loader.Read(&header, sizeof(header)) == sizeof(header)) {
							result.hierarchy_header_read = true;
							result.hierarchy_pivots = header.NumPivots;
							snprintf(result.hierarchy_name, sizeof(result.hierarchy_name),
								"%.*s", W3D_NAME_LEN, header.Name);
						}
					}
					loader.Close_Chunk();
				}
			}
			loader.Close_Chunk();
		}
		file->Close();
	}
	if (file != NULL) {
		factory_list.Return_File(file);
	}

	Check(result, result.original_chunk_loader && result.top_level_chunk_count > 0,
		"original ChunkLoadClass top-level traversal");
	Check(result, result.hierarchy_found, "W3D hierarchy top-level chunk");
	Check(result, result.hierarchy_header_read, "W3D hierarchy header read");
	Check(result, result.hierarchy_pivots > 0 && result.hierarchy_pivots < 65536,
		"W3D hierarchy pivot count");
	Check(result, result.hierarchy_name[0] != 0, "W3D hierarchy name");

	FileClass *asset_file = factory_list.Get_File(kKnownEntry);
	if (asset_file != NULL && asset_file->Is_Available()) {
		FileFactoryClass *previous_file_factory = _TheFileFactory;
		_TheFileFactory = &factory_list;
		{
		WW3DAssetManager asset_manager;
		result.asset_manager_loaded = asset_manager.Load_3D_Assets(*asset_file);

		RenderObjIterator *iterator = asset_manager.Create_Render_Obj_Iterator();
		if (iterator != NULL) {
			for (iterator->First(); !iterator->Is_Done(); iterator->Next()) {
				const unsigned index = result.prototype_count++;
				if (index < 16) {
					snprintf(result.prototype_names[index],
						sizeof(result.prototype_names[index]), "%s",
						iterator->Current_Item_Name() != NULL ?
						iterator->Current_Item_Name() : "");
					result.prototype_class_ids[index] = iterator->Current_Item_Class_ID();
				}
			}
			asset_manager.Release_Render_Obj_Iterator(iterator);
		}

		RenderObjClass *object = asset_manager.Create_Render_Obj(result.hierarchy_name);
		if (object != NULL) {
			result.render_object_created = true;
			snprintf(result.render_object_name, sizeof(result.render_object_name), "%s",
				object->Get_Name() != NULL ? object->Get_Name() : "");
			result.render_object_class_id = object->Class_ID();
			Fingerprint_Render_Object(result, object, 0);

			const HTreeClass *tree = object->Get_HTree();
			if (tree != NULL) {
				result.render_hierarchy_pivots = static_cast<unsigned>(tree->Num_Pivots());
				snprintf(result.render_hierarchy_name,
					sizeof(result.render_hierarchy_name), "%s", tree->Get_Name());
			}

			const SphereClass &sphere = object->Get_Bounding_Sphere();
			result.bounding_sphere_center[0] = sphere.Center.X;
			result.bounding_sphere_center[1] = sphere.Center.Y;
			result.bounding_sphere_center[2] = sphere.Center.Z;
			result.bounding_sphere_radius = sphere.Radius;
			const AABoxClass &box = object->Get_Bounding_Box();
			result.bounding_box_center[0] = box.Center.X;
			result.bounding_box_center[1] = box.Center.Y;
			result.bounding_box_center[2] = box.Center.Z;
			result.bounding_box_extent[0] = box.Extent.X;
			result.bounding_box_extent[1] = box.Extent.Y;
			result.bounding_box_extent[2] = box.Extent.Z;

			object->Set_Transform(Matrix3D(1));

			SimpleSceneClass *scene = new SimpleSceneClass();
			CameraClass *camera = new CameraClass();
			camera->Set_Aspect_Ratio(960.0f / 544.0f);
			camera->Set_Clip_Planes(0.1f, 100.0f);
			scene->Add_Render_Object(object);

			result.renderer_initialized =
				WW3D::Init(NULL, NULL, true) == WW3D_ERROR_OK && WW3D::Is_Initted();
			if (result.renderer_initialized) {
				RenegadeVitaRenderer::Reset_Statistics();
				const bool present_frames = render_options != NULL &&
					render_options->present_frames;
				const unsigned maximum_frames = render_options != NULL ?
					render_options->maximum_frames : 1U;
				A22CameraControlState camera_control = { 0.0f, 0.08f, 4.0f };
				bool frame_path_ok = true;
				unsigned frame_index = 0;
				do {
					const float horizontal_distance = camera_control.distance *
						cosf(camera_control.pitch);
					const Vector3 camera_position(
						horizontal_distance * sinf(camera_control.yaw),
						-horizontal_distance * cosf(camera_control.yaw),
						camera_control.distance * sinf(camera_control.pitch));
					Matrix3D camera_transform(1);
					camera_transform.Look_At(camera_position, Vector3(0.0f, 0.0f, 0.0f), 0.0f);
					camera->Set_Transform(camera_transform);
					WW3D::Sync((frame_index + 1U) * 16U);

					const bool began = WW3D::Begin_Render(true, true,
						Vector3(0.035f, 0.055f, 0.085f)) == WW3D_ERROR_OK;
					const bool rendered = began &&
						WW3D::Render(scene, camera) == WW3D_ERROR_OK;
					const bool ended = rendered &&
						WW3D::End_Render(present_frames) == WW3D_ERROR_OK;
					frame_path_ok = began && rendered && ended;
					++frame_index;
					if (!frame_path_ok || (maximum_frames != 0 && frame_index >= maximum_frames)) {
						break;
					}
					if (render_options == NULL || render_options->update_camera == NULL) {
						break;
					}
					if (!render_options->update_camera(render_options->context, camera_control)) {
						result.render_loop_exit_requested = true;
						break;
					}
				} while (true);
				const RenegadeVitaRenderer::Statistics &statistics =
					RenegadeVitaRenderer::Get_Statistics();
				result.rendered_frames = statistics.frames;
				result.rendered_meshes = statistics.mesh_submissions;
				result.rendered_vertices = statistics.vertex_submissions;
				result.rendered_triangles = statistics.triangle_submissions;
				result.unsupported_render_objects = statistics.unsupported_submissions;
				result.rendered_geometry_checksum = statistics.geometry_checksum;
				result.original_scene_rendered = frame_path_ok &&
					result.rendered_frames > 0 && result.rendered_meshes > 0 &&
					result.rendered_vertices > 0 && result.rendered_triangles > 0;
			}
			scene->Remove_Render_Object(object);
			object->Release_Ref();
			camera->Release_Ref();
			scene->Release_Ref();
			if (WW3D::Is_Initted()) {
				WW3D::Shutdown();
			}
		}
		}
		_TheFileFactory = previous_file_factory;
	}
	if (asset_file != NULL) {
		factory_list.Return_File(asset_file);
	}

	Check(result, result.asset_manager_loaded,
		"original WW3DAssetManager Load_3D_Assets");
	Check(result, result.prototype_count >= 10,
		"original prototype registry populated");
	Check(result, result.render_object_created,
		"original RenderObj creation");
	Check(result, result.mesh_count >= 8,
		"original mesh object hierarchy");
	Check(result, result.vertex_count > 0 && result.polygon_count > 0,
		"original mesh semantic geometry");
	Check(result, result.render_hierarchy_pivots == result.hierarchy_pivots,
		"RenderObj hierarchy matches W3D hierarchy");
	Check(result, result.renderer_initialized,
		"Vita renderer boundary initialization");
	Check(result, result.original_scene_rendered,
		"original SimpleScene/Camera/WW3D render traversal");

	result.passed = result.failures == 0;
	if (result.passed) {
		strcpy(result.first_failure, "none");
	}
	return result;
}
