// Copyright 2026 Moomoo
#include "MMAPI_ConnectImpl.h"
#include "MMAPI_Connect.h"

MMAPI_Connect::MMAPI_Connect(MMAPI_ConnectSink* pSink)
{
	m_pImpl = new MMAPI_ConnectImpl(pSink);
}

MMAPI_Connect::~MMAPI_Connect(void)
{
	API_If_Do(m_pImpl, m_pImpl->UnInit());
	API_DeleteP(m_pImpl);
}

void MMAPI_Connect::SetSink(MMAPI_ConnectSink* pSink)
{
	m_pImpl->SetSink(pSink);
}

void MMAPI_Connect::SetProtoFmtType(u8_t nProtoFmtType)
{
	m_pImpl->SetProtoFmtType(nProtoFmtType);
}

void MMAPI_Connect::SetRSAPrivateKey(const char* strRSAPrivateKey)
{
	m_pImpl->SetRSAPrivateKey(strRSAPrivateKey);
}

void MMAPI_Connect::SetConnAESKey(const char* strConnAESKey)
{
	m_pImpl->SetConnAESKey(strConnAESKey);
}

u32_t MMAPI_Connect::GetConnectID()
{
	return m_pImpl->GetConnectID();
}

bool MMAPI_Connect::Connect(const char* strAddr, u16_t nPort)
{
	return m_pImpl->Connect(strAddr, nPort);
}

bool MMAPI_Connect::IsConnected()
{
	return m_pImpl->IsConnected();
}

bool MMAPI_Connect::Close()
{
	return m_pImpl->Close();
}

u32_t MMAPI_Connect::SendProto(u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen, const i8_t* pHeaderReserved /*= nullptr*/, i32_t nHeaderReservedLen /*= 0*/)
{
	return m_pImpl->SendProto(nProtoID, nProtoVer, pProtoData, nDataLen, pHeaderReserved, nHeaderReservedLen);
}
