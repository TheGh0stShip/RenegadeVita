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
 *                 Project Name : LevelEdit                                                    *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/WWAudio/AudioSaveLoad.cpp                    $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 9/08/01 10:41a                                              $*
 *                                                                                             *
 *                    $Revision:: 7                                                           $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "always.h"
#include "audiosaveload.h"
#include "persist.h"
#include "persistfactory.h"
#include "definition.h"
#include "soundchunkids.h"
#include "chunkio.h"
#include "SoundScene.h"
#include "wwmemlog.h"
#include "a31_audio_lifecycle.h"


///////////////////////////////////////////////////////////////////////
// Global singleton instance
///////////////////////////////////////////////////////////////////////
StaticAudioSaveLoadClass _StaticAudioSaveLoadSubsystem;
DynamicAudioSaveLoadClass _DynamicAudioSaveLoadSubsystem;


///////////////////////////////////////////////////////////////////////
//	Constants
///////////////////////////////////////////////////////////////////////
enum
{
	CHUNKID_STATIC_SCENE		= 0x10291220,
	CHUNKID_DYNAMIC_SCENE,
	CHUNKID_DYNAMIC_VARIABLES
};


enum
{
	VARID_INCLUDE_FILE		= 0x01,
	VARID_CAMERA_TM,
	VARID_BACK_COLOR,
	VARID_LOGICAL_LISTENER_GLOBAL_SCALE,
	VARID_BACKGROUND_MUSIC_NAME
};


///////////////////////////////////////////////////////////////////////
//
//	Chunk_ID
//
///////////////////////////////////////////////////////////////////////
uint32
StaticAudioSaveLoadClass::Chunk_ID (void) const
{
	return CHUNKID_STATIC_SAVELOAD;
}


///////////////////////////////////////////////////////////////////////
//
//	Contains_Data
//
///////////////////////////////////////////////////////////////////////
bool
StaticAudioSaveLoadClass::Contains_Data (void) const
{
	return true;
}


///////////////////////////////////////////////////////////////////////
//
//	Save
//
///////////////////////////////////////////////////////////////////////
bool
StaticAudioSaveLoadClass::Save (ChunkSaveClass &csave)
{
	WWMEMLOG(MEM_SOUND);

	bool retval = true;

	//
	//	Save the static sounds
	//
	SoundSceneClass *scene = WWAudioClass::Get_Instance ()->Get_Sound_Scene ();
	if (scene != NULL) {
		csave.Begin_Chunk (CHUNKID_STATIC_SCENE);
			retval &= scene->Save_Static (csave);
		csave.End_Chunk ();
	}

	return retval && !csave.Has_Error();
}


///////////////////////////////////////////////////////////////////////
//
//	Load
//
///////////////////////////////////////////////////////////////////////
bool
StaticAudioSaveLoadClass::Load (ChunkLoadClass &cload)
{
	WWMEMLOG(MEM_SOUND);

	bool retval = true;
	bool scene_seen = false;
	while (cload.Open_Chunk ()) {
		switch (cload.Cur_Chunk_ID ()) {

			//
			//	Load the static scene information
			//
			case CHUNKID_STATIC_SCENE:
			{
				if (scene_seen) {
					retval = false;
					break;
				}
				scene_seen = true;
				A31_Audio_Save_Load_Breadcrumb("static-audio SaveLoad entry");
				SoundSceneClass *scene = WWAudioClass::Get_Instance ()->Get_Sound_Scene ();
				if (scene != NULL) {
					retval &= scene->Load_Static (cload);
				} else retval = false;
			}
			break;
		}

		cload.Close_Chunk ();
	}

	return retval && !cload.Has_Error();
}


//*******************************************************************//
//*
//*	Start of DynamicAudioSaveLoadClass
//*
//*******************************************************************//



///////////////////////////////////////////////////////////////////////
//
//	Chunk_ID
//
///////////////////////////////////////////////////////////////////////
uint32
DynamicAudioSaveLoadClass::Chunk_ID (void) const
{
	return CHUNKID_DYNAMIC_SAVELOAD;
}


