"""Asynchronous native updater; no pip changes inside the frozen application."""
import json,pathlib,sys,tempfile
from PySide6.QtCore import QObject,QProcess,Signal
class OpenDRuntime(QObject):
    status=Signal(str)
    def __init__(self,parent=None):
        super().__init__(parent); self.process=None
        self.directory=pathlib.Path(sys.executable).resolve().parent.parent/'Resources/OpenD'
        self.workspace=tempfile.TemporaryDirectory(prefix='moopie-opend-')
        self.output=pathlib.Path(self.workspace.name)/'result.json'
    @property
    def available(self): return sys.platform=='darwin' and (self.directory/'opend.json').is_file()
    def run(self,action='launch'):
        if not self.available:
            self.status.emit('请启动并登录官方 OpenD，再点击分析；默认连接本机 11111 端口'); return
        if self.process is not None:
            self.status.emit('OpenD 正在启动或检查更新，请稍候'); return
        try: version=json.loads((self.directory/'opend.json').read_text())['version']
        except (OSError,ValueError,KeyError) as error:
            self.status.emit(f'OpenD 元数据读取失败：{error}'); return
        process=QProcess(self); self.process=process; process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(lambda:self.status.emit(bytes(process.readAllStandardOutput()).decode('utf-8',errors='replace').strip()))
        self.output.unlink(missing_ok=True)
        def finished(code=0,*_):
            if self.process is not process: return
            try:
                result=json.loads(self.output.read_text(encoding='utf-8'))
                messages=result.get('messages',[])
                if messages: self.status.emit('\n'.join(messages))
                elif result.get('error'): self.status.emit(result['error'])
            except (OSError,ValueError):
                if code: self.status.emit(f'OpenD 管理器退出：{code}')
            self.process=None; process.deleteLater()
        process.finished.connect(finished)
        process.errorOccurred.connect(lambda error:(self.status.emit(f'OpenD 更新器无法启动：{process.errorString()}'),finished()) if error==QProcess.ProcessError.FailedToStart else None)
        flags={'launch':['--launch'],'update':['--force'],'rollback':['--rollback'],'check':[]}[action]
        self.status.emit('正在启动官方 OpenD…' if action=='launch' else '正在检查 OpenD 更新…' if action=='update' else '正在回退 OpenD…')
        arguments=['opend'] if getattr(sys,'frozen',False) else ['-m','moopython.opend_manager']
        process.start(sys.executable,[*arguments,'--metadata',str(self.directory/'opend.json'),
                                     '--output',str(self.output),*flags])
