#pragma once

// Compile-time Miles Sound System ABI surface used by original WWAudio class
// declarations. Miles is unavailable on Vita; behavior is implemented later
// below WWAudio by the Vita audio backend rather than fabricated here.

#include <stdint.h>

typedef uint32_t U32;
typedef int32_t S32;

typedef void *H3DPOBJECT;
typedef void *H3DSAMPLE;
typedef void *HDIGDRIVER;
typedef void *HPROVIDER;
typedef void *HSAMPLE;
typedef void *HSTREAM;
typedef void *HTIMER;
typedef void *LPWAVEFORMAT;

static inline void AIL_lock(void) {}
static inline void AIL_unlock(void) {}
static inline void AIL_set_3D_position(H3DSAMPLE, float, float, float) {}
static inline void AIL_set_3D_orientation(H3DSAMPLE, float, float, float,
	float, float, float) {}

#ifndef AILCALLBACK
#define AILCALLBACK
#endif
