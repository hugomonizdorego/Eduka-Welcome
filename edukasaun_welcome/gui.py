"""Native seven-page Welcome Screen for Edukasaun OS; all system operations are asynchronous."""
import shlex
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from PyQt6.QtCore import (
    QDateTime, QPointF, QProcess, QRectF, QTemporaryDir, QThread, QTimer, Qt, QUrl, pyqtSignal,
)
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import (
    QAbstractButton, QApplication, QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDateTimeEdit,
    QDialog, QFileDialog, QFormLayout, QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSlider,
    QSpinBox, QStackedWidget, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)
from .catalog import load_project, recommendations, install_commands
from .desktop import open_tool
from .eduka_desktop import (
    ACCENT_CHOICES, CLOCK_STYLES, DEFAULT_DESKTOP, DEFAULT_PANEL, EFFECT_HOVER, EFFECT_LAUNCH, GLASS_THEMES,
    LAYOUTS, PANEL_POSITIONS, PANEL_STYLES, SECTIONS, START_ICON, TASKBAR_STYLES, THEME_DEFAULT,
    THEME_LIQUID, THEME_LOW, THEME_MULTI, THEMES, TILE_SIZES, WALLPAPER_MODES, background_images,
    effects_capability, finish_in_eduka, glass_capability, installed as eduka_installed, logo_path,
    normalize_theme, read_settings as read_eduka_settings, save_settings,
)
from .i18n import Translator
from .inventory import Inventory, apt_available, scan_inventory, write_inventory
from .preferences import config_home, load_preferences, save_preferences
from .session import start_desktop
from .timesettings import (
    DEFAULT_TIMEZONE, current_timezone, format_clock, time_commands, timezone_choices, utc_offset,
)
from .widgets import (
    AnalogClock, ChoiceCard, DesktopPreview, Swatch, edukasaun_mark, glyph, panel_style_preview,
    theme_preview,
)

PAGES = [("stepWelcome", "stepWelcomeHint"), ("stepTime", "stepTimeHint"), ("stepSuite", "stepSuiteHint"),
         ("stepDesktop", "stepDesktopHint"), ("stepApps", "stepAppsHint"), ("stepSponsors", "stepSponsorsHint"),
         ("stepFinish", "stepFinishHint")]
SPONSOR_DIRS = [Path(__file__).parent / "data/sponsors", Path("/usr/share/edukasaun-welcome/sponsors")]
QUICK_ZONES = ["Asia/Dili", "Asia/Jakarta", "Asia/Makassar", "Australia/Darwin", "Asia/Singapore",
               "Europe/Lisbon", "UTC"]
GREETINGS = [("Benvindu", "Tetun"), ("Bem-vindo", "Português"), ("Welcome", "English"),
             ("Selamat datang", "Bahasa Indonesia"), ("Maligayang pagdating", "Filipino"),
             ("Chào mừng", "Tiếng Việt"), ("Bienvenue", "Français"), ("Bienvenido", "Español"),
             ("Willkommen", "Deutsch")]
FONT_FAMILIES = ["Inter", "Noto Sans", "Cantarell", "Ubuntu", "DejaVu Sans"]

