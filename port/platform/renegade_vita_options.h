#pragma once

#include "renegade_vita_user_settings.h"
#include "wwaudio.h"
#include "ww3d.h"
#include "pscene.h"
#include "surfaceeffects.h"

namespace RenegadeVitaOptions {
inline bool Save_Audio(WWAudioClass &audio)
{
	using namespace RenegadeVitaUserSettings;
	Record r = State().record;
	r.value[0] |= Audio;
	const float volumes[] = {audio.Get_Sound_Effects_Volume(), audio.Get_Music_Volume(),
		audio.Get_Dialog_Volume(), audio.Get_Cinematic_Volume()};
	for (int i = 0; i < 4; ++i) {
		if (!(volumes[i] >= 0 && volumes[i] <= 1)) return false;
		r.value[i + 1] = static_cast<unsigned>(volumes[i] * 100.0F + 0.5F);
	}
	r.value[5] = audio.Are_Sound_Effects_On();
	r.value[6] = audio.Is_Music_On();
	r.value[7] = audio.Is_Dialog_On();
	r.value[8] = audio.Is_Cinematic_Sound_On();
	return Save(r);
}

inline void Apply_Audio(WWAudioClass &audio)
{
	using namespace RenegadeVitaUserSettings;
	const Record &r = State().record;
	if ((r.value[0] & Audio) == 0) return;
	audio.Set_Sound_Effects_Volume(r.value[1] / 100.0F);
	audio.Set_Music_Volume(r.value[2] / 100.0F);
	audio.Set_Dialog_Volume(r.value[3] / 100.0F);
	audio.Set_Cinematic_Volume(r.value[4] / 100.0F);
	audio.Allow_Sound_Effects(r.value[5] != 0);
	audio.Allow_Music(r.value[6] != 0);
	audio.Allow_Dialog(r.value[7] != 0);
	audio.Allow_Cinematic_Sound(r.value[8] != 0);
}

inline bool Save_Performance(PhysicsSceneClass &scene)
{
	using namespace RenegadeVitaUserSettings;
	Record r = State().record;
	int stat = 0, dynamic = 0;
	scene.Get_Polygon_Budgets(&stat, &dynamic);
	if (stat < 0 || dynamic < 0) return false;
	r.value[0] |= Performance;
	r.value[9] = stat;
	r.value[10] = dynamic;
	r.value[11] = WW3D::Get_Texture_Reduction();
	r.value[12] = SurfaceEffectsManager::Get_Mode();
	return Save(r);
}

inline void Apply_Performance(PhysicsSceneClass &scene)
{
	using namespace RenegadeVitaUserSettings;
	const Record &r = State().record;
	if ((r.value[0] & Performance) == 0) return;
	scene.Set_Polygon_Budgets(r.value[9], r.value[10]);
	WW3D::Set_Texture_Reduction(r.value[11]);
	SurfaceEffectsManager::Set_Mode(static_cast<SurfaceEffectsManager::MODE>(r.value[12]));
}
} // namespace RenegadeVitaOptions
