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

/******************************************************************************
*
* FILE
*     $Archive: /Commando/Code/Commando/DlgMPTeamSelect.h $
*
* DESCRIPTION
*     Multiplayer team selection dialog.
*
* PROGRAMMER
*     Denzil E. Long, Jr.
*     $Author: Denzil_l $
*
* VERSION INFO
*     $Revision: 8 $
*     $Modtime: 2/11/02 11:28a $
*
******************************************************************************/

#ifndef __DLGMPTEAMSELECT_H__
#define __DLGMPTEAMSELECT_H__

#include "playermanager.h"
#include <WWUI\MenuDialog.h>
#include <WWLib\Notify.h>
#include <WWLib\Signaler.h>
#if !defined(RENEGADE_VITA_LAN_FRONTEND)
#include <WWOnline\RefPtr.h>
#include "WOLGameInfo.h"

namespace WWOnline
{
class Session;
class ChannelEvent;
class UserEvent;
class GameOptionsMessage;
};
#endif

class cPlayer;

typedef TypedEventPair<bool, int> MPChooseTeamSignal;

class DlgMPTeamSelect :
		public MenuDialogClass,
		protected Signaler<MPChooseTeamSignal>,
#if !defined(RENEGADE_VITA_LAN_FRONTEND)
		protected Observer<WWOnline::ChannelEvent>,
		protected Observer<WWOnline::UserEvent>,
		protected Observer<WWOnline::GameOptionsMessage>,
#endif
		protected Observer<PlayerMgrEvent>
	{
	public:
		static void DoDialog(Signaler<MPChooseTeamSignal>& target);

	protected:
		DlgMPTeamSelect(void);
		~DlgMPTeamSelect();

		bool FinalizeCreate(void);

		void On_Init_Dialog(void);
		void On_Frame_Update(void);
		void On_Command(int ctrlID, int message, DWORD param);
		void On_Last_Menu_Ending(void);

		void InitSideChoice(int sidePref);
		void SelectSideChoice(int side);
		int GetSideChoice(void);

		void ShowTimeRemaining(float remainingSecond);
		bool FindPlayerInListCtrl(const WCHAR* name, ListCtrlClass*& outList, int& outIndex);

#if !defined(RENEGADE_VITA_LAN_FRONTEND)
		void RequestWOLGameInfo(void);
		void HandleNotification(WWOnline::ChannelEvent&);
		void HandleNotification(WWOnline::UserEvent&);
		void HandleNotification(WWOnline::GameOptionsMessage&);
		static void ProcessWOLGameInfo(DlgMPTeamSelect& dialog, const char* data);
		static void ProcessWOLTeamInfo(DlgMPTeamSelect& dialog, const char* data);
		static void ProcessWOLPlayerInfo(DlgMPTeamSelect& dialog, const char* data);
#endif
		void HandleNotification(PlayerMgrEvent&);

		void PopulateWithLANPlayers(void);
		void AddLANPlayerInfo(cPlayer* lanPlayer);
		void RemoveLANPlayerInfo(cPlayer* lanPlayer);

	protected:
#if !defined(RENEGADE_VITA_LAN_FRONTEND)
		bool mWOLGame;
#endif
		bool mCanChoose;
		float mTimeRemaining;

#if !defined(RENEGADE_VITA_LAN_FRONTEND)
		RefPtr<WWOnline::Session> mWOLSession;
		WOLGameInfo mGameInfo;
#endif
	};

#endif // __DLGMPTEAMSELECT_H__
