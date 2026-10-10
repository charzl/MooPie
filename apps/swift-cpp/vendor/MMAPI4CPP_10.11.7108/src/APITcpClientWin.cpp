// Copyright 2026 Moomoo
#include "APITcpClientWin.h"

// 仅在 Windows 上编译。其它平台此翻译单元为空。
#if defined(_WIN32)

#ifndef NOMINMAX
#define NOMINMAX
#endif

// 包含顺序：winsock2.h 必须早于 windows.h，避免与旧 winsock.h 冲突。
#include <winsock2.h>
#include <ws2tcpip.h>
#include <mswsock.h>
#include <windows.h>

#include <atomic>
#include <cstdio>
#include <memory>
#include <set>

namespace {

constexpr size_t kRecvBufferSize = 256 * 1024;
constexpr size_t kMaxSendBufferSize = 1024 * 1024;
constexpr size_t kMaxEventQueueSize = 1024;
constexpr size_t kSendBufferCompactThreshold = 64 * 1024;

// IOCP 完成线程 GetQueuedCompletionStatus 的等待超时（毫秒），用于驱动定时器。
constexpr DWORD kIocpWaitMs = 100;

const uintptr_t kInvalidSock = static_cast<uintptr_t>(INVALID_SOCKET);

enum class OpType {
    Connect,
    Recv,
    Send,
};

}  // namespace

// 重叠操作上下文：overlapped 必须为首成员，便于用 CONTAINING_RECORD 反查。
struct IocpOverlapped {
    WSAOVERLAPPED overlapped;
    OpType type;
    uint64_t generation;
    std::vector<char> buffer;  // recv 落地缓冲 / send 数据快照
    WSABUF wsabuf;
};

// ---------------------------------------------------------------------------
// IocpPoller：进程内单例。持有共享 IOCP 与唯一完成线程，监听所有 client 的
// socket 事件，并按秒驱动各 client 的定时器 / 连接超时检查。
// ---------------------------------------------------------------------------
class IocpPoller {
public:
    static IocpPoller& Instance() {
        static IocpPoller poller;
        return poller;
    }

    bool Valid() const { return m_iocp != nullptr; }

    // 将 socket 关联到共享 IOCP，completion key 设为 client 指针。线程安全，无需加锁。
    bool AssociateSocket(uintptr_t socket, APITcpClientWin* client) {
        const HANDLE h = CreateIoCompletionPort(
            reinterpret_cast<HANDLE>(socket), m_iocp,
            reinterpret_cast<ULONG_PTR>(client), 0);
        return h == m_iocp;
    }

    // 惰性加载 ConnectEx 扩展函数指针（进程内缓存一次）。
    LPFN_CONNECTEX LoadConnectEx(uintptr_t socket) {
        LPFN_CONNECTEX fn = m_connectEx.load(std::memory_order_acquire);
        if (fn != nullptr) {
            return fn;
        }
        GUID guid = WSAID_CONNECTEX;
        LPFN_CONNECTEX loaded = nullptr;
        DWORD bytes = 0;
        if (WSAIoctl(static_cast<SOCKET>(socket),
                     SIO_GET_EXTENSION_FUNCTION_POINTER, &guid, sizeof(guid),
                     &loaded, sizeof(loaded), &bytes, nullptr, nullptr) != 0) {
            return nullptr;
        }
        m_connectEx.store(loaded, std::memory_order_release);
        return loaded;
    }

    // 注册 client 以接收定时器 tick（对象生命周期内注册一次）。
    void Register(APITcpClientWin* client) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_clients.insert(client);
    }

    // 注销。持 m_mutex，故会阻塞直到进行中的定时器派发轮次结束，
    // 保证注销返回后不会再有针对该 client 的 OnTimerTick 调用。
    void Unregister(APITcpClientWin* client) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_clients.erase(client);
    }

