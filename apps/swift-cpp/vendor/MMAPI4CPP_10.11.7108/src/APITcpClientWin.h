// Copyright 2026 Moomoo
#ifndef CPPNET_APITCPCLIENTWIN_H
#define CPPNET_APITCPCLIENTWIN_H

// 仅在 Windows 上编译；其它平台此翻译单元为空，便于跨平台工程统一纳入构建。
#if defined(_WIN32)

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <memory>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>

#include "APITcpClientCommon.h"

// 前置声明：把 <winsock2.h> 等 Windows 头挡在本头文件之外。
// 完整定义在 APITcpClientWin.cpp 中。
struct IocpOverlapped;

// 基于 IOCP（Proactor 模型）的 Windows 套接字客户端。
// 公共接口与语义与 APITcpClientPosix 完全一致：
//   - 异步 Connect，结果经 ISocketClientSink::OnConnect 回调
//   - 异步 Send，未发完的数据缓存并在可写时继续发送
//   - Close 可与 Send / 回调并发调用；回调线程内调用不会自死锁
// 线程模型：
//   - 单个共享 IOCP 完成线程（IocpPoller）监听所有 client 的 socket 事件
//   - 每个 client 拥有独立工作线程，串行执行 sink 回调
// 生命周期契约（重要）：对象为「单次使用」——Connect 只能成功发起一次。
//   一旦发起连接，无论随后是 Close、对端断开、出错还是连接超时，都不得再次
//   Connect（会直接返回 false）；需要重连请销毁本对象并新建一个。
//   此约束保证在途重叠操作（m_connectOp/m_recvOp/m_sendOp）永远不会在其完成包
//   尚未从 IOCP 队列取出前被下一次连接复用，从根本上规避了 OVERLAPPED 复用竞态。
class APITcpClientWin {
public:
    APITcpClientWin();
    ~APITcpClientWin();

    APITcpClientWin(const APITcpClientWin&) = delete;
    APITcpClientWin& operator=(const APITcpClientWin&) = delete;

    void SetSink(ISocketClientSink* sink);

    // 异步连接，结果通过 ISocketClientSink::OnConnect 回调。
    // 单次使用：只能成功调用一次；Close / 断线 / 超时后再次调用将直接返回 false。
    bool Connect(const std::string& host, uint16_t port, int32_t timeout = 0);

    // 异步发送，未发完的数据会缓存并在可写时继续发送
    // 可与收包回调线程并发调用；失败返回 false
    bool Send(const void* data, size_t len);

    // 可与 Send / 回调并发调用；回调线程内调用不会自死锁
    void Close();

    bool IsConnected() const;

private:
    friend class IocpPoller;

    enum class State {
        Idle,
        Connecting,
        Connected,
        Disconnecting,
    };

    enum class EventType {
        Connect,
        Recv,
        Disconnect,
        TimerTick,
    };

    struct Event {
        EventType type;
        std::vector<char> data;
        bool connectSuccess = false;
        // Connect / Disconnect 事件的错误分类；无错误时为 None
        APITcpClientErrType errType = APITcpClientErrType::None;
        // Disconnect 事件的断开原因分类
        APITcpClientDisConnectType disconnectType = APITcpClientDisConnectType::Unknown;
        int32_t sysErrNo = 0;
        uint64_t generation = 0;
    };

    // 工作线程 / 事件队列（平台无关，与 Posix 版一致）
    void StartRecvThread();
    void StopRecvThread();
    bool PushEvent(Event event);
    void ClearEventQueue();
    void RecvThreadLoop();

    // IOCP 完成分发（均在 IOCP 完成线程上执行）
    void OnIocpCompletion(IocpOverlapped* op, uint32_t transferred,
                          uint32_t errorCode);
    void HandleConnectCompleteUnlocked(uint32_t errorCode);
    void HandleRecvCompleteUnlocked(uint32_t transferred, uint32_t errorCode);
    void HandleSendCompleteUnlocked(uint32_t transferred, uint32_t errorCode);
    void OnTimerTick();

    // 需持 m_closeMutex。投递一个 WSARecv；失败返回 false。
    bool PostRecvUnlocked();
    // 需持 m_closeMutex 与 m_sendMutex。若无在途发送且有待发数据则投递 WSASend。
    // 返回 0 表示可继续；非 0 为导致断连的错误码。
    int32_t StartSendUnlocked();
    void HandleDisconnectUnlocked(bool notifyDisconnect,
                                  APITcpClientErrType errType,
                                  APITcpClientDisConnectType disconnectType,
                                  int32_t sysErrNo = 0);
    void FinishCloseUnlocked();

    // 在途重叠操作计数：保证 IOCP 线程不再引用本对象后才可析构。
    void AddPendingOp();
    void ReleasePendingOp();
    void WaitAllOpsDone();

    // SOCKET 句柄，以 uintptr_t 存储以避免在头文件引入 winsock2.h。
    // 无效值等价于 INVALID_SOCKET。
    uintptr_t m_socket;
    std::atomic<State> m_state;
    std::string m_host;
    uint16_t m_port;

    // 每次进入 Connecting / 完成关闭时递增，用于丢弃过期事件与过期完成包
    std::atomic<uint64_t> m_generation;

    // Connect 超时截止时间；max() 表示不超时（timeout==0）
    std::chrono::steady_clock::time_point m_connectDeadline;

    // 发送缓冲（待提交给 WSASend 的数据）
    std::vector<char> m_sendBuffer;
    size_t m_sendOffset;
    bool m_sendInFlight;
    std::mutex m_sendMutex;

    // 事件队列 / 工作线程
    std::queue<Event> m_eventQueue;
    std::mutex m_eventMutex;
    std::condition_variable m_eventCv;
    std::thread m_recvThread;
    std::atomic<bool> m_recvThreadRunning;

    // 重叠操作上下文；每种操作同一时刻最多一个在途。配合「单次使用」契约（见类注释），
    // 同一 op 只会在其完成包被取出后才投递下一次（recv 串行、send 由 m_sendInFlight 保护、
    // connect 仅一次），且不存在跨连接复用，故三块上下文可安全复用。
    // IocpOverlapped 为不完整类型，unique_ptr 的构造/析构均在 .cpp（类型完整处）进行。
    std::unique_ptr<IocpOverlapped> m_connectOp;
    std::unique_ptr<IocpOverlapped> m_recvOp;
    std::unique_ptr<IocpOverlapped> m_sendOp;

    // 在途操作计数（由 m_pendingMutex 保护）
    int m_pendingOps;
    std::mutex m_pendingMutex;
    std::condition_variable m_pendingCv;

    // 锁顺序（禁止反向）：m_closeMutex -> m_sendMutex -> m_eventMutex
    // 等待 m_pendingCv / join 工作线程 / 向 IocpPoller 注销时，均不得持 m_closeMutex，
    // 以避免与回调里的 Send/Close、以及定时器派发发生死锁。
    // m_sinkMutex 独立且为 recursive：回调期间持有它防止 SetSink 置空，回调内可再调 SetSink。
    // 加锁需同时涉及 m_closeMutex 与 m_pendingMutex 时，顺序为 m_closeMutex -> m_pendingMutex。
    mutable std::mutex m_closeMutex;

    ISocketClientSink* m_sink;
    mutable std::recursive_mutex m_sinkMutex;
};

#endif  // _WIN32

#endif  // CPPNET_APITCPCLIENTWIN_H
