#pragma once

#include "always.h"

#include <assert.h>
#include <pthread.h>

class MutexClass
{
	pthread_mutex_t Handle;
	unsigned Locked;

	bool Lock(int)
	{
		if (pthread_mutex_lock(&Handle) != 0) {
			return false;
		}
		++Locked;
		return true;
	}

	void Unlock()
	{
		assert(Locked != 0);
		--Locked;
		pthread_mutex_unlock(&Handle);
	}

public:
	enum { WAIT_INFINITE = -1 };

	explicit MutexClass(const char * = NULL) : Locked(0)
	{
		pthread_mutex_init(&Handle, NULL);
	}

	~MutexClass()
	{
		assert(Locked == 0);
		pthread_mutex_destroy(&Handle);
	}

	class LockClass
	{
		MutexClass &Mutex;
		bool FailedFlag;
	public:
		LockClass(MutexClass &mutex, int time = WAIT_INFINITE)
			: Mutex(mutex), FailedFlag(!Mutex.Lock(time)) {}
		~LockClass() { if (!FailedFlag) Mutex.Unlock(); }
		bool Failed() { return FailedFlag; }
	private:
		LockClass &operator=(const LockClass &);
	};

	friend class LockClass;
};

class CriticalSectionClass
{
	pthread_mutex_t Handle;
	unsigned Locked;

	void Lock()
	{
		pthread_mutex_lock(&Handle);
		++Locked;
	}

	void Unlock()
	{
		assert(Locked != 0);
		--Locked;
		pthread_mutex_unlock(&Handle);
	}

public:
	CriticalSectionClass() : Locked(0)
	{
		pthread_mutexattr_t attributes;
		pthread_mutexattr_init(&attributes);
		pthread_mutexattr_settype(&attributes, PTHREAD_MUTEX_RECURSIVE);
		pthread_mutex_init(&Handle, &attributes);
		pthread_mutexattr_destroy(&attributes);
	}

	~CriticalSectionClass()
	{
		assert(Locked == 0);
		pthread_mutex_destroy(&Handle);
	}

	class LockClass
	{
		CriticalSectionClass &CriticalSection;
	public:
		explicit LockClass(CriticalSectionClass &critical_section)
			: CriticalSection(critical_section) { CriticalSection.Lock(); }
		~LockClass() { CriticalSection.Unlock(); }
	private:
		LockClass &operator=(const LockClass &);
	};

	friend class LockClass;
};

class FastCriticalSectionClass
{
	pthread_mutex_t Handle;

public:
	FastCriticalSectionClass()
	{
		pthread_mutex_init(&Handle, NULL);
	}

	~FastCriticalSectionClass()
	{
		pthread_mutex_destroy(&Handle);
	}

	class LockClass
	{
		FastCriticalSectionClass &CriticalSection;
	public:
		explicit LockClass(FastCriticalSectionClass &critical_section)
			: CriticalSection(critical_section)
		{
			pthread_mutex_lock(&CriticalSection.Handle);
		}
		~LockClass()
		{
			pthread_mutex_unlock(&CriticalSection.Handle);
		}
	private:
		LockClass &operator=(const LockClass &);
	};

	friend class LockClass;
};
