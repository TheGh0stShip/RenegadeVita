#pragma once

#include "renegade_vita_bench_hooks.h"
#include "camera.h"
#include "matrix3d.h"
#include "vector3.h"

/*
** Called by CombatManager::Think directly after the original
** CCameraClass::Update in its non-host-model branch. When a tutorial
** benchmark viewpoint is armed, the original camera object receives a fixed
** pose through its own CameraClass::Set_Transform at the exact point where the
** original update writes it, so everything downstream in the same original
** frame (Post_Think, sound environment, sky/background, weather, HUD,
** visibility and rendering) consumes that pose. Star targeting was already
** computed by the original update from the player camera and is unchanged.
** FOV and clip planes are fixed too (the original update rewrites them every
** frame, so nothing persists past an armed frame); the vertical FOV follows
** the camera's existing aspect ratio exactly as the original profile path.
** Inert (one load and branch) when not armed.
*/
inline void Renegade_Vita_Bench_Apply_Camera(CameraClass &camera)
{
	RenegadeVitaBenchHooks &hooks = g_renegade_vita_bench_hooks;
	if (!hooks.camera_armed) return;
	Matrix3D transform(1);
	transform.Look_At(
		Vector3(hooks.camera_position[0], hooks.camera_position[1], hooks.camera_position[2]),
		Vector3(hooks.camera_target[0], hooks.camera_target[1], hooks.camera_target[2]),
		0.0f);
	camera.Set_Transform(transform);
	camera.Set_View_Plane(hooks.camera_horizontal_fov);
	camera.Set_Clip_Planes(hooks.camera_near_clip, hooks.camera_far_clip);
	++hooks.camera_applied;
}
