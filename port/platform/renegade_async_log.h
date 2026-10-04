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

	// Sink callbacks run only on the writer thread (or inside Flush when the
	// writer never started). They return false on an unrecoverable failure.
	typedef bool (*WriteSink)(void *context, const char *data, unsigned length);
	typedef bool (*SyncSink)(void *context);

	RenegadeAsyncLogRing() : write_(NULL), sync_(NULL), context_(NULL),
		enqueued_(0U), written_(0U), synced_(0U), flush_target_(0U),
		dropped_(0U), dropped_reported_(0U), stop_(false), running_(false) {
		pthread_mutex_init(&mutex_, NULL);
		pthread_cond_init(&data_, NULL);
		pthread_cond_init(&drained_, NULL);
	}

	void Configure(WriteSink write, SyncSink sync, void *context) {
		write_ = write;
		sync_ = sync;
		context_ = context;
	}

	// Called by the owner after starting the writer thread successfully.
	void Mark_Running() {
		pthread_mutex_lock(&mutex_);
		running_ = true;
		pthread_mutex_unlock(&mutex_);
	}
	bool Running() {
		pthread_mutex_lock(&mutex_);
		const bool running = running_;
		pthread_mutex_unlock(&mutex_);
		return running;
	}

	// Copies one complete line. Never blocks on I/O. A line that does not fit
	// is counted and reported in order once space is available again.
	bool Enqueue(const char *data, unsigned length) {
		if (length == 0U) return true;
		pthread_mutex_lock(&mutex_);
		const uint64_t used = enqueued_ - written_;
		if (length > Capacity || used + length > Capacity) {
			++dropped_;
			pthread_mutex_unlock(&mutex_);
			return false;
		}
		const uint32_t start = static_cast<uint32_t>(enqueued_ % Capacity);
		const uint32_t first = length < Capacity - start ? length : Capacity - start;
		memcpy(ring_ + start, data, first);
		if (first < length) memcpy(ring_, data + first, length - first);
		enqueued_ += length;
		pthread_cond_signal(&data_);
		pthread_mutex_unlock(&mutex_);
		return true;
	}

	// Blocks until everything enqueued before this call is written and synced.
	void Flush() {
		pthread_mutex_lock(&mutex_);
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

	// Writer-thread body. Written lines are synced within sync_interval_ms,
	// immediately when a Flush() is waiting.
	void Run(uint32_t sync_interval_ms) {
		uint64_t last_sync_ms = Now_Ms();
		pthread_mutex_lock(&mutex_);
		while (!stop_) {
			// Report drops ahead of later lines, preserving the gap's position.
			if (dropped_reported_ != dropped_) {
				const uint64_t dropped = dropped_ - dropped_reported_;
				dropped_reported_ = dropped_;
				pthread_mutex_unlock(&mutex_);
				char note[96];
				const int count = Format_Drop_Note(note, sizeof(note), dropped);
				if (count > 0 && write_ != NULL) write_(context_, note, static_cast<unsigned>(count));
				pthread_mutex_lock(&mutex_);
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
				if (write_ != NULL) write_(context_, ring_ + start, length);
				pthread_mutex_lock(&mutex_);
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
				if (sync_ != NULL) sync_(context_);
				last_sync_ms = Now_Ms();
				pthread_mutex_lock(&mutex_);
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
		static const char prefix[] = "[runtime-log] dropped lines while the writer was behind: ";
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
	bool stop_;
	bool running_;
	char ring_[Capacity];
};

// Vita runtime log entry points (port/platform/vita/vita_platform.cpp).
// Returns false when the line must be written synchronously by the caller.
bool Renegade_Runtime_Log_Enqueue(const char *line, unsigned length);
// Blocks until every enqueued line is on the card. No-op without a writer.
void Renegade_Runtime_Log_Flush();
