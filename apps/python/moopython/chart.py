"""Qt raster chart: cached plot, lightweight crosshair overlay, no idle redraw timer."""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF, QPixmap, QFont
from PySide6.QtWidgets import QWidget
from .market import averages, compact

BG = "#15161b"
TEXT = "#dce0e9"
MUTED = "#939caa"
RED = "#ed3057"
GREEN = "#00a86b"
ORANGE = "#ff7109"

class CandleChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars = []
        self.period = "日K"
        self.red_up = True
        self.show_ma = True
        self.line_mode = False
        self.visible_count = 160
        self.hover = None
        self.message = ""
        self.cache = None
        self.metrics = None
        self.setMouseTracking(True)
        self.setMinimumSize(400, 280)

    def set_bars(self, bars, period=None):
        self.bars = bars
        if period:
            self.period = period
        self.invalidate()

    def invalidate(self):
        self.cache = None
        self.update()

    def zoom(self, delta):
        self.visible_count = max(30, min(200, self.visible_count + delta))
        self.invalidate()

    def wheelEvent(self, event):
        self.zoom(-20 if event.angleDelta().y() > 0 else 20)
        event.accept()

    def mouseMoveEvent(self, event):
        self.hover = event.position()
        self.update()

    def leaveEvent(self, event):
        self.hover = None
        self.update()

    def resizeEvent(self, event):
        self.cache = None
        super().resizeEvent(event)

    def text(self, p, x, y, value, color=MUTED, width=200, align=Qt.AlignmentFlag.AlignLeft):
        p.setPen(QColor(color))
        p.drawText(QRectF(x, y-8, width, 18), align | Qt.AlignmentFlag.AlignVCenter, value)

    def render_plot(self):
        ratio = self.devicePixelRatioF()
        pixmap = QPixmap(round(self.width()*ratio), round(self.height()*ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(QColor(BG))
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setFont(QFont("Menlo", 9))
        bars = self.bars[-self.visible_count:]
        self.metrics = None
        if not bars:
            p.end()
            return pixmap
        left, top, width = 10, 38, max(1, self.width()-82)
        price_height = max(60, self.height()*.76-top)
        volume_top = top+price_height+28
        volume_height = max(20, self.height()-volume_top-28)
        lower, upper = min(b.low for b in bars), max(b.high for b in bars)
        padding = max((upper-lower)*.07, abs(upper)*.002, .001)
        low, high = lower-padding, upper+padding
        span, dx = high-low, width/len(bars)
        body_width = max(1, dx*.65)
        y = lambda price: top+(high-price)/span*price_height
        x = lambda index: left+(index+.5)*dx
        self.metrics = (left, top, width, price_height, volume_top, volume_height, dx, bars)
        p.setPen(QPen(QColor("#242630"), .6))
        for i in range(9):
            value = high-span*i/8
            p.drawLine(QPointF(left, y(value)), QPointF(left+width, y(value)))
            self.text(p, left+width+7, y(value), f"{value:.3f}", width=66)
            p.setPen(QPen(QColor("#242630"), .6))
        for i in range(7):
            xx = left+width*i/6
            p.drawLine(QPointF(xx, top), QPointF(xx, self.height()-24))
            index = min(len(bars)-1, len(bars)*i//6)
            value = bars[index].time[11:16] if self.period in ("1分", "5分", "15分") else bars[index].time[5:10]
            label_x = xx if i == 0 else xx-62 if i == 6 else xx-31
            self.text(p, label_x, self.height()-12, value, width=62,
                      align=Qt.AlignmentFlag.AlignLeft if i == 0 else Qt.AlignmentFlag.AlignRight if i == 6 else Qt.AlignmentFlag.AlignHCenter)
            p.setPen(QPen(QColor("#242630"), .6))
        if self.line_mode:
            p.setPen(QPen(QColor("#21c9e9"), 1.3))
            p.drawPolyline(QPolygonF([QPointF(x(i), y(b.close)) for i, b in enumerate(bars)]))
        max_volume = max(1, max(b.volume for b in bars))
        for i, bar in enumerate(bars):
            color = QColor(RED if (bar.close >= bar.open) == self.red_up else GREEN)
            p.setPen(QPen(color, 1))
            if not self.line_mode:
                p.drawLine(QPointF(x(i), y(bar.high)), QPointF(x(i), y(bar.low)))
                rect = QRectF(x(i)-body_width/2, min(y(bar.open), y(bar.close)), body_width, max(1, abs(y(bar.open)-y(bar.close))))
                if bar.close >= bar.open:
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    p.drawRect(rect)
                else:
                    p.fillRect(rect, color)
            h = bar.volume/max_volume*volume_height
            p.fillRect(QRectF(x(i)-body_width/2, volume_top+volume_height-h, body_width, h), color)
        if self.show_ma:
            offset = len(self.bars)-len(bars)
            for j, (period, color) in enumerate(zip((5,10,20,60), (ORANGE,"#df61cf",GREEN,"#21c9e9"))):
                values = averages(self.bars, period)
                points = [QPointF(x(i), y(value)) for i, value in enumerate(values[offset:]) if value is not None]
                p.setPen(QPen(QColor(color), 1))
                p.drawPolyline(QPolygonF(points))
                if values[-1] is not None:
                    self.text(p, 12+j*132, 17, f"MA{period}: {values[-1]:.3f}", color, width=130)
        last = bars[-1]
        p.setPen(QPen(QColor(RED if (last.close >= last.open) == self.red_up else GREEN), .8, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(left,y(last.close)), QPointF(left+width,y(last.close)))
        self.text(p, left, volume_top-13, f"成交量  {compact(last.volume)}", width=260)
        p.end()
        return pixmap

    def paintEvent(self, event):
        if self.cache is None:
            self.cache = self.render_plot()
        p = QPainter(self)
        p.drawPixmap(0, 0, self.cache)
        p.setFont(QFont("Menlo", 9))
        if self.message:
            p.setPen(QColor(MUTED))
            p.drawText(self.rect().adjusted(40,40,-40,-40), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
        elif self.hover is not None and self.metrics:
            left, top, width, height, vtop, vh, dx, bars = self.metrics
            if left <= self.hover.x() <= left+width:
                index = max(0,min(len(bars)-1,int((self.hover.x()-left)/dx)))
                xx, yy = left+(index+.5)*dx, max(top,min(top+height,self.hover.y()))
                p.setPen(QPen(QColor(MUTED), .7, Qt.PenStyle.DashLine))
                p.drawLine(QPointF(xx,top),QPointF(xx,vtop+vh))
                p.drawLine(QPointF(left,yy),QPointF(left+width,yy))
                bar = bars[index]
                p.fillRect(QRectF(8,0,min(width,680),29),QColor("#1b1e24"))
                self.text(p,14,14,f"{bar.time}  开 {bar.open:.3f}  高 {bar.high:.3f}  低 {bar.low:.3f}  收 {bar.close:.3f}",TEXT,width=680)
        p.end()
