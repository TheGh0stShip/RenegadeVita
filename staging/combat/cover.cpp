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
 *                     $Archive:: /Commando/Code/Combat/cover.cpp                             $* 
 *                                                                                             * 
 *                      $Author:: Byon_g                                                      $* 
 *                                                                                             * 
 *                     $Modtime:: 4/17/01 11:44a                                              $* 
 *                                                                                             * 
 *                    $Revision:: 7                                                           $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "cover.h"
#include "debug.h"
#include "chunkio.h"
#include "saveload.h"
#include "crandom.h"

/*
**
*/
DynamicVectorClass<CoverEntryClass *>		CoverManager::CoverPositions;

/*
**
*/
void	CoverManager::Init( void )
{
}

void	CoverManager::Shutdown( void )
{
	Remove_All();
}

/*
**
*/
enum	{
	CHUNKID_COVER_ENTRY					=	524001203,
};

bool	CoverManager::Save( ChunkSaveClass & csave )
{
	for ( int index = 0; index < CoverPositions.Count(); index++ ) {
		if (CoverPositions[index] == NULL) {
			csave.Report_Error();
			continue;
		}
		csave.Begin_Chunk( CHUNKID_COVER_ENTRY );
		if (!CoverPositions[index]->Save(csave)) csave.Report_Error();
		csave.End_Chunk();
	}

	return !csave.Has_Error();
}

bool	CoverManager::Load( ChunkLoadClass & cload )
{
	WWASSERT( CoverPositions.Count() == 0 );
	bool loaded = true;

	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_COVER_ENTRY:
			{
				CoverEntryClass * cover = NEW_REF( CoverEntryClass, () );
				if (cover->Load(cload)) Add_Entry(cover);
				else loaded = false;
				cover->Release_Ref();
				break;
			}

			default:
				Debug_Say(( "Unrecognized CombatSaveLoad chunkID\n" ));
				break;

		}
		cload.Close_Chunk();
	}
	return loaded && !cload.Has_Error();
}


/*
**
*/
void	CoverManager::Add_Entry( CoverEntryClass * entry )
{
	if ( entry != NULL ) {
		entry->Add_Ref();
		CoverPositions.Add( entry );
	}
}

void	CoverManager::Remove_Entry( CoverEntryClass * entry )
{
	if ( entry != NULL ) {
		CoverPositions.Delete( entry );
		entry->Release_Ref();
	}
}

void	CoverManager::Remove_All( void )
{
	while ( CoverPositions.Count() ) {
		CoverPositions[0]->Release_Ref();
		CoverPositions.Delete( 0 );
	}
}

/*
**
*/
CoverEntryClass * CoverManager::Request_Cover( const Vector3 & cur_pos, const Vector3 & danger, float max_dist )
{
	// Find a cover spot, not in use, within max_dist, that blocks from danger
	int best_index = -1;
	int best_dist = max_dist;
	for ( int index = 0; index < CoverPositions.Count(); index++ ) {
		CoverEntryClass * cover = CoverPositions[ index ];
		if ( cover->Get_In_Use() ) {	
			continue;		// Already in use
		}
		Vector3 range_vector = cur_pos - cover->Get_Transform().Get_Translation();
		float dist = range_vector.Length();
		if ( dist > max_dist ) {  
			continue;		// Too far away
		}

		if ( !Is_Cover_Safe( cover, danger ) ) {
			continue;		// Does not provide cover
		}

		if ( best_dist < dist ) {
			continue;		// Already ahave a better one
		}

		if ( best_index != -1 ) {
			if ( FreeRandom.Get_Int() & 1 ) {
				continue;
			}
		}

		best_index = index;
		best_dist = dist;
	}

	if ( best_index != -1 ) {
//		Debug_Say(( "Chose cover # %d\n", best_index ));
		CoverPositions[ best_index ]->Set_In_Use( true );
		return CoverPositions[best_index];
	}

	return NULL;
}

void	CoverManager::Release_Cover( CoverEntryClass * entry )
{
	WWASSERT( entry->Get_In_Use() );
	entry->Set_In_Use( false );
}

