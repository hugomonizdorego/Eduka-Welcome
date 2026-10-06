"""Painted widgets for the Welcome Screen: no image plugins or icon themes needed."""
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
    QRadialGradient,
)
from PyQt6.QtWidgets import QAbstractButton, QSizePolicy, QWidget
from .eduka_desktop import (
    DARK_THEMES, GLASS_THEMES, MULTI_COLORS, THEME_LOW, THEME_MULTI, THEME_SWATCHES,
)

GREEN = "#00856e"
DEEP = "#0b4f45"


def glyph(kind, color="#00856e", size=28):
    """Simple line icons drawn with QPainter, so they look the same everywhere."""
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(1.6, size / 13), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
               Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    s = size
    u = s / 24.0

    def r(x, y, w, h):
        return QRectF(x * u, y * u, w * u, h * u)

    if kind == "clock":
        p.drawEllipse(r(3, 3, 18, 18))
        p.drawLine(QPointF(12 * u, 12 * u), QPointF(12 * u, 7 * u))
        p.drawLine(QPointF(12 * u, 12 * u), QPointF(16 * u, 14 * u))
    elif kind == "desktop":
        p.drawRoundedRect(r(2.5, 4, 19, 13), 2 * u, 2 * u)
        p.drawLine(QPointF(9 * u, 21 * u), QPointF(15 * u, 21 * u))
        p.drawLine(QPointF(12 * u, 17 * u), QPointF(12 * u, 21 * u))
    elif kind == "menu":
        for x in (4, 10.5, 17):
            for y in (4, 10.5, 17):
                p.drawRoundedRect(r(x, y, 3.5, 3.5), u, u)
    elif kind == "panel":
        p.drawRoundedRect(r(2.5, 15, 19, 5), 2 * u, 2 * u)
        p.drawRoundedRect(r(5, 4, 14, 8), 1.5 * u, 1.5 * u)
        p.drawPoint(QPointF(5.5 * u, 17.5 * u))
    elif kind == "settings":
        p.drawEllipse(r(8.5, 8.5, 7, 7))
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(QPointF(12 * u + 6.5 * u * math.cos(a), 12 * u + 6.5 * u * math.sin(a)),
                       QPointF(12 * u + 9 * u * math.cos(a), 12 * u + 9 * u * math.sin(a)))
    elif kind == "apps":
        p.drawRoundedRect(r(3, 3, 7.5, 7.5), 2 * u, 2 * u)
        p.drawRoundedRect(r(13.5, 3, 7.5, 7.5), 2 * u, 2 * u)
        p.drawRoundedRect(r(3, 13.5, 7.5, 7.5), 2 * u, 2 * u)
        p.drawLine(QPointF(17.25 * u, 14 * u), QPointF(17.25 * u, 20.5 * u))
        p.drawLine(QPointF(14 * u, 17.25 * u), QPointF(20.5 * u, 17.25 * u))
    elif kind == "heart":
        path = QPainterPath(QPointF(12 * u, 20 * u))
        path.cubicTo(QPointF(2 * u, 13 * u), QPointF(3 * u, 4 * u), QPointF(12 * u, 8 * u))
        path.cubicTo(QPointF(21 * u, 4 * u), QPointF(22 * u, 13 * u), QPointF(12 * u, 20 * u))
        p.drawPath(path)
    elif kind == "people":
        p.drawEllipse(r(5, 4, 6, 6))
        p.drawArc(r(2, 12, 12, 10), 0, 180 * 16)
        p.drawEllipse(r(14, 6, 5, 5))
        p.drawArc(r(12.5, 13, 9, 8), 0, 180 * 16)
    elif kind == "globe":
        p.drawEllipse(r(3, 3, 18, 18))
        p.drawEllipse(r(8, 3, 8, 18))
        p.drawLine(QPointF(3.5 * u, 12 * u), QPointF(20.5 * u, 12 * u))
    elif kind == "star":
        path = QPainterPath()
        for i in range(10):
            radius = 9 if i % 2 == 0 else 4
            a = -math.pi / 2 + i * math.pi / 5
            point = QPointF(12 * u + radius * u * math.cos(a), 12.5 * u + radius * u * math.sin(a))
            path.moveTo(point) if i == 0 else path.lineTo(point)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "book":
        p.drawRoundedRect(r(3, 4, 8.5, 15), u, u)
        p.drawRoundedRect(r(12.5, 4, 8.5, 15), u, u)
        p.drawLine(QPointF(5.5 * u, 8 * u), QPointF(9 * u, 8 * u))
        p.drawLine(QPointF(15 * u, 8 * u), QPointF(18.5 * u, 8 * u))
    elif kind == "shield":
        path = QPainterPath(QPointF(12 * u, 3 * u))
        path.lineTo(QPointF(20 * u, 6 * u))
        path.cubicTo(QPointF(20 * u, 14 * u), QPointF(16 * u, 19 * u), QPointF(12 * u, 21 * u))
        path.cubicTo(QPointF(8 * u, 19 * u), QPointF(4 * u, 14 * u), QPointF(4 * u, 6 * u))
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "chat":
        p.drawRoundedRect(r(3, 4, 18, 12), 3 * u, 3 * u)
        p.drawLine(QPointF(8 * u, 16 * u), QPointF(7 * u, 20.5 * u))
        p.drawLine(QPointF(7 * u, 20.5 * u), QPointF(12 * u, 16 * u))
    elif kind == "update":
        p.drawArc(r(4, 4, 16, 16), 30 * 16, 300 * 16)
        p.drawLine(QPointF(19.5 * u, 4 * u), QPointF(19 * u, 9 * u))
        p.drawLine(QPointF(19 * u, 9 * u), QPointF(14.5 * u, 8 * u))
    elif kind == "check":
        p.drawLine(QPointF(5 * u, 12.5 * u), QPointF(10 * u, 17.5 * u))
        p.drawLine(QPointF(10 * u, 17.5 * u), QPointF(19 * u, 7 * u))
    elif kind == "leaf":
        path = QPainterPath(QPointF(4 * u, 20 * u))
        path.cubicTo(QPointF(4 * u, 8 * u), QPointF(10 * u, 4 * u), QPointF(20 * u, 4 * u))
        path.cubicTo(QPointF(20 * u, 14 * u), QPointF(14 * u, 20 * u), QPointF(4 * u, 20 * u))
        p.drawPath(path)
        p.drawLine(QPointF(4 * u, 20 * u), QPointF(14 * u, 10 * u))
    elif kind == "code":
        p.drawLine(QPointF(8 * u, 7 * u), QPointF(3 * u, 12 * u))
        p.drawLine(QPointF(3 * u, 12 * u), QPointF(8 * u, 17 * u))
        p.drawLine(QPointF(16 * u, 7 * u), QPointF(21 * u, 12 * u))
        p.drawLine(QPointF(21 * u, 12 * u), QPointF(16 * u, 17 * u))
        p.drawLine(QPointF(13.5 * u, 5 * u), QPointF(10.5 * u, 19 * u))
    elif kind == "palette":
        path = QPainterPath()
        path.addEllipse(r(3, 3, 18, 17))
        p.drawPath(path)
        for x, y in ((8, 8), (12.5, 6.5), (16.5, 9), (7.5, 13)):
            p.drawEllipse(r(x - 0.8, y - 0.8, 1.6, 1.6))
        p.drawEllipse(r(13, 13, 4, 4))
    elif kind == "accessibility":
        p.drawEllipse(r(10, 2.5, 4, 4))
        p.drawLine(QPointF(4 * u, 9 * u), QPointF(20 * u, 9 * u))
        p.drawLine(QPointF(12 * u, 9 * u), QPointF(12 * u, 15 * u))
        p.drawLine(QPointF(12 * u, 15 * u), QPointF(8 * u, 21 * u))
        p.drawLine(QPointF(12 * u, 15 * u), QPointF(16 * u, 21 * u))
    else:
        p.drawEllipse(r(4, 4, 16, 16))
    p.end()
    return pixmap


