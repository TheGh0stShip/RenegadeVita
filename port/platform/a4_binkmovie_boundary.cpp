#include "binkmovie.h"

#if defined(RENEGADE_HOST_ABI_TEST)
#include <stdio.h>
#else
#include "vita/a30_vita_runtime.h"
#endif

namespace {

bool g_initialized = false;
bool g_notice_logged = false;

void Log_Unsupported_Playback(const char *filename)
{
	if (g_notice_logged) return;
	g_notice_logged = true;
#if defined(RENEGADE_HOST_ABI_TEST)
	fprintf(stderr, "A4 Bink boundary: playback skipped (%s); original menu route continues\n",
		filename != NULL ? filename : "unnamed");
#else
	A30_Vita_Log("A4 Bink boundary: playback skipped (%s); original menu route continues\n",
		filename != NULL ? filename : "unnamed");
#endif
}

} // namespace

void BINKMovie::Init()
{
	g_initialized = true;
}

void BINKMovie::Shutdown()
{
	g_initialized = false;
}

void BINKMovie::Play(const char *filename, const char *, FontCharsClass *)
{
	Log_Unsupported_Playback(filename);
}

void BINKMovie::Stop() {}
void BINKMovie::Update() {}
void BINKMovie::Render() {}

bool BINKMovie::Is_Complete()
{
	return true;
}