private:
    IocpPoller()
        : m_iocp(nullptr), m_running(false), m_connectEx(nullptr), m_wsaOk(false) {
        WSADATA wsaData = {0};
        m_wsaOk = (WSAStartup(MAKEWORD(2, 2), &wsaData) == 0);
        m_iocp = CreateIoCompletionPort(INVALID_HANDLE_VALUE, nullptr, 0, 0);
        if (m_iocp != nullptr) {
            m_running.store(true);
            m_thread = std::thread(&IocpPoller::PollLoop, this);
        }
    }

    ~IocpPoller() {
        Stop();
        if (m_iocp != nullptr) {
            CloseHandle(m_iocp);
            m_iocp = nullptr;
        }
        if (m_wsaOk) {
            WSACleanup();
        }
    }

    IocpPoller(const IocpPoller&) = delete;
    IocpPoller& operator=(const IocpPoller&) = delete;

    void Stop() {
        if (!m_running.exchange(false)) {
            return;
        }
        // 投递哨兵完成包唤醒完成线程退出。
        PostQueuedCompletionStatus(m_iocp, 0, 0, nullptr);
        if (m_thread.joinable()) {
            m_thread.join();
        }
    }

    void PollLoop() {
        auto lastTimer = std::chrono::steady_clock::now();
        while (m_running.load()) {
            DWORD bytes = 0;
            ULONG_PTR key = 0;
            LPOVERLAPPED ov = nullptr;
            const BOOL ok =
                GetQueuedCompletionStatus(m_iocp, &bytes, &key, &ov, kIocpWaitMs);

            if (ov != nullptr) {
                // 有完成包（ok 为 FALSE 时表示该操作失败，错误码经 GetLastError 取得）。
                APITcpClientWin* client = reinterpret_cast<APITcpClientWin*>(key);
                IocpOverlapped* op =
                    CONTAINING_RECORD(ov, IocpOverlapped, overlapped);
                const DWORD err = ok ? ERROR_SUCCESS : GetLastError();
                if (client != nullptr) {
                    client->OnIocpCompletion(op, static_cast<uint32_t>(bytes),
                                             static_cast<uint32_t>(err));
                }
            } else {
                // ov == nullptr：等待超时、被哨兵唤醒或 IOCP 出错。
                if (!m_running.load()) {
                    break;
                }
            }

            const auto now = std::chrono::steady_clock::now();
            if (now - lastTimer >= std::chrono::seconds(1)) {
                lastTimer = now;
                // 全程持 m_mutex 派发，配合 Unregister 保证不会对已析构对象派发。
                std::lock_guard<std::mutex> lock(m_mutex);
                for (APITcpClientWin* client : m_clients) {
                    client->OnTimerTick();
                }
            }
        }
    }

    HANDLE m_iocp;
    std::thread m_thread;
    std::atomic<bool> m_running;
    std::mutex m_mutex;
    std::set<APITcpClientWin*> m_clients;
    std::atomic<LPFN_CONNECTEX> m_connectEx;
    bool m_wsaOk;
};

// ---------------------------------------------------------------------------
// APITcpClientWin
// ---------------------------------------------------------------------------

APITcpClientWin::APITcpClientWin()
    : m_socket(kInvalidSock),
      m_state(State::Idle),
      m_port(0),
      m_generation(0),
      m_connectDeadline(std::chrono::steady_clock::time_point::max()),
      m_sendOffset(0),
      m_sendInFlight(false),
      m_recvThreadRunning(false),
      m_connectOp(std::make_unique<IocpOverlapped>()),
      m_recvOp(std::make_unique<IocpOverlapped>()),
      m_sendOp(std::make_unique<IocpOverlapped>()),
      m_pendingOps(0),
      m_sink(nullptr) {}

APITcpClientWin::~APITcpClientWin() {
    Close();
    // 停止后续定时器 tick（阻塞至进行中的派发结束），随后等待在途完成包全部收敛，
    // 才可安全释放操作上下文与本对象。此处不得持 m_closeMutex。
    IocpPoller::Instance().Unregister(this);
    WaitAllOpsDone();
    SetSink(nullptr);
    // m_connectOp/m_recvOp/m_sendOp 由 unique_ptr 自动释放（此处类型完整）。
}

void APITcpClientWin::SetSink(ISocketClientSink* sink) {
    std::lock_guard<std::recursive_mutex> lock(m_sinkMutex);
    m_sink = sink;
}

bool APITcpClientWin::IsConnected() const {
    return m_state.load() == State::Connected;
}

// ---- 在途操作计数 --------------------------------------------------------

