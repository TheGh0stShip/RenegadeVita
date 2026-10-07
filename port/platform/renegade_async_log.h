#pragma once

#include <pthread.h>
#include <stdint.h>
#include <string.h>
#include <time.h>

// Moves runtime-log file I/O off the game thread.
//
// Every log line used to be written (and the renderer breadcrumbs also
// sceIoSyncByFd'd) synchronously on the calling thread. On a Vita memory card
// a sync costs several to tens of milliseconds, and the periodic checkpoint
// lines therefore produced visible gameplay hitches. Producers now copy each
// complete line into a bounded ring under a short lock; one writer thread
// appends the ring to the file in order and syncs at a bounded cadence.
//
// Durability: the writer is independent of the game thread, so lines logged
// before a game-thread hang still reach the card. Flush() blocks until every
// line enqueued before it is written and synced, for orderly exit and fatal
// paths. If the writer cannot start, the caller falls back to direct writes.
class RenegadeAsyncLogRing {
public:
	enum { Capacity = 256U * 1024U };
	// Per-session byte cap on lines accepted into the log. Past the soft cap
	// only priority lines ([LIFECYCLE], FATAL, crash, Teardown, Overall:) are
	// accepted, from a reserve. Existing log files are never pruned/rotated.
	enum { Session_Soft_Cap = 32U * 1024U * 1024U, Session_Reserve = 256U * 1024U };

	// Sink callbacks run only on the writer thread (or inside Flush when the
	// writer never started). They return false on an unrecoverable failure.
	typedef bool (*WriteSink)(void *context, const char *data, unsigned length);
	typedef bool (*SyncSink)(void *context);

	RenegadeAsyncLogRing() : write_(NULL), sync_(NULL), context_(NULL),
		enqueued_(0U), written_(0U), synced_(0U), flush_target_(0U),
		dropped_(0U), dropped_reported_(0U), session_bytes_(0U), soft_cap_(Session_Soft_Cap),
		reserve_(Session_Reserve), suppressed_(0U), suppressed_reported_(0U),
		truncated_(false), stop_(false), running_(false), failed_(false) {
		pthread_mutex_init(&mutex_, NULL);
		pthread_cond_init(&data_, NULL);
		pthread_cond_init(&drained_, NULL);
	}

	void Configure(WriteSink write, SyncSink sync, void *context) {
		write_ = write;
		sync_ = sync;
		context_ = context;
	}

	// Test hook; production uses the defaults.
	void Set_Session_Cap(uint64_t soft_cap, uint64_t reserve) {
		pthread_mutex_lock(&mutex_);
		soft_cap_ = soft_cap;
		reserve_ = reserve;
		pthread_mutex_unlock(&mutex_);
	}
	uint64_t Suppressed() {
		pthread_mutex_lock(&mutex_);
		const uint64_t suppressed = suppressed_;
		pthread_mutex_unlock(&mutex_);
		return suppressed;
	}

	// Called by the owner after starting the writer thread successfully.
	void Mark_Running() {
		pthread_mutex_lock(&mutex_);
		running_ = !failed_;
		pthread_mutex_unlock(&mutex_);
	}
	bool Running() {
		pthread_mutex_lock(&mutex_);
		const bool running = running_;
		pthread_mutex_unlock(&mutex_);
		return running;
	}
	bool Failed() {
		pthread_mutex_lock(&mutex_);
		const bool failed = failed_;
		pthread_mutex_unlock(&mutex_);
		return failed;
	}

	// Copies one complete line. Never blocks on I/O. A line that does not fit
	// is counted and reported in order once space is available again.
	bool Enqueue(const char *data, unsigned length) {
		if (length == 0U) return true;
		pthread_mutex_lock(&mutex_);
		if (failed_) {
			pthread_mutex_unlock(&mutex_);
			return false;
		}
		if (session_bytes_ + length > soft_cap_) {
			const bool priority = Is_Priority(data, length);
			if (!truncated_) {
				truncated_ = true;
				static const char marker[] =
					"[runtime-log] TRUNCATED: session log cap reached; only priority lines follow\n";
				Append_Locked(marker, sizeof(marker) - 1U);
			}
			if (!priority || session_bytes_ + length > soft_cap_ + reserve_) {
				++suppressed_;
				pthread_mutex_unlock(&mutex_);
				// Suppression is a policy outcome, not a failure needing fallback.
				return true;
			}
		}
		const bool ok = Append_Locked(data, length);
		pthread_mutex_unlock(&mutex_);
		return ok;
	}

