// Copyright 2026 Moomoo
#pragma once

#include "MMAPIChannel_InnerDefine.h"
#include "MMAPI_Connect.h"

class MMAPI_Client : public MMAPI_ConnectSink
{
public:
	MMAPI_Client();
	virtual ~MMAPI_Client(void);
	void UnInit();

public:
	/**
	* 设置客户端信息，与InitConnect.proto协议要求一致
	* @param [in] const char* strClientID 客户端唯一标识，无生具体生成规则，客户端自己保证唯一性即可
	* @param [in] i32_t nClientVer 客户端版本号，clientVer = "."以前的数 * 100 + "."以后的，举例：1.1版本的clientVer为1 * 100 + 1 = 101，2.21版本为2 * 100 + 21 = 221
	* @return void
	*/
	void SetClientInfo(const char* strClientID, i32_t nClientVer);

	/**
	* 设置接口编程语言，用于统计
	* @param [in] const char* strClientID 客户端唯一标识，无生具体生成规则，客户端自己保证唯一性即可
	* @return void
	*/
	void SetProgrammingLanguage(const char* strLanguage);

	/**
	* @see MMAPI_Connect::SetProtoFmtType
	*/
	void SetProtoFmtType(u8_t nProtoFmtType);

	/**
	* @see MMAPI_Connect::SetRSAPrivateKey
	*/
	void SetRSAPrivateKey(const char* strRSAPrivateKey);

	/**
	* 禁用协议包加密，默认是使用的AES_ECB加密的，如果连接只是用来接收行情数据，建议禁用加密，如果连接是做交易建议开启加密
	* @param [in] bool bDisable 是否禁用加密，true禁用，false不禁用即启用加密
	* @return void
	*/
	void DisablePacketEnc(bool bDisable);

	/**
	* 初始化连接，包含了创建连接和发送InitConnect协议等，打通信道，可正常首发业务协议包，结果通过OnInitConnect异步回调
	* @note 可继承重载加自己的逻辑，但需保证包含基类的所有处理逻辑
	* @param [in] cconst char* strAddr OpenD服务的IP地址
	* @param [in] u16_t nPort OpenD服务的端口
	* @return bool 是否启动了执行，不代表连接结果，结果通过OnInitConnect回调
	*/
	virtual bool InitConnect(const char* strAddr, u16_t nPort);

	/**
	* 初始化连接结果回调函数，在回调函数中响应处理
	* @note 可继承重载加自己的逻辑，但需保证包含基类的所有处理逻辑
	* @param [in] bool bSucceed 是否成功
	* @param [in] nErrCode 失败类型
	* @return void
	*/
	virtual void OnInitConnect(i64_t nErrCode, const char* strDesc);

	/**
	* @brief 此连接的连接ID，连接的唯一标识，InitConnect协议返回，没有初始化前为0
	* return u64_t 连接ID
	*/
	u64_t GetSvrConnectID();

	/**
	* @brief 本地连接ID
	* return u32_t 连接ID
	*/
	u32_t GetLocalConnectID();

	/**
	* @see MMAPI_Connect::IsConnected
	*/
	bool IsConnected();

	/**
	* @see MMAPI_Connect::Close
	*/
	bool Close();

	/**
	* @see MMAPI_Connect::Send
	*/
	u32_t Send(u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen);

	/**
	* @see MMAPI_ConnectSink
	* @note 可继承重载加自己的逻辑，但需保证包含基类的所有处理逻辑
	*/
	virtual void OnConnect(u32_t nConnectID, i64_t nErrCode);
	virtual void OnDisConnect(u32_t nConnectID, i64_t nErrCode, APITcpDisConnectType enDisConnType);
	virtual void OnTimeTicker(u32_t nConnectID);
	virtual void OnReply(u32_t nConnectID, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen);
	virtual void OnPush(u32_t nConnectID, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen);

private:
	u32_t SendProto_InitConnect();
	void OnReply_InitConnect(MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen);

	u32_t SendProto_KeepAlive();
	void OnReply_KeepAlive(MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen);

private:
	std::string m_strClientID;
	i32_t m_nClientVer{};

	std::string m_strLanguage;

	u64_t m_nConnID{}; //此连接的连接ID，连接的唯一标识，InitConnect协议返回的，并非MMAPI_Connect的连接ID

	std::string m_strRSAPrivateKey;
	bool m_bDisablePacketEnc{ false };
	u8_t m_nProtoFmtType{ MMAPI_ProtoFmtType_Protobuf };

	MMAPI_Connect m_connect;
	u32_t m_nSerialNo_InitConnect{};
	u32_t m_nSerialNo_KeepAlive{};
	i32_t m_nKeepAliveInterval_s{ 10 };
	i32_t m_nKeepAliveTicker{};
};
