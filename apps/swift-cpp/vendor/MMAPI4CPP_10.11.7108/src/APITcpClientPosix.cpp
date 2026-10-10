// Copyright 2026 Moomoo
#include "APITcpClientPosix.h"

#ifndef _WIN32

#include <arpa/inet.h>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <netdb.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <mutex>
#include <thread>
#include <unordered_map>

namespace {

constexpr size_t kRecvBufferSize = 4 * 1024 * 1024;
constexpr size_t kMaxSendBufferSize = 1024 * 1024;
constexpr size_t kMaxEventQueueSize = 1024;
constexpr size_t kSendBufferCompactThreshold = 64 * 1024;

// poll 事件掩码（跨平台；macOS 无 POLLRDHUP 时仅用 POLLIN/POLLHUP 检测对端关闭）
constexpr uint32_t kPollRead = POLLIN;
constexpr uint32_t kPollWrite = POLLOUT;
#if defined(POLLRDHUP)
constexpr uint32_t kPollPeerClosed = POLLRDHUP;
#else
constexpr uint32_t kPollPeerClosed = 0;
#endif

short ToPollEvents(uint32_t events) {
    short result = 0;
    if (events & kPollRead) {
        result = static_cast<short>(result | POLLIN);
    }
    if (events & kPollWrite) {
        result = static_cast<short>(result | POLLOUT);
    }
#if defined(POLLRDHUP)
    if (events & kPollPeerClosed) {
        result = static_cast<short>(result | POLLRDHUP);
    }
#endif
    return result;
}

bool IsPollErrorEvent(short reEvents) {
    if (reEvents & (POLLERR | POLLHUP)) {
        return true;
    }
#if defined(POLLRDHUP)
    if (reEvents & POLLRDHUP) {
        return true;
    }
#endif
    return false;
}

int SetNonBlocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) {
        return -1;
    }
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

}  // namespace

class PollPoller {
public:
    static PollPoller& Instance() {
        static PollPoller poller;
        return poller;
    }

    bool Add(APITcpClientPosix* client, int fd, uint32_t events) {
        std::lock_guard<std::mutex> lock(m_mutex);
        EnsureStarted();
        m_clients[fd] = ClientEntry{client, ToPollEvents(events)};
        return true;
    }

    void Modify(APITcpClientPosix* client, int fd, uint32_t events) {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_clients.find(fd);
        if (it == m_clients.end() || it->second.client != client) {
            return;
        }
        it->second.events = ToPollEvents(events);
    }

    void Remove(APITcpClientPosix* client, int fd) {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_clients.find(fd);
        if (it == m_clients.end() || it->second.client != client) {
            return;
        }
        m_clients.erase(it);
    }

private:
    struct ClientEntry {
        APITcpClientPosix* client;
        short events;
    };

    PollPoller() : m_running(false) {}

    ~PollPoller() {
        Stop();
    }

    PollPoller(const PollPoller&) = delete;
    PollPoller& operator=(const PollPoller&) = delete;

    void EnsureStarted() {
        if (m_running) {
            return;
        }
        m_running = true;
        m_pollThread = std::thread(&PollPoller::PollLoop, this);
    }

    void Stop() {
        if (!m_running) {
            return;
        }
        m_running = false;
        if (m_pollThread.joinable()) {
            m_pollThread.join();
        }
    }

