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

/****************************************************************************
*
* FILE
*     $Archive: /Commando/Code/BinkMovie/subtitleparser.cpp $
*
* DESCRIPTION
*     Subtitling control file parser
*
* PROGRAMMER
*     Denzil E. Long, Jr.
*
* VERSION INFO
*     $Author: Denzil_l $
*     $Modtime: 1/12/02 9:27p $
*     $Revision: 2 $
*
****************************************************************************/

#include "subtitleparser.h"
#include "subtitle.h"
#include "straw.h"
#include "readline.h"
#include "trim.h"
#include <wchar.h>
#include <stdlib.h>
#include <errno.h>
#include <stdint.h>

// Subtitle control file parsing tokens
#define BEGINMOVIE_TOKEN L"BeginMovie"
#define ENDMOVIE_TOKEN   L"EndMovie"
#define TIMEBIAS_TOKEN   L"TimeBias"
#define TIME_TOKEN       L"Time"
#define DURATION_TOKEN   L"Duration"
#define POSITION_TOKEN   L"Position"
#define COLOR_TOKEN      L"Color"
#define TEXT_TOKEN       L"Text"

static bool Decode_Time_String(const wchar_t* string, unsigned long& time);
bool Parse_Time(wchar_t* string, SubTitleClass* subTitle);
bool Parse_Duration(wchar_t* string, SubTitleClass* subTitle);
bool Parse_Position(wchar_t* string, SubTitleClass* subTitle);
bool Parse_Color(wchar_t* string, SubTitleClass* subTitle);
bool Parse_Text(wchar_t* string, SubTitleClass* subTitle);

SubTitleParserClass::TokenHook SubTitleParserClass::mTokenHooks[] =
{
	{TIME_TOKEN, Parse_Time},
	{DURATION_TOKEN, Parse_Duration},
	{POSITION_TOKEN, Parse_Position},
	{COLOR_TOKEN, Parse_Color},
	{TEXT_TOKEN, Parse_Text},
	{NULL, NULL}
};

/******************************************************************************
*
* NAME
*     SubTitleParserClass::SubTitleParserClass
*
* DESCRIPTION
*
* INPUTS
*     Input - Control file input stream.
*
* RESULTS
*     NONE
*
******************************************************************************/

SubTitleParserClass::SubTitleParserClass(Straw& input)
	:
	mInput(input),
	mLineNumber(0),
	mInputValid(false)
{
	// Check for Unicode byte-order mark.
	// All Unicode plaintext files are prefixed with the byte-order mark U+FEFF
	// or its mirror U+FFFE. This mark is  used to indicate the byte order of a
	// text stream.
	wchar_t byteOrderMark = 0;
	mInputValid = mInput.Get(&byteOrderMark, sizeof(byteOrderMark)) == sizeof(byteOrderMark) &&
		byteOrderMark == 0xFEFF;
	mBuffer[0] = 0;

	if (!mInputValid) {
		WWDEBUG_SAY(("Error: Subtitle control file is not unicode!\n"));
	}
}


/******************************************************************************
*
* NAME
*     SubTitleParserClass::~SubTitleParserClass
*
* DESCRIPTION
*
* INPUTS
*     NONE
*
* RESULTS
*     NONE
*
******************************************************************************/

SubTitleParserClass::~SubTitleParserClass()
{
}


/******************************************************************************
*
* NAME
*     SubTitleParserClass::GetSubTitles
*
* DESCRIPTION
*
* INPUTS
*     NONE
*
* RESULTS
*
******************************************************************************/

