/*
**	Command & Conquer Renegade(tm)
**	Copyright 2025 Electronic Arts Inc.
**
**	This program is free software: you can redistribute it and/or modify
**	it under the terms of the GNU General Public License as published by
**	the Free Software Foundation, either version 3 of the License, or
**	(at your option) any later version.
**
**	This program is distributed in the hope that it will be useful,
**	but WITHOUT ANY WARRANTY; without even the implied warranty of
**	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
**	GNU General Public License for more details.
**
**	You should have received a copy of the GNU General Public License
**	along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

/*********************************************************************************************** 
 ***                            Confidential - Westwood Studios                              *** 
 *********************************************************************************************** 
 *                                                                                             * 
 *                 Project Name : Commando                                                     * 
 *                                                                                             * 
 *                     $Archive:: /Commando/Code/Commando/campaign.cpp          $* 
 *                                                                                             * 
 *                      $Author:: Ian_l                                                       $* 
 *                                                                                             * 
 *                     $Modtime:: 1/19/02 12:30p                                              $* 
 *                                                                                             * 
 *                    $Revision:: 33                                                          $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "campaign.h"
#include "debug.h"
#include "gamemode.h"
#include "gamedata.h"
#include "singlepl.h"
#include "gdsingleplayer.h"
#include "cnetwork.h"
#include "playertype.h"
#include "gameinitmgr.h"
#include "scorescreen.h"
#include "assets.h"
#include "movie.h"
#include "consolefunction.h"
#include "renegadedialogmgr.h"
#include "registry.h"
#include "_globals.h"
#include "crandom.h"
#include "god.h"
#include "dlgloadspgame.h"
#include "ccamera.h"
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
#include "a4_frontend_lifecycle_boundary.h"
#endif

/*
**
*/
int	CampaignManager::State = 0;
int	CampaignManager::BackdropIndex = 0;

#define	CAMPAIGN_INI_FILENAME	"campaign.ini"
#define	SECTION_CAMPAIGN			"Campaign"
#define	NOT_IN_CAMPAIGN_STATE	-10
#define	REPLAY_LEVEL			-11
#define	REPLAY_SCORE			-12

DynamicVectorClass<StringClass>	CampaignFlowDescriptions;

struct BackdropDescriptionStruct {
	int State;
	DynamicVectorClass<StringClass>	Lines;

	bool operator == (BackdropDescriptionStruct const & rec) const	{ return false; }
	bool operator != (BackdropDescriptionStruct const & rec) const	{ return true; }
};

DynamicVectorClass<BackdropDescriptionStruct>	BackdropDescriptions;

/*
**
*/
void	CampaignManager::Init( void )
{
	// Init can be reached again after frontend recovery without a process
	// restart. These catalogs are process globals, so rebuilding them on top
	// of an earlier generation would duplicate the retail campaign sequence
	// and its backdrop records. Treat each Init as a fresh parse while leaving
	// campaign.ini as the sole owner of ordering and content.
	CampaignFlowDescriptions.Clear();
	BackdropDescriptions.Clear();
	State = NOT_IN_CAMPAIGN_STATE;
	BackdropIndex = 0;

	// Load CAMPAIGN.INI to get campain flow
	INIClass	* campaignINI = Get_INI( CAMPAIGN_INI_FILENAME );
	if (campaignINI != NULL) {
		WWASSERT( campaignINI && campaignINI->Section_Count() > 0 );
		int count =  campaignINI->Entry_Count( SECTION_CAMPAIGN );
		for ( int entry = 0; entry < count; entry++ )	{
			StringClass	description(0,true);
			campaignINI->Get_String(description, SECTION_CAMPAIGN, campaignINI->Get_Entry( SECTION_CAMPAIGN, entry) );
			CampaignFlowDescriptions.Add( description );
		}

		// Load Backdrop Descriptions
		// Load the first 100, because 90-95 are multiplay.. :)
		for ( int state = 0; state < 100; state++ ) {
			StringClass section_name;
			section_name.Format( "Backdrop%d", state );
			int count =  campaignINI->Entry_Count( section_name );
			if ( count != 0 ) {
				int index = BackdropDescriptions.Count();
				BackdropDescriptions.Uninitialized_Add();
				BackdropDescriptions[index].State = state;
				for ( int entry = 0; entry < count; entry++ )	{
					StringClass	description(0,true);
					campaignINI->Get_String(description, section_name, campaignINI->Get_Entry( section_name, entry) );
					BackdropDescriptions[index].Lines.Add( description );
				}
			}

		}

		Release_INI( campaignINI );
	} else {
		Debug_Say(("CampaignManager::Init - Unable to load %s\n", CAMPAIGN_INI_FILENAME));
	}

}