STYLE = """
QWidget { font-size: 14px; color: #173d37; }
QWidget#shell { background: #e9f2ee; }
QWidget#page, QWidget#tab { background: transparent; }
QWidget#content { background: #f8fbfa; border-radius: 22px; }
QFrame#rail { border-radius: 22px;
  background: qlineargradient(x1:0, y1:0, x2:0.4, y2:1, stop:0 #0a5c4e, stop:0.55 #0b4f45, stop:1 #08342e); }
QFrame#rail QLabel { color: #ffffff; background: transparent; }
QLabel#brand { font-size: 21px; font-weight: 800; }
QLabel#railNote { color: #a9dccb; font-size: 12px; }
QLabel#railFooter { color: #7fc2ad; font-size: 11px; font-weight: 800; letter-spacing: 1.5px; }
QProgressBar#railProgress { background: rgba(255,255,255,0.14); border: 0; border-radius: 3px; max-height: 6px; }
QProgressBar#railProgress::chunk { border-radius: 3px;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5ee0b3, stop:1 #f5d76e); }
QLabel#title { font-size: 30px; font-weight: 800; color: #0b4f45; }
QLabel#lead { color: #4d6963; font-size: 15px; }
QLabel#note { color: #64807a; font-size: 13px; }
QLabel#chip { color: #00785f; background: #dcf3e9; border-radius: 11px; padding: 4px 12px;
              font-weight: 800; font-size: 11px; letter-spacing: 1.2px; }
QLabel#section { color: #0b4f45; font-size: 13px; font-weight: 800; letter-spacing: 1px; }
QLabel#cardTitle { font-size: 16px; font-weight: 800; color: #12352f; }
QLabel#cardBody { color: #557069; font-size: 13.5px; }
QLabel#heroTitle { color: white; font-size: 33px; font-weight: 800; }
QLabel#heroGreeting { color: #f5d76e; font-size: 22px; font-weight: 800; }
QLabel#heroLanguage { color: #bfeadb; font-size: 12px; font-weight: 800; letter-spacing: 1.5px; }
QLabel#heroBody { color: #e3f6ef; font-size: 15px; }
QLabel#clock { font-size: 44px; font-weight: 800; color: #0b4f45; }
QLabel#clockDate { font-size: 15px; color: #4d6963; font-weight: 600; }
QLabel#statValue { font-size: 18px; font-weight: 800; color: #0b4f45; }
QFrame#hero { border-radius: 22px;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f8a70, stop:0.55 #0b5f52, stop:1 #13456a); }
QFrame#card { background: white; border: 1px solid #dcebe4; border-radius: 16px; }
QFrame#softCard { background: #eff8f4; border: 1px solid #dcebe4; border-radius: 16px; }
QFrame#logoCard { background: white; border: 1px solid #dcebe4; border-radius: 16px; }
QFrame#logoPlaceholder { background: #fbfdfc; border: 2px dashed #bcd6cb; border-radius: 16px; }
QLabel#placeholderText { color: #7b958e; font-size: 16px; font-weight: 800; }
QLabel#logoText { color: #0b6355; font-size: 20px; font-weight: 800; }
QPushButton { background: #ffffff; border: 1px solid #c4dbd1; border-radius: 10px; padding: 9px 16px;
              font-weight: 600; }
QPushButton:hover { background: #e9f6f0; border-color: #8cc5b0; }
QPushButton#primary { color: white; border: 0; font-weight: 800; padding: 11px 22px;
  background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00a07f, stop:1 #00856e); }
QPushButton#primary:hover { background: #006c59; }
QPushButton#primary:disabled { background: #b9d3ca; color: #f4f8f6; }
QPushButton#ghost { background: transparent; border: 1px solid transparent; color: #36524c; }
QPushButton#ghost:hover { background: #e3f1eb; }
QPushButton#chipButton { border-radius: 13px; padding: 5px 13px; font-size: 13px; min-height: 16px; }
QPushButton#chipButton:checked { background: #00856e; color: white; border-color: #00856e; }
QPushButton:disabled { color: #8fa29c; background: #edf2ef; border-color: #dfe9e4; }
QComboBox, QLineEdit, QDateTimeEdit, QSpinBox { border: 1px solid #c4dbd1; border-radius: 9px;
  background: white; padding: 7px 9px; min-height: 20px; }
QComboBox:focus, QLineEdit:focus, QDateTimeEdit:focus, QSpinBox:focus { border: 2px solid #00856e; }
QSlider::groove:horizontal { height: 6px; border-radius: 3px; background: #d5e8e0; }
QSlider::sub-page:horizontal { height: 6px; border-radius: 3px; background: #00a07f; }
QSlider::handle:horizontal { width: 16px; margin: -5px 0; border-radius: 8px; background: #00856e; }
QTabWidget::pane { border: 0; background: transparent; }
QTabBar::tab { padding: 8px 16px; margin-right: 6px; color: #4d6963; background: #e6f1ec; border-radius: 15px;
               font-weight: 700; }
QTabBar::tab:selected { color: white; background: #00856e; }
QTabBar::tab:hover:!selected { background: #d5eae1; }
QTableWidget { background: white; border: 1px solid #dcebe4; border-radius: 12px;
               selection-background-color: #e3f4ec; selection-color: #173d37; }
QTableWidget::item { padding: 6px; border-bottom: 1px solid #eef4f1; }
QHeaderView::section { background: #f0f8f4; border: 0; padding: 9px; font-weight: 800; color: #36524c; }
QTextEdit { background: #f8fbf9; border: 1px solid #dcebe4; border-radius: 10px; font-family: monospace; }
QCheckBox { spacing: 9px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { width: 10px; background: transparent; }
QScrollBar::handle:vertical { background: #c7ddd4; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class ScanWorker(QThread):
    completed = pyqtSignal(object, object, object)

    def run(self):
        inventory = scan_inventory()
        apps = recommendations(inventory)
        availability = {app["id"]: apt_available(app["sources"]["apt"])
                        for app in apps if "apt" in app["sources"]}
        self.completed.emit(inventory, apps, availability)


class DesktopWorker(QThread):
    """Save Eduka-Desktop settings, then let Eduka-Desktop apply them with its own code."""
    completed = pyqtSignal(str, str)

    def __init__(self, values, parent):
        super().__init__(parent)
        self.values = values

    def run(self):
        try:
            panel, desktop, menu = self.values["eduka"]
            save_settings(panel, desktop, menu)
            ok, notes = finish_in_eduka(self.values.get("theme"), self.values.get("orca"),
                                        self.values.get("wallpaper", False))
            if not ok and self.values.get("orca"):
                save_settings({}, {"orca_enabled": False}, {})
            self.completed.emit("" if ok else (notes or "Eduka-Desktop could not apply every setting."),
                                notes if ok else "")
        except Exception as error:
            self.completed.emit(str(error), "")


class StepButton(QAbstractButton):
    """A step in the left rail: number (or check mark), title and short hint."""

    def __init__(self, index, title, hint, parent=None):
        super().__init__(parent)
        self.index, self.title, self.hint = index, title, hint
        self.state = "todo"
        self.setText(title)
        self.setAccessibleName(f"{index + 1}. {title}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(56)

    def set_state(self, state):
        self.state = state
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0, 3, 0, -3)
        current = self.state == "current"
        if current or self.underMouse():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 40 if current else 16))
            p.drawRoundedRect(rect, 14, 14)
        center = QPointF(rect.left() + 24, rect.center().y())
        if self.state == "done":
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#5ee0b3"))
            p.drawEllipse(center, 13, 13)
            p.setPen(QPen(QColor("#08342e"), 2.4, cap=Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(center.x() - 5, center.y()), QPointF(center.x() - 1.5, center.y() + 4))
            p.drawLine(QPointF(center.x() - 1.5, center.y() + 4), QPointF(center.x() + 5.5, center.y() - 4))
        else:
            p.setPen(QPen(QColor("#ffffff" if current else "#7fc2ad"), 1.6))
            p.setBrush(QColor("#ffffff") if current else Qt.BrushStyle.NoBrush)
            p.drawEllipse(center, 13, 13)
            p.setPen(QColor("#0b4f45" if current else "#bfe6d8"))
            font = QFont(self.font())
            font.setBold(True)
            font.setPixelSize(12)
            p.setFont(font)
            p.drawText(QRectF(center.x() - 13, center.y() - 13, 26, 26), Qt.AlignmentFlag.AlignCenter,
                       str(self.index + 1))
        font = QFont(self.font())
        font.setBold(True)
        font.setPixelSize(14)
        p.setFont(font)
        p.setPen(QColor("#ffffff" if current or self.state == "done" else "#cfeee3"))
        p.drawText(QRectF(rect.left() + 48, rect.top() + 7, rect.width() - 52, 22),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)
        font.setBold(False)
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QColor("#9fd6c4"))
        p.drawText(QRectF(rect.left() + 48, rect.top() + 27, rect.width() - 52, 18),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.hint)


def label(text, name="", wrap=True):
    widget = QLabel(text)
    widget.setWordWrap(wrap)
    if name:
        widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text, callback, primary=False, name=""):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary or name:
        widget.setObjectName("primary" if primary else name)
    return widget


def shadow(widget, blur=28, alpha=26, offset=6):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, offset)
    effect.setColor(QColor(11, 79, 69, alpha))
    widget.setGraphicsEffect(effect)
    return widget


def script_greeting(script, romanized, writing_system):
    """Keep greetings readable when an optional script font is absent."""
    return script if writing_system in QFontDatabase.writingSystems() else romanized


def os_release(path="/etc/os-release"):
    try:
        text = Path(path).read_text()
    except OSError:
        return ""
    fields = dict(line.split("=", 1) for line in text.splitlines()
                  if "=" in line and not line.startswith("#"))
    return fields.get("PRETTY_NAME", "").strip('"')


def sponsor_entry(item, folders=None):
    """Accept a plain name or {"name", "logo", "url"}; logos resolve inside sponsor folders."""
    if isinstance(item, str):
        item = {"name": item}
    if not isinstance(item, dict) or not str(item.get("name", "")).strip():
        return None
    logo = None
    name = str(item.get("logo", "")).strip()
    if name and Path(name).suffix.lower() in (".png", ".svg", ".jpg", ".jpeg", ".webp"):
        for folder in folders or [config_home() / "edukasaun-welcome/sponsors", *SPONSOR_DIRS]:
            candidate = folder / Path(name).name
            if candidate.is_file():
                logo = candidate
                break
    url = str(item.get("url", ""))
    parsed = urlparse(url)
    return {"name": str(item["name"]).strip(), "logo": logo,
            "url": url if parsed.scheme == "https" and parsed.netloc else ""}


def theme_key(theme):
    return theme.replace("-", "").replace(" ", "")


class WelcomeWindow(QWidget):
    def __init__(self, language="en", preferences=None, auto_scan=True, session=False):
        super().__init__()
        self.preferences = preferences if preferences is not None else load_preferences()
        self.t = Translator(language)
        self.session = session
        # Before the LXQt session starts, startlxqt (not this window) starts Eduka-Desktop.
        self.start_desktop_on_close = session
        self.project = load_project()
        self.inventory = Inventory()
        self.apps = []
        self.availability = {}
        self.scanned = False
        self.worker = None
        self.desktop_worker = None
        self.process = None
        self.commands = []
        self.commands_done = None
        self.command_log = None
        self.pending = None
        self.install_consent = False
        self.installing = 0
        self.installed_count = 0
        self.visited = {0}
        self.greeting_index = 0
        self.setObjectName("shell")
        self.setWindowTitle(self.t("nativeTitle"))
        self.resize(1180, 800)
        self.setMinimumSize(980, 680)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "data/icon.svg")))
        families = set(QFontDatabase.families())
        family = next((name for name in FONT_FAMILIES if name in families), None)
        if family:
            self.setFont(QFont(family, 10))
        self.setStyleSheet(STYLE + self.arrow_style())
        self.build()
        for combo in self.findChildren(QComboBox):
            # Long time zone names must not widen the page beyond the window.
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(10)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        self.greeting_timer = QTimer(self)
        self.greeting_timer.timeout.connect(self.next_greeting)
        self.greeting_timer.start(2600)
        if auto_scan:
            QTimer.singleShot(100, self.start_scan)

    def arrow_style(self):
        """Style sheets hide the native arrows; draw small ones that match the design."""
        self.arrow_dir = QTemporaryDir()
        paths = {}
        for name, points in (("down", ((3, 5), (8, 10), (13, 5))), ("up", ((3, 10), (8, 5), (13, 10)))):
            pixmap = QPixmap(32, 32)
            pixmap.setDevicePixelRatio(2)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#00856e"), 2, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin))
            painter.drawPolyline([QPointF(x, y) for x, y in points])
            painter.end()
            paths[name] = self.arrow_dir.filePath(name + ".png")
            pixmap.save(paths[name])
        return f"""
QComboBox::drop-down, QDateTimeEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
  width: 28px; border: 0; }}
