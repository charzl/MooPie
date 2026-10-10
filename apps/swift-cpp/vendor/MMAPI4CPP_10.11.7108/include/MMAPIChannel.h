// Copyright 2026 Moomoo
#pragma once
#include "MMAPIChannel_Define.h"

#ifdef __cplusplus
extern "C" {
#endif

	typedef void *MMAPIChannelPtr;
	typedef void(*MMAPIChannel_OnDisConnectCallback)(MMAPIChannelPtr pChannel, Moomoo::i64_t nErrCode);
	typedef void(*MMAPIChannel_OnInitConnectCallback)(MMAPIChannelPtr pChannel, Moomoo::i64_t nErrCode, const char* strDesc);
	typedef void(*MMAPIChannel_OnReplyCallback)(MMAPIChannelPtr pChannel, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader* pProtoHeader, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen);
	typedef void(*MMAPIChannel_OnPushCallback)(MMAPIChannelPtr pChannel, const MMAPI_ProtoHeader* pProtoHeader, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen);

	DllXPort_MMAPICHANNEL void MMAPIChannel_Init();
	DllXPort_MMAPICHANNEL void MMAPIChannel_UnInit();
	DllXPort_MMAPICHANNEL MMAPIChannelPtr CreateMMAPIChannel();
	DllXPort_MMAPICHANNEL void ReleaseMMAPIChannel(MMAPIChannelPtr pChannel);

	/* 设置客户端信息 */
	DllXPort_MMAPICHANNEL void MMAPIChannel_SetClientInfo(MMAPIChannelPtr pChannel, const char* szClientID, Moomoo::i32_t nClientVer);

	/* 设置接口编程语言 */
	DllXPort_MMAPICHANNEL void MMAPIChannel_SetProgrammingLanguage(MMAPIChannelPtr pChannel, const char* szLanguage);

	/* 设置密钥 */
	DllXPort_MMAPICHANNEL void MMAPIChannel_SetRSAPrivateKey(MMAPIChannelPtr pChannel, const char* strRSAPrivateKey);

	/* 初始化连接，连接并初始化 */
	DllXPort_MMAPICHANNEL Moomoo::i32_t MMAPIChannel_InitConnect(MMAPIChannelPtr pChannel, const char* szIPAddr, Moomoo::u16_t nPort, Moomoo::i32_t nEnableEncrypt);

	/* 此连接的连接ID，连接的唯一标识，InitConnect协议返回，没有初始化前为0 */
	DllXPort_MMAPICHANNEL Moomoo::u64_t MMAPIChannel_GetConnectID(MMAPIChannelPtr pChannel);

	DllXPort_MMAPICHANNEL Moomoo::u32_t MMAPIChannel_SendProto(MMAPIChannelPtr pChannel, Moomoo::u32_t nProtoID, Moomoo::u8_t nProtoVer, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen);

	/* 关闭连接 */
	DllXPort_MMAPICHANNEL Moomoo::i32_t MMAPIChannel_Close(MMAPIChannelPtr pChannel);

	DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnDisconnectCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnDisConnectCallback callback);
	DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnInitConnectCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnInitConnectCallback callback);
	DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnReplyCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnReplyCallback callback);
	DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnPushCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnPushCallback callback);

#ifdef __cplusplus
}
#endif