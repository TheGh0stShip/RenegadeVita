#pragma once

/*
** RVIO1 load-time I/O switches (tutorial round 1, LOAD_TIME_IO).
**
** A user config file ux0:data/renegade/user/config/load-io-v1.flag containing
** exactly "RVIO1 <d>\n" (d = 0..7) selects a mask. A missing, short, long or
** malformed file keeps the build default, which is 0: every original path.
**
**  bit 0  direct reads. VitaSDK newlib gives every FILE a 1 KiB buffer
**         (__smakebuf_r hard-codes BUFSIZ; scestat_to_stat leaves st_blksize
**         0), and a buffered fread copies through it one sceIoRead per KiB.
**         Read-only retail streams opened by RenegadeRootedFileClass are set
**         unbuffered before their first stdio operation, so each 16 KiB
**         BufferedFileClass refill and each large chunk read reaches sceIoRead
**         once. Bytes, file positions and short-read/EOF results are those of
**         the same stdio stream; only the syscall split changes.
**  bit 1  archive size reuse. Original RawFileClass::Bias measures the whole
**         MIX archive with RawFileClass::Size(), which opens and closes the
**         archive once more before every member open. A fresh retail archive
**         object whose size an earlier native probe measured takes the same
**         BiasStart/BiasLength arithmetic without that extra open/close.
**  bit 2  loading presenter cadence. Sub-status (minimum_progress < 0) repaints
**         of the synchronous loading screen are spaced 250 ms instead of 50 ms.
**         Milestone repaints and their catch-up frames are unchanged, so the
**         original progress bar still advances on every milestone.
**
** Gains are hypotheses until measured on hardware.
*/

#include <stddef.h>
#include <stdio.h>
#include <string.h>

enum {
	RENEGADE_LOAD_IO_DIRECT_READS = 1U,
	RENEGADE_LOAD_IO_ARCHIVE_SIZE_REUSE = 2U,
	RENEGADE_LOAD_IO_REPAINT_CADENCE = 4U,
	RENEGADE_LOAD_IO_ALL = 7U,
	RENEGADE_LOAD_IO_DEFAULT = 0U
};

#define RENEGADE_LOAD_IO_FLAG_PATH "ux0:data/renegade/user/config/load-io-v1.flag"

static const unsigned kRenegadeLoadIoDefaultRepaintUs = 50000U;
static const unsigned kRenegadeLoadIoCadenceRepaintUs = 250000U;

// Pure parser shared by the runtime and tools/test_vita_load_io.py's model.
inline unsigned Renegade_Load_Io_Parse_Flag(const char *value, size_t size)
{
	if (value == NULL || size != 8U || memcmp(value, "RVIO1 ", 6U) != 0 ||
		value[7] != '\n' || value[6] < '0' || value[6] > '7') {
		return RENEGADE_LOAD_IO_DEFAULT;
	}
	return static_cast<unsigned>(value[6] - '0');
}

inline unsigned Renegade_Load_Io_Read_Flag_File(const char *path)
{
	FILE *file = fopen(path, "rb");
	if (file == NULL) return RENEGADE_LOAD_IO_DEFAULT;
	char value[9] = {};
	const size_t size = fread(value, 1U, sizeof(value), file);
	const bool read_ok = !ferror(file);
	fclose(file);
	return read_ok ? Renegade_Load_Io_Parse_Flag(value, size) : RENEGADE_LOAD_IO_DEFAULT;
}

inline unsigned Renegade_Load_Io_Substatus_Repaint_Interval_Us(unsigned mask)
{
	return (mask & RENEGADE_LOAD_IO_REPAINT_CADENCE) != 0U ?
		kRenegadeLoadIoCadenceRepaintUs : kRenegadeLoadIoDefaultRepaintUs;
}