void APITcpClientWin::AddPendingOp() {
    std::lock_guard<std::mutex> lock(m_pendingMutex);
    ++m_pendingOps;
}

void APITcpClientWin::ReleasePendingOp() {
    std::lock_guard<std::mutex> lock(m_pendingMutex);
    // 计数递减与归零通知均在锁内完成，杜绝 WaitAllOpsDone 因虚假唤醒而
    // 在本函数触碰成员前提前返回导致的析构竞态。
    if (--m_pendingOps == 0) {
        m_pendingCv.notify_all();
    }
}

void APITcpClientWin::WaitAllOpsDone() {
    std::unique_lock<std::mutex> lock(m_pendingMutex);
    m_pendingCv.wait(lock, [this] { return m_pendingOps == 0; });
}

// ---- 工作线程 / 事件队列（与 Posix 版语义一致） -------------------------

void APITcpClientWin::StartRecvThread() {
    if (m_recvThreadRunning.exchange(true)) {
        return;
    }
    m_recvThread = std::thread(&APITcpClientWin::RecvThreadLoop, this);
}

void APITcpClientWin::StopRecvThread() {
    const bool wasRunning = m_recvThreadRunning.exchange(false);
    if (wasRunning) {
        std::lock_guard<std::mutex> lock(m_eventMutex);
        m_eventCv.notify_all();
    }
    // 禁止在持有 m_closeMutex 时 join，否则回调里 Send/Close 会死锁。
    if (m_recvThread.joinable() &&
        std::this_thread::get_id() != m_recvThread.get_id()) {
        m_recvThread.join();
    }
}

void APITcpClientWin::ClearEventQueue() {
    std::lock_guard<std::mutex> lock(m_eventMutex);
    while (!m_eventQueue.empty()) {
        m_eventQueue.pop();
    }
}

bool APITcpClientWin::PushEvent(Event event) {
    {
        std::lock_guard<std::mutex> lock(m_eventMutex);
        if (m_eventQueue.size() >= kMaxEventQueueSize) {
            printf("SocketClient event queue is full: socket=%llu, size=%d\n",
                   static_cast<unsigned long long>(m_socket),
                   static_cast<int32_t>(m_eventQueue.size()));
        }
        m_eventQueue.push(std::move(event));
    }
    m_eventCv.notify_one();
    return true;
}

void APITcpClientWin::RecvThreadLoop() {
    while (true) {
        Event event;
        {
            std::unique_lock<std::mutex> lock(m_eventMutex);
            m_eventCv.wait(lock, [this] {
                return !m_eventQueue.empty() || !m_recvThreadRunning.load();
            });
            if (!m_recvThreadRunning.load() && m_eventQueue.empty()) {
                break;
            }
            if (m_eventQueue.empty()) {
                continue;
            }
            event = std::move(m_eventQueue.front());
            m_eventQueue.pop();
        }

        // 仅丢弃过期收包/定时器；Connect/Disconnect 通知在清队列后重新投递，必须送达。
        if ((event.type == EventType::Recv ||
             event.type == EventType::TimerTick) &&
            event.generation != m_generation.load()) {
            continue;
        }

        // 持有 m_sinkMutex 调用回调，避免期间 SetSink 将 m_sink 置空；
        // 不持有 m_closeMutex，回调内仍可安全 Send/Close。
        std::lock_guard<std::recursive_mutex> sinkLock(m_sinkMutex);
        if (!m_sink) {
            continue;
        }

        switch (event.type) {
            case EventType::Connect:
                m_sink->OnConnect(event.connectSuccess, event.sysErrNo,
                                  event.errType);
                break;
            case EventType::Recv:
                if (!event.data.empty()) {
                    m_sink->OnRecv(event.data.data(),
                                   static_cast<int32_t>(event.data.size()));
                }
                break;
            case EventType::Disconnect:
                m_sink->OnDisconnect(event.sysErrNo, event.errType,
                                     event.disconnectType);
                break;
            case EventType::TimerTick:
                m_sink->OnTimerTick();
                break;
        }
    }
}

// ---- Connect -------------------------------------------------------------

