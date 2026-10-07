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
 *                     $Archive:: /Commando/Code/Combat/weaponbag.cpp                         $* 
 *                                                                                             * 
 *                      $Author:: Tom_s                                                       $* 
 *                                                                                             * 
 *                     $Modtime:: 1/02/02 4:21p                                               $* 
 *                                                                                             * 
 *                    $Revision:: 55                                                          $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#include "weaponbag.h"
#include <vector>
#include "renegade_client_effects.h"
#include "weapons.h"
#include "debug.h"
#include "weaponmanager.h"
#include "wwpacket.h"
#include "armedgameobj.h"
#include "inventory.h"

/*
**
*/
WeaponBagClass::WeaponBagClass( ArmedGameObj * owner ) :
	Owner( owner ),
	WeaponIndex( 0 ),
	IsChanged( true ),
	HUDIsChanged( true )
{
	Mark_Owner_Dirty();

	WeaponList.Add( NULL );		// Index 0 is no weapon
}

WeaponBagClass::~WeaponBagClass( void )
{
	while ( WeaponList.Count() ) {
		delete	WeaponList[0];
		WeaponList.Delete( 0 );
	}
}

/*
** WeaponBagClass Save and Load
*/
enum	{
	CHUNKID_VARIABLES						=	921991503,
	CHUNKID_WEAPON_LIST,
	CHUNKID_WEAPON_ENTRY,

	MICROCHUNKID_WEAPON_INDEX			=	1,
};

bool	WeaponBagClass::Save( ChunkSaveClass & csave )
{
	int i;
	csave.Begin_Chunk( CHUNKID_VARIABLES );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_WEAPON_INDEX, WeaponIndex );
	csave.End_Chunk();

	csave.Begin_Chunk( CHUNKID_WEAPON_LIST );
	for( i = 1; i < WeaponList.Count(); i++ ) {
		csave.Begin_Chunk( CHUNKID_WEAPON_ENTRY );
		if (WeaponList[i] == NULL || !WeaponList[i]->Save(csave)) {
			csave.Report_Error();
		}
		csave.End_Chunk();
	}
	csave.End_Chunk();

	// Don't need to save Owner or IsChanged;
	return !csave.Has_Error();
}

bool	WeaponBagClass::Load( ChunkLoadClass &cload )
{
	bool loaded = true;
	bool variables_seen = false;
	bool weapon_list_seen = false;
	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_VARIABLES:
				if (variables_seen) loaded = false;
				variables_seen = true;
				while (cload.Open_Micro_Chunk()) {
					switch(cload.Cur_Micro_Chunk_ID()) {
						READ_MICRO_CHUNK( cload, MICROCHUNKID_WEAPON_INDEX, WeaponIndex );
						default:
							Debug_Say(("Unhandled Micro Chunk:%d File:%s Line:%d\r\n",cload.Cur_Micro_Chunk_ID(),__FILE__,__LINE__));
							break;
					}
					cload.Close_Micro_Chunk();
				}
				break;

			case CHUNKID_WEAPON_LIST:
				if (weapon_list_seen || WeaponList.Count() != 1) loaded = false;
				weapon_list_seen = true;
				while (cload.Open_Chunk()) {
					WWASSERT( cload.Cur_Chunk_ID() == CHUNKID_WEAPON_ENTRY );
					WeaponClass *weapon = new WeaponClass;
					if (weapon->Load(cload)) {
						WeaponList.Add(weapon);
					} else {
						delete weapon;
						loaded = false;
					}
					cload.Close_Chunk();
				}
				break;

			default:
				Debug_Say(("Unhandled Chunk:%d File:%s Line:%d\r\n",cload.Cur_Chunk_ID(),__FILE__,__LINE__));
				break;

		}
		cload.Close_Chunk();
	}

	IsChanged = true;
	HUDIsChanged = true;
	if (WeaponIndex < 0 || WeaponIndex >= WeaponList.Count()) loaded = false;
	return loaded && variables_seen && weapon_list_seen && !cload.Has_Error();
}


/*
**
*/
bool	WeaponBagClass::Is_Weapon_Owned( int weapon_id )
{
	WeaponClass * weapon = Find_Weapon( WeaponManager::Find_Weapon_Definition( weapon_id ) );
	return ( weapon != NULL && weapon->Does_Weapon_Exist() );
}

bool	WeaponBagClass::Is_Ammo_Full( int weapon_id )
{
	WeaponClass * weapon = Find_Weapon( WeaponManager::Find_Weapon_Definition( weapon_id ) );
	return weapon && weapon->Is_Ammo_Maxed();
}


