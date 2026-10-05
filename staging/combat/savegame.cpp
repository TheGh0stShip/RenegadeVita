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
 *                     $Archive:: /Commando/Code/Combat/savegame.cpp                          $* 
 *                                                                                             * 
 *                      $Author:: Tom_s                                                       $* 
 *                                                                                             * 
 *                     $Modtime:: 3/07/02 12:05p                                              $* 
 *                                                                                             * 
 *                    $Revision:: 45                                                          $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "savegame.h"
#if defined(__vita__)
#include "vita_runtime_log.h"
#define RV_SAVE_PHASE(phase) Vita_Append_A22_Runtime_Breadcrumb("save", "phase=%s", phase)
#else
#define RV_SAVE_PHASE(phase) ((void)0)
#endif
#include "definitionmgr.h"
#include "debug.h"
#include "chunkio.h"
#include "ffactory.h"
#include "combatsaveload.h"
#include "physstaticsavesystem.h"
#include "physdynamicsavesystem.h"
#include "AudioSaveLoad.h"
#include "matrix3d.h"
#include "scripts.h"
#include "combat.h"
#include "backgroundmgr.h"
#include "conversationmgr.h"
#include "WeatherMgr.h"
#include "wwmemlog.h"
#include "translatedb.h"
#include "mapmgr.h"
#include "encyclopediamgr.h"
#include "ffactorylist.h"
#include "mixfile.h"
#include "texturethumbnail.h"
#include "systeminfolog.h"
#include "wwprofile.h"
#include <stdlib.h>
#include "specialbuilds.h"
#if defined(__vita__)
#include "a35_level_load_status.h"
#endif

/*
**
*/
StringClass		SaveGameManager::MapFilename;
StringClass		SaveGameManager::CurrentGameFilename;
WideStringClass	SaveGameManager::Description;
int				SaveGameManager::MissionDescriptionID = 0;
const char *	SaveGameManager::DefaultDefinitionFilename = "Objects.DDB";

/*
**
*/
enum	{

#ifdef BETACLIENT
	//
	// This CHUNKID_LEVEL_INFO tweaking is temporary, to disallow the aircraft maps 
	// to be used outside of the beta. The maps distributed with the Beta client must have 
	// 1011991648 replaced with 1011991650 and 1011991649 replaced with 1011991651.
	//
	CHUNKID_LEVEL_INFO					=	1011991650,
#else
	CHUNKID_LEVEL_INFO					=	1011991648,
#endif

	CHUNKID_LEVEL_DATA,

	MICROCHUNKID_MAP_FILENAME			=	1,
	MICROCHUNKID_MISSION_DESCRIPTION,
	MICROCHUNKID_DESCRIPTION,
};

#if defined(RENEGADE_VITA_PORT)
static bool Read_Player_Save_Level_Info(ChunkLoadClass &cload,
	StringClass &map_filename, WideStringClass &description, int &mission_description)
{
	StringClass loaded_map(0, true);
	WideStringClass loaded_description;
	int loaded_mission_description = 0;
	uint32 loaded_values = 0U;
	bool loaded = true;
	while (cload.Open_Micro_Chunk()) {
		const uint32 length = cload.Cur_Micro_Chunk_Length();
		switch(cload.Cur_Micro_Chunk_ID()) {
			case MICROCHUNKID_MAP_FILENAME:
				if ((loaded_values & 1U) != 0U || length == 0U || length > 512U) loaded = false;
				else {
					loaded_values |= 1U;
					loaded = cload.Read(loaded_map.Get_Buffer(length), length) == length && loaded;
					loaded = static_cast<uint32>(loaded_map.Get_Length() + 1) == length && loaded;
				}
				break;
			case MICROCHUNKID_MISSION_DESCRIPTION:
				if ((loaded_values & 2U) != 0U || length != sizeof(loaded_mission_description)) loaded = false;
				else {
					loaded_values |= 2U;
					loaded = cload.Read(&loaded_mission_description, sizeof(loaded_mission_description)) ==
						sizeof(loaded_mission_description) && loaded;
				}
				break;
			case MICROCHUNKID_DESCRIPTION:
				if ((loaded_values & 4U) != 0U || length < sizeof(WCHAR) ||
					(length % sizeof(WCHAR)) != 0U || length > 4096U) loaded = false;
				else {
					loaded_values |= 4U;
					loaded = cload.Read(loaded_description.Get_Buffer(length / sizeof(WCHAR)), length) == length && loaded;
					loaded = static_cast<uint32>((loaded_description.Get_Length() + 1) * sizeof(WCHAR)) == length && loaded;
				}
				break;
			default:
				break;
		}
		cload.Close_Micro_Chunk();
	}

	const int map_length = loaded_map.Get_Length();
	loaded = loaded && loaded_values == 7U && map_length > 4 &&
		::stricmp(&loaded_map[map_length - 4], ".LSD") == 0 && !cload.Has_Error();
	if (loaded) {
		map_filename = loaded_map;
		description = loaded_description;
		mission_description = loaded_mission_description;
	}
	return loaded;
}

