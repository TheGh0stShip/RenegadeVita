#pragma once

#include "Threads.h"
#include "refcount.h"
#include "mss.h"
#include "WWAudio.h"
#include "SoundScene.h"
#include "LogicalSound.h"
#include "Sound3D.h"
#include "renegade_miles_test.h"
#include <algorithm>
#include <vector>
#include <cstring>
#include <atomic>
#include <chrono>
#include <thread>
#include <cstdio>

namespace AudioReleaseProbe {
template<class Base>
struct SceneOwnedSound : Base {
	unsigned &destroyed;
	explicit SceneOwnedSound(unsigned &count) : destroyed(count) {}
	~SceneOwnedSound() override { ++destroyed; }
};

inline int Run_Audible_Removal() {
	WWAudioClass audio(false);
	audio.Initialize();
	if (audio.Get_Sound_Scene() == nullptr) return 2;
	WWAudioThreadsClass::Flush_Delayed_Release_Objects();
	unsigned destroyed = 0;
	for (unsigned kind = 0; kind < 3; ++kind) {
		AudibleSoundClass *sound = nullptr;
		if (kind == 0) {
			sound = new SceneOwnedSound<AudibleSoundClass>(destroyed);
		} else {
			auto *spatial = new SceneOwnedSound<Sound3DClass>(destroyed);
			spatial->Make_Static(kind == 1);
			sound = spatial;
		}
		// No sample or play-list reference: the scene must be the final owner.
		sound->Set_Position(Vector3(10000.0f, 0.0f, 0.0f));
		sound->Add_To_Scene(false);
		if (sound->Peek_Cullable_Wrapper() == nullptr) {
			sound->Release_Ref();
			return 2;
		}
		sound->Release_Ref();
		std::fprintf(stderr, "audio_audible_removal=removing kind=%u\n", kind);
		sound->Remove_From_Scene();
		if (destroyed != kind + 1) return 1;
	}
	std::printf("audio_audible_removal=finished destroyed=%u\n", destroyed);
	return destroyed == 3 ? 0 : 1;
}

inline unsigned completed_callback_count = 0;
inline void _stdcall Count_Completed_Callback(SoundSceneObjClass *, uint32) {
	++completed_callback_count;
}

inline int Run_Completed_Sounds() {
	WWAudioClass audio(false);
	audio.Initialize();
	completed_callback_count = 0;
	audio.Register_EOS_Callback(Count_Completed_Callback, 0);
	unsigned destroyed = 0;
	for (unsigned restart_before_cleanup = 0; restart_before_cleanup < 2; ++restart_before_cleanup) {
		auto *sound = new SceneOwnedSound<AudibleSoundClass>(destroyed);
		// Use the original playlist/state transitions without requiring an asset.
		for (unsigned repeat = 0; repeat < 3; ++repeat) {
			if (!sound->Play(false) || !sound->Stop()) return 2;
		}
		if (restart_before_cleanup && !sound->Play(false)) return 2;
		sound->Release_Ref();
		std::fprintf(stderr, "audio_completed_sounds=cleanup restarted=%u\n", restart_before_cleanup);
		audio.On_Frame_Update(16);
		if (restart_before_cleanup) {
			if (destroyed != 1 || sound->Get_State() != AudibleSoundClass::STATE_PLAYING) return 1;
			if (!sound->Stop()) return 2;
			audio.On_Frame_Update(16);
		}
		if (destroyed != restart_before_cleanup + 1) return 1;
	}
	audio.UnRegister_EOS_Callback(Count_Completed_Callback);
	std::printf("audio_completed_sounds=finished destroyed=%u callbacks=%u\n",
		destroyed, completed_callback_count);
	return destroyed == 2 && completed_callback_count == 7 ? 0 : 1;
}

inline int Run_Continuous_Removal() {
	std::vector<unsigned char> wave(44 + 960, 0);
	auto put = [&](size_t offset, uint32_t value, unsigned bytes) {
		for (unsigned i = 0; i < bytes; ++i) wave[offset + i] = (value >> (8 * i)) & 255;
	};
	std::memcpy(wave.data(), "RIFF", 4);
	put(4, wave.size() - 8, 4);
	std::memcpy(wave.data() + 8, "WAVEfmt ", 8);
	put(16, 16, 4); put(20, 1, 2); put(22, 1, 2);
	put(24, 48000, 4); put(28, 96000, 4); put(32, 2, 2); put(34, 16, 2);
	std::memcpy(wave.data() + 36, "data", 4);
	put(40, 960, 4);
	for (size_t i = 44; i < wave.size(); i += 2) put(i, 4096, 2);
	WWAudioClass audio(false);
	audio.Initialize();
	Sound3DClass *sound = audio.Create_3D_Sound("continuous_probe.wav", wave.data(), wave.size());
	if (!sound) return 2;
	sound->Set_Loop_Count(0);
	sound->Add_To_Scene();
	sound->Play();
	int16_t output[2048] = {};
	bool passed = Renegade_Miles_Mix_For_Test(output, 1024) &&
		std::any_of(std::begin(output), std::end(output), [](int16_t v) { return v != 0; });
	// Match BeaconGameObj::Stop_Armed_Sound, without skipping scene ownership.
	sound->Remove_From_Scene();
	sound->Release_Ref();
	audio.On_Frame_Update(16);
	passed = Renegade_Miles_Mix_For_Test(output, 1024) && passed;
	passed = std::all_of(std::begin(output), std::end(output), [](int16_t v) { return v == 0; }) && passed;
	AudibleSoundClass *ending = audio.Create_Sound_Effect("ending_probe.wav", wave.data(), wave.size());
	if (!ending) return 2;
	ending->Play();
	passed = Renegade_Miles_Mix_For_Test(output, 1024) && passed;
	passed = std::any_of(std::begin(output), std::end(output), [](int16_t v) { return v != 0; }) && passed;
	passed = Renegade_Miles_Mix_For_Test(output, 1024) && passed;
	passed = std::all_of(std::begin(output), std::end(output), [](int16_t v) { return v == 0; }) && passed;
	ending->Stop();
	ending->Release_Ref();
	std::printf("audio_continuous_removal=%s\n", passed ? "passed" : "failed");
	return passed ? 0 : 1;
}

struct LogicalObject : LogicalSoundClass {
	unsigned &destroyed;
	explicit LogicalObject(unsigned &count) : destroyed(count) {}
	~LogicalObject() override { ++destroyed; }
};

inline int Run_Logical_Removal() {
	WWAudioClass audio(false);
	audio.Initialize();
	if (audio.Get_Sound_Scene() == nullptr) return 2;
	// Exercise immediate release, also reached after audio shutdown/recreation.
	WWAudioThreadsClass::Flush_Delayed_Release_Objects();
	unsigned destroyed = 0;
	for (unsigned i = 0; i < 3; ++i) {
		LogicalObject *sound = new LogicalObject(destroyed);
		sound->Set_Single_Shot(true);
		sound->Add_To_Scene();
		sound->Set_Listener_Timestamp(0);
		sound->Release_Ref();
	}
	audio.Get_Sound_Scene()->Collect_Logical_Sounds(0);
	std::printf("audio_logical_removal=finished destroyed=%u\n", destroyed);
	return destroyed == 3 ? 0 : 1;
}

struct Object : RefCountClass {
	std::atomic<bool> *entered;
	std::atomic<unsigned> &destroyed;
	Object(std::atomic<bool> *flag, std::atomic<unsigned> &count)
		: entered(flag), destroyed(count) {}
	~Object() override {
		if (entered) entered->store(true);
		AIL_lock();
		++destroyed;
		AIL_unlock();
	}
};

inline int Run_Flush_Enqueue() {
	std::atomic<unsigned> destroyed{0};
	std::atomic<unsigned> ready{0};
	std::atomic<bool> go{false};
	// Start the worker before racing producers, isolating the queue/flush contract.
	WWAudioThreadsClass::Add_Delayed_Release_Object(new Object(nullptr, destroyed), 60000);
	std::vector<std::thread> producers;
	for (unsigned producer = 0; producer < 4; ++producer) {
		producers.emplace_back([&] {
			++ready;
			while (!go.load()) std::this_thread::yield();
			for (unsigned i = 0; i < 512; ++i)
				WWAudioThreadsClass::Add_Delayed_Release_Object(new Object(nullptr, destroyed), 60000);
		});
	}
	while (ready.load() != 4) std::this_thread::yield();
	go.store(true);
	WWAudioThreadsClass::Flush_Delayed_Release_Objects();
	for (auto &producer : producers) producer.join();
	// Check before End's additional flush can conceal a stranded late enqueue.
	const unsigned after_flush = destroyed.load();
	WWAudioThreadsClass::End_Delayed_Release_Thread();
	std::printf("audio_flush_enqueue=finished destroyed_before_end=%u expected=2049\n", after_flush);
	return after_flush == 2049 ? 0 : 1;
}

inline int Run() {
	std::atomic<bool> entered{false};
	std::atomic<unsigned> destroyed{0};
	AIL_lock();
	WWAudioThreadsClass::Add_Delayed_Release_Object(new Object(&entered, destroyed), 0);
	const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
	while (!entered.load() && std::chrono::steady_clock::now() < deadline)
		std::this_thread::sleep_for(std::chrono::milliseconds(1));
	if (!entered.load()) {
		AIL_unlock();
		WWAudioThreadsClass::End_Delayed_Release_Thread();
		return 2;
	}
	// The worker is inside destruction, waiting for our audio lock. Enqueue
	// must not wait for a list lock retained by that destructor.
	std::fprintf(stderr, "audio_release_probe=worker_destructor_entered\n");
	WWAudioThreadsClass::Add_Delayed_Release_Object(new Object(nullptr, destroyed), 0);
	AIL_unlock();
	WWAudioThreadsClass::End_Delayed_Release_Thread();
	std::printf("audio_release_probe=finished destroyed=%u\n", destroyed.load());
	return destroyed.load() == 2 ? 0 : 1;
}
}
