// Copyright 2026 Moomoo
#include "MMAPI_Client.h"
#include "Include_3rd_protobuf.h"
#include "Proto/Common.pb.h"
#include "Proto/InitConnect.pb.h"
#include "Proto/KeepAlive.pb.h"
using namespace google;

static inline bool PbObj2BinData(const protobuf::Message& pbObj, std::string& binData)
{
	binData.clear();

	i32_t nSize = pbObj.ByteSize();
	API_If_Warn_Return(nSize < 0, false);
	API_If_Return(nSize == 0, true); // pb为空

	binData.resize(nSize);
	API_If_Do_Warn_Return(!pbObj.SerializeToString(&binData), binData.clear(), false);
	return true;
}

static inline bool BinData2PbObj(const i8_t* pData, i32_t nDataLen, protobuf::Message& pbObj)
{
	API_If_Warn_Return(!pbObj.ParseFromArray(pData, nDataLen), false);
	return true;
}

MMAPI_Client::MMAPI_Client()
	: m_connect(this)
{
}

MMAPI_Client::~MMAPI_Client(void)
{
}

void MMAPI_Client::UnInit()
{
	m_connect.SetSink(nullptr);
}

void MMAPI_Client::SetClientInfo(const char* strClientID, i32_t nClientVer)
{
	API_If_Warn_ReturnVoid(API_IsNullOrEmptyStr(strClientID) || nClientVer <= 0);

	m_strClientID = strClientID;
	m_nClientVer = nClientVer;
}

void MMAPI_Client::SetProgrammingLanguage(const char* strLanguage)
{
	m_strLanguage = strLanguage;
}

void MMAPI_Client::SetProtoFmtType(u8_t nProtoFmtType)
{
	m_nProtoFmtType = nProtoFmtType;
	m_connect.SetProtoFmtType(nProtoFmtType);
}

void MMAPI_Client::SetRSAPrivateKey(const char* strRSAPrivateKey)
{
	m_strRSAPrivateKey = API_IsNullOrEmptyStr(strRSAPrivateKey) ? "" : strRSAPrivateKey;
	m_connect.SetRSAPrivateKey(m_bDisablePacketEnc ? "" : m_strRSAPrivateKey.c_str());
}

void MMAPI_Client::DisablePacketEnc(bool bDisable)
{
	m_bDisablePacketEnc = bDisable;
	m_connect.SetRSAPrivateKey(m_bDisablePacketEnc ? "" : m_strRSAPrivateKey.c_str());
}

bool MMAPI_Client::InitConnect(const char* strAddr, u16_t nPort)
{
	return m_connect.Connect(strAddr, nPort);
}

void MMAPI_Client::OnInitConnect(i64_t nErrCode, const char* /*strDesc*/)
{
	API_If_Do(nErrCode != 0, m_connect.Close());
}

u64_t MMAPI_Client::GetSvrConnectID()
{
	return m_nConnID;
}

u32_t MMAPI_Client::GetLocalConnectID()
{
	return m_connect.GetConnectID();
}

bool MMAPI_Client::IsConnected()
{
	return m_connect.IsConnected();
}

bool MMAPI_Client::Close()
{
	return m_connect.Close();
}

u32_t MMAPI_Client::Send(u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen)
{
	return m_connect.SendProto(nProtoID, nProtoVer, pProtoData, nDataLen);
}

void MMAPI_Client::OnConnect(u32_t nConnectID, i64_t nErrCode)
{
	API_If_Warn_ReturnVoid(nConnectID != m_connect.GetConnectID());

	if (nErrCode == 0)
	{
		m_nSerialNo_InitConnect = SendProto_InitConnect();
		API_If_Do(m_nSerialNo_InitConnect == 0,
			OnInitConnect(API_MakeToU64(MMAPI_InitFailType_SendInitReqFailed, MMAPI_InitFail), "Failed! Send InitConnect Proto Failed"));
	}
	else
	{
		OnInitConnect(nErrCode, "Failed! Connect Failed");
	}
}

void MMAPI_Client::OnDisConnect(u32_t nConnectID, i64_t /*nErrCode*/, APITcpDisConnectType /*enDisConnType*/)
{
	API_If_Warn_ReturnVoid(nConnectID != m_connect.GetConnectID());

	m_nKeepAliveTicker = 0;
	m_nConnID = 0;
}

void MMAPI_Client::OnTimeTicker(u32_t nConnectID)
{
	API_If_Warn_ReturnVoid(nConnectID != m_connect.GetConnectID());

	m_nKeepAliveTicker++;
	if (m_nKeepAliveTicker >= (m_nKeepAliveInterval_s - 3)) // 缩短3秒，以免计时误差导致发晚了
	{
		m_nKeepAliveTicker = 0;
		m_nSerialNo_KeepAlive = SendProto_KeepAlive();
	}
}

void MMAPI_Client::OnReply(u32_t nConnectID, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen)
{
	API_If_Warn_ReturnVoid(nConnectID != m_connect.GetConnectID());

	API_If_Do(protoHeader.nProtoID == MMAPI_ProtoID_KeepAlive, OnReply_KeepAlive(enReqReplyType, protoHeader, pProtoData, nDataLen));
	API_If_Do(protoHeader.nProtoID == MMAPI_ProtoID_InitConnect, OnReply_InitConnect(enReqReplyType, protoHeader, pProtoData, nDataLen));
}