bool CampaignManager::Is_Catalog_Ready(void)
{
	// Campaign order remains data-owned. Admit only the directive forms that
	// Continue can parse; malformed data must not reach progression indexing.
	if (CampaignFlowDescriptions.Count() <= 0 || BackdropDescriptions.Count() <= 0) {
		return false;
	}
	for (int index = 0; index < CampaignFlowDescriptions.Count(); ++index) {
		const char *description = CampaignFlowDescriptions[index];
		if (description == NULL || description[0] == '\0') return false;
		if (::strncmp(description, "Message ", 8) == 0) {
			if (description[8] == '\0') return false;
		} else if (::strncmp(description, "Score", 5) == 0) {
			// Continue intentionally accepts the released Score prefix.
		} else if (::strncmp(description, "Level ", 6) == 0) {
			char map[96] = {};
			char trailing = '\0';
			if (::sscanf(description + 6, "%95s %c", map, &trailing) != 1 ||
				map[0] == '\0' || ::strchr(map, '.') == NULL) return false;
		} else if (::strncmp(description, "Movie ", 6) == 0) {
			char movie[96] = {};
			char unlock[96] = {};
			if (::sscanf(description + 6, "%95s %95s", movie, unlock) != 2 ||
				movie[0] == '\0' || unlock[0] == '\0') return false;
		} else {
			return false;
		}
	}
	for (int index = 0; index < BackdropDescriptions.Count(); ++index) {
		if (BackdropDescriptions[index].Lines.Count() <= 0) return false;
	}
	return true;
}

bool CampaignManager::Current_Level_Matches_Archive(const char *archive)
{
	if (archive == NULL || archive[0] == '\0' ||
		State < 0 || State >= CampaignFlowDescriptions.Count()) {
		return false;
	}
	const char *description = CampaignFlowDescriptions[State];
	if (description == NULL || ::strncmp(description, "Level ", 6) != 0) {
		return false;
	}
	char map[96] = {};
	char trailing = '\0';
	if (::sscanf(description + 6, "%95s %c", map, &trailing) != 1) {
		return false;
	}
	return ::stricmp(map, archive) == 0;
}

bool CampaignManager::Loaded_Save_State_Matches_Archive(const char *archive)
{
	if (archive == NULL || archive[0] == '\0') return false;
	if (State == NOT_IN_CAMPAIGN_STATE) {
		// The original Tutorial is outside campaign.ini but may be saved.
		return ::stricmp(archive, "M00_Tutorial.mix") == 0;
	}
	if (State == REPLAY_LEVEL) {
		// Replay has no campaign-flow index; the save header owns its map.
		return true;
	}
	if (State == REPLAY_SCORE) {
		// This intermission-only state cannot own a gameplay save.
		return false;
	}
	return Current_Level_Matches_Archive(archive);
}

/*
**
*/
void	CampaignManager::Shutdown( void )
{
	CampaignFlowDescriptions.Clear();
	BackdropDescriptions.Clear();
}



/*
**
*/
//-----------------------------------------------------------------------------
enum	{
	CHUNKID_VARIABLES = 906011356,

	MICROCHUNK_STATE = 1,
	MICROCHUNK_BACKDROP_INDEX,
};

//-----------------------------------------------------------------------------
bool CampaignManager::Save(ChunkSaveClass & csave)
{
	csave.Begin_Chunk(CHUNKID_VARIABLES);
		WRITE_MICRO_CHUNK(csave, MICROCHUNK_STATE, State);
		WRITE_MICRO_CHUNK(csave, MICROCHUNK_BACKDROP_INDEX, BackdropIndex);
	csave.End_Chunk();
	return !csave.Has_Error();
}