static bool Read_Player_Save_Envelope(ChunkLoadClass &cload,
	StringClass &map_filename, WideStringClass &description, int &mission_description)
{
	bool level_info_seen = false;
	bool level_data_seen = false;
	bool loaded = true;
	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {
			case CHUNKID_LEVEL_INFO:
				if (level_info_seen || level_data_seen) loaded = false;
				else {
					level_info_seen = true;
					loaded = Read_Player_Save_Level_Info(cload, map_filename,
						description, mission_description) && loaded;
				}
				break;
			case CHUNKID_LEVEL_DATA:
				if (!level_info_seen || level_data_seen) loaded = false;
				else level_data_seen = true;
				break;
			default:
				loaded = false;
				break;
		}
		cload.Close_Chunk();
	}
	return loaded && level_info_seen && level_data_seen && !cload.Has_Error();
}
#endif

/*
**
*/
void _cdecl SaveGameManager::Save_Game( const char * filename, ... )
{
#if defined(RENEGADE_VITA_PORT)
	LastSaveWriteSucceeded = false;
#endif
	Debug_Say(( "Save Game %s\n", filename ));
	CurrentGameFilename = filename;
	RV_SAVE_PHASE("open");

	FileClass * file = _TheWritingFileFactory->Get_File( filename );
	WWASSERT(file);
#if defined(RENEGADE_VITA_PORT)
	if (file == NULL) { RV_SAVE_PHASE("file-failed"); return; }
	if (!file->Open(FileClass::WRITE)) {
		RV_SAVE_PHASE("open-failed");
		_TheWritingFileFactory->Return_File(file);
		return;
	}
#else
	file->Open(FileClass::WRITE);
#endif

	ChunkSaveClass csave(file);
	bool save_succeeded = true;

	csave.Begin_Chunk( CHUNKID_LEVEL_INFO );
		WRITE_MICRO_CHUNK_WWSTRING( csave,		MICROCHUNKID_MAP_FILENAME,			MapFilename );
		WRITE_MICRO_CHUNK_WIDESTRING( csave,	MICROCHUNKID_DESCRIPTION,			Description );
		WRITE_MICRO_CHUNK( csave,				MICROCHUNKID_MISSION_DESCRIPTION,	MissionDescriptionID );
	csave.End_Chunk();

	csave.Begin_Chunk( CHUNKID_LEVEL_DATA );

		_ConversationMgrSaveLoad.Set_Category_To_Save (ConversationMgrClass::CATEGORY_LEVEL);

		RV_SAVE_PHASE("combat-begin");
		save_succeeded = SaveLoadSystemClass::Save( csave, _CombatSaveLoad ) && save_succeeded;
		RV_SAVE_PHASE("combat-end");
		RV_SAVE_PHASE("conversations-begin");
		save_succeeded = SaveLoadSystemClass::Save( csave, _ConversationMgrSaveLoad ) && save_succeeded;
		RV_SAVE_PHASE("conversations-end");
		RV_SAVE_PHASE("physics-begin");
		save_succeeded = SaveLoadSystemClass::Save( csave, _PhysDynamicSaveSystem ) && save_succeeded;
		RV_SAVE_PHASE("physics-end");
		RV_SAVE_PHASE("encyclopedia-begin");
		save_succeeded = SaveLoadSystemClass::Save( csave, _TheEncyclopediaMgrSaveLoadSubsystem ) && save_succeeded;
		RV_SAVE_PHASE("encyclopedia-end");
		RV_SAVE_PHASE("audio-begin");
		save_succeeded = SaveLoadSystemClass::Save( csave, _DynamicAudioSaveLoadSubsystem ) && save_succeeded;
		RV_SAVE_PHASE("audio-end");
		RV_SAVE_PHASE("map-begin");
		save_succeeded = SaveLoadSystemClass::Save( csave, _TheMapMgrSaveLoadSubsystem ) && save_succeeded;
		RV_SAVE_PHASE("map-end");

		va_list arg_list;
		va_start( arg_list, filename );

		bool done = false;
		while ( !done ) {
			SaveLoadSubSystemClass * sub_system = va_arg( arg_list, SaveLoadSubSystemClass * );
			if ( sub_system != NULL ) {
				save_succeeded = SaveLoadSystemClass::Save( csave, *sub_system ) && save_succeeded;
			} else {
				done = true;
			}
		}
		va_end (arg_list);

	csave.End_Chunk();

	RV_SAVE_PHASE("close-begin");
#if defined(RENEGADE_VITA_PORT)
	if (!save_succeeded) {
		file->Abort_Write();
	}
#endif
	file->Close();
	RV_SAVE_PHASE("close-end");
#if defined(RENEGADE_VITA_PORT)
	LastSaveWriteSucceeded = save_succeeded && !file->Has_Write_Failed();
	RV_SAVE_PHASE(LastSaveWriteSucceeded ? "write-complete" : "write-failed");
#endif

	_TheWritingFileFactory->Return_File(file);

}


