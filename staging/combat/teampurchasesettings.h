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
 ***              C O N F I D E N T I A L  ---  W E S T W O O D  S T U D I O S               ***
 ***********************************************************************************************
 *                                                                                             *
 *                 Project Name : combat                                                       *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/Combat/teampurchasesettings.h                $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 10/23/01 3:15p                                              $*
 *                                                                                             *
 *                    $Revision:: 2                                                           $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#if defined(_MSC_VER)
#pragma once
#endif

#ifndef __TEAMPURCHASESETTINGS_H
#define __TEAMPURCHASESETTINGS_H

#include "translatedb.h"
#include "wwstring.h"
#include "definition.h"
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
#include "networkobject.h"
#endif

//////////////////////////////////////////////////////////////////////
//
//	TeamPurchaseSettingsDefClass
//
//////////////////////////////////////////////////////////////////////
class TeamPurchaseSettingsDefClass : public DefinitionClass
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
    , public NetworkObjectClass
#endif
{
public:

	//////////////////////////////////////////////////////////////////////
	//	Public constants
	//////////////////////////////////////////////////////////////////////
	typedef enum
	{
		TEAM_GDI				= 0,
		TEAM_NOD,
		TEAM_COUNT
	} TEAM;
	
	//////////////////////////////////////////////////////////////////////
	//	Public constructors/destructors
	//////////////////////////////////////////////////////////////////////
	TeamPurchaseSettingsDefClass (void);
	~TeamPurchaseSettingsDefClass (void);

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
    uint32 Get_Network_Class_ID() const override { return 2005; }
    void Import_Occasional(BitStreamClass &packet) override;
    void Export_Occasional(BitStreamClass &packet) override;
    // The definition manager, not the network delete queue, owns presets.
    void Delete() override {}
    void Set_Delete_Pending() override {}
#endif
    bool Get_Hidden(int index) const { return Hidden[index]; }
    bool Get_Disabled(int index) const { return Disabled[index]; }
    bool Get_Busy(int index) const { return Busy[index]; }
    bool Is_Available(int index) const {
        return Is_Valid_Entry(index) && !Hidden[index] && !Disabled[index] && !Busy[index];
    }

	//////////////////////////////////////////////////////////////////////
	//	Public methods
	//////////////////////////////////////////////////////////////////////

	//
	//	From DefinitionClass
	//
	virtual uint32								Get_Class_ID (void) const;
	virtual PersistClass *					Create (void) const ;
	virtual bool								Save (ChunkSaveClass &csave);
	virtual bool								Load (ChunkLoadClass &cload);
	virtual void								On_Load_Rejected (void);
	virtual const PersistFactoryClass &	Get_Factory (void) const;	

	//
	//	Accessors
	//
	TEAM								Get_Team (void)							{ return Team; }
	static bool Is_Valid_Entry(int index) { return index >= 0 && index < MAX_ENTRIES; }

	const WCHAR *					Get_Enlisted_Name (int index);
	int								Get_Enlisted_Definition (int index)	{ return DefinitionList[index]; }
	const StringClass &			Get_Enlisted_Texture (int index)		{ return TextureList[index]; }

	const WCHAR *					Get_Beacon_Name (void)			{ return TRANSLATE (BeaconNameID); }
	int								Get_Beacon_Cost (void)			{ return BeaconCost; }
	int								Get_Beacon_Definition (void)	{ return BeaconDefinitionID; }
	const StringClass &			Get_Beacon_Texture (void)		{ return BeaconTextureName; }

	const WCHAR *					Get_Supply_Name (void)			{ return TRANSLATE (SupplyNameID); }
	const StringClass &			Get_Supply_Texture (void)		{ return SupplyTextureName; }

	//
	//	Singleton access
	//
	static TeamPurchaseSettingsDefClass *	Get_Definition (TEAM team);
	
	//
	//	Editable support
	//
	DECLARE_EDITABLE (TeamPurchaseSettingsDefClass, DefinitionClass);

protected:

	//////////////////////////////////////////////////////////////////////
	//	Protected methods
	//////////////////////////////////////////////////////////////////////
	bool				Load_Variables (ChunkLoadClass &cload);

	//////////////////////////////////////////////////////////////////////
	//	Protected constants
	//////////////////////////////////////////////////////////////////////
	enum
	{
		MAX_ENTRIES = 4
	};
	
	//////////////////////////////////////////////////////////////////////
	//	Protected member data
	//////////////////////////////////////////////////////////////////////
	TEAM					Team;
	
	//
	//	Enlisted character settings
	//
	int					DefinitionList[MAX_ENTRIES];
	int					NameList[MAX_ENTRIES];
	StringClass			TextureList[MAX_ENTRIES];

	//
	//	Beacon settings
	//
	int					BeaconCost;
	int					BeaconDefinitionID;
	int					BeaconNameID;
	StringClass			BeaconTextureName;

	//
	//	Supply settings
	//
	int					SupplyNameID;
	StringClass			SupplyTextureName;
	
	static TeamPurchaseSettingsDefClass *	DefinitionArray[TEAM_COUNT];
	int					PublishedTeam;
	TeamPurchaseSettingsDefClass *	PreviousDefinition;
    bool Hidden[MAX_ENTRIES] = {};
    bool Disabled[MAX_ENTRIES] = {};
    bool Busy[MAX_ENTRIES] = {};
};


#endif //__TEAMPURCHASESETTINGS_H
