// Copyright 2026 Moomoo
#pragma once

#include "MMAPIChannel_InnerDefine.h"

/**
* @class MMAPI_ConnectSink
* @brief MMAPI_Connect连接类的回调接口定义
*/
class MMAPI_ConnectSink
{
public:
	/**
	* 连接结果(成功或失败)回调，错误码为0代表连接成功，其他为失败
	* @param [in] u32_t nConnectID 连接ID
	* @param [in] i64_t nErrCode 错误码
	* @return void
	*/
	virtual void OnConnect(u32_t nConnectID, i64_t nErrCode) = 0;

	/**
	* 发生断线回调
	* @param [in] u32_t nConnectID 连接ID
	* @param [in] i64_t nErrCode 错误码
	* @param [in] APITcpDisConnectType enDisConnType 断线类型
	* @return void
	*/
	virtual void OnDisConnect(u32_t nConnectID, i64_t nErrCode, APITcpDisConnectType enDisConnType) = 0;

	/**
	* 每秒定时回调，供上层使用者当秒级定时器使用，处理如超时判断等
	* @param [in] u32_t nConnectID 连接ID
	* @return void
	*/
	virtual void OnTimeTicker(u32_t nConnectID) = 0;

	/**
	* 收到(请求)应答协议
	* @param [in] u32_t nConnectID 连接ID
	* @param [in] MMAPI_ReqReplyType enReqReplyType 应答类型
	* @param [in] const MMAPI_ProtoHeader protoHeader 协议头
	* @param [in] const i8_t* pProtoData 协议数据起地址
	* @param [in] i32_t nDataLen 协议数据长度
	* @return void
	*/
	virtual void OnReply(u32_t nConnectID, MMAPI_ReqReplyType enReqReplyType, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen) = 0;

	/**
	* 收到推送协议
	* @param [in] u32_t nConnectID 连接ID
	* @param [in] const MMAPI_ProtoHeader protoHeader 协议头
	* @param [in] const i8_t* pProtoData 协议数据起地址
	* @param [in] i32_t nDataLen 协议数据长度
	* @return void
	*/
	virtual void OnPush(u32_t nConnectID, const MMAPI_ProtoHeader& protoHeader, const i8_t* pProtoData, i32_t nDataLen) = 0;
};

class MMAPI_ConnectImpl;

/**
* @class MMAPI_Connect
* @brief 与OpenD建立基本连接功能类
*/
class MMAPI_Connect
{
public:
	MMAPI_Connect(MMAPI_ConnectSink* pSink);
	virtual ~MMAPI_Connect(void);

public:
	/**
	* 设置被回调实现类指针，可动态改变
	* @param [in] MMAPI_ConnectSink pSink 回调实现类指针
	* @return void
	*/
	void SetSink(MMAPI_ConnectSink* pSink);

	/**
	* 设置协议格式，只能初始设置一次，不能动态修改
	* @param [in] u8_t nProtoFmtType 协议格式，0为Protobuf格式，1为Json格式，默认协议格式为Protobuf
	* @return void
	*/
	void SetProtoFmtType(u8_t nProtoFmtType);

	/**
	* 设置建立加密通讯用的RSA私钥，不设置通讯不加密，只能初始设置一次，不能动态修改
	* @param [in] const char* strRSAPrivateKey RSA私钥内容字符串
	* @return void
	*/
	void SetRSAPrivateKey(const char* strRSAPrivateKey);

	/**
	* 设置加密通讯使用的AES密钥(InitConnect协议返回)，不设置通讯不加密，只能设置InitConnect协议返回的AES密钥，不能动态修改
	* @param [in] const char* strConnAESKey InitConnect协议返回的AES密钥
	* @return void
	*/
	void SetConnAESKey(const char* strConnAESKey);

	/**
	* 获取此连接类的ID，非InitConnet协议服务器返回的connID
	* @return u32_t 此连接类的ID
	*/
	u32_t GetConnectID();

	/**
	* 执行去连接OpenD，异步连接，结果通过OnConnect回调
	* @param [in] cconst char* strAddr OpenD服务的IP地址
	* @param [in] u16_t nPort OpenD服务的端口
	* @return bool 是否启动了执行，不代表连接结果，结果通过OnConnect回调
	*/
	bool Connect(const char* strAddr, u16_t nPort);

	/**
	* 是否与OpenD连接着
	* @return bool 是否连接着
	*/
	bool IsConnected();

	/**
	* 执行关闭与OpenD的连接，异步关闭
	* @return bool 是否启动了执行
	*/
	bool Close();

	/**
	* 发送与OpenD的API协议，通过返回值判断是否发送成功，返回0发送失败，返回非0发送成功，且返回值是发送此协议包产生的的唯一序列号
	* @param [in] u32_t nProtoID 协议号
	* @param [in] u8_t nProtoVer 协议版本
	* @param [in] const i8_t* pProtoData 协议数据起地址
	* @param [in] i32_t nDataLen 协议数据长度
	* @param [in] const i8_t* pHeaderReserved 包头保留数据起地址，默认为空
	* @param [in] i32_t nHeaderReservedLen 包头保留数据长度，默认为0
	* @return u32_t 0为失败，非0为包序列号
	*/
	u32_t SendProto(u32_t nProtoID, u8_t nProtoVer, const i8_t* pProtoData, i32_t nDataLen, const i8_t* pHeaderReserved = nullptr, i32_t nHeaderReservedLen = 0);

private:
	MMAPI_ConnectImpl* m_pImpl{ nullptr };
};
