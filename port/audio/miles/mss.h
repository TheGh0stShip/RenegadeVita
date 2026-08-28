#pragma once

// Miles Sound System compatibility surface used by the original WWAudio
// owners. Miles is unavailable on Vita; these declarations preserve the
// interface at which the native provider is implemented. They intentionally
// contain no replacement WWAudio policy or game-facing behavior.

#include <stdint.h>
#include <stddef.h>

#include "win32_compat.h"

typedef uint32_t U32;
typedef int32_t S32;
typedef uint16_t U16;
typedef int16_t S16;
typedef uint8_t U8;
typedef int8_t S8;
typedef float F32;

struct RenegadeMilesDriver {
	S32 emulated_ds;
};
struct RenegadeMilesSample;
struct RenegadeMilesStream;

typedef RenegadeMilesSample *H3DPOBJECT;
typedef RenegadeMilesSample *H3DSAMPLE;
typedef RenegadeMilesDriver *HDIGDRIVER;
typedef uintptr_t HPROVIDER;
typedef RenegadeMilesSample *HSAMPLE;
typedef RenegadeMilesStream *HSTREAM;
typedef intptr_t HTIMER;
typedef intptr_t HPROENUM;

typedef struct tWAVEFORMAT {
	U16 wFormatTag;
	U16 nChannels;
	U32 nSamplesPerSec;
	U32 nAvgBytesPerSec;
	U16 nBlockAlign;
} WAVEFORMAT, *LPWAVEFORMAT;

typedef struct pcmwaveformat_tag {
	WAVEFORMAT wf;
	U16 wBitsPerSample;
} PCMWAVEFORMAT;

typedef struct AILSOUNDINFO {
	S32 format;
	const void *data_ptr;
	U32 data_len;
	U32 rate;
	S32 bits;
	S32 channels;
	U32 samples;
	U32 block_size;
	const void *initial_ptr;
} AILSOUNDINFO;

#ifndef WAVE_FORMAT_PCM
#define WAVE_FORMAT_PCM 0x0001
#endif
#ifndef WAVE_FORMAT_IMA_ADPCM
#define WAVE_FORMAT_IMA_ADPCM 0x0011
#endif

enum {
	NO = 0,
	AIL_NO_ERROR = 0,
	AIL_LOCK_PROTECTION = 0,
	DIG_USE_WAVEOUT = 1,
	M3D_NOERR = 0,
	DP_FILTER = 0,
	AIL_3D_2_SPEAKER = 0,
	AIL_3D_HEADPHONE = 1,
	AIL_3D_SURROUND = 2,
	AIL_3D_4_SPEAKER = 3,
	AIL_FILE_SEEK_BEGIN = 0,
	AIL_FILE_SEEK_CURRENT = 1,
	AIL_FILE_SEEK_END = 2,
	ENVIRONMENT_GENERIC = 0
};

#ifndef HPROENUM_FIRST
#define HPROENUM_FIRST 0
#endif

#ifndef AILCALLBACK
#define AILCALLBACK
#endif

typedef U32 (AILCALLBACK *AIL_FILE_OPEN_CALLBACK)(const char *, U32 *);
typedef void (AILCALLBACK *AIL_FILE_CLOSE_CALLBACK)(U32);
typedef S32 (AILCALLBACK *AIL_FILE_SEEK_CALLBACK)(U32, S32, U32);
typedef U32 (AILCALLBACK *AIL_FILE_READ_CALLBACK)(U32, void *, U32);

void AIL_startup(void);
void AIL_shutdown(void);
void AIL_lock(void);
void AIL_unlock(void);
char *AIL_last_error(void);
S32 AIL_set_preference(S32 preference, S32 value);

S32 AIL_waveOutOpen(HDIGDRIVER *driver, void *wave_handle, U32 device,
	LPWAVEFORMAT format);
void AIL_waveOutClose(HDIGDRIVER driver);

HSAMPLE AIL_allocate_sample_handle(HDIGDRIVER driver);
void AIL_release_sample_handle(HSAMPLE sample);
void AIL_init_sample(HSAMPLE sample);
S32 AIL_set_named_sample_file(HSAMPLE sample, char *name, const void *data,
	U32 bytes, S32 block);
void AIL_start_sample(HSAMPLE sample);
void AIL_stop_sample(HSAMPLE sample);
void AIL_resume_sample(HSAMPLE sample);
void AIL_end_sample(HSAMPLE sample);
void AIL_set_sample_pan(HSAMPLE sample, S32 pan);
S32 AIL_sample_pan(HSAMPLE sample);
void AIL_set_sample_volume(HSAMPLE sample, S32 volume);
S32 AIL_sample_volume(HSAMPLE sample);
void AIL_set_sample_loop_count(HSAMPLE sample, U32 count);
U32 AIL_sample_loop_count(HSAMPLE sample);
void AIL_set_sample_ms_position(HSAMPLE sample, U32 milliseconds);
void AIL_sample_ms_position(HSAMPLE sample, S32 *length, S32 *position);
void AIL_set_sample_user_data(HSAMPLE sample, S32 index, U32 value);
U32 AIL_sample_user_data(HSAMPLE sample, S32 index);
S32 AIL_sample_playback_rate(HSAMPLE sample);
void AIL_set_sample_playback_rate(HSAMPLE sample, S32 rate);

