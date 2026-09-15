#include "vita_platform.h"
#include "vita_runtime_log.h"
#include "renegade_build_identity.h"

#include <psp2/io/fcntl.h>
#include <psp2/io/stat.h>

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

namespace {

const char *const kRetailRoot = "ux0:data/renegade/retail";
const char *const kLogPath = RENEGADE_BUILD_RUNTIME_LOG_PATH;
const char *const kRendererMilestone = RENEGADE_BUILD_CANDIDATE_LABEL;
unsigned g_renderer_breadcrumb_sequence = 0;

bool Is_Directory(const char *path)
{
	SceIoStat status = {};
	return sceIoGetstat(path, &status) >= 0 && SCE_S_ISDIR(status.st_mode);
}

bool Is_Regular_File(const char *path)
{
	SceIoStat status = {};
	return sceIoGetstat(path, &status) >= 0 && SCE_S_ISREG(status.st_mode);
}

bool Ensure_Directory(const char *path)
{
	if (Is_Directory(path)) {
		return true;
	}
	return sceIoMkdir(path, 0777) >= 0 && Is_Directory(path);
}

void Write_Line(SceUID file, const char *format, ...)
{
	char line[256];
	va_list arguments;
	va_start(arguments, format);
	const int count = vsnprintf(line, sizeof(line), format, arguments);
	va_end(arguments);
	if (count <= 0) {
		return;
	}
	const unsigned length = static_cast<unsigned>(
		count < static_cast<int>(sizeof(line)) ? count : static_cast<int>(sizeof(line) - 1));
	sceIoWrite(file, line, length);
}

} // namespace

int Vita_Append_A22_Runtime_Breadcrumb(const char *subsystem,
	const char *format, ...)
{
	char message[512];
	va_list arguments;
	va_start(arguments, format);
	const int count = vsnprintf(message, sizeof(message), format, arguments);
	va_end(arguments);
	if (count <= 0) {
		return -1;
	}

	const SceUID file = sceIoOpen(kLogPath,
		SCE_O_WRONLY | SCE_O_CREAT | SCE_O_APPEND, 0666);
	if (file < 0) {
		return file;
	}

	const unsigned sequence = ++g_renderer_breadcrumb_sequence;
	char line[640];
	const int line_count = snprintf(line, sizeof(line),
		"[%s %s %03u] %s\n", kRendererMilestone,
		subsystem != NULL ? subsystem : "renderer", sequence, message);
	int result = 0;
	if (line_count > 0) {
		const unsigned length = static_cast<unsigned>(
			line_count < static_cast<int>(sizeof(line)) ? line_count :
			static_cast<int>(sizeof(line) - 1));
		unsigned offset = 0;
		while (offset < length) {
			const int written = sceIoWrite(file, line + offset, length - offset);
			if (written < 0) {
				result = written;
				break;
			}
			if (written == 0) {
				result = -2;
				break;
			}
			offset += static_cast<unsigned>(written);
		}
	}
	const int sync_result = sceIoSyncByFd(file, 0);
	if (result >= 0 && sync_result < 0) {
		result = sync_result;
	}
	const int close_result = sceIoClose(file);
	if (result >= 0 && close_result < 0) {
		result = close_result;
	}
	return result;
}

const char *Vita_Pass_Fail(bool value)
{
	return value ? "PASS" : "FAIL";
}

VitaBootstrapStatus Vita_Initialize_Filesystem()
{
	VitaBootstrapStatus status = {};
	const char *const writable_directories[] = {
		"ux0:data/renegade",
		"ux0:data/renegade/user",
		"ux0:data/renegade/user/save",
		"ux0:data/renegade/user/saves",
		"ux0:data/renegade/user/config",
		"ux0:data/renegade/user/logs",
		"ux0:data/renegade/user/screenshots",
		"ux0:data/renegade/cache",
		"ux0:data/renegade/mods",
	};

	for (unsigned i = 0; i < sizeof(writable_directories) / sizeof(writable_directories[0]); ++i) {
		if (!Ensure_Directory(writable_directories[i])) {
			++status.directory_errors;
		}
	}
	status.user_tree_ready = status.directory_errors == 0;
	status.retail_root_found = Is_Directory(kRetailRoot);
	status.data_directory_found = Is_Directory("ux0:data/renegade/retail/Data");
	status.always_dat_found = Is_Regular_File("ux0:data/renegade/retail/Data/always.dat");
	status.always2_dat_found = Is_Regular_File("ux0:data/renegade/retail/Data/Always2.dat");
	status.always_dbs_found = Is_Regular_File("ux0:data/renegade/retail/Data/always.dbs");
	status.log_result = -1;
	return status;
}