bool APITcpClientWin::Connect(const std::string& host, uint16_t port,
                              int32_t timeout) {
    if (!IocpPoller::Instance().Valid()) {
        return false;
    }

    {
        std::lock_guard<std::mutex> lock(m_closeMutex);
        // 单次使用契约（见头文件类注释）：一个对象只允许进入连接流程一次。
        // m_generation 初值为 0，首次进入连接便自增，且此后（Close/断线/超时都会再自增）
        // 永不回到 0，据此闩锁——一旦发起过连接就拒绝再次 Connect。
        // 这从根本上杜绝了在途 OVERLAPPED 的完成包尚未从 IOCP 队列取出时，
        // m_connectOp/m_recvOp/m_sendOp 被下一次连接复用的竞态（否则旧 ABORTED
        // 完成包会因 generation 被覆写而遭误处理）。
        if (m_state.load() != State::Idle || m_generation.load() != 0) {
            return false;
        }
        m_state.store(State::Connecting);
        m_generation.fetch_add(1);
        m_host = host;
        m_port = port;
        m_connectDeadline =
            (timeout > 0) ? (std::chrono::steady_clock::now() +
                             std::chrono::milliseconds(timeout))
                          : std::chrono::steady_clock::time_point::max();
    }

    StartRecvThread();
    const uint64_t generation = m_generation.load();

    // 失败通知：先启动工作线程再投递事件，保证 OnConnect 能被送达。
    auto notifyConnectFailure = [this, generation](
                                    int32_t sysErrNo,
                                    APITcpClientErrType clientErrType) {
        Event event;
        event.type = EventType::Connect;
        event.connectSuccess = false;
        event.errType = clientErrType;
        event.sysErrNo = sysErrNo;
        event.generation = generation;
        PushEvent(std::move(event));
    };

    // 地址解析（阻塞，在调用线程内完成，与 Posix 版一致）。
    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    addrinfo* result = nullptr;
    const std::string portStr = std::to_string(port);
    const int gaiErr =
        getaddrinfo(host.c_str(), portStr.c_str(), &hints, &result);
    if (gaiErr != 0 || result == nullptr) {
        const int32_t sysErrNo = WSAGetLastError();
        // getaddrinfo 返回错误码 → 解析失败；返回成功但无结果 → 解析出错。
        const APITcpClientErrType errType =
            (gaiErr != 0) ? APITcpClientErrType::GetHostByNameFailed
                          : APITcpClientErrType::GetHostByNameWrong;
        std::lock_guard<std::mutex> lock(m_closeMutex);
        if (m_state.load() == State::Connecting &&
            m_generation.load() == generation) {
            m_state.store(State::Idle);
            ClearEventQueue();
            notifyConnectFailure(sysErrNo, errType);
        }
        if (result != nullptr) {
            freeaddrinfo(result);
        }
        return false;
    }

    // 不重试：仅使用首个解析结果。
    addrinfo* rp = result;
    sockaddr_storage peerAddr{};
    const int peerAddrLen = static_cast<int>(rp->ai_addrlen);
    memcpy(&peerAddr, rp->ai_addr, rp->ai_addrlen);
    const int family = rp->ai_family;
    const int socktype = rp->ai_socktype;
    const int protocol = rp->ai_protocol;
    freeaddrinfo(result);
    result = nullptr;

    // 创建重叠 socket 并设为非阻塞（需求 3）。
    const SOCKET s =
        WSASocketW(family, socktype, protocol, nullptr, 0, WSA_FLAG_OVERLAPPED);
    if (s == INVALID_SOCKET) {
        const int32_t sysErrNo = WSAGetLastError();
        std::lock_guard<std::mutex> lock(m_closeMutex);
        if (m_state.load() == State::Connecting &&
            m_generation.load() == generation) {
            m_state.store(State::Idle);
            ClearEventQueue();
            notifyConnectFailure(sysErrNo, APITcpClientErrType::CreateFailed);
        }
        return false;
    }

    auto failWithSocket = [&](int32_t sysErrNo,
                              APITcpClientErrType clientErrType) {
        closesocket(s);
        std::lock_guard<std::mutex> lock(m_closeMutex);
        if (m_state.load() == State::Connecting &&
            m_generation.load() == generation) {
            m_state.store(State::Idle);
            ClearEventQueue();
            notifyConnectFailure(sysErrNo, clientErrType);
        }
    };

    u_long nonBlocking = 1;
    if (ioctlsocket(s, FIONBIO, &nonBlocking) != 0) {
        failWithSocket(WSAGetLastError(), APITcpClientErrType::CreateFailed);
        return false;
    }

    // ConnectEx 要求 socket 已 bind 到通配地址。
    sockaddr_storage bindAddr{};
    int bindLen = 0;
    if (family == AF_INET6) {
        auto* a = reinterpret_cast<sockaddr_in6*>(&bindAddr);
        a->sin6_family = AF_INET6;
        a->sin6_addr = in6addr_any;
        a->sin6_port = 0;
        bindLen = static_cast<int>(sizeof(sockaddr_in6));
    } else {
        auto* a = reinterpret_cast<sockaddr_in*>(&bindAddr);
        a->sin_family = AF_INET;
        a->sin_addr.s_addr = INADDR_ANY;
        a->sin_port = 0;
        bindLen = static_cast<int>(sizeof(sockaddr_in));
    }
    if (bind(s, reinterpret_cast<sockaddr*>(&bindAddr), bindLen) != 0) {
        failWithSocket(WSAGetLastError(), APITcpClientErrType::BindFailed);
        return false;
    }

    if (!IocpPoller::Instance().AssociateSocket(static_cast<uintptr_t>(s),
                                                this)) {
        failWithSocket(WSAGetLastError(), APITcpClientErrType::ConnectFailed);
        return false;
    }

    const LPFN_CONNECTEX connectEx =
        IocpPoller::Instance().LoadConnectEx(static_cast<uintptr_t>(s));
    if (connectEx == nullptr) {
        failWithSocket(WSAGetLastError(), APITcpClientErrType::ConnectFailed);
        return false;
    }

    // 注册定时器（对象生命周期内幂等；即使本次连接失败也保留，Idle 时 tick 为 no-op）。
    IocpPoller::Instance().Register(this);

    std::lock_guard<std::mutex> lock(m_closeMutex);
    if (m_state.load() != State::Connecting ||
        m_generation.load() != generation) {
        closesocket(s);
        return false;
    }
    if (m_connectDeadline != std::chrono::steady_clock::time_point::max() &&
        std::chrono::steady_clock::now() >= m_connectDeadline) {
        closesocket(s);
        m_state.store(State::Idle);
        ClearEventQueue();
        notifyConnectFailure(WSAETIMEDOUT,
                             APITcpClientErrType::ConnectTimeout);
        return false;
    }

    m_socket = static_cast<uintptr_t>(s);

    // 投递 ConnectEx。
    ZeroMemory(&m_connectOp->overlapped, sizeof(m_connectOp->overlapped));
    m_connectOp->type = OpType::Connect;
    m_connectOp->generation = generation;
    AddPendingOp();
    const BOOL ok = connectEx(s, reinterpret_cast<sockaddr*>(&peerAddr),
                              peerAddrLen, nullptr, 0, nullptr,
                              &m_connectOp->overlapped);
    if (!ok && WSAGetLastError() != WSA_IO_PENDING) {
        const int32_t sysErrNo = WSAGetLastError();
        ReleasePendingOp();
        closesocket(s);
        m_socket = kInvalidSock;
        m_state.store(State::Idle);
        ClearEventQueue();
        notifyConnectFailure(sysErrNo, APITcpClientErrType::ConnectFailed);
        return false;
    }
    return true;
}

