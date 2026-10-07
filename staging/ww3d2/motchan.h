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

/* $Header: /Commando/Code/ww3d2/motchan.h 5     11/29/01 1:07p Jani_p $ */
/*********************************************************************************************** 
 ***                            Confidential - Westwood Studios                              *** 
 *********************************************************************************************** 
 *                                                                                             * 
 *                 Project Name : Commando / G 3D Library                                      * 
 *                                                                                             * 
 *                     $Archive:: /Commando/Code/ww3d2/motchan.h                              $* 
 *                                                                                             * 
 *                      $Author:: Jani_p                                                      $* 
 *                                                                                             * 
 *                     $Modtime:: 11/28/01 5:43p                                              $* 
 *                                                                                             * 
 *                    $Revision:: 5                                                           $* 
 *                                                                                             * 
 *---------------------------------------------------------------------------------------------* 
 * Functions:                                                                                  * 
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#if defined(_MSC_VER)
#pragma once
#endif

#ifndef MOTCHAN_H
#define MOTCHAN_H

#include "always.h"
#include "bittype.h"
#include "w3d_file.h"
#include "wwdebug.h"

class ChunkLoadClass;
class Quaternion;

/******************************************************************************

	MotionChannelClass is used to store motion.  Motion data
	is broken into separate channels for X, Y, Z, and orientation.
	Then if any of the channels are empty, they don't have to be stored.
	The X,Y,Z channels all contain one-dimensional vectors and the
	orientation channel contains four-dimensional vectors (quaternions).

******************************************************************************/

class MotionChannelClass
{

public:
	void Do_Data_Compression(int datasize);
	void Get_Vector(int frame,float * setvec) const;

	MotionChannelClass(void);
	~MotionChannelClass(void);

	bool	Load_W3D(ChunkLoadClass & cload);		
	WWINLINE int Get_Type(void) const { return Type; }
	WWINLINE int Get_Pivot(void) const { return PivotIdx; }
	WWINLINE void Set_Pivot(int idx) { PivotIdx=idx; }

private:

	uint32	PivotIdx;			// what pivot is this channel applied to
	uint32	Type;					// what type of channel is this
	int		VectorLen;			// size of each individual vector

	float		ValueOffset;
	float		ValueScale;
	unsigned short* CompressedData;

	float	*	Data;					// pointer to the raw floating point data
	int		FirstFrame;			// first frame which was non-identity
	int		LastFrame;			// last frame which was non-identity
	void Free(void);
	WWINLINE void set_identity(float * setvec) const;

//	friend class HRawAnimClass;

};

WWINLINE void MotionChannelClass::set_identity(float * setvec) const
{
	if (Type == ANIM_CHANNEL_Q) {

		setvec[0] = 0.0f;
		setvec[1] = 0.0f;
		setvec[2] = 0.0f;
		setvec[3] = 1.0f;

	} else {

		setvec[0] = 0.0f;

	}
}

// Inline so the per-pivot raw-animation samplers avoid one call per channel
// read; otherwise the original definition from motchan.cpp.  The fixed 1/4
// element copies are the original loop unrolled for the only W3D widths, so
// GCC cannot turn the inlined loop into a memcpy call.
WWINLINE void MotionChannelClass::Get_Vector(int frame,float * setvec) const
{
	if ((frame < FirstFrame) || (frame > LastFrame)) {
		set_identity(setvec);
	}else {
		int vframe = frame - FirstFrame;
		if (Data) {
			const float * src = &Data[vframe * VectorLen];
			if (VectorLen == 1) {
				setvec[0] = src[0];
			} else if (VectorLen == 4) {
				setvec[0] = src[0];
				setvec[1] = src[1];
				setvec[2] = src[2];
				setvec[3] = src[3];
			} else {
				for (int i=0; i<VectorLen; i++) {
					setvec[i] = Data[vframe * VectorLen + i];
				}
			}
		}
		else {
			WWASSERT(CompressedData);
			float scale=ValueScale/65535.0f;
			for (int i=0; i<VectorLen; i++) {
				float value=int(CompressedData[vframe * VectorLen + i]);
				setvec[i] = value*scale+ValueOffset;
			}
		}
	}
}

/******************************************************************************

	BitChannelClass is used to store a boolean "on/off" value for each frame
	in an animation.  

******************************************************************************/

class BitChannelClass
{

public:

