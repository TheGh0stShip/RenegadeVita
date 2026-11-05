#include "renegade_movie_subtitles.h"
#include "subtitlemanager.h"

// Compile this owner with the engine's normal enum/wchar ABI. FFmpeg's
// -fno-short-enums is scoped to a4_binkmovie_boundary.cpp, which cannot see
// the manager's Render2DSentenceClass or any other engine object layout.
RenegadeMovieSubtitles *Renegade_Movie_Subtitles_Create(
	const char *movie_name, const char *subtitle_name, FontCharsClass *font)
{
	if (movie_name == NULL || subtitle_name == NULL || font == NULL) return NULL;
	return reinterpret_cast<RenegadeMovieSubtitles *>(
		SubTitleManagerClass::Create(movie_name, subtitle_name, font));
}

void Renegade_Movie_Subtitles_Process(RenegadeMovieSubtitles *subtitles,
	uint32_t ticks)
{
	if (subtitles != NULL) {
		reinterpret_cast<SubTitleManagerClass *>(subtitles)->Process(
			static_cast<unsigned long>(ticks));
	}
}

void Renegade_Movie_Subtitles_Render(RenegadeMovieSubtitles *subtitles)
{
	if (subtitles != NULL) {
		reinterpret_cast<SubTitleManagerClass *>(subtitles)->Render();
	}
}

void Renegade_Movie_Subtitles_Destroy(RenegadeMovieSubtitles *subtitles)
{
	delete reinterpret_cast<SubTitleManagerClass *>(subtitles);
}