    void PollLoop() {
        std::vector<pollfd> pollFds;
        std::vector<APITcpClientPosix*> pollClients;
        auto lastTimer = std::chrono::steady_clock::now();

        while (m_running) {
            pollFds.clear();
            pollClients.clear();
            {
                std::lock_guard<std::mutex> lock(m_mutex);
                pollFds.reserve(m_clients.size());
                pollClients.reserve(m_clients.size());
                for (const auto& entry : m_clients) {
                    pollfd pfd{};
                    pfd.fd = entry.first;
                    pfd.events = entry.second.events;
                    pfd.revents = 0;
                    pollFds.push_back(pfd);
                    pollClients.push_back(entry.second.client);
                    // 持 poller 锁登记在途派发引用：此刻条目仍在 m_clients 中，对象
                    // 必然存活；Remove 同样需持本锁，故不会与本快照交错。据此保证
                    // 下方无锁派发期间 client 不会被析构（析构方会阻塞在
                    // WaitAllDispatchDone 直到本轮 ReleasePendingDispatch）。
                    entry.second.client->AddPendingDispatch();
                }
            }

            bool pollFailed = false;
            if (pollFds.empty()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            } else {
                const int n = ::poll(pollFds.data(),
                                     static_cast<nfds_t>(pollFds.size()),
                                     100);
                if (n < 0) {
                    // EINTR：被信号打断，本轮重试即可。
                    // 其它错误（EINVAL/ENOMEM/EFAULT 等）：绝不能让轮询线程停摆——那样
                    // m_running 仍为 true，EnsureStarted 不会重启，进程内所有（含后续新建
                    // 的）client 将永久收不到事件与断开通知。改为把本轮快照到的 client 全部
                    // 按错误断开（各自 OnPollError -> OnDisconnect / OnConnect(false)），使上
                    // 层可感知并回收；这些 client 随即从 m_clients 移除，线程继续存活自愈。
                    if (errno != EINTR) {
                        const int nErrNo = errno;
                        fprintf(stderr, "poll error: %s, errno: %d\n",
                                strerror(nErrNo), nErrNo);
                        pollFailed = true;
                        for (APITcpClientPosix* client : pollClients) {
                            if (client) {
                                client->OnPollError();
                            }
                        }
                    }
                } else if (n > 0) {
                    for (size_t i = 0; i < pollFds.size(); ++i) {
                        const short reEvents = pollFds[i].revents;
                        if (reEvents == 0) {
                            continue;
                        }

                        APITcpClientPosix* client = pollClients[i];
                        if (!client) {
                            continue;
                        }

                        if (IsPollErrorEvent(reEvents)) {
                            client->OnPollError();
                            continue;
                        }
                        if (reEvents & POLLOUT) {
                            client->OnPollWritable();
                        }
                        if (reEvents & POLLIN) {
                            client->OnPollReadable();
                        }
                    }
                }
            }

            // 释放本轮快照登记的在途派发引用；必须覆盖所有分支，否则析构方会
            // 永久阻塞在 WaitAllDispatchDone。
            for (APITcpClientPosix* client : pollClients) {
                client->ReleasePendingDispatch();
            }
            pollClients.clear();

            // poll 失败后短暂退避，避免持续性错误下热自旋。正常情况下上面已将出错的
            // client 断开并移出集合，下一轮多为空集（走 sleep 分支），不会走到这里。
            if (pollFailed) {
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            }

            const auto now = std::chrono::steady_clock::now();
            if (now - lastTimer >= std::chrono::seconds(1)) {
                lastTimer = now;
                std::vector<APITcpClientPosix*> timerClients;
                {
                    std::lock_guard<std::mutex> lock(m_mutex);
                    timerClients.reserve(m_clients.size());
                    for (const auto& entry : m_clients) {
                        if (entry.second.client) {
                            timerClients.push_back(entry.second.client);
                            // 与 I/O 派发同理：持 poller 锁登记在途引用，防止定时器
                            // 回调期间对象被析构。
                            entry.second.client->AddPendingDispatch();
                        }
                    }
                }
                for (APITcpClientPosix* client : timerClients) {
                    client->OnTimerTick();
                }
                for (APITcpClientPosix* client : timerClients) {
                    client->ReleasePendingDispatch();
                }
            }
        }
    }

    std::atomic<bool> m_running;
    std::thread m_pollThread;
    std::mutex m_mutex;
    std::unordered_map<int, ClientEntry> m_clients;
};

APITcpClientPosix::APITcpClientPosix()
    : m_fd(-1),
      m_state(State::Idle),
      m_port(0),
      m_generation(0),
      m_connectDeadline(std::chrono::steady_clock::time_point::max()),
      m_sendOffset(0),
      m_recvThreadRunning(false),
      m_pollEvents(0),
      m_pendingDispatch(0),
      m_sink(nullptr) {}

