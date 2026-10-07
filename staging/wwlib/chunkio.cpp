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

/* $Header: /Commando/Code/wwlib/chunkio.cpp 12    3/14/02 1:25p Greg_h $ */
/*********************************************************************************************** 
 ***                            Confidential - Westwood Studios                              *** 
 *********************************************************************************************** 
 *                                                                                             * 
 *                 Project Name : Tiberian Sun / Commando / G Library                          * 
 *                                                                                             * 
 *                     $Archive:: /Commando/Code/wwlib/chunkio.cpp                            $* 
 *                                                                                             * 
 *                      $Author:: Greg_h                                                      $* 
 *                                                                                             * 
 *                     $Modtime:: 3/04/02 4:00p                                               $* 
 *                                                                                             * 
 *                    $Revision:: 12                                                          $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 *   ChunkSaveClass::ChunkSaveClass -- Constructor                                             * 
 *   ChunkSaveClass::Begin_Chunk -- Begin a new chunk in the file                              * 
 *   ChunkSaveClass::End_Chunk -- Close a chunk, computes the size and adds to the header      * 
 *   ChunkSaveClass::Begin_Micro_Chunk -- begins a new "micro-chunk"                           *
 *   ChunkSaveClass::End_Micro_Chunk -- close a micro-chunk                                    *
 *   ChunkSaveClass::Write -- Write data into the current chunk                                * 
 *   ChunkSaveClass::Write -- write an IOVector2Struct                                         *
 *   ChunkSaveClass::Write -- write an IOVector3Struct                                         *
 *   ChunkSaveClass::Write -- write an IOVector4Struct                                         *
 *   ChunkSaveClass::Write -- write an IOQuaternionStruct                                      *
 *   ChunkSaveClass::Cur_Chunk_Depth -- returns the current chunk recursion depth (debugging)  * 
 *   ChunkLoadClass::ChunkLoadClass -- Constructor                                             * 
 *   ChunkLoadClass::Open_Chunk -- Open a chunk in the file, reads in the chunk header         * 
 *   ChunkLoadClass::Peek_Next_Chunk -- sneak peek into the next chunk that will be opened     *
 *   ChunkLoadClass::Close_Chunk -- Close a chunk, seeks to the end if needed                  * 
 *   ChunkLoadClass::Cur_Chunk_ID -- Returns the ID of the current chunk                       * 
 *   ChunkLoadClass::Cur_Chunk_Length -- Returns the current length of the current chunk       * 
 *   ChunkLoadClass::Cur_Chunk_Depth -- returns the current chunk recursion depth              * 
 *   ChunkLoadClass::Contains_Chunks -- Test whether the current chunk contains chunks (or dat *
 *   ChunkLoadClass::Open_Micro_Chunk -- reads in a micro-chunk header                         *
 *   ChunkLoadClass::Close_Micro_Chunk -- closes a micro-chunk                                 *
 *   ChunkLoadClass::Cur_Micro_Chunk_ID -- returns the ID of the current micro-chunk (asserts  *
 *   ChunkLoadClass::Cur_Micro_Chunk_Length -- returns the size of the current micro chunk     *
 *   ChunkLoadClass::Read -- Read data from the file                                           * 
 *   ChunkLoadClass::Read -- read an IOVector2Struct                                           *
 *   ChunkLoadClass::Read -- read an IOVector3Struct                                           *
 *   ChunkLoadClass::Read -- read an IOVector4Struct                                           *
 *   ChunkLoadClass::Read -- read an IOQuaternionStruct                                        *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */

#include "chunkio.h"
#include <string.h>
#include <assert.h>
#include "wwdebug.h"


