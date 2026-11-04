// Only the A2.2 host asset probe links this file. It retains original animation
// sound lookup but has no WWAudio device or Vita offscreen render target.
#if !defined(RENEGADE_HOST_ABI_TEST) || defined(__vita__)
#error Host asset device boundary must never enter the Vita target
#endif

#include "wwaudio.h"
#include <stdio.h>
#include <stdlib.h>

WWAudioClass *WWAudioClass::_theInstance = NULL;

int WWAudioClass::Create_Instant_Sound(int, const Matrix3D &, RefCountClass *,
	uint32, int)
{
	fputs("A2.2 asset probe unexpectedly requested an audio device\n", stderr);
	abort();
}

// The surface/target implementation lives in the native gameplay boundary,
// which this headless probe does not select. No offscreen target can be held.
void RenegadeVita_Release_DX8_Render_Target() {}