APITcpClientPosix::~APITcpClientPosix() {
    Close();
    // Close 已把本对象从 PollPoller 摘除（FinishCloseUnlocked -> Remove），此后不会再有
    // 新的派发引用登记；此处（不持 m_closeMutex）阻塞至已在途的派发引用全部归零，
    // 才可安全释放本对象。
    WaitAllDispatchDone();
    SetSink(nullptr);
}

void APITcpClientPosix::SetSink(ISocketClientSink* sink) {
    std::lock_guard<std::recursive_mutex> lock(m_sinkMutex);
    m_sink = sink;
}

bool APITcpClientPosix::IsConnected() const {
    return m_state.load() == State::Connected;
}

void APITcpClientPosix::StartRecvThread() {
    if (m_recvThreadRunning.exchange(true)) {
        return;
    }
    m_recvThread = std::thread(&APITcpClientPosix::RecvThreadLoop, this);
}

void APITcpClientPosix::StopRecvThread() {
    const bool wasRunning = m_recvThreadRunning.exchange(false);
    if (wasRunning) {
        std::lock_guard<std::mutex> lock(m_eventMutex);
        m_eventCv.notify_all();
    }
    // 禁止在持有 m_closeMutex 时 join，否则回调里 Send/Close 会死锁
    if (m_recvThread.joinable() &&
        std::this_thread::get_id() != m_recvThread.get_id()) {
        m_recvThread.join();
    }
}

void APITcpClientPosix::AddPendingDispatch() {
    std::lock_guard<std::mutex> lock(m_pendingMutex);
    ++m_pendingDispatch;
}

void APITcpClientPosix::ReleasePendingDispatch() {
    std::lock_guard<std::mutex> lock(m_pendingMutex);
    // 计数递减与归零通知均在锁内完成，杜绝 WaitAllDispatchDone 因虚假唤醒而
    // 在本函数触碰成员前提前返回导致的析构竞态。
    if (--m_pendingDispatch == 0) {
        m_pendingCv.notify_all();
    }
}

void APITcpClientPosix::WaitAllDispatchDone() {
    std::unique_lock<std::mutex> lock(m_pendingMutex);
    m_pendingCv.wait(lock, [this] { return m_pendingDispatch == 0; });
}

void APITcpClientPosix::ClearEventQueue() {
    std::lock_guard<std::mutex> lock(m_eventMutex);
    while (!m_eventQueue.empty()) {
        m_eventQueue.pop();
    }
}

bool APITcpClientPosix::PushEvent(Event event) {
    {
        std::lock_guard<std::mutex> lock(m_eventMutex);
        if (m_eventQueue.size() >= kMaxEventQueueSize) {
            printf("SocketClient event queue is full: fd=%d, size=%d\n", m_fd, (int32_t)m_eventQueue.size());
        }
        m_eventQueue.push(std::move(event));
    }
    m_eventCv.notify_one();
    return true;
}

