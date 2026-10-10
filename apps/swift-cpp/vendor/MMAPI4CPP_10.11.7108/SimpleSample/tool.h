#pragma once

#ifdef _WIN32
#include <windows.h>
#else
#include <time.h>
#include <semaphore.h>
#include <unistd.h>
#include <fcntl.h>
#endif
#include <iostream>
#include <stdint.h>
#include <sstream>
#include <string>
#include <stdlib.h>

using namespace std;
#include "Include_MMAPI.h"
#include "Include_3rd_protobuf.h"
using namespace google;
using namespace Moomoo;

#pragma warning(disable:4100)
#pragma warning(disable:4189)

inline void ProtoBufToBodyData(const protobuf::Message& pbObj, string& strBody)
{
	protobuf::util::JsonPrintOptions ops;
	ops.add_whitespace = true;
	ops.always_print_enums_as_ints = true;

	protobuf::util::Status status = MessageToJsonString(pbObj, &strBody, ops);
	if (!status.ok())
	{
		strBody.clear();
	}
}

#if defined(_WIN32)
inline string UTF8ToGBK(const string &strUTF8)
{
	int nLen = MultiByteToWideChar(CP_UTF8, 0, strUTF8.c_str(), -1, NULL, 0);
	wchar_t* wszGBK = new wchar_t[nLen + 1];
	memset(wszGBK, 0, nLen * 2 + 2);
	MultiByteToWideChar(CP_UTF8, 0, strUTF8.c_str(), -1, wszGBK, nLen);
	nLen = WideCharToMultiByte(CP_ACP, 0, wszGBK, -1, NULL, 0, NULL, NULL);
	char* szGBK = new char[nLen + 1];
	memset(szGBK, 0, nLen + 1);
	WideCharToMultiByte(CP_ACP, 0, wszGBK, -1, szGBK, nLen, NULL, NULL);
	string strGBK(szGBK);
	if (wszGBK) delete[] wszGBK;
	if (szGBK) delete[] szGBK;
	return strGBK;
}
#endif

inline string UTF8ToLocal(const string &strUTF8)
{
#if defined(_WIN32)
	int nCodePage = GetConsoleOutputCP();
	if (nCodePage == 936)
	{
		return UTF8ToGBK(strUTF8);
	}
	else
	{
		return strUTF8;
	}
#else
	return strUTF8;
#endif
}

#define PrintRsp(str)	std::cout << str << endl;\
						string strBody;\
						ProtoBufToBodyData(stRsp, strBody);\
						std::cout << strBody << endl;

#define Print(str) std::cout << str << endl;


#define PrintError(errMsg) std::cout << "ERROR: " << __FUNCTION__ << ", retMsg = " << errMsg << std::endl;

#define PrintUTF8(errMsg) std::cout << "ERROR: " << __FUNCTION__ << ", retMsg = " << UTF8ToLocal(errMsg) << std::endl;

inline void CPSleep(int32_t nSec)
{
#ifdef _WIN32
	Sleep(nSec * 1000);
#else
	struct timespec spec;
	spec.tv_sec = nSec;
	spec.tv_nsec = 0;
	nanosleep(&spec, NULL);
#endif
}


class Semaphore
{
#if defined(_WIN32)
	HANDLE m_sema;
#else
	sem_t *m_sem;
#endif

public:
	Semaphore(int32_t initValue)
	{
#if defined(_WIN32)
		m_sema = ::CreateSemaphoreA(NULL, initValue, 0x7fffffff, NULL);
#else
        pid_t pid = getpid();
        stringstream str;
        str << "ftapi.sample." << (long)pid;
		m_sem = ::sem_open(str.str().c_str(), O_CREAT | O_EXCL, S_IRWXU, initValue);
#endif
	}

	~Semaphore()
	{
#if defined(_WIN32)
		::CloseHandle(m_sema);
#else
		::sem_close(m_sem);
#endif
	}

	void wait()
	{
#if defined(_WIN32)
		::WaitForSingleObject(m_sema, INFINITE);
#else
		::sem_wait(m_sem);
#endif
	}

	void post()
	{
#if defined(_WIN32)
		::ReleaseSemaphore(m_sema, 1, NULL);
#else
		::sem_post(m_sem);
#endif
	}

	bool trywait()
	{
#if defined(_WIN32)
		return WAIT_OBJECT_0 == ::WaitForSingleObject(m_sema, 0);
#else
		return 0 == ::sem_trywait(m_sem);
#endif
	}
};
