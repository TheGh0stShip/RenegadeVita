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
 *                 Project Name : Combat																		  *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/Combat/purchasesettings.h                    $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 1/05/02 5:14p                                               $*
 *                                                                                             *
 *                    $Revision:: 6                                                           $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#if defined(_MSC_VER)
#pragma once
#endif

#ifndef __PURCHASESETTINGS_H
#define __PURCHASESETTINGS_H

#include "always.h"
#include "definition.h"
#include "widestring.h"
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
#include "networkobject.h"
#endif


///////////////////////////////////////////////////////////////////////////////////////////
//
//	PurchaseSettingsDefClass
//
///////////////////////////////////////////////////////////////////////////////////////////
class PurchaseSettingsDefClass : public DefinitionClass
#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
    , public NetworkObjectClass
#endif
{
public:

	//////////////////////////////////////////////////////////////////////////
	//	Public constants
	//////////////////////////////////////////////////////////////////////////
	typedef enum
	{
		TYPE_CLASSES		= 0,
		TYPE_VEHICLES,
		TYPE_EQUIPMENT,
		TYPE_SECRET_CLASSES,
		TYPE_SECRET_VEHICLES,
		TYPE_AIR,
		TYPE_NAVAL,
		TYPE_COUNT
	} TYPE;

	typedef enum
	{
		TEAM_GDI				= 0,
		TEAM_NOD,
		TEAM_MUTANT_GDI,
		TEAM_MUTANT_NOD,
		TEAM_COUNT
	} TEAM;
	
	//////////////////////////////////////////////////////////////////////////
	//	Public constructors/destructors
	//////////////////////////////////////////////////////////////////////////
	PurchaseSettingsDefClass (void);
	~PurchaseSettingsDefClass (void);

#if defined(RENEGADE_A4_ORIGINAL_FRONTEND) && !RENEGADE_VITA_M00_DEMO
    uint32 Get_Network_Class_ID() const override { return 2004; }
    void Import_Occasional(BitStreamClass &packet) override;
    void Export_Occasional(BitStreamClass &packet) override;
    // Definitions own this lifetime; network cleanup must not delete presets.
    void Delete() override {}
    void Set_Delete_Pending() override {}
#endif
    bool Get_Hidden(int index) const { return Hidden[index]; }
    bool Get_Disabled(int index) const { return Disabled[index]; }
    bool Get_Busy(int index) const { return Busy[index]; }
    bool Get_Page_Hidden() const { return PageHidden; }
    bool Get_Page_Disabled() const { return PageDisabled; }
    bool Get_Page_Busy() const { return PageBusy; }
    bool Is_Available(int index) const {
        return Is_Valid_Entry(index, -1) && !PageHidden && !PageDisabled && !PageBusy &&
            !Hidden[index] && !Disabled[index] && !Busy[index];
    }
    static PurchaseSettingsDefClass *Find_Network_Definition(int type, int team);

	//////////////////////////////////////////////////////////////////////////
	//	Public methods
	//////////////////////////////////////////////////////////////////////////

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
	TYPE								Get_Type (void)							{ return Type; }
	static bool Is_Valid_Entry(int index, int alternate) {
		return index >= 0 && index < MAX_ENTRIES && alternate >= -1 && alternate < MAX_ALTERNATES;
	}
	TEAM								Get_Team (void)							{ return Team; }

	const WCHAR *					Get_Name (int index);
	int								Get_Cost (int index)						{ return CostList[index]; }
	int								Get_Definition (int index)				{ return DefinitionList[index]; }
	const StringClass &			Get_Texture (int index)					{ return TextureList[index]; }

	const WCHAR *					Get_Enlisted_Name (int index);
	int								Get_Enlisted_Definition (int index)	{ return DefinitionList[index]; }
	const StringClass &			Get_Enlisted_Texture (int index)		{ return TextureList[index]; }

	//
	//	Alternate support
	//
	int								Get_Alt_Definition (int index, int alt_index)	{ return AlternateDefinitionList[index][alt_index]; }
	const StringClass &			Get_Alt_Texture (int index, int alt_index)		{ return AlternateTextureList[index][alt_index]; }

	//
	//	Singleton access
	//
	static PurchaseSettingsDefClass *	Find_Definition (TYPE type, TEAM team);
	
	//
	//	Editable support
	//
	DECLARE_EDITABLE (PurchaseSettingsDefClass, DefinitionClass);

protected:

	//////////////////////////////////////////////////////////////////////////
	//	Protected methods
	//////////////////////////////////////////////////////////////////////////
	bool				Load_Variables (ChunkLoadClass &cload);

	//////////////////////////////////////////////////////////////////////////
	//	Protected constants
	//////////////////////////////////////////////////////////////////////////
	enum
	{
		ROWS	= 4,
		COLS	= 5,
		MAX_ALTERNATES = 3,
		MAX_ENTRIES = 10
	};
	
	//////////////////////////////////////////////////////////////////////////
	//	Protected member data
	//////////////////////////////////////////////////////////////////////////

	TEAM					Team;
	TYPE					Type;
	int					CostList[MAX_ENTRIES];
	int					DefinitionList[MAX_ENTRIES];
	int					NameList[MAX_ENTRIES];
	StringClass			TextureList[MAX_ENTRIES];

	int					AlternateDefinitionList[MAX_ENTRIES][MAX_ALTERNATES];
	StringClass			AlternateTextureList[MAX_ENTRIES][MAX_ALTERNATES];
	
	static PurchaseSettingsDefClass *	DefinitionArray[TYPE_COUNT][TEAM_COUNT];
	int					PublishedType;
	int					PublishedTeam;
	PurchaseSettingsDefClass *	PreviousDefinition;
    bool Hidden[MAX_ENTRIES] = {};
    bool Disabled[MAX_ENTRIES] = {};
    bool Busy[MAX_ENTRIES] = {};
    bool PageHidden = false, PageDisabled = false, PageBusy = false;
};


#endif //__PURCHASESETTINGS_H
