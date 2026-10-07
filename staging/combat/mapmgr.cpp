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
 *                     $Archive:: /Commando/Code/Combat/mapmgr.cpp          $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 1/31/02 1:48p                                               $*
 *                                                                                             *
 *                    $Revision:: 11                                                          $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#include "mapmgr.h"
#include "texture.h"
#include "assetmgr.h"
#include "saveload.h"

//#define FORCE_DISABLE_VTOL  // remove this to allow VTOL's on maps that allow VTOLs


///////////////////////////////////////////////////////////////////////
// Global singleton instance
///////////////////////////////////////////////////////////////////////
MapMgrClass _TheMapMgrSaveLoadSubsystem;


////////////////////////////////////////////////////////////////
//	Local constants
////////////////////////////////////////////////////////////////
enum
{
	CHUNKID_VARIABLES		= 0x07020522,
	CHUNKID_SHROUD
};

enum
{
	VARID_TEXTURE_NAME		= 0x01,
	VARID_CENTER_POINT,
	VARID_SCALE,
	VARID_MAP_TITLE_ID,
	VARID_IS_PLAYER_MARKDER_VISIBLE,
	VARID_ENABLE_VTOL
};


////////////////////////////////////////////////////////////////
//	Static member intialization
////////////////////////////////////////////////////////////////
bool				MapMgrClass::IsPlayerMarkerVisible = true;
int				MapMgrClass::MapTitleID = 0;
StringClass		MapMgrClass::MapTextureName;
Vector2			MapMgrClass::MapCenterPoint (0, 0);
Vector2			MapMgrClass::MapScale (0, 0);
Vector2			MapMgrClass::MapSize (0, 0);
uint32			MapMgrClass::CloudVector[CLOUD_VECTOR_SIZE] = { 0 };
bool				MapMgrClass::EnableVTOL = false;

////////////////////////////////////////////////////////////////
//
//	Get_Map_Texture_Filename
//
////////////////////////////////////////////////////////////////
void
MapMgrClass::Get_Map_Texture_Filename (StringClass &filename)
{
	//
	//	Strip off the path if necessary
	//
	filename = MapTextureName;
	const char *dir_delimiter		= ::strrchr (MapTextureName, '\\');
	if (dir_delimiter != NULL) {
		filename = (dir_delimiter + 1);
	}

	return ;
}


////////////////////////////////////////////////////////////////
//
//	Set_Map_Texture
//
////////////////////////////////////////////////////////////////
void
MapMgrClass::Set_Map_Texture (const char *filename)
{
	//
	//	Strip off the path if necessary
	//
	StringClass filename_only	= filename;
	const char *dir_delimiter		= ::strrchr (filename, '\\');
	if (dir_delimiter != NULL) {
		filename_only = (dir_delimiter + 1);
	}

	//
	//	Load the texture
	//
	TextureClass *texture = WW3DAssetManager::Get_Instance ()->Get_Texture (filename_only, TextureClass::MIP_LEVELS_1);
	if (texture != NULL) {

#if defined(RENEGADE_VITA_PORT)
		// The native texture provider is lazy. MapSize must be established
		// before original Combat clears explored cloud cells on this map.
		texture->Init();
#endif

		//
		//	Get the dimensions of the texture
		//
//		SurfaceClass::SurfaceDescription surface_desc;
//		texture->Get_Level_Description (surface_desc);
//		MapSize.X = surface_desc.Width;
//		MapSize.Y = surface_desc.Height;
		MapSize.X = texture->Get_Width();
		MapSize.Y = texture->Get_Height();

		//
		//	Release our hold on the texture
		//
		REF_PTR_RELEASE (texture);
	}

	//
	//	Cache the texture name
	//
	MapTextureName = filename;
	return ;
}


////////////////////////////////////////////////////////////////
//
//	Save
//
////////////////////////////////////////////////////////////////
bool
MapMgrClass::Save (ChunkSaveClass &csave)
{
	//
	//	Write the variables
	//
	csave.Begin_Chunk (CHUNKID_VARIABLES);
		WRITE_MICRO_CHUNK_WWSTRING (csave, VARID_TEXTURE_NAME,	MapTextureName);
		WRITE_MICRO_CHUNK (csave, VARID_CENTER_POINT,				MapCenterPoint);
		WRITE_MICRO_CHUNK (csave, VARID_SCALE,							MapScale);
		WRITE_MICRO_CHUNK (csave, VARID_MAP_TITLE_ID,				MapTitleID);
		WRITE_MICRO_CHUNK (csave, VARID_IS_PLAYER_MARKDER_VISIBLE, IsPlayerMarkerVisible);		
		WRITE_MICRO_CHUNK (csave, VARID_ENABLE_VTOL,					EnableVTOL);
	csave.End_Chunk ();

	//
	//	Write the current shroud
	//
	csave.Begin_Chunk (CHUNKID_SHROUD);
		int size = CLOUD_VECTOR_SIZE;
		csave.Write (&size, sizeof (size));
		csave.Write (CloudVector, sizeof (CloudVector));
	csave.End_Chunk ();

	return true;
}


