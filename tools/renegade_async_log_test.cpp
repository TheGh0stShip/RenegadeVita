// Host contract for the background runtime-log writer ring.
#include <atomic>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>
#include <vector>

#include "renegade_async_log.h"

namespace {

struct Sink {
	pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
	std::string written;
	size_t synced_bytes = 0U;
	unsigned syncs = 0U;
	std::atomic<bool> blocked{false};
	std::atomic<unsigned> write_delay_us{0U};
};

bool Write(void *context, const char *data, unsigned length)
{
	Sink &sink = *static_cast<Sink *>(context);
	while (sink.blocked.load()) std::this_thread::sleep_for(std::chrono::microseconds(200));
	if (sink.write_delay_us.load() != 0U)
		std::this_thread::sleep_for(std::chrono::microseconds(sink.write_delay_us.load()));
	pthread_mutex_lock(&sink.mutex);
	sink.written.append(data, length);
	pthread_mutex_unlock(&sink.mutex);
	return true;
}

bool Sync(void *context)
{
	Sink &sink = *static_cast<Sink *>(context);
	pthread_mutex_lock(&sink.mutex);
	sink.synced_bytes = sink.written.size();
	++sink.syncs;
	pthread_mutex_unlock(&sink.mutex);
	return true;
}

struct Writer {
	RenegadeAsyncLogRing *ring;
	uint32_t interval_ms;
	std::thread thread;
	void Start() {
		ring->Mark_Running();
		thread = std::thread([this]() { ring->Run(interval_ms); });
	}
	void Stop() { ring->Stop(); thread.join(); }
};

void Test_Order_Completeness_And_Flush()
{
	static RenegadeAsyncLogRing ring;
	Sink sink;
	sink.write_delay_us = 50U;
	ring.Configure(Write, Sync, &sink);
	Writer writer{&ring, 1000U, {}};
	writer.Start();
	const unsigned producers = 4U, lines = 2000U;
	std::vector<std::thread> threads;
	for (unsigned producer = 0U; producer < producers; ++producer) {
		threads.emplace_back([producer]() {
			for (unsigned line = 0U; line < lines; ++line) {
				char text[64];
				const int count = snprintf(text, sizeof(text), "p%u l%u\n", producer, line);
				while (!ring.Enqueue(text, static_cast<unsigned>(count)))
					std::this_thread::yield();
			}
		});
	}
	for (std::thread &thread : threads) thread.join();
	// Producers retried any drop above; account for the reported notes.
	ring.Flush();
	pthread_mutex_lock(&sink.mutex);
	const std::string written = sink.written;
	assert(sink.synced_bytes == written.size());
	pthread_mutex_unlock(&sink.mutex);
	std::vector<unsigned> next(producers, 0U);
	size_t offset = 0U;
	unsigned notes = 0U;
	while (offset < written.size()) {
		const size_t end = written.find('\n', offset);
		assert(end != std::string::npos);
		const std::string line = written.substr(offset, end - offset);
		offset = end + 1U;
		if (line.rfind("[runtime-log] dropped", 0) == 0) { ++notes; continue; }
		unsigned producer = 0U, number = 0U;
		assert(sscanf(line.c_str(), "p%u l%u", &producer, &number) == 2);
		assert(producer < producers && number == next[producer]);
		++next[producer];
	}
	for (unsigned producer = 0U; producer < producers; ++producer) assert(next[producer] == lines);
	assert(notes == 0U || ring.Dropped() != 0U);
	writer.Stop();
	// After the writer stops, Flush must not wait forever.
	ring.Flush();
}

void Test_Overflow_Never_Blocks_And_Is_Reported()
{
	static RenegadeAsyncLogRing ring;
	Sink sink;
	sink.blocked = true;
	ring.Configure(Write, Sync, &sink);
	Writer writer{&ring, 5U, {}};
	writer.Start();
	char line[1024];
	memset(line, 'x', sizeof(line));
	line[sizeof(line) - 1U] = '\n';
	unsigned accepted = 0U, dropped = 0U;
	const auto start = std::chrono::steady_clock::now();
	for (unsigned i = 0U; i < 1024U; ++i) {
		if (ring.Enqueue(line, sizeof(line))) ++accepted; else ++dropped;
	}
	const auto elapsed = std::chrono::steady_clock::now() - start;
	assert(std::chrono::duration_cast<std::chrono::milliseconds>(elapsed).count() < 500);
	assert(dropped != 0U && accepted >= RenegadeAsyncLogRing::Capacity / sizeof(line) - 16U);
	assert(!ring.Enqueue(line, RenegadeAsyncLogRing::Capacity + 1U));
	sink.blocked = false;
	const char tail[] = "tail line\n";
	while (!ring.Enqueue(tail, sizeof(tail) - 1U)) std::this_thread::yield();
	ring.Flush();
	pthread_mutex_lock(&sink.mutex);
	const std::string written = sink.written;
	pthread_mutex_unlock(&sink.mutex);
	const size_t note = written.find("[runtime-log] dropped lines while the writer was behind: ");
	assert(note != std::string::npos);
	assert(written.find("tail line\n") > note);
	assert(written.size() >= static_cast<size_t>(accepted) * sizeof(line));
	writer.Stop();
}

void Test_Sync_Cadence_Is_Bounded()
{
	static RenegadeAsyncLogRing ring;
	Sink sink;
	ring.Configure(Write, Sync, &sink);
	Writer writer{&ring, 100U, {}};
	writer.Start();
	for (unsigned i = 0U; i < 200U; ++i) {
		ring.Enqueue("trickle\n", 8U);
		std::this_thread::sleep_for(std::chrono::milliseconds(2));
	}
	std::this_thread::sleep_for(std::chrono::milliseconds(250));
	pthread_mutex_lock(&sink.mutex);
	const unsigned syncs = sink.syncs;
	const bool all_synced = sink.synced_bytes == sink.written.size() &&
		sink.written.size() == 200U * 8U;
	pthread_mutex_unlock(&sink.mutex);
	// ~400 ms of trickle at a 100 ms cadence: a handful of syncs, not 200,
	// and the quiet period syncs everything without an explicit flush.
	assert(syncs >= 2U && syncs <= 12U);
	assert(all_synced);
	writer.Stop();
}

void Test_Flush_Without_Writer_Returns()
{
	static RenegadeAsyncLogRing ring;
	ring.Flush();
	assert(ring.Enqueue("queued\n", 7U));
	ring.Flush();
}

} // namespace

int main()
{
	Test_Order_Completeness_And_Flush();
	Test_Overflow_Never_Blocks_And_Is_Reported();
	Test_Sync_Cadence_Is_Bounded();
	Test_Flush_Without_Writer_Returns();
	std::puts("Async runtime log ring host contract PASS");
	return 0;
}