int Vita_Write_A22_Startup_Log(const VitaBootstrapStatus &status,
	const WestwoodSelfTestResult &self_test,
	const A21FilesystemSelfTestResult &filesystem,
	int framebuffer_result)
{
	const SceUID file = sceIoOpen(kLogPath, SCE_O_WRONLY | SCE_O_CREAT | SCE_O_TRUNC, 0666);
	if (file < 0) {
		return file;
	}

	Write_Line(file, "Renegade Vita A2.2 Original Visible Runtime\n");
	Write_Line(file, "Stage: pre-render startup breadcrumb\n");
	Write_Line(file, "A2.0 REGRESSION\n");
	Write_Line(file, "Native framebuffer: %s (%08X)\n",
		Vita_Pass_Fail(framebuffer_result >= 0), static_cast<unsigned>(framebuffer_result));
	Write_Line(file, "Westwood wwbitpack self-test: %s (%u checks, %u failures)\n",
		Vita_Pass_Fail(self_test.passed), self_test.checks, self_test.failures);
	Write_Line(file, "First self-test failure: %s\n", self_test.first_failure);
	Write_Line(file, "Writable user tree: %s (directory errors: %d)\n",
		Vita_Pass_Fail(status.user_tree_ready), status.directory_errors);
	Write_Line(file, "Retail root: %s\n", Vita_Pass_Fail(status.retail_root_found));
	Write_Line(file, "Data directory: %s\n", Vita_Pass_Fail(status.data_directory_found));
	Write_Line(file, "always.dat: %s\n", Vita_Pass_Fail(status.always_dat_found));
	Write_Line(file, "Always2.dat: %s\n", Vita_Pass_Fail(status.always2_dat_found));
	Write_Line(file, "always.dbs: %s\n", Vita_Pass_Fail(status.always_dbs_found));
	Write_Line(file, "A2.1 FILESYSTEM/ARCHIVE\n");
	Write_Line(file, "Overall: %s (%u checks, %u failures; first: %s)\n",
		Vita_Pass_Fail(filesystem.passed), filesystem.checks, filesystem.failures,
		filesystem.first_failure);
	Write_Line(file, "Path translation/case resolution: %s\n",
		Vita_Pass_Fail(filesystem.path_translation));
	Write_Line(file, "Traversal rejection: %s\n",
		Vita_Pass_Fail(filesystem.traversal_rejected));
	Write_Line(file, "Writes routed outside retail: %s\n",
		Vita_Pass_Fail(filesystem.write_routed_outside_retail));
	Write_Line(file, "Original FileClass available/read: %s/%s\n",
		Vita_Pass_Fail(filesystem.original_file_available),
		Vita_Pass_Fail(filesystem.original_file_read));
	Write_Line(file, "Original MixFileFactory valid/enumerated: %s/%s\n",
		Vita_Pass_Fail(filesystem.archive_valid),
		Vita_Pass_Fail(filesystem.archive_enumerated));
	Write_Line(file, "Archive entries: %u\n", filesystem.archive_entries);
	Write_Line(file, "Known entry dsp_o2tank.w3d found/read: %s/%s\n",
		Vita_Pass_Fail(filesystem.known_entry_found),
		Vita_Pass_Fail(filesystem.known_entry_read));
	Write_Line(file, "Known entry size/read/prefix: %u/%u/%08X\n",
		filesystem.known_entry_size, filesystem.known_entry_bytes_read,
		filesystem.known_entry_prefix);
	Write_Line(file, "Original FileFactoryList read: %s\n",
		Vita_Pass_Fail(filesystem.factory_list_read));
	Write_Line(file, "Resolved archive path: %s\n", filesystem.resolved_archive_path);
	Write_Line(file, "Original source translation units compiled: %d\n",
		RENEGADE_VITA_A22_ORIGINAL_SOURCES);
	Write_Line(file, "Vita port/validation translation units compiled: %d\n",
		RENEGADE_VITA_A22_PORT_SOURCES);
	Write_Line(file, "A2.2 renderer stage: STARTING\n");
	const int close_result = sceIoClose(file);
	return close_result;
}

