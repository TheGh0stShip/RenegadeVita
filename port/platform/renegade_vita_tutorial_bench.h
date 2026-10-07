#pragma once

/*
** Dev-only fixed tutorial performance benchmark (RVTB1).
**
** Flag file ux0:data/renegade/user/config/tutorial-bench-v1.flag, exactly one
** line of 8 bytes:
**   "RVTB1 0\n"        off (same as absent)
**   "RVTB1 1\n".."5\n" run 1..5 passes of the fixed viewpoint route
**   "RVTB1 C\n"        one pass plus one capture bundle per viewpoint
** Anything else is rejected and leaves the benchmark off.
**
** With M00_Tutorial.mix loaded and the flag on, the native frame loop waits
** for original player control plus a quiet period (no active original
** conversation), then holds the ORIGINAL Combat camera at each viewpoint below
** for SETTLE_FRAMES + MEASURE_FRAMES frames. The pose is applied by
** CombatManager::Think through CameraClass::Set_Transform directly after the
** original CCameraClass::Update (renegade_vita_bench_camera.h); gameplay input
** is neutral below DirectInput for the same frames (START stays live: it opens
** the original pause menu and aborts the run with partial results). The
** original simulation, scripts, AI and rendering keep running unchanged: there
** is no separate loop and no frozen world.
**
** Per viewpoint the controller records frame interval (frame start to next
** frame start), work time, simulation/render split and the renderer's
** submission counters, then logs p50/p95/p99/worst and a correctness
** fingerprint, and appends CSV rows under ux0:data/renegade/user/logs/.
** This header is engine-free; the runtime passes counters and pose in.
** The percentile, FNV and mode rules are mirrored by
** tools/test_tutorial_bench.py and tools/compare_tutorial_bench.py.
*/

#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "renegade_vita_bench_hooks.h"

