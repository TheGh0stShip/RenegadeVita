#pragma once

#include <stdint.h>

// The FFmpeg provider uses int-sized enums; original engine objects use the
// Vita short-enum ABI. Only opaque pointers and explicit-width scalars cross
// this interface. In particular, do not include subtitlemanager.h here.
class FontCharsClass;
struct RenegadeMovieSubtitles;

extern "C" {
RenegadeMovieSubtitles *Renegade_Movie_Subtitles_Create(
	const char *movie_name, const char *subtitle_name, FontCharsClass *font);
void Renegade_Movie_Subtitles_Process(RenegadeMovieSubtitles *subtitles,
	uint32_t ticks);
void Renegade_Movie_Subtitles_Render(RenegadeMovieSubtitles *subtitles);
void Renegade_Movie_Subtitles_Destroy(RenegadeMovieSubtitles *subtitles);
}

// The released subtitle owner consumes 60-Hz ticks. Derive these from the
// displayed video's normalized PTS, never the decoder's read-ahead count.
// Divide first so even an invalid UINT64_MAX timestamp cannot wrap.
inline uint32_t Renegade_Movie_Subtitle_Ticks(uint64_t presentation_us)
{
	const uint64_t seconds = presentation_us / UINT64_C(1000000);
	if (seconds > UINT32_MAX / UINT64_C(60)) return UINT32_MAX;
	const uint64_t ticks = seconds * UINT64_C(60) +
		(presentation_us % UINT64_C(1000000)) * UINT64_C(60) /
		UINT64_C(1000000);
	return ticks > UINT32_MAX ? UINT32_MAX : static_cast<uint32_t>(ticks);
}