/*
**
*/
void	WeaponBagClass::Remove_Weapon( int index )
{
	//
	//	Simply destroy the weapon if its in our list
	//
	if ( index > 0 && index < WeaponList.Count() ) {
		// Deselect while the weapon still exists; preserve the selected object
		// when removing a preceding slot. Slot zero is the permanent sentinel.
		if (WeaponIndex == index) Select_Index(0);
		delete	WeaponList[index];
		WeaponList.Delete( index );
		if (WeaponIndex > index) --WeaponIndex;
		IsChanged = HUDIsChanged = true;
		Mark_Owner_Dirty();
	}

	return ;
}

/*
**
*/
void	WeaponBagClass::Clear_Weapons( void )
{
	Select_Index(0);
	// find the next existing weapons
	while ( WeaponList.Count() > 1 ) {
		int index = WeaponList.Count()-1;
		delete WeaponList[index];
		WeaponList.Delete( index );		
	}

	return ;
}

/*
**
*/
WeaponClass * 	WeaponBagClass::Add_Weapon( const WeaponDefinitionClass * def, int rounds, bool give_weapon )
{
	if ( def == NULL ) {
		Debug_Say(( "Failed to create Weapon\n" ));
		return NULL;
	}

	WeaponClass * weapon = Find_Weapon( def );
	if ( weapon == NULL ) {
		//	Debug_Say(( "Adding new weapon %s\n", weapon->Get_Name() ));
		weapon = new WeaponClass( def );
		if ( weapon ) {
			weapon->Set_Owner( Owner );
			weapon->Add_Rounds( rounds );
			weapon->Set_Weapon_Exists( give_weapon );		// Assume it doesn't exist

			// add this weapon to the weapon list in order (0 at end)
			int index;
			for ( index = 1; index < WeaponList.Count(); index++ ) {
				if ( WeaponList[ index ]->Get_Key_Number() > weapon->Get_Key_Number() ) {
					break;
				}
			}

			if ( WeaponIndex >= index ) {
				WeaponIndex++;
			}
			WeaponList.Insert( index, weapon );

			IsChanged = true;
			HUDIsChanged = true;
#if 0			// Don't auto select
			bool use = true;
			for ( int i = 1; i < WeaponList.Count(); i++ ) {
				if ( i != index && WeaponList[ i ]->Does_Weapon_Exist() ) {
					use = false;
				}
			}

			// If no current weapon, make this weapon current
			if ( give_weapon && use ) {
				//	Debug_Say(( "Commando selecting first weapon %s\n", weapon->Get_Name() ));
				Select_Index( index );
			}
#endif
			Mark_Owner_Dirty();
		}
	} else {
		if ( give_weapon ) {					// Make sure we have it if we are supposed to
			weapon->Set_Weapon_Exists( true );
			Mark_Owner_Dirty();
		}
		weapon->Add_Rounds( rounds );		// if we already have this weapon, just take the ammo
		if ( rounds != 0 ) {
			Mark_Owner_Dirty();
		}

	}

	return weapon;
}

WeaponClass * 	WeaponBagClass::Add_Weapon( const char *weapon_name, int rounds, bool give_weapon )
{
	return Add_Weapon( WeaponManager::Find_Weapon_Definition( weapon_name ), rounds, give_weapon );
}

WeaponClass * 	WeaponBagClass::Add_Weapon( int id, int rounds, bool give_weapon )
{
	return Add_Weapon( WeaponManager::Find_Weapon_Definition( id ), rounds, give_weapon );
}

WeaponClass	*	WeaponBagClass::Get_Next_Weapon( void )
{
	// find the next existing weapons
	for ( int i = 0; i < WeaponList.Count(); i++ ) {
		int index = ( WeaponIndex + i + 1 ) % WeaponList.Count();
		// BMG remove no weapon slot
//		if ( WeaponList[ index ] == NULL || WeaponList[ index ]->Does_Weapon_Exist() ) {
		if ( WeaponList[ index ] != NULL && WeaponList[ index ]->Does_Weapon_Exist() ) {
			return WeaponList[ index ];
		}
	}
	return NULL;
}

void	WeaponBagClass::Select_Next( void ) 
{
	// Find the next existing weapons
	for ( int i = 1; i < WeaponList.Count(); i++ ) {
		int index = ( WeaponIndex + i ) % WeaponList.Count();
		// BMG remove no weapon slot
//		if ( WeaponList[ index ] == NULL || WeaponList[ index ]->Does_Weapon_Exist() ) {
		if ( WeaponList[ index ] != NULL && WeaponList[ index ]->Does_Weapon_Exist() ) {
			Select_Index( index );
			break;
		}
	}
}

void	WeaponBagClass::Select_Prev( void ) 
{
	// Find the next existing weapons
	for ( int i = 1; i < WeaponList.Count(); i++ ) {
		int index = ( WeaponIndex - i + WeaponList.Count()) % WeaponList.Count();
		// BMG remove no weapon slot
//		if ( WeaponList[ index ] == NULL || WeaponList[ index ]->Does_Weapon_Exist() ) {
		if ( WeaponList[ index ] != NULL && WeaponList[ index ]->Does_Weapon_Exist() ) {
			Select_Index( index );
			break;
		}
	}
}

