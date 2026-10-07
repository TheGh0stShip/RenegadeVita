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
 *                     $Archive:: /Commando/Code/Combat/playerdata.cpp                   $*
 *                                                                                             *
 *                      $Author:: Byon_g                                                      $*
 *                                                                                             *
 *                     $Modtime:: 3/29/02 3:40p                                               $*
 *                                                                                             *
 *                    $Revision:: 38                                                          $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "playerdata.h"
#include "debug.h"
#include "chunkio.h"
#include "wwpacket.h"
#include "persistfactory.h"
#include "combatchunkid.h"
#include "combat.h"
#include "hud.h"
#include "soldier.h"
#include "systeminfolog.h"
#include "stackdump.h"

/*
**
*/
PlayerDataClass::PlayerDataClass( void ) :
	Score( 0 ),
	Money( 0 ),
	PunishTimer( 0 )
{
	Stats_Reset();
}

PlayerDataClass::~PlayerDataClass( void )
{
	PlayerInfoLog::Append_To_Log(this);
	if ( Get_GameObj() ) {
		Get_GameObj()->Set_Player_Data( NULL );
	}
}

/*
**
*/
enum	{
	CHUNKID_VARIABLES						=	201011247,
	CHUNKID_STATS_WEAPON,

	MICROCHUNKID_SCORE					=	1,
	MICROCHUNKID_MONEY, 
	MICROCHUNKID_STAT_TIME_IN_GAME, 
	MICROCHUNKID_STAT_ENEMIES_KILLED, 
	MICROCHUNKID_STAT_ALLIES_KILLED, 
	MICROCHUNKID_STAT_SHOTS_FIRED, 
	MICROCHUNKID_STAT_HEAD_SHOTS, 
	MICROCHUNKID_STAT_TORSO_SHOTS, 
	MICROCHUNKID_STAT_ARM_SHOTS, 
	MICROCHUNKID_STAT_LEG_SHOTS, 
	MICROCHUNKID_STAT_CROTCH_CHOTS, 
	MICROCHUNKID_STAT_FINAL_HEALTH, 
	MICROCHUNKID_STAT_POWERUPS, 
	MICROCHUNKID_STAT_VEHICLES_DESTROYED, 
	MICROCHUNKID_STAT_TIME_IN_VEHICLES, 
	MICROCHUNKID_STAT_KILLS_FROM_VEHICLES, 
	MICROCHUNKID_STAT_SQUISHES, 
	MICROCHUNKID_STAT_CREDITS_GRANTED, 
	MICROCHUNKID_STAT_BUILDINGS_DESTROYED, 
	MICROCHUNKID_STAT_HEAD_HITS, 
	MICROCHUNKID_STAT_TORSO_HITS, 
	MICROCHUNKID_STAT_ARM_HITS, 
	MICROCHUNKID_STAT_LEG_HITS, 
	MICROCHUNKID_STAT_CROTCH_HITS, 

	MICROCHUNKID_STAT_WEAPON_ID,
	MICROCHUNKID_STAT_WEAPON_COUNT,
};

