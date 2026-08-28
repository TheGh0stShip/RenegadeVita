#include "binkmovie.h"
#include "a4_frontend_lifecycle_boundary.h"

#if defined(RENEGADE_HOST_ABI_TEST)
#include <stdio.h>
#else
#include "vita/a30_vita_runtime.h"
#endif

namespace {

bool g_initialized = false;

void Log_Unsupported_Playback(const char *filename)
{
#if defined(RENEGADE_HOST_ABI_TEST)
	fprintf(stderr,
		"A4 Bink boundary: playback skipped (%s); decoder provider unavailable; original menu route continues\n",
		filename != NULL ? filename : "unnamed");
#else
	A30_Vita_Log(
		"A4 Bink boundary: playback skipped (%s); decoder provider unavailable; original menu route continues\n",
		filename != NULL ? filename : "unnamed");
#endif
}

} // namespace

void BINKMovie::Init()
{
	g_initialized = true;
	A4_Frontend_Record_Bink_Init(true);
}

void BINKMovie::Shutdown()
{
	g_initialized = false;
	A4_Frontend_Record_Bink_Init(false);
}

void BINKMovie::Play(const char *filename, const char *, FontCharsClass *)
{
	A4_Frontend_Record_Bink_Play(filename);
	Log_Unsupported_Playback(filename);
	A4_Frontend_Record_Bink_Skip(filename);
}

void BINKMovie::Stop() {}
void BINKMovie::Update() {}
void BINKMovie::Render() {}

bool BINKMovie::Is_Complete()
{
	return true;
}