int Vita_Append_A22_Result_Log(const A22W3DSelfTestResult &w3d)
{
	const SceUID file = sceIoOpen(kLogPath,
		SCE_O_WRONLY | SCE_O_CREAT | SCE_O_APPEND, 0666);
	if (file < 0) {
		return file;
	}

	Write_Line(file, "\nA2.2 ORIGINAL W3D / WW3D VISIBLE RUNTIME\n");
	Write_Line(file, "Overall: %s (%u checks, %u failures; first: %s)\n",
		Vita_Pass_Fail(w3d.passed), w3d.checks, w3d.failures, w3d.first_failure);
	Write_Line(file, "Original ChunkLoadClass: %s (top-level chunks: %u)\n",
		Vita_Pass_Fail(w3d.original_chunk_loader), w3d.top_level_chunk_count);
	for (unsigned index = 0; index < w3d.top_level_chunk_count && index < 16; ++index) {
		Write_Line(file, "Top chunk %u: id=%08X length=%u\n", index,
			w3d.top_level_ids[index], w3d.top_level_lengths[index]);
	}
	Write_Line(file, "Hierarchy: %s (pivots: %u; header: %s)\n",
		w3d.hierarchy_name, w3d.hierarchy_pivots,
		Vita_Pass_Fail(w3d.hierarchy_header_read));
	Write_Line(file, "Original WW3DAssetManager load: %s\n",
		Vita_Pass_Fail(w3d.asset_manager_loaded));
	Write_Line(file, "Prototype registry: %u entries\n", w3d.prototype_count);
	for (unsigned index = 0; index < w3d.prototype_count && index < 16; ++index) {
		Write_Line(file, "Prototype %u: class=%d name=%s\n", index,
			w3d.prototype_class_ids[index], w3d.prototype_names[index]);
	}
	Write_Line(file, "Original RenderObj: %s (name=%s; class=%d; nodes=%u)\n",
		Vita_Pass_Fail(w3d.render_object_created), w3d.render_object_name,
		w3d.render_object_class_id, w3d.render_object_subobjects);
	Write_Line(file, "Mesh fingerprint: meshes=%u vertices=%u polygons=%u materials=%u textures=%u\n",
		w3d.mesh_count, w3d.vertex_count, w3d.polygon_count,
		w3d.material_count, w3d.texture_count);
	Write_Line(file, "Render hierarchy: %s/%u\n",
		w3d.render_hierarchy_name, w3d.render_hierarchy_pivots);
	Write_Line(file, "Sphere: center=(%.6f,%.6f,%.6f) radius=%.6f\n",
		w3d.bounding_sphere_center[0], w3d.bounding_sphere_center[1],
		w3d.bounding_sphere_center[2], w3d.bounding_sphere_radius);
	Write_Line(file, "AABox: center=(%.6f,%.6f,%.6f) extent=(%.6f,%.6f,%.6f)\n",
		w3d.bounding_box_center[0], w3d.bounding_box_center[1],
		w3d.bounding_box_center[2], w3d.bounding_box_extent[0],
		w3d.bounding_box_extent[1], w3d.bounding_box_extent[2]);
	Write_Line(file, "Vita renderer initialization: %s\n",
		Vita_Pass_Fail(w3d.renderer_initialized));
	Write_Line(file, "Original SimpleScene/Camera traversal: %s\n",
		Vita_Pass_Fail(w3d.original_scene_rendered));
	Write_Line(file, "Rendered frames/meshes/vertices/triangles: %u/%u/%u/%u\n",
		w3d.rendered_frames, w3d.rendered_meshes,
		w3d.rendered_vertices, w3d.rendered_triangles);
	Write_Line(file, "Unsupported submissions: %u\n", w3d.unsupported_render_objects);
	Write_Line(file, "Geometry checksum: %08X\n", w3d.rendered_geometry_checksum);
	Write_Line(file, "START exit request observed: %s\n",
		Vita_Pass_Fail(w3d.render_loop_exit_requested));
	return sceIoClose(file);
}
