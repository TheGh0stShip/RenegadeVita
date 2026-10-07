#pragma once

#include <stdint.h>

/*
** Dev-only fixed tutorial benchmark (tutorial-bench-v1.flag, prefix RVTB1).
**
** Shared state between the native frame loop (owner), the original Combat
** camera seam (CombatManager::Think, directly after the original
** CCameraClass::Update) and the DirectInput boundary. The native loop arms it
** only for the duration of one A31_Interactive_Run_Simulation_Frame call while
** a benchmark viewpoint is held, and disarms it as soon as that call returns.
** With the flag absent nothing ever sets these fields, so every reader stays
** on its original path.
*/
struct RenegadeVitaBenchHooks
{
	// Replace the original camera transform with a Look_At of this pose.
	bool camera_armed;
	// Neutral controller/touch below DirectInput (START stays live).
	bool input_suppressed;
	float camera_position[3];
	float camera_target[3];
	// Horizontal FOV (radians; vertical follows the camera aspect) and clip
	// planes. The original update rewrites all three every frame, so the
	// fixed values never outlive an armed frame.
	float camera_horizontal_fov;
	float camera_near_clip;
	float camera_far_clip;
	// Original camera updates overridden so far (monotonic, wraps).
	uint32_t camera_applied;
};

// C++17 inline variable: one definition shared by every translation unit.
inline RenegadeVitaBenchHooks g_renegade_vita_bench_hooks = {};
