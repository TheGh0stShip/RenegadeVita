#pragma once

#include "win32_compat.h"

// WWUI list controls retain a 32-bit user-data ABI. Vita is ILP32, while the
// host sanitizer harness is LP64. These helpers preserve the original Vita
// representation and give host-only validation an explicit reversible token.
uint32_t Renegade_Ui_Pointer_To_Token(void *pointer);
void *Renegade_Ui_Pointer_From_Token(uint32_t token);
void *Renegade_Ui_Take_Pointer_Token(uint32_t token);
