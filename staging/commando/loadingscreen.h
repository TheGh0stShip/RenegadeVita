/*
**	Command & Conquer Renegade(tm)
**	Copyright 2025 Electronic Arts Inc.
**
**	This program is free software: you can redistribute it and/or modify
**	it under the terms of the GNU General Public License as published by
**	the Free Software Foundation, either version 3 of the License, or
**	(at your option) any later version.
*/

#ifndef LOADINGSCREEN_H
#define LOADINGSCREEN_H

#include "menubackdrop.h"
#include "render2dsentence.h"

class LoadingScreenClass
{
	MenuBackDropClass	backdrop;
	Render2DSentenceClass backdropText;
	Render2DSentenceClass backdropText2;	// The BIG text
	Render2DSentenceClass statusText;
	float	LoadTime;
	float	LoadPercentage;
	float	LoadPercentageDrawn;
	float	LoadPercentageClamp;
	float	LoadPercentageRate;
	float PresentationProgress;
	unsigned long long LastPresentationUs;
	char	StatusTextBuffer[128];
	int LastLoadProgress;
	int LastConsolePercent;

	void Update_Status_Text(void);

public:
	LoadingScreenClass();
	~LoadingScreenClass();

	bool Has_Backdrop_Model( void ) const;
	float	Get_Predicted_Percentage( int state );
	void Render(bool update_network = false);
	void Set_Presentation_Progress(float progress);
};

void * Commando_Create_Original_Loading_Screen( void );
void Commando_Render_Original_Loading_Screen( void * screen, bool update_network );
bool Commando_Original_Loading_Screen_Has_Backdrop_Model( void * screen );
void Commando_Destroy_Original_Loading_Screen( void * screen );
void Commando_Set_Original_Loading_Progress(void *screen, float progress);

#endif // LOADINGSCREEN_H
