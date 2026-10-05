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
 *                 Project Name : Commando / G                                                 * 
 *                                                                                             * 
 *                     $Archive:: /Commando/Code/Combat/reflist.cpp          $* 
 *                                                                                             * 
 *                      $Author:: Patrick                                                     $* 
 *                                                                                             * 
 *                     $Modtime:: 2/06/01 2:26p                                               $* 
 *                                                                                             * 
 *                    $Revision:: 1                                                           $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#include "reflist.h"
#include "scriptablegameobj.h"




bool	ReferencerClass::Save( ChunkSaveClass & csave )
{
	uint32 target_token = static_cast<uint32>(
		reinterpret_cast<uintptr_t>(ReferenceTarget));
	csave.Begin_Chunk( CHUNKID_REF_VARIABLES );
		WRITE_MICRO_CHUNK( csave, MICROCHUNKID_TARGET, target_token );
	csave.End_Chunk();
	return !csave.Has_Error();
}


bool	ReferencerClass::Load( ChunkLoadClass & cload )
{
	uint32 target_token = 0;
	bool variables_seen = false;
	bool target_seen = false;
	bool loaded = true;

	WWASSERT( ReferenceTarget == NULL );
	WWASSERT( TargetReferencerListNext == NULL );

	while (cload.Open_Chunk()) {
		if (cload.Cur_Chunk_ID() != CHUNKID_REF_VARIABLES || variables_seen) {
			loaded = false;
		} else {
			variables_seen = true;
			while (cload.Open_Micro_Chunk()) {
				if (cload.Cur_Micro_Chunk_ID() != MICROCHUNKID_TARGET || target_seen ||
					cload.Cur_Micro_Chunk_Length() != sizeof(target_token) ||
					cload.Read(&target_token, sizeof(target_token)) != sizeof(target_token)) {
					loaded = false;
				} else {
					target_seen = true;
				}
				cload.Close_Micro_Chunk();
			}
		}
		cload.Close_Chunk();
	}
	loaded = loaded && variables_seen && target_seen && !cload.Has_Error();
	if (!loaded) return false;

	ReferenceTarget = target_token != 0
		? reinterpret_cast<ReferenceableClass<ScriptableGameObj> *>(
			static_cast<uintptr_t>(target_token))
		: NULL;

	if ( ReferenceTarget != NULL ) {
		REQUEST_POINTER_REMAP( (void **)&ReferenceTarget );
		SaveLoadSystemClass::Register_Post_Load_Callback( this );
	}

	return true;
}


void	ReferencerClass::On_Post_Load(void)	
{
	// if we found our target, re-link to it.  
	if ( ReferenceTarget ) {
		ScriptableGameObj* data = ReferenceTarget->Get_Data();
		ReferenceTarget = NULL;
		*this = data;
	}
}


const ReferencerClass & ReferencerClass::operator = ( const ScriptableGameObj * reference_target )
{
	if ( ReferenceTarget != NULL ) {		// if I currently have a target

		ReferencerClass *referencer = ReferenceTarget->ReferencerListHead;
		WWASSERT( referencer );

		if ( referencer == this ) {	// if I'm the first in the list, fix the head
			ReferenceTarget->ReferencerListHead = TargetReferencerListNext;
			TargetReferencerListNext = NULL;
			ReferenceTarget = NULL;
		} else {
			WWASSERT( referencer->TargetReferencerListNext );

			while ( ReferenceTarget != NULL ) {	// Find me in the list, and remove me
				if ( referencer->TargetReferencerListNext == this ) {
					referencer->TargetReferencerListNext = TargetReferencerListNext;
					TargetReferencerListNext = NULL;
					ReferenceTarget = NULL;
				} else {
					referencer = referencer->TargetReferencerListNext;
					WWASSERT( referencer != NULL );
				}
			}
		}
	}

	WWASSERT( ReferenceTarget == NULL );

	if ( reference_target != NULL ) {			// if new reference is non-null
		ReferenceTarget = (ReferenceableClass<ScriptableGameObj> *) (reference_target);		// set it and link list
		TargetReferencerListNext = ReferenceTarget->ReferencerListHead;
		ReferenceTarget->ReferencerListHead = this;
	}

	return *this;
}
