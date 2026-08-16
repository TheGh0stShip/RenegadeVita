#pragma once

#include <stddef.h>
#include <stdint.h>

// The canonical released chat.rc declares the original menu layouts.  CMake
// deterministically compiles its selected records into native RT_DIALOG bytes;
// this boundary exposes those bytes to unchanged DialogParserClass code.
namespace RenegadeDialogResources {
const unsigned char *Find_Dialog(uint16_t resource_id, size_t *byte_count);
const char *Last_Error();
}