// ---- Send ----------------------------------------------------------------

bool APITcpClientWin::Send(const void* data, size_t len) {
    if (!data || len == 0) {
        return false;
    }

    std::lock_guard<std::mutex> lock(m_closeMutex);
    if (m_state.load() != State::Connected || m_socket == kInvalidSock) {
        return false;
    }

    int32_t sendErrno = 0;
    size_t pending = 0;
    {
        std::lock_guard<std::mutex> sendLock(m_sendMutex);
        const char* bytes = static_cast<const char*>(data);
        m_sendBuffer.insert(m_sendBuffer.end(), bytes, bytes + len);
        sendErrno = StartSendUnlocked();
        pending = m_sendBuffer.size() - m_sendOffset;
    }

    if (pending > kMaxSendBufferSize) {
        fprintf(stderr, "SocketClient send buffer too large: socket=%llu, size=%d\n",
                static_cast<unsigned long long>(m_socket),
                static_cast<int32_t>(pending));
    }

    if (sendErrno != 0) {
        HandleDisconnectUnlocked(true, APITcpClientErrType::SendFailed,
                                 APITcpClientDisConnectType::SendFailed,
                                 sendErrno);
        return false;
    }
    return true;
}

// 需持 m_closeMutex 与 m_sendMutex。
int32_t APITcpClientWin::StartSendUnlocked() {
    if (m_sendInFlight) {
        return 0;
    }
    if (m_socket == kInvalidSock || m_state.load() != State::Connected) {
        return 0;
    }
    if (m_sendOffset >= m_sendBuffer.size()) {
        return 0;
    }

    // 快照待发数据到操作缓冲：即便并发 Send 追加导致 m_sendBuffer 重分配，
    // 在途 WSASend 引用的仍是独立的 m_sendOp->buffer，安全无虞。
    const size_t remaining = m_sendBuffer.size() - m_sendOffset;
    m_sendOp->buffer.assign(m_sendBuffer.data() + m_sendOffset,
                            m_sendBuffer.data() + m_sendBuffer.size());
    m_sendOp->wsabuf.buf = m_sendOp->buffer.data();
    m_sendOp->wsabuf.len = static_cast<ULONG>(remaining);
    m_sendOp->type = OpType::Send;
    m_sendOp->generation = m_generation.load();
    ZeroMemory(&m_sendOp->overlapped, sizeof(m_sendOp->overlapped));

    AddPendingOp();
    DWORD sent = 0;
    const int r = WSASend(static_cast<SOCKET>(m_socket), &m_sendOp->wsabuf, 1,
                          &sent, 0, &m_sendOp->overlapped, nullptr);
    if (r == 0 || WSAGetLastError() == WSA_IO_PENDING) {
        // r==0（立即完成）默认仍会投递完成包，统一按在途处理。
        m_sendInFlight = true;
        return 0;
    }
    ReleasePendingOp();
    return WSAGetLastError();
}

