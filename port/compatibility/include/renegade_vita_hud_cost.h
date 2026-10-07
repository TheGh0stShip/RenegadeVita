#ifndef RENEGADE_VITA_HUD_COST_H
#define RENEGADE_VITA_HUD_COST_H

// HUD/2D presentation-cost switches (tutorial round 1, prefix RVHD1).
//
// ux0:data/renegade/user/config/hud-cost-v1.flag holds exactly "RVHD1 X\n",
// where X is one hex digit (0-9, A-F) giving a bit mask of enabled changes:
//
//   bit 0 (1)  TextWindowClass keeps the rows its height measurement just
//              built when the next view update would rebuild the very same
//              rows (message window: dialogue subtitles and objective
//              messages). See textwindow.cpp, Can_Keep_Measured_Build.
//
// Bits 1-3 are reserved and ignored. A missing, short, long or otherwise
// malformed file selects RENEGADE_VITA_HUD_COST_DEFAULT (all off). The file
// is read once, on the first query.

#include <stdio.h>
#include <string.h>

#if !defined(RENEGADE_VITA_HUD_COST_DEFAULT)
#define RENEGADE_VITA_HUD_COST_DEFAULT 0U
#endif

enum
{
	RENEGADE_VITA_HUD_COST_TEXTWINDOW_MEASURED_BUILD = 1U,
	RENEGADE_VITA_HUD_COST_KNOWN_BITS = 1U
};

// Strict "RVHD1 X\n" parse of the flag file contents; anything else returns
// fallback.
inline unsigned Renegade_Vita_HUD_Cost_Parse(const char *value, size_t size,
	unsigned fallback)
{
	if (value == NULL || size != 8U || memcmp(value, "RVHD1 ", 6U) != 0 ||
		value[7] != '\n') {
		return fallback;
	}
	const char digit = value[6];
	unsigned mode;
	if (digit >= '0' && digit <= '9') {
		mode = static_cast<unsigned>(digit - '0');
	} else if (digit >= 'A' && digit <= 'F') {
		mode = 10U + static_cast<unsigned>(digit - 'A');
	} else {
		return fallback;
	}
	return mode & RENEGADE_VITA_HUD_COST_KNOWN_BITS;
}

inline unsigned Renegade_Vita_HUD_Cost_Read()
{
	unsigned mode = RENEGADE_VITA_HUD_COST_DEFAULT & RENEGADE_VITA_HUD_COST_KNOWN_BITS;
	FILE *file = fopen("ux0:data/renegade/user/config/hud-cost-v1.flag", "rb");
	if (file != NULL) {
		char value[9] = {};
		const size_t size = fread(value, 1U, sizeof(value), file);
		const bool read_ok = !ferror(file);
		fclose(file);
		if (read_ok) {
			mode = Renegade_Vita_HUD_Cost_Parse(value, size, mode);
		}
	}
	return mode;
}

// The enabled bit mask. Game-thread HUD code only; read on first use.
inline unsigned Renegade_Vita_HUD_Cost_Mode()
{
	static const unsigned mode = Renegade_Vita_HUD_Cost_Read();
	return mode;
}

inline bool Renegade_Vita_HUD_Cost_Enabled(unsigned bit)
{
	return (Renegade_Vita_HUD_Cost_Mode() & bit) != 0U;
}

#endif
