#include "world_render_callback.h"

#include "camera.h"
#include "matrix3d.h"
#include "pscene.h"
#include "ww3d.h"
#include "ww3d_vita_renderer.h"

#include <stdio.h>

namespace {

void Render_Breadcrumb(const char *stage)
{
	fprintf(stderr, "A3.0 original-world render stage: %s\n", stage);
	fflush(stderr);
}

} // namespace

bool A30_Render_Loaded_World(void *context, PhysicsSceneClass &scene,
	WW3DAssetManager &asset_manager, const A30WorldRuntimeFingerprint &world)
{
	(void)asset_manager;
	(void)world;
	A30HostWorldRenderResult *result =
		static_cast<A30HostWorldRenderResult *>(context);
	if (result == NULL) {
		return false;
	}
	*result = {};
	result->attempted = true;
	Render_Breadcrumb("callback entry");

	Vector3 level_min;
	Vector3 level_max;
	scene.Get_Level_Extents(level_min, level_max);
	const Vector3 center = (level_min + level_max) * 0.5f;
	const Vector3 span = level_max - level_min;
	const float largest_span =
		span.X > span.Y ? (span.X > span.Z ? span.X : span.Z) :
		(span.Y > span.Z ? span.Y : span.Z);

	/* Temporary development camera only: its position and clip depth are
	** derived from the original loaded world extents. The scene contents,
	** culling, traversal and submissions remain wholly Westwood-owned. */
	const Vector3 camera_position(center.X,
		center.Y - largest_span * 0.72f,
		center.Z + largest_span * 0.32f);
	result->camera_position[0] = camera_position.X;
	result->camera_position[1] = camera_position.Y;
	result->camera_position[2] = camera_position.Z;
	result->camera_target[0] = center.X;
	result->camera_target[1] = center.Y;
	result->camera_target[2] = center.Z;
	result->near_clip = 0.5f;
	result->far_clip = largest_span * 4.0f;

	CameraClass *camera = new CameraClass;
	camera->Set_Aspect_Ratio(960.0f / 544.0f);
	camera->Set_Clip_Planes(result->near_clip, result->far_clip);
	Matrix3D camera_transform(1);
	camera_transform.Look_At(camera_position, center, 0.0f);
	camera->Set_Transform(camera_transform);
	result->camera_initialized = true;
	Render_Breadcrumb("CameraClass initialized from world extents");

	RenegadeVitaRenderer::Reset_Statistics();
	WW3D::Sync(16U);

	Render_Breadcrumb("before PhysicsScene::Pre_Render_Processing");
	scene.Pre_Render_Processing(*camera);
	result->pre_render_completed = true;
	Render_Breadcrumb("after PhysicsScene::Pre_Render_Processing");
	Render_Breadcrumb("before WW3D::Begin_Render");
	result->begin_render_completed =
		WW3D::Begin_Render(true, true, Vector3(0.035f, 0.055f, 0.085f)) ==
		WW3D_ERROR_OK;
	Render_Breadcrumb("after WW3D::Begin_Render");
	if (result->begin_render_completed) {
		Render_Breadcrumb("before WW3D::Render(PhysicsScene,Camera)");
		result->scene_render_completed =
			WW3D::Render(&scene, camera) == WW3D_ERROR_OK;
		Render_Breadcrumb("after WW3D::Render(PhysicsScene,Camera)");
		/* End the original frame even if traversal reports an error so its
		** renderer-owned per-frame state remains balanced. */
		Render_Breadcrumb("before WW3D::End_Render");
		result->end_render_completed =
			WW3D::End_Render(false) == WW3D_ERROR_OK;
		Render_Breadcrumb("after WW3D::End_Render");
	}
	Render_Breadcrumb("before PhysicsScene::Post_Render_Processing");
	scene.Post_Render_Processing();
	result->post_render_completed = true;
	Render_Breadcrumb("after PhysicsScene::Post_Render_Processing");

	const RenegadeVitaRenderer::Statistics &statistics =
		RenegadeVitaRenderer::Get_Statistics();
	result->frames = statistics.frames;
	result->mesh_submissions = statistics.mesh_submissions;
	result->vertex_submissions = statistics.vertex_submissions;
	result->triangle_submissions = statistics.triangle_submissions;
	result->geometry_checksum = statistics.geometry_checksum;
	result->indexed_submissions = statistics.indexed_submissions;
	result->indexed_vertex_references = statistics.indexed_vertex_references;
	result->indexed_triangle_submissions =
		statistics.indexed_triangle_submissions;
	result->indexed_geometry_checksum = statistics.indexed_geometry_checksum;
	result->rejected_indexed_submissions =
		statistics.rejected_indexed_submissions;
	result->unsupported_submissions = statistics.unsupported_submissions;
	result->frame_path_completed = result->camera_initialized &&
		result->pre_render_completed && result->begin_render_completed &&
		result->scene_render_completed && result->end_render_completed &&
		result->post_render_completed && result->frames == 1U &&
		(result->mesh_submissions > 0U || result->indexed_submissions > 0U);

	camera->Release_Ref();
	return result->frame_path_completed;
}