///////////////////////////////////////////////////////////////////////
//
//	Contains_Data
//
///////////////////////////////////////////////////////////////////////
bool
DynamicAudioSaveLoadClass::Contains_Data (void) const
{
	return true;
}


///////////////////////////////////////////////////////////////////////
//
//	Save
//
///////////////////////////////////////////////////////////////////////
bool
DynamicAudioSaveLoadClass::Save (ChunkSaveClass &csave)
{
	bool retval = true;

	//
	//	Save the static sounds
	//
	SoundSceneClass *scene = WWAudioClass::Get_Instance ()->Get_Sound_Scene ();
	if (scene != NULL) {
		
		csave.Begin_Chunk (CHUNKID_DYNAMIC_VARIABLES);
			float global_scale	= LogicalListenerClass::Get_Global_Scale ();
			StringClass filename = WWAudioClass::Get_Instance ()->Get_Background_Music_Name ();

			WRITE_MICRO_CHUNK				(csave, VARID_LOGICAL_LISTENER_GLOBAL_SCALE, global_scale);
			WRITE_MICRO_CHUNK_WWSTRING (csave, VARID_BACKGROUND_MUSIC_NAME,			filename);			
		csave.End_Chunk ();
		
		csave.Begin_Chunk (CHUNKID_DYNAMIC_SCENE);
			retval &= scene->Save_Dynamic (csave);
		csave.End_Chunk ();
	}

	return retval && !csave.Has_Error();
}


///////////////////////////////////////////////////////////////////////
//
//	Load
//
///////////////////////////////////////////////////////////////////////
bool
DynamicAudioSaveLoadClass::Load (ChunkLoadClass &cload)
{
	bool retval = true;
	bool loaded_variables = false;
	bool loaded_scene = false;
	bool scale_seen = false;
	bool music_seen = false;
	float loaded_global_scale = 1.0F;
	StringClass loaded_music_name;
	while (cload.Open_Chunk ()) {
		switch (cload.Cur_Chunk_ID ()) {

			case CHUNKID_DYNAMIC_VARIABLES:
			{
				if (loaded_variables) {
					retval = false;
					break;
				}
				loaded_variables = true;
				//
				//	Read all the variables from their micro-chunks
				//
				while (cload.Open_Micro_Chunk ()) {
					switch (cload.Cur_Micro_Chunk_ID ()) {
						
						//
						//	Load the global scale for logical listeners
						//
						case VARID_LOGICAL_LISTENER_GLOBAL_SCALE:
						{
							if (scale_seen || cload.Cur_Micro_Chunk_Length() != sizeof(loaded_global_scale) ||
								cload.Read(&loaded_global_scale, sizeof(loaded_global_scale)) != sizeof(loaded_global_scale)) retval = false;
							scale_seen = true;
							break;
						}						

						//
						//	Load the background music name
						//
						case VARID_BACKGROUND_MUSIC_NAME:
						{
							if (music_seen || cload.Read(loaded_music_name.Get_Buffer(cload.Cur_Micro_Chunk_Length()),
								cload.Cur_Micro_Chunk_Length()) != cload.Cur_Micro_Chunk_Length()) retval = false;
							music_seen = true;
							break;
						}						

					}

					cload.Close_Micro_Chunk ();
				}
			}
			break;

			//
			//	Load the static scene information
			//
			case CHUNKID_DYNAMIC_SCENE:
			{
				if (loaded_scene) {
					retval = false;
					break;
				}
				loaded_scene = true;
				SoundSceneClass *scene = WWAudioClass::Get_Instance ()->Get_Sound_Scene ();
				if (scene != NULL) retval &= scene->Load_Dynamic (cload);
				else retval = false;
			}
			break;
		}

		cload.Close_Chunk ();
	}

	// The writer emits either both children when a sound scene exists or an
	// intentionally empty subsystem when it does not.
	retval = retval && loaded_variables == loaded_scene && !cload.Has_Error();
	if (loaded_variables) retval = retval && scale_seen && music_seen;
	if (retval && loaded_variables) {
		LogicalListenerClass::Set_Global_Scale (loaded_global_scale);
		WWAudioClass::Get_Instance ()->Set_Background_Music (loaded_music_name);
	}
	return retval;
}