bool	CoverManager::Is_Cover_Safe( CoverEntryClass * cover, const Vector3 & danger )
{
	WWASSERT( cover );

	Vector3 danger_local;
	Matrix3D::Inverse_Transform_Vector( cover->Get_Transform(), danger, &danger_local );
	if ( danger_local.X < WWMath::Fabs(danger_local.Y) ) {
		return false;
	}
	return true;
}

/*
**
*/
enum	{
	CHUNKID_VARIABLES								= 524001323,

	MICROCHUNKID_TRANSFORM						= 1,
	MICROCHUNKID_CROUCH,
	MICROCHUNKID_IN_USE,
	MICROCHUNKID_ATTACK_POSITION,
	MICROCHUNKID_REMAP_PTR,
};

bool	CoverEntryClass::Save( ChunkSaveClass & csave )
{
	CoverEntryClass * me = this;

	csave.Begin_Chunk( CHUNKID_VARIABLES );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_TRANSFORM,     Transform );				
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_CROUCH,        Crouch );				
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_IN_USE,        InUse );				
		for ( int i = 0; i < AttackPositionList.Count(); i++ ) {
			Vector3 pos = AttackPositionList[i];
			WRITE_MICRO_CHUNK( csave, MICROCHUNKID_ATTACK_POSITION,     pos );				
		}
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_REMAP_PTR,     me );				
	csave.End_Chunk();

	return true;
}

bool	CoverEntryClass::Load( ChunkLoadClass & cload )
{
	WWASSERT( AttackPositionList.Count() == 0 );

	uint32 old_me_token = 0U;
	bool variables_seen = false;
	bool loaded = true;
	uint32 loaded_values = 0U;

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

#define READ_REQUIRED_COVER_VALUE(id, value, bit) \
						case (id): \
							if ((loaded_values & (bit)) != 0U || cload.Cur_Micro_Chunk_Length() != sizeof(value) || \
								cload.Read(&(value), sizeof(value)) != sizeof(value)) loaded = false; \
							else loaded_values |= (bit); \
							break
						READ_REQUIRED_COVER_VALUE(MICROCHUNKID_TRANSFORM, Transform, 1U);
						READ_REQUIRED_COVER_VALUE(MICROCHUNKID_CROUCH, Crouch, 2U);
						READ_REQUIRED_COVER_VALUE(MICROCHUNKID_IN_USE, InUse, 4U);

						case MICROCHUNKID_ATTACK_POSITION:
						{
							Vector3 pos;
							if (cload.Cur_Micro_Chunk_Length() != sizeof(pos) ||
								cload.Read(&pos, sizeof(pos)) != sizeof(pos)) loaded = false;
							else AttackPositionList.Add(pos);
							break;
						}

						READ_REQUIRED_COVER_VALUE(MICROCHUNKID_REMAP_PTR, old_me_token, 8U);
#undef READ_REQUIRED_COVER_VALUE

						default:
							Debug_Say(( "Unrecognized CoverEntry Variable chunkID %d\n", cload.Cur_Micro_Chunk_ID() ));
							break;

					}
					cload.Close_Micro_Chunk();
				}
				break;

			default:
				Debug_Say(( "Unrecognized CoverEntry chunkID\n" ));
				break;

		}
		cload.Close_Chunk();
	}

	// publish my remap pair
	loaded = loaded && variables_seen && loaded_values == 15U && old_me_token != 0U && !cload.Has_Error();
	if (loaded) {
		SaveLoadSystemClass::Register_Pointer(
			reinterpret_cast<CoverEntryClass *>(static_cast<uintptr_t>(old_me_token)), this);
	}

	return loaded;
}

Vector3 CoverEntryClass::Get_Attack_Position( Vector3 & enemy_pos )	
{ 
	// Find a cover position that will allow attack of enemy_pos (not yet)

	// default to cover spot
	Vector3	pos = Transform.Get_Translation();

	if ( AttackPositionList.Count() ) {
		int index = FreeRandom.Get_Int( AttackPositionList.Count() );
		pos = AttackPositionList[index];
	}

	return pos;
}
