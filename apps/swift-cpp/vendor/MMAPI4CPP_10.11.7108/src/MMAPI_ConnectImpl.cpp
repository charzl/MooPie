// Copyright 2026 Moomoo
#include "MMAPI_ConnectImpl.h"
#include "MMAPI_Connect.h"
#include "APICrypt.h"

MMAPI_ConnectImpl::MMAPI_ConnectImpl(MMAPI_ConnectSink* pSink)
{
	m_pSink = pSink;
	m_nConnectID = APIGenConnectID();
	m_nHeaderLen = sizeof(MMAPI_ProtoHeader);
	m_tcpConnect.SetSink(this);
}

MMAPI_ConnectImpl::~MMAPI_ConnectImpl(void)
{
}

void MMAPI_ConnectImpl::UnInit()
{
	{
		std::lock_guard<std::recursive_mutex> autoLock_m_lockTcpConnect(m_lockTcpConnect);
		m_tcpConnect.SetSink(nullptr);
	}

	{
		std::lock_guard<std::recursive_mutex> autoLock_m_lockSink(m_lockSink);
		m_pSink = nullptr;
	}

	{
		std::lock_guard<std::recursive_mutex> autoLock_m_lockSendProto(m_lockSendProto);
		API_Delete1D(m_pSendBuf);
	}

	API_Delete1D(m_pDecryptBuf);
}

void MMAPI_ConnectImpl::SetSink(MMAPI_ConnectSink* pSink)
{
	std::lock_guard<std::recursive_mutex> autoLock_m_lockSink(m_lockSink);
	m_pSink = pSink;
}

void MMAPI_ConnectImpl::SetProtoFmtType(u8_t nProtoFmtType)
{
	m_nProtoFmtType = nProtoFmtType;
}

void MMAPI_ConnectImpl::SetRSAPrivateKey(const char* strRSAPrivateKey)
{
	m_strRSAPrivateKey = API_IsNullOrEmptyStr(strRSAPrivateKey) ? "" : strRSAPrivateKey;
}

void MMAPI_ConnectImpl::SetConnAESKey(const char* strConnAESKey)
{
	m_strConnAESKey = API_IsNullOrEmptyStr(strConnAESKey) ? "" : strConnAESKey;
}

u32_t MMAPI_ConnectImpl::GetConnectID()
{
	return m_nConnectID;
}

bool MMAPI_ConnectImpl::Connect(const char* strAddr, u16_t nPort)
{
	std::lock_guard<std::recursive_mutex> autoLock_m_lockTcpConnect(m_lockTcpConnect);
	return m_tcpConnect.Connect(strAddr, nPort);
}

bool MMAPI_ConnectImpl::IsConnected()
{
	std::lock_guard<std::recursive_mutex> autoLock_m_lockTcpConnect(m_lockTcpConnect);
	return m_tcpConnect.IsConnected();
}

bool MMAPI_ConnectImpl::Close()
{
	std::lock_guard<std::recursive_mutex> autoLock_m_lockTcpConnect(m_lockTcpConnect);
	m_tcpConnect.Close();
	return true;
}

