#pragma once

// Original movie ownership remains above this boundary. Vita has no Bink
// decoder in this milestone, so the platform implementation completes any
// requested playback and lets the original state machine continue to its
// authentic MainMenu route.
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