DynamicVectorClass<SubTitleClass*>* SubTitleParserClass::Get_Sub_Titles(const char* moviename)
{
	DynamicVectorClass<SubTitleClass*>* subTitleCollection = NULL;
	
	// Find the movie marker
	if (Find_Movie_Entry(moviename) == true)	{
		// Allocate container to hold subtitles
		subTitleCollection = new DynamicVectorClass<SubTitleClass*>;
		WWASSERT(subTitleCollection != NULL);

		if (subTitleCollection != NULL) {
			for (;;) {
				// Retrieve a line from the control file
				wchar_t* string = Get_Next_Line();
				if (string == NULL) {
					WWDEBUG_SAY(("Error on line %u: subtitle movie has no EndMovie token\n", Get_Line_Number()));
					break;
				}

				if (rv_utf16_length(string) > 0) {
					// Check for subtitle entry markers
					if ((string[0] == L'<') && (string[rv_utf16_length(string) - 1] == L'>')) {
						// Trim off markers
						string++;
						string[rv_utf16_length(string) - 1] = 0;
						rv_utf16_trim(string);

						// Ignore empty caption
						if (rv_utf16_length(string) == 0) {
							continue;
						}

						// Create a new SubTitleClass
						SubTitleClass* subTitle = new SubTitleClass();
						WWASSERT(subTitle != NULL);

						if (subTitle == NULL) {
							WWDEBUG_SAY(("***** Failed to create SubTitleClass!\n"));
							break;
						}

						if (Parse_Sub_Title(string, subTitle) == true)	{
							if (!subTitleCollection->Add(subTitle)) {
								delete subTitle;
								break;
							}
						}
						else {
							delete subTitle;
						}

						continue;
					}

					// A missing EndMovie must not consume another movie's captions.
					if (rv_utf16_case_n_compare(string, BEGINMOVIE_TOKEN, rv_utf16_length(BEGINMOVIE_TOKEN)) == 0) {
						WWDEBUG_SAY(("Error on line %u: subtitle movie has no EndMovie token\n", Get_Line_Number()));
						break;
					}

					// Terminate if end movie token encountered.
					if (rv_utf16_case_n_compare(string, ENDMOVIE_TOKEN, rv_utf16_length(ENDMOVIE_TOKEN)) == 0) {
						break;
					}
				}
			}

			if (subTitleCollection->Count() == 0) {
				delete subTitleCollection;
				subTitleCollection = NULL;
			}
		}
	}

	return subTitleCollection;
}


/******************************************************************************
*
* NAME
*     SubTitleParserClass::FindMovieEntry
*
* DESCRIPTION
*     No description provided,
*
* INPUTS
*     Moviename - Pointer to name of movie to find subtitles for.
*
* RESULTS
*     Success - True if movie entry found; False if unable to find movie entry.
*
******************************************************************************/

bool SubTitleParserClass::Find_Movie_Entry(const char* moviename)
{
	// Convert the moviename into Unicode
	if (!mInputValid || moviename == NULL || moviename[0] == 0) return false;
	wchar_t wideName[LINE_BUFFER_SIZE];
	// The original filenames are ANSI bytes. Use the existing port conversion
	// boundary; libc mbstowcs has a different wchar_t ABI on Vita.
	if (!MultiByteToWideChar(CP_ACP, 0, moviename, -1, wideName, LINE_BUFFER_SIZE)) {
		return false;
	}

	do {
		// Retrieve line of text
		wchar_t* string = Get_Next_Line();

		// Terminate if no string read.
		if (string == NULL) {
			break;
		}

		// Look for begin movie token
		if (rv_utf16_case_n_compare(string, BEGINMOVIE_TOKEN, rv_utf16_length(BEGINMOVIE_TOKEN)) == 0) {
			// Get moviename following the token
			wchar_t* ptr = string + rv_utf16_length(BEGINMOVIE_TOKEN);

			// Check for matching moviename
			if (*ptr != 0 && *ptr <= L' ') {
				rv_utf16_trim(ptr);

				if (rv_utf16_case_compare(ptr, wideName) == 0) {
					WWDEBUG_SAY(("Found movie entry %s\n", moviename));
					return true;
				}
			}
		}
	} while (true);

	return false;
}


/******************************************************************************
*
* NAME
*     SubTitleParserClass::ParseSubTitle
*
* DESCRIPTION
*
* INPUTS
*     wchar_t* string
*     SubTitleClass* subTitle
*
* RESULTS
*     bool
*
******************************************************************************/

