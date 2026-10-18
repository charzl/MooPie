"""Draw the existing app icon with the desktop's Qt dependency."""
import sys
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter, QPainterPath, QPen


def render(destination):
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Match the original Cartesian drawing coordinates.
    painter.translate(0, 1024); painter.scale(1, -1)
    gradient = QLinearGradient(QPointF(200, 180), QPointF(824, 844))
    gradient.setColorAt(0, QColor.fromRgbF(.16, .20, .27)); gradient.setColorAt(1, QColor.fromRgbF(.06, .08, .12))
    painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(gradient)
    painter.drawRoundedRect(QRectF(80, 80, 864, 864), 190, 190)
    def line(points, color, width):
        path = QPainterPath(QPointF(*points[0]))
        for point in points[1:]: path.lineTo(QPointF(*point))
        painter.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
    line([(248, 728), (248, 290), (772, 290)], QColor.fromRgbF(.43, .43, .43, .45), 30)
    orange = QColor.fromRgbF(1, .44, .035)
    for x, bottom, top in [(350, 365, 480), (478, 460, 590), (606, 510, 690)]:
        line([(x, bottom - 33), (x, top + 33)], orange, 13)
        painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(orange)
        painter.drawRoundedRect(QRectF(x - 26, bottom, 52, top - bottom), 8, 8)
    white = QColor.fromRgbF(.84, .94, 1)
    line([(330, 355), (458, 428), (585, 425), (743, 605)], white, 23)
    line([(677, 602), (748, 618), (744, 543)], white, 23)
    painter.end()
    if not image.save(destination): raise OSError('Unable to save app icon')


if __name__ == '__main__': render(sys.argv[1])