	// Blocks until everything enqueued before this call is written and synced.
	// Records the session's final suppressed-line count first.
	void Flush() {
		pthread_mutex_lock(&mutex_);
		if (suppressed_ != suppressed_reported_) {
			char note[96];
			const int count = Format_Count_Note(note, sizeof(note),
				"[runtime-log] suppressed lines past session cap: ", suppressed_);
			if (count > 0 && Append_Locked(note, static_cast<unsigned>(count)))
				suppressed_reported_ = suppressed_;
		}
		const uint64_t target = enqueued_;
		if (!running_) {
			pthread_mutex_unlock(&mutex_);
			return;
		}
		if (target > flush_target_) flush_target_ = target;
		pthread_cond_signal(&data_);
		while (running_ && synced_ < target) pthread_cond_wait(&drained_, &mutex_);
		pthread_mutex_unlock(&mutex_);
	}

private:
	static bool Contains(const char *data, unsigned length, const char *needle) {
		const unsigned n = static_cast<unsigned>(strlen(needle));
		for (unsigned i = 0U; i + n <= length; ++i)
			if (memcmp(data + i, needle, n) == 0) return true;
		return false;
	}
	static bool Is_Priority(const char *data, unsigned length) {
		return Contains(data, length, "[LIFECYCLE]") || Contains(data, length, "FATAL") ||
			Contains(data, length, "crash") || Contains(data, length, "Teardown") ||
			Contains(data, length, "Overall:");
	}
	// Caller holds mutex_. Copies into the ring without blocking.
	bool Append_Locked(const char *data, unsigned length) {
		const uint64_t used = enqueued_ - written_;
		if (length > Capacity || used + length > Capacity) {
			++dropped_;
			return false;
		}
		session_bytes_ += length;
		const uint32_t start = static_cast<uint32_t>(enqueued_ % Capacity);
		const uint32_t first = length < Capacity - start ? length : Capacity - start;
		memcpy(ring_ + start, data, first);
		if (first < length) memcpy(ring_, data + first, length - first);
		enqueued_ += length;
		pthread_cond_signal(&data_);
		return true;
	}

public:

	// Writer-thread body. Written lines are synced within sync_interval_ms,
	// immediately when a Flush() is waiting.
	void Run(uint32_t sync_interval_ms) {
		uint64_t last_sync_ms = Now_Ms();
		pthread_mutex_lock(&mutex_);
		while (!stop_) {
			// Producers may keep the ring nonempty indefinitely. Check durability
			// before draining another span, not only after the ring becomes empty.
			if (synced_ < written_ &&
				(flush_target_ > synced_ || Now_Ms() - last_sync_ms >= sync_interval_ms)) {
				const uint64_t target = written_;
				pthread_mutex_unlock(&mutex_);
				const bool ok = sync_ != NULL && sync_(context_);
				last_sync_ms = Now_Ms();
				pthread_mutex_lock(&mutex_);
				if (!ok) { failed_ = true; break; }
				if (target > synced_) synced_ = target;
				pthread_cond_broadcast(&drained_);
				continue;
			}
			// Report drops ahead of later lines, preserving the gap's position.
			if (dropped_reported_ != dropped_) {
				const uint64_t dropped = dropped_ - dropped_reported_;
				dropped_reported_ = dropped_;
				pthread_mutex_unlock(&mutex_);
				char note[96];
				const int count = Format_Drop_Note(note, sizeof(note), dropped);
				const bool ok = count > 0 && write_ != NULL &&
					write_(context_, note, static_cast<unsigned>(count));
				pthread_mutex_lock(&mutex_);
				if (!ok) { failed_ = true; break; }
				continue;
			}
			if (written_ != enqueued_) {
				// [written_, enqueued_) is never overwritten before written_
				// advances, so the contiguous span is written without a copy.
				const uint64_t available = enqueued_ - written_;
				const uint32_t start = static_cast<uint32_t>(written_ % Capacity);
				uint32_t length = available < Capacity - start ?
					static_cast<uint32_t>(available) : Capacity - start;
				pthread_mutex_unlock(&mutex_);
				const bool ok = write_ != NULL && write_(context_, ring_ + start, length);
				pthread_mutex_lock(&mutex_);
				if (!ok) { failed_ = true; break; }
				written_ += length;
				continue;
			}
			if (synced_ < written_) {
				const bool flush_waiting = flush_target_ > synced_;
				const uint64_t now = Now_Ms();
				if (!flush_waiting && now - last_sync_ms < sync_interval_ms) {
					Timed_Wait(static_cast<uint32_t>(sync_interval_ms - (now - last_sync_ms)));
					continue;
				}
				const uint64_t target = written_;
				pthread_mutex_unlock(&mutex_);
				const bool ok = sync_ != NULL && sync_(context_);
				last_sync_ms = Now_Ms();
				pthread_mutex_lock(&mutex_);
				if (!ok) { failed_ = true; break; }
				if (target > synced_) synced_ = target;
				pthread_cond_broadcast(&drained_);
				continue;
			}
			pthread_cond_wait(&data_, &mutex_);
		}
		running_ = false;
		pthread_cond_broadcast(&drained_);
		pthread_mutex_unlock(&mutex_);
	}

