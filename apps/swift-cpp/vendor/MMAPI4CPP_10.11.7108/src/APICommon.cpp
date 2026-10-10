// Copyright 2026 Moomoo
#include "APICommon.h"
#include <chrono>
#include <random>

i64_t APIGetTimeStamp()
{
	auto now = std::chrono::system_clock::now();
	return (i64_t)std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count();
}

u64_t APIGetMilliTimeStamp()
{
	auto now = std::chrono::system_clock::now();
	return (u64_t)std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
}

u32_t APIHashStrToU32(const char* str)
{
	API_If_Return(str == nullptr, 0x7FFFFFFF);

	u32_t nHash = 0;
	while (*str != '\0')
	{
		nHash = nHash * 131 + (u32_t)(u8_t)(*str);
		++str;
	}
	return (nHash & 0x7FFFFFFF); // 最高位清零
}

u32_t APIGenConnectID()
{
	// 本地连接 ID 只需唯一随机，直接用标准库随机数生成，替代原「随机 UUID → Base16 → BKDR 哈希」链路
	std::random_device rd;
	std::mt19937 gen(rd());
	std::uniform_int_distribution<u32_t> dist(1, 0x7FFFFFFF);
	return dist(gen);
}

u64_t APIGetRand_U64()
{
	// 用 C++11 标准库生成全范围随机 u64
	static std::mt19937_64 gen(std::random_device{}());
	static std::uniform_int_distribution<u64_t> dist;
	return dist(gen);
}

// ---------------------------------------------------------------------------
// SHA-1（RFC 3174，纯位运算自实现，不依赖任何外部库）
// ---------------------------------------------------------------------------
namespace
{
	inline u32_t API_SHA1_RotL(u32_t value, i32_t bits)
	{
		return (value << bits) | (value >> (32 - bits));
	}
}