/*********************************************************************************************** 
 * ChunkSaveClass::ChunkSaveClass -- Constructor                                               * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *  file - pointer to a FileClass object to write to														  * 
 * 																														  * 
 * OUTPUT:																												  * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
ChunkSaveClass::ChunkSaveClass(FileClass * file) :
	File(file),
	StackIndex(0),
	InMicroChunk(false),
	MicroChunkPosition(0),
	Error(false)
{
	memset(PositionStack,0,sizeof(PositionStack));
	memset(HeaderStack,0,sizeof(HeaderStack));
	memset(&MCHeader,0,sizeof(MCHeader));
}


/*********************************************************************************************** 
 * ChunkSaveClass::Begin_Chunk -- Begin a new chunk in the file                                * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *  id - id of the chunk																							  * 
 * 																														  * 
 * OUTPUT:																												  * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
bool ChunkSaveClass::Begin_Chunk(uint32 id)
{
	ChunkHeader	chunkh;
	int 			filepos;

	// If we have a parent chunk, set its 'Contains_Chunks' flag
	if (StackIndex > 0) {
		HeaderStack[StackIndex-1].Set_Sub_Chunk_Flag(true);
	}
	
	// Save the current file position and chunk header
	// for the call to End_Chunk.
	chunkh.Set_Type(id);
	chunkh.Set_Size(0);
	filepos = File->Seek(0); 
	
	PositionStack[StackIndex] = filepos;
	HeaderStack[StackIndex] = chunkh;	
	StackIndex++;
	
	// write a temporary chunk header (size = 0)
	if (File->Write(&chunkh,sizeof(chunkh)) != sizeof(chunkh)) {
		Error = true;
		return false;
	}
	return true;
}


/*********************************************************************************************** 
 * ChunkSaveClass::End_Chunk -- Close a chunk, computes the size and adds to the header        * 
 *  																														  * 
 * INPUT:																												  * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
bool ChunkSaveClass::End_Chunk(void)
{
	// If the user didn't close his micro chunks bad things are gonna happen
	assert(!InMicroChunk);

	// Save the current position
	int curpos = File->Seek(0);

	// Pop the position and chunk header off the stacks
	StackIndex--;
	int chunkpos = PositionStack[StackIndex];
	ChunkHeader chunkh = HeaderStack[StackIndex];
	
	// write the completed header
	File->Seek(chunkpos,SEEK_SET);
	if (File->Write(&chunkh,sizeof(chunkh)) != sizeof(chunkh)) {
		Error = true;
		return false;
	}

	// Add the total bytes written to any encompasing chunk
	if (StackIndex != 0) {
		HeaderStack[StackIndex-1].Add_Size(chunkh.Get_Size() + sizeof(chunkh));
	}
	
	// Go back to the end of the file
	File->Seek(curpos,SEEK_SET);

	return !Error;
}


/***********************************************************************************************
 * ChunkSaveClass::Begin_Micro_Chunk -- begins a new "micro-chunk"                             *
 *                                                                                             *
 * Micro chunks are used to wrap individual variables.  They aren't hierarchical so if you     *
 * attempt to open a micro chunk while already in one, an assert will occur.                   *
 *                                                                                             *
 * INPUT:                                                                                      *
 * id - 8bit id                                                                                *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 * id is asserted to be between 0 and 255                                                      *
 * cannot nest micro chunks so it asserts that you are currently not in another micro-chunk    *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   9/3/99     GTH : Created.                                                                 *
 *=============================================================================================*/
bool ChunkSaveClass::Begin_Micro_Chunk(uint32 id)
{
	assert(id < 256);
	assert(!InMicroChunk);
	
	// Save the current file position and chunk header
	// for the call to End_Micro_Chunk.
	MCHeader.Set_Type(id);
	MCHeader.Set_Size(0);
	MicroChunkPosition = File->Seek(0); 
	
	// Write a temporary chunk header 
	// NOTE: I'm calling the ChunkSaveClass::Write method so that the bytes for
	// this header are tracked in the wrapping chunk.  This is because micro-chunks
	// are simply data inside the normal chunks...
	if (Write(&MCHeader,sizeof(MCHeader)) != sizeof(MCHeader)) {
		return false;
	}

	InMicroChunk = true;
	return true;
}


/***********************************************************************************************
 * ChunkSaveClass::End_Micro_Chunk -- close a micro-chunk                                      *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   9/3/99     GTH : Created.                                                                 *
 *=============================================================================================*/
bool ChunkSaveClass::End_Micro_Chunk(void)
{
	assert(InMicroChunk);
	
	// Save the current position
	int curpos = File->Seek(0);

	// Seek back and write the micro chunk header
	File->Seek(MicroChunkPosition,SEEK_SET);
	if (File->Write(&MCHeader,sizeof(MCHeader)) != sizeof(MCHeader)) {
		Error = true;
		return false;
	}

	// Go back to the end of the file
	File->Seek(curpos,SEEK_SET);
	InMicroChunk = false;
	return !Error;
}

