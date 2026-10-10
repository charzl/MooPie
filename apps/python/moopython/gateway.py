"""Official SDK calls run in one QThread; SDK pushes cross to the GUI via signals."""
import socket
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from .market import PERIODS

class GatewayWorker(QObject):
    event = Signal(str, str, object)
    finished = Signal()

    def __init__(self, sdk_factory=None):
        super().__init__()
        self.ctx = None
        self.sdk = None
        self.token = ""
        self.subscriptions = set()
        self.sdk_factory = sdk_factory

    def close_context(self):
        if self.ctx is not None:
            context, self.ctx = self.ctx, None
            context.close()
        self.subscriptions.clear()

    @Slot(object)
    def execute(self, command):
        op, token = command["op"], command["token"]
        try:
            if op == "shutdown":
                self.token = ""
                self.close_context()
                self.finished.emit()
                return
            if op == "disconnect":
                self.token = token
                self.close_context()
                self.event.emit(token, "disconnected", None)
                return
            if op == "connect":
                self.token = token
                self.close_context()
                host, port = command["host"], int(command["port"])
                if host not in ("127.0.0.1", "localhost", "::1") or not 1 <= port <= 65535:
                    raise ValueError("此版本仅支持本机 OpenD，端口范围 1–65535")
                if self.sdk_factory is None:
                    # Fail quickly if the gateway is not listening, before importing the SDK.
                    with socket.create_connection((host, port), timeout=2):
                        pass
                    import moomoo as sdk
                else:
                    sdk = self.sdk_factory()
                self.sdk = sdk
                self.ctx = sdk.OpenQuoteContext(host=host, port=port)
                self.install_handlers(token)
                ret, data = self.ctx.get_global_state()
                if ret != sdk.RET_OK:
                    raise RuntimeError(str(data))
                self.event.emit(token, "connected", None)
                self.refresh(command.get("symbols", []))
                return
            if token != self.token or self.ctx is None:
                return
            if op == "refresh":
                self.refresh(command["symbols"])
            elif op == "chart":
                self.chart(command)
            elif op == "remove":
                types = [self.sdk.SubType.QUOTE]
                types.extend(key[1] for key in self.subscriptions if key[0] == command["code"])
                ret, data = self.ctx.unsubscribe([command["code"]], list(set(types)))
                if ret != self.sdk.RET_OK:
                    self.event.emit(token, "message", f"取消订阅：{data}")
                else:
                    self.subscriptions = {key for key in self.subscriptions if key[0] != command["code"]}
            elif op == "state":
                ret, data = self.ctx.get_global_state()
                if ret != self.sdk.RET_OK:
                    self.event.emit(token, "lost", str(data))
        except Exception as error:
            if op == "shutdown":
                self.finished.emit()
            elif op == "connect":
                try:
                    self.close_context()
                except Exception:
                    pass
                self.event.emit(token, "connection_error", f"连接失败：{error}")
            elif op == "chart":
                self.event.emit(token, "chart_error", {"request": command["request"], "message": str(error)})
            else:
                self.event.emit(token, "message", str(error))

    def install_handlers(self, token):
        worker, sdk = self, self.sdk

        class QuoteHandler(sdk.StockQuoteHandlerBase):
            def on_recv_rsp(self, response):
                ret, data = super().on_recv_rsp(response)
                if ret == sdk.RET_OK:
                    worker.event.emit(token, "quotes", data.to_dict("records"))
                else:
                    worker.event.emit(token, "message", f"报价推送：{data}")
                return ret, data

        class CandleHandler(sdk.CurKlineHandlerBase):
            def on_recv_rsp(self, response):
                ret, data = super().on_recv_rsp(response)
                if ret == sdk.RET_OK:
                    worker.event.emit(token, "candle_push", data.to_dict("records"))
                else:
                    worker.event.emit(token, "message", f"K 线推送：{data}")
                return ret, data

        self.ctx.set_handler(QuoteHandler())
        self.ctx.set_handler(CandleHandler())

    def refresh(self, symbols):
        errors = []
        for code in symbols:
            ret, data = self.ctx.subscribe([code], [self.sdk.SubType.QUOTE], subscribe_push=True)
            if ret != self.sdk.RET_OK:
                errors.append(f"{code}：{data}")
                continue
            ret, data = self.ctx.get_stock_quote([code])
            if ret == self.sdk.RET_OK:
                self.event.emit(self.token, "quotes", data.to_dict("records"))
            else:
                errors.append(f"{code}：{data}")
        self.event.emit(self.token, "refreshed", "；".join(errors) if errors else "已更新 · 行情实时性取决于账户权限和市场状态")

    def chart(self, command):
        code, period = command["code"], command["period"]
        subtype = getattr(self.sdk.SubType, PERIODS[period])
        key = (code, subtype)
        if key not in self.subscriptions:
            if len(self.subscriptions) >= 60:
                raise RuntimeError("本次连接已订阅 60 组 K 线，请重新连接释放订阅")
            ret, data = self.ctx.subscribe([code], [subtype], subscribe_push=True)
            if ret != self.sdk.RET_OK:
                raise RuntimeError(str(data))
            self.subscriptions.add(key)
        ret, data = self.ctx.get_cur_kline(code, 200, ktype=subtype, autype=self.sdk.AuType.QFQ)
        if ret != self.sdk.RET_OK:
            raise RuntimeError(str(data))
        self.event.emit(self.token, "candles", {"request": command["request"], "rows": data.to_dict("records")})

class Gateway(QObject):
    command = Signal(object)
    event = Signal(str, str, object)
    stopped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = QThread(self)
        self.worker = GatewayWorker()
        self.worker.moveToThread(self.thread)
        self.command.connect(self.worker.execute, Qt.ConnectionType.QueuedConnection)
        self.worker.event.connect(self.event)
        self.worker.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.stopped)
        self.thread.start()

    def send(self, op, token, **fields):
        self.command.emit(dict(op=op, token=token, **fields))

    def shutdown(self):
        self.send("shutdown", "")