void MMAPI_Client::OnPush(u32_t nConnectID, const MMAPI_ProtoHeader& /*protoHeader*/, const i8_t* /*pProtoData*/, i32_t /*nDataLen*/)
{
	API_If_Warn_ReturnVoid(nConnectID != m_connect.GetConnectID());
}

u32_t MMAPI_Client::SendProto_InitConnect()
{
	InitConnect::C2S* pC2S = new InitConnect::C2S();
	pC2S->set_clientid(m_strClientID);
	pC2S->set_clientver(m_nClientVer);
	pC2S->set_recvnotify(true);
	pC2S->set_packetencalgo(m_bDisablePacketEnc ? Common::PacketEncAlgo_None : Common::PacketEncAlgo_AES_ECB);
	pC2S->set_pushprotofmt(m_nProtoFmtType);
	pC2S->set_programminglanguage(m_strLanguage);

	InitConnect::Request req;
	req.set_allocated_c2s(pC2S);

	std::string binData;
	API_If_Warn_Return(!PbObj2BinData(req, binData), 0);

	return m_connect.SendProto(MMAPI_ProtoID_InitConnect, 0, binData.c_str(), (i32_t)binData.size());
}

void MMAPI_Client::OnReply_InitConnect(MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen)
{
	if (protoHeader.nSerialNo == m_nSerialNo_InitConnect)
	{
		m_nSerialNo_InitConnect = 0;

		switch (enReqReplyType)
		{
		case MMAPI_ReqReplyType_SvrReply:
			{
				InitConnect::Response rsp;
				if (BinData2PbObj(pProtoData, nDataLen, rsp))
				{
					Common::RetType enRetType = (Common::RetType)rsp.rettype();
					if (enRetType == Common::RetType_Succeed)
					{
						m_connect.SetConnAESKey(rsp.s2c().connaeskey().c_str());

						m_nKeepAliveTicker = 0;
						m_nKeepAliveInterval_s = rsp.s2c().keepaliveinterval();
						m_nSerialNo_KeepAlive = SendProto_KeepAlive();
						m_nConnID = rsp.s2c().connid();

						OnInitConnect(0, "Succeed!");
					}
					else if (enRetType == Common::RetType_Failed)
					{
						OnInitConnect(API_MakeToU64(MMAPI_InitFailType_OpenDReject, MMAPI_InitFail), rsp.retmsg().c_str());
					}
					else if (enRetType == Common::RetType_TimeOut)
					{
						OnInitConnect(API_MakeToU64(MMAPI_InitFailType_Timeout, MMAPI_InitFail), "Failed! InitConnect Proto Reply Timeout");
					}
					else if (enRetType == Common::RetType_Unknown)
					{
						OnInitConnect(API_MakeToU64(MMAPI_InitFailType_Unknow, MMAPI_InitFail), "Failed! Unknown Error");
					}
				}
			}
			break;
		case MMAPI_ReqReplyType_Timeout:
			OnInitConnect(API_MakeToU64(MMAPI_InitFailType_Timeout, MMAPI_InitFail), "Failed! InitConnect Proto Reply Timeout");
			break;
		case MMAPI_ReqReplyType_DisConnect:
			OnInitConnect(API_MakeToU64(MMAPI_InitFailType_DisConnect, MMAPI_InitFail), "Failed! DisConnect");
			break;
		default:
			OnInitConnect(API_MakeToU64(MMAPI_InitFailType_Unknow, MMAPI_InitFail), "Failed! Unknown ReplyType");
			break;
		}
	}
	else
	{
		OnInitConnect(API_MakeToU64(MMAPI_InitFailType_SeriaNoNotMatch, MMAPI_InitFail), "Failed! SerialNo Not Match");
	}
}

u32_t MMAPI_Client::SendProto_KeepAlive()
{
	KeepAlive::C2S* pC2S = new KeepAlive::C2S();
	pC2S->set_time(APIGetTimeStamp());

	KeepAlive::Request req;
	req.set_allocated_c2s(pC2S);

	std::string binData;
	API_If_Warn_Return(!PbObj2BinData(req, binData), 0);

	return m_connect.SendProto(MMAPI_ProtoID_KeepAlive, 0, binData.c_str(), (i32_t)binData.size());
}

void MMAPI_Client::OnReply_KeepAlive(MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen)
{
	bool bOK = false;
	if (protoHeader.nSerialNo == m_nSerialNo_KeepAlive)
	{
		m_nSerialNo_KeepAlive = 0;

		switch (enReqReplyType)
		{
		case MMAPI_ReqReplyType_SvrReply:
			{
				KeepAlive::Response rsp;
				if (BinData2PbObj(pProtoData, nDataLen, rsp))
				{
					if (rsp.rettype() == Common::RetType_Succeed)
					{
						bOK = true;
					}
				}
			}
			break;
		}
	}

	API_If_Do(!bOK, m_connect.Close());
}