//-----------------------------------------------------------------------------
bool CampaignManager::Load(ChunkLoadClass &cload)
{
	const int missing_value = (-2147483647 - 1);
	int loaded_state = missing_value;
	int loaded_backdrop_index = missing_value;
	bool variables_seen = false;
	bool state_seen = false;
	bool backdrop_seen = false;
	bool loaded = true;
	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_VARIABLES:
				if (variables_seen) loaded = false;
				variables_seen = true;
				while (cload.Open_Micro_Chunk()) {
					switch(cload.Cur_Micro_Chunk_ID()) {
						case MICROCHUNK_STATE:
							if (state_seen || cload.Cur_Micro_Chunk_Length() != sizeof(loaded_state)) loaded = false;
							else {
								state_seen = true;
								loaded = cload.Read(&loaded_state, sizeof(loaded_state)) ==
									sizeof(loaded_state) && loaded;
							}
							break;
						case MICROCHUNK_BACKDROP_INDEX:
							if (backdrop_seen || cload.Cur_Micro_Chunk_Length() != sizeof(loaded_backdrop_index)) loaded = false;
							else {
								backdrop_seen = true;
								loaded = cload.Read(&loaded_backdrop_index,
									sizeof(loaded_backdrop_index)) == sizeof(loaded_backdrop_index) && loaded;
							}
							break;
						default:
							Debug_Say(( "Unrecognized Campaign Variable chunkID\n" ));
							break;
					}
					cload.Close_Micro_Chunk();
				}
				break;

			default:
				Debug_Say(( "Unrecognized campaign chunkID\n" ));
				break;
		}
		cload.Close_Chunk();
	}

	const bool state_valid = loaded_state == NOT_IN_CAMPAIGN_STATE ||
		loaded_state == REPLAY_LEVEL || loaded_state == REPLAY_SCORE ||
		(loaded_state >= -1 && loaded_state < CampaignFlowDescriptions.Count());
	const bool backdrop_valid = loaded_backdrop_index >= 0 &&
		loaded_backdrop_index < BackdropDescriptions.Count();
	if (!loaded || !variables_seen || !state_seen || !backdrop_seen ||
		loaded_state == missing_value || loaded_backdrop_index == missing_value ||
		!state_valid || !backdrop_valid) {
		Debug_Say(("CampaignManager::Load - invalid campaign state=%d backdrop=%d flow=%d backdrops=%d\n",
			loaded_state, loaded_backdrop_index, CampaignFlowDescriptions.Count(),
			BackdropDescriptions.Count()));
		return false;
	}
	State = loaded_state;
	BackdropIndex = loaded_backdrop_index;
	return true;
}




/*
**
*/
void	CampaignManager::Start_Campaign( int difficulty )
{
	Debug_Say(( "CampaignManager::Start_Campaign( %d )\n", difficulty ));

	State = -1;
	BackdropIndex = 0;

	// Why was this commented out???
	CombatManager::Set_Difficulty_Level( difficulty );

	StringClass diff_string;
	diff_string.Format( "difficulty %d", difficulty );
	ConsoleFunctionManager::Parse_Input( diff_string );

	cGod::Reset_Inventory();

	Continue();
}

