#include "wwbitpack_selftest.h"
#include "a21_filesystem_selftest.h"
#include "a22_w3d_selftest.h"

#include <stdio.h>

int main(int argc, char **argv)
{
	const WestwoodSelfTestResult result = Run_Westwood_Bitpack_Self_Test();
	printf("wwbitpack host self-test: %s (%u checks, %u failures; first=%s)\n",
		result.passed ? "PASS" : "FAIL", result.checks, result.failures, result.first_failure);
	if (!result.passed) {
		return 1;
	}
	if (argc != 5) {
		fprintf(stderr, "usage: %s RETAIL_ROOT USER_ROOT CACHE_ROOT MODS_ROOT\n", argv[0]);
		return 2;
	}
	const RenegadePathRoots roots = { argv[1], argv[2], argv[3], argv[4] };
	const A21FilesystemSelfTestResult filesystem = Run_A21_Filesystem_Self_Test(roots);
	printf("A2.1 original filesystem/MIX self-test: %s "
		"(%u checks, %u failures; entries=%u; known-size=%u; read=%u; prefix=%08X; first=%s)\n",
		filesystem.passed ? "PASS" : "FAIL", filesystem.checks, filesystem.failures,
		filesystem.archive_entries, filesystem.known_entry_size,
		filesystem.known_entry_bytes_read, filesystem.known_entry_prefix,
		filesystem.first_failure);
	printf("Resolved retail archive: %s\n", filesystem.resolved_archive_path);
	if (!filesystem.passed) {
		return 1;
	}
	const A22W3DSelfTestResult w3d = Run_A22_W3D_Self_Test(roots);
	printf("A2.2 original W3D chunk traversal: %s "
		"(%u checks, %u failures; top-level=%u; first-id=%08X; "
		"hierarchy=%s; pivots=%u; first=%s)\n",
		w3d.passed ? "PASS" : "FAIL", w3d.checks, w3d.failures,
		w3d.top_level_chunk_count, w3d.top_level_ids[0],
		w3d.hierarchy_name, w3d.hierarchy_pivots, w3d.first_failure);
	for (unsigned index = 0; index < w3d.top_level_chunk_count && index < 16; ++index) {
		printf("  top chunk %u: id=%08X length=%u\n", index,
			w3d.top_level_ids[index], w3d.top_level_lengths[index]);
	}
	printf("A2.2 original asset manager: %s (prototypes=%u; object=%s; class=%d; "
		"nodes=%u; meshes=%u; vertices=%u; polygons=%u; materials=%u; textures=%u; "
		"hierarchy=%s/%u)\n",
		w3d.asset_manager_loaded && w3d.render_object_created ? "PASS" : "FAIL",
		w3d.prototype_count, w3d.render_object_name, w3d.render_object_class_id,
		w3d.render_object_subobjects, w3d.mesh_count, w3d.vertex_count,
		w3d.polygon_count, w3d.material_count, w3d.texture_count,
		w3d.render_hierarchy_name, w3d.render_hierarchy_pivots);
	for (unsigned index = 0; index < w3d.prototype_count && index < 16; ++index) {
		printf("  prototype %u: class=%d name=%s\n", index,
			w3d.prototype_class_ids[index], w3d.prototype_names[index]);
	}
	printf("  sphere: center=(%.6f, %.6f, %.6f) radius=%.6f\n",
		w3d.bounding_sphere_center[0], w3d.bounding_sphere_center[1],
		w3d.bounding_sphere_center[2], w3d.bounding_sphere_radius);
	printf("  box: center=(%.6f, %.6f, %.6f) extent=(%.6f, %.6f, %.6f)\n",
		w3d.bounding_box_center[0], w3d.bounding_box_center[1],
		w3d.bounding_box_center[2], w3d.bounding_box_extent[0],
		w3d.bounding_box_extent[1], w3d.bounding_box_extent[2]);
	printf("A2.2 original Scene/Camera traversal: %s "
		"(frames=%u; meshes=%u; vertices=%u; triangles=%u; unsupported=%u; checksum=%08X)\n",
		w3d.original_scene_rendered ? "PASS" : "FAIL", w3d.rendered_frames,
		w3d.rendered_meshes, w3d.rendered_vertices, w3d.rendered_triangles,
		w3d.unsupported_render_objects, w3d.rendered_geometry_checksum);
	return w3d.passed ? 0 : 1;
}
