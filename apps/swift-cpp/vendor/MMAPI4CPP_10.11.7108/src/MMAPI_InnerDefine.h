// Copyright 2026 Moomoo
#pragma once

#include "MMAPI_Define.h"
using namespace Moomoo;

// 平台
#ifdef _WIN32
#	define OM_Win32
#endif

#ifdef __linux__
#	define OM_Linux
#endif

#ifdef __APPLE__
#	define OM_Apple
#	include <TargetConditionals.h>
#	if (defined(TARGET_OS_IPHONE) && TARGET_OS_IPHONE) || (defined(TARGET_IPHONE_SIMULATOR) && TARGET_IPHONE_SIMULATOR)
#		define OM_Apple_iOS
#	else
#		define OM_Apple_Mac
#	endif
#endif

#ifdef __ANDROID__
#	define OM_Android
#endif

// OM_Debug - Win32、Linux、Apple、Android
#if (defined(OM_Win32) && defined(_DEBUG))
#	define OM_Debug
#endif

#if (defined(OM_Linux) && defined(DEBUG) && DEBUG)
#	define OM_Debug
#endif

#if (defined(OM_Apple) && defined(DEBUG) && DEBUG)
#	define OM_Debug
#endif

#if (defined(OM_Android) && !defined(NDEBUG))
#	define OM_Debug
#endif

// 某些平台没有定义NDEBUG，会导致assert始终是Debug模式，这里做保护性定义，避免Release版本因assert还在工作而崩溃
#if (!defined(OM_Debug) && !defined(NDEBUG))
#	define NDEBUG
#endif

//类型
typedef std::string Buf_t;
typedef std::string Str_t;

// 断言
#ifdef OM_Debug
#	ifdef OM_Win32
#		define OMWarn (__debugbreak(), 0) // Win32
#	else
#		ifdef OM_Apple
#			define OMWarn { assert(false); } // Apple
#		else 
#			define OMWarn
#		endif
#	endif
#else
#	define OMWarn 
#endif

//工具
#define IsNullPtr(p) ((p) == nullptr)
#define IsNotNullPtr(p) (!IsNullPtr(p))

#define If_Do(b, d) { if (b) { d; } } // d不能加括号
#define If_Return(b, r) { if (b) { return r; } } // r不被括起来(r)，是为了支持不传r，等同If_ReturnVoid
#define If_ReturnVoid(b) { if (b) { return; } }

#define If_OMWarn(b) { if (b) { OMWarn; } }
#define If_OMWarn_Return(b, r) { if (b) { OMWarn; return r; } } // r不被括起来(r)，是为了支持不传r，等同If_OMWarn_ReturnVoid
#define If_Do_OMWarn_Return(b, d, r) { if (b) { d; OMWarn; return r; } }

#define ContainerSize(container) ((i32_t)(container).size())

#define Foreach_Iter(iterName, container) for (auto iterName = (container).begin(); iterName != (container).end(); iterName++)