bool	PlayerDataClass::Save( ChunkSaveClass & csave )
{
	csave.Begin_Chunk( CHUNKID_VARIABLES );
		WRITE_SAFE_MICRO_CHUNK( csave, MICROCHUNKID_SCORE, Score, float );
		WRITE_SAFE_MICRO_CHUNK( csave, MICROCHUNKID_MONEY, Money, float );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_TIME_IN_GAME, StatTimeInGame );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_ENEMIES_KILLED, StatEnemiesKilled );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_ALLIES_KILLED, StatAlliesKilled );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_SHOTS_FIRED, StatShotsFired );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_HEAD_SHOTS, StatHeadShots );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_TORSO_SHOTS, StatTorsoShots );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_ARM_SHOTS, StatArmShots );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_LEG_SHOTS, StatLegShots );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_CROTCH_CHOTS, StatCrotchShots );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_FINAL_HEALTH, StatFinalHealth );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_POWERUPS, StatPowerups );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_VEHICLES_DESTROYED, StatVehiclesDestroyed );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_TIME_IN_VEHICLES, StatTimeInVehicles );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_KILLS_FROM_VEHICLES, StatKillsFromVehicles );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_SQUISHES, StatSquishes );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_CREDITS_GRANTED, StatCreditsGranted );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_BUILDINGS_DESTROYED, StatBuildingsDestroyed );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_HEAD_HITS, StatHeadHits );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_TORSO_HITS, StatTorsoHits );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_ARM_HITS, StatArmHits );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_LEG_HITS, StatLegHits );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_CROTCH_HITS, StatCrotchHits );
	csave.End_Chunk();

	for (int i = 0; i < StatWeaponIDFired.Count(); i++) {
		int	id = StatWeaponIDFired[i];
		int	count = StatWeaponFireCount[i];
		csave.Begin_Chunk( CHUNKID_STATS_WEAPON );
			WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_WEAPON_ID, id );
			WRITE_MICRO_CHUNK( csave, MICROCHUNKID_STAT_WEAPON_COUNT, count );
		csave.End_Chunk();
	}

	return true;
}

bool	PlayerDataClass::Load( ChunkLoadClass &cload )
{
	bool variables_seen = false;
	bool loaded = true;
	uint32 loaded_values = 0;
	const uint32 required_values = (1U << 24) - 1U;
	float score = 0.0F;
	float money = 0.0F;
	StatTimeInSession=0.0f;
	StatLastWeaponIndex = -1;
	WWASSERT( StatWeaponIDFired.Count() == 0 );
	WWASSERT( StatWeaponFireCount.Count() == 0 );

	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_VARIABLES:
				if (variables_seen) {
					loaded = false;
					break;
				}
				variables_seen = true;
				while (cload.Open_Micro_Chunk()) {
					switch(cload.Cur_Micro_Chunk_ID()) {
#define READ_REQUIRED_PLAYER_DATA_VALUE(id, value, bit) \
						case (id): \
							if ((loaded_values & (bit)) != 0U || cload.Cur_Micro_Chunk_Length() != sizeof(value) || \
								cload.Read(&(value), sizeof(value)) != sizeof(value)) loaded = false; \
							else loaded_values |= (bit); \
							break
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_SCORE, score, 1U << 0);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_MONEY, money, 1U << 1);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_TIME_IN_GAME, StatTimeInGame, 1U << 2);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_ENEMIES_KILLED, StatEnemiesKilled, 1U << 3);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_ALLIES_KILLED, StatAlliesKilled, 1U << 4);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_SHOTS_FIRED, StatShotsFired, 1U << 5);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_HEAD_SHOTS, StatHeadShots, 1U << 6);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_TORSO_SHOTS, StatTorsoShots, 1U << 7);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_ARM_SHOTS, StatArmShots, 1U << 8);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_LEG_SHOTS, StatLegShots, 1U << 9);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_CROTCH_CHOTS, StatCrotchShots, 1U << 10);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_FINAL_HEALTH, StatFinalHealth, 1U << 11);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_POWERUPS, StatPowerups, 1U << 12);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_VEHICLES_DESTROYED, StatVehiclesDestroyed, 1U << 13);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_TIME_IN_VEHICLES, StatTimeInVehicles, 1U << 14);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_KILLS_FROM_VEHICLES, StatKillsFromVehicles, 1U << 15);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_SQUISHES, StatSquishes, 1U << 16);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_CREDITS_GRANTED, StatCreditsGranted, 1U << 17);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_BUILDINGS_DESTROYED, StatBuildingsDestroyed, 1U << 18);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_HEAD_HITS, StatHeadHits, 1U << 19);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_TORSO_HITS, StatTorsoHits, 1U << 20);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_ARM_HITS, StatArmHits, 1U << 21);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_LEG_HITS, StatLegHits, 1U << 22);
						READ_REQUIRED_PLAYER_DATA_VALUE(MICROCHUNKID_STAT_CROTCH_HITS, StatCrotchHits, 1U << 23);