// ---- Recv ----------------------------------------------------------------

// 需持 m_closeMutex。
bool APITcpClientWin::PostRecvUnlocked() {
    if (m_socket == kInvalidSock) {
        return false;
    }
    if (m_recvOp->buffer.size() != kRecvBufferSize) {
        m_recvOp->buffer.resize(kRecvBufferSize);
    }
    m_recvOp->wsabuf.buf = m_recvOp->buffer.data();
    m_recvOp->wsabuf.len = static_cast<ULONG>(kRecvBufferSize);
    m_recvOp->type = OpType::Recv;
    m_recvOp->generation = m_generation.load();
    ZeroMemory(&m_recvOp->overlapped, sizeof(m_recvOp->overlapped));

    AddPendingOp();
    DWORD flags = 0;
    DWORD recvd = 0;
    const int r = WSARecv(static_cast<SOCKET>(m_socket), &m_recvOp->wsabuf, 1,
                          &recvd, &flags, &m_recvOp->overlapped, nullptr);
    if (r == 0 || WSAGetLastError() == WSA_IO_PENDING) {
        return true;
    }
    ReleasePendingOp();
    return false;
}

// ---- IOCP 完成分发（IOCP 完成线程） -------------------------------------

void APITcpClientWin::OnIocpCompletion(IocpOverlapped* op, uint32_t transferred,
                                       uint32_t errorCode) {
    const OpType type = op->type;
    {
        std::lock_guard<std::mutex> lock(m_closeMutex);
        // 过期完成包（Close/超时后 generation 已递增）直接丢弃，只释放计数。
        if (op->generation == m_generation.load()) {
            switch (type) {
                case OpType::Connect:
                    HandleConnectCompleteUnlocked(errorCode);
                    break;
                case OpType::Recv:
                    HandleRecvCompleteUnlocked(transferred, errorCode);
                    break;
                case OpType::Send:
                    HandleSendCompleteUnlocked(transferred, errorCode);
                    break;
            }
        }
    }
    // 必须作为最后一步（不再触碰任何成员），归零后析构方可安全推进。
    ReleasePendingOp();
}