#if defined(RENEGADE_VITA_PORT)
bool SaveGameManager::LastSaveWriteSucceeded = false;
#endif

void	SaveGameManager::Pre_Load_Game
(
	 const char *	filename,
	 StringClass & filename_to_load,
	 StringClass &	lsd_filename 
)
{
	//
	//	Get the root name and extension from the filename
	//
	char root_name[_MAX_FNAME] = { 0 };
	char extension[_MAX_EXT] = { 0 };
	::_splitpath (filename, NULL, NULL, root_name, extension);

	SystemInfoLog::Set_Current_Level(root_name);
	filename_to_load = filename;

	//
	//	Reset the search order
	//
	if (FileFactoryListClass::Get_Instance () != NULL)
	{
		FileFactoryListClass::Get_Instance ()->Reset_Search_Start();
	}

	//
	//	Is this a mix file?
	//
	if (::strcmpi (extension, ".mix") == 0) {
		
		StringClass thumb_filename(root_name,true);
		thumb_filename+=".thu";
		ThumbnailManagerClass::Add_Thumbnail_Manager(thumb_filename,filename);

		//
		//	Build the dynamic data filename from mix file's root name
		//
		filename_to_load.Format ("%s.ldd", root_name);
		lsd_filename .Format ("%s.lsd", root_name);

		//
		//	HACK HACK - Put the level 9 mix file first...
		//
		if (	::lstrcmpi (filename, "M09.mix") == 0 &&
				FileFactoryListClass::Get_Instance () != NULL)
		{
			FileFactoryListClass::Get_Instance ()->Set_Search_Start(filename);
		}

	} else if (::strcmpi (extension, ".lsd") == 0) {		
		lsd_filename = filename;
		filename_to_load.Format ("%s.ldd", root_name);
	} else {
		
		//
		//	Dig out the name of the map we'll use with this file
		//
		StringClass map_name(0,true);
		if (Peek_Map_Name (filename, map_name)) {

			char mix_root_name[_MAX_FNAME] = { 0 };
			::_splitpath ((const char *)map_name, NULL, NULL, mix_root_name, NULL);

			//
			//	Build the mix filename from the map name...
			//
			StringClass mix_filename(0, true);
			lsd_filename.Format ("%s.lsd", mix_root_name);
			mix_filename.Format ("%s.mix", mix_root_name);

			//
			//	HACK HACK - Put the level 9 mix file first...
			//
			if (	::lstrcmpi (mix_filename, "M09.mix") == 0 &&
					FileFactoryListClass::Get_Instance () != NULL)
			{
				FileFactoryListClass::Get_Instance ()->Set_Search_Start(mix_filename);
			}

			StringClass thumb_filename(mix_root_name,true);
			thumb_filename+=".thu";
			ThumbnailManagerClass::Add_Thumbnail_Manager(thumb_filename,mix_filename);
		}
	}

	return ;
}

