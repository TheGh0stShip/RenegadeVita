#ifndef RENEGADE_A4_FRONTEND_LIFECYCLE_BOUNDARY_H
#define RENEGADE_A4_FRONTEND_LIFECYCLE_BOUNDARY_H

#include "always.h"

struct A4FrontendTrace
{
	bool menu_loop_active;
	bool pause_loop_active;
	bool reload_requested;
	bool exit_requested;
	int exit_code;
	bool tutorial_start_latched;
	char tutorial_map[96];
	int tutorial_team_choice;
	unsigned long tutorial_clan_id;
	unsigned movie_play_requests;
	unsigned movie_skip_requests;
	char last_movie[160];
	bool bink_initialized;
};

void A4_Frontend_Reset_Trace(void);
void A4_Frontend_Begin_Menu_Loop(void);
void A4_Frontend_End_Menu_Loop(void);
void A4_Frontend_Begin_Pause_Loop(void);
void A4_Frontend_Prime_WWUI_Key_Transitions(void);
bool A4_Frontend_Is_Menu_Loop_Active(void);
bool A4_Frontend_Exit_Requested(void);
int A4_Frontend_Exit_Code(void);
bool A4_Frontend_Is_Tutorial_Source(const char *map_name);
bool A4_Frontend_Latch_Start_Game(const char *map_name, int teamChoice, unsigned long clanID);
A4FrontendTrace A4_Frontend_Get_Trace(void);
void A4_Frontend_Record_Bink_Init(bool initialized);
void A4_Frontend_Record_Bink_Play(const char *filename);
void A4_Frontend_Record_Bink_Skip(const char *filename);
void A4_Frontend_Pump_WWUI_Key_Transitions(void);
void A4_Frontend_Set_Test_WWUI_Key_State(int virtual_key, bool pressed);

#endif
