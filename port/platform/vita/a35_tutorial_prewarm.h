#ifndef RENEGADE_A35_TUTORIAL_PREWARM_H
#define RENEGADE_A35_TUTORIAL_PREWARM_H

// RVTP1 tutorial first-use roots (M00_Tutorial.mix only). Included once by
// a31_vita_runtime.cpp; tools/test_tutorial_prewarm_list.py checks every name
// against Scripts/Mission00.cpp and the M00 discovery receipt.
//
// The Vita level loader reads only the mission dependency list
// (m00_tutorial.dep, "preload_always=0"), so assets that the PC loaded from
// always.dep load inside the gameplay frame that first needs them: player
// weapon models (w_*, w_*_b, f_gm_*, f_cm_*), first-person F_GA_/F_HA_
// animations, tracers, muzzle flashes, explosion aggregates and the sounds
// of all of these. Character and vehicle models are already in the
// tutorial dependency list; their weapons and explosions are not.

// Weapons the instructor selects on the star (Mission00.cpp
// Select_Weapon). First-person assets are warmed for these.
static const char *const kTutorialPrewarmPlayerWeapons[] = {
	"Weapon_Pistol_Player",
};

// Power-ups created or granted to the star (Mission00.cpp Create_Object /
// Give_PowerUp), in route order, plus the twiddled drops of the original
// M00_Soldier_Powerup_Grant script on the tutorial Nod soldiers
// (Toolkit_Powerup.cpp). A granted weapon is warmed as a player weapon.
static const char *const kTutorialPrewarmPlayerPresets[] = {
	"POW_Health_100",
	"POW_Armor_100",
	"Level_01_Keycard",
	"POW_SniperRifle_Player",
	"POW_AutoRifle_Player",
	"POW_GrenadeLauncher_Player",
	"POW_Chaingun_Player",
	"POW_Flamethrower_Player",
	"POW_RocketLauncher_Player",
	"POW_MineRemote_Player",
	"POW_IonCannonBeacon_Player",
	"tw_POW00_Health",
	"tw_POW00_Armor",
};

// Soldiers and vehicles created by Mission00.cpp (range targets, vehicle
// yard, flyovers, mock invasion) and the X0I_Drop02.txt cinematic that
// the instructor attaches (Nod_Transport_Helicopter, Nod_MiniGunner_0).
// Third-person weapon models, projectiles, killed explosions and sounds.
static const char *const kTutorialPrewarmWorldPresets[] = {
	"Nod_Minigunner_0",
	"Nod_Buggy",
	"Nod_Light_Tank",
	"GDI_Humm-vee_Player",
	"GDI_Medium_Tank_Player",
	"GDI_Orca",
	"GDI_Transport_Helicopter",
	"NOD_Apache",
	"GDI_Female_Lieutenant",
	"Nod_Transport_Helicopter",
	"GDI_Engineer_0",
	"Nod_Minigunner_1Off",
};

// Power-up grant sounds (PowerUpGameObjDef::GrantSoundID is protected, so
// the tutorial presets' grant sounds are named here).
static const char *const kTutorialPrewarmSounds[] = {
	"Pickup Health Sound",
	"Pickup Armor Sound",
	"Pickup Ammo Sound",
};

#endif
