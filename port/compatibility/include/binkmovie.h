#pragma once

// Original movie ownership remains above this boundary. The Vita provider
// decodes retail Bink streams through the pinned FFmpeg build. Missing or
// invalid files still complete cleanly into the authentic MainMenu route.
class FontCharsClass;

class BINKMovie
{
public:
	static void Play(const char *filename, const char *subtitle_name = NULL,
		FontCharsClass *font = NULL);
	static void Stop();
	static void Update();
	static void Render();
	static void Init();
	static void Shutdown();
	static bool Is_Complete();
};