////////////////////////////////////////////////////////////////
//
//	Load
//
////////////////////////////////////////////////////////////////
bool
MapMgrClass::Load (ChunkLoadClass &cload)
{
	bool loaded_variables = false;
	bool loaded_shroud = false;
	bool loaded = true;

	while (cload.Open_Chunk ()) {
		switch (cload.Cur_Chunk_ID ()) {
			
			//
			//	Load all the variables from this chunk
			//
			case CHUNKID_VARIABLES:
				if (loaded_variables) {
					loaded = false;
				} else {
					loaded_variables = true;
					loaded = Load_Variables (cload) && loaded;
				}
				break;

			case CHUNKID_SHROUD:
			{
				if (loaded_shroud) {
					loaded = false;
					break;
				}
				loaded_shroud = true;
				//
				//	Read the shroud vector from its chunk
				//
				int size = 0;
				loaded = cload.Read (&size, sizeof (size)) == sizeof (size) && loaded;
				if (size == CLOUD_VECTOR_SIZE) {
					loaded = cload.Read (CloudVector, sizeof (CloudVector)) == sizeof (CloudVector) && loaded;
				} else {
					loaded = false;
				}
				break;
			}
		}

		cload.Close_Chunk ();
	}

	return loaded && loaded_variables && loaded_shroud;
}


////////////////////////////////////////////////////////////////
//
//	Load_Variables
//
////////////////////////////////////////////////////////////////
bool
MapMgrClass::Load_Variables (ChunkLoadClass &cload)
{
	uint32 loaded_values = 0U;
	bool loaded = true;
	#define LOAD_REQUIRED_MAP_VALUE(id, value, bit) \
		case (id): { \
			const uint32 value_bit = 1U << (bit); \
			if ((loaded_values & value_bit) != 0U || \
				cload.Cur_Micro_Chunk_Length() != sizeof(value)) { \
				loaded = false; \
			} else { \
				loaded_values |= value_bit; \
				loaded = cload.Read(&(value), sizeof(value)) == sizeof(value) && loaded; \
			} \
			break; \
		}
	while (cload.Open_Micro_Chunk ()) {
		switch (cload.Cur_Micro_Chunk_ID ()) {

			case VARID_TEXTURE_NAME:
			{
				if ((loaded_values & 1U) != 0U) {
					loaded = false;
				} else {
					loaded_values |= 1U;
					const uint32 length = cload.Cur_Micro_Chunk_Length();
					loaded = cload.Read(MapTextureName.Get_Buffer(length), length) == length && loaded;
				}
			}
			break;
			LOAD_REQUIRED_MAP_VALUE (VARID_CENTER_POINT, MapCenterPoint, 1);
			LOAD_REQUIRED_MAP_VALUE (VARID_SCALE, MapScale, 2);
			LOAD_REQUIRED_MAP_VALUE (VARID_MAP_TITLE_ID, MapTitleID, 3);
			LOAD_REQUIRED_MAP_VALUE (VARID_IS_PLAYER_MARKDER_VISIBLE, IsPlayerMarkerVisible, 4);
			LOAD_REQUIRED_MAP_VALUE (VARID_ENABLE_VTOL, EnableVTOL, 5);
		}

		cload.Close_Micro_Chunk ();
	}

	//
	// (gth) VTOL DISABLE!  We are not going to let Modders make VTOL aircraft
	// until we release some levels with them.  FORCE the EnableVTOL flag to
	// false for now.  When we release some maps with orcas, then we patch
	// the game with this line of code removed and the mod people can make them 
	// too.
	//
#ifdef FORCE_DISABLE_VTOL
	EnableVTOL = false;
#endif

	#undef LOAD_REQUIRED_MAP_VALUE
	const bool complete = loaded && loaded_values == ((1U << 6) - 1U);
	if (complete) {
		SaveLoadSystemClass::Register_Post_Load_Callback (this);
	}
	return complete;
}


///////////////////////////////////////////////////////////////////////
//
//	On_Post_Load
//
///////////////////////////////////////////////////////////////////////
void
MapMgrClass::On_Post_Load (void)
{
	Set_Map_Texture (MapTextureName);
	return ;
}


///////////////////////////////////////////////////////////////////////
//
//	Clear_Cloud_Cells
//
///////////////////////////////////////////////////////////////////////
void
MapMgrClass::Clear_Cloud_Cells (const Vector3 &pos, int pixel_radius)
{
	if (MapSize.X <= 0 || MapSize.Y <= 0) {
		return ;
	}

	//
	//	Calculate where (in map pixels) this position lies
	//
	float map_x_pos	= MapCenterPoint.X + (pos.X * MapScale.X);
	float map_y_pos	= MapCenterPoint.Y - (pos.Y * MapScale.Y);

	//
	//	Determine what the min and max cells this region includes
	//
	int min_cell_x	= int(((map_x_pos - pixel_radius) / MapSize.X) * CLOUD_WIDTH);
	int min_cell_y	= int(((map_y_pos - pixel_radius) / MapSize.Y) * CLOUD_HEIGHT);

	int max_cell_x	= int(((map_x_pos + pixel_radius) / MapSize.X) * CLOUD_WIDTH);
	int max_cell_y	= int(((map_y_pos + pixel_radius) / MapSize.Y) * CLOUD_HEIGHT);

	//
	//	Clear all the cells in this region
	//
	for (int cell_x = min_cell_x; cell_x <= max_cell_x; cell_x ++) {
		for (int cell_y = min_cell_y; cell_y <= max_cell_y; cell_y ++) {
			Clear_Cloud_Cell (cell_x, cell_y);
		}
	}

	return ;
}
