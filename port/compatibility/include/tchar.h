#pragma once

#include <string.h>
#include <strings.h>

typedef char TCHAR;

#define _T(text) text
#define _TEXT(text) text
#define _tcslen strlen
#define _tcsclen strlen
#define _tcscpy strcpy
#define _tcsncpy strncpy
#define _tcscmp strcmp
#define _tcsicmp strcasecmp
#define _tcsnicmp strncasecmp
