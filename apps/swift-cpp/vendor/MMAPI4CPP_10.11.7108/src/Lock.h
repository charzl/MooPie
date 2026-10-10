// Copyright 2026 Moomoo
#pragma once
#include "MMAPI_InnerDefine.h"

#ifdef OM_Win32
#include <windows.h>
#else
#include <pthread.h>
#endif

class CLock
{
public:
	CLock(void);
	~CLock(void);

public:
	void Lock();
	void UnLock();

private:
#ifdef OM_Win32
	CRITICAL_SECTION m_criticalSection{};
#else
	pthread_mutexattr_t m_mutexAttr{};
	pthread_mutex_t m_mutex{};
#endif
};

class CLock_Auto
{
public:
	CLock_Auto(CLock* pLock);
	~CLock_Auto(void);

private:
	CLock* m_pLock{ nullptr };
};

#define CAutoLock(lock) CLock_Auto autoLock_##lock(&lock)
