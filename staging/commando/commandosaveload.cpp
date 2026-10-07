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
 *                     $Archive:: /Commando/Code/Commando/commandosaveload.cpp                $* 
 *                                                                                             * 
 *                      $Author:: Byon_g                                                      $* 
 *                                                                                             * 
 *                     $Modtime:: 9/06/01 1:57p                                               $* 
 *                                                                                             * 
 *                    $Revision:: 7                                                           $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "commandosaveload.h"
#include "chunkio.h"
#include "cnetwork.h"
#include "debug.h"
#include "wwmemlog.h"
#include "god.h"
#include "campaign.h"

/*
**
*/
CommandoSaveLoadClass	_CommandoSaveLoad;

enum	{
	CHUNKID_NETWORK								= 1011991043,
	CHUNKID_GOD,
	CHUNKID_CAMPAIGN,
};

/*
**
*/
bool	CommandoSaveLoadClass::Save( ChunkSaveClass &csave )
{
	WWMEMLOG(MEM_GAMEDATA);
	bool saved = true;

	csave.Begin_Chunk( CHUNKID_NETWORK );
	saved = cNetwork::Save(csave) && saved;
	saved = csave.End_Chunk() && saved;

	csave.Begin_Chunk( CHUNKID_GOD );
	saved = cGod::Save(csave) && saved;
	saved = csave.End_Chunk() && saved;

	csave.Begin_Chunk( CHUNKID_CAMPAIGN );
	saved = CampaignManager::Save(csave) && saved;
	saved = csave.End_Chunk() && saved;

	return saved && !csave.Has_Error();
}

bool	CommandoSaveLoadClass::Load( ChunkLoadClass &cload )
{
	WWMEMLOG(MEM_GAMEDATA);
	bool loaded = true;
	bool network_seen = false;
	bool god_seen = false;
	bool campaign_seen = false;

	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_NETWORK:
				if (network_seen) {
					loaded = false;
				} else {
					network_seen = true;
					loaded = cNetwork::Load( cload ) && loaded;
				}
				break;

			case CHUNKID_GOD:
				if (god_seen) {
					loaded = false;
				} else {
					god_seen = true;
					loaded = cGod::Load( cload ) && loaded;
				}
				break;

			case CHUNKID_CAMPAIGN:
				if (campaign_seen) {
					loaded = false;
				} else {
					campaign_seen = true;
					loaded = CampaignManager::Load( cload ) && loaded;
				}
				break;

			default:
				Debug_Say(( "Unrecognized Commando chunkID\n" ));
				break;

		}
		cload.Close_Chunk();
	}
	return loaded && network_seen && god_seen && campaign_seen;
}


