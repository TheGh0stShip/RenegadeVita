// Prepared probe of the original ThreadClass. Not compiled under the build hold.
#include "thread.h"

#include <atomic>
#include <chrono>
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <thread>

namespace {
std::atomic<bool> release_start(false), fail_create(false), stop_returned(false);

struct Start {
	void *(*function)(void *);
	void *argument;
};

void *Gated_Start(void *value)
{
	Start *start = static_cast<Start *>(value);
	while (!release_start.load()) std::this_thread::yield();
	const Start call = *start;
	delete start;
	return call.function(call.argument);
}

class Probe : public ThreadClass {
public:
	Probe() : ThreadClass("publication probe"), payload(0U), work(0U) {}
	uint32_t payload;
	uint32_t work;
	bool Wants_Run() const { return Should_Run(); }
	unsigned Completed_ID() const { return ThreadID; } // read only after acquire completion
	void Thread_Function() override {
		if (Should_Run()) ++work;
		payload = UINT32_C(0x13579bdf); // ordinary worker write, published by completion
	}
};

template <typename Predicate> bool Await(Predicate predicate)
{
	const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(5);
	while (!predicate()) {
		if (std::chrono::steady_clock::now() >= deadline) return false;
		std::this_thread::yield();
	}
	return true;
}

bool Check(bool value, const char *message)
{
	if (!value) {
		fprintf(stderr, "thread publication probe failed: %s\n", message);
		// A failed lifecycle assertion must not enter a blocking destructor.
		_Exit(1);
	}
	return value;
}

void *Stopper(void *value)
{
	static_cast<Probe *>(value)->Stop();
	stop_returned.store(true);
	return NULL;
}
} // namespace

extern "C" int __real_pthread_create(pthread_t *, const pthread_attr_t *, void *(*)(void *), void *);
extern "C" int __wrap_pthread_create(pthread_t *thread, const pthread_attr_t *attributes,
	void *(*function)(void *), void *argument)
{
	if (fail_create.exchange(false)) return EAGAIN;
	Start *start = new Start{function, argument};
	const int status = __real_pthread_create(thread, attributes, Gated_Start, start);
	if (status != 0) delete start;
	return status;
}

int main()
{
	Probe probe;
	if (!Check(!probe.Is_Running() && !probe.Wants_Run() && probe.Completed_ID() == 0U,
		"initial idle state")) return 1;
	probe.Execute();
	if (!Check(probe.Is_Running(), "published before worker enters")) return 1;
	pthread_t stopper;
	if (!Check(__real_pthread_create(&stopper, NULL, Stopper, &probe) == 0,
		"stop observer")) return 1;
	if (!Check(Await([&] { return !probe.Wants_Run(); }) && !stop_returned.load(),
		"stop cancellation waits for worker completion")) return 1;
	release_start.store(true);
	pthread_join(stopper, NULL);
	if (!Check(!probe.Is_Running() && probe.work == 0U &&
		probe.payload == UINT32_C(0x13579bdf) && probe.Completed_ID() == 0U,
		"late startup preserves cancellation and terminal publication")) return 1;
	for (unsigned i = 0U; i < 50U; ++i) {
		probe.payload = 0U;
		probe.Execute();
		if (!Check(Await([&] { return !probe.Is_Running(); }) &&
			probe.payload == UINT32_C(0x13579bdf) && probe.Completed_ID() == 0U,
			"completion publishes payload and supports serialized reuse")) return 1;
	}
	fail_create.store(true);
	probe.Execute();
	if (!Check(!probe.Is_Running() && !probe.Wants_Run() && probe.Completed_ID() == 0U,
		"create failure clears both state flags")) return 1;
	puts("original ThreadClass publication probe: PASS");
	return 0;
}
