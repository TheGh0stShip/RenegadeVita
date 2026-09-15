#ifndef RENEGADE_VITA_TUTORIAL_HELP_H
#define RENEGADE_VITA_TUTORIAL_HELP_H

#include "string_ids.h"

// Presentation-only replacements for PC control hints used by original M00.
// Unknown messages and other languages retain TranslateDB ownership.
inline const char *Renegade_Vita_Tutorial_Help(int string_id, unsigned language)
{
	if (language != 0U) return nullptr; // TranslateDBClass::LANGID_ENGLISH
	switch (string_id) {
	// Spoken tutorial captions use different IDs from the short HUD hints.
	case IDS_MTUDSGN_DSGN0011I1GCLS_TXT:
		return "Tap the rear touch pad to switch between first and third person.";
	case IDS_MTUDSGN_DSGN0014I1GCLS_TXT:
	case IDS_MTUDSGN_DSGN0015I1GCLS_TXT:
		return "Use the right stick to look around.";
	case IDS_MTUDSGN_DSGN0018I1GCLS_TXT:
		return "Use the left stick to move forward, back and sideways.";
	case IDS_MTUDSGN_DSGN0019I1GCLS_TXT:
		return "Use the right stick to turn while moving with the left stick.";
	case IDS_MTUDSGN_DSGN0027I1GCLS_TXT:
		return "Press Circle to crouch.";
	case IDS_MTUDSGN_DSGN0046I1GCLS_TXT:
		return "Press Cross to jump.";
	case IDS_MTUDSGN_DSGN0048I1GCLS_TXT:
		return "To jump onto a small object, press Cross and move the left stick forward.";
	case IDS_MTUDSGN_DSGN0049I1GCLS_TXT:
		return "To climb a ladder, approach it and press Triangle.";
	case IDS_MTUDSGN_DSGN0050I1GCLS_TXT:
		return "Use the left stick to climb up or down the ladder.";
	case IDS_MTUDSGN_DSGN0060I1GCLS_TXT:
		return "Press Start to access your EVA unit.";
	case IDS_MTUDSGN_DSGN0079I1GCLS_TXT:
		return "Press Triangle to talk to a soldier.";
	case IDS_MTUDSGN_DSGN0157I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Auto-Pistol, then head to the firing range.";
	case IDS_MTUDSGN_DSGN0165I1GSRS_TXT:
		return "Aim at a target and press R to fire.";
	case IDS_MTUDSGN_DSGN0170I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Sniper Rifle.";
	case IDS_MTUDSGN_DSGN0172I1GSRS_TXT:
		return "Press L to activate the scope.";
	case IDS_MTUDSGN_DSGN0173I1GSRS_TXT:
		return "Use D-pad Up/Down to zoom in and out.";
	case IDS_MTUDSGN_DSGN0177I1GSRS_TXT:
		return "Press L again to deactivate the scope.";
	case IDS_MTUDSGN_DSGN0184I1GSRS_TXT:
		return "Press Square to reload.";
	case IDS_MTUDSGN_DSGN0188I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Auto-Rifle.";
	case IDS_MTUDSGN_DSGN0191I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Grenade Launcher.";
	case IDS_MTUDSGN_DSGN0196I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Chain Gun.";
	case IDS_MTUDSGN_DSGN0199I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Flamethrower.";
	case IDS_MTUDSGN_DSGN0203I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Rocket Launcher.";
	case IDS_MTUDSGN_DSGN0219I1GSRS_TXT:
		return "Use D-pad Left/Right to select the Ion Cannon Beacon.";
	case IDS_MTUDSGN_DSGN0209I1GSRS_TXT:
		return "Use D-pad Left/Right to select Remote C4.";
	case IDS_MTUDSGN_DSGN0210I1GSRS_TXT:
		return "Press R to place C4.";
	case IDS_MTUDSGN_DSGN0211I1GSRS_TXT:
		return "Press L to detonate Remote C4.";
	case IDS_MTUDSGN_DSGN0253I1GSEN_TXT:
		return "Face the vehicle door and press Triangle to enter.";
	case IDS_MTUDSGN_DSGN0257I1GSEN_TXT:
		return "Aim with the right stick and drive with the left stick.";
	case IDS_MTUDSGN_DSGN0258I1GSEN_TXT:
		return "Move the left stick forward to accelerate, or back to brake and reverse.";
	case IDS_M01DSGN_DSGN0515I1DSGN_TXT:
		return "Left stick: move. Right stick: look. Start: EVA.";
	case IDS_MTUDSGN_DSGN0382I1DSGN_TXT:
		return "Press Circle to crouch.";
	case IDS_MTUDSGN_DSGN0383I1DSGN_TXT:
		return "Press Triangle to use ladders.";
	case IDS_MTUDSGN_DSGN0384I1DSGN_TXT:
		return "Press Cross to jump.";
	case IDS_MTUDSGN_DSGN0385I1DSGN_TXT:
		return "Press Triangle to talk to the soldier.";
	case IDS_M02DSGN_DSGN0186I1DSGN_TXT:
		return "Press Triangle to enter the Humm-Vee.";
	case IDS_MP_PURCHASE_HUD:
		return "Press Triangle to use the purchase terminal.";
	case IDS_MTUDSGN_DSGN0390I1DSGN_TXT:
		return "Use D-pad Left/Right to select the Auto-Pistol.";
	case IDS_M01DSGN_DSGN0518I1DSGN_TXT:
		return "Use D-pad Left/Right to select the Sniper Rifle.";
	case IDS_MTUDSGN_DSGN0392I1DSGN_TXT:
		return "Use D-pad Left/Right to select the Auto-Rifle.";
	case IDS_MTUDSGN_DSGN0393I1DSGN_TXT:
		return "Use D-pad Left/Right to select the Rocket Launcher.";
	case IDS_M01DSGN_DSGN0519I1DSGN_TXT:
		return "Use D-pad Left/Right to select Remote C4.";
	case IDS_MTUDSGN_DSGN0394I1DSGN_TXT:
		return "Use D-pad Left/Right to select the Ion Cannon Beacon.";
	default:
		return nullptr;
	}
}

#endif
