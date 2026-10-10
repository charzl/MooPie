// Copyright 2026 Moomoo
#pragma once

#include <stdint.h>

namespace Moomoo {

typedef char i8_t; // arm-linux-gcc把char默认定义为了unsigned char，用-fsigned-char参数编译变成signed char
typedef short i16_t;
typedef int i32_t;
#ifdef __linux__
typedef int64_t i64_t;
#else
typedef long long i64_t;
#endif

typedef unsigned char u8_t;
typedef unsigned short u16_t;
typedef unsigned int u32_t;
#ifdef __linux__
typedef uint64_t u64_t;
#else
typedef unsigned long long u64_t;
#endif
}

#define DllXPort_MMAPICHANNEL

#pragma pack(push, MMAPI_ProtoHeader, 1)
/**
* @struct MMAPI_ProtoHeader
* @brief MMAPI协议包头结构定义
*/
struct MMAPI_ProtoHeader
{
	Moomoo::u8_t szHeaderFlag[2]; /**< 协议包头标识，固定为"FT" */
	Moomoo::u32_t nProtoID;	 /**< 协议号 */
	Moomoo::u8_t nProtoFmtType; /**< 协议格式，0代表Protobuf格式，1代表Json格式 */
	Moomoo::u8_t nProtoVer; /**< 协议版本，用于后续迭代升级兼容 */
	Moomoo::u32_t nSerialNo; /**< 包序列号 */
	Moomoo::u32_t nBodyLen; /**< 包体长度 */
	Moomoo::u8_t arrBodySHA1[20]; /**< 包体原始(加密前)数据的SHA1哈希值 */
	Moomoo::u8_t arrReserved[8]; /**< 保留8字节扩展 */
};
#pragma pack(pop, MMAPI_ProtoHeader)

#define MMAPI_ProtoFmtType_Protobuf 0 /**< Protobuf协议格式 */
#define MMAPI_ProtoFmtType_Json 1 /**< Json协议格式 */

/**
* @enum MMAPI_ReqReplyType
* @brief 请求应答类型枚举
*/
enum MMAPI_ReqReplyType
{
	MMAPI_ReqReplyType_SvrReply = 0, /**< 来自服务器的应答 */
	MMAPI_ReqReplyType_Timeout = -100, /**< 等待服务器应答超时 */
	MMAPI_ReqReplyType_DisConnect = -200, /**< 因连接已断开(被动断开或主动关闭)的应答 */
};

enum MMAPI_InitFailType
{
	MMAPI_InitFailType_Unknow = 0,  /**< 未知 */
	MMAPI_InitFailType_Timeout = 1,  /**< 超时 */
	MMAPI_InitFailType_DisConnect = 3,  /**< 连接断开 */
	MMAPI_InitFailType_SeriaNoNotMatch = 4, /**< 序列号不符 */
	MMAPI_InitFailType_SendInitReqFailed = 4, /**< 发送初始化协议失败 */
	MMAPI_InitFailType_OpenDReject = 5, /**< FutuOpenD回包指定错误，具体错误看描述*/
};

enum MMAPI_ConnectFailType
{
	MMAPI_ConnectFailType_Unknown = -1,
	MMAPI_ConnectFailType_None = 0,
	MMAPI_ConnectFailType_CreateFailed = 1,
	MMAPI_ConnectFailType_CloseFailed = 2,
	MMAPI_ConnectFailType_ShutdownFailed = 3,
	MMAPI_ConnectFailType_GetHostByNameFailed = 4,
	MMAPI_ConnectFailType_GetHostByNameWrong = 5,
	MMAPI_ConnectFailType_ConnectFailed = 6,
	MMAPI_ConnectFailType_BindFailed = 7,
	MMAPI_ConnectFailType_ListenFailed = 8,
	MMAPI_ConnectFailType_SelectReturnError = 9,
	MMAPI_ConnectFailType_SendFailed = 10,
	MMAPI_ConnectFailType_RecvFailed = 11,
};

#define MMAPI_InitFail		100
