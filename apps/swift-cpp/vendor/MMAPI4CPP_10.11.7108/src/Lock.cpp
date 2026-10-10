// Copyright 2026 Moomoo
#include "Lock.h"

#ifdef OM_Win32

CLock::CLock(void)
{
	If_OMWarn(!::InitializeCriticalSectionAndSpinCount(&m_criticalSection, 0x00000400));
}

CLock::~CLock(void)
{
	DeleteCriticalSection(&m_criticalSection);
}

void CLock::Lock()
{
	EnterCriticalSection(&m_criticalSection);
}

void CLock::UnLock()
{
	LeaveCriticalSection(&m_criticalSection);
}

#else

CLock::CLock(void)
{
	If_OMWarn(pthread_mutexattr_init(&m_mutexAttr) != 0);
	If_OMWarn(pthread_mutexattr_settype(&m_mutexAttr, PTHREAD_MUTEX_RECURSIVE) != 0);
	If_OMWarn(pthread_mutex_init(&m_mutex, &m_mutexAttr) != 0);
}

CLock::~CLock(void)
{
	pthread_mutex_destroy(&m_mutex);
	pthread_mutexattr_destroy(&m_mutexAttr);
}

void CLock::Lock()
{
	pthread_mutex_lock(&m_mutex);
}

void CLock::UnLock()
{
	pthread_mutex_unlock(&m_mutex);
}

#endif

CLock_Auto::CLock_Auto(CLock* pLock)
{
	If_OMWarn(IsNullPtr(pLock));

	m_pLock = pLock;
	If_Do(IsNotNullPtr(m_pLock), m_pLock->Lock());
}

CLock_Auto::~CLock_Auto(void)
{
	If_Do(IsNotNullPtr(m_pLock), m_pLock->UnLock());
}
