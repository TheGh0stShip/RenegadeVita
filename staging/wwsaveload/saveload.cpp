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
 *                 Project Name : WWSaveLoad                                                   *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/wwsaveload/saveload.cpp                      $*
 *                                                                                             *
 *                       Author:: Greg Hjelstrom                                               *
 *                                                                                             *
 *                     $Modtime:: 12/09/01 6:42p                                              $*
 *                                                                                             *
 *                    $Revision:: 19                                                          $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#include "saveload.h"
#include "saveloadsubsystem.h"
#include "persist.h"
#include "persistfactory.h"
#include "chunkio.h"
#include "wwdebug.h"
#include "saveloadstatus.h"
#include "wwhack.h"
#include "wwprofile.h"

#pragma warning(disable:4201) // warning C4201: nonstandard extension used : nameless struct/union
#include <windows.h>
#include "systimer.h"


SaveLoadSubSystemClass *		SaveLoadSystemClass::SubSystemListHead = NULL;
PersistFactoryClass *			SaveLoadSystemClass::FactoryListHead = NULL;
SList<PostLoadableClass>		SaveLoadSystemClass::PostLoadList;
SList<PersistClass>			SaveLoadSystemClass::RejectedLoadList;
PointerRemapClass					SaveLoadSystemClass::PointerRemapper;
bool								SaveLoadSystemClass::ReportedLoadFailure = false;



bool SaveLoadSystemClass::Save (ChunkSaveClass &csave,SaveLoadSubSystemClass & subsystem)
{
	bool ok = true;

	if (subsystem.Contains_Data()) {
		ok = csave.Begin_Chunk (subsystem.Chunk_ID ());
		ok &= subsystem.Save (csave);
		ok = csave.End_Chunk () && ok;
	}

	return ok && !csave.Has_Error();
}

bool SaveLoadSystemClass::Load (ChunkLoadClass &cload,bool auto_post_load,
	bool require_player_save_subsystems)
{
	WWLOG_PREPARE_TIME_AND_MEMORY("SaveLoadSystemClass::Load");
	PointerRemapper.Reset();
	ReportedLoadFailure = false;
	// Rejected objects outlive the failed Load return so the caller can unwind
	// partially loaded owners that may have remapped pointers to them.
	PersistClass *retired_object = RejectedLoadList.Remove_Head();
	while (retired_object != NULL) {
		delete retired_object;
		retired_object = RejectedLoadList.Remove_Head();
	}
	WWLOG_INTERMEDIATE("PointerRemapper.Reset()");
	bool ok = true;
	SaveLoadSubSystemClass *sys = NULL;
	if (require_player_save_subsystems) {
		for (sys = SubSystemListHead; sys != NULL; sys = sys->NextSubSystem) {
			sys->PlayerSaveLoadSeen = false;
		}
	}

	// Load each chunk we encounter and link the manager into the PostLoad list
	while (cload.Open_Chunk ()) {
		SaveLoadStatus::Inc_Status_Count();		// Count the sub systems loaded
		sys = Find_Sub_System(cload.Cur_Chunk_ID ());
		WWLOG_INTERMEDIATE("Find_Sub_System");
		if (sys != NULL) {
//WWRELEASE_SAY(("			Name: %s\n",sys->Name()));
			if (require_player_save_subsystems && sys->Required_For_Player_Save() &&
				sys->PlayerSaveLoadSeen) {
				ok = false;
			} else {
				if (require_player_save_subsystems && sys->Required_For_Player_Save()) {
					sys->PlayerSaveLoadSeen = true;
				}
				INIT_SUB_STATUS(sys->Name());
				ok &= sys->Load(cload);
				WWLOG_INTERMEDIATE(sys->Name());
			}
		}
		cload.Close_Chunk();
	}
	ok = !cload.Has_Error() && ok;

	if (require_player_save_subsystems) {
		for (sys = SubSystemListHead; sys != NULL; sys = sys->NextSubSystem) {
			if (sys->Required_For_Player_Save() && !sys->PlayerSaveLoadSeen) {
				ok = false;
			}
			sys->PlayerSaveLoadSeen = false;
		}
	}
	ok = !ReportedLoadFailure && ok;

	// Process all of the pointer remap requests
	ok = PointerRemapper.Process() && ok;
	WWLOG_INTERMEDIATE("PointerRemapper.Process()");
	PointerRemapper.Reset();
	WWLOG_INTERMEDIATE("PointerRemapper.Reset()");

	// A rejected load still remaps pointer tokens above so partially created
	// objects can be destroyed safely, but it must never execute their post-load
	// behavior. Remove registrations while every registered object is alive.
	if (!ok) {
		Discard_Post_Load_Callbacks();
	} else if (auto_post_load) {
		Post_Load_Processing(NULL);
	}
	WWLOG_INTERMEDIATE("PostLoadProcessing");

	return ok;
}

