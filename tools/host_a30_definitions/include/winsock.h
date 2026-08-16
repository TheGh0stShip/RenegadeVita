#pragma once

/* Header-only compatibility needed by networking types pulled transitively
 * into the non-networked world-load proof. Actual networking remains disabled
 * at its subsystem boundary. Keep the canonical centralized socket spellings. */
#include "../../../port/compatibility/include/winsock.h"