#undef READ_REQUIRED_PLAYER_DATA_VALUE
						default:
							loaded = false;
							break;
					}
					cload.Close_Micro_Chunk();
				}
				break;

			case CHUNKID_STATS_WEAPON:
			{
				int id = 0;
				int count = 0;
				bool id_seen = false;
				bool count_seen = false;

				while (cload.Open_Micro_Chunk()) {
					switch(cload.Cur_Micro_Chunk_ID()) {
						case MICROCHUNKID_STAT_WEAPON_ID:
							if (id_seen || cload.Cur_Micro_Chunk_Length() != sizeof(id) ||
								cload.Read(&id, sizeof(id)) != sizeof(id)) loaded = false;
							else id_seen = true;
							break;
						case MICROCHUNKID_STAT_WEAPON_COUNT:
							if (count_seen || cload.Cur_Micro_Chunk_Length() != sizeof(count) ||
								cload.Read(&count, sizeof(count)) != sizeof(count)) loaded = false;
							else count_seen = true;
							break;

						default:
							loaded = false;
							break;
					}
					cload.Close_Micro_Chunk();
				}

				bool duplicate_id = false;
				for (int index = 0; index < StatWeaponIDFired.Count(); ++index) {
					if (StatWeaponIDFired[index] == id) duplicate_id = true;
				}
				if (!id_seen || !count_seen || id == 0 || count < 0 || duplicate_id) loaded = false;
				else {
					StatWeaponIDFired.Add(id);
					StatWeaponFireCount.Add(count);
				}
				break;
			}

			default:
				loaded = false;
				break;

		}
		cload.Close_Chunk();
	}

	loaded = loaded && variables_seen && loaded_values == required_values && !cload.Has_Error();
	if (loaded) {
		Score = score;
		Money = money;
	}
	return loaded;
}

void PlayerDataClass::Reset_Player(void)
{
	Stats_Reset();
	Set_Score( 0 );
	Set_Money( 0 );
}

void	PlayerDataClass::Increment_Score( float add )		
{ 
	if (!CombatManager::Is_Gameplay_Permitted()) {
		return;
	}

	//
	// Look out for very big increments
	//
	static int warning_num = 0;
	if (add >= 10000 && ++warning_num < 10) {
		WWDEBUG_SAY(("* PlayerDataClass::Increment_Score(%10.2f) - is this ok?\n", add));
		LOG_CALL_STACK;
	}

	Score = (float)Score + add; 

	//
	// TSS101001 - let's try giving 1 credit per point
	//
	if (add > 0) {
		Increment_Money(add);
	}
}

void	PlayerDataClass::Increment_Money( float add )		
{ 
	if (add > 0 && !CombatManager::Is_Gameplay_Permitted()) {
		return;
	}

	//
	// Look out for very big increments
	//
#pragma message ("(gth) this caused a crash and seems like debugging code so I'm disabling it...")
#if 0 
	static int warning_num = 0;
	if (add >= 10000 && ++warning_num < 10) {
		WWDEBUG_SAY(("* PlayerDataClass::Increment_Money(%f) - is this ok?\n", add));
		LOG_CALL_STACK;
	}
#endif

	Money = (float)Money + add; 

	if ( add > 0 ) {
		Stats_Add_Credit_Grant( (int) add );
	}

	//Set_Object_Dirty_Bit(NetworkObjectClass::BIT_OCCASIONAL, true);
}

/*
**
*/
void	PlayerDataClass::Apply_Damage_Points( float points, DamageableGameObj * victim )
{
	//Increment_Score( ::fabs(points) );
	Increment_Score( points );

	// If this is the star's PlayerData, display the points on the HUD
	if ( COMBAT_STAR && COMBAT_STAR->Get_Player_Data() == this ) {
		HUDClass::Display_Points( points );
	}

}