void SaveLoadSystemClass::Report_Load_Failure (void)
{
	ReportedLoadFailure = true;
}

bool SaveLoadSystemClass::Has_Reported_Load_Failure (void)
{
	return ReportedLoadFailure;
}

void SaveLoadSystemClass::Retain_Rejected_Object_Until_Next_Load (PersistClass *object)
{
	if (object != NULL && RejectedLoadList.Find_Node(object) == NULL) {
		RejectedLoadList.Add_Tail(object);
	}
}

// Nework update macro for post loader.
#define UPDATE_NETWORK 											\
	if (network_callback) {                            \
		unsigned long time2 = TIMEGETTIME();            \
		if (time2 - time > 20) {                        \
			network_callback();                          \
			time = time2;                                \
		}                                               \
	}                                                  \

bool SaveLoadSystemClass::Post_Load_Processing (void(*network_callback)(void))
{
	unsigned long time = TIMEGETTIME();

	// Call PostLoad on each PersistClass that wanted post-load
	PostLoadableClass * obj = PostLoadList.Remove_Head();
	while (obj) {
		UPDATE_NETWORK;
		obj->On_Post_Load();
		obj->Set_Post_Load_Registered(false);
		obj = PostLoadList.Remove_Head();
	}

	return true;
}

void SaveLoadSystemClass::Discard_Post_Load_Callbacks (void)
{
	PostLoadableClass *obj = PostLoadList.Remove_Head();
	while (obj != NULL) {
		obj->Set_Post_Load_Registered(false);
		obj = PostLoadList.Remove_Head();
	}
}

void SaveLoadSystemClass::Register_Sub_System (SaveLoadSubSystemClass * sys)
{
	WWASSERT(sys != NULL);
	Link_Sub_System(sys);
}


void SaveLoadSystemClass::Unregister_Sub_System (SaveLoadSubSystemClass * sys)
{
	WWASSERT(sys != NULL);
	Unlink_Sub_System(sys);
}


SaveLoadSubSystemClass * SaveLoadSystemClass::Find_Sub_System (uint32 chunk_id)
{
	// TODO: need a d-s that gives fast searching based on chunk_id!!
	SaveLoadSubSystemClass * sys;
	for ( sys = SubSystemListHead; sys != NULL; sys = sys->NextSubSystem ) {
		if ( sys->Chunk_ID() == chunk_id ) {
			break;
		}
	}
	return sys;
}

void SaveLoadSystemClass::Register_Persist_Factory(PersistFactoryClass * factory)
{
	WWASSERT(factory != NULL);
	Link_Factory(factory);
}

void SaveLoadSystemClass::Unregister_Persist_Factory(PersistFactoryClass * factory)
{
	WWASSERT(factory != NULL);
	Unlink_Factory(factory);
}

PersistFactoryClass * SaveLoadSystemClass::Find_Persist_Factory(uint32 chunk_id)
{
	// TODO: need a d-s that gives fast searching based on chunk_id!!
	PersistFactoryClass * fact;
	for ( fact = FactoryListHead; fact != NULL; fact = fact->NextFactory ) {
		if ( fact->Chunk_ID() == chunk_id ) {
			break;
		}
	}
	return fact;
}

