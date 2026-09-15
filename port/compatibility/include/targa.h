#pragma once

// All translation units must use the patched disk layout, irrespective of
// include search order or a cached dependency on the pristine upstream header.
// Keep this an explicit forwarding boundary, like audiosaveload.h.
#include "../../../staging/wwlib/TARGA.H"
