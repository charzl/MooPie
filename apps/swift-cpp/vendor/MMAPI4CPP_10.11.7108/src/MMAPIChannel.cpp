// Copyright 2026 Moomoo
#include "MMAPIChannel.h"
#include "MMAPI_Client.h"

namespace
{
	class MMCAPI_ClientImp : public MMAPI_Client
	{
	public:
		void SetOnDisconnectCallback(MMAPIChannel_OnDisConnectCallback callback) { m_onDisconnectCallback = callback; }
		void SetOnInitConnectCallback(MMAPIChannel_OnInitConnectCallback callback) { m_onInitConnectCallback = callback; }
		void SetOnReplyCallback(MMAPIChannel_OnReplyCallback callback) { m_onReplyCallback = callback; }
		void SetOnPushCallback(MMAPIChannel_OnPushCallback callback) { m_onPushCallback = callback; }
	private:
		virtual void OnConnect(Moomoo::u32_t nConnectID, Moomoo::i64_t nErrCode);
		virtual void OnDisConnect(Moomoo::u32_t nConnectID, Moomoo::i64_t nErrCode, APITcpDisConnectType enDisConnType);
		virtual void OnInitConnect(Moomoo::i64_t nErrCode, const char* strDesc);
		virtual void OnTimeTicker(Moomoo::u32_t nConnectID);
		virtual void OnReply(Moomoo::u32_t nConnectID, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen);
		virtual void OnPush(Moomoo::u32_t nConnectID, const MMAPI_ProtoHeader& protoHeader, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen);
	private:
		MMAPIChannel_OnDisConnectCallback m_onDisconnectCallback{ nullptr };
		MMAPIChannel_OnInitConnectCallback m_onInitConnectCallback{ nullptr };
		MMAPIChannel_OnReplyCallback m_onReplyCallback{ nullptr };
		MMAPIChannel_OnPushCallback m_onPushCallback{ nullptr };
	};

	void MMCAPI_ClientImp::OnConnect(Moomoo::u32_t nConnectID, Moomoo::i64_t nErrCode)
	{
		MMAPI_Client::OnConnect(nConnectID, nErrCode);
	}

	void MMCAPI_ClientImp::OnDisConnect(Moomoo::u32_t nConnectID, Moomoo::i64_t nErrCode, APITcpDisConnectType enDisConnType)
	{
		MMAPI_Client::OnDisConnect(nConnectID, nErrCode, (APITcpDisConnectType)enDisConnType);
		if (m_onDisconnectCallback && MMAPI_Client::GetLocalConnectID() == nConnectID)
		{
			m_onDisconnectCallback(this, nErrCode);
		}
	}

	void MMCAPI_ClientImp::OnInitConnect(Moomoo::i64_t nErrCode, const char* strDesc)
	{
		MMAPI_Client::OnInitConnect(nErrCode, strDesc);
		if (m_onInitConnectCallback)
		{
			m_onInitConnectCallback(this, nErrCode, strDesc);
		}
	}

	void MMCAPI_ClientImp::OnTimeTicker(Moomoo::u32_t nConnectID)
	{
		MMAPI_Client::OnTimeTicker(nConnectID);
	}

	void MMCAPI_ClientImp::OnReply(Moomoo::u32_t nConnectID, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen)
	{
		MMAPI_Client::OnReply(nConnectID, enReqReplyType, protoHeader, pProtoData, nDataLen);
		if (m_onReplyCallback&& MMAPI_Client::GetLocalConnectID() == nConnectID)
		{
			m_onReplyCallback(this, enReqReplyType, &protoHeader, pProtoData, nDataLen);
		}
	}

	void MMCAPI_ClientImp::OnPush(Moomoo::u32_t nConnectID, const MMAPI_ProtoHeader& protoHeader, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen)
	{
		MMAPI_Client::OnPush(nConnectID, protoHeader, pProtoData, nDataLen);
		if (m_onPushCallback && MMAPI_Client::GetLocalConnectID() == nConnectID)
		{
			m_onPushCallback(this, &protoHeader, pProtoData, nDataLen);
		}
	}
}

DllXPort_MMAPICHANNEL void MMAPIChannel_Init()
{
	// 无需初始化子系统：网络/定时由 SocketClient 自带（含 WSAStartup 与秒级 OnTimerTick）
}

DllXPort_MMAPICHANNEL void MMAPIChannel_UnInit()
{
	// 对应 MMAPIChannel_Init，无子系统需要反初始化
}

MMAPIChannelPtr CreateMMAPIChannel()
{
	return new MMCAPI_ClientImp();
}

void ReleaseMMAPIChannel(MMAPIChannelPtr pChannel)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->UnInit();
	delete pImp;
}

DllXPort_MMAPICHANNEL void MMAPIChannel_SetClientInfo(MMAPIChannelPtr pChannel, const char* szClientID, Moomoo::i32_t nClientVer)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetClientInfo(szClientID, nClientVer);
}

DllXPort_MMAPICHANNEL void MMAPIChannel_SetProgrammingLanguage(MMAPIChannelPtr pChannel, const char* szLanguage)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetProgrammingLanguage(szLanguage);
}

DllXPort_MMAPICHANNEL void MMAPIChannel_SetRSAPrivateKey(MMAPIChannelPtr pChannel, const char* strRSAPrivateKey)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetRSAPrivateKey(strRSAPrivateKey);
}

DllXPort_MMAPICHANNEL Moomoo::i32_t MMAPIChannel_InitConnect(MMAPIChannelPtr pChannel, const char* szIPAddr, Moomoo::u16_t nPort, Moomoo::i32_t nEnableEncrypt)
{
	API_If_Return(!pChannel, 1);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetProtoFmtType(MMAPI_ProtoFmtType_Protobuf);
	pImp->DisablePacketEnc(nEnableEncrypt == 0);
	return pImp->InitConnect(szIPAddr, nPort) ? 0 : 1;
}

DllXPort_MMAPICHANNEL u64_t MMAPIChannel_GetConnectID(MMAPIChannelPtr pChannel)
{
	API_If_Return(!pChannel, 0);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	return pImp->GetSvrConnectID();
}

DllXPort_MMAPICHANNEL Moomoo::u32_t MMAPIChannel_SendProto(MMAPIChannelPtr pChannel, Moomoo::u32_t nProtoID, u8_t nProtoVer, const Moomoo::i8_t* pProtoData, Moomoo::i32_t nDataLen)
{
	API_If_Return(!pChannel, 0);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	return pImp->Send(nProtoID, nProtoVer, pProtoData, nDataLen);
}

DllXPort_MMAPICHANNEL Moomoo::i32_t MMAPIChannel_Close(MMAPIChannelPtr pChannel)
{
	API_If_Return(!pChannel, 1);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	return pImp->Close() ? 0 : 1;
}

DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnDisconnectCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnDisConnectCallback callback)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetOnDisconnectCallback(callback);
}

DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnInitConnectCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnInitConnectCallback callback)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetOnInitConnectCallback(callback);
}

DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnReplyCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnReplyCallback callback)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetOnReplyCallback(callback);
}

DllXPort_MMAPICHANNEL void MMAPIChannel_SetOnPushCallback(MMAPIChannelPtr pChannel, MMAPIChannel_OnPushCallback callback)
{
	API_If_ReturnVoid(!pChannel);

	MMCAPI_ClientImp *pImp = (MMCAPI_ClientImp*)pChannel;
	pImp->SetOnPushCallback(callback);
}

