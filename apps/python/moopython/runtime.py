"""Asynchronous native updater; no pip changes inside the frozen application."""
import json,pathlib,sys
from PySide6.QtCore import QObject,QProcess,Signal
class OpenDRuntime(QObject):
    status=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent); self.process=None
        self.directory=pathlib.Path(sys.executable).resolve().parent.parent/'Resources/OpenD'
    @property
    def available(self): return (self.directory/'OpenDManager').is_file()
    def run(self,action='launch'):
        if not self.available:
            self.status.emit('当前是源码运行；请打包后使用内置 OpenD，或连接已安装的官方 OpenD'); return
        if self.process is not None:
            self.status.emit('OpenD 正在启动或检查更新，请稍候'); return
        try: version=json.loads((self.directory/'opend.json').read_text())['version']
        except (OSError,ValueError,KeyError) as error:
            self.status.emit(f'OpenD 元数据读取失败：{error}'); return
        process=QProcess(self); self.process=process; process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda:self.status.emit(bytes(process.readAllStandardOutput()).decode('utf-8',errors='replace').strip()))
        def finished(*_): self.process=None; process.deleteLater()
        process.finished.connect(finished)
        process.errorOccurred.connect(lambda error:(self.status.emit(f'OpenD 更新器无法启动：{process.errorString()}'),finished()) if error==QProcess.ProcessError.FailedToStart else None)
        flags={'launch':['--launch'],'update':['--force'],'rollback':['--rollback'],'check':[]}[action]
        self.status.emit('正在启动官方 OpenD…' if action=='launch' else '正在检查 OpenD 更新…' if action=='update' else '正在回退 OpenD…')
        process.start(str(self.directory/'OpenDManager'),['--bundle',str(self.directory/'moomoo_OpenD.app'),'--version',version,*flags])
