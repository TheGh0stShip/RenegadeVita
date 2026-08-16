#pragma once

/*
 * The pinned Windows source includes "audiosaveload.h" while the canonical
 * WWAudio header is AudioSaveLoad.h. On the DrvFS workspace a case-only alias
 * can self-include, so retain one explicit portable spelling at the platform
 * compatibility boundary rather than depending on a host-test include path.
 */
#include "../../../staging/wwaudio/AudioSaveLoad.h"