bool SubTitleParserClass::Parse_Sub_Title(wchar_t* string, SubTitleClass* subTitle)
{
	// Parameter check
	WWASSERT(string != NULL);
	WWASSERT(subTitle != NULL);

	for (;;) {
		// Find token separator
		wchar_t* separator = rv_utf16_chr(string, L'=');

		if (separator == NULL) {
			WWDEBUG_SAY(("Error on line %d: syntax error\n", Get_Line_Number()));
			return false;
		}

		// NULL terminate token part
		*separator++ = 0;

		// Tokens are to the left of the separator
		wchar_t* token = string;
		rv_utf16_trim(token);

		// Parameters are to the right of the separator
		wchar_t* param = separator;
		rv_utf16_trim(param);

		// Quoted parameters are treated as literals (ignore contents)
		if (param[0] == L'"') {
			// Skip leading quote
			param++;

			// Use next quote to mark end of parameter
			separator = rv_utf16_chr(param, L'"');

			if (separator == NULL) {
				WWDEBUG_SAY(("Error on line %d: mismatched quotes\n", Get_Line_Number()));
				return false;
			}

			// NULL terminate parameter
			*separator++ = 0;

			// Skip any comma following a literal string since we used the trailing
			// quote to terminate the tokens parameters
			rv_utf16_trim(separator);
			
			if (*separator == L',') {
				separator++;
			}

			// Advance string past quoted parameter
			string = separator;
		}
		else {
			// Look for separator to next token
			separator = param;
			while (*separator != 0 && *separator != L',' && *separator != L' ') ++separator;
			if (*separator == 0) separator = NULL;

			if (separator != NULL) {
				*separator++ = 0;
				string = separator;
			}
			else {
				string = param + rv_utf16_length(param);
			}
		}

		// Error on empty tokens
		if (rv_utf16_length(token) == 0) {
			WWDEBUG_SAY(("Error on line %d: missing token\n", Get_Line_Number()));
			return false;
		}

		// Parse current token
		if (!Parse_Token(token, param, subTitle)) {
			WWDEBUG_SAY(("Error on line %u: invalid subtitle parameter\n", Get_Line_Number()));
			return false;
		}

		// Prepare for next token
		rv_utf16_trim(string);

		if (rv_utf16_length(string) == 0) {
			break;
		}
	}

	if (subTitle->Get_Caption() == NULL) {
		WWDEBUG_SAY(("Error on line %u: missing subtitle Text token\n", Get_Line_Number()));
		return false;
	}
	return true;
}


/******************************************************************************
*
* NAME
*     SubTitleParserClass::ParseToken
*
* DESCRIPTION
*
* INPUTS
*     wchar_t* token
*     wchar_t* param
*     SubTitleClass* subTitle
*
* RESULTS
*     NONE
*
******************************************************************************/

bool SubTitleParserClass::Parse_Token(wchar_t* token, wchar_t* param, SubTitleClass* subTitle)
{
	// Parameter check
	WWASSERT(token != NULL);
	WWASSERT(subTitle != NULL);

	if (token != NULL) {
		int index = 0;

		while (mTokenHooks[index].Token != NULL) {
			TokenHook& hook = mTokenHooks[index];

			if (rv_utf16_case_compare(hook.Token, token) == 0) {
				WWASSERT(subTitle != NULL);
				return hook.Handler(param, subTitle);
			}

			index++;
		}
	}
	// Retain the original forward-compatible handling of unknown tokens.
	return true;
}


/******************************************************************************
*
* NAME
*     SubTitleParserClass::GetNextLine
*
* DESCRIPTION
*     Retrieve the next line of text from the control file.
*
* INPUTS
*     NONE
*
* RESULTS
*     String - Pointer to next line of text. NULL if error or EOF.
*
******************************************************************************/

wchar_t* SubTitleParserClass::Get_Next_Line(void)
{
	if (!mInputValid) return NULL;
	bool eof = false;

	while (eof == false) {
		// Read in a line of text
		Read_Line(mInput, mBuffer, LINE_BUFFER_SIZE, eof);
		mLineNumber++;

		// Remove whitespace
		wchar_t* string = rv_utf16_trim(mBuffer);

		// Skip comments and blank lines
		if ((rv_utf16_length(string) > 0) && (string[0] != L';')) {
			return string;
		}
	}

	return NULL;
}