void	SaveGameManager::Load_Game( const char * filename )
{
	WWLOG_PREPARE_TIME_AND_MEMORY("Load_Game");

	WWMEMLOG(MEM_GAMEDATA);
	Debug_Say(( "Load Game %s\n", filename ));
	CurrentGameFilename = filename;

	FileClass * file = _TheFileFactory->Get_File( filename );
#if defined(__vita__)
	if (file == NULL) {
		A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_UNAVAILABLE);
		return;
	}
	if (!file->Open(FileClass::READ)) {
		A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_OPEN_FAILED);
		file->Close();
		_TheFileFactory->Return_File(file);
		return;
	}
#else
	WWASSERT( file );
	file->Open( FileClass::READ );
#endif
	ChunkLoadClass cload(file);
#if defined(__vita__)
	bool level_info_found = false;
	bool level_info_valid = false;
	bool level_data_found = false;
#endif

	WWLOG_INTERMEDIATE("Open file");
	while (cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_LEVEL_INFO:
#if defined(__vita__)
				if (level_info_found || level_data_found) {
					A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_INFO_MISSING);
					break;
				}
				level_info_found = true;
				{
					StringClass loaded_map_filename(0, true);
					WideStringClass loaded_description;
					int loaded_mission_description = 0;
					if (!Read_Player_Save_Level_Info(cload, loaded_map_filename,
						loaded_description, loaded_mission_description)) {
						A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_INFO_MISSING);
						break;
					}
					MapFilename = loaded_map_filename;
					Description = loaded_description;
					MissionDescriptionID = loaded_mission_description;
					level_info_valid = true;
				}
#else
				while (cload.Open_Micro_Chunk()) {
					switch(cload.Cur_Micro_Chunk_ID()) {
						
						READ_MICRO_CHUNK_WWSTRING( cload,	MICROCHUNKID_MAP_FILENAME,			MapFilename );
						READ_MICRO_CHUNK( cload,			MICROCHUNKID_MISSION_DESCRIPTION,	MissionDescriptionID );
						READ_MICRO_CHUNK_WIDESTRING( cload, MICROCHUNKID_DESCRIPTION,			Description );

						default:
							Debug_Say(( "Unrecognized Level Info chunkID\n" ));
							break;
					}
					cload.Close_Micro_Chunk();
				}
#endif


				{
				// Load level specific Defs
				StringClass temp_ddb(MapFilename,true);
				WWASSERT( temp_ddb.Get_Length() > 4 );
				temp_ddb.Erase( MapFilename.Get_Length()-4, 4 );
				temp_ddb	+= ".ddb";
				if (!Load_Definitions(temp_ddb, false)) {
#if defined(__vita__)
					DefinitionMgrClass::Free_Definitions();
					A35_Level_Load_Record_Failure(A35_LOAD_STATIC_SUBSYSTEM_FAILED);
					break;
#endif
				}
				}
				WWLOG_INTERMEDIATE("Load_Definitions");

				// Load the static data
				Load_Level();	
				WWLOG_INTERMEDIATE("Load_Level");
				
				break;
								
			case CHUNKID_LEVEL_DATA:
#if defined(__vita__)
				if (level_data_found || !level_info_valid) {
					A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_SUBSYSTEM_FAILED);
					break;
				}
				level_data_found = true;
#endif
				if (CombatManager::I_Am_Server()) {
#if defined(__vita__)
					if (!SaveLoadSystemClass::Load(cload, false, true)) {
						A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_SUBSYSTEM_FAILED);
					}
#else
					SaveLoadSystemClass::Load( cload, false, true );
#endif
				}
				WWLOG_INTERMEDIATE("Load");
				break;

			default:
				Debug_Say(( "Unrecognized Level chunkID\n" ));
				break;

		}
		cload.Close_Chunk();
	}

#if defined(__vita__)
	if (cload.Has_Error()) A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_SUBSYSTEM_FAILED);
	if (!level_info_found || !level_info_valid) A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_INFO_MISSING);
	if (CombatManager::I_Am_Server() && !level_data_found) {
		A35_Level_Load_Record_Failure(A35_LOAD_DYNAMIC_DATA_MISSING);
	}
#endif
	file->Close();
	_TheFileFactory->Return_File(file);
	WWLOG_INTERMEDIATE("Rest of the stuff");
}