void	WeaponBagClass::Select_Key_Number( int key_number ) 
{
	if ( key_number == -1 ) {
		Select_Index( 0 );
	} else {
		// Start from the current, find the next existing weapon with the right key_number
		for ( int i = 1; i < WeaponList.Count(); i++ ) {
			int index = ( WeaponIndex + i ) % WeaponList.Count();
			if (	WeaponList[ index ] != NULL && 
					WeaponList[ index ]->Does_Weapon_Exist() && 
					(int)WeaponList[ index ]->Get_Key_Number() == key_number ) {
				Select_Index( index );
				break;
			}
		}
	}
}

void	WeaponBagClass::Select_Weapon_ID( int weapon_id ) 
{
	for( int i = 1; i < WeaponList.Count(); i++ ) {
		if ( WeaponList[i]->Get_ID() == weapon_id ) {
			Select_Index ( i );
			return;
		}
	}
}

void	WeaponBagClass::Select_Weapon_Name( const char * name )
{
	if ( ( name == NULL ) || ( *name == 0 ) ) {
		Select_Index ( 0 );
	} else {
		for( int i = 1; i < WeaponList.Count(); i++ ) {
			if ( strcmp( WeaponList[i]->Get_Name(), name ) == 0 ) {
				Select_Index ( i );
				return;
			}
		}
		Debug_Say(( "Unable to select weapon %s\n", name ));
	}
}


void	WeaponBagClass::Select_Weapon( WeaponClass * weapon )
{
	for( int i = 1; i < WeaponList.Count(); i++ ) {
		if ( WeaponList[i] == weapon ) {
			Select_Index ( i );
			return;
		}
	}
}

void	WeaponBagClass::Select_Index( int index )
{
	if ( index >= WeaponList.Count() ) {
		index = 0;
	}

	if ( WeaponIndex != index ) {

		if ( Get_Weapon() ) {
			Get_Weapon()->Deselect();
		}

		WeaponIndex = index;
		IsChanged = true;
		HUDIsChanged = true;

		if ( Get_Weapon() ) {
			Get_Weapon()->Select();
		}

		Mark_Owner_Dirty();
	}
}

void WeaponBagClass::Deselect( void )
{
	// Need to be able to tell client to put weapon away
	Select_Index( 0 );
}


//-----------------------------------------------------------------------------
bool WeaponBagClass::Import_TT_Weapon_Selection(BitStreamClass &packet, bool has_selection)
{
	int count = 0, selected = 0;
	packet.Get(count);
	if (packet.Has_Read_Error() || count < 0 ||
		unsigned(count) > (packet.Get_Bit_Write_Position() - packet.Get_Bit_Read_Position()) / 32) {
		packet.Mark_Read_Error();
		return false;
	}
	std::vector<int> ids;
	for (int i = 0; i < count; ++i) {
		int id = 0;
		packet.Get(id);
		if (packet.Has_Read_Error() || !WeaponManager::Find_Weapon_Definition(id)) {
			packet.Mark_Read_Error(); return false;
		}
		for (unsigned j = 0; j < ids.size(); ++j)
			if (ids[j] == id) { packet.Mark_Read_Error(); return false; }
		ids.push_back(id);
	}
	if (has_selection) packet.Get(selected);
	if (packet.Has_Read_Error() || (has_selection && (selected < 0 || selected > count))) {
		packet.Mark_Read_Error(); return false;
	}
	// Modern occasional updates reconcile membership, not ammunition. Keep
	// existing weapon instances/rounds and let the original bag own changes.
	for (int i = WeaponList.Count() - 1; i > 0; --i) {
		int match = -1;
		for (unsigned j = 0; j < ids.size(); ++j)
			if (WeaponList[i]->Get_ID() == ids[j]) { match = j; break; }
		if (match < 0) Remove_Weapon(i);
		else ids.erase(ids.begin() + match);
	}
	for (unsigned i = 0; i < ids.size(); ++i) {
		Add_Weapon(ids[i], 0);
		if (WeaponIndex == 0 && WeaponList.Count() > 1) Select_Index(1);
	}
	const bool changed = has_selection && WeaponIndex != selected;
	if (changed) Select_Index(selected);
	return changed;
}