/*
**
*/
void	CampaignManager::Continue( bool success )
{
	BackdropIndex = 0;

	if ( State == REPLAY_LEVEL ) {
		State = REPLAY_SCORE;

		// Activeate the Score screen before the combat deactivates, so we can get the stats
		ScoreScreenGameModeClass * ss = (ScoreScreenGameModeClass *)GameModeManager::Find ("ScoreScreen");
		if ( ss != NULL ) {
		 	ss->Save_Stats();
		}

		GameModeManager::Find ("Movie")->Deactivate();
		GameModeManager::Find ("Combat")->Suspend();
		GameInitMgrClass::End_Game();
		GameModeManager::Find ("Menu")->Deactivate();

		if ( ss != NULL ) {
			ss->Activate();
		}
		return;
	}

	if ( State == NOT_IN_CAMPAIGN_STATE || State == REPLAY_SCORE || ( State >= CampaignFlowDescriptions.Count() - 1 ) ) {
		State = NOT_IN_CAMPAIGN_STATE;
		GameModeManager::Find ("Movie")->Deactivate();
		GameModeManager::Find ("ScoreScreen")->Deactivate();		// BMG???
		GameModeManager::Find ("Combat")->Suspend();
		GameInitMgrClass::End_Game();
		GameInitMgrClass::Display_End_Game_Menu();
		return;
	}

	State = State+1;

	Debug_Say(( "CampaignManager::Continue %d\n", State ));

	const char * state_description = CampaignFlowDescriptions[State];

#define	StringMatch(a,b)	(!::strncmp( a,b,strlen(b) ))

	if ( StringMatch( state_description, "Message " ) ) {

		state_description += ::strlen( "Message " );

		GameModeManager::Find ("Movie")->Deactivate();
		GameModeManager::Find ("Combat")->Suspend();
		GameInitMgrClass::End_Game();

		GameModeManager::Find ("Menu")->Deactivate();
		GameModeManager::Find ("ScoreScreen")->Activate();

	} else if ( StringMatch( state_description, "Score" ) ) {

		state_description += ::strlen( "Score" );

		// Activeate the Score screen before the combat deactivates, so we can get the stats
		ScoreScreenGameModeClass * ss = (ScoreScreenGameModeClass *)GameModeManager::Find ("ScoreScreen");
		if ( ss != NULL ) {
		 	ss->Save_Stats();
		}

		GameModeManager::Find ("Movie")->Deactivate();
		GameModeManager::Find ("Combat")->Suspend();
		GameInitMgrClass::End_Game();
		GameModeManager::Find ("Menu")->Deactivate();

		if ( ss != NULL ) {
			ss->Activate();
		}

	} else if ( StringMatch( state_description, "Level " ) ) {


		GameModeManager::Find ("Combat")->Suspend();
		GameModeManager::Find ("Movie")->Deactivate();
	    GameModeManager::Find ("ScoreScreen")->Deactivate ();

		GameInitMgrClass::End_Game();

		state_description += ::strlen( "Level " );

		int mission = cGameData::Get_Mission_Number_From_Map_Name( state_description );
		Select_Backdrop_Number( mission );
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND)
		A4_Frontend_Mark_Next_Start_Game_As_Campaign_Level();
#endif
		GameInitMgrClass::Start_Game ( state_description, PLAYERTYPE_RENEGADE, 0 );

		// Hack to not autosave for Mission 0 (M13)
		if ( ::strnicmp( state_description, "M13", 3 ) != 0 ) {
			CombatManager::Request_Autosave();
		}

	} else if ( StringMatch( state_description, "Movie " ) ) {

		if (COMBAT_CAMERA != NULL) {
			COMBAT_CAMERA->Set_Host_Model (NULL);
		}

		GameModeManager::Find ("Combat")->Suspend();
		GameInitMgrClass::End_Game();
		GameModeManager::Find ("Menu")->Deactivate();
		GameModeManager::Find ("ScoreScreen")->Deactivate ();

		//
		//	Parse the parameters
		//
		int len = ::strlen( state_description );
		StringClass foo( len + 1, true );
		StringClass filename( len + 1, true );
		StringClass description( len + 1, true );
		::sscanf (state_description, "%s %s %s", foo.Peek_Buffer (), filename.Peek_Buffer (), description.Peek_Buffer ());

		MovieGameModeClass * mode = (MovieGameModeClass *)GameModeManager::Find ("Movie");
		if ( mode ) {
			mode->Activate();
			mode->Start_Movie( filename );

			//
			//	Add this movie name to the registry (that way the user
			// can watch it later)
			//	
			RegistryClass registry( APPLICATION_SUB_KEY_NAME_MOVIES );
			if ( !registry.Is_Valid() ||
				!registry.Set_String_Checked( filename, description ) ) {
				Debug_Say(( "CampaignManager::Continue - unable to persist movie unlock %s\n",
					filename.Peek_Buffer() ));
			}
		}

	} else {

		Debug_Say(( "Failed to Parse Campaign Description %s\n", state_description ));

		State = NOT_IN_CAMPAIGN_STATE;		
		RenegadeDialogMgrClass::Goto_Location (RenegadeDialogMgrClass::LOC_MAIN_MENU);
	}

}