def edukasaun_mark(size=96, light=True):
    """Fallback Edukasaun logo: an open book on a rounded tile."""
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    tile = QRectF(2, 2, size - 4, size - 4)
    gradient = QLinearGradient(tile.topLeft(), tile.bottomRight())
    gradient.setColorAt(0, QColor("#ffffff" if light else "#16a085"))
    gradient.setColorAt(1, QColor("#d8f3e8" if light else "#0b6355"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(tile, size * 0.26, size * 0.26)
    u = size / 24.0
    color = QColor(GREEN if light else "#ffffff")
    p.setPen(QPen(color, 1.6 * u, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    left = QPainterPath(QPointF(12 * u, 8 * u))
    left.cubicTo(QPointF(9.5 * u, 6.2 * u), QPointF(7 * u, 6 * u), QPointF(5 * u, 6.5 * u))
    left.lineTo(QPointF(5 * u, 17 * u))
    left.cubicTo(QPointF(7 * u, 16.5 * u), QPointF(9.5 * u, 16.8 * u), QPointF(12 * u, 18.5 * u))
    p.drawPath(left)
    right = QPainterPath(QPointF(12 * u, 8 * u))
    right.cubicTo(QPointF(14.5 * u, 6.2 * u), QPointF(17 * u, 6 * u), QPointF(19 * u, 6.5 * u))
    right.lineTo(QPointF(19 * u, 17 * u))
    right.cubicTo(QPointF(17 * u, 16.5 * u), QPointF(14.5 * u, 16.8 * u), QPointF(12 * u, 18.5 * u))
    p.drawPath(right)
    p.drawLine(QPointF(12 * u, 8 * u), QPointF(12 * u, 18.5 * u))
    p.setBrush(QColor("#f5b335"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(17.6 * u, 4.6 * u), 1.7 * u, 1.7 * u)
    p.end()
    return pixmap


def theme_preview(theme, width=150, height=88, selected=False):
    """Miniature of an Eduka theme: desktop, Eduka-Desktop window and panel."""
    surface, panel, accent, text = THEME_SWATCHES[theme]
    pixmap = QPixmap(width * 2, height * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, width, height), 10, 10)
    p.setClipPath(clip)
    background = QLinearGradient(0, 0, width, height)
    dark = theme in DARK_THEMES
    background.setColorAt(0, QColor("#3a4a46" if dark else "#a8dcc2"))
    background.setColorAt(1, QColor("#101413" if dark else "#3f8f6a"))
    p.fillRect(QRectF(0, 0, width, height), background)
    window = QColor(surface)
    if theme in GLASS_THEMES:
        window.setAlpha(185)
    radius = 3 if theme == THEME_LOW else 8
    p.setPen(QPen(QColor(255, 255, 255, 100), 1))
    p.setBrush(window)
    p.drawRoundedRect(QRectF(12, 9, width - 24, height - 34), radius, radius)
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(4):
        color = QColor(MULTI_COLORS[i * 2] if theme == THEME_MULTI else accent)
        if theme != THEME_MULTI:
            color.setAlpha(255 - i * 45)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(20 + i * 28, 18, 20, 20), 5, 5)
    p.setBrush(QColor(text))
    p.setOpacity(0.35)
    p.drawRoundedRect(QRectF(20, 45, width - 70, 4), 2, 2)
    p.setOpacity(1)
    bar = QColor(panel)
    if theme in GLASS_THEMES:
        bar.setAlpha(170)
    p.setBrush(bar)
    p.drawRoundedRect(QRectF(10, height - 19, width - 20, 13), 0 if theme == THEME_LOW else 6.5,
                      0 if theme == THEME_LOW else 6.5)
    p.setBrush(QColor(accent))
    p.drawRoundedRect(QRectF(15, height - 16.5, 18, 8), 4, 4)
    p.setClipping(False)
    if selected:
        p.setPen(QPen(QColor("#00856e"), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1.5, 1.5, width - 3, height - 3), 9, 9)
    p.end()
    return pixmap


def panel_style_preview(style, width=120, height=72, accent="#00a879"):
    """Small screen with Eduka-Panel in the chosen shape."""
    pixmap = QPixmap(width * 2, height * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(QPen(QColor("#9fb5ae"), 1.2))
    p.setBrush(QColor("#e6f2ed"))
    p.drawRoundedRect(QRectF(1, 1, width - 2, height - 2), 7, 7)
    if style == "full":
        bar, radius = QRectF(2, height - 14, width - 4, 12), 0
    elif style == "short":
        bar, radius = QRectF(width * 0.18, height - 17, width * 0.64, 10), 5
    elif style == "dock":
        bar, radius = QRectF(width * 0.31, height - 19, width * 0.38, 12), 6
    else:
        bar, radius = QRectF(8, height - 17, width - 16, 10), 5
    p.setPen(QPen(QColor(0, 0, 0, 40), 1))
    p.setBrush(QColor("#ffffff"))
    p.drawRoundedRect(bar, radius, radius)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(accent))
    p.drawRoundedRect(QRectF(bar.left() + 4, bar.top() + 2.5, 9, bar.height() - 5), 2, 2)
    for i in range(3):
        p.setBrush(QColor("#9fb5ae"))
        p.drawRoundedRect(QRectF(bar.left() + 17 + i * 9, bar.top() + 3, 6, bar.height() - 6), 1.5, 1.5)
    p.end()
    return pixmap


class ChoiceCard(QAbstractButton):
    """A checkable picture card with a caption (themes, panel styles, wallpapers)."""

    def __init__(self, pixmap, caption, value, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.pixmap = pixmap
        self.caption = caption
        self.value = value
        self.setText(caption)
        self.setAccessibleName(caption)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        size = pixmap.deviceIndependentSize()
        self.setFixedSize(int(size.width()) + 16, int(size.height()) + 40)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        checked = self.isChecked()
        p.setPen(QPen(QColor(GREEN if checked else ("#9fc9ba" if self.underMouse() else "#d5e6df")),
                      2.4 if checked else 1.2))
        p.setBrush(QColor("#eefaf4" if checked else "#ffffff"))
        p.drawRoundedRect(rect, 12, 12)
        p.drawPixmap(8, 8, self.pixmap)
        p.setPen(QColor("#0b4f45" if checked else "#36524c"))
        font = QFont(self.font())
        font.setBold(checked)
        font.setPointSizeF(font.pointSizeF() * 0.95)
        p.setFont(font)
        text_rect = QRectF(6, rect.bottom() - 30, rect.width() - 12, 26)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.caption)
        if checked:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(GREEN))
            p.drawEllipse(QPointF(rect.right() - 13, 13), 9, 9)
            p.setPen(QPen(QColor("white"), 2, cap=Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(rect.right() - 17, 13), QPointF(rect.right() - 14, 16))
            p.drawLine(QPointF(rect.right() - 14, 16), QPointF(rect.right() - 9, 10))
        if self.hasFocus():
            p.setPen(QPen(QColor(GREEN), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect.adjusted(3, 3, -3, -3), 10, 10)


class Swatch(QAbstractButton):
    """Round accent color button; an empty color means 'follow the theme'."""

    def __init__(self, color, name, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.color = color
        self.setToolTip(name)
        self.setAccessibleName(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(34, 34)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(17, 17)
        if self.isChecked():
            p.setPen(QPen(QColor("#173d37"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(center, 15, 15)
        p.setPen(QPen(QColor(0, 0, 0, 40), 1))
        if self.color:
            p.setBrush(QColor(self.color))
            p.drawEllipse(center, 11, 11)
        else:
            gradient = QLinearGradient(6, 6, 28, 28)
            for i, color in enumerate(("#00a879", "#1e9bd7", "#5b6ee1", "#f9a825")):
                gradient.setColorAt(i / 3, QColor(color))
            p.setBrush(gradient)
            p.drawEllipse(center, 11, 11)


class AnalogClock(QWidget):
    """Analog clock for the selected time zone."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zone = "Asia/Dili"
        self.accent = QColor(GREEN)
        self.setMinimumSize(170, 170)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFixedSize(190, 190)

    def set_zone(self, zone):
        self.zone = zone or "UTC"
        self.update()

    def paintEvent(self, event):
        now = datetime.now(ZoneInfo(self.zone))
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        p.translate(self.width() / 2, self.height() / 2)
        p.scale(side / 200.0, side / 200.0)
        glow = QRadialGradient(QPointF(0, 0), 100)
        glow.setColorAt(0, QColor("#ffffff"))
        glow.setColorAt(0.85, QColor("#effaf5"))
        glow.setColorAt(1, QColor("#d3eee3"))
        p.setPen(QPen(QColor("#bfe0d4"), 3))
        p.setBrush(glow)
        p.drawEllipse(QPointF(0, 0), 94, 94)
        for i in range(60):
            p.save()
            p.rotate(i * 6)
            if i % 5 == 0:
                p.setPen(QPen(QColor("#0b4f45"), 3.2, cap=Qt.PenCapStyle.RoundCap))
                p.drawLine(QPointF(0, -82), QPointF(0, -72))
            else:
                p.setPen(QPen(QColor("#9fc9ba"), 1.2))
                p.drawLine(QPointF(0, -82), QPointF(0, -78))
            p.restore()
        hour = (now.hour % 12) * 30 + now.minute * 0.5
        minute = now.minute * 6 + now.second * 0.1
        for angle, length, width, color in ((hour, 44, 6, "#0b4f45"), (minute, 64, 4, "#0b4f45"),
                                            (now.second * 6, 72, 1.8, self.accent.name())):
            p.save()
            p.rotate(angle)
            p.setPen(QPen(QColor(color), width, cap=Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(0, 10), QPointF(0, -length))
            p.restore()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.accent)
        p.drawEllipse(QPointF(0, 0), 5.5, 5.5)


class DesktopPreview(QWidget):
    """Live miniature of the desktop as Eduka-Desktop will draw it."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(230)
        self.panel = {}
        self.desktop = {}
        self.clock = "09:00"
        self.wallpaper = None
        self.wallpaper_path = ""

    def update_preview(self, panel, desktop, clock_text, wallpaper=""):
        self.panel, self.desktop, self.clock = panel, desktop, clock_text
        if wallpaper != self.wallpaper_path:
            self.wallpaper_path = wallpaper
            image = QPixmap(wallpaper) if wallpaper else QPixmap()
            self.wallpaper = None if image.isNull() else image
        self.update()

    def accent(self):
        theme = self.desktop.get("theme_style")
        return QColor(self.desktop.get("accent_color") or THEME_SWATCHES.get(theme, THEME_SWATCHES[
            "Eduka-Default-Theme"])[2])

    def paintEvent(self, event):
        if not self.panel:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        screen = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath()
        clip.addRoundedRect(screen, 16, 16)
        p.setClipPath(clip)
        theme = self.desktop.get("theme_style", "Eduka-Default-Theme")
        surface, panel_color, _accent, text = THEME_SWATCHES.get(theme, THEME_SWATCHES["Eduka-Default-Theme"])
        accent = self.accent()
        high_contrast = self.desktop.get("visual_accessibility")
        dark = theme in DARK_THEMES
        if self.wallpaper is not None:
            scaled = self.wallpaper.scaled(screen.size().toSize(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                           Qt.TransformationMode.SmoothTransformation)
            p.drawPixmap(int(screen.center().x() - scaled.width() / 2),
                         int(screen.center().y() - scaled.height() / 2), scaled)
        else:
            gradient = QLinearGradient(screen.topLeft(), screen.bottomRight())
            gradient.setColorAt(0, QColor("#2b3a37" if dark else "#8fd3bd"))
            gradient.setColorAt(0.55, QColor("#16201e" if dark else "#2f8f83"))
            gradient.setColorAt(1, QColor("#0b0f0e" if dark else "#12455f"))
            p.fillRect(screen, gradient)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 18))
            p.drawEllipse(QPointF(screen.width() * 0.82, screen.height() * 0.2), 120, 120)
            p.drawEllipse(QPointF(screen.width() * 0.1, screen.height() * 0.95), 90, 90)
        position = self.panel.get("position", "Bottom")
        vertical = position in ("Left", "Right")
        thickness = int(self.panel.get("height", 42)) * 0.62
        style = self.panel.get("panel_style", "floating")
        length_full = screen.height() if vertical else screen.width()
        length = {"full": length_full, "short": length_full * 0.64, "dock": length_full * 0.42}.get(
            style, length_full * self.panel.get("width_percent", 96) / 100 - 20)
        gap = 0 if style == "full" else 8
        start = (length_full - length) / 2
        if position == "Bottom":
            bar = QRectF(start, screen.bottom() - thickness - gap, length, thickness)
        elif position == "Top":
            bar = QRectF(start, gap + 1, length, thickness)
        elif position == "Left":
            bar = QRectF(gap + 1, start, thickness, length)
        else:
            bar = QRectF(screen.right() - thickness - gap, start, thickness, length)
        # Eduka-Desktop window (start menu) next to the panel.
        width_percent = self.desktop.get("width_percent", 98) / 100
        height_percent = self.desktop.get("height_percent", 92) / 100
        win_w, win_h = screen.width() * 0.55 * width_percent, screen.height() * 0.62 * height_percent
        if position == "Bottom":
            win = QRectF(screen.center().x() - win_w / 2, bar.top() - win_h - 10, win_w, win_h)
        elif position == "Top":
            win = QRectF(screen.center().x() - win_w / 2, bar.bottom() + 10, win_w, win_h)
        elif position == "Left":
            win = QRectF(bar.right() + 12, screen.center().y() - win_h / 2, win_w, win_h)
        else:
            win = QRectF(bar.left() - 12 - win_w, screen.center().y() - win_h / 2, win_w, win_h)
        window_color = QColor("#000000" if high_contrast else surface)
        alpha = 1.0 if high_contrast else float(self.desktop.get("transparency", 0.51))
        if theme in GLASS_THEMES:
            alpha = min(alpha, 0.72)
        window_color.setAlphaF(max(0.45, alpha) if theme != THEME_LOW else 1.0)
        if self.desktop.get("enable_shadows"):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 55))
            p.drawRoundedRect(win.translated(0, 5), 14, 14)
        p.setPen(QPen(QColor(255, 255, 255, 140 if theme in GLASS_THEMES else 60), 1.2))
        p.setBrush(window_color)
        radius = 4 if theme == THEME_LOW else 14
        p.drawRoundedRect(win, radius, radius)
        # Category column and application tiles.
        multi = theme == THEME_MULTI or (self.desktop.get("multicolor") and theme != THEME_LOW)
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(5):
            color = QColor(MULTI_COLORS[i] if multi else accent)
            if not multi:
                color.setAlpha(230 if i == 0 else 60)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(win.left() + 12, win.top() + 14 + i * 20, win.width() * 0.22, 13), 6, 6)
        grid = self.desktop.get("layout", "Grid") == "Grid"
        text_color = QColor("#ffffff" if (high_contrast or dark) else text)
        tile = 26 * self.desktop.get("tile_size", 132) / 132
        left = win.left() + win.width() * 0.3
        if grid:
            columns = max(2, int((win.right() - left - 8) // (tile + 10)))
            for i in range(columns * 2):
                x = left + (i % columns) * (tile + 10)
                y = win.top() + 16 + (i // columns) * (tile + 18)
                color = QColor(MULTI_COLORS[(i + 3) % len(MULTI_COLORS)] if multi else accent)
                color.setAlpha(210)
                p.setBrush(color)
                p.drawRoundedRect(QRectF(x, y, tile, tile), 7, 7)
                text_color.setAlpha(110)
                p.setBrush(text_color)
                p.drawRoundedRect(QRectF(x + 3, y + tile + 5, tile - 6, 3), 1.5, 1.5)
        else:
            for i in range(5):
                y = win.top() + 16 + i * 20
                color = QColor(accent)
                color.setAlpha(200)
                p.setBrush(color)
                p.drawRoundedRect(QRectF(left, y, 13, 13), 4, 4)
                text_color.setAlpha(110)
                p.setBrush(text_color)
                p.drawRoundedRect(QRectF(left + 20, y + 4, win.right() - left - 36, 4), 2, 2)
        # Eduka-Panel.
        bar_color = QColor("#000000" if high_contrast else panel_color)
        bar_alpha = 1.0 if high_contrast else float(self.panel.get("transparency", 0.54))
        if theme in GLASS_THEMES:
            bar_alpha = min(bar_alpha, 0.7)
        bar_color.setAlphaF(1.0 if theme == THEME_LOW else max(0.5, bar_alpha))
        p.setPen(QPen(QColor(255, 255, 255, 120 if theme in GLASS_THEMES else 40), 1))
        p.setBrush(bar_color)
        bar_radius = 0 if style == "full" else thickness / 2.6
        p.drawRoundedRect(bar, bar_radius, bar_radius)
        bar_text = QColor("#ffffff" if (high_contrast or dark or theme == THEME_LOW) else "#1f2d2a")
        font = QFont(self.font())
        font.setPixelSize(max(9, int(thickness * 0.38)))
        font.setBold(True)
        p.setFont(font)
        inner = bar.adjusted(6, 4, -6, -4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(accent)
        label = self.panel.get("menu_label", "Edukasaun") if self.panel.get("show_menu_text", True) else ""
        if vertical:
            p.drawRoundedRect(QRectF(inner.left(), inner.top(), inner.width(), inner.width()), 6, 6)
            for i in range(4):
                p.setBrush(QColor(bar_text.red(), bar_text.green(), bar_text.blue(), 90))
                p.drawRoundedRect(QRectF(inner.left() + 3, inner.top() + inner.width() + 8 + i * (inner.width() + 4),
                                         inner.width() - 6, inner.width() - 6), 4, 4)
        else:
            button_width = inner.height() + (p.fontMetrics().horizontalAdvance(label) + 12 if label else 0)
            p.drawRoundedRect(QRectF(inner.left(), inner.top(), button_width, inner.height()), 7, 7)
            p.setPen(QColor("#ffffff"))
            p.drawText(QRectF(inner.left() + inner.height() - 2, inner.top(), button_width, inner.height()),
                       Qt.AlignmentFlag.AlignVCenter, label)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 230))
            p.drawRoundedRect(QRectF(inner.left() + 4, inner.top() + 4, inner.height() - 8, inner.height() - 8),
                              3, 3)
            task_style = self.panel.get("taskbar_style", "Icon and Text")
            x = inner.left() + button_width + 10
            for i in range(3 if style != "dock" else 4):
                if x > inner.right() - 70:
                    break
                p.setBrush(QColor(bar_text.red(), bar_text.green(), bar_text.blue(), 70))
                width = inner.height() if (task_style == "Icon only" or style == "dock") else inner.height() * 3
                p.drawRoundedRect(QRectF(x, inner.top() + 2, width, inner.height() - 4), 5, 5)
                x += width + 6
            p.setPen(bar_text)
            if style != "dock":
                p.drawText(QRectF(inner.right() - 70, inner.top(), 66, inner.height()),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, self.clock)