	void Stop() {
		pthread_mutex_lock(&mutex_);
		stop_ = true;
		pthread_cond_signal(&data_);
		pthread_mutex_unlock(&mutex_);
	}

	uint64_t Dropped() {
		pthread_mutex_lock(&mutex_);
		const uint64_t dropped = dropped_;
		pthread_mutex_unlock(&mutex_);
		return dropped;
	}

private:
	static int Format_Drop_Note(char *output, unsigned capacity, uint64_t dropped) {
		return Format_Count_Note(output, capacity,
			"[runtime-log] dropped lines while the writer was behind: ", dropped);
	}
	static int Format_Count_Note(char *output, unsigned capacity, const char *prefix, uint64_t dropped) {
		unsigned length = 0U;
		for (const char *p = prefix; *p != '\0' && length + 1U < capacity; ++p)
			output[length++] = *p;
		char digits[24];
		unsigned count = 0U;
		do {
			digits[count++] = static_cast<char>('0' + dropped % 10U);
			dropped /= 10U;
		} while (dropped != 0U && count < sizeof(digits));
		while (count != 0U && length + 2U < capacity) output[length++] = digits[--count];
		output[length++] = '\n';
		return static_cast<int>(length);
	}

	static uint64_t Now_Ms() {
		struct timespec now;
		clock_gettime(CLOCK_MONOTONIC, &now);
		return static_cast<uint64_t>(now.tv_sec) * 1000U +
			static_cast<uint64_t>(now.tv_nsec) / 1000000U;
	}

	void Timed_Wait(uint32_t milliseconds) {
		struct timespec deadline;
		clock_gettime(CLOCK_REALTIME, &deadline);
		deadline.tv_sec += milliseconds / 1000U;
		deadline.tv_nsec += static_cast<long>(milliseconds % 1000U) * 1000000L;
		if (deadline.tv_nsec >= 1000000000L) {
			deadline.tv_nsec -= 1000000000L;
			++deadline.tv_sec;
		}
		pthread_cond_timedwait(&data_, &mutex_, &deadline);
	}

	pthread_mutex_t mutex_;
	pthread_cond_t data_;
	pthread_cond_t drained_;
	WriteSink write_;
	SyncSink sync_;
	void *context_;
	uint64_t enqueued_;
	uint64_t written_;
	uint64_t synced_;
	uint64_t flush_target_;
	uint64_t dropped_;
	uint64_t dropped_reported_;
	uint64_t session_bytes_;
	uint64_t soft_cap_;
	uint64_t reserve_;
	uint64_t suppressed_;
	uint64_t suppressed_reported_;
	bool truncated_;
	bool stop_;
	bool running_;
	bool failed_;
	char ring_[Capacity];
};

// Vita runtime log entry points (port/platform/vita/vita_platform.cpp).
// Returns false when the line must be written synchronously by the caller.
bool Renegade_Runtime_Log_Enqueue(const char *line, unsigned length);
// Blocks until every enqueued line is on the card. No-op without a writer.
void Renegade_Runtime_Log_Flush();
