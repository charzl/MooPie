// Copyright 2026 Moomoo
#pragma once

#ifndef _WIN32

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <queue>
#include <string>
#include <thread>
#include <vector>
#include "APITcpClientCommon.h"



// 基于 poll（Reactor 模型）的 Posix 套接字客户端。
// 生命周期契约（重要）：对象为「单次使用」——Connect 只能成功发起一次。
//   一旦发起连接，无论随后是 Close、对端断开、出错还是连接超时，都不得再次
//   Connect（会直接返回 false）；需要重连请销毁本对象并新建一个。
//   此约束保证不会出现「上一轮未消费的 OnConnect/OnDisconnect（这两类通知不受
//   generation 过滤）在新一轮 Connecting/Connected 时被送达」而扰乱上层状态。
class APITcpClientPosix {
public:
    APITcpClientPosix();
    ~APITcpClientPosix();

    APITcpClientPosix(const APITcpClientPosix&) = delete;
    APITcpClientPosix& operator=(const APITcpClientPosix&) = delete;

    void SetSink(ISocketClientSink* sink);

    // 异步连接，结果通过 ISocketClientSink::OnConnect 回调。
    // 单次使用：只能成功调用一次；Close / 断线 / 超时后再次调用将直接返回 false。
    bool Connect(const std::string& host, uint16_t port, int32_t timeout=0);

    // 异步发送，未发完的数据会缓存并在可写时继续发送
    // 可与收包回调线程并发调用；失败返回 false
    bool Send(const void* data, size_t len);

    // 可与 Send / 回调并发调用；回调线程内调用不会自死锁
    void Close();

    bool IsConnected() const;

private:
    friend class PollPoller;

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

    void StartRecvThread();
    void StopRecvThread();
    bool PushEvent(Event event);
    void ClearEventQueue();
    void RecvThreadLoop();

    void OnPollReadable();
    void OnPollWritable();
    void OnPollError();
    void OnTimerTick();

    // 调用方必须已持有 m_closeMutex；TrySend/UpdatePoll 还需持有 m_sendMutex
    // 返回 0 表示可继续；非 0 为导致断连的 errno
    int32_t TrySend();
    void UpdatePollEventsUnlocked();
    void HandleDisconnectUnlocked(bool notifyDisconnect,
                                  APITcpClientErrType errType,
                                  APITcpClientDisConnectType disconnectType,
                                  int32_t sysErrNo = 0);
    void FinishCloseUnlocked();

    // 在途派发计数：轮询线程在持 poller 锁快照裸指针时登记一次引用，
    // 对该 client 的本轮回调派发全部结束后释放。析构在不持 m_closeMutex 的
    // 前提下阻塞至计数归零，保证轮询线程不再触碰本对象后才继续销毁，
    // 从而消解「派发回调 vs. 析构」的 use-after-free。
    void AddPendingDispatch();
    void ReleasePendingDispatch();
    void WaitAllDispatchDone();

    int m_fd;
    std::atomic<State> m_state;
    std::string m_host;
    uint16_t m_port;

    // 每次进入 Connecting / 完成关闭时递增，用于丢弃过期事件
    std::atomic<uint64_t> m_generation;

    // Connect 超时截止时间；max() 表示不超时（timeout==0）
    std::chrono::steady_clock::time_point m_connectDeadline;

    std::vector<char> m_sendBuffer;
    size_t m_sendOffset;
    std::mutex m_sendMutex;

    std::queue<Event> m_eventQueue;
    std::mutex m_eventMutex;
    std::condition_variable m_eventCv;
    std::thread m_recvThread;
    std::atomic<bool> m_recvThreadRunning;

    uint32_t m_pollEvents;

    // 在途派发计数（由 m_pendingMutex 保护，为独立叶子锁）
    int m_pendingDispatch;
    std::mutex m_pendingMutex;
    std::condition_variable m_pendingCv;

    // 锁顺序（禁止反向）：m_closeMutex -> m_sendMutex -> m_eventMutex
    // Close/join 时不得持有 m_closeMutex，避免回调里 Send/Close 死锁
    // 等待 m_pendingCv 时同样不得持 m_closeMutex，避免与派发回调（取 m_closeMutex）死锁。
    // m_pendingMutex 为叶子锁：轮询线程可在持 poller 锁时对其加锁登记引用，反向不成立。
    // m_sinkMutex 独立；回调期间持有它，防止 SetSink 清空指针。
    // m_sinkMutex 为 recursive，回调内可调用 SetSink。
    mutable std::mutex m_closeMutex;

    ISocketClientSink* m_sink;
    mutable std::recursive_mutex m_sinkMutex;
};

#endif