S32 AIL_enumerate_3D_providers(HPROENUM *next, HPROVIDER *provider,
	char **name);
S32 AIL_open_3D_provider(HPROVIDER provider);
void AIL_close_3D_provider(HPROVIDER provider);
H3DPOBJECT AIL_3D_open_listener(HPROVIDER provider);
void AIL_set_3D_speaker_type(HPROVIDER provider, S32 speaker_type);
H3DSAMPLE AIL_allocate_3D_sample_handle(HPROVIDER provider);
void AIL_release_3D_sample_handle(H3DSAMPLE sample);
U32 AIL_set_3D_sample_file(H3DSAMPLE sample, const void *data);
void AIL_start_3D_sample(H3DSAMPLE sample);
void AIL_stop_3D_sample(H3DSAMPLE sample);
void AIL_resume_3D_sample(H3DSAMPLE sample);
void AIL_end_3D_sample(H3DSAMPLE sample);
void AIL_set_3D_sample_volume(H3DSAMPLE sample, S32 volume);
S32 AIL_3D_sample_volume(H3DSAMPLE sample);
void AIL_set_3D_sample_loop_count(H3DSAMPLE sample, U32 count);
U32 AIL_3D_sample_loop_count(H3DSAMPLE sample);
void AIL_set_3D_sample_offset(H3DSAMPLE sample, U32 bytes);
U32 AIL_3D_sample_offset(H3DSAMPLE sample);
U32 AIL_3D_sample_length(H3DSAMPLE sample);
void AIL_set_3D_object_user_data(H3DSAMPLE sample, S32 index, U32 value);
U32 AIL_3D_object_user_data(H3DSAMPLE sample, S32 index);
S32 AIL_3D_sample_playback_rate(H3DSAMPLE sample);
void AIL_set_3D_sample_playback_rate(H3DSAMPLE sample, S32 rate);
void AIL_set_3D_position(H3DSAMPLE sample, F32 x, F32 y, F32 z);
void AIL_set_3D_orientation(H3DSAMPLE sample, F32 x_face, F32 y_face,
	F32 z_face, F32 x_up, F32 y_up, F32 z_up);
void AIL_set_3D_velocity_vector(H3DSAMPLE sample, F32 x, F32 y, F32 z);
void AIL_set_3D_sample_distances(H3DSAMPLE sample, F32 maximum,
	F32 minimum);
void AIL_set_3D_sample_effects_level(H3DSAMPLE sample, F32 level);

HSTREAM AIL_open_stream_by_sample(HDIGDRIVER driver, HSAMPLE sample,
	const char *name, S32 stream_mem);
HSTREAM AIL_open_stream(HDIGDRIVER driver, const char *name, S32 stream_mem);
void AIL_close_stream(HSTREAM stream);
void AIL_start_stream(HSTREAM stream);
void AIL_pause_stream(HSTREAM stream, S32 pause);
void AIL_set_stream_pan(HSTREAM stream, S32 pan);
S32 AIL_stream_pan(HSTREAM stream);
void AIL_set_stream_volume(HSTREAM stream, S32 volume);
S32 AIL_stream_volume(HSTREAM stream);
void AIL_set_stream_loop_block(HSTREAM stream, S32 start, S32 end);
void AIL_set_stream_loop_count(HSTREAM stream, U32 count);
U32 AIL_stream_loop_count(HSTREAM stream);
void AIL_set_stream_ms_position(HSTREAM stream, U32 milliseconds);
void AIL_stream_ms_position(HSTREAM stream, S32 *length, S32 *position);
S32 AIL_stream_playback_rate(HSTREAM stream);
void AIL_set_stream_playback_rate(HSTREAM stream, S32 rate);

S32 AIL_WAV_info(const void *data, AILSOUNDINFO *info);
S32 AIL_WAV_info_bounded(const void *data, size_t bytes, AILSOUNDINFO *info);
S32 AIL_enumerate_filters(HPROENUM *next, HPROVIDER *provider, char **name);
void AIL_set_sample_processor(HSAMPLE sample, S32 stage, HPROVIDER provider);
S32 AIL_set_filter_sample_preference(HSAMPLE sample, const char *name,
	const void *value);
void AIL_set_file_callbacks(AIL_FILE_OPEN_CALLBACK open_callback,
	AIL_FILE_CLOSE_CALLBACK close_callback,
	AIL_FILE_SEEK_CALLBACK seek_callback,
	AIL_FILE_READ_CALLBACK read_callback);
void AIL_stop_timer(HTIMER timer);
void AIL_release_timer_handle(HTIMER timer);
