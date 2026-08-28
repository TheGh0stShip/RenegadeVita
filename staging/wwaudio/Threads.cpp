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
 *                 Project Name : WWAudio                                                      *
 *                                                                                             *
 *                     $Archive:: /Commando/Code/WWAudio/Threads.cpp                                                                                                                                                                                                                                                                                                                               $Modtime:: 7/17/99 3:32p                                               $*
 *                                                                                             *
 *                    $Revision:: 9                                                           $*
 *                                                                                             *
 *---------------------------------------------------------------------------------------------*
 * Functions:                                                                                  *
 * - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - */


#include "Threads.h"
#include "refcount.h"
#include "Utils.h"
#if defined(_UNIX)
#include <errno.h>
#include <pthread.h>
#include <time.h>
#else
#include <Process.h>
#endif
#include "wwdebug.h"
#include "systimer.h"

#if defined(_UNIX)
static pthread_t g_WWAudioReleaseThread;
static pthread_mutex_t g_WWAudioReleaseSignalMutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t g_WWAudioReleaseSignal = PTHREAD_COND_INITIALIZER;
static bool g_WWAudioReleaseStop = false;
#endif

///////////////////////////////////////////////////////////////////////////////////////////
//	Static member initialization
///////////////////////////////////////////////////////////////////////////////////////////
WWAudioThreadsClass::DELAYED_RELEASE_INFO *	WWAudioThreadsClass::m_ReleaseListHead	= NULL;
CriticalSectionClass		WWAudioThreadsClass::m_ListMutex;
HANDLE						WWAudioThreadsClass::m_hDelayedReleaseThread	= (HANDLE)-1;
HANDLE						WWAudioThreadsClass::m_hDelayedReleaseEvent	= (HANDLE)-1;
CriticalSectionClass		WWAudioThreadsClass::m_CriticalSection;
bool							WWAudioThreadsClass::m_IsFlushing				= false;

///////////////////////////////////////////////////////////////////////////////////////////
//
//	WWAudioThreadsClass
//
///////////////////////////////////////////////////////////////////////////////////////////
WWAudioThreadsClass::WWAudioThreadsClass (void)
{
	return ;
}


///////////////////////////////////////////////////////////////////////////////////////////
//
//	~WWAudioThreadsClass
//
///////////////////////////////////////////////////////////////////////////////////////////
WWAudioThreadsClass::~WWAudioThreadsClass (void)
{
	return ;
}

///////////////////////////////////////////////////////////////////////////////////////////
//
//	Create_Delayed_Release_Thread
//
///////////////////////////////////////////////////////////////////////////////////////////
HANDLE
WWAudioThreadsClass::Create_Delayed_Release_Thread (LPVOID param)
{
	//
	//	If the thread isn't already running, then
	//
	if (m_hDelayedReleaseThread == (HANDLE)-1) {
#if defined(_UNIX)
		pthread_mutex_lock (&g_WWAudioReleaseSignalMutex);
		g_WWAudioReleaseStop = false;
		pthread_mutex_unlock (&g_WWAudioReleaseSignalMutex);
		const int create_result = pthread_create (&g_WWAudioReleaseThread, NULL,
			[](void *thread_param) -> void * {
				WWAudioThreadsClass::Delayed_Release_Thread_Proc (thread_param);
				return NULL;
			}, param);
		if (create_result == 0) {
			m_hDelayedReleaseEvent = (HANDLE)1;
			m_hDelayedReleaseThread = (HANDLE)1;
		} else {
			m_hDelayedReleaseEvent = (HANDLE)-1;
			m_hDelayedReleaseThread = (HANDLE)-1;
		}
#else
		m_hDelayedReleaseEvent	= ::CreateEvent (NULL, FALSE, FALSE, NULL);
		m_hDelayedReleaseThread = (HANDLE)::_beginthread (Delayed_Release_Thread_Proc, 0, param);
#endif
	}

	return m_hDelayedReleaseThread;
}


///////////////////////////////////////////////////////////////////////////////////////////
//
//	End_Delayed_Release_Thread
//
///////////////////////////////////////////////////////////////////////////////////////////
void
WWAudioThreadsClass::End_Delayed_Release_Thread (DWORD timeout)
{
#if defined(_UNIX)
	(void)timeout;
#endif
	//
	//	If the thread is running, then wait for it to finish
	//
	if (m_hDelayedReleaseThread != (HANDLE)-1) {
#if defined(_UNIX)
		pthread_mutex_lock (&g_WWAudioReleaseSignalMutex);
		g_WWAudioReleaseStop = true;
		pthread_cond_broadcast (&g_WWAudioReleaseSignal);
		pthread_mutex_unlock (&g_WWAudioReleaseSignalMutex);
		pthread_join (g_WWAudioReleaseThread, NULL);
#else
		::SetEvent (m_hDelayedReleaseEvent);
		::WaitForSingleObject (m_hDelayedReleaseThread, timeout);
#endif

		m_hDelayedReleaseEvent	= (HANDLE)-1;
		m_hDelayedReleaseThread	= (HANDLE)-1;
	}

	return ;
}