QComboBox::down-arrow, QDateTimeEdit::down-arrow {{ image: url({paths['down']}); width: 16px; height: 16px; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 24px; border: 0; background: transparent; }}
QSpinBox::up-arrow {{ image: url({paths['up']}); width: 14px; height: 14px; }}
QSpinBox::down-arrow {{ image: url({paths['down']}); width: 14px; height: 14px; }}
QComboBox QAbstractItemView {{ border: 1px solid #c4dbd1; border-radius: 8px; background: white;
  selection-background-color: #dcf3e9; selection-color: #0b4f45; padding: 4px; }}
"""

    # Layout -----------------------------------------------------------------

    def build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(16)
        outer.addWidget(self.build_rail())
        content = QWidget()
        content.setObjectName("content")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 18, 24, 18)
        self.stack = QStackedWidget()
        for make_page in [self.welcome_page, self.time_page, self.suite_page, self.desktop_page,
                          self.apps_page, self.sponsors_page, self.finish_page]:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            scroll.setWidget(make_page())
            scroll.viewport().setAutoFillBackground(False)
            self.stack.addWidget(scroll)
        content_layout.addWidget(self.stack, 1)
        self.message = label("", "note")
        content_layout.addWidget(self.message)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #e0ece6;")
        content_layout.addWidget(divider)
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 8, 0, 0)
        self.back_button = button("‹  " + self.t("back"), lambda: self.navigate(self.stack.currentIndex() - 1),
                                  name="ghost")
        footer.addWidget(self.back_button)
        self.counter = label("", "note")
        footer.addWidget(self.counter, 1, Qt.AlignmentFlag.AlignCenter)
        # Shown on the last page only, where it stays visible without scrolling.
        self.always = QCheckBox(self.t("alwaysShow"))
        self.always.setChecked(self.preferences.get("always_show", True))
        self.always.setToolTip(self.t("alwaysShowNote"))
        self.always.toggled.connect(self.update_always)
        footer.addWidget(self.always, 1, Qt.AlignmentFlag.AlignRight)
        self.next_button = button(self.t("next"), self.next_page, True)
        self.next_button.setMinimumWidth(150)
        footer.addWidget(self.next_button)
        content_layout.addLayout(footer)
        outer.addWidget(shadow(content, 40, 22, 8), 1)
        self.navigate(0)
        self.populate_apps()

    def build_rail(self):
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(272)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(2)
        brand = QHBoxLayout()
        brand.setSpacing(12)
        brand.addWidget(self.logo_label(46))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(label("Edukasaun OS", "brand", wrap=False))
        names.addWidget(label(self.t("railSubtitle"), "railNote", wrap=False))
        brand.addLayout(names, 1)
        layout.addLayout(brand)
        layout.addSpacing(24)
        self.step_buttons = []
        for index, (title, hint) in enumerate(PAGES):
            step = StepButton(index, self.t(title), self.t(hint))
            step.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            self.step_buttons.append(step)
            layout.addWidget(step)
        layout.addStretch()
        self.rail_progress = QProgressBar()
        self.rail_progress.setObjectName("railProgress")
        self.rail_progress.setRange(0, len(PAGES))
        self.rail_progress.setTextVisible(False)
        layout.addWidget(self.rail_progress)
        layout.addSpacing(10)
        layout.addWidget(label(self.t("educationFirst"), "railFooter"))
        layout.addWidget(label(self.t("madeInTimor"), "railNote"))
        return rail

    def logo_label(self, size):
        mark = QLabel()
        logo = logo_path()
        pixmap = QPixmap(str(logo)) if logo else QPixmap()
        mark.setPixmap(pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation) if not pixmap.isNull()
                       else edukasaun_mark(size))
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return mark

    def page(self, eyebrow, title, lead):
        widget = QWidget()
        widget.setObjectName("page")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 10, 12, 10)
        layout.setSpacing(16)
        row = QHBoxLayout()
        row.addWidget(label(self.t(eyebrow), "chip", wrap=False))
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(label(self.t(title), "title"))
        layout.addWidget(label(self.t(lead), "lead"))
        return widget, layout

    def icon_tile(self, kind, size=24, color="#00856e", background="#e2f5ec"):
        tile = QLabel()
        tile.setPixmap(glyph(kind, color, size))
        tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile.setFixedSize(size + 22, size + 22)
        tile.setStyleSheet(f"background: {background}; border-radius: 13px;")
        return tile

    def card(self, title, body, action=None, icon=None, name="card"):
        frame = QFrame()
        frame.setObjectName(name)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)
        if icon:
            layout.addWidget(self.icon_tile(icon))
            layout.addSpacing(4)
        layout.addWidget(label(title, "cardTitle"))
        layout.addWidget(label(body, "cardBody"))
        layout.addStretch()
        if action is not None:
            row = QHBoxLayout()
            row.addWidget(action)
            row.addStretch()
            layout.addLayout(row)
        return frame

    def grid(self, cards, columns=2):
        grid = QGridLayout()
        grid.setSpacing(14)
        for index, widget in enumerate(cards):
            grid.addWidget(widget, index // columns, index % columns)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        return grid

    def heading(self, key):
        return label(self.t(key), "section")

    # Page 1: Welcome --------------------------------------------------------

    def welcome_page(self):
        widget = QWidget()
        widget.setObjectName("page")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 10, 12, 10)
        layout.setSpacing(18)
        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(36, 32, 36, 32)
        hero_layout.setSpacing(28)
        text = QVBoxLayout()
        text.setSpacing(8)
        self.hero_language = label(GREETINGS[0][1].upper(), "heroLanguage", wrap=False)
        self.hero_greeting = label(GREETINGS[0][0] + "!", "heroGreeting", wrap=False)
        text.addWidget(self.hero_language)
        text.addWidget(self.hero_greeting)
        text.addWidget(label(self.t("welcomeTitle"), "heroTitle"))
        text.addWidget(label(self.t("welcomeLead"), "heroBody"))
        text.addStretch()
        hero_layout.addLayout(text, 1)
        hero_layout.addWidget(self.logo_label(150))
        layout.addWidget(shadow(hero, 36, 60, 10))
        layout.addLayout(self.grid([
            self.card(self.t("highlightTimor"), self.t("highlightTimorBody"), icon="leaf"),
            self.card(self.t("highlightFree"), self.t("highlightFreeBody"), icon="heart"),
            self.card(self.t("highlightLearning"), self.t("highlightLearningBody"), icon="book"),
        ], 3))
        systems = QFontDatabase.WritingSystem
        asean = ["Selamat datang", "Maligayang pagdating",
                 script_greeting("ยินดีต้อนรับ", "Yindi tonrap", systems.Thai), "Chào mừng",
                 script_greeting("សូមស្វាគមន៍", "Soum sva kum", systems.Khmer),
                 script_greeting("ຍິນດີຕ້ອນຮັບ", "Nyin di ton hap", systems.Lao),
                 script_greeting("ကြိုဆိုပါတယ်", "Kyo so par", systems.Myanmar)]
        international = ["Welcome", "Bienvenue", "Bienvenido", "Willkommen", "Добро пожаловать",
                         script_greeting("مرحبًا", "Marhaban", systems.Arabic),
                         script_greeting("欢迎", "Huanying", systems.SimplifiedChinese),
                         script_greeting("स्वागत है", "Swagat hai", systems.Devanagari)]
        layout.addLayout(self.grid([
            self.card(self.t("cplp"), "Benvindu · Bem-vindo · Bem-vinda", name="softCard"),
            self.card(self.t("asean"), " · ".join(asean), name="softCard"),
            self.card(self.t("international"), " · ".join(international), name="softCard"),
        ], 3))
        release = os_release()
        if release:
            layout.addWidget(label(self.t("installedSystem", name=release), "note"))
        layout.addStretch()
        return widget

    def next_greeting(self):
        self.greeting_index = (self.greeting_index + 1) % len(GREETINGS)
        word, language = GREETINGS[self.greeting_index]
        self.hero_greeting.setText(word + "!")
        self.hero_language.setText(language.upper())

    # Page 2: Date & time ----------------------------------------------------

    def time_page(self):
        widget, layout = self.page("timeEyebrow", "timeTitle", "timeLead")
        self.system_zone = current_timezone()
        eduka_panel = read_eduka_settings()["panel"]
        clock_card = QFrame()
        clock_card.setObjectName("card")
        clock_layout = QHBoxLayout(clock_card)
        clock_layout.setContentsMargins(24, 20, 24, 20)
        clock_layout.setSpacing(28)
        self.analog_clock = AnalogClock()
        clock_layout.addWidget(self.analog_clock)
        digital = QVBoxLayout()
        digital.setSpacing(4)
        self.zone_title = label("", "chip", wrap=False)
        chip_row = QHBoxLayout()
        chip_row.addWidget(self.zone_title)
        chip_row.addStretch()
        digital.addStretch()
        digital.addLayout(chip_row)
        self.clock_label = label("", "clock", wrap=False)
        self.date_label = label("", "clockDate")
        digital.addWidget(self.clock_label)
        digital.addWidget(self.date_label)
        digital.addSpacing(10)
        digital.addWidget(label(self.t("quickZones"), "note"))
        quick = QGridLayout()
        quick.setSpacing(6)
        self.quick_group = QButtonGroup(self)
        self.quick_group.setExclusive(True)
        for index, zone in enumerate(QUICK_ZONES):
            chip = QPushButton(zone.split("/")[-1].replace("_", " "))
            chip.setObjectName("chipButton")
            chip.setCheckable(True)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip(zone)
            chip.clicked.connect(lambda checked=False, z=zone: self.choose_zone(z))
            self.quick_group.addButton(chip)
            quick.addWidget(chip, index // 4, index % 4)
        digital.addLayout(quick)
        digital.addStretch()
        clock_layout.addLayout(digital, 1)
        layout.addWidget(shadow(clock_card, 30, 18, 6))

        self.zone_search = QLineEdit()
        self.zone_search.setPlaceholderText(self.t("searchTimezone"))
        self.zone_search.setAccessibleName(self.t("searchTimezone"))
        self.zone_search.setClearButtonEnabled(True)
        self.zone_search.textChanged.connect(self.filter_timezones)
        self.zone_combo = QComboBox()
        self.zone_combo.setAccessibleName(self.t("timezone"))
        self.zone_combo.setMaxVisibleItems(16)
        self.zone_combo.currentIndexChanged.connect(self.zone_changed)
        self.clock_format = QComboBox()
        self.clock_format.addItem(self.t("clock24"), True)
        self.clock_format.addItem(self.t("clock12"), False)
        twelve = eduka_panel.get("clock_format") == "12h" or not self.preferences.get("clock_24h", True)
        self.clock_format.setCurrentIndex(1 if twelve else 0)
        self.clock_format.setAccessibleName(self.t("clockFormat"))
        self.clock_format.currentIndexChanged.connect(self.update_clock_format)
        self.panel_clock_style = QComboBox()
        for style in CLOCK_STYLES:
            self.panel_clock_style.addItem(self.t("clockStyle_" + style), style)
        self.panel_clock_style.setCurrentIndex(max(0, self.panel_clock_style.findData(
            eduka_panel.get("clock_style", "digital"))))
        self.panel_clock_style.setAccessibleName(self.t("panelClockStyle"))
        self.panel_seconds = QCheckBox(self.t("panelSeconds"))
        self.panel_seconds.setChecked(bool(eduka_panel.get("panel_clock_seconds", False)))
        self.automatic_time = QCheckBox(self.t("automaticTime"))
        self.automatic_time.setChecked(True)
        self.manual_time = QDateTimeEdit()
        self.manual_time.setDisplayFormat("yyyy-MM-dd  HH:mm")
        self.manual_time.setCalendarPopup(True)
        self.manual_time.setAccessibleName(self.t("manualTime"))
        self.manual_time.setEnabled(False)
        self.automatic_time.toggled.connect(self.toggle_automatic_time)
        self.filter_timezones("")

        cards = QHBoxLayout()
        cards.setSpacing(14)
        zone_card = QFrame()
        zone_card.setObjectName("card")
        zone_form = QFormLayout(zone_card)
        zone_form.setContentsMargins(20, 16, 20, 16)
        zone_form.setVerticalSpacing(12)
        zone_form.addRow(self.heading("zoneSection"))
        zone_form.addRow(self.t("searchTimezone"), self.zone_search)
        zone_form.addRow(self.t("timezone"), self.zone_combo)
        zone_form.addRow("", self.automatic_time)
        zone_form.addRow(self.t("manualTime"), self.manual_time)
        clock_form_card = QFrame()
        clock_form_card.setObjectName("card")
        clock_form = QFormLayout(clock_form_card)
        clock_form.setContentsMargins(20, 16, 20, 16)
        clock_form.setVerticalSpacing(12)
        clock_form.addRow(self.heading("panelClockSection"))
        clock_form.addRow(self.t("clockFormat"), self.clock_format)
        clock_form.addRow(self.t("panelClockStyle"), self.panel_clock_style)
        clock_form.addRow("", self.panel_seconds)
        cards.addWidget(zone_card, 3)
        cards.addWidget(clock_form_card, 2)
        layout.addLayout(cards)
        row = QHBoxLayout()
        self.time_button = button(self.t("applyTime"), self.apply_time, True)
        row.addWidget(self.time_button)
        self.time_status = label(self.t("currentTimezone", zone=self.system_zone or self.t("unknown")), "note")
        row.addWidget(self.time_status, 1)
        layout.addLayout(row)
        layout.addWidget(label(self.t("timeNote"), "note"))
        layout.addStretch()
        self.reset_manual_time()
        self.update_clock()
        return widget

    def filter_timezones(self, text):
        selected = self.zone_combo.currentData() or DEFAULT_TIMEZONE
        query = text.strip().casefold().replace(" ", "_")
        self.zone_combo.blockSignals(True)
        self.zone_combo.clear()
        for zone in timezone_choices():
            if query and query not in zone.casefold():
                continue
            name = zone.replace("_", " ")
            if zone == DEFAULT_TIMEZONE:
                name += " — Timor-Leste"
            self.zone_combo.addItem(f"{name}   ({utc_offset(zone)})", zone)
        self.zone_combo.setCurrentIndex(max(0, self.zone_combo.findData(selected)))
        self.zone_combo.blockSignals(False)
        self.zone_changed()

    def choose_zone(self, zone):
        self.zone_search.blockSignals(True)
        self.zone_search.clear()
        self.zone_search.blockSignals(False)
        self.filter_timezones("")
        self.zone_combo.setCurrentIndex(max(0, self.zone_combo.findData(zone)))

    def zone_changed(self):
        self.reset_manual_time()
        zone = self.selected_timezone()
        if hasattr(self, "quick_group"):
            for chip in self.quick_group.buttons():
                chip.setChecked(chip.toolTip() == zone)
        self.update_clock()

    def toggle_automatic_time(self, automatic):
        self.manual_time.setEnabled(not automatic)
        self.reset_manual_time()

    def reset_manual_time(self):
        """Manual time is entered in the selected zone, which is applied before set-time."""
        zone = self.selected_timezone()
        if zone and hasattr(self, "manual_time"):
            local = datetime.now(ZoneInfo(zone)).replace(tzinfo=None, microsecond=0)
            self.manual_time.setDateTime(QDateTime(local))

    def selected_timezone(self):
        return self.zone_combo.currentData() if hasattr(self, "zone_combo") else None

    def short_clock(self):
        zone = self.selected_timezone() or DEFAULT_TIMEZONE
        clock = format_clock(zone, self.clock_format.currentData() is not False).rpartition(" · ")[2]
        return clock[:5] + clock[8:]  # Drop the seconds.

    def update_clock(self):
        if not hasattr(self, "clock_label"):
            return
        zone = self.selected_timezone()
        if not zone:
            self.zone_title.setText(self.t("noTimezoneMatch"))
            self.clock_label.setText("--:--")
            self.date_label.setText("")
            return
        date, _, clock = format_clock(zone, self.clock_format.currentData() is not False).rpartition(" · ")
        self.zone_title.setText(zone.replace("_", " ").upper() + "  ·  " + utc_offset(zone))
        self.clock_label.setText(clock)
        self.date_label.setText(date)
        self.analog_clock.set_zone(zone)
        if hasattr(self, "preview"):
            self.update_preview()

    def update_clock_format(self):
        self.preferences["clock_24h"] = bool(self.clock_format.currentData())
        self.persist()
        self.update_clock()

    def apply_time(self):
        if self.busy():
            self.message.setText(self.t("closeBusy"))
            return
        try:
            manual = None if self.automatic_time.isChecked() else \
                self.manual_time.dateTime().toPyDateTime()
            commands = time_commands(self.selected_timezone() or "", self.automatic_time.isChecked(), manual)
            # The panel clock is a per-user Eduka-Panel setting: no administrator needed.
            save_settings({"clock_format": "24h" if self.clock_format.currentData() else "12h",
                           "clock_style": self.panel_clock_style.currentData(),
                           "panel_clock_seconds": self.panel_seconds.isChecked()}, {}, {})
            if not shutil.which("timedatectl"):
                raise RuntimeError(self.t("timedatectlMissing"))
        except (OSError, ValueError, RuntimeError) as error:
            self.error(error)
            return
        self.time_button.setEnabled(False)
        self.time_status.setText(self.t("timeApplying"))
        self.run_commands(commands, None, self.time_finished)

    def time_finished(self, success):
        self.time_button.setEnabled(True)
        if success:
            self.system_zone = self.selected_timezone()
            self.preferences["timezone"] = self.system_zone
            self.persist()
            self.time_status.setText(self.t("timeApplied", zone=self.system_zone))
        else:
            self.time_status.setText(self.t("timeFailed"))

    # Page 3: Eduka-Desktop Suite --------------------------------------------

    def suite_page(self):
        widget, layout = self.page("suiteEyebrow", "suiteTitle", "suiteLead")
        open_menu = button(self.t("openEdukaDesktop"), lambda: self.run_tool("menu"))
        open_settings = button(self.t("openMenuSettings"), lambda: self.run_tool("suite"), True)
        layout.addLayout(self.grid([
            self.card("Eduka-Desktop", self.t("suiteDesktop"), open_menu, "menu"),
            self.card("Eduka-Panel", self.t("suitePanel"), icon="panel"),
            self.card(self.t("actionCenter"), self.t("suiteActionCenter"), icon="clock"),
            self.card("Eduka-Settings", self.t("suiteSettings"), open_settings, "settings"),
        ], 2))
        if not eduka_installed():
            layout.addWidget(label(self.t("edukaMissingShort"), "note"))
        layout.addWidget(self.heading("suiteHighlights"))
        layout.addLayout(self.grid([
            self.card(self.t("featureThemes"), self.t("featureThemesBody"), icon="palette", name="softCard"),
            self.card(self.t("featureParental"), self.t("featureParentalBody"), icon="shield", name="softCard"),
            self.card(self.t("featureLogin"), self.t("featureLoginBody"), icon="people", name="softCard"),
            self.card(self.t("featureAccess"), self.t("featureAccessBody"), icon="accessibility",
                      name="softCard"),
            self.card(self.t("featureLanguages"), self.t("featureLanguagesBody"), icon="globe", name="softCard"),
            self.card(self.t("featureLight"), self.t("featureLightBody"), icon="leaf", name="softCard"),
        ], 3))
        layout.addWidget(self.heading("projectTools"))
        layout.addLayout(self.grid([
            self.card("EUS", self.t("toolEus"), icon="update"),
            self.card("Eduka-Konekta", self.t("toolKonekta"), icon="chat"),
            self.card("Eduka-Block", self.t("toolBlock"), icon="shield"),
        ], 3))
        about = QHBoxLayout()
        about.addWidget(button(self.t("about"), self.show_about, name="ghost"))
        about.addStretch()
        layout.addLayout(about)
        layout.addStretch()
        return widget

    # Page 4: Your desktop (Eduka-Desktop Suite settings) --------------------

    def desktop_page(self):
        widget, layout = self.page("makeItYours", "desktopTitle", "desktopLead")
        self.eduka = read_eduka_settings()
        panel, desktop, menu = self.eduka["panel"], self.eduka["desktop"], self.eduka["menu"]
        self.initial_orca = bool(desktop.get("orca_enabled"))
        self.initial_theme = normalize_theme(desktop.get("theme_style"))
        self.glass_confirmed = self.initial_theme in GLASS_THEMES
        self.effects_confirmed = bool(desktop.get("effects_enabled"))
        self.accent = str(desktop.get("accent_color", "") or "")
        images = desktop.get("wallpaper", {}).get("images") or []
        self.wallpaper = images[0] if images and Path(images[0]).is_file() else ""
        self.wallpaper_changed = False
        if not eduka_installed():
            layout.addWidget(label(self.t("edukaMissing"), "note"))
        self.preview = DesktopPreview()
        self.preview.setMinimumHeight(260)
        layout.addWidget(shadow(self.preview, 30, 40, 8))

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self.theme_tab(desktop), self.tab_title("tabTheme"))
        tabs.addTab(self.panel_tab(panel), "Eduka-Panel")
        tabs.addTab(self.menu_tab(desktop, menu), "Eduka-Desktop")
        tabs.addTab(self.wallpaper_tab(desktop), self.tab_title("wallpaper"))
        tabs.addTab(self.form_tab([
            (self.t("vision"), self.check("vision", "visionAccess", desktop.get("visual_accessibility"))),
            (self.t("hearing"), self.check("hearing", "hearingAccess", desktop.get("hearing_accessibility"))),
            (self.t("screenReader"), self.check("orca", "orcaAccess", desktop.get("orca_enabled"))),
        ], "accessNote"), self.t("accessibility"))
        layout.addWidget(tabs)

        actions = QHBoxLayout()
        self.apply_button = button(self.t("apply"), self.apply_settings, True)
        actions.addWidget(self.apply_button)
        actions.addWidget(button(self.t("restoreDefaults"), self.restore_eduka_defaults))
        actions.addWidget(button(self.t("openMenuSettings"), lambda: self.run_tool("suite"), name="ghost"))
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(label(self.t("desktopWarning"), "note"))
        self.update_preview()
        return widget

    def tab_title(self, key):
        return self.t(key).replace("&", "&&")  # A single & would become a keyboard mnemonic.

    def tab_page(self):
        tab = QWidget()
        tab.setObjectName("tab")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(4, 16, 4, 6)
        layout.setSpacing(12)
        return tab, layout

    def form(self):
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        return form

    def theme_tab(self, desktop):
        tab, layout = self.tab_page()
        layout.addWidget(self.heading("visualTheme"))
        self.theme_group = QButtonGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_cards = {}
        grid = QGridLayout()
        grid.setSpacing(10)
        for index, theme in enumerate(THEMES):
            card = ChoiceCard(theme_preview(theme, 140, 82), self.t("theme_" + theme_key(theme)), theme)
            card.setToolTip(self.t("themeHint_" + theme_key(theme)))
            self.theme_cards[theme] = card
            self.theme_group.addButton(card)
            grid.addWidget(card, index // 3, index % 3)
        grid.setColumnStretch(3, 1)
        layout.addLayout(grid)
        self.theme_cards[normalize_theme(desktop.get("theme_style"))].setChecked(True)
        self.theme_group.buttonToggled.connect(self.theme_card_toggled)
        self.theme_note = label("", "note")
        layout.addWidget(self.theme_note)
        layout.addWidget(self.heading("accentColor"))
        swatches = QHBoxLayout()
        swatches.setSpacing(2)
        self.accent_group = QButtonGroup(self)
        self.accent_group.setExclusive(True)
        for color, name in ACCENT_CHOICES:
            swatch = Swatch(color, self.t("accentTheme") if not color else name)
            swatch.setChecked(color.casefold() == self.accent.casefold())
            swatch.clicked.connect(lambda checked=False, c=color: self.set_accent(c))
            self.accent_group.addButton(swatch)
            swatches.addWidget(swatch)
        swatches.addSpacing(8)
        swatches.addWidget(button(self.t("customColor"), self.choose_color, name="chipButton"))
        swatches.addStretch()
        layout.addLayout(swatches)
        form = self.form()
        form.addRow(self.t("panelTransparency"), self.slider("panel_transparency", 50,
                                                              self.eduka["panel"]["transparency"]))
        form.addRow(self.t("desktopTransparency"), self.slider("desktop_transparency", 45,
                                                                desktop["transparency"]))
        form.addRow("", self.check("multicolor", "multicolorOption", desktop.get("multicolor")))
        form.addRow("", self.check("glass_blur", "glassBlur", desktop.get("glass_blur")))
        form.addRow("", self.check("shadows", "enableShadows", desktop.get("enable_shadows")))
        form.addRow("", self.check("low_resource", "lowResource", desktop.get("low_resource_mode")))
        layout.addLayout(form)
        return tab

    def panel_tab(self, panel):
        tab, layout = self.tab_page()
        layout.addWidget(self.heading("panelStyle"))
        self.panel_style_group = QButtonGroup(self)
        self.panel_style_group.setExclusive(True)
        self.panel_style_cards = {}
        row = QHBoxLayout()
        row.setSpacing(10)
        for style, _name in PANEL_STYLES:
            card = ChoiceCard(panel_style_preview(style, 120, 72), self.t("panelStyle_" + style), style)
            self.panel_style_cards[style] = card
            self.panel_style_group.addButton(card)
            row.addWidget(card)
        row.addStretch()
        layout.addLayout(row)
        self.panel_style_cards.get(panel.get("panel_style", "floating"), self.panel_style_cards["floating"]) \
            .setChecked(True)
        self.panel_style_group.buttonToggled.connect(self.update_preview)
        position = QHBoxLayout()
        position.setSpacing(6)
        self.position_group = QButtonGroup(self)
        self.position_group.setExclusive(True)
        for name in PANEL_POSITIONS:
            chip = QPushButton(self.t("position_" + name))
            chip.setObjectName("chipButton")
            chip.setCheckable(True)
            chip.setProperty("value", name)
            chip.setChecked(panel.get("position", "Bottom") == name)
            chip.clicked.connect(self.update_preview)
            self.position_group.addButton(chip)
            position.addWidget(chip)
        position.addStretch()
        menu_icon = QHBoxLayout()
        self.menu_icon = QLineEdit(panel["menu_icon"])
        self.menu_icon.setAccessibleName(self.t("menuIcon"))
        self.menu_icon.textChanged.connect(self.update_preview)
        menu_icon.addWidget(self.menu_icon, 1)
        menu_icon.addWidget(button(self.t("browse"), self.choose_menu_icon))
        self.menu_label = QLineEdit(panel["menu_label"])
        self.menu_label.setMaxLength(40)
        self.menu_label.setAccessibleName(self.t("menuLabel"))
        self.menu_label.textChanged.connect(self.update_preview)
        form = self.form()
        form.addRow(self.t("panelPosition"), position)
        form.addRow(self.t("panelHeight"), self.spin("panel_height", 34, 58, panel["height"], " px"))
        form.addRow(self.t("panelWidth"), self.spin("panel_width", 70, 100, panel["width_percent"], " %"))
        form.addRow(self.t("taskbarStyle"), self.combo("taskbar_style", [
            (style, self.t("taskbar_" + style.replace(" ", ""))) for style in TASKBAR_STYLES],
            panel["taskbar_style"]))
        form.addRow(self.t("menuLabel"), self.menu_label)
        form.addRow(self.t("menuIcon"), menu_icon)
        form.addRow(self.t("menuIconSize"), self.spin("menu_icon_size", 16, 64, panel["menu_icon_size"], " px"))
        form.addRow("", self.check("show_text", "showMenuText", panel["show_menu_text"]))
        layout.addLayout(form)
        return tab

    def menu_tab(self, desktop, menu):
        tab, layout = self.tab_page()
        form = self.form()
        form.addRow(self.t("defaultLayout"), self.combo("desktop_layout", [
            (value, self.t("layout_" + value)) for value in LAYOUTS], desktop["layout"]))
        form.addRow(self.t("defaultSection"), self.combo("default_section", [
            (value, value) for value in SECTIONS[1:]], desktop["last_category"]))
        form.addRow(self.t("tileSize"), self.combo("tile_size", [
            (value, self.t(f"tile{value}")) for value in TILE_SIZES], int(desktop.get("tile_size", 132))))
        form.addRow(self.t("desktopWidth"), self.spin("desktop_width", 94, 99, desktop["width_percent"], " %"))
        form.addRow(self.t("desktopHeight"), self.spin("desktop_height", 78, 95, desktop["height_percent"], " %"))
        form.addRow(self.t("menuLanguage"), self.combo("menu_language", [
            ("system", self.t("languageSystem")), ("tet", "Tetun")], menu.get("language", "system")))
        layout.addLayout(form)
        layout.addWidget(self.heading("effectsTitle"))
        effects = self.form()
        effects.addRow("", self.check("effects", "effectsOption", desktop.get("effects_enabled")))
        effects.addRow(self.t("effectHover"), self.combo("effect_hover", [
            (value, self.t("hover_" + value.replace("-", ""))) for value in EFFECT_HOVER],
            desktop.get("effect_hover", "wave")))
        effects.addRow(self.t("effectLaunch"), self.combo("effect_launch", [
            (value, self.t("launch_" + value.replace("-", ""))) for value in EFFECT_LAUNCH],
            desktop.get("effect_launch", "bubble")))
        layout.addLayout(effects)
        self.effects.toggled.connect(self.effects_toggled)
        layout.addWidget(label(self.t("effectsNote"), "note"))
        return tab

    def wallpaper_tab(self, desktop):
        tab, layout = self.tab_page()
        self.wallpaper_group = QButtonGroup(self)
        self.wallpaper_group.setExclusive(True)
        images = background_images()
        if images:
            row = QGridLayout()
            row.setSpacing(10)
            for index, path in enumerate(images[:8]):
                thumb = QPixmap(str(path)).scaled(132, 74, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                                  Qt.TransformationMode.SmoothTransformation).copy(0, 0, 132, 74)
                card = ChoiceCard(thumb, path.stem.replace("_", " ")[:18], str(path))
                card.setChecked(str(path) == self.wallpaper)
                card.clicked.connect(lambda checked=False, p=str(path): self.set_wallpaper(p))
                self.wallpaper_group.addButton(card)
                row.addWidget(card, index // 4, index % 4)
            row.setColumnStretch(4, 1)
            layout.addLayout(row)
        else:
            layout.addWidget(label(self.t("noBackgrounds"), "note"))
        file_row = QHBoxLayout()
        self.wallpaper_label = label(self.wallpaper or self.t("wallpaperEmpty"), "note")
        file_row.addWidget(self.wallpaper_label, 1)
        file_row.addWidget(button(self.t("chooseFile"), self.choose_wallpaper))
        layout.addLayout(file_row)
        form = self.form()
        form.addRow(self.t("wallpaperMode"), self.combo("wallpaper_mode", [
            (mode, self.t("mode_" + mode)) for mode in WALLPAPER_MODES],
            desktop.get("wallpaper", {}).get("mode", "zoom")))
        layout.addLayout(form)
        layout.addWidget(label(self.t("wallpaperNote"), "note"))
        return tab

    def form_tab(self, rows, note=None):
        tab, layout = self.tab_page()
        form = self.form()
        for text, field in rows:
            form.addRow(text, field)
        layout.addLayout(form)
        if note:
            layout.addWidget(label(self.t(note), "note"))
        layout.addStretch()
        return tab

    def combo(self, name, choices, current):
        widget = QComboBox()
        for value, text in choices:
            widget.addItem(text, value)
        widget.setCurrentIndex(max(0, widget.findData(current)))
        widget.currentIndexChanged.connect(self.update_preview)
        setattr(self, name, widget)
        return widget

    def spin(self, name, low, high, value, suffix):
        widget = QSpinBox()
        widget.setRange(low, high)
        widget.setValue(max(low, min(high, int(value))))
        widget.setSuffix(suffix)
        widget.valueChanged.connect(self.update_preview)
        setattr(self, name, widget)
        return widget

    def slider(self, name, minimum, value):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QSlider(Qt.Orientation.Horizontal)
        widget.setRange(minimum, 100)
        widget.setValue(max(minimum, min(100, round(float(value) * 100))))
        value_label = label(f"{widget.value() / 100:.2f}", "note", wrap=False)
        value_label.setMinimumWidth(40)
        widget.valueChanged.connect(lambda v: value_label.setText(f"{v / 100:.2f}"))
        widget.valueChanged.connect(self.update_preview)
        layout.addWidget(widget, 1)
        layout.addWidget(value_label)
        setattr(self, name, widget)
        return row

    def check(self, name, key, value):
        widget = QCheckBox(self.t(key))
        widget.setChecked(bool(value))
        widget.toggled.connect(self.update_preview)
        setattr(self, name, widget)
        return widget

    def selected_theme(self):
        checked = self.theme_group.checkedButton() if hasattr(self, "theme_group") else None
        return checked.value if checked else THEME_DEFAULT

    def eduka_values(self):
        theme = self.selected_theme()
        style = self.panel_style_group.checkedButton()
        position = self.position_group.checkedButton()
        panel = {"menu_label": self.menu_label.text().strip() or "Edukasaun",
                 "menu_icon": self.menu_icon.text().strip() or START_ICON,
                 "show_menu_text": self.show_text.isChecked(), "menu_icon_size": self.menu_icon_size.value(),
                 "height": self.panel_height.value(), "width_percent": self.panel_width.value(),
                 "transparency": self.panel_transparency.value() / 100,
                 "taskbar_style": self.taskbar_style.currentData(),
                 "position": position.property("value") if position else "Bottom",
                 "panel_style": style.value if style else "floating", "theme_style": theme}
        desktop = {"layout": self.desktop_layout.currentData(), "last_category": self.default_section.currentData(),
                   "width_percent": self.desktop_width.value(), "height_percent": self.desktop_height.value(),
                   "transparency": self.desktop_transparency.value() / 100,
                   "low_resource_mode": self.low_resource.isChecked(), "enable_shadows": self.shadows.isChecked(),
                   "theme_style": theme, "glass_blur": self.glass_blur.isChecked(), "show_right_panel": True,
                   "visual_accessibility": self.vision.isChecked(),
                   "hearing_accessibility": self.hearing.isChecked(), "orca_enabled": self.orca.isChecked(),
                   "accent_color": self.accent, "multicolor": self.multicolor.isChecked(),
                   "effects_enabled": self.effects.isChecked(), "effect_hover": self.effect_hover.currentData(),
                   "effect_launch": self.effect_launch.currentData(), "tile_size": self.tile_size.currentData()}
        if self.wallpaper_changed and self.wallpaper:
            desktop["wallpaper"] = {"images": [self.wallpaper], "mode": self.wallpaper_mode.currentData(),
                                    "slideshow": False}
        menu = {"mode": "Eduka-Desktop", "language": self.menu_language.currentData()}
        return panel, desktop, menu

    def update_preview(self, *args):
        if not hasattr(self, "orca"):
            return  # Still building the page.
        theme = self.selected_theme()
        glass = theme in GLASS_THEMES
        if glass:
            self.low_resource.setChecked(False)
        if theme == THEME_LOW:
            self.low_resource.setChecked(True)
        self.low_resource.setEnabled(not glass and theme != THEME_LOW)
        self.glass_blur.setEnabled(theme == THEME_LIQUID)
        self.multicolor.setEnabled(theme not in (THEME_LOW, THEME_MULTI))
        self.theme_note.setText(self.t("themeHint_" + theme_key(theme)))
        panel, desktop, _ = self.eduka_values()
        self.preview.update_preview(panel, desktop, self.short_clock(), self.wallpaper)

    def theme_card_toggled(self, card, checked):
        if not checked:
            return
        if card.value in GLASS_THEMES and not self.glass_confirmed:
            memory, threads, capable = glass_capability()
            detected = self.t("liquidDetected", memory=f"{memory:.1f}", threads=threads)
            if not capable:
                QMessageBox.warning(self, self.t("liquidTitle"), self.t("liquidRequirement") + "\n\n" + detected +
                                    "\n\n" + self.t("liquidRefused"))
                self.theme_cards[THEME_DEFAULT].setChecked(True)
                return
            answer = QMessageBox.question(self, self.t("liquidTitle"), self.t("liquidRequirement") + "\n\n" +
                                          detected, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                          QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                self.theme_cards[THEME_DEFAULT].setChecked(True)
                return
            self.glass_confirmed = True
        self.update_preview()

    def effects_toggled(self, enabled):
        if not enabled or self.effects_confirmed:
            return
        memory, threads, capable = effects_capability()
        if not capable:
            QMessageBox.information(self, self.t("effectsTitle"), self.t("effectsRequirement") + "\n\n" +
                                    self.t("liquidDetected", memory=f"{memory:.1f}", threads=threads))
            self.effects.setChecked(False)
            return
        self.effects_confirmed = True

    def set_accent(self, color):
        self.accent = color
        for swatch in self.accent_group.buttons():
            swatch.setChecked(swatch.color.casefold() == color.casefold())
        self.update_preview()

    def restore_eduka_defaults(self):
        self.theme_cards[THEME_DEFAULT].setChecked(True)
        self.set_accent("")
        self.panel_transparency.setValue(round(DEFAULT_PANEL["transparency"] * 100))
        self.desktop_transparency.setValue(round(DEFAULT_DESKTOP["transparency"] * 100))
        for name in ("shadows", "multicolor", "glass_blur", "effects", "vision", "hearing", "orca"):
            getattr(self, name).setChecked(False)
        self.low_resource.setChecked(DEFAULT_DESKTOP["low_resource_mode"])
        self.menu_label.setText(DEFAULT_PANEL["menu_label"])
        self.menu_icon.setText(DEFAULT_PANEL["menu_icon"])
        self.show_text.setChecked(DEFAULT_PANEL["show_menu_text"])
        self.menu_icon_size.setValue(DEFAULT_PANEL["menu_icon_size"])
        self.panel_height.setValue(DEFAULT_PANEL["height"])
        self.panel_width.setValue(DEFAULT_PANEL["width_percent"])
        self.panel_style_cards["floating"].setChecked(True)
        for chip in self.position_group.buttons():
            chip.setChecked(chip.property("value") == "Bottom")
        for combo, value in ((self.taskbar_style, DEFAULT_PANEL["taskbar_style"]),
                             (self.desktop_layout, DEFAULT_DESKTOP["layout"]),
                             (self.default_section, DEFAULT_DESKTOP["last_category"]),
                             (self.tile_size, DEFAULT_DESKTOP["tile_size"]), (self.menu_language, "system"),
                             (self.effect_hover, DEFAULT_DESKTOP["effect_hover"]),
                             (self.effect_launch, DEFAULT_DESKTOP["effect_launch"])):
            combo.setCurrentIndex(max(0, combo.findData(value)))
        self.desktop_width.setValue(DEFAULT_DESKTOP["width_percent"])
        self.desktop_height.setValue(DEFAULT_DESKTOP["height_percent"])
        self.update_preview()
        self.message.setText(self.t("defaultsRestored"))

    # Page 5: Applications ---------------------------------------------------

    def apps_page(self):
        widget, layout = self.page("toolsForEveryday", "appsTitle", "appsLead")
        filters = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItem("★  " + self.t("recommendedCategory"), "recommended")
        self.category_combo.addItem(self.t("allCategories"), "all")
        for key in ["educationGames", "developmentTools", "officeDocuments", "internetMail", "audioVideo",
                    "graphicsDesign", "systemTools", "accessibility"]:
            self.category_combo.addItem(self.t(key), key)
        self.category_combo.setAccessibleName(self.t("category"))
        self.source_combo = QComboBox()
        for name, key in [(self.t("aptSource"), "apt"), (self.t("flatpakSource"), "flatpak"),
                          (self.t("vendorRepository"), "brave")]:
            self.source_combo.addItem(name, key)
        self.source_combo.setAccessibleName(self.t("source"))
        self.category_combo.currentIndexChanged.connect(self.populate_apps)
        self.source_combo.currentIndexChanged.connect(self.populate_apps)
        filters.addWidget(self.category_combo, 2)
        filters.addWidget(self.source_combo, 1)
        self.refresh_button = button(self.t("refresh"), self.start_scan)
        filters.addWidget(self.refresh_button)
        layout.addLayout(filters)
        self.scan_status = label(self.t("scanProgress"), "note")
        layout.addWidget(self.scan_status)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", self.t("application"), self.t("description"), self.t("weight")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setWordWrap(True)
        self.table.setMinimumHeight(330)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        self.consent = QCheckBox()
        layout.addWidget(self.consent)
        actions = QHBoxLayout()
        self.install_button = button(self.t("installSelected"), self.request_install, True)
        actions.addWidget(self.install_button)
        actions.addWidget(button(self.t("viewCommands"), self.show_commands))
        actions.addWidget(button(self.t("exportInventory"), self.export_inventory, name="ghost"))
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(label(self.t("catalogFreshness"), "note"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(2000)
        self.log.setAccessibleName(self.t("log"))
        self.log.setPlaceholderText(self.t("log"))
        self.log.setMinimumHeight(110)
        self.log.setMaximumHeight(180)
        layout.addWidget(self.log)
        layout.addStretch()
        return widget

    # Page 6: Sponsors and support -------------------------------------------

    def sponsors_page(self):
        widget, layout = self.page("sponsorsEyebrow", "sponsorsTitle", "sponsorsLead")
        for field, key in (("sponsors", "sponsors"), ("partners", "partners")):
            layout.addWidget(label(self.t(key).upper(), "section"))
            entries = [entry for entry in (sponsor_entry(item) for item in self.project.get(field, [])) if entry]
            cards = [self.logo_card(entry) for entry in entries] or \
                [self.logo_card(None, field) for _ in range(3)]
            layout.addLayout(self.grid(cards, 3))
        layout.addWidget(self.heading("supportEyebrow"))
        sponsor_button = button(self.t("becomeSponsorAction"), lambda: self.open_link("sponsor_contact"))
        sponsor_button.setEnabled(bool(self.project.get("sponsor_contact")))
        github_button = button(self.t("contributeAction"), lambda: self.open_link("github"))
        github_button.setEnabled(bool(self.project.get("github")))
        layout.addLayout(self.grid([
            self.card(self.t("supportProject"), self.t("donationBody") + " " + self.t("donationOptional"),
                      button(self.t("donatePayPal"), lambda: self.open_link("paypal"), True), "heart"),
            self.card(self.t("becomeSponsor"), self.t("becomeSponsorBody"), sponsor_button, "star"),
            self.card(self.t("contribute"), self.t("contributeBody"), github_button, "code"),
        ], 3))
        layout.addStretch()
        return widget

    def logo_card(self, entry, field="sponsors"):
        frame = QFrame()
        frame.setObjectName("logoCard" if entry else "logoPlaceholder")
        frame.setMinimumHeight(118 if entry is None else 150)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 14, 14, 12)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setMinimumHeight(84 if entry else 40)
        pixmap = QPixmap(str(entry["logo"])) if entry and entry["logo"] else QPixmap()
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(180, 84, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.SmoothTransformation))
            logo.setAccessibleName(entry["name"])
        else:
            logo.setText(entry["name"] if entry else self.t("logoPlaceholder"))
            logo.setObjectName("logoText" if entry else "placeholderText")
            logo.setWordWrap(True)
        layout.addWidget(logo, 1)
        if entry:
            name = label(entry["name"], "cardTitle")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(name)
            if entry["url"]:
                visit = button(self.t("visit"), lambda checked=False, url=entry["url"]: self.open_url(url))
                layout.addWidget(visit, 0, Qt.AlignmentFlag.AlignCenter)
        else:
            hint = label(self.t("logoPlaceholderHint" if field == "sponsors" else "partnerPlaceholderHint"), "note")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)
        return frame

    # Page 7: Community and finish -------------------------------------------

    def finish_page(self):
        widget = QWidget()
        widget.setObjectName("page")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 10, 12, 10)
        layout.setSpacing(18)
        hero = QFrame()
        hero.setObjectName("hero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(34, 28, 34, 28)
        hero_layout.setSpacing(24)
        badge = QLabel()
        badge.setPixmap(glyph("check", "#f5d76e", 78))
        hero_layout.addWidget(badge)
        text = QVBoxLayout()
        text.addWidget(label(self.t("journeyStarts"), "heroLanguage", wrap=False))
        text.addWidget(label(self.t("finishTitle"), "heroTitle"))
        text.addWidget(label(self.t("finishLead"), "heroBody"))
        hero_layout.addLayout(text, 1)
        layout.addWidget(shadow(hero, 36, 60, 10))
        summary = QFrame()
        summary.setObjectName("card")
        summary_layout = QHBoxLayout(summary)
        summary_layout.setContentsMargins(22, 16, 22, 16)
        self.summary_values = {}
        for key, icon in (("summaryZone", "clock"), ("summaryTheme", "palette"), ("summaryApps", "apps")):
            item = QHBoxLayout()
            item.setSpacing(12)
            item.addWidget(self.icon_tile(icon, 22))
            texts = QVBoxLayout()
            texts.setSpacing(0)
            texts.addWidget(label(self.t(key), "note", wrap=False))
            value = label("", "statValue", wrap=False)
            self.summary_values[key] = value
            texts.addWidget(value)
            item.addLayout(texts, 1)
            summary_layout.addLayout(item, 1)
        layout.addWidget(summary)
        layout.addWidget(self.heading("joinCommunity"))
        links = []
        for field, title, body, icon in [("website", self.t("officialWebsite"), self.t("websiteBody"), "globe"),
                                         ("facebook", "Facebook", self.t("facebookBody"), "people"),
                                         ("whatsapp", self.t("whatsappChannel"), self.t("whatsappBody"), "chat"),
                                         ("github", "GitHub", self.t("githubBody"), "code")]:
            link_button = button(self.t("open"), lambda checked=False, field=field: self.open_link(field))
            link_button.setEnabled(bool(self.project.get(field)))
            link_button.setToolTip(self.project.get(field, ""))
            links.append(self.card(title, body, link_button, icon))
        layout.addLayout(self.grid(links, 4))
        layout.addWidget(self.heading("ourGoals"))
        layout.addLayout(self.grid([self.card(self.t(key), self.t(key + "Body"), name="softCard")
                                    for key in ("goalEducation", "goalAccess", "goalSkills")], 3))
        layout.addWidget(self.card(self.t("developmentTeam"),
                                   "\n".join(self.project.get("developers", [])) or self.t("pendingCredits"),
                                   name="softCard"))
        layout.addWidget(label(self.t("upstreamThanks"), "note"))
        layout.addStretch()
        return widget

    def update_summary(self):
        self.summary_values["summaryZone"].setText((self.selected_timezone() or DEFAULT_TIMEZONE).replace("_", " "))
        self.summary_values["summaryTheme"].setText(self.t("theme_" + theme_key(self.selected_theme())))
        self.summary_values["summaryApps"].setText(self.t("appsInstalled", count=self.installed_count))

    # Navigation -------------------------------------------------------------

    def navigate(self, page):
        if not hasattr(self, "stack") or not 0 <= page < len(PAGES):
            return
        self.stack.setCurrentIndex(page)
        self.visited.add(page)
        for index, step in enumerate(self.step_buttons):
            step.set_state("current" if index == page else
                           "done" if index in self.visited and index < page else "todo")
        self.rail_progress.setValue(page + 1)
        self.back_button.setEnabled(page > 0)
        last = page == len(PAGES) - 1
        self.always.setVisible(last)
        self.counter.setVisible(not last)
        self.next_button.setText(self.t("startDesktop" if self.session else "finish") if last
                                 else self.t("next") + "  ›")
        self.counter.setText(self.t("stepCounter", current=page + 1, total=len(PAGES)))
        self.message.setText("")
        if last:
            self.update_summary()

    def next_page(self):
        page = self.stack.currentIndex()
        if page == len(PAGES) - 1:
            self.close()
        else:
            self.navigate(page + 1)

    def update_always(self, value):
        self.preferences["always_show"] = value
        self.persist()

    def persist(self):
        try:
            save_preferences(self.preferences)
        except OSError as error:
            self.error(error)

    def busy(self):
        return bool(self.worker is not None or self.desktop_worker is not None or self.process is not None)

    # Application inventory and installation ---------------------------------

    def start_scan(self):
        if self.busy():
            return
        self.scan_status.setText(self.t("scanProgress"))
        self.install_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.worker = ScanWorker(self)
        self.worker.completed.connect(self.scan_finished)
        self.worker.finished.connect(self.worker_finished)
        self.worker.start()

    def scan_finished(self, inventory, apps, availability):
        self.inventory, self.apps, self.availability = inventory, apps, availability
        self.scanned = True
        self.populate_apps()
        if inventory.errors:
            self.log.setPlainText("\n".join(inventory.errors))

    def worker_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.refresh_button.setEnabled(True)
        self.populate_apps()
        if self.pending:
            identifiers, source = self.pending
            self.pending = None
            current = {app["id"]: app for app in self.apps}
            if self.inventory.errors or any(identifier not in current for identifier in identifiers):
                self.message.setText(self.t("preflightChanged"))
                return
            if source == "apt" and any(not self.availability.get(identifier) for identifier in identifiers):
                self.message.setText(self.t("noCandidate"))
                return
            self.begin_install([current[identifier] for identifier in identifiers], source)

    def populate_apps(self):
        if not hasattr(self, "table"):
            return
        source = self.source_combo.currentData()
        category = self.category_combo.currentData()
        self.table.setRowCount(0)
        shown = [app for app in self.apps if source in app["sources"] and
                 (category == "all" or category == app["category"] or
                  (category == "recommended" and app.get("recommended")))]
        shown.sort(key=lambda app: not app.get("recommended"))
        colors = {"light": "#00785f", "medium": "#8a6500", "heavy": "#b3261e"}
        for app in shown:
            row = self.table.rowCount()
            self.table.insertRow(row)
            check = QTableWidgetItem()
            check.setData(Qt.ItemDataRole.UserRole, app["id"])
            check.setCheckState(Qt.CheckState.Unchecked)
            enabled = source != "apt" or self.availability.get(app["id"], False)
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable |
                           (Qt.ItemFlag.ItemIsEnabled if enabled else Qt.ItemFlag.NoItemFlags))
            self.table.setItem(row, 0, check)
            name = QTableWidgetItem(("★ " if app.get("recommended") else "") + app["name"])
            font = name.font()
            font.setBold(True)
            name.setFont(font)
            if app.get("recommended"):
                name.setToolTip(self.t("recommendedTip"))
            self.table.setItem(row, 1, name)
            description = self.t(app["description"])
            if not enabled:
                description += "\n" + self.t("noCandidate")
            self.table.setItem(row, 2, QTableWidgetItem(description))
            weight = app.get("weight", "medium")
            badge = QTableWidgetItem("●  " + self.t("weight_" + weight))
            badge.setForeground(QColor(colors.get(weight, colors["medium"])))
            self.table.setItem(row, 3, badge)
        self.table.resizeRowsToContents()
        self.consent.setVisible(source in ("flatpak", "brave"))
        self.consent.setChecked(False)
        self.consent.setText(self.t("consentFlathub" if source == "flatpak" else "consentBrave"))
        ready = self.scanned and not self.inventory.errors and not self.busy()
        self.install_button.setEnabled(ready and self.table.rowCount() > 0)
        if source == "flatpak" and not shutil.which("flatpak"):
            self.install_button.setEnabled(False)
            self.scan_status.setText(self.t("flatpakMissing"))
        elif self.scanned:
            self.scan_status.setText(self.t("scanError") if self.inventory.errors else
                                     self.t("scanResult", count=len(self.apps)))

    def selected_apps(self):
        identifiers = {self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                       for row in range(self.table.rowCount())
                       if self.table.item(row, 0).checkState() == Qt.CheckState.Checked}
        return [app for app in self.apps if app["id"] in identifiers]

    def request_install(self):
        if self.busy() or not self.scanned or self.inventory.errors:
            return
        apps = self.selected_apps()
        if not apps:
            self.message.setText(self.t("noSelections"))
            return
        source = self.source_combo.currentData()
        # Preserve explicit consent while rechecking the complete inventory.
        self.install_consent = self.consent.isChecked()
        if source == "brave" and not self.install_consent:
            self.message.setText(self.t("consentBrave"))
            return
        answer = QMessageBox.question(self, self.t("confirmInstall"),
            "\n".join(app["name"] for app in apps) + "\n\n" + self.t("confirmDetail"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.pending = ([app["id"] for app in apps], source)
        self.start_scan()

    def begin_install(self, apps, source):
        try:
            if source in ("apt", "brave") and not Path("/usr/lib/edukasaun-welcome/admin-helper").is_file():
                raise RuntimeError(self.t("helperMissing"))
            commands = install_commands(apps, source, self.install_consent, self.install_consent)
        except (OSError, ValueError, RuntimeError) as error:
            self.error(error)
            return
        self.log.clear()
        self.installing = len(apps)
        for widget in (self.refresh_button, self.category_combo, self.source_combo, self.install_button):
            widget.setEnabled(False)
        self.run_commands(commands, self.log, self.finish_install)

    def finish_install(self, success):
        self.message.setText(self.t("installComplete" if success else "installFailed"))
        if success:
            self.installed_count += self.installing
        self.installing = 0
        for widget in (self.refresh_button, self.category_combo, self.source_combo):
            widget.setEnabled(True)
        self.start_scan()

    # Sequential, asynchronous command runner --------------------------------

    def run_commands(self, commands, log, done):
        self.commands = list(commands)
        self.command_log = log
        self.commands_done = done
        self.run_next_command()

    def run_next_command(self):
        if not self.commands:
            self.end_commands(True)
            return
        arguments = self.commands.pop(0)
        self.write_log("$ " + shlex.join(arguments) + "\n")
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.command_finished)
        self.process.errorOccurred.connect(self.command_error)
        self.process.start(arguments[0], arguments[1:])

    def write_log(self, text):
        if self.command_log is not None:
            self.command_log.moveCursor(self.command_log.textCursor().MoveOperation.End)
            self.command_log.insertPlainText(text)
            self.command_log.ensureCursorVisible()

    def read_output(self):
        if self.process:
            self.write_log(bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace"))

    def command_finished(self, code, status):
        if self.process is None:
            return
        self.read_output()
        self.process.deleteLater()
        self.process = None
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.run_next_command()
        else:
            self.end_commands(False)

    def command_error(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.process:
            self.write_log(self.process.errorString() + "\n")
            self.process.deleteLater()
            self.process = None
            self.end_commands(False)

    def end_commands(self, success):
        self.commands = []
        done, self.commands_done = self.commands_done, None
        if done is not None:
            done(success)

    def show_commands(self):
        try:
            commands = install_commands(self.selected_apps(), self.source_combo.currentData(),
                                        self.consent.isChecked(), self.consent.isChecked())
        except ValueError as error:
            self.error(error)
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(self.t("viewCommands"))
        dialog.resize(650, 300)
        layout = QVBoxLayout(dialog)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText("\n".join(shlex.join(command) for command in commands))
        layout.addWidget(text)
        layout.addWidget(button(self.t("close"), dialog.close))
        dialog.exec()

    # Desktop personalization ------------------------------------------------

    def choose_menu_icon(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t("menuIcon"), "/usr/share/icons",
                                             "Images (*.png *.svg *.xpm *.jpg)")
        if path:
            self.menu_icon.setText(path)

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.accent or "#00a879"), self, self.t("accentColor"))
        if color.isValid():
            self.set_accent(color.name())

    def set_wallpaper(self, path):
        self.wallpaper = path
        self.wallpaper_changed = True
        self.wallpaper_label.setText(path)
        for card in self.wallpaper_group.buttons():
            card.setChecked(card.value == path)
        self.update_preview()

    def choose_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t("chooseFile"), str(Path.home()),
                                             "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self.set_wallpaper(path)

    def apply_settings(self):
        if self.busy():
            self.message.setText(self.t("closeBusy"))
            return
        panel, desktop, menu = self.eduka_values()
        orca = desktop["orca_enabled"]
        theme = desktop["theme_style"]
        # Like Eduka-Settings: apply the desktop theme when it changed or is a system-wide theme.
        system_theme = theme not in (THEME_DEFAULT, THEME_LIQUID)
        values = {"eduka": (panel, desktop, menu),
                  "theme": theme if theme != self.initial_theme or system_theme else None,
                  "orca": orca if (orca or orca != self.initial_orca) else None,
                  "wallpaper": "wallpaper" in desktop}
        self.apply_button.setEnabled(False)
        self.message.setText(self.t("applying"))
        self.desktop_worker = DesktopWorker(values, self)
        self.desktop_worker.completed.connect(self.desktop_finished)
        self.desktop_worker.finished.connect(self.desktop_thread_finished)
        self.desktop_worker.start()

    def desktop_finished(self, error, notes):
        if error:
            # Eduka-Desktop may have turned Orca off again; show the saved state.
            self.orca.setChecked(bool(read_eduka_settings()["desktop"].get("orca_enabled")))
            self.error(error)
            return
        self.initial_orca = self.orca.isChecked()
        self.initial_theme = self.selected_theme()
        self.wallpaper_changed = False
        self.message.setText(self.t("desktopApplied") + (" " + notes if notes else ""))

    def desktop_thread_finished(self):
        self.desktop_worker.deleteLater()
        self.desktop_worker = None
        self.apply_button.setEnabled(True)

    # Misc -------------------------------------------------------------------

    def run_tool(self, key):
        if not open_tool(self.project.get("suite_tools", {}).get(key, [])):
            self.message.setText(self.t("notInstalledApp"))

    def open_link(self, key):
        self.open_url(self.project.get(key, ""))

    def open_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc:
            QDesktopServices.openUrl(QUrl(url))

    def show_about(self):
        QMessageBox.about(self, self.t("about"), self.t("nativeTitle") + "\n\n" + self.t("suiteLead") +
                          "\n\n" + self.t("developmentBuild") + "\nGPL-3.0-or-later · Python / Qt 6")

    def export_inventory(self):
        if not self.scanned:
            self.message.setText(self.t("scanProgress"))
            return
        path, _ = QFileDialog.getSaveFileName(self, self.t("exportInventory"),
                                             "edukasaun-installed-apps.json", "JSON (*.json)")
        if path:
            try:
                write_inventory(path, self.inventory)
            except OSError as error:
                self.error(error)

    def error(self, error):
        QMessageBox.warning(self, self.t("operationError"), str(error))

    def closeEvent(self, event):
        if self.busy():
            self.message.setText(self.t("closeBusy"))
            event.ignore()
            return
        event.accept()
        if self.session and self.start_desktop_on_close:
            # Welcome Screen first, then the desktop: start Eduka-Desktop on the way out.
            start_desktop(self.project.get("eduka_desktop", {}))


def launch(language="en", preferences=None, session=False, before_session=False):
    application = QApplication([])
    application.setApplicationName("Edukasaun Welcome")
    application.setDesktopFileName("edukasaun-welcome")
    window = WelcomeWindow(language, preferences, session=session or before_session)
    window.start_desktop_on_close = session
    if session or before_session:
        # Eduka-Desktop is not running yet, so take the whole screen.
        window.showMaximized()
    else:
        window.show()
    return application.exec()
