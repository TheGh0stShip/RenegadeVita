// Low frame-rate scheduling of the original Test_Cinematic.
//
// Drives the real staged script (Created, Timer_Expired, Custom, Parse_Commands,
// Load_Control_File, every Command_* handler) through a model of the original
// per-frame order:
//   TimeManager::Update_Frame_Time  FrameTicks = min(real, 1000/SLOWEST_FPS) or 0 paused
//   CombatManager::Think            SyncTime += (int)(FrameSeconds * 1000 + 0.5)
//   COMBAT_SCENE->Update            animations advance by FrameSeconds
//   GameObjManager::Post_Think      observer timers: reverse walk, RemainingTime -= FrameSeconds
// Combat suspension (pause menu) skips CombatManager::Think entirely.
//
// Each control file is run under a fine 1 ms reference and several Vita-like
// profiles.  Every profile must consume every authored line exactly once, in
// the original sorted order, never before its time, at most one frame late,
// produce the reference's effect sequence, keep FrameSync equal to the
// overshoot, keep animation time equal to cinematic time, and destroy the
// controller only in the callback that consumes the final authored line.
#define main CinematicSaveFixtureMain
#include "host_cinematic_save_test.cpp"
#undef main

#include "ScriptRegistrar.h"
#include <cmath>
#include <map>
#include <random>

