#pragma once

// The original multiplayer-only HUD shares method names with GameModeClass
// virtuals, an MSVC-era construct rejected by current GCC. The campaign's
// authentic HUD remains separate; this narrow disabled provider only absorbs
// CombatGameMode's optional multiplayer overlay calls.
enum PlayerlistFormatEnum {
	PLAYERLIST_FORMAT_TINY,
	PLAYERLIST_FORMAT_MEDIUM,
	PLAYERLIST_FORMAT_FULL,
};

class MultiHUDClass {
public:
	static void Init(void) {}
	static void Shutdown(void) {}
	static void Think(void) {}
	static void Render(void) {}
	static void Toggle(void) {}
	static bool Is_On(void) { return false; }
	static void Next_Playerlist_Format(void) {}
	static void Set_Bottom_Text_Y_Pos(float value) { BottomTextYPos = value; }
	static float Get_Bottom_Text_Y_Pos(void) { return BottomTextYPos; }
	static PlayerlistFormatEnum Get_Playerlist_Format(void)
	{
		return PLAYERLIST_FORMAT_TINY;
	}
private:
	inline static float BottomTextYPos = 0.0F;
};
