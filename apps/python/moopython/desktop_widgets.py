"""Native controls with a consistent, reserved dropdown indicator area."""
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QComboBox


class SelectBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty('vectorArrow',True)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(self.palette().color(QPalette.ColorRole.Text),1.5))
        x,y=self.width()-21,self.height()/2
        path=QPainterPath(QPointF(x-4,y-2))
        path.lineTo(x,y+2); path.lineTo(x+4,y-2)
        painter.drawPath(path)