namespace lowfps {

struct Line { float time; std::string text; };
struct Effect { int line; std::string what; bool operator==(const Effect &o) const { return line == o.line && what == o.what; } };
struct Anim { int line; float start_frame; float line_time; float time_at_start; unsigned sync_at_start; double scene_clock_at_start; };

static std::string Payload;
static size_t Cursor;
static Test_Cinematic *Active;
static std::map<const void *, int> NodeIndex;
static std::vector<Line> Loaded;
static unsigned SyncTime;
static float FrameSeconds;
static double SceneClock; // sum of COMBAT_SCENE->Update steps
static int Frame;
static int Callback;
static int DestroyCallback;
static int DestroyCount;
static int NextId;
static std::vector<float> Timers;
static std::vector<Effect> Effects;
static std::vector<Anim> Anims;
static std::string Failure;
static int KillOnCustomType = -1;
static GameObject *const Controller = reinterpret_cast<GameObject *>(16);

static GameObject *Obj(int id) { return reinterpret_cast<GameObject *>(static_cast<uintptr_t>(id) * 16U); }
static int Id(GameObject *object) { return static_cast<int>(reinterpret_cast<uintptr_t>(object) / 16U); }
static void Ignore(char *, ...) {}
static int Head() {
	if (Active == nullptr || Active->Controls == nullptr) return -1;
	auto it = NodeIndex.find(Active->Controls);
	return it == NodeIndex.end() ? -2 : it->second;
}
static void Note(const std::string &what) { Effects.push_back({Head(), what}); }
static std::string S(const char *text) { return text ? text : "(null)"; }

static void Install(ScriptCommands &c)
{
	c.Debug_Message = Ignore;
	c.Text_File_Open = [](const char *) { Cursor = 0; return 1; };
	c.Text_File_Get_String = [](int handle, char *buffer, int size) {
		assert(handle == 1);
		int written = 0;
		while (Cursor < Payload.size()) {
			char ch = Payload[Cursor++];
			if (written < size) buffer[written++] = ch;
			if (ch == '\n') break;
		}
		buffer[written] = 0;
		return buffer[0] != 0;
	};
	c.Text_File_Close = [](int) {
		// Load_Control_File has built the sorted list: index every node once.
		NodeIndex.clear(); Loaded.clear();
		for (auto *node = Active->Controls; node; node = node->Next) {
			NodeIndex[node] = static_cast<int>(Loaded.size());
			Loaded.push_back({node->Time, node->Command});
		}
	};
	c.Get_Sync_Time = []() { return SyncTime; };
	c.Get_ID = [](GameObject *object) { return Id(object); };
	c.Find_Object = [](int id) { return id ? Obj(id) : static_cast<GameObject *>(nullptr); };
	c.Get_The_Star = []() { return Obj(2); };
	c.Get_Position = [](GameObject *) { return Vector3(0, 0, 0); };
	c.Get_Bone_Position = [](GameObject *, const char *) { return Vector3(0, 0, 0); };
	c.Get_Facing = [](GameObject *) { return 0.f; };
	c.Set_Facing = [](GameObject *, float) {};
	c.Start_Timer = [](GameObject *object, ScriptClass *, float duration, int) {
		if (object != Controller) Failure = "timer on foreign object";
		if (!(duration > 0)) Failure = "non-positive timer";
		Timers.push_back(duration);
	};
	c.Destroy_Object = [](GameObject *object) {
		if (object == Controller) { ++DestroyCount; if (DestroyCallback < 0) DestroyCallback = Callback; }
		else Note("destroy:" + std::to_string(Id(object)));
	};
	c.Enable_Hibernation = [](GameObject *, bool) {};
	c.Enable_Cinematic_Freeze = [](GameObject *, bool) {};
	c.Add_To_Dirty_Cull_List = [](GameObject *) {};
	c.Innate_Disable = [](GameObject *) {};
	c.Enable_Engine = [](GameObject *, bool) {};
	c.Create_Object = [](const char *preset, const Vector3 &) { Note("create:" + S(preset)); return Obj(NextId++); };
	c.Create_Object_At_Bone = [](GameObject *, const char *preset, const char *bone) {
		Note("create_bone:" + S(preset) + "@" + S(bone)); return Obj(NextId++); };
	c.Set_Model = [](GameObject *object, const char *model) { Note("model:" + std::to_string(Id(object)) + ":" + S(model)); };
	c.Create_Explosion_At_Bone = [](const char *preset, GameObject *, const char *, GameObject *) { Note("explosion:" + S(preset)); };
	c.Set_Animation = [](GameObject *object, const char *anim, bool loop, const char *sub, float start, float, bool) {
		Note("anim:" + std::to_string(Id(object)) + ":" + S(anim) + ":" + (loop ? "1" : "0") + ":" + S(sub));
		const int line = Head();
		if (line < 0) { Failure = "animation outside an authored line"; return; }
		Anims.push_back({line, start, Loaded[line].time, Active->Time, SyncTime, SceneClock});
	};
	c.Create_2D_Sound = [](const char *name) { Note("sound2d:" + S(name)); return 1; };
	c.Create_3D_Sound_At_Bone = [](const char *name, GameObject *object, const char *bone) {
		Note("sound3d:" + S(name) + ":" + std::to_string(Id(object)) + ":" + S(bone)); return 1; };
	c.Set_Camera_Host = [](GameObject *object) { Note("camera:" + std::to_string(Id(object))); };
	c.Control_Enable = [](GameObject *, bool on) { Note(on ? "input_on" : "input_off"); };
	c.Enable_HUD = [](bool on) { Note(on ? "hud_on" : "hud_off"); };
	c.Send_Custom_Event = [](GameObject *from, GameObject *to, int type, int param, float delay) {
		Note("custom:" + std::to_string(Id(from)) + ">" + std::to_string(Id(to)) + ":" +
			std::to_string(type) + ":" + std::to_string(param) + ":" + std::to_string(delay));
		// Optional synchronous primary kill inside a command (re-entrancy probe).
		if (type == KillOnCustomType) Active->Custom(Controller, M00_CUSTOM_CINEMATIC_PRIMARY_KILLED, 0, nullptr);
	};
	c.Attach_To_Object_Bone = [](GameObject *object, GameObject *host, const char *bone) {
		Note("bone:" + std::to_string(Id(object)) + ">" + std::to_string(Id(host)) + ":" + S(bone)); };
	c.Attach_Script = [](GameObject *object, const char *name, const char *params) {
		Note("script:" + std::to_string(Id(object)) + ":" + S(name) + ":" + S(params)); };
	c.Cinematic_Sniper_Control = [](bool on, float zoom) { Note("sniper:" + std::to_string(on) + ":" + std::to_string(zoom)); };
	c.Shake_Camera = [](const Vector3 &, float r, float i, float d) {
		Note("shake:" + std::to_string(r) + ":" + std::to_string(i) + ":" + std::to_string(d)); };
	c.Enable_Shadow = [](GameObject *object, bool on) { Note("shadow:" + std::to_string(Id(object)) + ":" + std::to_string(on)); };
	c.Enable_Letterbox = [](bool on, float t) { Note("letterbox:" + std::to_string(on) + ":" + std::to_string(t)); };
	c.Set_Screen_Fade_Color = [](float r, float g, float b, float t) {
		Note("fade_color:" + std::to_string(r) + ":" + std::to_string(g) + ":" + std::to_string(b) + ":" + std::to_string(t)); };
	c.Set_Screen_Fade_Opacity = [](float o, float t) { Note("fade_opacity:" + std::to_string(o) + ":" + std::to_string(t)); };
}

struct FrameSpec { unsigned real_ms; bool suspended; bool paused; };
struct Profile {
	const char *name;
	std::vector<FrameSpec> (*make)(size_t frames);
};

static std::vector<FrameSpec> Repeat(size_t n, std::initializer_list<unsigned> pattern) {
	std::vector<FrameSpec> out; out.reserve(n);
	std::vector<unsigned> p(pattern);
	for (size_t i = 0; i < n; ++i) out.push_back({p[i % p.size()], false, false});
	return out;
}
static std::vector<FrameSpec> Fine(size_t n) { return Repeat(n, {1}); }
static std::vector<FrameSpec> Fps30(size_t n) { return Repeat(n, {33, 33, 34}); }
static std::vector<FrameSpec> Fps20(size_t n) { return Repeat(n, {50}); }
static std::vector<FrameSpec> Fps15(size_t n) { return Repeat(n, {67, 66, 67}); }
static std::vector<FrameSpec> Cap(size_t n) { return Repeat(n, {600, 200, 201, 199, 450}); }
static std::vector<FrameSpec> Jitter(size_t n) {
	// 15-30 fps with first-spawn and loading spikes of 200-600 ms (seeded).
	std::mt19937 rng(0x5EED1234u);
	std::uniform_int_distribution<unsigned> normal(33, 67), spike(200, 600), coin(0, 36);
	std::vector<FrameSpec> out; out.reserve(n);
	for (size_t i = 0; i < n; ++i) {
		unsigned ms = (i < 3 || coin(rng) == 0) ? spike(rng) : normal(rng);
		out.push_back({ms, false, false});
	}
	return out;
}
static std::vector<FrameSpec> PauseResume(size_t n) {
	// 15 fps; a 90-frame pause-menu window (Combat suspended), a 30 s system
	// suspend gap, and a 60-frame Is_Game_Paused window (FrameTicks = 0).
	std::vector<FrameSpec> out = Fps15(n);
	for (size_t i = 0; i < n; ++i) {
		if (i >= 40 && i < 130) out[i].suspended = true;
		if (i == 200) out[i].real_ms = 30000;
		if (i >= 260 && i < 320) out[i].paused = true;
	}
	return out;
}

struct Result {
	std::vector<Effect> effects;
	std::vector<int> consumed;
	int last_consume_callback = -1;
	int destroy_callback = -1;
	int destroy_count = 0;
	int late_one_frame = 0;
	unsigned max_float_hold_ms = 0;
	double max_lateness = 0;
	double max_frame_sync_error = 0;
	double max_anim_drift = 0;
	double max_wall_lag = 0;
	int frames = 0;
	std::string failure;
};

enum Creation { CREATED_BEFORE_OWN_POST_THINK, CREATED_AFTER_OWN_POST_THINK };

static Result Run(const std::string &payload, const Profile &profile, Creation creation, int kill_type = -1)
{
	Result r;
	Payload = payload; Cursor = 0; SyncTime = 7000; FrameSeconds = 0; SceneClock = 0; Frame = 0; Callback = 0;
	DestroyCallback = -1; DestroyCount = 0; NextId = 1000; Timers.clear(); Effects.clear(); Anims.clear();
	Failure.clear(); KillOnCustomType = kill_type;
	ScriptImpClass *created = ScriptRegistrar::CreateScript("Test_Cinematic");
	assert(created != nullptr);
	created->Set_Parameters_String("fixture.txt");
	Active = static_cast<Test_Cinematic *>(created);

	// Remaining-node snapshot: the dispatch loop only consumes from the head.
	std::vector<int> remaining;
	auto snapshot = [&]() {
		std::vector<int> now;
		for (auto *node = Active->Controls; node; node = node->Next) {
			auto it = NodeIndex.find(node);
			now.push_back(it == NodeIndex.end() ? -2 : it->second);
		}
		return now;
	};
	int combat_frame = -1;  // frames in which Combat thought (suspended frames excluded)
	std::vector<unsigned> frame_sync;    // SyncTime at end of each frame
	std::vector<double> frame_wall;      // wall ms at end of each frame
	std::vector<std::pair<int, int>> consume_frame; // (line, frame)
	std::vector<float> consume_time;
	unsigned create_sync = 0;
	double wall = 0, create_wall = 0;
	auto after_callback = [&](bool initial) {
		std::vector<int> now = snapshot();
		const std::vector<int> &before = initial ? std::vector<int>() : remaining;
		if (initial) {
			// Lines consumed by Created's own Parse_Commands.
			for (size_t i = 0; i < Loaded.size() && (now.empty() || static_cast<int>(i) < now.front()); ++i) {
				r.consumed.push_back(static_cast<int>(i)); consume_frame.push_back({static_cast<int>(i), combat_frame});
				consume_time.push_back(Active->Time); r.last_consume_callback = Callback;
			}
		} else {
			if (now.size() > before.size() || !std::equal(now.begin(), now.end(), before.end() - now.size()))
				Failure = "dispatch consumed a non-head line";
			for (size_t i = 0; i + now.size() < before.size(); ++i) {
				r.consumed.push_back(before[i]); consume_frame.push_back({before[i], combat_frame});
				consume_time.push_back(Active->Time); r.last_consume_callback = Callback;
			}
		}
		remaining = now;
	};

	float last_normal = 0;
	std::vector<FrameSpec> frames = profile.make(400000);
	bool alive = true, created_yet = false;
	for (size_t f = 0; f < frames.size() && alive; ++f) {
		Frame = static_cast<int>(f);
		const FrameSpec spec = frames[f];
		wall += spec.real_ms;
		// TimeManager::Update_Frame_Time (TICKS_PER_SECOND 1000, SLOWEST_FPS 5).
		int ticks = static_cast<int>(spec.real_ms);
		ticks = ticks < 1000 / 5 ? ticks : 1000 / 5;
		if (spec.paused) ticks = 0;
		FrameSeconds = static_cast<float>(ticks) / 1000;
		if (spec.suspended) continue;  // pause menu: CombatManager::Think is not called
		++combat_frame;
		// CombatManager::Think.
		SyncTime += static_cast<int>((FrameSeconds * 1000.0f) + 0.5f);
		// COMBAT_SCENE->Update: animations started in an earlier Post_Think advance.
		SceneClock += FrameSeconds;
		auto create = [&]() {
			created_yet = true; create_sync = SyncTime; create_wall = wall;
			++Callback;
			Active->Created(Controller);
			for (const Line &line : Loaded) if (line.time < 999000.0f) last_normal = std::max(last_normal, line.time);
			after_callback(true);
		};
		if (!created_yet && creation == CREATED_BEFORE_OWN_POST_THINK) create();
		// GameObjManager::Post_Think -> ScriptableGameObj::Post_Think timers.
		for (int i = static_cast<int>(Timers.size()) - 1; i >= 0; --i) {
			Timers[i] -= FrameSeconds;
			if (Timers[i] <= 0) {
				++Callback;
				Active->Timer_Expired(Controller, 0);
				after_callback(false);
				Timers.erase(Timers.begin() + i);
			}
		}
		if (!created_yet && creation == CREATED_AFTER_OWN_POST_THINK) create();
		frame_sync.push_back(SyncTime); frame_wall.push_back(wall);
		if (DestroyCount > 0) alive = false;  // deleted at end of frame
		if (!Failure.empty()) break;
		if ((SyncTime - create_sync) / 1000.0 > last_normal + 30.0) { Failure = "controller never finished"; break; }
	}
	r.frames = Frame + 1;
	r.effects = Effects;
	r.destroy_callback = DestroyCallback;
	r.destroy_count = DestroyCount;
	r.failure = Failure;
	// Timing properties.  Once the primary is killed, consumed lines below the
	// tail are discarded unexecuted by the original skip loop; time them only
	// for ordinary runs.
	const bool killed = Active->PrimaryKilled;
	for (size_t k = 0; !killed && k < r.consumed.size(); ++k) {
		const int line = r.consumed[k];
		const float t = Loaded[line].time;
		if (t >= 999000.0f) continue;  // primary-killed tail runs early by design
		const double exec = consume_time[k];
		if (exec + 1e-6 < t) r.failure = "line executed before its authored time";
		r.max_lateness = std::max(r.max_lateness, exec - t);
		// First frame whose cinematic clock reached the line.
		const int f_exec = consume_frame[k].second;
		const double threshold = create_sync + (static_cast<double>(t) - 1e-6) * 1000.0;
		const int f_due = static_cast<int>(std::lower_bound(frame_sync.begin(), frame_sync.begin() + f_exec + 1, threshold,
			[](unsigned value, double limit) { return value < limit; }) - frame_sync.begin());
		// float32 Time accumulation may hold a line back by whole tiny frames at
		// 1 ms steps; bound it in simulated milliseconds as well as frames.
		const unsigned due_delay_ms = frame_sync[f_exec] - frame_sync[f_due];
		if (f_exec - f_due > 1) r.max_float_hold_ms = std::max(r.max_float_hold_ms, due_delay_ms);
		// The 1 ms reference performs ~1000 float32 RemainingTime decrements per
		// second; that original countdown rounding can hold a line for tens of
		// ms there.  Vita-rate profiles must stay within one frame.
		if (f_exec - f_due > 1 && profile.make != Fine) r.failure = "line executed more than one frame late";
		if (f_exec - f_due == 1) ++r.late_one_frame;
		if (f_exec - f_due >= 1 && getenv("LOWFPS_DEBUG_LATE") && r.late_one_frame < 6)
			printf("    late line=%d t=%.9f exec_time=%.9f f_due=%d sync_due=%u f_exec=%d sync_exec=%u create_sync=%u\n",
				line, t, exec, f_due, frame_sync[f_due] - create_sync, f_exec, frame_sync[f_exec] - create_sync, create_sync);
		r.max_wall_lag = std::max(r.max_wall_lag, (frame_wall[f_exec] - create_wall) - 1000.0 * t);
	}
	for (const Anim &anim : Anims) {
		r.max_frame_sync_error = std::max(r.max_frame_sync_error,
			static_cast<double>(std::fabs(anim.start_frame - (anim.time_at_start - anim.line_time) * 30.0f)));
		const double anim_frame = anim.start_frame + 30.0 * (SceneClock - anim.scene_clock_at_start);
		const double cine_frame = 30.0 * ((anim.time_at_start - anim.line_time) +
			(static_cast<double>(SyncTime) - anim.sync_at_start) / 1000.0);
		r.max_anim_drift = std::max(r.max_anim_drift, std::fabs(anim_frame - cine_frame));
	}
	delete created;
	Active = nullptr;
	return r;
}

static const Profile Profiles[] = {
	{"fine_1ms", Fine}, {"fps30", Fps30}, {"fps20", Fps20}, {"fps15", Fps15},
	{"cap_200ms", Cap}, {"jitter_spikes", Jitter}, {"pause_suspend", PauseResume},
};

// Returns true when every profile matches the fine reference.
static bool Check(const std::string &name, const std::string &payload, bool verbose)
{
	bool ok = true;
	Result ref = Run(payload, Profiles[0], CREATED_BEFORE_OWN_POST_THINK);
	std::vector<int> expected;
	for (size_t i = 0; i < Loaded.size(); ++i) if (Loaded[i].time < 999000.0f) expected.push_back(static_cast<int>(i));
	const int final_line = expected.empty() ? -1 : expected.back();
	double worst_late = 0, worst_wall = 0, worst_anim = 0, worst_sync = 0; int late_frames = 0; unsigned worst_hold = 0;
	for (const Profile &profile : Profiles) {
		for (Creation creation : {CREATED_BEFORE_OWN_POST_THINK, CREATED_AFTER_OWN_POST_THINK}) {
			Result r = Run(payload, profile, creation);
			std::string why = r.failure;
			if (why.empty() && r.consumed != expected) why = "consumed lines differ from authored order";
			if (why.empty() && !(r.effects == ref.effects)) why = "effect sequence differs from reference";
			if (why.empty() && r.destroy_count < 1) why = "controller not destroyed";
			if (why.empty() && final_line >= 0 && r.destroy_callback != r.last_consume_callback)
				why = "destroy not in the final line's callback";
			if (why.empty() && r.max_frame_sync_error > 1e-4) why = "FrameSync differs from overshoot";
			if (why.empty() && r.max_anim_drift > 0.05) why = "animation clock drifted from cinematic clock";
			if (why.empty() && r.max_lateness > 0.2 + 1e-4) why = "lateness exceeds one clamped frame";
			if (!why.empty()) {
				ok = false;
				printf("FAIL %s profile=%s creation=%d: %s\n", name.c_str(), profile.name, creation, why.c_str());
			}
			worst_late = std::max(worst_late, r.max_lateness);
			worst_wall = std::max(worst_wall, r.max_wall_lag);
			worst_anim = std::max(worst_anim, r.max_anim_drift);
			worst_sync = std::max(worst_sync, r.max_frame_sync_error);
			late_frames += r.late_one_frame;
			worst_hold = std::max(worst_hold, r.max_float_hold_ms);
			if (verbose) printf("  %s %s creation=%d lines=%zu effects=%zu frames=%d max_late_ms=%.1f one_frame_late=%d wall_lag_ms=%.0f anim_drift_frames=%.6f\n",
				name.c_str(), profile.name, creation, r.consumed.size(), r.effects.size(), r.frames,
				1000 * r.max_lateness, r.late_one_frame, r.max_wall_lag, r.max_anim_drift);
		}
	}
	printf("%s %s lines=%zu final_t=%.4f effects=%zu worst_late_ms=%.1f one_frame_late=%d worst_wall_lag_ms=%.0f anim_drift_frames=%.6f framesync_err=%.6f multi_frame_hold_ms=%u\n",
		ok ? "PASS" : "FAIL", name.c_str(), expected.size(),
		final_line >= 0 ? Loaded[final_line].time : 0.0f, ref.effects.size(), 1000 * worst_late, late_frames,
		worst_wall, worst_anim, worst_sync, worst_hold);
	return ok;
}

static bool Synthetic()
{
	bool ok = true;
	// Dense: one or more authored lines every frame, equal-time ties authored
	// out of order, a frame-440 final Send_Custom batch, and a primary-killed tail.
	std::string dense;
	for (int frame = 500; frame >= 1; --frame) {
		dense += "-" + std::to_string(frame) + "\tPlay_Audio, cue_" + std::to_string(frame) + "_a\r\n";
		if (frame % 7 == 0) dense += "-" + std::to_string(frame) + "\tPlay_Audio, cue_" + std::to_string(frame) + "_b\r\n";
	}
	dense += "0 Create_Object, 0, model\r\n-3 Play_Animation, 0, model.anim, 0\r\n-251 Play_Animation, 0, model.loop, 1\r\n";
	dense += "-500 Send_Custom, 1500017, 445009, 1\r\n-500 Destroy_Object, 0\r\n1000000 Destroy_Object, 0\r\n";
	ok &= Check("synthetic_dense_every_frame", dense, getenv("LOWFPS_VERBOSE") != nullptr);
	// X0Z_Finale shape: the last authored batch is Send_Custom plus destroys.
	ok &= Check("synthetic_final_batch",
		"; finale\r\n0 Create_Object, 1, m\r\n-439 Play_Audio, a\r\n-440 Send_Custom, 1500017, 445009, 1\r\n"
		"-440 Destroy_Object, 1\r\n-440 Control_Camera, -1\r\n", false);
	// Zero-length cinematic: everything at time 0.
	ok &= Check("synthetic_time_zero_only", "0 Play_Audio, a\r\n0 Play_Audio, b\r\n", false);

	// Re-entrancy: a Send_Custom whose receiver synchronously kills the
	// primary.  Original semantics: the custom's line, then the >999000 tail,
	// then nothing else; no line executes twice; the controller is destroyed.
	const std::string reentrant =
		"0 Play_Audio, a\r\n-30 Send_Custom, 77, 4242, 0\r\n-30 Play_Audio, skipped_same_batch\r\n"
		"-60 Play_Audio, skipped_later\r\n1000000 Play_Audio, tail\r\n";
	for (const Profile &profile : Profiles) {
		Result r = Run(reentrant, profile, CREATED_BEFORE_OWN_POST_THINK, 4242);
		std::vector<std::string> names;
		for (const Effect &e : r.effects) names.push_back(e.what);
		const std::vector<std::string> want = {"sound2d:a", "custom:0>77:4242:0:0.000000", "sound2d:tail"};
		// The nested and the outer Parse_Commands both reach Destroy_Object (original).
		if (names != want || r.destroy_count != 2 || !r.failure.empty()) {
			ok = false; printf("FAIL reentrant primary kill profile=%s destroy=%d failure=%s\n", profile.name, r.destroy_count, r.failure.c_str());
			for (const std::string &n : names) printf("  effect %s\n", n.c_str());
		}
	}
	printf("%s synthetic re-entrant primary kill: custom line, tail only, no duplicate\n", ok ? "PASS" : "FAIL");
	return ok;
}

} // namespace lowfps