u32_t MMAPI_ConnectImpl::SendProto(u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen, const i8_t* pHeaderReserved /*= nullptr*/, i32_t nHeaderReservedLen /*= 0*/)
{
	//API_If_Warn_Return(API_IsNullPtr(pProtoData) || nDataLen <= 0, 0); // 允许协议内容为空，因为pb不赋值取默认值可能为空
	std::lock_guard<std::recursive_mutex> autoLock_m_lockSendProto(m_lockSendProto);

	MMAPI_ProtoHeader header{};
	API_If_Warn_Return(!SetProtoHeaderSomeFields(header, nProtoID, nProtoVer, pProtoData, nDataLen, pHeaderReserved, nHeaderReservedLen), 0);

	// m_strRSAPrivateKey不为空代表启用加密通讯，为空代表不加密通讯，启用加密且协议内容不为空时才进行加密处理
	bool bEncrypt = (!m_strRSAPrivateKey.empty() && API_IsNotNullPtr(pProtoData) && nDataLen > 0);
	// 还未等到InitConnect协议返回ConnAESKey，不允许发其他加密处理协议
	API_If_Warn_Return(bEncrypt && header.nProtoID != MMAPI_ProtoID_InitConnect && m_strConnAESKey.length() <= 0, 0);

	ResizeCacheBuf(&m_pSendBuf, &m_nSendBufLen, m_nHeaderLen
		+ (bEncrypt ? ((header.nProtoID == MMAPI_ProtoID_InitConnect) ? APICrypto_RSA_CalcEncBufLen(nDataLen) : APICrypto_FTAES_MD5_CalcEncBufLen(nDataLen)) : nDataLen)
		, 256 * 1024);

	if (bEncrypt)
	{
		i32_t nEncDataLen = (header.nProtoID == MMAPI_ProtoID_InitConnect)
			? APICrypto_RSA_PublicEncrypt(m_strRSAPrivateKey.c_str(), false, pProtoData, nDataLen, m_pSendBuf + m_nHeaderLen, m_nSendBufLen - m_nHeaderLen, APICrypto_RSAPaddingMode_Default, true)
			: APICrypto_AES_ECB_Encrypt(m_strConnAESKey.c_str(), 16, pProtoData, nDataLen, m_pSendBuf + m_nHeaderLen, m_nSendBufLen - m_nHeaderLen);
		API_If_Warn_Return(nEncDataLen <= 0, 0);
		header.nBodyLen = nEncDataLen;
	}
	else
	{
		memcpy(m_pSendBuf + m_nHeaderLen, pProtoData, nDataLen);
		header.nBodyLen = nDataLen;
	}
	header.nSerialNo = (++m_nSendSerialNo);
	memcpy(m_pSendBuf, &header, m_nHeaderLen);

	//先记录SendSerialNo，如果发送失败再去掉，否则回包有可能比记录SendSerialNo先回来
	{
		std::lock_guard<std::recursive_mutex> autoLock_m_lockSendPackInfo(m_lockSendPackInfo);
		APIMapInsert(m_mapSendPackInfo, m_nSendSerialNo, MMAPI_SendPackInfo(header));
	}

	bool bSendRet{ false };
	{
		std::lock_guard<std::recursive_mutex> autoLock_m_lockTcpConnect(m_lockTcpConnect);
		bSendRet = m_tcpConnect.Send(m_pSendBuf, m_nHeaderLen + header.nBodyLen);
	}
	if (!bSendRet)
	{
		std::lock_guard<std::recursive_mutex> autoLock_m_lockSendPackInfo(m_lockSendPackInfo);
		APIMapErase(m_mapSendPackInfo, m_nSendSerialNo);
	}
	return (bSendRet ? header.nSerialNo : 0);
}

#define MMAPI_SinkCallBack(func) \
	{\
		std::lock_guard<std::recursive_mutex> autoLock_m_lockSink(m_lockSink);\
		API_If_Do(API_IsNotNullPtr(m_pSink), m_pSink->func);\
	}


void MMAPI_ConnectImpl::OnConnect(bool isSuccess, int32_t sysErrNo, APITcpClientErrType clientErrType)
{
	uint64_t nErrCode = API_MakeToU64(sysErrNo, (int32_t)clientErrType);
	MMAPI_SinkCallBack(OnConnect(m_nConnectID, nErrCode));
}

void MMAPI_ConnectImpl::OnRecv(const char* pData, int32_t nDataLen)
{
	if (!pData || nDataLen == 0)
		return;

	m_recvBuf.insert(m_recvBuf.end(), (i8_t*)pData, (i8_t*)pData + nDataLen);
	while (m_recvBuf.size() > m_nHeaderLen)
	{
		if (IsValidFAPIProtoHeader((const MMAPI_ProtoHeader*)m_recvBuf.data()))
		{
			i32_t nBodyLen = ((const MMAPI_ProtoHeader*)m_recvBuf.data())->nBodyLen;
			i32_t nPacketLen = m_nHeaderLen + nBodyLen;
			if (m_recvBuf.size() >= nPacketLen)
			{
				OnRecvAPacket((const MMAPI_ProtoHeader*)m_recvBuf.data(), (i8_t*)m_recvBuf.data() + m_nHeaderLen, nBodyLen);
				m_recvBuf.erase(m_recvBuf.begin(), m_recvBuf.begin() + nPacketLen);
			}
			else
			{
				break;
			}
		}
		else
		{
			API_Warn;
			m_recvBuf.clear();
		}
	}
}

