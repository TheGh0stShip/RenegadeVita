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

/***********************************************************************************************
 ***              C O N F I D E N T I A L  ---  W E S T W O O D  S T U D I O S               ***
 ***********************************************************************************************
 *                                                                                             *
 *                 Project Name : Combat																		  *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/wwui/dialogparser.cpp          $*
 *                                                                                             *
 *                       Author:: Patrick Smith                                                *
 *                                                                                             *
 *                     $Modtime:: 10/25/01 3:54p                                              $*
 *                                                                                             *
 *                    $Revision:: 12                                                          $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#include "dialogparser.h"
#include "win.h"
#include "translatedb.h"
#include <commctrl.h>
#if defined(__vita__)
#include "a30_vita_runtime.h"
#endif

//////////////////////////////////////////////////////////////////////////////
//	Macros
//////////////////////////////////////////////////////////////////////////////
#define ALIGN_WORD_PTR(p)	((WORD *)(((uintptr_t)p + 1U) & ~(uintptr_t)1U))
#define ALIGN_DWORD_PTR(p) ((DWORD *)(((uintptr_t)p + 3U) & ~(uintptr_t)3U))


//////////////////////////////////////////////////////////////////////////////
//	Local prototypes
//////////////////////////////////////////////////////////////////////////////
WORD *Skip_Dlg_Field (WORD *src, WCHAR *buffer = NULL, int buffer_len = 0, WORD *ctrl_type = NULL);
#if defined(__vita__)
static unsigned g_vita_dialog_template_logs = 0U;

static unsigned Vita_Dialog_Text_Length(const WCHAR *text)
{
	unsigned length = 0U;
	if (text == NULL) return 0U;
	while (text[length] != 0 && length < 255U) {
		++length;
	}
	return length;
}

static unsigned Vita_Dialog_Buffer_Remaining(const WCHAR *buffer,
	const WCHAR *cursor, unsigned capacity)
{
	if (buffer == NULL || cursor == NULL || capacity == 0U) return 0U;
	for (unsigned offset = 0U; offset < capacity; ++offset) {
		if (buffer + offset == cursor) return capacity - offset;
	}
	return 0U;
}

static bool Vita_Dialog_Copy_Translation(WCHAR *destination,
	unsigned capacity, const WCHAR *translation, unsigned *source_length,
	unsigned *copied_length)
{
	const unsigned source = Vita_Dialog_Text_Length(translation);
	if (source_length != NULL) *source_length = source;
	if (copied_length != NULL) *copied_length = 0U;
	if (destination == NULL || capacity == 0U) return source == 0U;

	unsigned copied = 0U;
	while (translation != NULL && translation[copied] != 0 &&
		copied + 1U < capacity) {
		destination[copied] = translation[copied];
		++copied;
	}
	destination[copied] = 0;
	if (copied_length != NULL) *copied_length = copied;
	return translation == NULL || translation[copied] == 0;
}
#endif


//////////////////////////////////////////////////////////////////////////////
//
//	Skip_Dlg_Field
//
//////////////////////////////////////////////////////////////////////////////
WORD *
Skip_Dlg_Field (WORD *src, WCHAR *buffer, int buffer_len, WORD *ctrl_type)
{
	//
	//	These fields always start on the next word boundary, so align
	//	the source pointer on this boundary.
	//
	WORD *retval = ALIGN_WORD_PTR(src);

	//
	//	Note:  The field codes are as follows:
	//
	//		0xFFFF		- The following WORD is an ordinal value of a system class.
	//		0x0000		- Empty field
	//		Otherwise	- The remaining data is a NULL terminated WCHAR string.
	//
	if (*retval == 0xFFFF) {
		
		//
		//	Move past the field designator
		//
		retval ++;
		
		//
		//	Does the user want information about the ctrl type?
		//
		if (ctrl_type != NULL) {
			*ctrl_type = *retval;
		}

		//
		//	Move past the ctrl type identifier
		//
		retval ++;
	} else if (*retval == 0x0000) {
		
		//
		//	Null terminate the string if the user is expecting data
		//
		if (buffer != NULL) {
			*buffer = 0;
		}

		//
		//	Move past the field designator
		//
		retval ++;
	} else {

		//
		//	The following data is a null-terminated string.  Scan
		// as much data into our desination buffer as possible.
		//	Note:  The data is stored in wide character format.
		//
		while (*retval != 0x0000) {
			if (buffer != NULL && buffer_len > 1) {
				
				//
				//	Store this character in the supplied buffer
				// and decrement the remaining buffer length.
				//
				*buffer++ = *retval;
				buffer_len --;
			}
			retval ++;
		}

		//
		//	Ensure the supplied buffer is NULL terminated
		//
		if (buffer != NULL) {
			*buffer = 0;
		}

		//
		//	Advance to the next field
		//
		retval ++;
	}

	//
	//	Return the new buffer position to the caller
	//
	return retval;
}


//////////////////////////////////////////////////////////////////////////////
//
//	Parse_Template
//
//////////////////////////////////////////////////////////////////////////////
void
DialogParserClass::Parse_Template
(
	int															res_id,
	int *															dlg_width,
	int *															dlg_height,
	WideStringClass *											dlg_title,
	DynamicVectorClass<ControlDefinitionStruct> *	control_list
)
{
	//
	//	Load the resource file
	//
	HRSRC resource		= ::FindResource (ProgramInstance, MAKEINTRESOURCE (res_id), RT_DIALOG);
	HGLOBAL hglobal	= ::LoadResource (ProgramInstance, resource);
	LPVOID res_buffer	= ::LockResource (hglobal);
	if(res_buffer != NULL) {

		//
		//	The first few bytes of the resource buffer are the DLGTEMPLATE structure
		//
		DLGTEMPLATE *dlg_template = (DLGTEMPLATE *)res_buffer;
		(*dlg_width)	= (int)dlg_template->cx;
		(*dlg_height)	= (int)dlg_template->cy;

		//
		//	Move past the DLGTEMPLATE header to the other fields
		//
		WORD *buffer = (WORD *)(((char *)res_buffer) + sizeof (DLGTEMPLATE));
		
		//
		//	Skip the menu, and window class
		//
		buffer = Skip_Dlg_Field (buffer);
		buffer = Skip_Dlg_Field (buffer);

		//
		//	Read the title
		//
		buffer = Skip_Dlg_Field (buffer, dlg_title->Get_Buffer (96), 96);

		WCHAR *string_id = ::wcsstr (dlg_title->Peek_Buffer (), L"IDS_");
		if (string_id != NULL) {
#if defined(__vita__)
			WideStringClass untranslated_title = dlg_title->Peek_Buffer ();
#endif
			WideStringClass wide_string_id = string_id;				
			StringClass ascii_string_id;
			wide_string_id.Convert_To (ascii_string_id);
			(*dlg_title) = TRANSLATE_BY_DESC(ascii_string_id);
#if defined(__vita__)
			if (g_vita_dialog_template_logs < 96U) {
				++g_vita_dialog_template_logs;
				A30_Vita_Log("A3.5 WWUI dialog template: res=%d title_desc=%s untranslated_len=%u translated_len=%u log=%u/96\n",
					res_id, static_cast<const char *>(ascii_string_id),
					Vita_Dialog_Text_Length(untranslated_title),
					Vita_Dialog_Text_Length(dlg_title->Peek_Buffer ()),
					g_vita_dialog_template_logs);
			}
#endif
		}


		//
		//	Do we need to skip past the font settings?
		//
		if (dlg_template->style & DS_SETFONT) {
			buffer ++;
			while (*buffer != 0x0000) {
				buffer ++;
			}
			buffer ++;
		}

		//
		//	Loop over each control and gather information about them
		//
		for (int index = 0; index < dlg_template->cdit; index ++) {
			DLGITEMTEMPLATE *dlg_item_template = (DLGITEMTEMPLATE *)ALIGN_DWORD_PTR((DWORD *)buffer);
			buffer = (WORD *)(((char *)dlg_item_template) + sizeof (DLGITEMTEMPLATE));

			//
			//	Read the ctrl type
			//
			WCHAR text_buffer[256]	= { 0 };
			WORD ctrl_type				= 0x0000;
			buffer = Skip_Dlg_Field (buffer, text_buffer, 256, &ctrl_type);
			
			//
			//	Wasn't one of the standard types, so see if we can determine
			// what it is by its class name.
			//
			if (ctrl_type == 0) {
				::_wcsupr (text_buffer);
				if (::wcsstr (text_buffer, L"TRACKBAR") != 0) {
					ctrl_type = SLIDER;
				} else if (::wcsstr (text_buffer, L"TABCONTROL") != 0) {
					ctrl_type = TAB;
				} else if (::wcsstr (text_buffer, L"LISTVIEW") != 0) {
					ctrl_type = LIST_CTRL;
				} else if (::wcsstr (text_buffer, L"MAP") != 0) {
					ctrl_type = MAP;
				} else if (::wcsstr (text_buffer, L"VIEWER") != 0) {
					ctrl_type = VIEWER;
				} else if (::wcsstr (text_buffer, L"HOTKEY") != 0) {
					ctrl_type = HOTKEY;
				} else if (::wcsstr (text_buffer, L"SHORTCUTBAR") != 0) {
					ctrl_type = SHORTCUT_BAR;
				} else if (::wcsstr (text_buffer, L"MERCHANDISE") != 0) {
					ctrl_type = MERCHANDISE_CTRL;
				} else if (::wcsstr (text_buffer, L"TREEVIEW") != 0) {
					ctrl_type = TREE_CTRL;
				} else if (::wcsicmp(text_buffer, PROGRESS_CLASSW) == 0) {
					ctrl_type = PROGRESS_BAR;
				} else if (::wcsstr (text_buffer, L"HEALTHBAR") != 0) {
					ctrl_type = HEALTH_BAR;
				}						
			}

			//
			//	Read the window text
			//			
			buffer = Skip_Dlg_Field (buffer, text_buffer, 256);

			WCHAR *string_id = ::wcsstr (text_buffer, L"IDS_");
#if defined(__vita__)
			const bool vita_had_string_id = string_id != NULL;
			WideStringClass vita_untranslated_text = text_buffer;
			StringClass vita_ascii_string_id;
			unsigned vita_translation_len = 0U;
			unsigned vita_copied_len = 0U;
			bool vita_translation_complete = true;
#endif
			if (string_id != NULL) {
				WideStringClass wide_string_id = string_id;				
				StringClass ascii_string_id;
				wide_string_id.Convert_To (ascii_string_id);
#if defined(__vita__)
				vita_ascii_string_id = ascii_string_id;
#endif
				WideStringClass translation = TRANSLATE_BY_DESC(ascii_string_id);
#if defined(__vita__)
				vita_translation_complete = Vita_Dialog_Copy_Translation(
					string_id,
					Vita_Dialog_Buffer_Remaining(text_buffer, string_id, 256U),
					translation, &vita_translation_len, &vita_copied_len);
#else
				::wcscpy (string_id, translation);
#endif
			}
#if defined(__vita__)
			if (g_vita_dialog_template_logs < 96U && (res_id == 128 || res_id == 130 || res_id == 131 || vita_had_string_id)) {
				++g_vita_dialog_template_logs;
				A30_Vita_Log("A3.5 WWUI dialog template: res=%d control=%d type=%u style=%08X rect=%d,%d %dx%d had_ids=%d desc=%s untranslated_len=%u translated_len=%u copied_len=%u final_len=%u truncated=%d log=%u/96\n",
					res_id, static_cast<int>(dlg_item_template->id), static_cast<unsigned>(ctrl_type),
					static_cast<unsigned>(dlg_item_template->style), static_cast<int>(dlg_item_template->x),
					static_cast<int>(dlg_item_template->y), static_cast<int>(dlg_item_template->cx),
					static_cast<int>(dlg_item_template->cy), vita_had_string_id ? 1 : 0,
					vita_had_string_id ? static_cast<const char *>(vita_ascii_string_id) : "literal",
					Vita_Dialog_Text_Length(vita_untranslated_text), vita_translation_len,
					vita_copied_len, Vita_Dialog_Text_Length(text_buffer),
					vita_translation_complete ? 0 : 1, g_vita_dialog_template_logs);
			}
#endif

			//
			//	Add this control definition to the list
			//
			ControlDefinitionStruct definition;
			definition.id		= (int)dlg_item_template->id;
			definition.style	= dlg_item_template->style;
			definition.x		= dlg_item_template->x;
			definition.y		= dlg_item_template->y;
			definition.cx		= dlg_item_template->cx;
			definition.cy		= dlg_item_template->cy;
			definition.type	= (CONTROL_TYPE)ctrl_type;
			definition.title	= text_buffer;
			control_list->Add (definition);

			//
			//	Skip past the extra data
			//
			WORD extra_data_size = *buffer;
			buffer ++;
			if (extra_data_size > 0) {
				buffer = (WORD *)(((char *)ALIGN_WORD_PTR(buffer)) + extra_data_size);
			}
		}
	}

	return ;
}

