#include "ww3d_vita_renderer.h"

#include <stdio.h>

namespace {

bool Check(bool condition, const char *label, unsigned &checks,
	unsigned &failures)
{
	++checks;
	if (!condition) {
		++failures;
	}
	printf("%s: %s\n", label, condition ? "PASS" : "FAIL");
	return condition;
}

} // namespace

int main()
{
	unsigned checks = 0;
	unsigned failures = 0;
	const RenegadeVitaRenderer::BackendLifecycleStatistics &initial =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(!initial.native_initialization_attempted &&
		!initial.native_backend_ready && !initial.logical_session_active &&
		initial.native_initialization_calls == 0U &&
		initial.logical_sessions == 0U && initial.logical_shutdowns == 0U,
		"fresh process renderer lifecycle", checks, failures);

	Check(RenegadeVitaRenderer::Initialize(),
		"first logical renderer session initializes", checks, failures);
	const RenegadeVitaRenderer::BackendLifecycleStatistics &first =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(first.native_initialization_attempted &&
		first.native_backend_ready && first.logical_session_active &&
		first.native_initialization_calls == 1U &&
		first.logical_sessions == 1U && first.logical_shutdowns == 0U,
		"first session owns exactly one native initialization", checks,
		failures);

	Check(RenegadeVitaRenderer::Initialize(),
		"active-session Initialize is idempotent", checks, failures);
	const RenegadeVitaRenderer::BackendLifecycleStatistics &idempotent_init =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(idempotent_init.native_initialization_calls == 1U &&
		idempotent_init.logical_sessions == 1U &&
		idempotent_init.logical_shutdowns == 0U,
		"idempotent Initialize does not create another session", checks,
		failures);

	RenegadeVitaRenderer::Shutdown();
	const RenegadeVitaRenderer::BackendLifecycleStatistics &first_shutdown =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(first_shutdown.native_backend_ready &&
		!first_shutdown.logical_session_active &&
		first_shutdown.native_initialization_calls == 1U &&
		first_shutdown.logical_sessions == 1U &&
		first_shutdown.logical_shutdowns == 1U,
		"logical shutdown preserves process-lifetime backend", checks,
		failures);

	RenegadeVitaRenderer::Shutdown();
	const RenegadeVitaRenderer::BackendLifecycleStatistics &idempotent_shutdown =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(idempotent_shutdown.logical_shutdowns == 1U,
		"inactive-session Shutdown is idempotent", checks, failures);

	Check(RenegadeVitaRenderer::Initialize(),
		"second logical renderer session reactivates", checks, failures);
	const RenegadeVitaRenderer::BackendLifecycleStatistics &second =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(second.native_initialization_calls == 1U &&
		second.logical_sessions == 2U && second.logical_shutdowns == 1U &&
		second.logical_session_active,
		"second session reuses the single native initialization", checks,
		failures);

	RenegadeVitaRenderer::Reset_Statistics();
	const RenegadeVitaRenderer::BackendLifecycleStatistics &after_reset =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(after_reset.native_initialization_calls == 1U &&
		after_reset.logical_sessions == 2U &&
		after_reset.logical_session_active,
		"frame-statistics reset preserves lifecycle state", checks, failures);

	RenegadeVitaRenderer::Shutdown();
	const RenegadeVitaRenderer::BackendLifecycleStatistics &final_state =
		RenegadeVitaRenderer::Get_Backend_Lifecycle_Statistics();
	Check(final_state.native_initialization_calls == 1U &&
		final_state.logical_sessions == 2U &&
		final_state.logical_shutdowns == 2U &&
		final_state.native_backend_ready &&
		!final_state.logical_session_active,
		"two logical sessions complete over one native backend", checks,
		failures);

	printf("A3 renderer process lifecycle: %u checks, %u failures; native=%u sessions=%u shutdowns=%u\n",
		checks, failures, final_state.native_initialization_calls,
		final_state.logical_sessions, final_state.logical_shutdowns);
	return failures == 0U ? 0 : 1;
}