void APITcpClientWin::HandleConnectCompleteUnlocked(uint32_t errorCode) {
    if (m_state.load() != State::Connecting) {
        return;
    }

    if (errorCode != ERROR_SUCCESS) {
        HandleDisconnectUnlocked(false, APITcpClientErrType::ConnectFailed,
                                 APITcpClientDisConnectType::Unknown);
        Event event;
        event.type = EventType::Connect;
        event.connectSuccess = false;
        event.errType = APITcpClientErrType::ConnectFailed;
        event.sysErrNo = static_cast<int32_t>(errorCode);
        event.generation = m_generation.load();
        PushEvent(std::move(event));
        return;
    }

    // 更新连接上下文，使 socket 可用于后续 API（如 getpeername / shutdown）。
    setsockopt(static_cast<SOCKET>(m_socket), SOL_SOCKET,
               SO_UPDATE_CONNECT_CONTEXT, nullptr, 0);

    State expected = State::Connecting;
    if (!m_state.compare_exchange_strong(expected, State::Connected)) {
        return;
    }
    m_connectDeadline = std::chrono::steady_clock::time_point::max();

    // 连接建立事件先入队。
    Event event;
    event.type = EventType::Connect;
    event.connectSuccess = true;
    event.errType = APITcpClientErrType::None;
    event.sysErrNo = 0;
    event.generation = m_generation.load();
    PushEvent(std::move(event));

    // 投递首个 recv。
    if (!PostRecvUnlocked()) {
        HandleDisconnectUnlocked(true, APITcpClientErrType::RecvFailed,
                                 APITcpClientDisConnectType::RecvFailed,
                                 WSAGetLastError());
        return;
    }

    // flush 连接前缓存的待发数据。
    int32_t sendErrno = 0;
    {
        std::lock_guard<std::mutex> sendLock(m_sendMutex);
        sendErrno = StartSendUnlocked();
    }
    if (sendErrno != 0) {
        HandleDisconnectUnlocked(true, APITcpClientErrType::SendFailed,
                                 APITcpClientDisConnectType::SendFailed,
                                 sendErrno);
    }
}

void APITcpClientWin::HandleRecvCompleteUnlocked(uint32_t transferred,
                                                 uint32_t errorCode) {
    if (errorCode != ERROR_SUCCESS) {
        HandleDisconnectUnlocked(true, APITcpClientErrType::RecvFailed,
                                 APITcpClientDisConnectType::RecvFailed,
                                 static_cast<int32_t>(errorCode));
        return;
    }
    if (transferred == 0) {
        // 对端优雅关闭。
        HandleDisconnectUnlocked(true, APITcpClientErrType::RecvFailed,
                                 APITcpClientDisConnectType::RecvFailed, 0);
        return;
    }

    Event event;
    event.type = EventType::Recv;
    event.data.assign(m_recvOp->buffer.data(),
                      m_recvOp->buffer.data() + transferred);
    event.generation = m_generation.load();
    PushEvent(std::move(event));

    // 复用 m_recvOp 重投递下一个 recv。
    if (!PostRecvUnlocked()) {
        HandleDisconnectUnlocked(true, APITcpClientErrType::RecvFailed,
                                 APITcpClientDisConnectType::RecvFailed,
                                 WSAGetLastError());
    }
}

void APITcpClientWin::HandleSendCompleteUnlocked(uint32_t transferred,
                                                 uint32_t errorCode) {
    int32_t sendErrno = 0;
    {
        std::lock_guard<std::mutex> sendLock(m_sendMutex);
        m_sendInFlight = false;

        if (errorCode != ERROR_SUCCESS) {
            sendErrno = static_cast<int32_t>(errorCode);
        } else {
            m_sendOffset += transferred;
            if (m_sendOffset >= m_sendBuffer.size()) {
                m_sendBuffer.clear();
                m_sendOffset = 0;
            } else if (m_sendOffset >= kSendBufferCompactThreshold) {
                m_sendBuffer.erase(
                    m_sendBuffer.begin(),
                    m_sendBuffer.begin() + static_cast<ptrdiff_t>(m_sendOffset));
                m_sendOffset = 0;
            }
            // 继续发送剩余数据。
            sendErrno = StartSendUnlocked();
        }
    }
    if (sendErrno != 0) {
        HandleDisconnectUnlocked(true, APITcpClientErrType::SendFailed,
                                 APITcpClientDisConnectType::SendFailed,
                                 sendErrno);
    }
}