void	CampaignManager::Reset()
{
	State = NOT_IN_CAMPAIGN_STATE;		
}

/*
**
*/
void	CampaignManager::Replay_Level( const char * mission_name, int difficulty )
{
	State = REPLAY_LEVEL;

	cGod::Reset_Inventory();
	CombatManager::Set_Difficulty_Level( difficulty );

	GameInitMgrClass::Start_Game( mission_name, PLAYERTYPE_RENEGADE, 0 );
}

/*
**
*/
int	CampaignManager::Get_Backdrop_Description_Count( void )
{
	if (BackdropIndex >= 0 && BackdropIndex < BackdropDescriptions.Count()) {
		return BackdropDescriptions[BackdropIndex].Lines.Count();
	}
	return 0;
}

const char * CampaignManager::Get_Backdrop_Description( int index )
{
	if (BackdropIndex < 0 || BackdropIndex >= BackdropDescriptions.Count() ||
		index < 0 || index >= BackdropDescriptions[BackdropIndex].Lines.Count()) {
		return "";
	}
	return BackdropDescriptions[BackdropIndex].Lines[index];
}

void	CampaignManager::Select_Backdrop_Number( int state_number )
{
	// Find Backdrop Index
	BackdropIndex = 0;
	bool found = false;
	for ( int i = 0; i < BackdropDescriptions.Count(); i++ ) {
		if ( BackdropDescriptions[i].State == state_number ) {
			BackdropIndex = i;
			found = true;
			break;
		}
	}

	if ( !found ) {
		Debug_Say(( "Failed to find load menu for state %d\n", state_number ));
	}
}

void	CampaignManager::Select_Backdrop_Number_By_MP_Type( int type )
{
	//
	//	Setup Load Menu
	//
	/*
	#define	MULTIPLAY_LOAD_MENU_NUMBER_DEATHMATCH			91
	#define	MULTIPLAY_LOAD_MENU_NUMBER_TEAM_DEATHMATCH	92
	#define	MULTIPLAY_LOAD_MENU_NUMBER_CTF					93
	#define	MULTIPLAY_LOAD_MENU_NUMBER_CNC1					94
	#define	MULTIPLAY_LOAD_MENU_NUMBER_CNC2					95
	int load_menu_number = 0;
	if ( type == cGameData::GAME_TYPE_DEATHMATCH ) {
		load_menu_number = MULTIPLAY_LOAD_MENU_NUMBER_DEATHMATCH;	
	}
	if ( type == cGameData::GAME_TYPE_TEAM_DEATHMATCH ) {
		load_menu_number = MULTIPLAY_LOAD_MENU_NUMBER_TEAM_DEATHMATCH;	
	}
	if ( type == cGameData::GAME_TYPE_CNC ) {
		load_menu_number = MULTIPLAY_LOAD_MENU_NUMBER_CNC1;	
		if ( FreeRandom.Get_Int() & 1 ) {
			load_menu_number = MULTIPLAY_LOAD_MENU_NUMBER_CNC2;	
		}
	}
	Select_Backdrop_Number( load_menu_number );
	*/

	WWASSERT(type == cGameData::GAME_TYPE_CNC);

	#define	MULTIPLAY_LOAD_MENU_NUMBER_CNC1					94
	#define	MULTIPLAY_LOAD_MENU_NUMBER_CNC2					95

	int load_menu_number = 0;
	if (FreeRandom.Get_Int() & 1) {
		load_menu_number = MULTIPLAY_LOAD_MENU_NUMBER_CNC1;
	} else {
		load_menu_number = MULTIPLAY_LOAD_MENU_NUMBER_CNC2;
	}

//	Select_Backdrop_Number(load_menu_number);
	//forget the random screen, alwayds do 94 (BMG 11/24/01)
	Select_Backdrop_Number( MULTIPLAY_LOAD_MENU_NUMBER_CNC1 );

}





















	/*
	if ( type == cGameData::GAME_TYPE_CTF ) {
		load_menu_number = MULTIPLAY_LOAD_MENU_NUMBER_CTF;	
	}
	*/