bool SaveLoadSystemClass::Is_Post_Load_Callback_Registered(PostLoadableClass * obj)
{
	// obsolete!
	bool retval = false;

	SLNode<PostLoadableClass> *list_node = NULL;
	for (	list_node = PostLoadList.Head();
			retval == false && list_node != NULL;
			list_node = list_node->Next())
	{
		retval = (list_node->Data() == obj);
	}

	return retval;
}

void SaveLoadSystemClass::Register_Post_Load_Callback(PostLoadableClass * obj)
{
	WWASSERT(obj != NULL);
	if (!obj->Is_Post_Load_Registered()) {
		obj->Set_Post_Load_Registered(true);
		PostLoadList.Add_Head(obj);
	}
}

void SaveLoadSystemClass::Register_Pointer (void *old_pointer, void *new_pointer)
{
	PointerRemapper.Register_Pointer(old_pointer,new_pointer);
}

#ifdef WWDEBUG

void SaveLoadSystemClass::Request_Pointer_Remap (void **pointer_to_convert,const char * file,int line)
{
	PointerRemapper.Request_Pointer_Remap(pointer_to_convert,file,line);
}

void SaveLoadSystemClass::Request_Ref_Counted_Pointer_Remap (RefCountClass **pointer_to_convert,const char * file,int line)
{
	PointerRemapper.Request_Ref_Counted_Pointer_Remap(pointer_to_convert,file,line);
}

#else

void SaveLoadSystemClass::Request_Pointer_Remap (void **pointer_to_convert)
{
	PointerRemapper.Request_Pointer_Remap(pointer_to_convert);
}

void SaveLoadSystemClass::Request_Ref_Counted_Pointer_Remap (RefCountClass **pointer_to_convert)
{
	PointerRemapper.Request_Ref_Counted_Pointer_Remap(pointer_to_convert);
}

#endif

void SaveLoadSystemClass::Link_Sub_System(SaveLoadSubSystemClass * sys)
{
	WWASSERT(sys != NULL);
	if (sys != NULL) {
		WWASSERT(sys->NextSubSystem == NULL);			// sys should never be registered twice!
		sys->NextSubSystem = SubSystemListHead;
		SubSystemListHead = sys;
	}
}

void SaveLoadSystemClass::Unlink_Sub_System(SaveLoadSubSystemClass * sys)
{
	WWASSERT(sys != NULL);
	SaveLoadSubSystemClass * cursys = SubSystemListHead;
	SaveLoadSubSystemClass * prev = NULL;

	while (cursys != sys) {
		prev = cursys;
		cursys = cursys->NextSubSystem;
	}

	if (prev == NULL) {
		SubSystemListHead = sys->NextSubSystem;
	} else {
		prev->NextSubSystem = sys->NextSubSystem;
	}

	sys->NextSubSystem = NULL;
}


void SaveLoadSystemClass::Link_Factory(PersistFactoryClass * fact)
{
	WWASSERT(fact != NULL);
	if (fact != NULL) {
		WWASSERT(fact->NextFactory == NULL);			// factories should never be registered twice!
		fact->NextFactory = FactoryListHead;
		FactoryListHead = fact;
	}
}

void SaveLoadSystemClass::Unlink_Factory(PersistFactoryClass * fact)
{
	WWASSERT(fact != NULL);

	PersistFactoryClass * curfact = FactoryListHead;
	PersistFactoryClass * prev = NULL;

	while (curfact != fact) {
		prev = curfact;
		curfact = curfact->NextFactory;
	}

	if (prev == NULL) {
		FactoryListHead = fact->NextFactory;
	} else {
		prev->NextFactory = fact->NextFactory;
	}

	fact->NextFactory = NULL;
}

void Force_Link_WWSaveLoad (void)
{
	FORCE_LINK( Twiddler );
	return ;
}