/*********************************************************************************************** 
 * ChunkSaveClass::Write -- Write data into the current chunk                                  * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
uint32 ChunkSaveClass::Write(const void * buf, uint32 nbytes)
{
	// If this assert hits, you mixed data and chunks within the same chunk NO NO!
	assert(HeaderStack[StackIndex-1].Get_Sub_Chunk_Flag() == 0);
	
	// If this assert hits, you didnt open any chunks yet
	assert(StackIndex > 0);

	// write the bytes into the file
	if (File->Write(buf,nbytes) != (int)nbytes) {
		Error = true;
		return 0;
	}

	// track them in the wrapping chunk
	HeaderStack[StackIndex-1].Add_Size(nbytes);
	
	// track them if you are using a micro-chunk too.
	if (InMicroChunk) {
		assert(MCHeader.Get_Size() < 255 - nbytes);	// micro chunks can only be 255 bytes
		MCHeader.Add_Size(nbytes);
	}

	return nbytes;
}


/***********************************************************************************************
 * ChunkSaveClass::Write -- write an IOVector2Struct                                           *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkSaveClass::Write(const IOVector2Struct & v)
{
	return Write(&v,sizeof(v));
}


/***********************************************************************************************
 * ChunkSaveClass::Write -- write an IOVector3Struct                                           *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkSaveClass::Write(const IOVector3Struct & v)
{	
	return Write(&v,sizeof(v));
}


/***********************************************************************************************
 * ChunkSaveClass::Write -- write an IOVector4Struct                                           *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkSaveClass::Write(const IOVector4Struct & v)
{
	return Write(&v,sizeof(v));
}
	
/***********************************************************************************************
 * ChunkSaveClass::Write -- write an IOQuaternionStruct                                        *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkSaveClass::Write(const IOQuaternionStruct & q)
{
	return Write(&q,sizeof(q));
}

/*********************************************************************************************** 
 * ChunkSaveClass::Cur_Chunk_Depth -- returns the current chunk recursion depth (debugging)    * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
int ChunkSaveClass::Cur_Chunk_Depth(void)
{
	return StackIndex;
}


/*********************************************************************************************** 
 * ChunkLoadClass::ChunkLoadClass -- Constructor                                               * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
ChunkLoadClass::ChunkLoadClass(FileClass * file) :
	File(file),
	StackIndex(0),
	InMicroChunk(false),
	MicroChunkPosition(0),
	Error(false)
{
	memset(PositionStack,0,sizeof(PositionStack));
	memset(HeaderStack,0,sizeof(HeaderStack));
	memset(&MCHeader,0,sizeof(MCHeader));
}


/*********************************************************************************************** 
 * ChunkLoadClass::Open_Chunk -- Open a chunk in the file, reads in the chunk header           * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
bool ChunkLoadClass::Open_Chunk()
{
	if (Error) return false;
	if (InMicroChunk) {
		Error = true;
		return false;
	}
	if (File == NULL) {
		WWDEBUG_ERROR(("ChunkLoadClass::Open_Chunk null file pointer depth=%d\n", StackIndex));
		Error = true;
		return false;
	}
	if (StackIndex >= MAX_STACK_DEPTH - 1) {
		Error = true;
		return false;
	}

	uint32 available = 0U;
	if (StackIndex > 0) {
		const uint32 parent_size = HeaderStack[StackIndex-1].Get_Size();
		const uint32 parent_position = PositionStack[StackIndex-1];
		if (parent_position > parent_size) {
			Error = true;
			return false;
		}
		available = parent_size - parent_position;
		if (available == 0U) return false;
		if (available < sizeof(ChunkHeader)) {
			Error = true;
			return false;
		}
	} else {
		// Original semantics: an unopened file simply has no chunks (its Read
		// returned 0). Tell/Size would seek a closed handle.
		if (!File->Is_Open()) return false;
		const int file_position = File->Tell();
		const int file_size = File->Size();
		if (file_position < 0 || file_size < file_position) {
			Error = true;
			return false;
		}
		available = static_cast<uint32>(file_size - file_position);
		if (available == 0U) return false;
		if (available < sizeof(ChunkHeader)) {
			Error = true;
			return false;
		}
	}

	WWDEBUG_SAY(("ChunkLoadClass::Open_Chunk pre-read id/len depth=%d parent-depth=%d remaining=%u\n",
		StackIndex + 1, StackIndex,
		(StackIndex > 0) ? (HeaderStack[StackIndex-1].Get_Size() - PositionStack[StackIndex-1]) : 0U ));

	// read the chunk header
	if (File->Read(&HeaderStack[StackIndex],sizeof(ChunkHeader)) != sizeof(ChunkHeader)) {
		WWDEBUG_WARNING(("ChunkLoadClass::Open_Chunk short header read at depth=%d expected=%u\n",
			StackIndex + 1, (uint32)sizeof(ChunkHeader) ));
		Error = true;
		return false;
	}
	if (HeaderStack[StackIndex].Get_Size() > available - sizeof(ChunkHeader)) {
		Error = true;
		return false;
	}
	WWDEBUG_SAY(("ChunkLoadClass::Open_Chunk opened id=%u length=%u has_children=%u depth=%d\n",
		HeaderStack[StackIndex].Get_Type(),
		HeaderStack[StackIndex].Get_Size(),
		(HeaderStack[StackIndex].Get_Sub_Chunk_Flag() != 0U),
		StackIndex + 1 ));

	PositionStack[StackIndex] = 0;
	StackIndex++;
	return true;
}


/***********************************************************************************************
 * ChunkLoadClass::Peek_Next_Chunk -- sneak peek into the next chunk that will be opened       *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   3/4/2002   gth : Created.                                                                 *
 *=============================================================================================*/