void MMAPI_ConnectImpl::OnDisconnect(int32_t sysErrNo, APITcpClientErrType clientErrType,
	APITcpClientDisConnectType clientDisconnectType)
{
	OnDisConnect_RelpyReq();

	uint64_t nErrCode = API_MakeToU64(sysErrNo, (int32_t)clientErrType);
	MMAPI_SinkCallBack(OnDisConnect(m_nConnectID, nErrCode, (APITcpDisConnectType)clientDisconnectType));
}

void MMAPI_ConnectImpl::OnTimerTick()
{
	MMAPI_SinkCallBack(OnTimeTicker(m_nConnectID));

	MMAPI_SendPackInfo packInfo{};
	u64_t nCurtTime_ms = APIGetMilliTimeStamp();
	while (GetSendPackInfo_ATimeout(nCurtTime_ms, &packInfo))
	{
		MMAPI_SinkCallBack(OnReply(m_nConnectID, MMAPI_ReqReplyType_Timeout, packInfo.sendHeader, nullptr, 0));
	}
}

bool MMAPI_ConnectImpl::GetSendPackInfo_ByReplyHeader(const MMAPI_ProtoHeader& header, MMAPI_SendPackInfo* pPackInfo, bool bErase /*= true*/)
{
	std::lock_guard<std::recursive_mutex> autoLock_m_lockSendPackInfo(m_lockSendPackInfo);

	API_IfTreeFind_Iter(iter, m_mapSendPackInfo, header.nSerialNo)
	{
		API_If_Warn_Return(header.nProtoID != iter->second.sendHeader.nProtoID, false);
		API_If_Do(API_IsNotNullPtr(pPackInfo), *pPackInfo = iter->second);
		API_If_Do(bErase, m_mapSendPackInfo.erase(iter));
		return true;
	}
	return false;
}

bool MMAPI_ConnectImpl::GetSendPackInfo_TheBegin(MMAPI_SendPackInfo* pPackInfo, bool bErase /*= true*/)
{
	std::lock_guard<std::recursive_mutex> autoLock_m_lockSendPackInfo(m_lockSendPackInfo);

	if (!m_mapSendPackInfo.empty())
	{
		API_If_Do(API_IsNotNullPtr(pPackInfo), *pPackInfo = m_mapSendPackInfo.begin()->second);
		API_If_Do(bErase, m_mapSendPackInfo.erase(m_mapSendPackInfo.begin()));
		return true;
	}
	return false;
}

bool MMAPI_ConnectImpl::GetSendPackInfo_ATimeout(u64_t nCurtTime_ms, MMAPI_SendPackInfo* pPackInfo, bool bErase /*= true*/)
{
	std::lock_guard<std::recursive_mutex> autoLock_m_lockSendPackInfo(m_lockSendPackInfo);

	API_Foreach_Iter(iter, m_mapSendPackInfo)
	{
		if ((nCurtTime_ms - iter->second.nSendTime_ms) > MMAPI_ProtoTimeout_ms)
		{
			API_If_Do(API_IsNotNullPtr(pPackInfo), *pPackInfo = iter->second);
			API_If_Do(bErase, m_mapSendPackInfo.erase(iter));
			return true;
		}
	}
	return false;
}

bool MMAPI_ConnectImpl::IsValidFAPIProtoHeader(const MMAPI_ProtoHeader* pHeader)
{
	API_If_Return(pHeader->szHeaderFlag[0] != MMAPI_ProtoHeaderFlag_F || pHeader->szHeaderFlag[1] != MMAPI_ProtoHeaderFlag_T, false);

	return true;
}