void	PlayerDataClass::Apply_Death_Points( float points, DamageableGameObj * victim )
{
	Increment_Score( points );

	if ( Get_GameObj() == COMBAT_STAR && COMBAT_STAR != NULL ) {
		HUDClass::Display_Points( points );
	}
}

bool	PlayerDataClass::Purchase_Item( int cost )
{
	bool retval = false;

	if (cost >= 0) {

		//
		//	Check to ensure the player has enough cash
		//
		float money = (float)Money;
		if (money >= cost) {
			/*
			money -= cost;
			Money = money;
			*/
			//
			// Use Increment_Money so that dirty is set.
			//
			Increment_Money(-1 * cost);

			retval = true;
		}
	}

	return retval;
}


//
//	Import_Rare
//
void	PlayerDataClass::Import_Occasional( BitStreamClass & packet )
{
	//
	//	Get the score and money from the server
	//

	float score = packet.Get(score);
	Score = score;

	float money = packet.Get(money);
	Money = money;
}


//
//	Export_Rare
//
void	PlayerDataClass::Export_Occasional( BitStreamClass & packet )
{
	//
	//	Transmit the score and money
	//
	packet.Add ((float)Score);
	packet.Add ((float)Money);
}


/*
** Stats
*/
void	PlayerDataClass::Stats_Reset( void )
{
	StatTimeInGame = 0.0f;
	StatTimeInSession = 0.0f;
	StatEnemiesKilled = 0;
	StatAlliesKilled = 0;
	StatShotsFired = 0;
	StatHeadShots = 0;
	StatTorsoShots = 0;
	StatArmShots = 0;
	StatLegShots = 0;
	StatCrotchShots = 0;
	StatFinalHealth = 0;
	StatPowerups = 0;
	StatVehiclesDestroyed = 0;
	StatTimeInVehicles = 0;
	StatKillsFromVehicles = 0;
	StatSquishes = 0;
	StatCreditsGranted = 0;
	StatBuildingsDestroyed = 0;
	StatHeadHits = 0;
	StatTorsoHits = 0;
	StatArmHits = 0;
	StatLegHits = 0;
	StatCrotchHits = 0;

	StatLastWeaponIndex = -1;
	StatWeaponIDFired.Delete_All();
	StatWeaponFireCount.Delete_All();
}

void	PlayerDataClass::Stats_Add_Weapon_Fired( int weapon_id )
{
	// Check for using same weapon as last time
	if ((StatLastWeaponIndex >= 0) && (StatWeaponIDFired[StatLastWeaponIndex] == weapon_id)) {
		StatWeaponFireCount[StatLastWeaponIndex]++;
		return;
	}

	// See if we already have this weapon
	for (int i = 0; i < StatWeaponIDFired.Count(); i++) {
		if (StatWeaponIDFired[i] == weapon_id) {
			StatLastWeaponIndex = i;
			StatWeaponFireCount[StatLastWeaponIndex]++;
			return;
		}
	}

	// Add this new weapon
	StatLastWeaponIndex = StatWeaponIDFired.Count();
	StatWeaponIDFired.Add(weapon_id);
	StatWeaponFireCount.Add(1);
}

//------------------------------------------------------------------------------------
int PlayerDataClass::Get_Weapon_Fired_Count(void) const
{
	return StatWeaponIDFired.Count();
}

//------------------------------------------------------------------------------------
bool PlayerDataClass::Get_Weapon_Fired(int index, unsigned long& weaponID, unsigned long& firedCount) const
{
	if ((index >= 0) && (index < StatWeaponIDFired.Count())) {
		weaponID = (unsigned long)StatWeaponIDFired[index];
		firedCount = (unsigned long)StatWeaponFireCount[index];
		return true;
	}

	return false;
}














/*
bool	PlayerDataClass::Purchase_Item( int cost )
{
	bool retval = false;

	//
	//	Check to ensure the player has enough cash
	//
	int score = (int)Score;
	if (score >= cost) {
		score -= cost;
		Score = score;
		retval = true;
	}

	return retval;
}
*/