bool ChunkLoadClass::Peek_Next_Chunk(uint32 * set_id,uint32 * set_size)
{
	if (Error || InMicroChunk || File == NULL || StackIndex >= MAX_STACK_DEPTH - 1) {
		Error = true;
		return false;
	}
	uint32 available = 0U;
	if (StackIndex > 0) {
		const uint32 parent_size = HeaderStack[StackIndex-1].Get_Size();
		const uint32 parent_position = PositionStack[StackIndex-1];
		if (parent_position > parent_size) { Error = true; return false; }
		available = parent_size - parent_position;
	} else {
		if (!File->Is_Open()) return false;
		const int file_position = File->Tell();
		const int file_size = File->Size();
		if (file_position < 0 || file_size < file_position) { Error = true; return false; }
		available = static_cast<uint32>(file_size - file_position);
	}
	if (available == 0U) return false;
	// A peek is speculative (original semantics never set Error here): a
	// header that cannot fit the remaining bytes is "no chunk", not a fault.
	// Open_Chunk still rejects the same structure if a caller opens it.
	if (available < sizeof(ChunkHeader)) return false;

	// peek at the next chunk header, return false if the read fails
	ChunkHeader temp_header;
	if (File->Read(&temp_header,sizeof(ChunkHeader)) != sizeof(ChunkHeader)) {
		Error = true;
		return false;
	}

	const int header_end = File->Tell();
	if (header_end < static_cast<int>(sizeof(ChunkHeader)) ||
		File->Seek(-static_cast<int>(sizeof(ChunkHeader)),SEEK_CUR) !=
			header_end - static_cast<int>(sizeof(ChunkHeader))) {
		Error = true;
		return false;
	}
	if (temp_header.Get_Size() > available - sizeof(ChunkHeader)) return false;
	
	if (set_id != NULL) {
		*set_id = temp_header.Get_Type();
	}
	if (set_size != NULL) {
		*set_size = temp_header.Get_Size();
	}

	return true;
}