namespace RenegadeVitaTutorialBench {

// Plain unsigned (32-bit on the ILP32 target and on LP64 hosts) keeps every
// printf field an exact %u/%X match without per-argument casts.
static_assert(sizeof(unsigned) == 4U, "tutorial bench words must be 32-bit");

constexpr unsigned VERSION = 1U;
constexpr unsigned SETTLE_FRAMES = 30U;
constexpr unsigned MEASURE_FRAMES = 120U;
constexpr unsigned HOLD_FRAMES = SETTLE_FRAMES + MEASURE_FRAMES;
constexpr unsigned MAX_PASSES = 5U;
constexpr unsigned QUIET_FRAMES_REQUIRED = 120U;
constexpr unsigned MIN_FRAMES_AFTER_CONTROL = 300U;
constexpr unsigned READY_TIMEOUT_FRAMES = 5400U;
constexpr unsigned LONG_INTERVAL_US = 1000000U;
constexpr unsigned MAX_RUN_FILES = 99U;
constexpr unsigned POSE_WORDS = 16U;
constexpr unsigned COUNTER_COUNT = 8U;
constexpr unsigned FINGERPRINT_COUNTERS = 4U;

// Per-frame deltas of RenegadeVitaRenderer::Statistics. MeshClass counters
// are incremented before static-cache / vertex-array path selection, so the
// first four stay comparable across RVSM1/RVVA1/RVGS1 A/B runs.
enum Counter : unsigned {
	COUNTER_MESHES = 0U,
	COUNTER_VERTICES,
	COUNTER_TRIANGLES,
	COUNTER_MATERIAL_PASSES,
	COUNTER_INDEXED_DRAWS,
	COUNTER_INDEXED_TRIANGLES,
	COUNTER_TEXTURE_BINDS,
	COUNTER_STATE_CHANGES,
};

enum FrameFlag : unsigned {
	FLAG_CAMERA_NOT_APPLIED = 1U,  // original hook did not run (cinematic host, Combat idle)
	FLAG_FRAME_GAP = 2U,           // an armed frame never completed (pause, restart)
	FLAG_POSE_CHANGED = 4U,        // camera readback differs from the hold reference
	FLAG_COUNTER_RESET = 8U,       // renderer statistics went backwards
	FLAG_LONG_INTERVAL = 16U,      // informational: interval over LONG_INTERVAL_US
	FLAG_CONVERSATION = 32U,       // informational: an original conversation was active
	FLAG_INVALIDATING = FLAG_CAMERA_NOT_APPLIED | FLAG_FRAME_GAP |
		FLAG_POSE_CHANGED | FLAG_COUNTER_RESET,
};

struct Viewpoint
{
	const char *name;
	float position[3];
	float target[3];
};

/*
** M00_Tutorial.mix world coordinates, in tutorial route order. Positions are
** derived from walkable player positions in the physical Dev134 M00 run,
** Mission00.cpp script coordinates and tut_lm015.w3d mesh bounds (see the
** TUT_R1_TUTORIAL_BENCHMARK report). M00 has no Tiberium field (the only
** Tiberium asset is the refinery's ref_tib_dump), so the refinery's east
** dump/road side stands in for it. Changing any entry changes every
** fingerprint: bump VERSION and record it.
*/
static const Viewpoint kViewpoints[] = {
	{"spawn_course_start",     {-57.00f, -43.00f,  2.80f}, {-50.00f, -20.00f,  1.50f}},
	{"logan_course_overlook",  {-40.50f, -42.00f,  7.50f}, {-55.00f, -14.00f,  1.00f}},
	{"agt_keycard_yard",       {-14.90f,  34.00f,  2.40f}, {-11.50f,  18.00f,  4.00f}},
	{"sydney_agt_interior",    {-11.90f,  25.13f, -8.33f}, {-11.45f,  20.14f, -8.60f}},
	{"gunner_range_lane",      {-34.00f,  76.00f,  2.65f}, {-34.56f,  52.91f,  1.84f}},
	{"hotwire_vehicle_yard",   {  8.00f, -48.00f,  5.00f}, {-10.00f, -30.00f,  1.50f}},
	{"refinery_exterior",      { 18.90f,  33.00f,  2.20f}, { 25.00f,  14.00f,  8.00f}},
	{"mobius_refinery_interior", {22.97f,  16.95f, -8.35f}, { 29.63f,  11.98f, -8.30f}},
	{"refinery_tib_dump_east", { 51.00f,  26.00f,  3.00f}, { 42.50f,  16.00f,  2.50f}},
	{"petrova_power_interior", {-45.61f,  19.48f, -6.36f}, {-43.23f,  25.66f, -6.80f}},
	{"base_overview_elevated", {  0.00f, -50.00f, 25.00f}, {-10.00f,  20.00f,  2.00f}},
};

constexpr unsigned VIEWPOINT_COUNT =
	static_cast<unsigned>(sizeof(kViewpoints) / sizeof(kViewpoints[0]));

// Original cameras.ini [Default] profile FOV (75 degrees, horizontal; the
// vertical FOV follows the camera aspect) and CCameraClass CCAMERA_NEARZ /
// CCAMERA_FARZ, so first/third-person state cannot change the benchmark view.
static const float kHorizontalFovRadians = 1.30899694f;
static const float kNearClip = 0.26f;
static const float kFarClip = 300.0f;

static const char *const kFlagPath = "ux0:data/renegade/user/config/tutorial-bench-v1.flag";
static const char *const kLogDirectory = "ux0:data/renegade/user/logs";

enum FlagStatus : unsigned {
	FLAG_STATUS_ABSENT = 0U,
	FLAG_STATUS_OFF,
	FLAG_STATUS_ON,
	FLAG_STATUS_REJECTED,
};

struct FlagConfig
{
	FlagStatus status;
	unsigned passes;
	bool capture;
};

inline FlagConfig Parse_Flag(const char *bytes, size_t size)
{
	FlagConfig config = {FLAG_STATUS_REJECTED, 0U, false};
	if (bytes == NULL || size != 8U || memcmp(bytes, "RVTB1 ", 6U) != 0 || bytes[7] != '\n') {
		return config;
	}
	const char value = bytes[6];
	if (value == '0') {
		config.status = FLAG_STATUS_OFF;
	} else if (value >= '1' && value <= static_cast<char>('0' + MAX_PASSES)) {
		config.status = FLAG_STATUS_ON;
		config.passes = static_cast<unsigned>(value - '0');
	} else if (value == 'C') {
		config.status = FLAG_STATUS_ON;
		config.passes = 1U;
		config.capture = true;
	}
	return config;
}

inline FlagConfig Read_Flag_File(const char *path = kFlagPath)
{
	FILE *file = fopen(path, "rb");
	if (file == NULL) {
		const FlagConfig absent = {FLAG_STATUS_ABSENT, 0U, false};
		return absent;
	}
	char value[9] = {};
	const size_t size = fread(value, 1U, sizeof(value), file);
	const bool read_ok = !ferror(file);
	fclose(file);
	return Parse_Flag(value, read_ok ? size : 0U);
}

// Ascending insertion sort; inputs are at most VIEWPOINT_COUNT * MEASURE_FRAMES
// values and sorting happens only between holds, never inside a measured frame.
inline void Sort_Ascending(unsigned *values, unsigned count)
{
	for (unsigned index = 1U; index < count; ++index) {
		const unsigned value = values[index];
		unsigned cursor = index;
		while (cursor > 0U && values[cursor - 1U] > value) {
			values[cursor] = values[cursor - 1U];
			--cursor;
		}
		values[cursor] = value;
	}
}

// Nearest-rank percentile of an ascending array (same rule as the capture
// telemetry summary): rank = ceil(percentile * count / 100), clamped to 1..count.
inline unsigned Nearest_Rank(const unsigned *sorted, unsigned count, unsigned percentile)
{
	if (count == 0U) return 0U;
	unsigned rank = (percentile * count + 99U) / 100U;
	if (rank == 0U) rank = 1U;
	if (rank > count) rank = count;
	return sorted[rank - 1U];
}

inline unsigned Mean(const unsigned *values, unsigned count)
{
	if (count == 0U) return 0U;
	uint64_t total = 0U;
	for (unsigned index = 0U; index < count; ++index) total += values[index];
	return static_cast<unsigned>((total + count / 2U) / count);
}

constexpr unsigned FNV_OFFSET = 2166136261U;
constexpr unsigned FNV_PRIME = 16777619U;

// FNV-1a over the four little-endian bytes of a 32-bit word.
inline unsigned Fnv1a_Word(unsigned hash, unsigned word)
{
	for (unsigned shift = 0U; shift < 32U; shift += 8U) {
		hash ^= (word >> shift) & 0xFFU;
		hash *= FNV_PRIME;
	}
	return hash;
}

inline unsigned Float_Bits(float value)
{
	unsigned bits;
	memcpy(&bits, &value, sizeof(bits));
	return bits;
}

inline unsigned Clamp_Us(uint64_t value)
{
	return value > 0xFFFFFFFFULL ? 0xFFFFFFFFU : static_cast<unsigned>(value);
}

template <class Statistics>
inline void Copy_Counters(const Statistics &statistics, unsigned counters[COUNTER_COUNT])
{
	counters[COUNTER_MESHES] = static_cast<unsigned>(statistics.mesh_submissions);
	counters[COUNTER_VERTICES] = static_cast<unsigned>(statistics.vertex_submissions);
	counters[COUNTER_TRIANGLES] = static_cast<unsigned>(statistics.triangle_submissions);
	counters[COUNTER_MATERIAL_PASSES] = static_cast<unsigned>(statistics.material_passes);
	counters[COUNTER_INDEXED_DRAWS] = static_cast<unsigned>(statistics.indexed_submissions);
	counters[COUNTER_INDEXED_TRIANGLES] =
		static_cast<unsigned>(statistics.indexed_triangle_submissions);
	counters[COUNTER_TEXTURE_BINDS] = static_cast<unsigned>(statistics.texture_binds);
	counters[COUNTER_STATE_CHANGES] = static_cast<unsigned>(statistics.state_changes);
}

// Read back the original camera's rendered pose: 3x4 transform rows, then
// horizontal/vertical FOV and near/far clip planes.
template <class Camera>
inline bool Read_Pose(Camera *camera, float pose[POSE_WORDS])
{
	memset(pose, 0, sizeof(float) * POSE_WORDS);
	if (camera == NULL) return false;
	const auto transform = camera->Get_Transform();
	for (unsigned row = 0U; row < 3U; ++row) {
		for (unsigned column = 0U; column < 4U; ++column) {
			pose[row * 4U + column] = transform[row][column];
		}
	}
	pose[12] = camera->Get_Horizontal_FOV();
	pose[13] = camera->Get_Vertical_FOV();
	camera->Get_Clip_Planes(pose[14], pose[15]);
	return true;
}

inline unsigned Pose_Crc(const float pose[POSE_WORDS])
{
	unsigned hash = FNV_OFFSET;
	for (unsigned index = 0U; index < POSE_WORDS; ++index) {
		hash = Fnv1a_Word(hash, Float_Bits(pose[index]));
	}
	return hash;
}

// Correctness fingerprint of one held viewpoint: version, viewpoint index,
// rendered pose and the modal per-frame MeshClass submission tuple.
inline unsigned Viewpoint_Fingerprint(unsigned viewpoint, unsigned pose_crc,
	const unsigned mode[FINGERPRINT_COUNTERS])
{
	unsigned hash = Fnv1a_Word(FNV_OFFSET, VERSION);
	hash = Fnv1a_Word(hash, viewpoint);
	hash = Fnv1a_Word(hash, pose_crc);
	for (unsigned index = 0U; index < FINGERPRINT_COUNTERS; ++index) {
		hash = Fnv1a_Word(hash, mode[index]);
	}
	return hash;
}

struct FrameSample
{
	unsigned interval_us;
	unsigned work_us;
	unsigned simulation_us;
	unsigned render_us;
	unsigned counters[COUNTER_COUNT];
	unsigned flags;
};

// Most frequent fingerprint tuple among the samples; ties go to the
// lexicographically smallest tuple so the choice never depends on order.
inline unsigned Modal_Tuple(const FrameSample *samples, unsigned count,
	unsigned mode[FINGERPRINT_COUNTERS])
{
	memset(mode, 0, sizeof(unsigned) * FINGERPRINT_COUNTERS);
	unsigned best_count = 0U;
	for (unsigned candidate = 0U; candidate < count; ++candidate) {
		unsigned matches = 0U;
		for (unsigned other = 0U; other < count; ++other) {
			if (memcmp(samples[candidate].counters, samples[other].counters,
				sizeof(unsigned) * FINGERPRINT_COUNTERS) == 0) {
				++matches;
			}
		}
		bool better = matches > best_count;
		if (!better && matches == best_count && best_count != 0U) {
			for (unsigned index = 0U; index < FINGERPRINT_COUNTERS; ++index) {
				if (samples[candidate].counters[index] != mode[index]) {
					better = samples[candidate].counters[index] < mode[index];
					break;
				}
			}
		}
		if (better) {
			best_count = matches;
			memcpy(mode, samples[candidate].counters, sizeof(unsigned) * FINGERPRINT_COUNTERS);
		}
	}
	return best_count;
}

struct Summary
{
	unsigned frames;
	unsigned invalid_frames;
	unsigned flags;
	unsigned interval_p50;
	unsigned interval_p95;
	unsigned interval_p99;
	unsigned interval_worst;
	unsigned interval_mean;
	unsigned work_p50;
	unsigned work_p95;
	unsigned work_worst;
	unsigned simulation_mean;
	unsigned render_mean;
	unsigned counter_median[COUNTER_COUNT];
	unsigned mode[FINGERPRINT_COUNTERS];
	unsigned mode_frames;
	unsigned settle_worst_us;
	unsigned pose_crc;
	unsigned fingerprint;
	float camera[3];
	float forward[3];
	float horizontal_fov;
};

inline Summary Summarize(unsigned viewpoint, const FrameSample *measured, unsigned count,
	const float pose[POSE_WORDS], unsigned settle_worst_us)
{
	Summary summary = {};
	summary.frames = count;
	summary.settle_worst_us = settle_worst_us;
	unsigned values[MEASURE_FRAMES];
	if (count > MEASURE_FRAMES) count = MEASURE_FRAMES;
	for (unsigned index = 0U; index < count; ++index) {
		summary.flags |= measured[index].flags;
		if ((measured[index].flags & FLAG_INVALIDATING) != 0U) ++summary.invalid_frames;
		values[index] = measured[index].interval_us;
	}
	summary.interval_mean = Mean(values, count);
	Sort_Ascending(values, count);
	summary.interval_p50 = Nearest_Rank(values, count, 50U);
	summary.interval_p95 = Nearest_Rank(values, count, 95U);
	summary.interval_p99 = Nearest_Rank(values, count, 99U);
	summary.interval_worst = count != 0U ? values[count - 1U] : 0U;
	for (unsigned index = 0U; index < count; ++index) values[index] = measured[index].work_us;
	Sort_Ascending(values, count);
	summary.work_p50 = Nearest_Rank(values, count, 50U);
	summary.work_p95 = Nearest_Rank(values, count, 95U);
	summary.work_worst = count != 0U ? values[count - 1U] : 0U;
	for (unsigned index = 0U; index < count; ++index) values[index] = measured[index].simulation_us;
	summary.simulation_mean = Mean(values, count);
	for (unsigned index = 0U; index < count; ++index) values[index] = measured[index].render_us;
	summary.render_mean = Mean(values, count);
	for (unsigned counter = 0U; counter < COUNTER_COUNT; ++counter) {
		for (unsigned index = 0U; index < count; ++index) {
			values[index] = measured[index].counters[counter];
		}
		Sort_Ascending(values, count);
		summary.counter_median[counter] = Nearest_Rank(values, count, 50U);
	}
	summary.mode_frames = Modal_Tuple(measured, count, summary.mode);
	summary.pose_crc = Pose_Crc(pose);
	summary.fingerprint = Viewpoint_Fingerprint(viewpoint, summary.pose_crc, summary.mode);
	summary.camera[0] = pose[3];
	summary.camera[1] = pose[7];
	summary.camera[2] = pose[11];
	// The camera looks down its local -Z axis.
	summary.forward[0] = -pose[2];
	summary.forward[1] = -pose[6];
	summary.forward[2] = -pose[10];
	summary.horizontal_fov = pose[12];
	return summary;
}

struct FrameInput
{
	unsigned frame_index;
	uint64_t frame_begin_us;
	uint64_t simulation_begin_us;
	uint64_t render_begin_us;
	uint64_t frame_end_us;
	unsigned counters_after[COUNTER_COUNT];
	bool control_ready;
	bool camera_host_model;
	bool star_alive;
	bool first_person;
	unsigned active_conversations;
	bool pose_valid;
	float pose[POSE_WORDS];
};

typedef void (*LineSink)(const char *line);

class Controller
{
public:
	enum State : unsigned {
		STATE_DISABLED = 0U,
		STATE_WAITING,
		STATE_RUNNING,
		STATE_DONE,
		STATE_ABORTED,
	};