void APITcpClientPosix::RecvThreadLoop() {
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

        // 仅丢弃过期收包/定时器，Connect/Disconnect 通知在清队列后重新投递，必须送达
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
                m_sink->OnConnect(event.connectSuccess,
                                  event.sysErrNo,
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

bool APITcpClientPosix::Connect(const std::string& host,
                                uint16_t port,
                                int32_t timeout) {
    {
        std::lock_guard<std::mutex> lock(m_closeMutex);
        // 单次使用契约（见头文件类注释）：一个对象只允许进入连接流程一次。
        // m_generation 初值为 0，首次进入连接便自增，且此后（Close/断线/超时都会再自增）
        // 永不回到 0，据此闩锁——一旦发起过连接就拒绝再次 Connect。
        // 这从根本上杜绝了「上一轮未消费的 OnConnect/OnDisconnect（不受 generation 过滤）
        // 在新一轮 Connecting/Connected 时被送达，扰乱上层状态」的问题：因为不存在下一轮。
        if (m_state.load() != State::Idle || m_generation.load() != 0) {
            return false;
        }
        m_state.store(State::Connecting);
        m_generation.fetch_add(1);
        m_host = host;
        m_port = port;
        m_connectDeadline =
            (timeout > 0)
                ? (std::chrono::steady_clock::now() +
                   std::chrono::milliseconds(timeout))
                : std::chrono::steady_clock::time_point::max();
    }

    StartRecvThread();
    const uint64_t generation = m_generation.load();

    auto isConnectTimedOut = [this]() {
        std::lock_guard<std::mutex> lock(m_closeMutex);
        return m_connectDeadline !=
                   std::chrono::steady_clock::time_point::max() &&
               std::chrono::steady_clock::now() >= m_connectDeadline;
    };

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

    addrinfo hints{};
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    addrinfo* result = nullptr;
    const std::string portStr = std::to_string(port);
    const int gaiErr = getaddrinfo(host.c_str(), portStr.c_str(), &hints, &result);
    if (gaiErr != 0) {
        const int32_t sysErrNo = (gaiErr == EAI_SYSTEM) ? errno : 0;
        std::lock_guard<std::mutex> lock(m_closeMutex);
        if (m_state.load() == State::Connecting &&
            m_generation.load() == generation) {
            m_state.store(State::Idle);
            ClearEventQueue();
            notifyConnectFailure(sysErrNo,
                                 APITcpClientErrType::GetHostByNameFailed);
        }
        return false;
    }

    if (isConnectTimedOut()) {
        freeaddrinfo(result);
        std::lock_guard<std::mutex> lock(m_closeMutex);
        if (m_state.load() == State::Connecting &&
            m_generation.load() == generation) {
            m_state.store(State::Idle);
            ClearEventQueue();
            notifyConnectFailure(ETIMEDOUT,
                                 APITcpClientErrType::ConnectTimeout);
        }
        return false;
    }

    int fd = -1;
    bool connectedImmediately = false;
    int32_t lastErrno = 0;
    APITcpClientErrType lastErrType = APITcpClientErrType::ConnectFailed;
    for (addrinfo* rp = result; rp != nullptr; rp = rp->ai_next) {
        if (isConnectTimedOut()) {
            lastErrno = ETIMEDOUT;
            lastErrType = APITcpClientErrType::ConnectTimeout;
            if (fd >= 0) {
                close(fd);
                fd = -1;
            }
            break;
        }

        fd = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
        if (fd < 0) {
            lastErrno = errno;
            lastErrType = APITcpClientErrType::CreateFailed;
            continue;
        }
        if (SetNonBlocking(fd) != 0) {
            lastErrno = errno;
            lastErrType = APITcpClientErrType::CreateFailed;
            close(fd);
            fd = -1;
            continue;
        }

        const int ret = connect(fd, rp->ai_addr, rp->ai_addrlen);
        if (ret == 0) {
            connectedImmediately = true;
            break;
        }
        if (ret < 0 && errno == EINPROGRESS) {
            break;
        }
        lastErrno = errno;
        lastErrType = APITcpClientErrType::ConnectFailed;
        close(fd);
        fd = -1;
    }
    freeaddrinfo(result);

    if (fd < 0) {
        std::lock_guard<std::mutex> lock(m_closeMutex);
        if (m_state.load() == State::Connecting &&
            m_generation.load() == generation) {
            m_state.store(State::Idle);
            ClearEventQueue();
            notifyConnectFailure(lastErrno, lastErrType);
        }
        return false;
    }

    std::lock_guard<std::mutex> lock(m_closeMutex);
    if (m_state.load() != State::Connecting ||
        m_generation.load() != generation) {
        close(fd);
        return false;
    }

    if (m_connectDeadline != std::chrono::steady_clock::time_point::max() &&
        std::chrono::steady_clock::now() >= m_connectDeadline) {
        close(fd);
        m_state.store(State::Idle);
        ClearEventQueue();
        notifyConnectFailure(ETIMEDOUT, APITcpClientErrType::ConnectTimeout);
        return false;
    }

    m_fd = fd;

    auto failConnect = [&](int32_t sysErrNo, APITcpClientErrType clientErrType) {
        close(m_fd);
        m_fd = -1;
        m_state.store(State::Idle);
        ClearEventQueue();
        notifyConnectFailure(sysErrNo, clientErrType);
    };

    if (connectedImmediately) {
        m_state.store(State::Connected);
        m_connectDeadline = std::chrono::steady_clock::time_point::max();
        m_pollEvents = kPollRead | kPollPeerClosed;
        if (!PollPoller::Instance().Add(this, m_fd, m_pollEvents)) {
            failConnect(errno != 0 ? errno : EIO,
                        APITcpClientErrType::ConnectFailed);
            return false;
        }

        Event event;
        event.type = EventType::Connect;
        event.connectSuccess = true;
        event.errType = APITcpClientErrType::None;
        event.sysErrNo = 0;
        event.generation = generation;
        PushEvent(std::move(event));
        return true;
    }

    m_pollEvents = kPollRead | kPollWrite | kPollPeerClosed;
    if (!PollPoller::Instance().Add(this, m_fd, m_pollEvents)) {
        failConnect(errno != 0 ? errno : EIO,
                    APITcpClientErrType::ConnectFailed);
        return false;
    }
    return true;
}

bool APITcpClientPosix::Send(const void* data, size_t len) {
    if (!data || len == 0) {
        return false;
    }

    // 与 Close/断线同一把 m_closeMutex，保证 m_fd/m_state 与发送视图一致
    std::lock_guard<std::mutex> lock(m_closeMutex);
    if (m_state.load() != State::Connected || m_fd < 0) {
        return false;
    }

    int32_t sendErrno = 0;
    int32_t pending = 0;

    {
        std::lock_guard<std::mutex> sendLock(m_sendMutex);
        const char* bytes = static_cast<const char*>(data);
        m_sendBuffer.insert(m_sendBuffer.end(), bytes, bytes + len);
        sendErrno = TrySend();
        if (sendErrno == 0) {
            UpdatePollEventsUnlocked();
        }
        pending = (int32_t)(m_sendBuffer.size() - m_sendOffset);
    }

    if (pending > kMaxSendBufferSize) {
        fprintf(stderr, "SocketClient send buffer too large: fd=%d, size=%d\n", m_fd, pending);        
    }

    if (sendErrno != 0) {
        HandleDisconnectUnlocked(true, APITcpClientErrType::SendFailed,
                                 APITcpClientDisConnectType::SendFailed,
                                 sendErrno);
        return false;
    }

    return true;
}

int32_t APITcpClientPosix::TrySend() {
    if (m_fd < 0) {
        return EBADF;
    }

    while (m_sendOffset < m_sendBuffer.size()) {
        const size_t remaining = m_sendBuffer.size() - m_sendOffset;
        const ssize_t n = ::send(m_fd,
                                 m_sendBuffer.data() + m_sendOffset,
                                 remaining,
                                 MSG_NOSIGNAL);
        if (n > 0) {
            m_sendOffset += static_cast<size_t>(n);
            continue;
        }
        if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
            break;
        }
        return (errno != 0) ? errno : ECONNRESET;
    }

    if (m_sendOffset >= m_sendBuffer.size()) {
        m_sendBuffer.clear();
        m_sendOffset = 0;
    } else if (m_sendOffset >= kSendBufferCompactThreshold) {
        m_sendBuffer.erase(m_sendBuffer.begin(),
                           m_sendBuffer.begin() + static_cast<ptrdiff_t>(m_sendOffset));
        m_sendOffset = 0;
    }
    return 0;
}

void APITcpClientPosix::UpdatePollEventsUnlocked() {
    if (m_fd < 0) {
        return;
    }

    uint32_t events = kPollRead | kPollPeerClosed;
    if (m_state.load() == State::Connecting) {
        events |= kPollWrite;
    } else if (m_sendOffset < m_sendBuffer.size()) {
        events |= kPollWrite;
    }

    if (events != m_pollEvents) {
        m_pollEvents = events;
        PollPoller::Instance().Modify(this, m_fd, m_pollEvents);
    }
}

void APITcpClientPosix::OnPollReadable() {
    // 每次 recv 均在持 m_closeMutex 时执行：socket 为非阻塞，recv 仅消费内核缓冲已有
    // 数据后即以 EAGAIN 返回，不会长时间持锁；关键在于——持锁期间并发 Close 无法
    // 关闭 m_fd，从而杜绝「fd 被关闭并被进程内其它 socket 复用后，recv 从该 fd 误读
    // 别的连接字节」的串扰（隐患 2）。每读一段即释放并重取锁，允许并发 Send 在两次
    // 读之间穿插，保留原有的读写并发特性。
    std::vector<char> buffer(kRecvBufferSize);
    while (true) {
        std::lock_guard<std::mutex> lock(m_closeMutex);
        if (m_fd < 0) {
            return;
        }
        // 仅在已连接后收包：连接完成前（Connecting）不得 recv，否则可能把 Recv 事件
        // 排在 OnConnect 之前，违反「OnConnect 先于 OnRecv」契约。连接完成同一轮里
        // POLLOUT 先于 POLLIN 派发（先切 Connected 并投 OnConnect），本轮 POLLIN 仍能
        // 读到；极端情况下也只是延到下一轮读，数据不丢。与 Win 版仅在连接完成后投递
        // recv 的语义一致。
        if (m_state.load() != State::Connected) {
            return;
        }

        const uint64_t generation = m_generation.load();
        const ssize_t n = ::recv(m_fd, buffer.data(), buffer.size(), 0);
        if (n > 0) {
            Event event;
            event.type = EventType::Recv;
            event.data.assign(buffer.data(), buffer.data() + n);
            event.generation = generation;
            PushEvent(std::move(event));
            continue;
        }
        if (n == 0) {
            HandleDisconnectUnlocked(true, APITcpClientErrType::RecvFailed,
                                     APITcpClientDisConnectType::RecvFailed, 0);
            return;
        }
        const int32_t sysErrNo = errno;
        if (sysErrNo == EAGAIN || sysErrNo == EWOULDBLOCK) {
            return;
        }
        HandleDisconnectUnlocked(true, APITcpClientErrType::RecvFailed,
                                 APITcpClientDisConnectType::RecvFailed,
                                 sysErrNo);
        return;
    }
}

void APITcpClientPosix::OnPollWritable() {
    std::lock_guard<std::mutex> lock(m_closeMutex);
    if (m_fd < 0) {
        return;
    }

    if (m_state.load() == State::Connecting) {
        int error = 0;
        socklen_t len = sizeof(error);
        if (getsockopt(m_fd, SOL_SOCKET, SO_ERROR, &error, &len) != 0) {
            error = errno;
        }

        if (error == 0) {
            State expected = State::Connecting;
            if (!m_state.compare_exchange_strong(expected, State::Connected)) {
                return;
            }
            m_connectDeadline = std::chrono::steady_clock::time_point::max();

            // 先投递 OnConnect(true)：确保即便随后 flush 待发数据失败，上层也已收到
            // 配对的连接成功通知（再跟 OnDisconnect(SendFailed)），不会出现孤儿
            // OnDisconnect。与 Win 版 HandleConnectCompleteUnlocked 的顺序一致。
            Event event;
            event.type = EventType::Connect;
            event.connectSuccess = true;
            event.errType = APITcpClientErrType::None;
            event.sysErrNo = 0;
            event.generation = m_generation.load();
            PushEvent(std::move(event));

            // flush 连接前缓存的待发数据。
            int32_t sendErrno = 0;
            {
                std::lock_guard<std::mutex> sendLock(m_sendMutex);
                sendErrno = TrySend();
                if (sendErrno == 0) {
                    UpdatePollEventsUnlocked();
                }
            }
            if (sendErrno != 0) {
                HandleDisconnectUnlocked(
                    true, APITcpClientErrType::SendFailed,
                    APITcpClientDisConnectType::SendFailed, sendErrno);
                return;
            }
        } else {
            HandleDisconnectUnlocked(false, APITcpClientErrType::ConnectFailed,
                                     APITcpClientDisConnectType::Unknown);
            Event event;
            event.type = EventType::Connect;
            event.connectSuccess = false;
            event.errType = APITcpClientErrType::ConnectFailed;
            event.sysErrNo = error;
            event.generation = m_generation.load();
            PushEvent(std::move(event));
        }
        return;
    }

    if (m_state.load() == State::Connected) {
        int32_t sendErrno = 0;
        {
            std::lock_guard<std::mutex> sendLock(m_sendMutex);
            sendErrno = TrySend();
            if (sendErrno == 0) {
                UpdatePollEventsUnlocked();
            }
        }
        if (sendErrno != 0) {
            HandleDisconnectUnlocked(
                true, APITcpClientErrType::SendFailed,
                APITcpClientDisConnectType::SendFailed, sendErrno);
        }
    }
}

void APITcpClientPosix::OnPollError() {
    std::lock_guard<std::mutex> lock(m_closeMutex);
    if (m_fd < 0) {
        return;
    }

    int error = 0;
    socklen_t len = sizeof(error);
    if (getsockopt(m_fd, SOL_SOCKET, SO_ERROR, &error, &len) != 0) {
        error = errno;
    }

    const bool connecting = (m_state.load() == State::Connecting);
    // poll 报错：连接中不通过 OnDisconnect 通知（改由 OnConnect 报失败）；
    // 已连接时按 poll 返回错误归类（PollReturnError），断开原因归为 RecvFailed
    //（含对端挂断 / POLLERR 等链路问题）。
    HandleDisconnectUnlocked(!connecting, APITcpClientErrType::PollReturnError,
                             APITcpClientDisConnectType::RecvFailed, error);
    if (connecting) {
        Event event;
        event.type = EventType::Connect;
        event.connectSuccess = false;
        event.errType = APITcpClientErrType::ConnectFailed;
        event.sysErrNo = error;
        event.generation = m_generation.load();
        PushEvent(std::move(event));
    }
}

void APITcpClientPosix::OnTimerTick() {
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
        event.sysErrNo = ETIMEDOUT;
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

void APITcpClientPosix::HandleDisconnectUnlocked(
    bool isNotifyDisconnect, APITcpClientErrType errType,
    APITcpClientDisConnectType disconnectType, int32_t sysErrNo) {
    State expected = State::Connecting;
    if (!m_state.compare_exchange_strong(expected, State::Disconnecting)) {
        expected = State::Connected;
        if (!m_state.compare_exchange_strong(expected, State::Disconnecting)) {
            return;
        }
    }

    FinishCloseUnlocked();

    if (isNotifyDisconnect) {
        Event event;
        event.type = EventType::Disconnect;
        event.errType = errType;
        event.disconnectType = disconnectType;
        event.sysErrNo = sysErrNo;
        event.generation = m_generation.load();
        PushEvent(std::move(event));
    }
}

void APITcpClientPosix::FinishCloseUnlocked() {
    if (m_fd >= 0) {
        PollPoller::Instance().Remove(this, m_fd);
        close(m_fd);
        m_fd = -1;
    }
    {
        std::lock_guard<std::mutex> lock(m_sendMutex);
        m_sendBuffer.clear();
        m_sendOffset = 0;
    }
    ClearEventQueue();
    // 使仍在投递路上的旧 Recv 失效
    m_generation.fetch_add(1);
    m_pollEvents = 0;
    m_connectDeadline = std::chrono::steady_clock::time_point::max();
    m_state.store(State::Idle);
}

void APITcpClientPosix::Close() {
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
    // 必须在释放 m_closeMutex 后再 join，否则回调中的 Send/Close 会死锁
    StopRecvThread();
}

#endif
