#pragma once

// Root of every writable Renegade Vita path (settings, saves, logs,
// screenshots). Retail data stays read-only under ux0:data/renegade/retail.
// The VitaD3D graphics variant uses its own root so it never shares writable
// state with the default build.
#ifndef RENEGADE_VITA_USER_ROOT
#define RENEGADE_VITA_USER_ROOT "ux0:data/renegade/user"
#endif
