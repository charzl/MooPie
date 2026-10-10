// Copyright 2026 Moomoo
#pragma once

#include <cstdint>
#include <cstring>
#include <string>
#include <map>
#include <utility>

// ---------------------------------------------------------------------------
// 整型别名（供本目录内部代码使用）
// ---------------------------------------------------------------------------
typedef char i8_t;
typedef short i16_t;
typedef int i32_t;
typedef unsigned char u8_t;
typedef unsigned short u16_t;
typedef unsigned int u32_t;
#if defined(__linux__)
typedef int64_t i64_t;
typedef uint64_t u64_t;
#else
typedef long long i64_t;
typedef unsigned long long u64_t;
#endif

// ---------------------------------------------------------------------------
// 断言/告警（无对应日志系统，降级为 no-op 占位）
// ---------------------------------------------------------------------------
#define API_Warn ((void)0)

// ---------------------------------------------------------------------------
// 指针判空
// ---------------------------------------------------------------------------
#define API_IsNullPtr(p) ((p) == nullptr)
#define API_IsNotNullPtr(p) ((p) != nullptr)

// 数据缓冲区判空（指针为空或长度非正）
#define API_IsNullData(p, nLen) ((p) == nullptr || (nLen) <= 0)

// ---------------------------------------------------------------------------
// 条件返回/执行
// ---------------------------------------------------------------------------
#define API_If_Return(b, r) { if (b) { return r; } }
#define API_If_ReturnVoid(b) { if (b) { return; } }
#define API_If_Do(b, d) { if (b) { d; } }
#define API_If_Warn_Return(b, r) { if (b) { API_Warn; return r; } }
#define API_If_Warn_ReturnVoid(b) { if (b) { API_Warn; return; } }
#define API_If_Do_Warn_Return(b, d, r) { if (b) { d; API_Warn; return r; } }

// ---------------------------------------------------------------------------
// 资源释放（delete 后置空）
// ---------------------------------------------------------------------------
template <typename T>
inline void APIDeleteP(T*& p)
{
	if (p != nullptr)
	{
		delete p;
		p = nullptr;
	}
}

template <typename T>
inline void APIDelete1D(T*& p)
{
	if (p != nullptr)
	{
		delete[] p;
		p = nullptr;
	}
}

#define API_DeleteP(p) APIDeleteP(p)
#define API_Delete1D(p) APIDelete1D(p)

// ---------------------------------------------------------------------------
// 数组元素个数
// ---------------------------------------------------------------------------
template <typename T, i32_t N>
inline i32_t APIArrayVarSize(const T (&)[N])
{
	return N;
}

#define API_ArrayVarSize(arrayVar) APIArrayVarSize(arrayVar)

// ---------------------------------------------------------------------------
// 位拼接为 u64（低 32 位 low，高 32 位 hi）
// ---------------------------------------------------------------------------
#define API_MakeToU64(low, hi) ((u64_t)(((u32_t)(low)) | ((u64_t)((u32_t)(hi))) << 32))

// ---------------------------------------------------------------------------
// 字符串判空
// ---------------------------------------------------------------------------
inline bool APIIsNullOrEmptyStr(const char* str)
{
	return (str == nullptr || *str == '\0');
}

#define API_IsNullOrEmptyStr(s) APIIsNullOrEmptyStr(s)

// 锁直接用 std::recursive_mutex + std::lock_guard，不再定义类型/宏。

// ---------------------------------------------------------------------------
// std::map 常用操作（替代 Map_Insert / Map_Erase / IfTreeFind_Iter / Foreach_Iter）
// ---------------------------------------------------------------------------
template <typename TMap, typename TKey, typename TVal>
inline bool APIMapInsert(TMap& theMap, const TKey& theKey, const TVal& theValue)
{
	return theMap.insert(std::make_pair(theKey, theValue)).second;
}

template <typename TMap, typename TKey>
inline bool APIMapErase(TMap& theMap, const TKey& theKey)
{
	auto iterFind = theMap.find(theKey);
	if (iterFind != theMap.end())
	{
		theMap.erase(iterFind);
		return true;
	}
	return false;
}

#define API_IfTreeFind_Iter(iterName, container, key) auto iterName = (container).find(key); if (iterName != (container).end())
#define API_Foreach_Iter(iterName, container) for (auto iterName = (container).begin(); iterName != (container).end(); ++iterName)

// ---------------------------------------------------------------------------
// 断线类型（取值与 APITcpClientDisConnectType 一一对应）
// ---------------------------------------------------------------------------
enum APITcpDisConnectType
{
	APITcpDisConnectType_Unknown = 0,    // 未知原因断开
	APITcpDisConnectType_CallClose = 1,  // 主动调用 Close 断开
	APITcpDisConnectType_RecvFailed = 2, // 接收失败断开
	APITcpDisConnectType_SendFailed = 3, // 发送失败断开
	APITcpDisConnectType_Exception = 4,  // 致命异常断开
};

// ---------------------------------------------------------------------------
// 加密 Padding 模式
// ---------------------------------------------------------------------------
enum APICrypto_RSAPaddingMode
{
	APICrypto_RSAPaddingMode_Default = 0, // 使用默认 padding
	APICrypto_RSAPaddingMode_PKCS1 = 1,
};

enum APICrypto_AESPaddingMode
{
	APICrypto_AESPaddingMode_Default = 0, // 使用默认 padding
	APICrypto_AESPaddingMode_PKCS7 = 1,
	APICrypto_AESPaddingMode_Zero = 3,
	APICrypto_AESPaddingMode_ANSIX923 = 4,
	APICrypto_AESPaddingMode_ISO10126 = 5,
};

// ---------------------------------------------------------------------------
// 时间戳（替代 GetTimeStamp / GetMilliTimeStamp）
// ---------------------------------------------------------------------------
/**
 * @brief  取当前 Unix 时间戳（秒）
 * @return i64_t 秒级时间戳
 */
i64_t APIGetTimeStamp();

/**
 * @brief  取当前 Unix 时间戳（毫秒）
 * @return u64_t 毫秒级时间戳
 */
u64_t APIGetMilliTimeStamp();

// ---------------------------------------------------------------------------
// 字符串哈希 / 连接 ID 生成（替代 HashStrToU32 / GetRand_UniqueIDBaseX 链路）
// ---------------------------------------------------------------------------
/**
 * @brief  BKDR 字符串哈希，最高位清零
 * @param  [in] str 待哈希字符串
 * @return u32_t 哈希值
 */
u32_t APIHashStrToU32(const char* str);

/**
 * @brief  生成本地连接唯一 ID（随机 u32）
 * @return u32_t 连接 ID
 */
u32_t APIGenConnectID();

/**
 * @brief  生成一个随机 u64（供 AES ISO10126 padding 等使用）
 * @return u64_t 随机数
 */
u64_t APIGetRand_U64();
