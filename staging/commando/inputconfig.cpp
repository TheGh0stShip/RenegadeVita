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
 *                     $Archive:: /Commando/Code/commando/inputconfig.cpp        $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 7/18/01 6:09p                                               $*
 *                                                                                             *
 *                    $Revision:: 2                                                           $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#include "inputconfig.h"
#include "chunkio.h"
#include "debug.h"
#if defined(RENEGADE_VITA_PORT)
#include <string.h>
#endif


////////////////////////////////////////////////////////////////
//	Save/load constants
////////////////////////////////////////////////////////////////
enum
{
	CHUNKID_VARIABLES			= 0x07181106,
};

enum
{
	VARID_DISPLAY_NAME			= 1,
	VARID_FILENAME,
	VARID_IS_DEFAULT,
	VARID_IS_CUSTOM,
};


////////////////////////////////////////////////////////////////
//
//	Save
//
////////////////////////////////////////////////////////////////
void
InputConfigClass::Save (ChunkSaveClass &csave)
{
	//
	//	Save the variables to their own chunk
	//
	csave.Begin_Chunk (CHUNKID_VARIABLES);
		WRITE_MICRO_CHUNK_WIDESTRING	(csave, VARID_DISPLAY_NAME,	DisplayName);
		WRITE_MICRO_CHUNK_WWSTRING		(csave, VARID_FILENAME,			Filename);
		WRITE_MICRO_CHUNK					(csave, VARID_IS_DEFAULT,		IsDefault);
		WRITE_MICRO_CHUNK					(csave, VARID_IS_CUSTOM,		IsCustom);
	csave.End_Chunk ();
	return ;
}


////////////////////////////////////////////////////////////////
//
//	Load
//
////////////////////////////////////////////////////////////////
void
InputConfigClass::Load (ChunkLoadClass &cload)
{
	//
	//	Read all the sub-chunks
	//
	while (cload.Open_Chunk ()) {
		switch (cload.Cur_Chunk_ID ()) {

			case CHUNKID_VARIABLES:
				Load_Variables (cload);
				break;

			default:
				Debug_Say (("Unrecognized InputConfigClass::Load Chunk ID\n"));
				break;
		}

		cload.Close_Chunk ();
	}

	return ;
}


////////////////////////////////////////////////////////////////
//
//	Load_Variables
//
////////////////////////////////////////////////////////////////
void
InputConfigClass::Load_Variables (ChunkLoadClass &cload)
{
	//
	//	Read all the microchunks
	//
	while (cload.Open_Micro_Chunk ()) {
		switch(cload.Cur_Micro_Chunk_ID ()) {			

#if defined(RENEGADE_VITA_PORT)
			// CONFIG.DAT is writable user state. The original string macros
			// size each buffer to the stored byte count and copy no terminator,
			// so a truncated or damaged record left the strings unterminated.
			// Reserve and write the terminator after the bytes actually read.
			case VARID_DISPLAY_NAME:
			{
				const int count = (int)(cload.Cur_Micro_Chunk_Length () / sizeof (WCHAR));
				WCHAR *buffer = DisplayName.Get_Buffer (count + 1);
				const int read = (int)(cload.Read (buffer, count * sizeof (WCHAR)) / sizeof (WCHAR));
				buffer[read] = 0;
				break;
			}
			case VARID_FILENAME:
			{
				const int count = (int)cload.Cur_Micro_Chunk_Length ();
				char *buffer = Filename.Get_Buffer (count + 1);
				const int read = (int)cload.Read (buffer, count);
				buffer[read] = 0;
				break;
			}
#else
			READ_MICRO_CHUNK_WIDESTRING	(cload, VARID_DISPLAY_NAME,	DisplayName);
			READ_MICRO_CHUNK_WWSTRING		(cload, VARID_FILENAME,			Filename);
#endif
			READ_MICRO_CHUNK					(cload, VARID_IS_DEFAULT,		IsDefault);
			READ_MICRO_CHUNK					(cload, VARID_IS_CUSTOM,		IsCustom);
		}

		cload.Close_Micro_Chunk ();
	}

#if defined(RENEGADE_VITA_PORT)
	//
	//	Filename is joined onto user/config/ for load, save and delete. Keep
	// only a bounded bare leaf name; Load_Config_List drops cleared records.
	//
	const char *name = Filename;
	const size_t name_length = ::strlen (name);
	bool name_valid = name_length > 0 && name_length < 64 &&
		::strstr (name, "..") == NULL;
	for (size_t index = 0; name_valid && index < name_length; index ++) {
		const unsigned char ch = (unsigned char)name[index];
		name_valid = ch >= 32 && ch != '/' && ch != '\\' && ch != ':';
	}
	if (!name_valid) {
		Filename = "";
	}
#endif

	return ;
}


////////////////////////////////////////////////////////////////
//
//	operator=
//
////////////////////////////////////////////////////////////////
const InputConfigClass &
InputConfigClass::operator= (const InputConfigClass &src)
{
	if (&src != this) {
		DisplayName	= src.DisplayName;
		Filename		= src.Filename;
		IsDefault	= src.IsDefault;
		IsCustom		= src.IsCustom;
	}

	return *this;
}
