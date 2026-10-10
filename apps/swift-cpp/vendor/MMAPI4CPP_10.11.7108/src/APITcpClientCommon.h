// Copyright 2026 Moomoo
#ifndef OPENAPI_SOCKET_CLIENT_COMMON_H
#define OPENAPI_SOCKET_CLIENT_COMMON_H

#include <cstdint>
#include <string>

enum class APITcpClientErrType
{
    Unknown = -1, // 未知错误
    None = 0, // 没有错误
    CreateFailed = 1, // 创建Socket失败
    CloseFailed = 2, // Close模式关闭Socket失败
    ShutdownFailed = 3, // Shutdown模式关闭Socket失败
    GetHostByNameFailed = 4, // 通过域名获取主机地址失败
    GetHostByNameWrong = 5, // 通过域名获取主机地址出错
    ConnectFailed = 6, // 连接失败
    BindFailed = 7, // 绑定失败
    ListenFailed = 8, // 监听失败
    PollReturnError = 9, // Poll返回错误
    SendFailed = 10, // 发送失败
    RecvFailed = 11, // 接收失败
    ConnectTimeout = 12 // 连接超时
};

enum class APITcpClientDisConnectType
{
    Unknown = 0, // 未知原因断开
    CallClose = 1, // 主动调用Close关闭连接断开
    RecvFailed = 2, // 接收失败，绝大部分是远程断开了，本地收到事件，再主动断开，也可能是其他链路问题
    SendFailed = 3, // 发送失败，发不出去，主动断开
    Exception = 4, // 出现致命异常，主动断开
};

class ISocketClientSink {
public:
    virtual ~ISocketClientSink() = default;

    virtual void OnConnect(bool isSuccess, int32_t sysErrNo, APITcpClientErrType clientErrType) = 0;
    virtual void OnRecv(const char* data, int32_t len) = 0;
    virtual void OnDisconnect(int32_t sysErrNo, APITcpClientErrType clientErrType, APITcpClientDisConnectType clientDisconnectType) = 0;
    virtual void OnTimerTick() = 0;
};

#endif