bool MMAPI_ConnectImpl::SetProtoHeaderSomeFields(MMAPI_ProtoHeader& header, u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen, const i8_t* pHeaderReserved, i32_t nHeaderReservedLen)
{
	header.szHeaderFlag[0] = MMAPI_ProtoHeaderFlag_F;
	header.szHeaderFlag[1] = MMAPI_ProtoHeaderFlag_T;
	header.nProtoFmtType = m_nProtoFmtType;
	header.nProtoID = nProtoID;
	header.nProtoVer = nProtoVer;
	if (API_IsNotNullPtr(pHeaderReserved) && nHeaderReservedLen > 0)
	{
		API_If_Warn_Return(nHeaderReservedLen > API_ArrayVarSize(header.arrReserved), false);
		memcpy(header.arrReserved, pHeaderReserved, nHeaderReservedLen);
	}
	if (API_IsNotNullPtr(pProtoData) && nDataLen > 0)
	{
		API_If_Warn_Return(!APICrypto_Hash_SHA1(pProtoData, nDataLen, (i8_t*)header.arrBodySHA1), false);
	}
	return true;
}

void MMAPI_ConnectImpl::ResizeCacheBuf(i8_t** ppBuf, i32_t* pBufLen, i32_t nDataLen, i32_t nMaxSize)
{
	if ((nDataLen + 8) > *pBufLen || *pBufLen > nMaxSize)
	{
		API_Delete1D(*ppBuf);
		*pBufLen = 2 * nDataLen + 8;
		*ppBuf = new i8_t[*pBufLen];
	}
}

void MMAPI_ConnectImpl::OnRecvAPacket(const MMAPI_ProtoHeader* pHeader, const i8_t* pData, i32_t nDataLen)
{
	API_If_Warn_ReturnVoid(API_IsNullPtr(pHeader));

	const i8_t* pProtoData = pData;
	i32_t nProtoDataLen = nDataLen;

	// m_strRSAPrivateKey不为空代表启用加密通讯，为空代表不加密通讯，启用加密且协议内容不为空时才进行解密处理
	if (!m_strRSAPrivateKey.empty() && API_IsNotNullPtr(pData) && nDataLen > 0)
	{
		ResizeCacheBuf(&m_pDecryptBuf, &m_nDecryptBufLen, nDataLen, 1024 * 1024);

		i32_t nDecDataLen = (pHeader->nProtoID == MMAPI_ProtoID_InitConnect)
			? APICrypto_RSA_PrivateDecrypt(m_strRSAPrivateKey.c_str(), false, pData, nDataLen, m_pDecryptBuf, m_nDecryptBufLen)
			: APICrypto_AES_ECB_Decrypt(m_strConnAESKey.c_str(), 16, pData, nDataLen, m_pDecryptBuf, m_nDecryptBufLen);
		API_If_Warn_ReturnVoid(nDecDataLen <= 0);

		pProtoData = m_pDecryptBuf;
		nProtoDataLen = nDecDataLen;
	}

	// SHA1数据校验，无论加不加密都得校验数据完整性
	if (API_IsNotNullPtr(pProtoData) && nProtoDataLen > 0)
	{
		i8_t sha1[20]{};
		APICrypto_Hash_SHA1(pProtoData, nProtoDataLen, sha1);
		API_If_Warn_ReturnVoid(memcmp(pHeader->arrBodySHA1, sha1, API_ArrayVarSize(pHeader->arrBodySHA1)) != 0);
	}

	if (FAPI_IsPushProto(pHeader->nProtoID))
	{
		MMAPI_SinkCallBack(OnPush(m_nConnectID, *pHeader, pProtoData, nProtoDataLen));
	}
	else
	{
		API_If_Warn_ReturnVoid(!GetSendPackInfo_ByReplyHeader(*pHeader, nullptr));

		MMAPI_SinkCallBack(OnReply(m_nConnectID, MMAPI_ReqReplyType_SvrReply, *pHeader, pProtoData, nProtoDataLen));
	}
}

void MMAPI_ConnectImpl::OnDisConnect_RelpyReq()
{
	MMAPI_SendPackInfo packInfo{};
	while (GetSendPackInfo_TheBegin(&packInfo))
	{
		MMAPI_SinkCallBack(OnReply(m_nConnectID, MMAPI_ReqReplyType_DisConnect, packInfo.sendHeader, nullptr, 0));
	}
}
