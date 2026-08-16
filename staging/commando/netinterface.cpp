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

//
// Filename:     netinterface.cpp
// Project:      Network.lib, for Commando
// Author:       Tom Spencer-Smith
// Date:         Dec 1998
// Description:  
//

#include "netinterface.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "miscutil.h"
#include "wwdebug.h"
#include "win.h"
#include "mmsys.h"
#include "renegade_network_provider.h"
#include "useroptions.h"

//
// class statics
//
WideStringClass	cNetInterface::Nickname;
int cNetInterface::mSidePreference = -1;

//-----------------------------------------------------------------------------
cNetInterface::cNetInterface(void)
{
}

//-----------------------------------------------------------------------------
cNetInterface::~cNetInterface(void)
{
}

//-----------------------------------------------------------------------------
WideStringClass cNetInterface::Get_Nickname(void)
{
	// LAN/direct-IP identity remains the original cNetInterface nickname.
	return Nickname;
}

//-----------------------------------------------------------------------------
void cNetInterface::Set_Nickname(WideStringClass & name)
{
	Nickname = name;
	if (Nickname.Get_Length() > 30) Nickname[30] = 0;
}

//-----------------------------------------------------------------------------
void cNetInterface::Set_Random_Nickname(void)
{      
	char name[MAX_COMPUTERNAME_LENGTH + 1];
	DWORD size = sizeof(name);
	::GetComputerName(name, &size);

	int length_test = MAX_COMPUTERNAME_LENGTH + 1 - MAX_NICKNAME_LENGTH;
	if (length_test > 0) {
		name[MAX_NICKNAME_LENGTH - 1] = 0;
	}

	WideStringClass widename;
	widename.Convert_From(name);

   Set_Nickname(widename);
}


void cNetInterface::Set_Side_Preference(int side)
{
	mSidePreference = side;
}


int cNetInterface::Get_Side_Preference(void)
{
	return mSidePreference;
}
























//WideStringClass & cNetInterface::Get_Nickname(void)
	/*
	Nickname = name;

  //
	// Abbreviate to 9 chars
	//
	if (Nickname.Get_Length() > 9) {
		Nickname[9] = 0;
	}
	*/

	/*
	Nickname = name;
	
	int max_len = 0;
	if (cGameSpyAdmin::Is_Gamespy_Game()) {
		max_len = 34;
	} else {
		max_len = 9;
	}

	if (Nickname.Get_Length() > max_len) {
		Nickname[max_len] = 0;
	}
	*/

   //return Nickname;