bool	SaveGameManager::Smart_Peek_Description
(
	const char *		filename,
	WideStringClass &	description,
	WideStringClass &	mission_name
)
{
	//
	//	Get the root name and extension from the filename
	//
	char root_name[_MAX_FNAME] = { 0 };
	char extension[_MAX_EXT] = { 0 };
	::_splitpath (filename, NULL, NULL, root_name, extension);

	StringClass filename_to_load(filename,true);

	//
	//	Is this a mix file?
	//
	FileFactoryClass * mix_factory = NULL;
	if (::strcmpi (extension, ".mix") == 0) {		
		
		//
		// Configure a mix file factory for this mix file
		//
		Debug_Say(( "Adding Temp MIX file factory %s\n", filename ));
		if ( FileFactoryListClass::Get_Instance() != NULL ) {
			mix_factory = new MixFileFactoryClass( filename, _TheFileFactory );
			FileFactoryListClass::Get_Instance()->Add_FileFactory( mix_factory, filename );
		}

		//
		//	Build the dynamic data filename from mix file's root name
		//
		filename_to_load.Format ("%s.ldd", root_name);
	}

	//
	//	Peek at the information inside this mix file...
	//
	bool retval = Peek_Description (filename_to_load, description, mission_name);

	//
	//	Remove the temporary mix file factory we added
	//
	if (mix_factory != NULL) {
		FileFactoryListClass::Get_Instance()->Remove_FileFactory(mix_factory);
		delete mix_factory;
		mix_factory = NULL;
	}

	return retval;
}


bool SaveGameManager::Peek_Description
(
	const char *		filename,
	WideStringClass &	description,
	WideStringClass &	mission_name
)
{
	//
	//	Open the file as a chunk
	//
	FileClass * file = _TheFileFactory->Get_File(filename);
	if (file == NULL) return false;
	if (!file->Open(FileClass::READ)) {
		_TheFileFactory->Return_File(file);
		return false;
	}
	ChunkLoadClass cload(file);

	bool retval			= false;
	int mission_name_id	= 0;
	StringClass map_filename(0,true);
	
	#if defined(RENEGADE_VITA_PORT)
	retval = Read_Player_Save_Envelope(cload, map_filename, description, mission_name_id);
	#else
	//
	//	Loop until we've found the header chunk
	//
	while (retval == false && cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_LEVEL_INFO:
				while (cload.Open_Micro_Chunk()) {
					switch(cload.Cur_Micro_Chunk_ID()) {
						
						//
						//	Read the header chunks
						//
						READ_MICRO_CHUNK_WWSTRING( cload,	MICROCHUNKID_MAP_FILENAME,			map_filename );
						READ_MICRO_CHUNK( cload,			MICROCHUNKID_MISSION_DESCRIPTION,	mission_name_id );
						READ_MICRO_CHUNK_WIDESTRING( cload,	MICROCHUNKID_DESCRIPTION,			description );

					}
					cload.Close_Micro_Chunk();
				}
				retval = true;
				break;
		}
		cload.Close_Chunk();
	}
	#endif

	//
	//	Either load the mission name from the translation database
	//	or simply return the map filename
	//
	if (mission_name_id == 0) {
		mission_name.Convert_From ( map_filename );
		WCHAR *extension = ::wcsrchr (mission_name.Peek_Buffer(), static_cast<WCHAR>('.'));
		if (extension != NULL) {
			extension[0] = 0;
		}
	} else {
		mission_name = TRANSLATE(mission_name_id);
	}

	//
	//	Close the file
	//
	file->Close();
	_TheFileFactory->Return_File(file);

	return retval;
}

bool SaveGameManager::Peek_Map_Name( const char * filename, StringClass &map_name )
{
	//
	//	Open the file as a chunk
	//
	FileClass * file = _TheFileFactory->Get_File(filename);
	if (file == NULL) return false;
	if (!file->Open(FileClass::READ)) {
		_TheFileFactory->Return_File(file);
		return false;
	}
	ChunkLoadClass cload(file);

	bool retval = false;
	
	#if defined(RENEGADE_VITA_PORT)
	WideStringClass description;
	int mission_description = 0;
	retval = Read_Player_Save_Envelope(cload, map_name, description, mission_description);
	#else
	//
	//	Loop until we've found the header chunk
	//
	while (retval == false && cload.Open_Chunk()) {
		switch(cload.Cur_Chunk_ID()) {

			case CHUNKID_LEVEL_INFO:
				while (retval == false && cload.Open_Micro_Chunk()) {
					switch(cload.Cur_Micro_Chunk_ID()) {
						
					//
					//	Read the map name string from chunk	
					//
					case MICROCHUNKID_MAP_FILENAME:
						LOAD_MICRO_CHUNK_WWSTRING( cload, map_name );
						retval = true;
						break;
					}
					cload.Close_Micro_Chunk();
				}
				break;
		}
		cload.Close_Chunk();
	}
	#endif

	//
	//	Close the file
	//
	file->Close();
	_TheFileFactory->Return_File(file);

	return retval;
}