void WeaponBagClass::Import_Weapon_List(BitStreamClass & packet)
{
	bool modern = false;
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
	modern = Renegade_Client_Uses_TT_Replication();
#endif
	// Validate the whole list before changing inventory. A mismatched protocol
	// must not reinterpret a physics definition as a weapon definition.
	BitStreamClass scan;
	scan = packet;
	int count = 0;
	scan.Get(count);
	if (scan.Has_Read_Error() || count < 0 ||
		static_cast<unsigned>(count) > (scan.Get_Bit_Write_Position() - scan.Get_Bit_Read_Position()) / 64) {
		packet.Mark_Read_Error();
		return;
	}
	for (int i = 0; i < count; ++i) {
		int id = 0, rounds = 0;
		scan.Get(id);
		scan.Get(rounds);
		if (scan.Has_Read_Error() || !WeaponManager::Find_Weapon_Definition(id)) {
			packet.Mark_Read_Error();
			return;
		}
	}
	int weapon_count = packet.Get(weapon_count);
	int weapon_id;
	for (int weapon = 0; weapon < weapon_count; weapon++) {
		weapon_id = packet.Get(weapon_id);
		int total_rounds = 0;
		USHORT clip = 0, inventory = 0;
		if (modern) {
			packet.Get(clip);
			packet.Get(inventory);
		} else packet.Get(total_rounds);
		Add_Weapon(weapon_id, 0);

		WeaponClass * weapon_instance = NULL;
		for( int i = 1; i < WeaponList.Count(); i++ ) {
			if ( (int) WeaponList[i]->Get_Definition()->Get_ID() == weapon_id ) {
				weapon_instance = WeaponList[i];
			}
		}
		if ( weapon_instance != NULL ) {
			if (modern) {
				weapon_instance->Set_Clip_Rounds(clip < 0x8000 ? int(clip) : int(clip) - 0x10000);
				weapon_instance->Set_Inventory_Rounds(inventory < 0x8000 ? int(inventory) : int(inventory) - 0x10000);
			} else weapon_instance->Set_Total_Rounds( total_rounds );
		}
	}
}

//-----------------------------------------------------------------------------
void WeaponBagClass::Export_Weapon_List(BitStreamClass & packet)
{
	packet.Add((int) (WeaponList.Count() - 1));
	for( int i = 1; i < WeaponList.Count(); i++ ) {
		packet.Add(WeaponList[i]->Get_ID());
		packet.Add(WeaponList[i]->Get_Total_Rounds());
	}
}

//-----------------------------------------------------------------------------
WeaponClass * WeaponBagClass::Find_Weapon( const WeaponDefinitionClass * def )
{
	if ( def == NULL ) {
		return NULL;
	}

	for( int i = 1; i < WeaponList.Count(); i++ ) {
		if ( (unsigned)WeaponList[i]->Get_ID() == def->Get_ID() ) {
			return WeaponList[i];
		}
	}
//	Debug_Say(( "Didn't Find weapon %s\n", name ));
	return NULL;
}


/*
**
*/
bool	WeaponBagClass::Move_Contents( WeaponBagClass * source )
{
	// Was anyhting actually moved?
	bool moved = false;

	// Move all the weapons and ammo from the source to me
	// For each weapon in the source bag...
	for( int i = 1; i < source->WeaponList.Count(); i++ ) {
		WeaponClass * weapon = source->WeaponList[i];

		// If I already have it,
		WeaponClass * my_weapon = Find_Weapon( weapon->Get_Definition() );
		if ( my_weapon ) {
			// Copy the ammo and the weapon
			if ( !my_weapon->Is_Ammo_Maxed() && weapon->Get_Total_Rounds() != 0 ) {
				my_weapon->Add_Rounds( weapon->Get_Total_Rounds() );
				moved = true;
			}

			if ( weapon->Does_Weapon_Exist() && !my_weapon->Does_Weapon_Exist() ) {
				my_weapon->Set_Weapon_Exists( true );
				moved = true;
			}
//			Debug_Say(( "Add %s %d\n", weapon->Get_Definition()->Get_Name(), weapon->Get_Total_Rounds() ));
		} else {
			// else, give it to me
			Add_Weapon( weapon->Get_Definition(), weapon->Get_Total_Rounds(), weapon->Does_Weapon_Exist() );
			if ( weapon->Does_Weapon_Exist() ) {
				moved = true;
			}
//			Debug_Say(( "Give %s %d\n", weapon->Get_Definition()->Get_Name(), weapon->Get_Total_Rounds() ));
		}
	}

	Mark_Owner_Dirty();

	return moved;
}


/*
**
*/
void	WeaponBagClass::Store_Inventory( InventoryClass * inventory )
{
	for( int i = 1; i < WeaponList.Count(); i++ ) {
		WeaponClass * weapon = WeaponList[i];
		inventory->Add_Weapon( weapon->Get_ID(), weapon->Get_Total_Rounds(), weapon->Does_Weapon_Exist() );
	}
}

/*
**
*/
void	WeaponBagClass::Mark_Owner_Dirty( void ) 
{
	if ( Owner != NULL ) {
		Owner->Set_Object_Dirty_Bit( NetworkObjectClass::BIT_OCCASIONAL, true );
	}
}