///////////////////////////////////////////////////////////////////////////////////////////
//
//	Add_Delayed_Release_Object
//
///////////////////////////////////////////////////////////////////////////////////////////
void
WWAudioThreadsClass::Add_Delayed_Release_Object
(
	RefCountClass *	object,
	DWORD					delay
)
{
	if (m_IsFlushing) {
		REF_PTR_RELEASE (object);
	} else {

		//
		//	Make sure we have a thread running that will handle
		// the operation for us.
		//
		if (m_hDelayedReleaseThread == (HANDLE)-1) {
			Create_Delayed_Release_Thread ();
		}

		//
		//	Wait for the release thread to finish using the
		// list pointer
		//
		{
			CriticalSectionClass::LockClass lock(m_ListMutex);

			//
			//	Create a new delay-information structure and
			//	add it to our list
			//
			DELAYED_RELEASE_INFO *info = new DELAYED_RELEASE_INFO;
			info->object	= object;
			info->time		= TIMEGETTIME () + delay;
			info->next		= m_ReleaseListHead;
			info->prev		= NULL;

			if (info->next != NULL) {
				info->next->prev = info;
			}

			m_ReleaseListHead = info;
		}
	}

	return ;
}


///////////////////////////////////////////////////////////////////////////////////////////
//
//	Flush_Delayed_Release_Objects
//
///////////////////////////////////////////////////////////////////////////////////////////
void
WWAudioThreadsClass::Flush_Delayed_Release_Objects (void)
{
	CriticalSectionClass::LockClass lock(m_ListMutex);
	m_IsFlushing = true;

	//
	//	Loop through all the objects in our delay list, and
	// free them now.
	//
	DELAYED_RELEASE_INFO *info = NULL;
	DELAYED_RELEASE_INFO *next = NULL;
	for (info = m_ReleaseListHead; info != NULL; info = next) {
		next = info->next;

		//
		//	Free the object
		//
		REF_PTR_RELEASE (info->object);
		SAFE_DELETE (info);
	}

	m_ReleaseListHead = NULL;
	return ;
}


///////////////////////////////////////////////////////////////////////////////////////////
//
//	Delayed_Release_Thread_Proc
//
///////////////////////////////////////////////////////////////////////////////////////////
void __cdecl
WWAudioThreadsClass::Delayed_Release_Thread_Proc (LPVOID /*param*/)
{
	const DWORD base_timeout = 2000;
	DWORD timeout = base_timeout + rand () % 1000;

	//
	//	Keep looping forever until we are singalled to quit (or an error occurs)
	//
#if defined(_UNIX)
	for (;;) {
		struct timespec deadline;
		clock_gettime (CLOCK_REALTIME, &deadline);
		deadline.tv_sec += timeout / 1000;
		deadline.tv_nsec += (long)(timeout % 1000) * 1000000L;
		if (deadline.tv_nsec >= 1000000000L) {
			deadline.tv_sec ++;
			deadline.tv_nsec -= 1000000000L;
		}
		pthread_mutex_lock (&g_WWAudioReleaseSignalMutex);
		while (!g_WWAudioReleaseStop) {
			const int wait_result = pthread_cond_timedwait (
				&g_WWAudioReleaseSignal, &g_WWAudioReleaseSignalMutex, &deadline);
			if (wait_result == ETIMEDOUT) break;
		}
		const bool stop_requested = g_WWAudioReleaseStop;
		pthread_mutex_unlock (&g_WWAudioReleaseSignalMutex);
		if (stop_requested) break;
#else
	while (::WaitForSingleObject (m_hDelayedReleaseEvent, timeout) == WAIT_TIMEOUT) {
#endif

		{
			CriticalSectionClass::LockClass lock(m_ListMutex);

			//
			//	Loop through all the objects in our delay list, and
			// free any that have expired.
			//
			DWORD current_time			= TIMEGETTIME ();
			DELAYED_RELEASE_INFO *curr = NULL;
			DELAYED_RELEASE_INFO *prev	= NULL;
			DELAYED_RELEASE_INFO *next	= NULL;
			for (curr = m_ReleaseListHead; curr != NULL; curr = next) {
				next = curr->next;
				prev = curr->prev;

				//
				//	If the time has expired, free the object
				//
				if ((S32)(current_time - curr->time) >= 0) {

					//
					//	Unlink the object
					//
					if (curr == m_ReleaseListHead) {
						m_ReleaseListHead = next;
					}

					if (prev != NULL) {
						prev->next = next;
					}

					if (next != NULL) {
						next->prev = prev;
					}

					//
					//	Free the object
					//
					REF_PTR_RELEASE (curr->object);
					SAFE_DELETE (curr);
				}
			}
		}

		//
		//	To avoid 'periodic' releases, randomize our timeout
		//
		timeout = base_timeout + rand () % 1000;
	}

	Flush_Delayed_Release_Objects ();
	return ;
}

/*
///////////////////////////////////////////////////////////////////////////////////////////
//
//	Begin_Modify_List
//
///////////////////////////////////////////////////////////////////////////////////////////
bool
WWAudioThreadsClass::Begin_Modify_List (void)
{
	bool retval = false;

	//
	//	Wait for up to one second to modify the list object
	//
	if (m_ListMutex != NULL) {
		retval = (::WaitForSingleObject (m_ListMutex, 1000) == WAIT_OBJECT_0);
		WWASSERT (retval);
	}

	return retval;
}


///////////////////////////////////////////////////////////////////////////////////////////
//
//	End_Modify_List
//
///////////////////////////////////////////////////////////////////////////////////////////
void
WWAudioThreadsClass::End_Modify_List (void)
{
	//
	//	Release this thread's hold on the mutex object.
	//
	if (m_ListMutex != NULL) {
		::ReleaseMutex (m_ListMutex);
	}

	return ;
}
*/