/*
**
*/
void	SaveGameManager::Save_Level( void )
{
	Debug_Say(( "Save Level %s\n", MapFilename ));
	Save_Save_Load_System(	MapFilename,	
									&_PhysStaticDataSaveSystem, 
									&_PhysStaticObjectsSaveSystem,
									&_StaticAudioSaveLoadSubsystem,
									&_TheBackgroundMgr,
									&_TheWeatherMgr,
									&_TheMapMgrSaveLoadSubsystem,
									NULL );
}

void	SaveGameManager::Load_Level( void )
{
	Debug_Say(( "Load Level %s\n", MapFilename ));
	Load_Save_Load_System( MapFilename, false, true );	// false = no automatic post load processing (needs to be called explicitly)
}

/*
**
*/
void	SaveGameManager::Save_Definitions( const char * filename )
{
	Debug_Say(( "Save Definitions %s\n", filename ));
	Save_Save_Load_System( filename, &_TheDefinitionMgr, NULL );
}

bool	SaveGameManager::Load_Definitions( const char * filename, bool required_file )
{
	WWMEMLOG(MEM_GAMEDATA);
	Debug_Say(( "Load Definitions %s\n", filename ));
	return Load_Save_Load_System(filename, true, required_file);
}

/*
**
*/
void _cdecl SaveGameManager::Save_Save_Load_System( const char * filename, ... )
{
	FileClass * file = _TheWritingFileFactory->Get_File( filename );
	WWASSERT(file);
	file->Open(FileClass::WRITE);
	ChunkSaveClass csave(file);
	bool save_succeeded = true;

	va_list arg_list;
	va_start( arg_list, filename );
	bool done = false;
	while ( !done ) {
		SaveLoadSubSystemClass * sub_system = va_arg( arg_list, SaveLoadSubSystemClass * );
		if ( sub_system != NULL ) {
			save_succeeded = SaveLoadSystemClass::Save( csave, *sub_system ) && save_succeeded;
		} else {
			done = true;
		}
	}
	va_end (arg_list);

#if defined(RENEGADE_VITA_PORT)
	if (!save_succeeded) {
		file->Abort_Write();
	}
#endif
	file->Close();
	_TheWritingFileFactory->Return_File(file);
}

bool	SaveGameManager::Load_Save_Load_System( const char * filename, bool auto_post_load, bool required_file )
{
	bool load_succeeded = !required_file;
	FileClass * file = _TheFileFactory->Get_File( filename );
	if ( file != NULL ) {
#if defined(__vita__)
		if (!file->Open(FileClass::READ)) {
			if (required_file) A35_Level_Load_Record_Failure(A35_LOAD_STATIC_OPEN_FAILED);
			file->Close();
			_TheFileFactory->Return_File(file);
			return !required_file;
		}
		ChunkLoadClass cload(file);
		load_succeeded = SaveLoadSystemClass::Load(cload, auto_post_load);
		if (!load_succeeded && required_file) {
			A35_Level_Load_Record_Failure(A35_LOAD_STATIC_SUBSYSTEM_FAILED);
		}
#else
		file->Open( FileClass::READ );
		ChunkLoadClass cload(file);
		load_succeeded = SaveLoadSystemClass::Load( cload, auto_post_load );
#endif
		file->Close();
		_TheFileFactory->Return_File(file);
	} else {
#if defined(__vita__)
		if (required_file) A35_Level_Load_Record_Failure(A35_LOAD_STATIC_UNAVAILABLE);
#endif
		Debug_Say(( "Failed to load file %s\n", filename ));
//		WWASSERT( file );
	}
	return load_succeeded;
}
