from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QRectF, QPointF
from PySide6.QtGui import QPainterPath, QPen, QColor, QFont, QLinearGradient
from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from .market import NAMES
from .chart import BG, TEXT, MUTED, RED, GREEN

class QuoteTableModel(QAbstractTableModel):
    headers = ["名称代码", "走势", "最新价", "涨跌幅", "涨跌额"]

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.rows = []
        self.filter = "全部"
        self.search = ""
        self.sort_column = -1
        self.sort_order = Qt.SortOrder.DescendingOrder
        self.rebuild()

    def rebuild(self):
        self.beginResetModel()
        state = self.state
        self.rows = [code for code in state.symbols if
                     (self.filter == "全部" or self.filter == "特别关注" and code in state.favorites or
                      self.filter == "美股" and code.startswith("US.") or self.filter == "港股" and code.startswith("HK.") or
                      self.filter == "沪深" and code.startswith(("SH.","SZ."))) and
                     (not self.search or self.search.upper() in code or
                      self.search.casefold() in (state.quotes.get(code).name if code in state.quotes else getattr(state, 'names', {}).get(code, NAMES.get(code,code))).casefold())]
        if self.sort_column >= 0:
            def key(code):
                q = state.quotes.get(code)
                if self.sort_column == 0:
                    return code
                if not q:
                    return float("-inf")
                return {2:q.price,3:q.percent,4:q.change}.get(self.sort_column,0)
            self.rows.sort(key=key,reverse=self.sort_order == Qt.SortOrder.DescendingOrder)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.headers)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        code = self.rows[index.row()]
        quote = self.state.quotes.get(code)
        if role == Qt.ItemDataRole.UserRole:
            return code
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return quote.name if quote else getattr(self.state, 'names', {}).get(code, NAMES.get(code,code))
            if not quote:
                return "—"
            return {1:"",2:f"{quote.price:.3f}",3:f"{quote.percent:+.2f}%",4:f"{quote.change:+.3f}"}.get(index.column(),"")
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.headers[section]
        return None

    def sort(self, column, order):
        if column == 1:
            return
        self.sort_column, self.sort_order = column, order
        self.rebuild()

class QuoteDelegate(QStyledItemDelegate):
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state

    def paint(self, painter, option, index):
        code = index.data(Qt.ItemDataRole.UserRole)
        quote = self.state.quotes.get(code)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        color = QColor(RED if (quote and quote.change > 0) == self.state.red_up else GREEN) if quote else QColor(MUTED)
        painter.save()
        rect = option.rect
        painter.fillRect(rect,QColor("#1d2027" if selected else BG))
        if selected:
            painter.setPen(QPen(QColor("#aeb6c6"),.8))
            painter.drawLine(rect.topLeft(),rect.topRight())
            painter.drawLine(rect.bottomLeft(),rect.bottomRight())
        if index.column() == 0:
            painter.setFont(QFont("Arial",11,QFont.Weight.DemiBold))
            painter.setPen(QColor(TEXT))
            name = quote.name if quote else getattr(self.state, 'names', {}).get(code, NAMES.get(code,code))
            name = painter.fontMetrics().elidedText(name,Qt.TextElideMode.ElideRight,rect.width()-12)
            painter.drawText(rect.adjusted(8,6,-4,-25),Qt.AlignmentFlag.AlignVCenter,name)
            painter.setFont(QFont("Arial",9))
            painter.setPen(QColor(MUTED))
            painter.drawText(rect.adjusted(8,31,-4,-6),Qt.AlignmentFlag.AlignVCenter,code.split(".",1)[1]+(" ★" if code in self.state.favorites else ""))
        elif index.column() == 1:
            values = self.state.sparks.get(code,[])
            if len(values)>1:
                r = QRectF(rect).adjusted(4,16,-4,-16)
                lo, hi = min(values), max(values)
                span = max(hi-lo,.001)
                path = QPainterPath()
                for i,value in enumerate(values):
                    point = QPointF(r.left()+r.width()*i/(len(values)-1),r.bottom()-r.height()*(value-lo)/span)
                    if i == 0:
                        path.moveTo(point)
                    else:
                        path.lineTo(point)
                area = QPainterPath(path)
                area.lineTo(r.bottomRight()); area.lineTo(r.bottomLeft()); area.closeSubpath()
                gradient = QLinearGradient(r.topLeft(),r.bottomLeft())
                faded = QColor(color); faded.setAlpha(55)
                clear = QColor(color); clear.setAlpha(0)
                gradient.setColorAt(0,faded); gradient.setColorAt(1,clear)
                painter.fillPath(area,gradient)
                painter.setPen(QPen(color,1)); painter.drawPath(path)
        else:
            painter.setFont(QFont("Arial",11,QFont.Weight.DemiBold))
            painter.setPen(color)
            if index.column() == 3 and quote:
                badge = QRectF(rect).adjusted(6,18,-6,-18)
                background = QColor(color); background.setAlpha(155)
                painter.fillRect(badge,background)
                painter.setPen(QColor("white"))
                painter.drawText(badge,Qt.AlignmentFlag.AlignCenter,index.data())
            else:
                painter.drawText(rect.adjusted(3,0,-8,0),Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,index.data())
        painter.restore()
