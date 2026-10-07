// AIL_set_3D_position publishes instead of waiting while another thread (the
// mixer) holds the provider lock. Deterministic interleavings check that it
// does not block, that a published position is applied in call order before
// anything observes it, and that released samples never stay queued. The
// provider is included directly to reach its internal state.
#include "../port/audio/vita/renegade_miles_provider.cpp"

#include <chrono>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <mutex>
#include <thread>
#include <vector>

#define CHECK(condition) do { if (!(condition)) { \
	std::fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #condition); \
	std::abort(); } } while (0)

namespace {

// Holds the provider lock on another thread, as the mixer does during a mix,
// until Release() (or a timeout, which the test reports as a blocked call).
class LockHolder {
public:
	explicit LockHolder(int release_delay_ms = 0) : delay_(release_delay_ms)
	{
		thread_ = std::thread([this] {
			AIL_lock();
			{
				std::unique_lock<std::mutex> guard(mutex_);
				held_ = true;
				changed_.notify_all();
				if (!changed_.wait_for(guard, std::chrono::seconds(20), [this] { return release_; }))
					timed_out_ = true;
			}
			if (delay_ > 0) std::this_thread::sleep_for(std::chrono::milliseconds(delay_));
			released_.store(true);
			AIL_unlock();
		});
		std::unique_lock<std::mutex> guard(mutex_);
		changed_.wait(guard, [this] { return held_; });
	}
	void Release()
	{
		{
			std::lock_guard<std::mutex> guard(mutex_);
			release_ = true;
		}
		changed_.notify_all();
	}
	~LockHolder()
	{
		Release();
		thread_.join();
		CHECK(!timed_out_);
	}
	bool Released() const { return released_.load(); }
private:
	int delay_;
	std::thread thread_;
	std::mutex mutex_;
	std::condition_variable changed_;
	bool held_ = false, release_ = false, timed_out_ = false;
	std::atomic<bool> released_{false};
};

std::vector<uint8_t> Pcm_Wave(uint32_t frames)
{
	const uint32_t data_bytes = frames * 2U;
	std::vector<uint8_t> image(44U + data_bytes);
	auto put32 = [&](size_t at, uint32_t value) {
		for (unsigned i = 0; i < 4U; ++i) image[at + i] = static_cast<uint8_t>(value >> (8U * i));
	};
	auto put16 = [&](size_t at, uint16_t value) {
		image[at] = static_cast<uint8_t>(value);
		image[at + 1U] = static_cast<uint8_t>(value >> 8U);
	};
	std::memcpy(&image[0], "RIFF", 4); put32(4, 36U + data_bytes);
	std::memcpy(&image[8], "WAVEfmt ", 8); put32(16, 16U);
	put16(20, 1U); put16(22, 1U); put32(24, 22050U);
	put32(28, 44100U); put16(32, 2U);
	put16(34, 16U); std::memcpy(&image[36], "data", 4); put32(40, data_bytes);
	for (uint32_t index = 0; index < frames; ++index)
		put16(44U + index * 2U, static_cast<uint16_t>((index * 2654435761U) >> 16U));
	return image;
}

S32 Expected_Pan(F32 x, F32 maximum)
{
	const F32 scale = std::max(1.0F, maximum);
	const F32 normalized = std::max(-1.0F, std::min(1.0F, x / scale));
	return static_cast<S32>(std::lround((normalized + 1.0F) * 63.5F));
}

void Check_Does_Not_Block_And_Applies_Before_Observation()
{
	H3DSAMPLE sample = AIL_allocate_3D_sample_handle(kNative3DProvider);
	CHECK(sample != nullptr);
	{
		LockHolder mixer;
		AIL_set_3D_position(sample, 30.0F, 1.0F, 2.0F);   // returns while held
		CHECK(!mixer.Released());
		CHECK(sample->position_pending && sample->position[0] == 0.0F);
	}
	// Any locked access applies it first.
	CHECK(AIL_sample_pan(sample) == Expected_Pan(30.0F, 100.0F));
	CHECK(!sample->position_pending && sample->position[0] == 30.0F &&
		sample->position[1] == 1.0F && sample->position[2] == 2.0F);
	AIL_release_3D_sample_handle(sample);
	std::printf("deferred position non-blocking PASS\n");
}

void Check_Call_Order_Is_Preserved()
{
	H3DSAMPLE sample = AIL_allocate_3D_sample_handle(kNative3DProvider);
	// Maximum distance changed after the position: pan uses the old distance.
	{
		LockHolder mixer;
		AIL_set_3D_position(sample, 50.0F, 0.0F, 0.0F);
	}
	AIL_set_3D_sample_distances(sample, 10.0F, 1.0F);
	CHECK(sample->pan == Expected_Pan(50.0F, 100.0F) && sample->pan == 95);
	// An explicit pan after the position wins.
	{
		LockHolder mixer;
		AIL_set_3D_position(sample, -5.0F, 0.0F, 0.0F);
	}
	AIL_set_sample_pan(sample, 3);
	CHECK(AIL_sample_pan(sample) == 3 && sample->position[0] == -5.0F);
	// Reinitialising after the position resets it.
	{
		LockHolder mixer;
		AIL_set_3D_position(sample, 7.0F, 8.0F, 9.0F);
	}
	AIL_init_sample(sample);
	CHECK(sample->position[0] == 0.0F && sample->pan == 64 && !sample->position_pending);
	// The last of several published positions wins, queued once.
	{
		LockHolder mixer;
		for (int step = 1; step <= 5; ++step)
			AIL_set_3D_position(sample, static_cast<F32>(step), 0.0F, 0.0F);
		CHECK(g_pending_position_count == 1U);
	}
	AIL_lock();
	CHECK(sample->position[0] == 5.0F && g_pending_position_count == 0U);
	AIL_unlock();
	// The caller already holding the lock (WWAudio MMSLockClass) applies directly.
	AIL_lock();
	AIL_set_3D_position(sample, 11.0F, 0.0F, 0.0F);
	CHECK(sample->position[0] == 11.0F && !sample->position_pending);
	AIL_unlock();
	// The listener handle is not a registered sample.
	H3DPOBJECT listener = AIL_3D_open_listener(kNative3DProvider);
	{
		LockHolder mixer;
		AIL_set_3D_position(listener, 4.0F, 0.0F, 0.0F);
	}
	AIL_lock();
	CHECK(listener->position[0] == 4.0F);
	AIL_unlock();
	AIL_release_3D_sample_handle(sample);
	std::printf("deferred position ordering PASS\n");
}

void Check_Mix_Uses_Published_Position()
{
	const std::vector<uint8_t> image = Pcm_Wave(4000U);
	H3DSAMPLE deferred = AIL_allocate_3D_sample_handle(kNative3DProvider);
	H3DSAMPLE direct = AIL_allocate_3D_sample_handle(kNative3DProvider);
	for (H3DSAMPLE sample : {deferred, direct}) {
		CHECK(AIL_set_3D_sample_file_bounded(sample, image.data(), image.size()) == 1U);
		AIL_set_3D_sample_distances(sample, 60.0F, 2.0F);
		AIL_set_3D_sample_volume(sample, 120);
	}
	AIL_set_3D_position(direct, -12.0F, 3.0F, 25.0F);
	{
		LockHolder mixer;
		AIL_set_3D_position(deferred, -12.0F, 3.0F, 25.0F);
	}
	int16_t a[512 * 2], b[512 * 2];
	AIL_start_3D_sample(deferred);
	CHECK(Renegade_Miles_Mix_For_Test(a, 512U));
	AIL_end_3D_sample(deferred);
	AIL_start_3D_sample(direct);
	CHECK(Renegade_Miles_Mix_For_Test(b, 512U));
	CHECK(std::memcmp(a, b, sizeof(a)) == 0);
	bool audible = false;
	for (int16_t value : a) audible |= value != 0;
	CHECK(audible);
	AIL_release_3D_sample_handle(deferred);
	AIL_release_3D_sample_handle(direct);
	std::printf("deferred position mix PASS\n");
}

void Check_Release_Forgets_Queued_Sample()
{
	H3DSAMPLE kept = AIL_allocate_3D_sample_handle(kNative3DProvider);
	H3DSAMPLE released = AIL_allocate_3D_sample_handle(kNative3DProvider);
	CHECK(Publish_Pending_Position(kept, 1.0F, 0.0F, 0.0F));
	CHECK(Publish_Pending_Position(released, 2.0F, 0.0F, 0.0F));
	// Raw lock: no application on entry, so the release sees a queued sample.
	pthread_mutex_lock(&g_mutex);
	Release_Sample(released);
	CHECK(g_pending_position_count == 1U && g_pending_positions[0] == kept);
	Apply_Pending_Positions_Locked();   // ASan: no use of the freed sample
	CHECK(kept->position[0] == 1.0F);
	pthread_mutex_unlock(&g_mutex);
	AIL_release_3D_sample_handle(kept);
	std::printf("deferred position release PASS\n");
}

void Check_Full_Queue_Falls_Back_To_Waiting()
{
	std::vector<H3DSAMPLE> samples;
	for (size_t index = 0; index <= kPendingPositionSlots; ++index)
		samples.push_back(AIL_allocate_3D_sample_handle(kNative3DProvider));
	{
		LockHolder mixer(100);
		for (size_t index = 0; index < kPendingPositionSlots; ++index)
			AIL_set_3D_position(samples[index], static_cast<F32>(index), 0.0F, 0.0F);
		CHECK(g_pending_position_count == kPendingPositionSlots);
		mixer.Release();
		// No free slot: this call waits for the lock like the original.
		AIL_set_3D_position(samples.back(), 999.0F, 0.0F, 0.0F);
		CHECK(mixer.Released());
		CHECK(samples.back()->position[0] == 999.0F && g_pending_position_count == 0U);
	}
	for (size_t index = 0; index < kPendingPositionSlots; ++index)
		CHECK(samples[index]->position[0] == static_cast<F32>(index));
	for (H3DSAMPLE sample : samples) AIL_release_3D_sample_handle(sample);
	std::printf("deferred position full queue PASS\n");
}

// A free-running mixer thread against random game-thread calls: whatever the
// interleaving, the observed state equals sequential application.
void Check_Concurrent_Mixer_Matches_Sequential()
{
	const std::vector<uint8_t> image = Pcm_Wave(3000U);
	constexpr int kVoices = 6;
	H3DSAMPLE samples[kVoices];
	for (H3DSAMPLE &sample : samples) {
		sample = AIL_allocate_3D_sample_handle(kNative3DProvider);
		CHECK(AIL_set_3D_sample_file_bounded(sample, image.data(), image.size()) == 1U);
		AIL_set_3D_sample_loop_count(sample, 0U);
		AIL_start_3D_sample(sample);
	}
	pthread_mutex_lock(&g_position_mutex);
	const uint64_t published_before = g_published_positions;
	pthread_mutex_unlock(&g_position_mutex);
	std::atomic<bool> stop{false};
	std::atomic<uint32_t> mixes{0U};
	std::thread mixer([&] {
		int16_t output[256 * 2];
		while (!stop.load()) {
			AIL_lock();
			Mix_Locked(output, 256U);
			AIL_unlock();
			mixes.fetch_add(1U);
		}
	});
	uint64_t state = 0x1234567ULL;
	auto next = [&state] {
		state = state * 6364136223846793005ULL + 1442695040888963407ULL;
		return static_cast<uint32_t>(state >> 33U);
	};
	struct Expected { F32 x = 0.0F, y = 0.0F, z = 0.0F, maximum = 100.0F; S32 pan = 64; };
	Expected expected[kVoices];
	uint32_t checks = 0U;
	for (int step = 0; step < 200000; ++step) {
		const int voice = static_cast<int>(next() % kVoices);
		H3DSAMPLE sample = samples[voice];
		Expected &model = expected[voice];
		const uint32_t action = next() % 16U;
		if (action < 12U) {
			model.x = static_cast<F32>(static_cast<int>(next() % 400U) - 200);
			model.y = static_cast<F32>(next() % 50U);
			model.z = static_cast<F32>(next() % 70U);
			AIL_set_3D_position(sample, model.x, model.y, model.z);
			model.pan = Expected_Pan(model.x, model.maximum);
		} else if (action == 12U) {
			model.maximum = static_cast<F32>(1U + next() % 150U);
			AIL_set_3D_sample_distances(sample, model.maximum, 1.0F);
		} else if (action == 13U) {
			model.pan = static_cast<S32>(next() % 128U);
			AIL_set_sample_pan(sample, model.pan);
		} else {
			CHECK(AIL_sample_pan(sample) == model.pan);
			AIL_lock();
			CHECK(sample->position[0] == model.x && sample->position[1] == model.y &&
				sample->position[2] == model.z && sample->maximum_distance == model.maximum);
			AIL_unlock();
			++checks;
		}
	}
	stop.store(true);
	mixer.join();
	pthread_mutex_lock(&g_position_mutex);
	const uint64_t published = g_published_positions - published_before;
	pthread_mutex_unlock(&g_position_mutex);
	CHECK(published != 0U);   // the interleaving reached the non-waiting path
	AIL_lock();
	for (int voice = 0; voice < kVoices; ++voice) {
		CHECK(samples[voice]->position[0] == expected[voice].x &&
			samples[voice]->pan == expected[voice].pan);
	}
	AIL_unlock();
	for (H3DSAMPLE sample : samples) AIL_release_3D_sample_handle(sample);
	std::printf("deferred position concurrent PASS mixes=%u checks=%u published=%llu\n",
		mixes.load(), checks, static_cast<unsigned long long>(published));
}

} // namespace

int main()
{
	AIL_startup();
	Check_Does_Not_Block_And_Applies_Before_Observation();
	Check_Call_Order_Is_Preserved();
	Check_Mix_Uses_Published_Position();
	Check_Release_Forgets_Queued_Sample();
	Check_Full_Queue_Falls_Back_To_Waiting();
	Check_Concurrent_Mixer_Matches_Sequential();
	AIL_shutdown();
	CHECK(g_pending_position_count == 0U);
	return 0;
}