// Parse decimal fields without crossing libc's four-byte wchar_t boundary.
// Bound every component to the original 32-bit Windows/Vita unsigned long.
static bool Decode_Unsigned_Fields(const wchar_t* string, unsigned long* fields, int count)
{
	if (string == NULL) return false;
	for (int index = 0; index < count; ++index) {
		if (*string < L'0' || *string > L'9') return false;
		unsigned long value = 0;
		do {
			const unsigned long digit = static_cast<unsigned long>(*string - L'0');
			if (value > (UINT32_MAX - digit) / 10UL) return false;
			value = value * 10UL + digit;
			++string;
		} while (*string >= L'0' && *string <= L'9');
		fields[index] = value;
		if (index + 1 < count) {
			if (*string != L':') return false;
			++string;
		} else if (*string != 0) {
			return false;
		}
	}
	return true;
}

// Original authored format: hours:minutes:seconds:hundredths. Convert to
// 1/60-second ticks, retaining the original truncation and field rollover.
static bool Decode_Time_String(const wchar_t* string, unsigned long& time)
{
	unsigned long fields[4];
	if (!Decode_Unsigned_Fields(string, fields, 4)) return false;
	const uint64_t ticks = static_cast<uint64_t>(fields[0]) * 216000U +
		static_cast<uint64_t>(fields[1]) * 3600U +
		static_cast<uint64_t>(fields[2]) * 60U +
		(static_cast<uint64_t>(fields[3]) * 60U) / 100U;
	if (ticks > UINT32_MAX) return false;
	time = static_cast<unsigned long>(ticks);
	return true;
}


bool Parse_Time(wchar_t* param, SubTitleClass* subTitle)
{
	unsigned long time;
	if (subTitle == NULL || !Decode_Time_String(param, time)) return false;
	subTitle->Set_Display_Time(time);
	return true;
}


bool Parse_Duration(wchar_t* param, SubTitleClass* subTitle)
{
	unsigned long time;
	if (subTitle == NULL || !Decode_Time_String(param, time)) return false;
	if (time > 0) {
		subTitle->Set_Display_Duration(time);
	}
	return true;
}


bool Parse_Position(wchar_t* param, SubTitleClass* subTitle)
{
	static struct
	{
		const wchar_t* Name;
		SubTitleClass::Alignment Align;
		} _alignLookup[] = {
			{L"Left", SubTitleClass::Left},
			{L"Right", SubTitleClass::Right},
			{L"Center", SubTitleClass::Center},
			{NULL, SubTitleClass::Center}
	};

	if (param == NULL || subTitle == NULL) return false;
	wchar_t* ptr = param;

	// Keep the original base-zero line-number syntax, but use the narrow
	// libc API and enforce the line-position contract (1 through 15).
	wchar_t* separator = rv_utf16_chr(ptr, L':');
	if (separator != NULL) {
		char line[32];
		const size_t length = static_cast<size_t>(separator - ptr);
		if (length == 0 || length >= sizeof(line)) return false;
		for (size_t index = 0; index < length; ++index) {
			if (ptr[index] > 0x7f) return false;
			line[index] = static_cast<char>(ptr[index]);
		}
		line[length] = 0;
		char* end = NULL;
		errno = 0;
		const long linePos = strtol(line, &end, 0);
		if (errno == ERANGE || end == line || *end != 0 || linePos < 1 || linePos > 15) return false;
		subTitle->Set_Line_Position(static_cast<int>(linePos));
		ptr = separator + 1;
	}

	// Retain the original center fallback for an unrecognized alignment.
	SubTitleClass::Alignment align = SubTitleClass::Center;
	int index = 0;
	while (_alignLookup[index].Name != NULL) {
		if (rv_utf16_case_compare(ptr, _alignLookup[index].Name) == 0) {
			align = _alignLookup[index].Align;
			break;
		}
		index++;
	}
	subTitle->Set_Alignment(align);
	return true;
}


bool Parse_Color(wchar_t* param, SubTitleClass* subTitle)
{
	unsigned long components[3];
	if (subTitle == NULL || !Decode_Unsigned_Fields(param, components, 3)) return false;
	for (int index = 0; index < 3; ++index) {
		if (components[index] > 255U) return false;
	}
	subTitle->Set_RGB_Color(static_cast<unsigned char>(components[0]),
		static_cast<unsigned char>(components[1]), static_cast<unsigned char>(components[2]));
	return true;
}


bool Parse_Text(wchar_t* param, SubTitleClass* subTitle)
{
	if (param == NULL || subTitle == NULL) return false;
	subTitle->Set_Caption(param);
	return true;
}