/*********************************************************************************************** 
 * ChunkLoadClass::Close_Chunk -- Close a chunk, seeks to the end if needed                    * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
bool ChunkLoadClass::Close_Chunk()
{
	if (InMicroChunk || StackIndex <= 0 || File == NULL) {
		Error = true;
		return false;
	}
	
	const uint32 csize = HeaderStack[StackIndex-1].Get_Size();
	const uint32 pos = PositionStack[StackIndex-1];
	
	if (pos > csize) {
		Error = true;
	} else if (pos < csize && !Error && Seek(csize - pos) != csize - pos) {
		Error = true;
	}

	StackIndex--;
	if (StackIndex > 0) {
		const uint32 parent_size = HeaderStack[StackIndex - 1].Get_Size();
		const uint32 parent_position = PositionStack[StackIndex - 1];
		const uint32 child_total = csize + static_cast<uint32>(sizeof(ChunkHeader));
		if (child_total < csize || parent_position > parent_size ||
			child_total > parent_size - parent_position) {
			Error = true;
		} else {
			PositionStack[StackIndex - 1] += child_total;
		}
	}

	return !Error;
}


/*********************************************************************************************** 
 * ChunkLoadClass::Cur_Chunk_ID -- Returns the ID of the current chunk                         * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
uint32 ChunkLoadClass::Cur_Chunk_ID()
{
	assert(StackIndex >= 1);
	return HeaderStack[StackIndex-1].Get_Type();
}


/*********************************************************************************************** 
 * ChunkLoadClass::Cur_Chunk_Length -- Returns the current length of the current chunk         * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
uint32 ChunkLoadClass::Cur_Chunk_Length()
{
	assert(StackIndex >= 1);
	return HeaderStack[StackIndex-1].Get_Size();
}


/*********************************************************************************************** 
 * ChunkLoadClass::Cur_Chunk_Depth -- returns the current chunk recursion depth                * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
int ChunkLoadClass::Cur_Chunk_Depth()
{
	return StackIndex;
}


/***********************************************************************************************
 * ChunkLoadClass::Contains_Chunks -- Test whether the current chunk contains chunks (or data) *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   9/24/99    GTH : Created.                                                                 *
 *=============================================================================================*/
int ChunkLoadClass::Contains_Chunks()
{
	return HeaderStack[StackIndex-1].Get_Sub_Chunk_Flag();
}

/***********************************************************************************************
 * ChunkLoadClass::Open_Micro_Chunk -- reads in a micro-chunk header                           *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   9/3/99     GTH : Created.                                                                 *
 *=============================================================================================*/
bool ChunkLoadClass::Open_Micro_Chunk()
{
	if (Error || InMicroChunk || StackIndex <= 0) {
		Error = true;
		return false;
	}
	const uint32 chunk_size = HeaderStack[StackIndex-1].Get_Size();
	const uint32 chunk_position = PositionStack[StackIndex-1];
	if (chunk_position > chunk_size) { Error = true; return false; }
	const uint32 available = chunk_size - chunk_position;
	if (available == 0U) return false;
	if (available < sizeof(MicroChunkHeader)) { Error = true; return false; }
	
	// read the chunk header
	// calling the ChunkLoadClass::Read fn so that if we exhaust the chunk, the read will fail
	if (Read(&MCHeader,sizeof(MCHeader)) != sizeof(MCHeader)) {
		return false;
	}
	if (MCHeader.Get_Size() > available - sizeof(MicroChunkHeader)) {
		Error = true;
		return false;
	}
	
	InMicroChunk = true;
	MicroChunkPosition = 0;
	return true;
}


/***********************************************************************************************
 * ChunkLoadClass::Close_Micro_Chunk -- closes a micro-chunk (seeks to end)                    *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   9/3/99     GTH : Created.                                                                 *
 *=============================================================================================*/
bool ChunkLoadClass::Close_Micro_Chunk()
{
	if (!InMicroChunk || StackIndex <= 0 || File == NULL) {
		Error = true;
		return false;
	}

	const uint32 csize = MCHeader.Get_Size();
	const uint32 pos = static_cast<uint32>(MicroChunkPosition);
	
	if (pos > csize) {
		Error = true;
	} else if (pos < csize && !Error && Seek(csize - pos) != csize - pos) {
		Error = true;
	}
	InMicroChunk = false;

	return !Error;
}


