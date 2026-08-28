#pragma once

#include <stddef.h>
#include <stdint.h>

// Deterministic manual-mix entry point used only by the host provider test.
// Production output remains owned by the blocking sceAudioOut worker.
bool Renegade_Miles_Mix_For_Test(int16_t *stereo_output, size_t frames);
