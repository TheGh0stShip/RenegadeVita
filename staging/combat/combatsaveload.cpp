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
 *                     $Archive:: /Commando/Code/Combat/combatsaveload.cpp                    $* 
 *                                                                                             * 
 *                      $Author:: Byon_g                                                      $* 
 *                                                                                             * 
 *                     $Modtime:: 1/17/02 11:58a                                              $* 
 *                                                                                             * 
 *                    $Revision:: 34                                                          $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "combatsaveload.h"
#include "chunkio.h"
#include "gameobjmanager.h"
#include "combat.h"
#include "debug.h"
#include "spawn.h"
#include "timemgr.h"
#include "scripts.h"
#include "persistentgameobjobserver.h"
#include "wwmemlog.h"
#include "cover.h"
#include "objectives.h"
#include "radar.h"
#include "building.h"
#include "bullet.h"
#include "backgroundmgr.h"
#include "weathermgr.h"
#include "weaponview.h"
#include "hud.h"
#include "screenfademanager.h"

/*
**
*/
CombatSaveLoadClass	_CombatSaveLoad;

enum	{
	CHUNKID_GAMEOBJMANAGER					=	916991654,
	CHUNKID_COMBAT_GAME_MODE,
	XXX_CHUNKID_TRANSITIONS,
	CHUNKID_SPAWNERS,
	XXXCHUNKID_TIME,
	CHUNKID_SCRIPTS,
	CHUNKID_PERSISTENT_GAME_OBJ_OBSERVERS,
	CHUNKID_COVER,
	CHUNKID_OBJECTIVES,
	CHUNKID_RADAR,
	XXXCHUNKID_BUILDINGS,
	CHUNKID_GAME_OBJ_OBSERVERS,
	CHUNKID_BULLETS,
	CHUNKID_WEAPON_VIEW,
	CHUNKID_DYNAMIC_BACKGROUND,
	CHUNKID_DYNAMIC_WEATHER,
	CHUNKID_HUD,
	CHUNKID_SCREEN_FADE,
};

/*
**
*/
bool	CombatSaveLoadClass::Save( ChunkSaveClass &csave )
{
	WWMEMLOG(MEM_GAMEDATA);
	bool saved = true;
	#define SAVE_REQUIRED_COMBAT_CHUNK(chunk_id, expression) \
		do { \
			const bool opened = csave.Begin_Chunk(chunk_id); \
			const bool child_saved = (expression); \
			const bool closed = csave.End_Chunk(); \
			saved = opened && child_saved && closed && saved; \
		} while (0)

	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_GAMEOBJMANAGER, GameObjManager::Save(csave));

	// CombatManager should load before scripts for SyncTime
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_COMBAT_GAME_MODE, CombatManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_SPAWNERS, SpawnManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_SCRIPTS, ScriptManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_PERSISTENT_GAME_OBJ_OBSERVERS, PersistentGameObjObserverManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_COVER, CoverManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_OBJECTIVES, ObjectiveManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_RADAR, RadarManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_GAME_OBJ_OBSERVERS, GameObjObserverManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_BULLETS, BulletManager::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_WEAPON_VIEW, WeaponViewClass::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_DYNAMIC_BACKGROUND, BackgroundMgrClass::Save_Dynamic(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_DYNAMIC_WEATHER, WeatherMgrClass::Save_Dynamic(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_HUD, HUDClass::Save(csave));
	SAVE_REQUIRED_COMBAT_CHUNK(CHUNKID_SCREEN_FADE, ScreenFadeManager::Save(csave));

	#undef SAVE_REQUIRED_COMBAT_CHUNK
	return saved && !csave.Has_Error();
}

bool	CombatSaveLoadClass::Load( ChunkLoadClass &cload )
{
	WWMEMLOG(MEM_GAMEDATA);
	uint32 loaded_chunks = 0U;
	bool loaded = true;
	#define LOAD_REQUIRED_COMBAT_CHUNK(bit, expression) \
		do { \
			const uint32 chunk_bit = 1U << (bit); \
			if ((loaded_chunks & chunk_bit) != 0U) { \
				loaded = false; \
			} else { \
				loaded_chunks |= chunk_bit; \
				loaded = (expression) && loaded; \
			} \
		} while (0)

	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_GAMEOBJMANAGER:
				LOAD_REQUIRED_COMBAT_CHUNK(0, GameObjManager::Load( cload ));
				break;

			case CHUNKID_COMBAT_GAME_MODE:
				LOAD_REQUIRED_COMBAT_CHUNK(1, CombatManager::Load( cload ));
				break;

			case CHUNKID_SPAWNERS:
				LOAD_REQUIRED_COMBAT_CHUNK(2, SpawnManager::Load( cload ));
				break;

			case CHUNKID_SCRIPTS:
				LOAD_REQUIRED_COMBAT_CHUNK(3, ScriptManager::Load( cload ));
				break;

			case CHUNKID_PERSISTENT_GAME_OBJ_OBSERVERS:
				LOAD_REQUIRED_COMBAT_CHUNK(4, PersistentGameObjObserverManager::Load( cload ));
				break;

			case CHUNKID_COVER:
				LOAD_REQUIRED_COMBAT_CHUNK(5, CoverManager::Load( cload ));
				break;

			case CHUNKID_OBJECTIVES:
				LOAD_REQUIRED_COMBAT_CHUNK(6, ObjectiveManager::Load( cload ));
				break;

			case CHUNKID_RADAR:
				LOAD_REQUIRED_COMBAT_CHUNK(7, RadarManager::Load( cload ));
				break;
			
			case CHUNKID_GAME_OBJ_OBSERVERS:
				LOAD_REQUIRED_COMBAT_CHUNK(8, GameObjObserverManager::Load( cload ));
				break;

			case CHUNKID_BULLETS:
				LOAD_REQUIRED_COMBAT_CHUNK(9, BulletManager::Load( cload ));
				break;

			case CHUNKID_WEAPON_VIEW:
				LOAD_REQUIRED_COMBAT_CHUNK(10, WeaponViewClass::Load( cload ));
				break;

			case CHUNKID_DYNAMIC_BACKGROUND:
				LOAD_REQUIRED_COMBAT_CHUNK(11, BackgroundMgrClass::Load_Dynamic( cload ));
				break;

			case CHUNKID_DYNAMIC_WEATHER:
				LOAD_REQUIRED_COMBAT_CHUNK(12, WeatherMgrClass::Load_Dynamic( cload ));
				break;

			case CHUNKID_HUD:
				LOAD_REQUIRED_COMBAT_CHUNK(13, HUDClass::Load( cload ));
				break;

			case CHUNKID_SCREEN_FADE:
				LOAD_REQUIRED_COMBAT_CHUNK(14, ScreenFadeManager::Load( cload ));
				break;

			default:
				Debug_Say(( "Unrecognized CombatSaveLoad chunkID\n" ));
				break;

		}
		cload.Close_Chunk();
	}

	#undef LOAD_REQUIRED_COMBAT_CHUNK
	loaded = loaded && loaded_chunks == ((1U << 15) - 1U);
	// Register unconditionally (original): a rejected load discards all callbacks.
	SaveLoadSystemClass::Register_Post_Load_Callback(this);

	return loaded;
}


void	CombatSaveLoadClass::On_Post_Load(void) 
{
}