	void Configure(const FlagConfig &flag, bool m00_archive, bool fresh_start,
		const char *candidate_label, LineSink sink)
	{
		Release_Hooks();
		memset(this, 0, sizeof(*this));
		sink_ = sink;
		snprintf(label_, sizeof(label_), "%s", candidate_label != NULL ? candidate_label : "unknown");
		for (char *cursor = label_; *cursor != 0; ++cursor) {
			const char c = *cursor;
			const bool safe = (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
				(c >= '0' && c <= '9') || c == '.' || c == '-' || c == '_';
			if (!safe) *cursor = '_';
		}
		if (flag.status == FLAG_STATUS_ABSENT || flag.status == FLAG_STATUS_OFF) return;
		if (flag.status == FLAG_STATUS_REJECTED) {
			Emit("A4 tutorial-bench: rejected flag=tutorial-bench-v1.flag expected=\"RVTB1 1..5|C\\n\"; benchmark off");
			return;
		}
		if (!m00_archive) {
			Emit("A4 tutorial-bench: inactive; requires M00_Tutorial.mix");
			return;
		}
		passes_ = flag.passes;
		capture_ = flag.capture;
		fresh_start_ = fresh_start;
		state_ = STATE_WAITING;
		Emitf("A4 tutorial-bench: armed v=%u passes=%u capture=%d viewpoints=%u settle=%u measure=%u source=%s; waiting for original control and %u quiet frames",
			VERSION, passes_, capture_ ? 1 : 0, VIEWPOINT_COUNT, SETTLE_FRAMES,
			MEASURE_FRAMES, fresh_start_ ? "fresh" : "save", QUIET_FRAMES_REQUIRED);
	}

	bool Enabled() const { return state_ == STATE_WAITING || state_ == STATE_RUNNING; }
	bool Running() const { return state_ == STATE_RUNNING; }

	// Directly before A31_Interactive_Run_Simulation_Frame().
	void Arm_Simulation(const unsigned counters_before[COUNTER_COUNT])
	{
		if (state_ != STATE_RUNNING) return;
		if (pending_) gap_ = true;
		const Viewpoint &viewpoint = kViewpoints[viewpoint_];
		RenegadeVitaBenchHooks &hooks = g_renegade_vita_bench_hooks;
		memcpy(hooks.camera_position, viewpoint.position, sizeof(hooks.camera_position));
		memcpy(hooks.camera_target, viewpoint.target, sizeof(hooks.camera_target));
		hooks.camera_horizontal_fov = kHorizontalFovRadians;
		hooks.camera_near_clip = kNearClip;
		hooks.camera_far_clip = kFarClip;
		applied_before_ = hooks.camera_applied;
		hooks.camera_armed = true;
		hooks.input_suppressed = true;
		memcpy(counters_before_, counters_before, sizeof(counters_before_));
		pending_ = true;
	}

	// Directly after the simulation call returns, on every path.
	static void Release_Hooks()
	{
		g_renegade_vita_bench_hooks.camera_armed = false;
		g_renegade_vita_bench_hooks.input_suppressed = false;
	}

	// After the frame's timing is final (after End_Render and audio update).
	void End_Frame(const FrameInput &input)
	{
		if (state_ == STATE_WAITING) {
			Evaluate_Readiness(input);
		} else if (state_ == STATE_RUNNING) {
			Record(input);
		}
	}

	// Session end: release hooks and report an unfinished run once.
	void Finish(const char *reason)
	{
		Release_Hooks();
		if (state_ == STATE_RUNNING) Abort(reason);
		else if (state_ == STATE_WAITING) {
			Emitf("A4 tutorial-bench: not started reason=%s control_frames=%u quiet_frames=%u",
				reason, control_frames_, quiet_frames_);
			state_ = STATE_DONE;
		}
	}

	// One capture request per completed viewpoint on the "C" flag's pass.
	bool Take_Capture_Request(char *label, size_t capacity, unsigned *viewpoint)
	{
		if (!capture_pending_) return false;
		capture_pending_ = false;
		snprintf(label, capacity, "tutorial-bench-%s-vp%02u-%s", run_, capture_viewpoint_,
			kViewpoints[capture_viewpoint_].name);
		if (viewpoint != NULL) *viewpoint = capture_viewpoint_;
		return true;
	}

private:
	void Emit(const char *line) { if (sink_ != NULL) sink_(line); }

	__attribute__((format(printf, 2, 3))) void Emitf(const char *format, ...)
	{
		char line[768];
		va_list arguments;
		va_start(arguments, format);
		vsnprintf(line, sizeof(line), format, arguments);
		va_end(arguments);
		Emit(line);
	}

	void Evaluate_Readiness(const FrameInput &input)
	{
		if (!input.control_ready || !input.star_alive) {
			control_frames_ = 0U;
			quiet_frames_ = 0U;
			return;
		}
		++control_frames_;
		if (input.camera_host_model || input.active_conversations != 0U) {
			quiet_frames_ = 0U;
		} else {
			++quiet_frames_;
		}
		const bool quiet = quiet_frames_ >= QUIET_FRAMES_REQUIRED &&
			control_frames_ >= MIN_FRAMES_AFTER_CONTROL;
		const bool timeout = control_frames_ >= READY_TIMEOUT_FRAMES && !input.camera_host_model;
		if (!quiet && !timeout) return;
		Start(input, quiet);
	}

	bool File_Exists(const char *path) const
	{
		FILE *file = fopen(path, "rb");
		if (file == NULL) return false;
		fclose(file);
		return true;
	}

	void Start(const FrameInput &input, bool quiet)
	{
		// First unused run number keeps repeated launches of one candidate apart.
		bool run_selected = false;
		for (unsigned run = 1U; run <= MAX_RUN_FILES && !run_selected; ++run) {
			snprintf(run_, sizeof(run_), "r%02u", run);
			snprintf(summary_path_, sizeof(summary_path_), "%s/tutorial-bench-%s-%s.csv",
				kLogDirectory, label_, run_);
			run_selected = !File_Exists(summary_path_);
		}
		if (!run_selected) {
			Emitf("A4 tutorial-bench: not started; %u result files already exist for candidate=%s",
				MAX_RUN_FILES, label_);
			state_ = STATE_DONE;
			return;
		}
		snprintf(frames_path_, sizeof(frames_path_), "%s/tutorial-bench-%s-%s-frames.csv",
			kLogDirectory, label_, run_);
		FILE *summary = fopen(summary_path_, "wb");
		FILE *frames = fopen(frames_path_, "wb");
		csv_ok_ = summary != NULL && frames != NULL;
		if (summary != NULL) {
			fprintf(summary, "candidate,run,pass,viewpoint,name,valid,frames,invalid_frames,flags,"
				"interval_p50_us,interval_p95_us,interval_p99_us,interval_worst_us,interval_mean_us,"
				"work_p50_us,work_p95_us,work_worst_us,simulation_mean_us,render_mean_us,"
				"meshes,vertices,triangles,material_passes,indexed_draws,indexed_triangles,"
				"texture_binds,state_changes,mode_frames,fingerprint,pose_crc,settle_worst_us,"
				"cam_x,cam_y,cam_z,fwd_x,fwd_y,fwd_z,hfov,source,quiet_start\n");
			fclose(summary);
		}
		if (frames != NULL) {
			fprintf(frames, "candidate,run,pass,viewpoint,hold_frame,measured,interval_us,work_us,"
				"simulation_us,render_us,meshes,vertices,triangles,material_passes,indexed_draws,"
				"indexed_triangles,texture_binds,state_changes,flags\n");
			fclose(frames);
		}
		quiet_start_ = quiet;
		state_ = STATE_RUNNING;
		pass_ = 0U;
		viewpoint_ = 0U;
		hold_frame_ = 0U;
		pending_ = false;
		gap_ = false;
		last_frame_begin_us_ = input.frame_begin_us;
		Begin_Pass();
		// first_person matters: the original first-person weapon view renders
		// with the camera, so it is part of every viewpoint fingerprint.
		Emitf("A4 tutorial-bench: start v=%u run=%s candidate=%s frame=%u passes=%u viewpoints=%u quiet=%d control_frames=%u source=%s first_person=%d csv=%s csv_ok=%d",
			VERSION, run_, label_, input.frame_index, passes_, VIEWPOINT_COUNT,
			quiet ? 1 : 0, control_frames_, fresh_start_ ? "fresh" : "save",
			input.first_person ? 1 : 0, summary_path_, csv_ok_ ? 1 : 0);
	}

	void Begin_Pass()
	{
		pooled_count_ = 0U;
		valid_viewpoints_ = 0U;
		route_fingerprint_ = FNV_OFFSET;
	}

	void Record(const FrameInput &input)
	{
		if (!pending_) return;
		pending_ = false;
		const RenegadeVitaBenchHooks &hooks = g_renegade_vita_bench_hooks;
		FrameSample &sample = samples_[hold_frame_];
		memset(&sample, 0, sizeof(sample));
		sample.interval_us = Clamp_Us(input.frame_begin_us - last_frame_begin_us_);
		last_frame_begin_us_ = input.frame_begin_us;
		sample.work_us = Clamp_Us(input.frame_end_us - input.frame_begin_us);
		sample.simulation_us = Clamp_Us(input.render_begin_us - input.simulation_begin_us);
		sample.render_us = Clamp_Us(input.frame_end_us - input.render_begin_us);
		// Unsigned deltas survive counter wrap; only a backwards mesh count (a
		// renderer statistics reset) marks the frame.
		for (unsigned counter = 0U; counter < COUNTER_COUNT; ++counter) {
			sample.counters[counter] = input.counters_after[counter] - counters_before_[counter];
		}
		if (input.counters_after[COUNTER_MESHES] < counters_before_[COUNTER_MESHES]) {
			sample.flags |= FLAG_COUNTER_RESET;
		}
		if (hooks.camera_applied == applied_before_ || input.camera_host_model ||
			!input.pose_valid || !input.star_alive) {
			sample.flags |= FLAG_CAMERA_NOT_APPLIED;
		}
		if (gap_) {
			sample.flags |= FLAG_FRAME_GAP;
			gap_ = false;
		}
		if (sample.interval_us > LONG_INTERVAL_US) sample.flags |= FLAG_LONG_INTERVAL;
		if (input.active_conversations != 0U) sample.flags |= FLAG_CONVERSATION;
		if (hold_frame_ == SETTLE_FRAMES) {
			memcpy(reference_pose_, input.pose, sizeof(reference_pose_));
		} else if (hold_frame_ > SETTLE_FRAMES &&
			memcmp(reference_pose_, input.pose, sizeof(reference_pose_)) != 0) {
			sample.flags |= FLAG_POSE_CHANGED;
		}
		if (hold_frame_ < SETTLE_FRAMES) {
			if (sample.interval_us > settle_worst_us_) settle_worst_us_ = sample.interval_us;
		} else if (pooled_count_ < VIEWPOINT_COUNT * MEASURE_FRAMES) {
			pooled_[pooled_count_++] = sample.interval_us;
		}
		++hold_frame_;
		// A skipped frame or a frame the fixed camera did not own (START/pause
		// returns before Combat Think, a cinematic host camera, a dead star)
		// ends the run; partial results are still reported.
		if ((sample.flags & FLAG_FRAME_GAP) != 0U) {
			Abort("frame-gap(pause/restart/skipped-render)");
			return;
		}
		if ((sample.flags & FLAG_CAMERA_NOT_APPLIED) != 0U) {
			Abort("camera-not-applied(start/pause/cinematic/star)");
			return;
		}
		if (hold_frame_ == HOLD_FRAMES) Finish_Viewpoint(input.frame_index);
	}

	// Raw rows of the current hold; written between holds, during the next
	// viewpoint's settle frames, never inside a measured frame.
	void Write_Frame_Rows(unsigned count)
	{
		FILE *file = csv_ok_ ? fopen(frames_path_, "ab") : NULL;
		if (file == NULL) return;
		for (unsigned index = 0U; index < count && index < HOLD_FRAMES; ++index) {
			const FrameSample &row = samples_[index];
			fprintf(file, "%s,%s,%u,%u,%u,%d,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u\n",
				label_, run_, pass_ + 1U, viewpoint_, index,
				index >= SETTLE_FRAMES ? 1 : 0, row.interval_us,
				row.work_us, row.simulation_us, row.render_us,
				row.counters[0], row.counters[1], row.counters[2], row.counters[3],
				row.counters[4], row.counters[5], row.counters[6], row.counters[7],
				row.flags);
		}
		fclose(file);
	}

	void Finish_Viewpoint(unsigned frame_index)
	{
		Write_Frame_Rows(hold_frame_);
		const unsigned measured = hold_frame_ > SETTLE_FRAMES ? hold_frame_ - SETTLE_FRAMES : 0U;
		const Summary summary = Summarize(viewpoint_, samples_ + SETTLE_FRAMES, measured,
			reference_pose_, settle_worst_us_);
		const bool valid = measured == MEASURE_FRAMES && summary.invalid_frames == 0U;
		if (valid) ++valid_viewpoints_;
		route_fingerprint_ = Fnv1a_Word(route_fingerprint_, summary.fingerprint);
		const Viewpoint &viewpoint = kViewpoints[viewpoint_];
		Emitf("A4 tutorial-bench: run=%s pass=%u/%u vp=%02u/%u name=%s valid=%d frames=%u invalid=%u flags=%02X interval_us p50/p95/p99/worst/mean=%u/%u/%u/%u/%u work_us p50/p95/worst=%u/%u/%u sim/render_mean_us=%u/%u meshes/vertices/triangles/passes=%u/%u/%u/%u idx_draws/idx_tris=%u/%u binds/states=%u/%u mode=%u/%u fingerprint=%08X pose=%08X settle_worst_us=%u cam=(%.2f,%.2f,%.2f) fwd=(%.3f,%.3f,%.3f) hfov=%.4f frame=%u",
			run_, pass_ + 1U, passes_, viewpoint_, VIEWPOINT_COUNT, viewpoint.name,
			valid ? 1 : 0, summary.frames, summary.invalid_frames, summary.flags,
			summary.interval_p50, summary.interval_p95, summary.interval_p99,
			summary.interval_worst, summary.interval_mean, summary.work_p50,
			summary.work_p95, summary.work_worst, summary.simulation_mean,
			summary.render_mean, summary.counter_median[0], summary.counter_median[1],
			summary.counter_median[2], summary.counter_median[3],
			summary.counter_median[4], summary.counter_median[5],
			summary.counter_median[6], summary.counter_median[7], summary.mode_frames,
			summary.frames, summary.fingerprint, summary.pose_crc,
			summary.settle_worst_us, summary.camera[0], summary.camera[1],
			summary.camera[2], summary.forward[0], summary.forward[1],
			summary.forward[2], summary.horizontal_fov, frame_index);
		FILE *file = csv_ok_ ? fopen(summary_path_, "ab") : NULL;
		if (file != NULL) {
			fprintf(file, "%s,%s,%u,%u,%s,%d,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%08X,%08X,%u,%.3f,%.3f,%.3f,%.4f,%.4f,%.4f,%.4f,%s,%d\n",
				label_, run_, pass_ + 1U, viewpoint_, viewpoint.name, valid ? 1 : 0,
				summary.frames, summary.invalid_frames, summary.flags,
				summary.interval_p50, summary.interval_p95, summary.interval_p99,
				summary.interval_worst, summary.interval_mean, summary.work_p50,
				summary.work_p95, summary.work_worst, summary.simulation_mean,
				summary.render_mean, summary.counter_median[0], summary.counter_median[1],
				summary.counter_median[2], summary.counter_median[3],
				summary.counter_median[4], summary.counter_median[5],
				summary.counter_median[6], summary.counter_median[7],
				summary.mode_frames, summary.fingerprint, summary.pose_crc,
				summary.settle_worst_us, summary.camera[0], summary.camera[1],
				summary.camera[2], summary.forward[0], summary.forward[1],
				summary.forward[2], summary.horizontal_fov,
				fresh_start_ ? "fresh" : "save", quiet_start_ ? 1 : 0);
			fclose(file);
		}
		if (capture_ && pass_ == 0U) {
			capture_pending_ = true;
			capture_viewpoint_ = viewpoint_;
		}
		hold_frame_ = 0U;
		settle_worst_us_ = 0U;
		++viewpoint_;
		if (viewpoint_ < VIEWPOINT_COUNT) return;
		Finish_Pass(false);
		viewpoint_ = 0U;
		++pass_;
		if (pass_ < passes_) {
			Begin_Pass();
			return;
		}
		Release_Hooks();
		state_ = STATE_DONE;
		Emitf("A4 tutorial-bench: complete run=%s passes=%u csv=%s frames_csv=%s",
			run_, passes_, summary_path_, frames_path_);
	}

	void Finish_Pass(bool aborted)
	{
		unsigned *pooled = pooled_;
		const unsigned count = pooled_count_;
		const unsigned mean = Mean(pooled, count);
		Sort_Ascending(pooled, count);
		const unsigned p50 = Nearest_Rank(pooled, count, 50U);
		const unsigned p95 = Nearest_Rank(pooled, count, 95U);
		const unsigned p99 = Nearest_Rank(pooled, count, 99U);
		const unsigned worst = count != 0U ? pooled[count - 1U] : 0U;
		Emitf("A4 tutorial-bench: summary v=%u run=%s pass=%u/%u candidate=%s aborted=%d viewpoints=%u/%u valid=%u frames=%u interval_us p50/p95/p99/worst/mean=%u/%u/%u/%u/%u route_fingerprint=%08X source=%s quiet=%d",
			VERSION, run_, pass_ + 1U, passes_, label_, aborted ? 1 : 0, viewpoint_,
			VIEWPOINT_COUNT, valid_viewpoints_, count, p50, p95, p99, worst, mean,
			route_fingerprint_, fresh_start_ ? "fresh" : "save", quiet_start_ ? 1 : 0);
		FILE *file = csv_ok_ ? fopen(summary_path_, "ab") : NULL;
		if (file != NULL) {
			fprintf(file, "%s,%s,%u,ALL,route,%d,%u,0,0,%u,%u,%u,%u,%u,0,0,0,0,0,0,0,0,0,0,0,0,0,0,%08X,00000000,0,0,0,0,0,0,0,0,%s,%d\n",
				label_, run_, pass_ + 1U,
				!aborted && valid_viewpoints_ == VIEWPOINT_COUNT ? 1 : 0, count,
				p50, p95, p99, worst, mean, route_fingerprint_,
				fresh_start_ ? "fresh" : "save", quiet_start_ ? 1 : 0);
			fclose(file);
		}
	}

	void Abort(const char *reason)
	{
		Release_Hooks();
		Write_Frame_Rows(hold_frame_);
		Emitf("A4 tutorial-bench: aborted run=%s pass=%u/%u vp=%u/%u hold_frame=%u reason=%s",
			run_, pass_ + 1U, passes_, viewpoint_, VIEWPOINT_COUNT, hold_frame_, reason);
		Finish_Pass(true);
		state_ = STATE_ABORTED;
	}

	State state_;
	LineSink sink_;
	char label_[64];
	char run_[8];
	char summary_path_[192];
	char frames_path_[192];
	unsigned passes_;
	bool capture_;
	bool fresh_start_;
	bool quiet_start_;
	bool csv_ok_;
	unsigned control_frames_;
	unsigned quiet_frames_;
	unsigned pass_;
	unsigned viewpoint_;
	unsigned hold_frame_;
	bool pending_;
	bool gap_;
	unsigned applied_before_;
	unsigned counters_before_[COUNTER_COUNT];
	uint64_t last_frame_begin_us_;
	unsigned settle_worst_us_;
	float reference_pose_[POSE_WORDS];
	FrameSample samples_[HOLD_FRAMES];
	unsigned pooled_[VIEWPOINT_COUNT * MEASURE_FRAMES];
	unsigned pooled_count_;
	unsigned valid_viewpoints_;
	unsigned route_fingerprint_;
	bool capture_pending_;
	unsigned capture_viewpoint_;
};

// Releases the hooks and reports an unfinished run when the native session
// scope ends on any path (break, error, teardown).
class Session_Guard
{
public:
	explicit Session_Guard(Controller &controller) : Controller_(controller) {}
	~Session_Guard() { Controller_.Finish("session-end"); }

private:
	Session_Guard(const Session_Guard &);
	Session_Guard &operator=(const Session_Guard &);
	Controller &Controller_;
};

} // namespace RenegadeVitaTutorialBench