/***********************************************************************************************
 * ChunkLoadClass::Cur_Micro_Chunk_ID -- returns the ID of the current micro-chunk (asserts if *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 * Asserts if you are not currently inside a micro-chunk                                       *
 * Micro chunks have an id between 0 and 255                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   9/3/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkLoadClass::Cur_Micro_Chunk_ID()
{
	assert(InMicroChunk);
	return MCHeader.Get_Type();
}


/***********************************************************************************************
 * ChunkLoadClass::Cur_Micro_Chunk_Length -- returns the size of the current micro chunk       *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 * Asserts if you are not currently inside a micro-chunk                                       *
 * Micro chunks have a maximum size of 255 bytes                                               *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   9/3/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkLoadClass::Cur_Micro_Chunk_Length()
{
	assert(InMicroChunk);
	return MCHeader.Get_Size();
}

// Seek over nbytes in the stream
uint32 ChunkLoadClass::Seek(uint32 nbytes)
{
	if (Error || StackIndex < 1 || File == NULL) {
		Error = true;
		return 0;
	}

	// Don't seek if we would go past the end of the current chunk
	if (PositionStack[StackIndex-1] > HeaderStack[StackIndex-1].Get_Size() ||
		nbytes > HeaderStack[StackIndex-1].Get_Size() - PositionStack[StackIndex-1]) {
		Error = true;
		return 0;
	}

	// Don't read if we are in a micro chunk and would go past the end of it
	if (InMicroChunk && (MicroChunkPosition < 0 ||
		nbytes > MCHeader.Get_Size() - static_cast<uint32>(MicroChunkPosition))) {
		Error = true;
		return 0;
	}
	
	uint32 curpos=File->Tell();
	if (File->Seek(nbytes,SEEK_CUR)-curpos != (int)nbytes) {
		Error = true;
		return 0;
	}

	// Update our position in the chunk
	PositionStack[StackIndex-1] += nbytes;

	// Update our position in the micro chunk if we are in one
	if (InMicroChunk) {
		MicroChunkPosition += nbytes;
	}

	return nbytes;
}

/*********************************************************************************************** 
 * ChunkLoadClass::Read -- Read data from the file                                             * 
 *                                                                                             * 
 * INPUT:                                                                                      * 
 *                                                                                             * 
 * OUTPUT:                                                                                     * 
 *                                                                                             * 
 * WARNINGS:                                                                                   * 
 *                                                                                             * 
 * HISTORY:                                                                                    * 
 *   07/17/1997 GH  : Created.                                                                 * 
 *=============================================================================================*/
uint32 ChunkLoadClass::Read(void * buf,uint32 nbytes)
{
	if (Error || StackIndex < 1 || File == NULL || (buf == NULL && nbytes != 0U)) {
		Error = true;
		return 0;
	}

	// Don't read if we would go past the end of the current chunk
	if (PositionStack[StackIndex-1] > HeaderStack[StackIndex-1].Get_Size() ||
		nbytes > HeaderStack[StackIndex-1].Get_Size() - PositionStack[StackIndex-1]) {
		Error = true;
		return 0;
	}

	// Don't read if we are in a micro chunk and would go past the end of it
	if (InMicroChunk && (MicroChunkPosition < 0 ||
		nbytes > MCHeader.Get_Size() - static_cast<uint32>(MicroChunkPosition))) {
		Error = true;
		return 0;
	}
	
	if (File->Read(buf,nbytes) != (int)nbytes) {
		Error = true;
		return 0;
	}

	// Update our position in the chunk
	PositionStack[StackIndex-1] += nbytes;

	// Update our position in the micro chunk if we are in one
	if (InMicroChunk) {
		MicroChunkPosition += nbytes;
	}

	return nbytes;
}


/***********************************************************************************************
 * ChunkLoadClass::Read -- read an IOVector2Struct                                             *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkLoadClass::Read(IOVector2Struct * v)
{
	assert(v != NULL);
	return Read(v,sizeof(*v));
}


/***********************************************************************************************
 * ChunkLoadClass::Read -- read an IOVector3Struct                                             *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkLoadClass::Read(IOVector3Struct * v)
{
	assert(v != NULL);
	return Read(v,sizeof(*v));
}


/***********************************************************************************************
 * ChunkLoadClass::Read -- read an IOVector4Struct                                             *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkLoadClass::Read(IOVector4Struct * v)
{
	assert(v != NULL);
	return Read(v,sizeof(*v));
}


/***********************************************************************************************
 * ChunkLoadClass::Read -- read an IOQuaternionStruct                                          *
 *                                                                                             *
 * INPUT:                                                                                      *
 *                                                                                             *
 * OUTPUT:                                                                                     *
 *                                                                                             *
 * WARNINGS:                                                                                   *
 *                                                                                             *
 * HISTORY:                                                                                    *
 *   1/4/99     GTH : Created.                                                                 *
 *=============================================================================================*/
uint32 ChunkLoadClass::Read(IOQuaternionStruct * q)
{
	assert(q != NULL);
	return Read(q,sizeof(*q));
}