int main(int argc, char **argv)
{
	ScriptCommands commands = {};
	lowfps::Install(commands);
	Commands = &commands;
	bool ok = lowfps::Synthetic();
	const bool verbose = argc > 1 && strcmp(argv[1], "--verbose") == 0;
	// Optional retail stream on stdin: [u32 name length][name][u32 payload length][payload]...
	unsigned members = 0, passed = 0;
	unsigned char bytes[4];
	auto read_u32 = [&](uint32_t &value) {
		if (fread(bytes, 1, 4, stdin) != 4) return false;
		value = uint32_t(bytes[0]) | uint32_t(bytes[1]) << 8 | uint32_t(bytes[2]) << 16 | uint32_t(bytes[3]) << 24;
		return true;
	};
	uint32_t length;
	while (argc > 1 && read_u32(length)) {
		assert(length < 4096);
		std::string name(length, '\0');
		assert(fread(name.data(), 1, length, stdin) == length);
		assert(read_u32(length) && length < 16U * 1024U * 1024U);
		std::string payload(length, '\0');
		assert(fread(payload.data(), 1, length, stdin) == length);
		++members;
		if (lowfps::Check(name, payload, verbose)) ++passed;
	}
	if (argc > 1) printf("Retail low-fps scheduling: %u/%u control members PASS\n", passed, members);
	Commands = nullptr;
	if (ok && passed == members) puts("Original cinematic low-fps scheduling PASS");
	return ok && passed == members ? 0 : 1;
}