	BitChannelClass(void);
	~BitChannelClass(void);

	bool	Load_W3D(ChunkLoadClass & cload);
	WWINLINE int	Get_Type(void) const { return Type; }
	WWINLINE int	Get_Pivot(void) const { return PivotIdx; }
	WWINLINE int	Get_Bit(int frame) const;

private:

	uint32	PivotIdx;
	uint32	Type;
	int		DefaultVal;
	int		FirstFrame;
	int		LastFrame;

	uint8 *	Bits;

	void Free(void);

	friend class HRawAnimClass;
};


WWINLINE int BitChannelClass::Get_Bit(int frame) const
{
	if ((frame < FirstFrame) || (frame > LastFrame)) {

		return DefaultVal;

	} else {
	
		int bit = frame - FirstFrame;

		uint8 mask = (uint8)(1 << (bit % 8));
		return ((*(Bits + (bit/8)) & mask) != 0);
		
	}
}

/******************************************************************************

	TimeCodedMotionChannelClass is used to store motion.  Motion data
	is broken into separate channels for X, Y, Z, and orientation.
	Then if any of the channels are empty, they don't have to be stored.
	The X,Y,Z channels all contain one-dimensional vectors and the
	orientation channel contains four-dimensional vectors (quaternions).

******************************************************************************/

class TimeCodedMotionChannelClass
{

public:

	TimeCodedMotionChannelClass(void);
	~TimeCodedMotionChannelClass(void);

	bool	Load_W3D(ChunkLoadClass & cload);		
	int	Get_Type(void) { return Type; }
	int	Get_Pivot(void) { return PivotIdx; }
	void	Get_Vector(float32 frame, float * setvec);

	Quaternion Get_QuatVector(float32 frame);

private:

	uint32	PivotIdx;			// what pivot is this channel applied to
	uint32	Type;					// what type of channel is this
	int		VectorLen;			// size of each individual vector
	uint32	PacketSize;			// size of each packet
	
	uint32	NumTimeCodes;		// Number of packets

	uint32	LastTimeCodeIdx;	// absolute index to last time code
	uint32	CachedIdx;			// Last Index Used
  
	uint32	*	Data;			 	// pointer to packet data

	void 		Free(void);
	void 		set_identity(float * setvec);
	uint32	get_index(uint32 timecode);
	uint32	binary_search_index(uint32 timecode);

	friend class HCompressedAnimClass;
};

class AdaptiveDeltaMotionChannelClass
{

public:

	AdaptiveDeltaMotionChannelClass(void);
	~AdaptiveDeltaMotionChannelClass(void);

	bool	Load_W3D(ChunkLoadClass & cload);		
	int	Get_Type(void) { return Type; }
	int	Get_Pivot(void) { return PivotIdx; }
	void	Get_Vector(float32 frame, float * setvec);

	Quaternion Get_QuatVector(float32 frame);

private:

	uint32	PivotIdx;			// what pivot is this channel applied to
	uint32	Type;					// what type of channel is this
	int		VectorLen;			// size of each individual vector
	
	uint32	NumFrames;			// Number of frames

	float		Scale;				// Scale Filter, this much
  
	uint32  *Data;				 	// pointer to packet data

	uint32	CacheFrame;
	float	  *CacheData;			// the data for CachedFrame, and CachedFrame+1, x VectorLen

	void 		Free(void);

	float		getframe(uint32 frame_idx, uint32 vector_idx=0);
   void		decompress(uint32 frame_idx, float *outdata);
   void		decompress(uint32 src_idx, float *srcdata, uint32 frame_idx, float *outdata);

	friend class HCompressedAnimClass;
};



/******************************************************************************

	TimeCodedBitChannelClass is used to store a boolean "on/off" value for each frame
	in an animation.  

******************************************************************************/

class TimeCodedBitChannelClass
{

public:

	TimeCodedBitChannelClass(void);
	~TimeCodedBitChannelClass(void);

	bool	Load_W3D(ChunkLoadClass & cload);
	int	Get_Type(void) { return Type; }
	int	Get_Pivot(void) { return PivotIdx; }
	int	Get_Bit(int frame);

private:

	uint32	PivotIdx;
	uint32	Type;
	int		DefaultVal;
	
	uint32	NumTimeCodes;
	uint32	CachedIdx;

	uint32	*Bits;

	void Free(void);

	friend class HCompressedAnimClass;
};


#endif