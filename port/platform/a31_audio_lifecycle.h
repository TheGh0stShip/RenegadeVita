#pragma once

/*
** A3.1 audio lifecycle probe.
**
** This is deliberately observability only.  WWAudioClass remains the original
** owner and StaticAudioSaveLoadClass retains its retail loading algorithm.
*/
struct A31AudioLifecycleTrace
{
	unsigned static_audio_load_entries;
	bool singleton_present_at_static_load;
	bool sound_scene_present_at_static_load;
};

void A31_Audio_Lifecycle_Reset_Trace();
A31AudioLifecycleTrace A31_Audio_Lifecycle_Get_Trace();
void A31_Audio_Save_Load_Breadcrumb(const char *stage);
