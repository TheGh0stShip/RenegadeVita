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
 *                 Project Name : wwtranslatedb																  *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/wwtranslatedb/tdbcategory.cpp      $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 11/22/00 10:53a                                             $*
 *                                                                                             *
 *                    $Revision:: 2                                                           $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "tdbcategory.h"

#include "chunkio.h"
#include "persistfactory.h"
#include "translatedbids.h"
#include "tdbcategories.h"


//////////////////////////////////////////////////////////////////////////////
//	Persist factory
//////////////////////////////////////////////////////////////////////////////
SimplePersistFactoryClass<TDBCategoryClass, CHUNKID_TDBCATEGORY> _TDBCategoryPersistFactory;


//////////////////////////////////////////////////////////////////////////////
//	Constants
//////////////////////////////////////////////////////////////////////////////
enum
{
	CHUNKID_VARIABLES				= 0x11221022,
	CHUNKID_BASE_CLASS,
};

enum
{
	VARID_ID							= 0x01,
	VARID_NAME,
};


///////////////////////////////////////////////////////////////////////
//
//	TDBCategoryClass
//
///////////////////////////////////////////////////////////////////////
TDBCategoryClass::TDBCategoryClass (void)	:
	ID (CATEGORY_DEFAULT)
{
	return ;
}


///////////////////////////////////////////////////////////////////////
//
//	TDBCategoryClass
//
///////////////////////////////////////////////////////////////////////
TDBCategoryClass::TDBCategoryClass (const TDBCategoryClass &src)	:
	ID (CATEGORY_DEFAULT)
{
	(*this) = src;
	return ;
}


///////////////////////////////////////////////////////////////////////
//
//	~TDBCategoryClass
//
///////////////////////////////////////////////////////////////////////
TDBCategoryClass::~TDBCategoryClass (void)
{
	return ;
}


/////////////////////////////////////////////////////////////////
//
//	operator=
//
/////////////////////////////////////////////////////////////////
const TDBCategoryClass &	
TDBCategoryClass::operator= (const TDBCategoryClass &src)
{
	ID		= src.ID;
	Name	= src.Name;

	return *this;
}


///////////////////////////////////////////////////////////////////////
//
//	Get_Factory
//
///////////////////////////////////////////////////////////////////////
const PersistFactoryClass &
TDBCategoryClass::Get_Factory (void) const
{
	return _TDBCategoryPersistFactory;
}


/////////////////////////////////////////////////////////////////
//
//	Save
//
/////////////////////////////////////////////////////////////////
bool
TDBCategoryClass::Save (ChunkSaveClass &csave)
{
	csave.Begin_Chunk (CHUNKID_BASE_CLASS);
		PersistClass::Save (csave);
	csave.End_Chunk ();	

	csave.Begin_Chunk (CHUNKID_VARIABLES);
		Save_Variables (csave);
	csave.End_Chunk ();
	return true;
}


/////////////////////////////////////////////////////////////////
//
//	Load
//
/////////////////////////////////////////////////////////////////
bool
TDBCategoryClass::Load (ChunkLoadClass &cload)
{
	bool loaded = true;
	bool base_seen = false;
	bool variables_seen = false;
	while (cload.Open_Chunk ()) {		
		switch (cload.Cur_Chunk_ID ()) {

			case CHUNKID_BASE_CLASS:
				if (base_seen || !PersistClass::Load (cload)) loaded = false;
				base_seen = true;
				break;
			
			case CHUNKID_VARIABLES:
				if (variables_seen || !Load_Variables (cload)) loaded = false;
				variables_seen = true;
				break;
		}

		cload.Close_Chunk ();
	}

	return loaded && base_seen && variables_seen && !Name.Is_Empty() && !cload.Has_Error();
}


/////////////////////////////////////////////////////////////////
//
//	Save_Variables
//
/////////////////////////////////////////////////////////////////
void
TDBCategoryClass::Save_Variables (ChunkSaveClass &csave)
{	
	//
	//	Save each variable to its own micro chunk
	//
	WRITE_MICRO_CHUNK					(csave, VARID_ID,		ID);
	WRITE_MICRO_CHUNK_WWSTRING		(csave, VARID_NAME,	Name);	
	return ;
}


/////////////////////////////////////////////////////////////////
//
//	Load_Variables
//
/////////////////////////////////////////////////////////////////
bool
TDBCategoryClass::Load_Variables (ChunkLoadClass &cload)
{	
	unsigned int fields_seen = 0;
	bool loaded = true;
	while (cload.Open_Micro_Chunk ()) {
		switch (cload.Cur_Micro_Chunk_ID ()) {			
			
			case VARID_ID:
				if ((fields_seen & 0x01U) || cload.Cur_Micro_Chunk_Length() != sizeof(ID) ||
					cload.Read(&ID, sizeof(ID)) != sizeof(ID)) loaded = false;
				fields_seen |= 0x01U; break;
			case VARID_NAME:
				if ((fields_seen & 0x02U) || cload.Read(Name.Get_Buffer(cload.Cur_Micro_Chunk_Length()),
					cload.Cur_Micro_Chunk_Length()) != cload.Cur_Micro_Chunk_Length()) loaded = false;
				fields_seen |= 0x02U; break;
		}

		cload.Close_Micro_Chunk ();
	}

	return loaded && fields_seen == 0x03U && !cload.Has_Error();
}
