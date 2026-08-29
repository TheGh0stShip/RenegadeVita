/*
 * Narrow SceLibMp4Recorder compatibility header for the Renegade demo recorder
 * helper when the installed VitaSDK has the stubs/YAML but not psp2/mp4rec.h.
 *
 * API shape follows the public VitaSDK mp4rec.h documentation and links only
 * against the installed VitaSDK SceLibMp4Recorder stubs. This file is not used
 * by the Renegade VPK.
 */
#ifndef _PSP2_MP4REC_H_
#define _PSP2_MP4REC_H_

#include <vitasdk/build_utils.h>
#include <psp2/types.h>

#ifdef __cplusplus
extern "C" {
#endif

#define SCE_MP4REC_COMMON_DENOM_TIMESCALE 240000
#define SCE_MP4REC_VIDEO_TIMESCALE 30000
#define SCE_MP4REC_AUDIO_TIMESCALE 48000

#define SCE_MP4REC_VIDEO_SAMPLE_DURATION 1001
#define SCE_MP4REC_AUDIO_SAMPLE_DURATION 1024

#define SCE_MP4REC_AUDIO_BUFFER_SIZE 4096

typedef enum {
	SCE_MP4REC_PIXELFORMAT_A8B8G8R8 = 0x00000000,
	SCE_MP4REC_PIXELFORMAT_YUV420_PACKED = 0x00000020
} SceMp4RecPixelFormat;

typedef enum {
	SCE_MP4REC_MODE_640_368_2MBPS,
	SCE_MP4REC_MODE_640_368_1MBPS,
	SCE_MP4REC_MODE_480_272_2MBPS,
	SCE_MP4REC_MODE_480_272_1MBPS,
	SCE_MP4REC_MODE_368_208_2MBPS,
	SCE_MP4REC_MODE_368_208_1MBPS
} SceMp4RecMode;

typedef struct {
	SceSize size;
	void *base;
	uint32_t base_size;
	int unk;
} SceMp4RecRecorder;

typedef struct {
	SceSize size;
	uint32_t mode;
	void *encoder_mem;
	uint32_t encoder_size;
	void *av_mem;
	uint32_t av_size;
	int affinity;
	int priority;
} SceMp4RecInitParam;

typedef struct {
	SceSize size;
	int pixelformat;
	int stride;
	int width;
	int height;
	char unk[16];
	void *buffer;
	uint32_t reserved;
} SceMp4RecFrame;

typedef struct {
	SceSize size;
	SceBool discard;
	uint32_t reserved[128];
	void *metadata;
} SceMp4RecTermParam;

int sceMp4RecCreateRecorder(SceMp4RecRecorder *rec);
int sceMp4RecDeleteRecorder(SceMp4RecRecorder *rec);
int sceMp4RecQueryPhysicalMemSize(SceMp4RecRecorder *rec, int mode, uint32_t *encoder_size, uint32_t *av_size);
int sceMp4RecInit(SceMp4RecRecorder *rec, SceMp4RecInitParam *params);
int sceMp4RecTerm(SceMp4RecRecorder *rec, SceMp4RecTermParam *params);
int sceMp4RecCsc(SceMp4RecFrame *dst, SceMp4RecFrame *src);
int sceMp4RecAddVideoSample(SceMp4RecRecorder *rec, void *buffer, int size);
int sceMp4RecAddAudioSample(SceMp4RecRecorder *rec, void *buffer, int size);

#ifdef __cplusplus
}
#endif

#endif
