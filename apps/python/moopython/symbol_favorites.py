"""Suggestion-row favorite rendering and isolated Watchlist membership writes."""
import json
from pathlib import Path
import sys

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem


def favorite_rect(rect):
    return QRect(rect.right()-43, rect.center().y()-18, 36, 36)


class SuggestionDelegate(QStyledItemDelegate):
    def __init__(self, suggestions):
        super().__init__(suggestions.view)
        self.suggestions = suggestions

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        return QSize(size.width()+44, max(36,size.height()))

    def paint(self, painter, option, index):
        row = index.data(Qt.ItemDataRole.UserRole)
        if not row: return super().paint(painter,option,index)
        owner = self.suggestions
        styled = QStyleOptionViewItem(option); self.initStyleOption(styled,index)
        styled.text = ''
        painter.save()
        owner.view.style().drawControl(QStyle.ControlElement.CE_ItemViewItem,styled,painter,owner.view)
        painter.setFont(option.font); painter.setPen(QColor(owner.ui.colors['text']))
        text_rect = option.rect.adjusted(12,0,-52,0)
        label = option.fontMetrics.elidedText(index.data(),Qt.TextElideMode.ElideRight,max(0,text_rect.width()))
        painter.drawText(text_rect,Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,label)
        heart = favorite_rect(option.rect)
        active = row['code'] in owner.members
        color = ('#ee89aa' if owner.ui.effective_theme=='dark' else '#b53662') if active else owner.ui.colors['muted']
        if owner.adder.process is not None: color = owner.ui.colors['muted']
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(heart.center().x()-11,heart.center().y()-10)
        path = QPainterPath(); path.moveTo(11,19)
        path.cubicTo(9,17,1,12,1,6); path.cubicTo(1,0,8,-1,11,4)
        path.cubicTo(14,-1,21,0,21,6); path.cubicTo(21,12,13,17,11,19)
        path.closeSubpath()
        painter.setPen(QPen(QColor(color),1.6))
        painter.setBrush(QColor(color) if active else Qt.BrushStyle.NoBrush)
        painter.drawPath(path); painter.restore()


class WatchlistAdder(QObject):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(self, parent):
        super().__init__(parent)
        self.owner = parent
        self.process = None
        self.symbol = None
        self.result_path = Path(parent.workspace.name)/'favorite.json'

    def add(self, symbol):
        if self.process is not None: return
        self.symbol = symbol
        self.result_path.unlink(missing_ok=True)
        process = QProcess(self); self.process = process
        environment = QProcessEnvironment.systemEnvironment(); environment.insert('PYTHONUTF8','1')
        process.setProcessEnvironment(environment)
        process.setStandardOutputFile(str(self.result_path.with_suffix('.stdout.log')))
        process.setStandardErrorFile(str(self.result_path.with_suffix('.stderr.log')))
        args = ['research'] if getattr(sys,'frozen',False) else ['-X','utf8','-m','moopython.research_cli']
        args += ['add',symbol,'--port',str(self.owner.port.value()),'--output',str(self.result_path)]
        process.finished.connect(lambda code,status:self.finished(code))
        process.errorOccurred.connect(lambda error:self.finished(-1) if error==QProcess.ProcessError.FailedToStart else None)
        process.start(sys.executable,args)

    def finished(self, code):
        process = self.process
        if process is None: return
        self.process = None
        try:
            result = json.loads(self.result_path.read_text(encoding='utf-8'))
            if code or result.get('error'): raise ValueError(result.get('error') or process.errorString())
            if result.get('action')!='watchlist_add' or result.get('symbol')!=self.symbol:
                raise ValueError('Unexpected Watchlist result')
            self.completed.emit(result)
        except (ValueError,OSError) as error: self.failed.emit(str(error))
        finally:
            self.symbol = None; process.deleteLater()

    def shutdown(self):
        if self.process is not None:
            process=self.process; process.blockSignals(True); process.kill(); process.waitForFinished(2000)
            process.deleteLater(); self.process=None
