#pragma once

/*
 * The pinned tree was authored for a case-insensitive filesystem:
 * Combat/savegame.cpp includes "audiosaveload.h", while the canonical file is
 * WWAudio/AudioSaveLoad.h.  Keep that source pristine and make the filename
 * compatibility explicit in this host integration target.
 */
/* The workspace is on Windows/DrvFs, where changing only the filename case
 * resolves this shim again. Use the explicit canonical staged path so pragma
 * once cannot turn the compatibility include into an empty self-include. */
#include "../../../staging/wwaudio/AudioSaveLoad.h"
