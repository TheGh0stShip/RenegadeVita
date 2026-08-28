#include "renegade_vita_input_contract.h"

#include <stdio.h>

namespace {

void Check(bool condition, const char *name, unsigned &checks, unsigned &failures)
{
	++checks;
	if (!condition) {
		++failures;
		fprintf(stderr, "Vita input contract failed: %s\n", name);
	}
}

} // namespace

int main()
{
	unsigned checks = 0U;
	unsigned failures = 0U;
	using namespace RenegadeVitaInput;
	Check(To_DirectInput_Axis(128U) == 0, "128 is exact neutral", checks, failures);
	Check(To_DirectInput_Axis(108U) < 0 && To_DirectInput_Axis(108U) > -1000,
		"negative partial tilt remains bounded", checks, failures);
	Check(To_DirectInput_Axis(146U) == 0 && To_DirectInput_Axis(108U) < 0,
		"dead-zone boundary is stable on both signs", checks, failures);
	Check(To_DirectInput_Axis(160U) > 100 && To_DirectInput_Axis(160U) < 200,
		"quarter positive tilt is smoothly remapped", checks, failures);
	Check(To_DirectInput_Axis(64U) < -400 && To_DirectInput_Axis(64U) > -500,
		"half negative tilt is smoothly remapped", checks, failures);
	Check(To_DirectInput_Axis(0U) == DIRECTINPUT_AXIS_MIN,
		"negative endpoint maps to original minimum", checks, failures);
	Check(To_DirectInput_Axis(255U) == DIRECTINPUT_AXIS_MAX,
		"positive endpoint maps to original maximum", checks, failures);
	Check(To_DirectInput_Axis(0U) + To_DirectInput_Axis(255U) == 0,
		"endpoints are symmetric despite 127/128 hardware range", checks, failures);
	Check(To_DirectInput_Axis(128U) != 32767,
		"logical axis cannot leak device-scale range", checks, failures);
	Check(To_DirectInput_Axis(147U) == 0 && To_DirectInput_Axis(109U) == 0,
		"inside device-neutral band remains zero", checks, failures);
	Check(To_DirectInput_Axis(148U) > 0 && To_DirectInput_Axis(108U) < 0,
		"outside device-neutral band preserves both signs", checks, failures);
	int32_t prior = DIRECTINPUT_AXIS_MIN;
	bool monotonic = true;
	for (unsigned value = 0U; value <= 255U; ++value) {
		const int32_t logical = To_DirectInput_Axis(static_cast<uint8_t>(value));
		if (logical < prior || logical < DIRECTINPUT_AXIS_MIN ||
			logical > DIRECTINPUT_AXIS_MAX || logical == 32767) monotonic = false;
		prior = logical;
	}
	Check(monotonic, "full device range is monotonic and bounded", checks, failures);
	const AxisSample half = Sample_Device_Axis(192U);
	Check(half.raw == 192U && half.normalized > 0.40f && half.normalized < 0.42f &&
		half.logical > 400 && half.logical < 420,
		"sample retains raw normalized and logical contracts", checks, failures);
	const StickSample diagonal = Sample_Device_Stick(255U, 255U);
	const float diagonal_length = sqrtf(diagonal.x.normalized * diagonal.x.normalized +
		diagonal.y.normalized * diagonal.y.normalized);
	Check(diagonal_length > 0.99f && diagonal_length <= 1.001f,
		"diagonal full tilt is normalized", checks, failures);
	Check(diagonal.x.logical > 700 && diagonal.y.logical > 700,
		"diagonal retains both directions", checks, failures);
	const StickSample physical_up = Sample_Device_Stick(128U, 0U);
	const StickSample physical_down = Sample_Device_Stick(128U, 255U);
	Check(physical_up.y.logical < 0 && physical_down.y.logical > 0,
		"device Y preserves DirectInput up/down slider orientation", checks, failures);
	const int32_t camera_60 = To_Camera_Mouse_Delta(1.0f, 1.0f / 60.0f);
	const int32_t camera_30 = To_Camera_Mouse_Delta(1.0f, 1.0f / 30.0f);
	Check(camera_60 > 0 && camera_30 >= camera_60 * 2 &&
		camera_30 <= camera_60 * 2 + 1,
		"camera delta scales with elapsed time", checks, failures);
	Check(To_Camera_Mouse_Delta(1.0f, 1.0f) ==
		To_Camera_Mouse_Delta(1.0f, MAX_INPUT_FRAME_SECONDS),
		"camera hitch input is bounded", checks, failures);
	Check(To_Camera_Mouse_Delta(0.2f, 1.0f / 60.0f) <
		To_Camera_Mouse_Delta(0.5f, 1.0f / 60.0f),
		"nonlinear camera response preserves fine low-deflection control",
		checks, failures);
	Check(To_Camera_Mouse_Delta(1.0f, 1.0f / 60.0f,
		DEFAULT_CAMERA_RESPONSE.vertical_scale) <
		To_Camera_Mouse_Delta(1.0f, 1.0f / 60.0f,
		DEFAULT_CAMERA_RESPONSE.horizontal_scale),
		"vertical response has an independent conservative scale", checks, failures);
	Check(To_Camera_Mouse_Delta(0.6f, 1.0f / 60.0f, 1.0f, true) ==
		-To_Camera_Mouse_Delta(0.6f, 1.0f / 60.0f),
		"optional Y inversion reverses only the platform response", checks, failures);
	Check(To_Camera_Mouse_Delta(physical_up.y.normalized, 1.0f / 60.0f,
		DEFAULT_CAMERA_RESPONSE.vertical_scale, DEFAULT_CAMERA_RESPONSE.invert_y) > 0 &&
		To_Camera_Mouse_Delta(physical_down.y.normalized, 1.0f / 60.0f,
		DEFAULT_CAMERA_RESPONSE.vertical_scale, DEFAULT_CAMERA_RESPONSE.invert_y) < 0,
		"default Vita camera response corrects physical up/down orientation", checks, failures);
	printf("A3.2 Vita controller axis-contract: %s (%u checks, %u failures)\n",
		failures == 0U ? "PASS" : "FAIL", checks, failures);
	return failures == 0U ? 0 : 1;
}
