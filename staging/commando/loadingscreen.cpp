/*
**	Command & Conquer Renegade(tm)
**	Copyright 2025 Electronic Arts Inc.
**
**	This program is free software: you can redistribute it and/or modify
**	it under the terms of the GNU General Public License as published by
**	the Free Software Foundation, either version 3 of the License, or
**	(at your option) any later version.
*/

#include "loadingscreen.h"

#include "campaign.h"
#include "combat.h"
#include "cnetwork.h"
#include "console.h"
#include "a31_console_stub.h"
#include "debug.h"
#include "render2d.h"
#include "saveloadstatus.h"
#include "stylemgr.h"
#include "timemgr.h"
#include "translatedb.h"
#include "ww3d.h"
#include "wwmath.h"
#include "wwmemlog.h"

#include <stdio.h>
#include <string.h>
#if defined(__vita__)
#include <psp2/kernel/processmgr.h>
#endif

LoadingScreenClass::LoadingScreenClass()
{
	int color = 0xFFFFFFFF;

	WWMEMLOG(MEM_GAMEDATA);

	backdropText.Set_Texture_Size_Hint( 256 );
	backdropText2.Set_Texture_Size_Hint( 256 );
#if RENEGADE_VITA_M00_DEMO
	statusText.Set_Texture_Size_Hint( 256 );
#endif

	LoadTime = 0.001f;
	LoadPercentage = 0;
	LoadPercentageDrawn = 0;
	LoadPercentageRate = 0;
	PresentationProgress = -1.0f;
	LastPresentationUs = 0;
	LoadPercentageClamp = 0;
	LastLoadProgress = -1;
	LastConsolePercent = -1;
	StatusTextBuffer[0] = '\0';

	FontCharsClass *font	= StyleMgrClass::Peek_Font( StyleMgrClass::FONT_INGAME_TXT );
	backdropText.Set_Font( font );
#if RENEGADE_VITA_M00_DEMO
	statusText.Set_Font( font );
#endif

	font = StyleMgrClass::Peek_Font( StyleMgrClass::FONT_INGAME_BIG_TXT );
	backdropText2.Set_Font( font );

	// Parse Descriptions
	int count = CampaignManager::Get_Backdrop_Description_Count();
	for ( int i = 0; i < count; i++ ) {
		const char * read = CampaignManager::Get_Backdrop_Description( i );
//		Debug_Say(( "Parse %s\n", read ));
		StringClass desc = read;
		while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
		while ( desc.Get_Length() && desc[desc.Get_Length()-1]<=' ' ) desc.Erase(desc.Get_Length()-1, 1 );

		// Parse Big Translated Text
		if ( ::strnicmp( "Text2", desc, 5 ) == 0 ) {
			desc.Erase( 0, 5 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
			float x,y;
			::sscanf( desc, "%f,%f,", &x, &y );
			const char * str = ::strchr( desc, ',' );
			if ( str != NULL ) {
				str = ::strchr( str+1, ',' );
				if ( str != NULL ) {
					WideStringClass wide_str = TranslateDBClass::Get_String( str+1 );
					backdropText2.Build_Sentence( wide_str );
					// Scale
					x *= Render2DClass::Get_Screen_Resolution().Right / 640.0f;
					y *= Render2DClass::Get_Screen_Resolution().Bottom / 480.0f;
					backdropText2.Set_Location( Vector2( (int)x, (int)y ) );
					backdropText2.Draw_Sentence( color );
					color=0xFFFFFFFF;
					backdropText2.Set_Wrapping_Width( 0 );
				}
			}
		}

		// Parse Translated Text
		if ( ::strnicmp( "Text", desc, 4 ) == 0 ) {
			desc.Erase( 0, 4 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
			float x,y;
			::sscanf( desc, "%f,%f,", &x, &y );
			const char * str = ::strchr( desc, ',' );
			if ( str != NULL ) {
				str = ::strchr( str+1, ',' );
				if ( str != NULL ) {
					WideStringClass wide_str = TranslateDBClass::Get_String( str+1 );
					backdropText.Build_Sentence( wide_str );
					// Scale
					x *= Render2DClass::Get_Screen_Resolution().Right / 640.0f;
					y *= Render2DClass::Get_Screen_Resolution().Bottom / 480.0f;
					backdropText.Set_Location( Vector2( (int)x, (int)y ) );
					backdropText.Draw_Sentence( color );
					color=0xFFFFFFFF;
					backdropText.Set_Wrapping_Width( 0 );
				}
			}
		}

		// Set Big Wrapping Width
		if ( ::strnicmp( "Wrap2", desc, 5 ) == 0 ) {
			desc.Erase( 0, 5 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
			float w;
			::sscanf( desc, "%f,", &w );
			// Scale
			w *= Render2DClass::Get_Screen_Resolution().Right / 640.0f;
			backdropText2.Set_Wrapping_Width( w );
		}

		// Set Wrapping Width
		if ( ::strnicmp( "Wrap", desc, 4 ) == 0 ) {
			desc.Erase( 0, 4 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
			float w;
			::sscanf( desc, "%f,", &w );
			// Scale
			w *= Render2DClass::Get_Screen_Resolution().Right / 640.0f;
			backdropText.Set_Wrapping_Width( w );
		}

		// Parse test Text
		if ( ::strnicmp( "Test", desc, 4 ) == 0 ) {
			desc.Erase( 0, 4 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
			float x,y;
			::sscanf( desc, "%f,%f,", &x, &y );
			const char * str = ::strchr( desc, ',' );
			if ( str != NULL ) {
				str = ::strchr( str+1, ',' );
				if ( str != NULL ) {
					WideStringClass wide_str;
					wide_str.Convert_From( str+1 );
					backdropText.Build_Sentence( wide_str );
					// Scale
					x *= Render2DClass::Get_Screen_Resolution().Right / 640.0f;
					y *= Render2DClass::Get_Screen_Resolution().Bottom / 480.0f;
					backdropText.Set_Location( Vector2( (int)x, (int)y ) );
					backdropText.Draw_Sentence( color );
					color=0xFFFFFFFF;
					backdropText.Set_Wrapping_Width( 0 );
				}
			}
		}

		// Parse back model
		if ( ::strnicmp( "Model", desc, 5 ) == 0 ) {
			desc.Erase( 0, 5 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );

			backdrop.Set_Model(desc);
			StringClass anim_name;
			anim_name.Format( "%s.%s", static_cast<const char *>(desc), static_cast<const char *>(desc) );
			backdrop.Set_Animation( anim_name );
			backdrop.Set_Animation_Percentage( 0 );
		}

		if ( ::strnicmp( "Color", desc, 5 ) == 0 ) {
			desc.Erase( 0, 5 );
			while ( desc.Get_Length() && desc[0] <= ' ' ) desc.Erase( 0, 1 );
			float r,g,b;
			::sscanf( desc, "%f,%f,%f", &r, &g, &b );

			Vector3 c( r/255.0f, g/255.0f, b/255.0f );
			color = c.Convert_To_ARGB();
		}


	}
	SaveLoadStatus::Reset_Status_Count();
}

LoadingScreenClass::~LoadingScreenClass()
{
}

bool LoadingScreenClass::Has_Backdrop_Model( void ) const
{
	return backdrop.Peek_Model() != NULL;
}

float	LoadingScreenClass::Get_Predicted_Percentage( int state )
{
	switch( state )
	{
#define	TOTAL	(18.0f)
		case 0:	return 0.1f / TOTAL;
		case 1:	return 0.2f / TOTAL;
		case 2:	return 0.3f / TOTAL;
		case 3:	return 0.7f / TOTAL;
		case 4:	return 3.8f / TOTAL;
		case 5:	return 15.5f / TOTAL;
		case 6:	return 17.6f / TOTAL;
		default:	return 1.0f;
	}
}

void LoadingScreenClass::Update_Status_Text(void)
{
	StringClass status;
	SaveLoadStatus::Get_Status_Text(status, 0);
	if (status.Get_Length() == 0) {
		SaveLoadStatus::Get_Status_Text(status, 1);
	}
	if (status.Get_Length() == 0) {
		status = "Loading M00 Tutorial";
	}

	int percent = (int)(LoadPercentageDrawn * 100.0f);
	if (percent < 0) percent = 0;
	if (percent > 100) percent = 100;
	char text[128];
	::snprintf(text, sizeof(text), "%s %d%%", (const char *)status, percent);
	text[sizeof(text) - 1] = '\0';
	if (::strcmp(StatusTextBuffer, text) == 0) {
		return;
	}
	::snprintf(StatusTextBuffer, sizeof(StatusTextBuffer), "%s", text);
	StatusTextBuffer[sizeof(StatusTextBuffer) - 1] = '\0';

	WideStringClass wide_status;
	wide_status.Convert_From(StatusTextBuffer);
	const RectClass &screen = Render2DClass::Get_Screen_Resolution();
	statusText.Reset();
	statusText.Set_Wrapping_Width(screen.Right - 64.0f);
	statusText.Build_Sentence(wide_status);
	statusText.Set_Location(Vector2(32, (int)(screen.Bottom - 42.0f)));
	statusText.Draw_Sentence(0xFFFFFFFF);
}

void LoadingScreenClass::Set_Presentation_Progress(float progress)
{
	PresentationProgress = WWMath::Clamp(progress, 0.0f, 1.0f);
}

void LoadingScreenClass::Render(bool update_network)
{
	TimeManager::Update_Frame_Time();
	float presentation_seconds = TimeManager::Get_Frame_Seconds();
#if defined(__vita__)
	// Loading presentation must not stop when Combat's simulation clock pauses.
	const unsigned long long now = sceKernelGetProcessTimeWide();
	presentation_seconds = LastPresentationUs != 0 && now >= LastPresentationUs ?
		WWMath::Clamp(float(now - LastPresentationUs) / 1000000.0f, 0.0f, 0.25f) : 0.0f;
	LastPresentationUs = now;
#endif
	LoadTime += presentation_seconds;

	int &last_count = LastLoadProgress;
	int &_last_percent_drawn = LastConsolePercent;
	if ( last_count != CombatManager::Get_Load_Progress() ) {
		last_count = CombatManager::Get_Load_Progress();
		Debug_Say(( " ****** Status Count %d at %f\n", last_count, LoadTime ));
		LoadPercentage = Get_Predicted_Percentage( last_count );
		LoadPercentageRate = LoadPercentage / LoadTime;
		LoadPercentageClamp = Get_Predicted_Percentage( last_count+1 );
	}

	LoadPercentage += LoadPercentageRate * presentation_seconds;
	LoadPercentage = WWMath::Clamp( LoadPercentage, 0, LoadPercentageClamp );
	if ( LoadPercentage > LoadPercentageDrawn ) {
		LoadPercentageDrawn = LoadPercentage;
	} else {
		LoadPercentageDrawn += ( LoadPercentage - LoadPercentageDrawn ) * 0.1f;
	}
#if defined(__vita__) && RENEGADE_VITA_M00_DEMO
	// Native post-load texture and scene preparation owns the final ten percent.
	const float predicted = LoadPercentageDrawn;
	LoadPercentageDrawn = PresentationProgress >= 0.0f ?
		PresentationProgress : predicted * 0.90f;
#endif
	backdrop.Set_Animation_Percentage( LoadPercentageDrawn );
#if RENEGADE_VITA_M00_DEMO
	Update_Status_Text();
#endif
#if defined(__vita__) && RENEGADE_VITA_M00_DEMO
	LoadPercentageDrawn = predicted;
#endif
	if (ConsoleBox.Is_Exclusive() && _last_percent_drawn != LoadPercentageDrawn) {
		_last_percent_drawn = LoadPercentageDrawn;
		ConsoleBox.Print("Load %d%% complete\r", (int)(LoadPercentageDrawn * 100.0f));
	}

   WW3D::Begin_Render( true, true, Vector3(0.0f,0.0f,0.0f), update_network ? &cNetwork::Update : NULL);

	backdrop.Render();
	backdropText.Render();
	backdropText2.Render();
#if RENEGADE_VITA_M00_DEMO
	statusText.Render();
#endif

#if 0
	StringClass txt=SaveLoadStatus::Get_Status_Text(0);
	txt=SaveLoadStatus::Get_Status_Text(1);
#endif

	WW3D::End_Render();
}

void * Commando_Create_Original_Loading_Screen( void )
{
	return new LoadingScreenClass;
}

void Commando_Render_Original_Loading_Screen( void * screen, bool update_network )
{
	if ( screen != NULL ) {
		((LoadingScreenClass *)screen)->Render( update_network );
	}
}

bool Commando_Original_Loading_Screen_Has_Backdrop_Model( void * screen )
{
	return screen != NULL &&
		((LoadingScreenClass *)screen)->Has_Backdrop_Model();
}

void Commando_Set_Original_Loading_Progress(void *screen, float progress)
{
	if (screen != NULL) {
		((LoadingScreenClass *)screen)->Set_Presentation_Progress(progress);
	}
}

void Commando_Destroy_Original_Loading_Screen( void * screen )
{
	delete ((LoadingScreenClass *)screen);
}
