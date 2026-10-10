// Copyright 2026 Moomoo
#pragma once

#include "MMAPIChannel_InnerDefine.h"
#include "APITcpClientCommon.h"
#include "APITcpClientWin.h"
#include "APITcpClientPosix.h"
#include <mutex>

struct MMAPI_SendPackInfo
{
	MMAPI_ProtoHeader sendHeader{};
	u64_t nSendTime_ms{};

	MMAPI_SendPackInfo()
	{
	}
	MMAPI_SendPackInfo(const MMAPI_ProtoHeader& _sendHeader)
	{
		sendHeader = _sendHeader;
		nSendTime_ms = APIGetMilliTimeStamp();
	}
};

class MMAPI_ConnectSink;
class MMAPI_ConnectImpl : public ISocketClientSink
{
public:
	MMAPI_ConnectImpl(MMAPI_ConnectSink* pSink);
	virtual ~MMAPI_ConnectImpl(void);
	void UnInit();

public:
	void SetSink(MMAPI_ConnectSink* pSink);

	void SetProtoFmtType(u8_t nProtoFmtType);
	void SetRSAPrivateKey(const char* strRSAPrivateKey);
	void SetConnAESKey(const char* strConnAESKey);

	u32_t GetConnectID();

	bool Connect(const char* strAddr, u16_t nPort);
	bool IsConnected();

	bool Close();

	u32_t SendProto(u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen, const i8_t* pHeaderReserved = nullptr, i32_t nHeaderReservedLen = 0);

	void OnConnect(bool isSuccess, int32_t sysErrNo, APITcpClientErrType clientErrType) override;
	void OnRecv(const char* data, int32_t len) override;
	void OnDisconnect(int32_t sysErrNo, APITcpClientErrType clientErrType, APITcpClientDisConnectType clientDisconnectType) override;
	void OnTimerTick() override;

private:
	bool GetSendPackInfo_ByReplyHeader(const MMAPI_ProtoHeader& header, MMAPI_SendPackInfo* pPackInfo, bool bErase = true);
	bool GetSendPackInfo_TheBegin(MMAPI_SendPackInfo* pPackInfo, bool bErase = true);
	bool GetSendPackInfo_ATimeout(u64_t nCurtTime_ms, MMAPI_SendPackInfo* pPackInfo, bool bErase = true);
	bool IsValidFAPIProtoHeader(const MMAPI_ProtoHeader* pHeader);
	bool SetProtoHeaderSomeFields(MMAPI_ProtoHeader& header, u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen, const i8_t* pHeaderReserved, i32_t nHeaderReservedLen);
	void ResizeCacheBuf(i8_t** ppBuf, i32_t* pBufLen, i32_t nDataLen, i32_t nMaxSize);
	void OnRecvAPacket(const MMAPI_ProtoHeader* pHeader, const i8_t* pData, i32_t nDataLen);
	void OnDisConnect_RelpyReq();

private:
	std::recursive_mutex m_lockTcpConnect;
	std::recursive_mutex m_lockSink;
	std::recursive_mutex m_lockSendProto;
	std::recursive_mutex m_lockSendPackInfo;

#if defined(_WIN32)
	APITcpClientWin m_tcpConnect;
#else
	APITcpClientPosix m_tcpConnect;
#endif
	MMAPI_ConnectSink* m_pSink{ nullptr };
	u32_t m_nConnectID{};
	i32_t m_nHeaderLen{};

	u8_t m_nProtoFmtType{ MMAPI_ProtoFmtType_Protobuf }; // 默认为Protobuf
	std::string m_strRSAPrivateKey;
	std::string m_strConnAESKey;

	u32_t m_nSendSerialNo{};
	std::map<u32_t, MMAPI_SendPackInfo> m_mapSendPackInfo;

	i8_t* m_pSendBuf{ nullptr };
	i32_t m_nSendBufLen{};
	i8_t* m_pDecryptBuf{ nullptr };
	i32_t m_nDecryptBufLen{};
	std::vector<i8_t> m_recvBuf;
};