void APITcpClientWin::OnTimerTick() {
    std::lock_guard<std::mutex> lock(m_closeMutex);
    const State state = m_state.load();
    if (state == State::Connecting) {
        if (m_connectDeadline == std::chrono::steady_clock::time_point::max() ||
            std::chrono::steady_clock::now() < m_connectDeadline) {
            return;
        }
        State expected = State::Connecting;
        if (!m_state.compare_exchange_strong(expected, State::Disconnecting)) {
            return;
        }
        FinishCloseUnlocked();

        Event event;
        event.type = EventType::Connect;
        event.connectSuccess = false;
        event.errType = APITcpClientErrType::ConnectTimeout;
        event.sysErrNo = WSAETIMEDOUT;
        event.generation = m_generation.load();
        PushEvent(std::move(event));
        return;
    }

    if (state != State::Connected) {
        return;
    }

    Event event;
    event.type = EventType::TimerTick;
    event.generation = m_generation.load();
    PushEvent(std::move(event));
}

// ---- 断连 / 关闭 ---------------------------------------------------------

void APITcpClientWin::HandleDisconnectUnlocked(
    bool notifyDisconnect, APITcpClientErrType errType,
    APITcpClientDisConnectType disconnectType, int32_t sysErrNo) {
    State expected = State::Connecting;
    if (!m_state.compare_exchange_strong(expected, State::Disconnecting)) {
        expected = State::Connected;
        if (!m_state.compare_exchange_strong(expected, State::Disconnecting)) {
            return;
        }
    }

    FinishCloseUnlocked();

    if (notifyDisconnect) {
        Event event;
        event.type = EventType::Disconnect;
        event.errType = errType;
        event.disconnectType = disconnectType;
        event.sysErrNo = sysErrNo;
        event.generation = m_generation.load();
        PushEvent(std::move(event));
    }
}

void APITcpClientWin::FinishCloseUnlocked() {
    if (m_socket != kInvalidSock) {
        // 取消并关闭 socket：在途的 WSARecv/WSASend/ConnectEx 会以
        // ERROR_OPERATION_ABORTED 完成，其完成包稍后按 generation 失配丢弃。
        // 注意：此处不触碰 m_recvOp/m_sendOp 的缓冲——它们仍被在途操作引用。
        CancelIoEx(reinterpret_cast<HANDLE>(m_socket), nullptr);
        closesocket(static_cast<SOCKET>(m_socket));
        m_socket = kInvalidSock;
    }
    {
        std::lock_guard<std::mutex> lock(m_sendMutex);
        m_sendBuffer.clear();
        m_sendOffset = 0;
        m_sendInFlight = false;
    }
    ClearEventQueue();
    // 使仍在投递路上的旧 Recv/Send/Connect 完成包与旧事件失效。
    m_generation.fetch_add(1);
    m_connectDeadline = std::chrono::steady_clock::time_point::max();
    m_state.store(State::Idle);
}

void APITcpClientWin::Close() {
    {
        std::lock_guard<std::mutex> lock(m_closeMutex);
        const State current = m_state.load();
        if (current != State::Idle && current != State::Disconnecting) {
            const bool wasConnected = (current == State::Connected);
            const bool wasConnecting = (current == State::Connecting);
            m_state.store(State::Disconnecting);
            FinishCloseUnlocked();

            if (wasConnected) {
                Event event;
                event.type = EventType::Disconnect;
                event.disconnectType = APITcpClientDisConnectType::CallClose;
                event.sysErrNo = 0;
                event.generation = m_generation.load();
                PushEvent(std::move(event));
            } else if (wasConnecting) {
                // 连接过程中被主动 Close 取消，非真实错误，归为 Unknown。
                Event event;
                event.type = EventType::Connect;
                event.connectSuccess = false;
                event.errType = APITcpClientErrType::Unknown;
                event.sysErrNo = 0;
                event.generation = m_generation.load();
                PushEvent(std::move(event));
            }
        }
    }
    // 必须在释放 m_closeMutex 后再 join，否则回调中的 Send/Close 会死锁。
    StopRecvThread();
}

#endif  // _WIN32
