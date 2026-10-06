"""Native six-page Welcome Screen for Edukasaun OS; all system operations are asynchronous."""
import shlex
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from PyQt6.QtCore import QDateTime, QProcess, QSize, QThread, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFontDatabase, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDateTimeEdit, QDialog, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QScrollArea, QSlider, QSpinBox, QStackedWidget,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)
from .catalog import load_project, recommendations, install_commands
from .desktop import apply_desktop, open_tool, theme_choices
from .eduka_desktop import (
    DEFAULT_DESKTOP, DEFAULT_PANEL, LAYOUTS, SECTIONS, START_ICON, TASKBAR_STYLES, THEME_LIQUID, THEMES,
    configure_orca, installed as eduka_installed, liquid_glass_capability, normalize_theme,
    read_settings as read_eduka_settings, save_settings,
)
from .i18n import Translator
from .inventory import Inventory, apt_available, scan_inventory, write_inventory
from .preferences import config_home, load_preferences, save_preferences
from .session import start_desktop
from .timesettings import (
    DEFAULT_TIMEZONE, current_timezone, format_clock, time_commands, timezone_choices, utc_offset,
)

PAGES = ["stepWelcome", "stepTime", "stepSuite", "stepDesktop", "stepApps", "stepSponsors", "stepFinish"]
SPONSOR_DIRS = [Path(__file__).parent / "data/sponsors", Path("/usr/share/edukasaun-welcome/sponsors")]

STYLE = """
QWidget { font-family: sans-serif; font-size: 14px; color: #173d37; }
QWidget#shell, QWidget#page { background: #f4faf7; }
QFrame#rail { background: #0b6355; border-radius: 18px; }
QFrame#rail QLabel { color: #ffffff; }
QLabel#brand { font-size: 24px; font-weight: 700; }
QLabel#railNote { color: #bfe6d8; font-size: 12px; }
QLabel#title { font-size: 30px; font-weight: 700; color: #0b6355; }
QLabel#lead { color: #4d6963; font-size: 15px; }
QLabel#note { color: #5f7a74; font-size: 13px; }
QLabel#eyebrow { color: #008c70; font-weight: 700; font-size: 12px; letter-spacing: 1px; }
QLabel#hero { font-size: 26px; font-weight: 700; padding: 22px; color: #0b6355;
              background: #dcf4e6; border-radius: 12px; }
QLabel#clock { font-size: 22px; font-weight: 700; color: #0b6355; }
QLabel#cardTitle { font-size: 16px; font-weight: 700; }
QFrame#card { background: white; border: 1px solid #d7e7df; border-radius: 12px; }
QPushButton { background: #ffffff; border: 1px solid #b9d2c7; border-radius: 8px; padding: 10px 16px; }
QPushButton:hover { background: #e4f4ec; }
QPushButton#primary { background: #00856e; color: white; border: 1px solid #00856e; font-weight: 700; }
QPushButton#primary:hover { background: #006c59; }
QPushButton:disabled { color: #768983; background: #edf2ef; }
QComboBox, QLineEdit, QDateTimeEdit { border: 1px solid #bad2c7; border-radius: 6px;
                                      background: white; padding: 8px; }
QListWidget { background: transparent; border: 0; color: white; outline: 0; }
QListWidget::item { padding: 14px 8px; border-radius: 8px; }
QListWidget::item:selected { background: #208771; color: white; }
QTableWidget { background: white; border: 1px solid #d7e7df; border-radius: 6px; gridline-color: #e5efea; }
QHeaderView::section { background: #e7f3ed; border: 0; padding: 9px; font-weight: 700; }
QTextEdit { background: #f8fbf9; border: 1px solid #d7e7df; border-radius: 6px; }
QCheckBox { spacing: 8px; }
QScrollArea { border: 0; background: transparent; }
QFrame#logoCard { background: white; border: 1px solid #d7e7df; border-radius: 12px; }
QFrame#logoPlaceholder { background: #fbfdfc; border: 2px dashed #b9d2c7; border-radius: 12px; }
QLabel#placeholderText { color: #7b958e; font-size: 16px; font-weight: 700; }
QLabel#logoText { color: #0b6355; font-size: 20px; font-weight: 700; }
QFrame#preview { border-radius: 14px; border: 1px solid #b9d2c7;
                 background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #7fd1b9, stop:0.55 #2f8f83, stop:1 #12455f); }
QLabel#previewCaption { color: #173d37; font-weight: 700; }
QTabWidget::pane { border: 1px solid #d7e7df; border-radius: 10px; background: #f4faf7; }
QTabBar::tab { padding: 9px 14px; color: #4d6963; }
QTabBar::tab:selected { color: #0b6355; font-weight: 700; border-bottom: 3px solid #00856e; }
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
    """Save Eduka-Desktop settings, sync Orca, then apply optional LXQt changes."""
    completed = pyqtSignal(str, str)

    def __init__(self, values, parent):
        super().__init__(parent)
        self.values = values

    def run(self):
        notes = []
        try:
            panel, desktop, menu = self.values["eduka"]
            save_settings(panel, desktop, menu)
            if self.values.get("orca") is not None:
                ok, message = configure_orca(self.values["orca"])
                if not ok:
                    save_settings({}, {"orca_enabled": False}, {})
                    raise RuntimeError(message)
                notes.append(message)
            lxqt = self.values.get("lxqt", {})
            if any(lxqt.values()):
                apply_desktop(lxqt)
            self.completed.emit("", "\n".join(note for note in notes if note))
        except Exception as error:
            self.completed.emit(str(error), "")


class PanelPreview(QFrame):
    """Small live preview of Eduka-Panel on a desktop background."""

    def __init__(self):
        super().__init__()
        self.setObjectName("preview")
        self.setMinimumHeight(150)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 12)
        self.desk_window = QFrame()
        self.window_layout = QHBoxLayout(self.desk_window)
        self.caption = label("", "previewCaption")
        self.window_layout.addWidget(self.caption)
        layout.addWidget(self.desk_window, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
        self.panel = QFrame()
        panel_layout = QHBoxLayout(self.panel)
        panel_layout.setContentsMargins(10, 4, 10, 4)
        self.menu_button = QPushButton()
        self.menu_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        panel_layout.addWidget(self.menu_button)
        self.tasks = label("", "previewTasks", wrap=False)
        panel_layout.addWidget(self.tasks, 1)
        self.clock = label("", "previewTasks", wrap=False)
        panel_layout.addWidget(self.clock)
        self.panel_row = QHBoxLayout()
        self.panel_row.addWidget(self.panel)
        layout.addLayout(self.panel_row)

    def update_preview(self, panel, desktop, clock_text):
        liquid = panel["theme_style"] == "Liquid Glass"
        high_contrast = desktop.get("visual_accessibility")
        alpha = 1.0 if high_contrast else panel["transparency"]
        if high_contrast:
            background, text, border = "rgb(0, 0, 0)", "#ffffff", "#ffffff"
        elif liquid:
            background, text, border = f"rgba(235, 250, 245, {alpha:.2f})", "#0b3d35", "rgba(255,255,255,0.95)"
        else:
            background, text, border = f"rgba(12, 52, 46, {alpha:.2f})", "#ffffff", "rgba(255,255,255,0.15)"
        shadow = "border-bottom: 3px solid rgba(0,0,0,0.25);" if panel.get("enable_shadows") else ""
        self.panel.setStyleSheet(f"QFrame {{ background: {background}; border: 1px solid {border};"
                                 f" border-radius: 12px; {shadow} }} QLabel {{ color: {text}; border: 0;"
                                 f" background: transparent; }}")
        self.panel.setFixedHeight(int(panel["height"]))
        self.panel_row.setStretch(0, 1)
        self.panel.setMaximumWidth(max(240, int(self.width() * panel["width_percent"] / 100) - 32))
        size = int(panel["menu_icon_size"])
        self.menu_button.setIcon(QIcon(panel["menu_icon"]) if Path(panel["menu_icon"]).is_file()
                                 else QIcon(str(Path(__file__).parent / "data/icon.svg")))
        self.menu_button.setIconSize(QSize(size, size))
        self.menu_button.setText(" " + panel["menu_label"] if panel["show_menu_text"] else "")
        self.menu_button.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,0.18); color: {text};"
                                       " border: 0; border-radius: 10px; padding: 2px 10px; font-weight: 700; }")
        style = panel["taskbar_style"]
        tasks = ["Files", "Browser", "Writer"]
        self.tasks.setText("    " + "   ".join("▣" if style == "Icon only" else
                                              t if style == "Text only" else "▣ " + t for t in tasks))
        self.clock.setText(clock_text)
        window_alpha = 1.0 if high_contrast else desktop["transparency"]
        self.desk_window.setFixedSize(int(260 * desktop["width_percent"] / 100), int(64 * desktop["height_percent"] / 100))
        radius = 6 if desktop.get("visual_accessibility") else 14
        self.desk_window.setStyleSheet(f"QFrame {{ background: rgba(255,255,255,{window_alpha:.2f});"
                                  f" border-radius: {radius}px; }}")
        self.caption.setText("Eduka-Desktop · " + desktop["layout"] + " · " + desktop["last_category"])


def label(text, name="", wrap=True):
    widget = QLabel(text)
    widget.setWordWrap(wrap)
    if name:
        widget.setObjectName(name)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.clicked.connect(callback)
    if primary:
        widget.setObjectName("primary")
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
            candidate = (folder / Path(name).name)
            if candidate.is_file():
                logo = candidate
                break
    url = str(item.get("url", ""))
    parsed = urlparse(url)
    return {"name": str(item["name"]).strip(), "logo": logo,
            "url": url if parsed.scheme == "https" and parsed.netloc else ""}


class WelcomeWindow(QWidget):
    def __init__(self, language="en", preferences=None, auto_scan=True, session=False):
        super().__init__()
        self.preferences = preferences if preferences is not None else load_preferences()
        self.t = Translator(language)
        self.session = session
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
        self.wallpaper = ""
        self.accent = ""
        self.setObjectName("shell")
        self.setWindowTitle(self.t("nativeTitle"))
        self.resize(1080, 760)
        self.setMinimumSize(860, 640)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "data/icon.svg")))
        self.setStyleSheet(STYLE)
        self.build()
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        if auto_scan:
            QTimer.singleShot(100, self.start_scan)

    # Layout -----------------------------------------------------------------

    def build(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(22)
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(240)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(20, 26, 20, 22)
        rail_layout.addWidget(label("Edukasaun OS", "brand"))
        rail_layout.addWidget(label(self.t("railSubtitle"), "railNote"))
        rail_layout.addSpacing(14)
        self.steps = QListWidget()
        self.steps.setAccessibleName(self.t("firstSteps"))
        for i, key in enumerate(PAGES):
            self.steps.addItem(f"{i + 1:02d}   {self.t(key)}")
        self.steps.currentRowChanged.connect(self.navigate)
        rail_layout.addWidget(self.steps, 1)
        rail_layout.addWidget(label(self.t("educationFirst"), "railNote"))
        outer.addWidget(rail)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 0)
        self.stack = QStackedWidget()
        for make_page in [self.welcome_page, self.time_page, self.suite_page, self.desktop_page,
                          self.apps_page, self.sponsors_page, self.finish_page]:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(make_page())
            self.stack.addWidget(scroll)
        content_layout.addWidget(self.stack, 1)
        self.message = label("", "note")
        content_layout.addWidget(self.message)
        footer = QHBoxLayout()
        self.back_button = button(self.t("back"), lambda: self.navigate(self.stack.currentIndex() - 1))
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
        footer.addWidget(self.next_button)
        content_layout.addLayout(footer)
        outer.addWidget(content, 1)
        self.navigate(0)
        self.populate_apps()

    def page(self, eyebrow, title, lead):
        widget = QWidget()
        widget.setObjectName("page")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 22, 10, 10)
        layout.setSpacing(16)
        layout.addWidget(label(self.t(eyebrow), "eyebrow"))
        layout.addWidget(label(self.t(title), "title"))
        layout.addWidget(label(self.t(lead), "lead"))
        return widget, layout

    def card(self, title, body, action=None):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.addWidget(label(title, "cardTitle"))
        layout.addWidget(label(body, "lead"))
        if action is not None:
            row = QHBoxLayout()
            row.addWidget(action)
            row.addStretch()
            layout.addLayout(row)
        layout.addStretch()
        return frame

    def grid(self, cards, columns=2):
        grid = QGridLayout()
        grid.setSpacing(12)
        for index, widget in enumerate(cards):
            grid.addWidget(widget, index // columns, index % columns)
        for column in range(columns):
            grid.setColumnStretch(column, 1)
        return grid

    # Page 1: Welcome --------------------------------------------------------

    def welcome_page(self):
        widget, layout = self.page("educationFirst", "welcomeTitle", "welcomeLead")
        layout.addWidget(label(self.t("mainGreeting"), "hero"))
        systems = QFontDatabase.WritingSystem
        international = ["Welcome", "Bienvenue", "Bienvenido", "Willkommen", "Добро пожаловать",
            script_greeting("مرحبًا", "Marhaban", systems.Arabic),
            script_greeting("欢迎", "Huanying", systems.SimplifiedChinese),
            script_greeting("स्वागत है", "Swagat hai", systems.Devanagari)]
        asean = ["Selamat datang", "Maligayang pagdating",
            script_greeting("ยินดีต้อนรับ", "Yindi tonrap", systems.Thai), "Chào mừng",
            script_greeting("សូមស្វាគមន៍", "Soum sva kum", systems.Khmer),
            script_greeting("ຍິນດີຕ້ອນຮັບ", "Nyin di ton hap", systems.Lao),
            script_greeting("ကြိုဆိုပါတယ်", "Kyo so par", systems.Myanmar)]
        layout.addLayout(self.grid([
            self.card(self.t("cplp"), "Benvindu · Bem-vindo · Bem-vinda"),
            self.card(self.t("asean"), " · ".join(asean)),
            self.card(self.t("international"), " · ".join(international)),
            self.card(self.t("setupOverview"), self.t("setupOverviewBody")),
        ]))
        release = os_release()
        if release:
            layout.addWidget(label(self.t("installedSystem", name=release), "note"))
        layout.addStretch()
        return widget

    # Page 2: Date & time ----------------------------------------------------

    def time_page(self):
        widget, layout = self.page("timeEyebrow", "timeTitle", "timeLead")
        self.system_zone = current_timezone()
        self.zone_search = QLineEdit()
        self.zone_search.setPlaceholderText(self.t("searchTimezone"))
        self.zone_search.setAccessibleName(self.t("searchTimezone"))
        self.zone_search.textChanged.connect(self.filter_timezones)
        self.zone_combo = QComboBox()
        self.zone_combo.setAccessibleName(self.t("timezone"))
        self.zone_combo.setMaxVisibleItems(16)
        self.zone_combo.currentIndexChanged.connect(self.zone_changed)
        self.filter_timezones("")
        self.clock_format = QComboBox()
        self.clock_format.addItem(self.t("clock24"), True)
        self.clock_format.addItem(self.t("clock12"), False)
        self.clock_format.setCurrentIndex(0 if self.preferences.get("clock_24h", True) else 1)
        self.clock_format.setAccessibleName(self.t("clockFormat"))
        self.clock_format.currentIndexChanged.connect(self.update_clock_format)
        self.automatic_time = QCheckBox(self.t("automaticTime"))
        self.automatic_time.setChecked(True)
        self.manual_time = QDateTimeEdit()
        self.manual_time.setDisplayFormat("yyyy-MM-dd  HH:mm")
        self.manual_time.setCalendarPopup(True)
        self.manual_time.setAccessibleName(self.t("manualTime"))
        self.manual_time.setEnabled(False)
        self.reset_manual_time()
        self.automatic_time.toggled.connect(self.toggle_automatic_time)

        preview = QFrame()
        preview.setObjectName("card")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(18, 14, 18, 14)
        self.zone_title = label("", "cardTitle")
        self.clock_label = label("", "clock")
        preview_layout.addWidget(self.zone_title)
        preview_layout.addWidget(self.clock_label)
        layout.addWidget(preview)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow(self.t("searchTimezone"), self.zone_search)
        form.addRow(self.t("timezone"), self.zone_combo)
        form.addRow(self.t("clockFormat"), self.clock_format)
        form.addRow("", self.automatic_time)
        form.addRow(self.t("manualTime"), self.manual_time)
        layout.addLayout(form)
        self.time_button = button(self.t("applyTime"), self.apply_time, True)
        row = QHBoxLayout()
        row.addWidget(self.time_button)
        row.addStretch()
        layout.addLayout(row)
        self.time_status = label(self.t("currentTimezone", zone=self.system_zone or self.t("unknown")),
                                 "note")
        layout.addWidget(self.time_status)
        layout.addWidget(label(self.t("timeNote"), "note"))
        layout.addStretch()
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

    def zone_changed(self):
        self.reset_manual_time()
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

    def update_clock(self):
        zone = self.selected_timezone()
        if not hasattr(self, "clock_label"):
            return
        if not zone:
            self.zone_title.setText(self.t("noTimezoneMatch"))
            self.clock_label.setText("")
            return
        self.zone_title.setText(zone.replace("_", " ") + " · " + utc_offset(zone))
        self.clock_label.setText(format_clock(zone, self.clock_format.currentData() is not False))

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
            commands = time_commands(self.selected_timezone() or "", self.automatic_time.isChecked(),
                                     manual)
            if not shutil.which("timedatectl"):
                raise RuntimeError(self.t("timedatectlMissing"))
        except (ValueError, RuntimeError) as error:
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
        settings_button = button(self.t("openMenuSettings"), lambda: self.run_tool("suite"))
        settings_button.setEnabled(bool(self.project.get("suite_tools", {}).get("suite")))
        layout.addLayout(self.grid([
            self.card("Eduka-Desktop", self.t("suiteDesktop")),
            self.card("Eduka-Menu", self.t("suiteMenu")),
            self.card("Eduka-Panel", self.t("suitePanel")),
            self.card("Eduka-Menu-Settings", self.t("suiteSettings"), settings_button),
        ]))
        layout.addWidget(label(self.t("projectTools"), "eyebrow"))
        layout.addLayout(self.grid([
            self.card("EUS", self.t("toolEus")),
            self.card("Eduka-Konekta", self.t("toolKonekta")),
            self.card("Eduka-Block", self.t("toolBlock")),
        ], 3))
        about = QHBoxLayout()
        about.addWidget(button(self.t("about"), self.show_about))
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
        self.liquid_confirmed = normalize_theme(desktop.get("theme_style")) == THEME_LIQUID
        if not eduka_installed():
            layout.addWidget(label(self.t("edukaMissing"), "note"))
        self.preview = PanelPreview()
        layout.addWidget(self.preview)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self.form_tab([
            (self.t("visualTheme"), self.combo("visual_theme", THEMES, normalize_theme(desktop.get("theme_style")))),
            (self.t("panelTransparency"), self.slider("panel_transparency", panel["transparency"])),
            (self.t("desktopTransparency"), self.slider("desktop_transparency", desktop["transparency"])),
            ("", self.check("shadows", "enableShadows", desktop.get("enable_shadows"))),
            ("", self.check("low_resource", "lowResource", desktop.get("low_resource_mode"))),
        ], "themeNote"), self.tab_title("tabTheme"))
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
        tabs.addTab(self.form_tab([
            (self.t("menuLabel"), self.menu_label),
            (self.t("menuIcon"), menu_icon),
            ("", self.check("show_text", "showMenuText", panel["show_menu_text"])),
            (self.t("menuIconSize"), self.spin("menu_icon_size", 18, 48, panel["menu_icon_size"], " px")),
            (self.t("panelHeight"), self.spin("panel_height", 34, 58, panel["height"], " px")),
            (self.t("panelWidth"), self.spin("panel_width", 70, 100, panel["width_percent"], " %")),
            (self.t("taskbarStyle"), self.combo("taskbar_style", TASKBAR_STYLES, panel["taskbar_style"])),
        ]), "Eduka-Panel")
        tabs.addTab(self.form_tab([
            (self.t("defaultLayout"), self.combo("desktop_layout", LAYOUTS, desktop["layout"])),
            (self.t("defaultSection"), self.combo("section", SECTIONS[1:], desktop["last_category"])),
            (self.t("desktopWidth"), self.spin("desktop_width", 92, 99, desktop["width_percent"], " %")),
            (self.t("desktopHeight"), self.spin("desktop_height", 78, 95, desktop["height_percent"], " %")),
            ("", self.check("follow_language", "followLanguage", menu.get("language", "system") == "system")),
        ]), "Eduka-Desktop")
        tabs.addTab(self.form_tab([
            (self.t("vision"), self.check("vision", "visionAccess", desktop.get("visual_accessibility"))),
            (self.t("hearing"), self.check("hearing", "hearingAccess", desktop.get("hearing_accessibility"))),
            (self.t("screenReader"), self.check("orca", "orcaAccess", desktop.get("orca_enabled"))),
        ], "accessNote"), self.t("accessibility"))
        tabs.addTab(self.lxqt_tab(), self.tab_title("tabLxqt"))
        layout.addWidget(tabs)

        actions = QHBoxLayout()
        self.apply_button = button(self.t("apply"), self.apply_settings, True)
        actions.addWidget(self.apply_button)
        actions.addWidget(button(self.t("restoreDefaults"), self.restore_eduka_defaults))
        settings_button = button(self.t("openMenuSettings"), lambda: self.run_tool("suite"))
        actions.addWidget(settings_button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(label(self.t("desktopWarning"), "note"))
        self.update_preview()
        return widget

    def tab_title(self, key):
        return self.t(key).replace("&", "&&")  # A single & would become a keyboard mnemonic.

    def form_tab(self, rows, note=None):
        tab = QWidget()
        tab.setObjectName("page")
        form = QFormLayout(tab)
        form.setContentsMargins(8, 14, 8, 8)
        form.setSpacing(10)
        for text, field in rows:
            form.addRow(text, field)
        if note:
            form.addRow(label(self.t(note), "note"))
        return tab

    def combo(self, name, choices, current):
        widget = QComboBox()
        for choice in choices:
            widget.addItem(self.t("theme" + choice.replace(" ", "").replace("-", "")) if name == "visual_theme"
                           else choice, choice)
        widget.setCurrentIndex(max(0, widget.findData(current)))
        widget.currentIndexChanged.connect(self.update_preview)
        if name == "visual_theme":
            widget.currentIndexChanged.connect(self.theme_changed)
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

    def slider(self, name, value):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        widget = QSlider(Qt.Orientation.Horizontal)
        widget.setRange(45, 100)
        widget.setValue(max(45, min(100, round(float(value) * 100))))
        value_label = label(f"{widget.value() / 100:.2f}", wrap=False)
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

    def lxqt_tab(self):
        tab = QWidget()
        tab.setObjectName("page")
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 14, 8, 8)
        form = QFormLayout()
        form.setSpacing(10)
        self.theme_combo = QComboBox()
        self.icon_combo = QComboBox()
        for combo, kind, key in [(self.theme_combo, "theme", "theme"), (self.icon_combo, "icons", "icons")]:
            combo.addItem(self.t("keepCurrentSettings"), "")
            for name in theme_choices(kind):
                combo.addItem(name, name)
            combo.setAccessibleName(self.t(key))
            form.addRow(self.t(key), combo)
        self.color_button = button(self.t("keepCurrentSettings"), self.choose_color)
        form.addRow(self.t("accentColor"), self.color_button)
        file_row = QHBoxLayout()
        self.wallpaper_label = label(self.t("wallpaperEmpty"))
        file_row.addWidget(self.wallpaper_label, 1)
        file_row.addWidget(button(self.t("chooseFile"), self.choose_wallpaper))
        form.addRow(self.t("wallpaper"), file_row)
        layout.addLayout(form)
        self.wallpaper_preview = label("")
        self.wallpaper_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.wallpaper_preview)
        tools = QHBoxLayout()
        tools.addWidget(button(self.t("openAppearance"), lambda: self.run_tool("appearance")))
        tools.addWidget(button(self.t("openDesktop"), lambda: self.run_tool("desktop")))
        tools.addWidget(button(self.t("openEffects"), lambda: self.run_tool("effects")))
        tools.addStretch()
        layout.addLayout(tools)
        layout.addWidget(label(self.t("effectsNote"), "note"))
        layout.addStretch()
        return tab

    def eduka_values(self):
        theme = self.visual_theme.currentData()
        panel = {"menu_label": self.menu_label.text().strip() or "Edukasaun",
                 "menu_icon": self.menu_icon.text().strip() or START_ICON,
                 "show_menu_text": self.show_text.isChecked(), "menu_icon_size": self.menu_icon_size.value(),
                 "height": self.panel_height.value(), "width_percent": self.panel_width.value(),
                 "transparency": self.panel_transparency.value() / 100,
                 "taskbar_style": self.taskbar_style.currentData(), "position": "Bottom",
                 "theme_style": theme, "enable_shadows": self.shadows.isChecked()}
        desktop = {"layout": self.desktop_layout.currentData(), "last_category": self.section.currentData(),
                   "width_percent": self.desktop_width.value(), "height_percent": self.desktop_height.value(),
                   "transparency": self.desktop_transparency.value() / 100,
                   "low_resource_mode": self.low_resource.isChecked(), "enable_shadows": self.shadows.isChecked(),
                   "theme_style": theme, "show_right_panel": True,
                   "visual_accessibility": self.vision.isChecked(),
                   "hearing_accessibility": self.hearing.isChecked(), "orca_enabled": self.orca.isChecked()}
        menu = {"mode": "Eduka-Desktop", "language": "system" if self.follow_language.isChecked() else "en"}
        return panel, desktop, menu

    def update_preview(self):
        if not hasattr(self, "follow_language"):
            return  # Still building the page.
        liquid = self.visual_theme.currentData() == THEME_LIQUID
        self.low_resource.setEnabled(not liquid)
        if liquid:
            self.low_resource.setChecked(False)
        panel, desktop, _ = self.eduka_values()
        zone = self.selected_timezone() or DEFAULT_TIMEZONE
        self.preview.update_preview(panel, desktop, format_clock(zone, self.clock_format.currentData() is not False)
                                    .split(" · ")[-1][:5])

    def theme_changed(self):
        if self.visual_theme.currentData() != THEME_LIQUID:
            self.liquid_confirmed = False
            return
        if self.liquid_confirmed:
            return
        memory, threads, capable = liquid_glass_capability()
        detected = self.t("liquidDetected", memory=f"{memory:.1f}", threads=threads)
        if not capable:
            QMessageBox.warning(self, self.t("liquidTitle"), self.t("liquidRequirement") + "\n\n" + detected +
                                "\n\n" + self.t("liquidRefused"))
            self.visual_theme.setCurrentIndex(0)
            return
        answer = QMessageBox.question(self, self.t("liquidTitle"),
                                      self.t("liquidRequirement") + "\n\n" + detected,
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)
        if answer == QMessageBox.StandardButton.Yes:
            self.liquid_confirmed = True
        else:
            self.visual_theme.setCurrentIndex(0)

    def restore_eduka_defaults(self):
        self.visual_theme.blockSignals(True)
        self.visual_theme.setCurrentIndex(0)
        self.visual_theme.blockSignals(False)
        self.liquid_confirmed = False
        self.panel_transparency.setValue(round(DEFAULT_PANEL["transparency"] * 100))
        self.desktop_transparency.setValue(round(DEFAULT_DESKTOP["transparency"] * 100))
        self.shadows.setChecked(DEFAULT_DESKTOP["enable_shadows"])
        self.low_resource.setChecked(DEFAULT_DESKTOP["low_resource_mode"])
        self.menu_label.setText(DEFAULT_PANEL["menu_label"])
        self.menu_icon.setText(DEFAULT_PANEL["menu_icon"])
        self.show_text.setChecked(DEFAULT_PANEL["show_menu_text"])
        self.menu_icon_size.setValue(DEFAULT_PANEL["menu_icon_size"])
        self.panel_height.setValue(DEFAULT_PANEL["height"])
        self.panel_width.setValue(DEFAULT_PANEL["width_percent"])
        self.taskbar_style.setCurrentIndex(self.taskbar_style.findData(DEFAULT_PANEL["taskbar_style"]))
        self.desktop_layout.setCurrentIndex(self.desktop_layout.findData(DEFAULT_DESKTOP["layout"]))
        self.section.setCurrentIndex(self.section.findData(DEFAULT_DESKTOP["last_category"]))
        self.desktop_width.setValue(DEFAULT_DESKTOP["width_percent"])
        self.desktop_height.setValue(DEFAULT_DESKTOP["height_percent"])
        self.follow_language.setChecked(True)
        self.vision.setChecked(False)
        self.hearing.setChecked(False)
        self.orca.setChecked(False)
        self.message.setText(self.t("defaultsRestored"))

    # Page 5: Applications ---------------------------------------------------

    def apps_page(self):
        widget, layout = self.page("toolsForEveryday", "appsTitle", "appsLead")
        filters = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItem(self.t("allCategories"), "all")
        for key in ["educationGames", "internetMail", "officeDocuments", "audioVideo",
                    "graphicsDesign", "systemTools", "developmentTools", "accessibility"]:
            self.category_combo.addItem(self.t(key), key)
        self.category_combo.setAccessibleName(self.t("category"))
        self.source_combo = QComboBox()
        for name, key in [(self.t("aptSource"), "apt"), (self.t("flatpakSource"), "flatpak"),
                          (self.t("vendorRepository"), "brave")]:
            self.source_combo.addItem(name, key)
        self.source_combo.setAccessibleName(self.t("source"))
        self.category_combo.currentIndexChanged.connect(self.populate_apps)
        self.source_combo.currentIndexChanged.connect(self.populate_apps)
        filters.addWidget(self.category_combo, 1)
        filters.addWidget(self.source_combo, 1)
        self.refresh_button = button(self.t("refresh"), self.start_scan)
        filters.addWidget(self.refresh_button)
        layout.addLayout(filters)
        self.scan_status = label(self.t("scanProgress"), "note")
        layout.addWidget(self.scan_status)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["", self.t("application"), self.t("description")])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setWordWrap(True)
        self.table.setMinimumHeight(280)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.consent = QCheckBox()
        layout.addWidget(self.consent)
        actions = QHBoxLayout()
        self.install_button = button(self.t("installSelected"), self.request_install, True)
        actions.addWidget(self.install_button)
        actions.addWidget(button(self.t("viewCommands"), self.show_commands))
        actions.addWidget(button(self.t("exportInventory"), self.export_inventory))
        actions.addStretch()
        layout.addLayout(actions)
        layout.addWidget(label(self.t("catalogFreshness"), "note"))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(2000)
        self.log.setAccessibleName(self.t("log"))
        self.log.setMinimumHeight(140)
        self.log.setMaximumHeight(200)
        layout.addWidget(self.log)
        layout.addStretch()
        return widget

    # Page 6: Sponsors and support -------------------------------------------

    def sponsors_page(self):
        widget, layout = self.page("sponsorsEyebrow", "sponsorsTitle", "sponsorsLead")
        for field, key in (("sponsors", "sponsors"), ("partners", "partners")):
            layout.addWidget(label(self.t(key).upper(), "eyebrow"))
            entries = [entry for entry in (sponsor_entry(item) for item in self.project.get(field, [])) if entry]
            cards = [self.logo_card(entry) for entry in entries] or \
                [self.logo_card(None, field) for _ in range(3)]
            layout.addLayout(self.grid(cards, 3))
        layout.addWidget(label(self.t("supportEyebrow"), "eyebrow"))
        sponsor_button = button(self.t("becomeSponsorAction"), lambda: self.open_link("sponsor_contact"))
        sponsor_button.setEnabled(bool(self.project.get("sponsor_contact")))
        github_button = button(self.t("contributeAction"), lambda: self.open_link("github"))
        github_button.setEnabled(bool(self.project.get("github")))
        layout.addLayout(self.grid([
            self.card(self.t("supportProject"), self.t("donationBody") + " " + self.t("donationOptional"),
                      button(self.t("donatePayPal"), lambda: self.open_link("paypal"), True)),
            self.card(self.t("becomeSponsor"), self.t("becomeSponsorBody"), sponsor_button),
            self.card(self.t("contribute"), self.t("contributeBody"), github_button),
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
            hint = label(self.t("logoPlaceholderHint" if field == "sponsors" else "partnerPlaceholderHint"),
                         "note")
            hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(hint)
        return frame

    # Page 7: Community and finish -------------------------------------------

    def finish_page(self):
        widget, layout = self.page("journeyStarts", "finishTitle", "finishLead")
        links = QHBoxLayout()
        for field, text in [("website", self.t("officialWebsite")), ("facebook", "Facebook"),
                            ("whatsapp", self.t("whatsappChannel")), ("github", "GitHub")]:
            link_button = button(text, lambda checked=False, field=field: self.open_link(field))
            link_button.setEnabled(bool(self.project.get(field)))
            link_button.setToolTip(self.project.get(field, ""))
            links.addWidget(link_button)
        links.addStretch()
        layout.addLayout(links)
        layout.addWidget(label(self.t("ourGoals"), "eyebrow"))
        layout.addLayout(self.grid([self.card(self.t(key), self.t(key + "Body"))
                                    for key in ("goalEducation", "goalAccess", "goalSkills")], 3))
        layout.addWidget(self.card(self.t("developmentTeam"),
                                   "\n".join(self.project.get("developers", [])) or self.t("pendingCredits")))
        layout.addWidget(label(self.t("upstreamThanks"), "note"))
        layout.addStretch()
        return widget

    # Navigation -------------------------------------------------------------

    def navigate(self, page):
        if not hasattr(self, "stack") or not 0 <= page < len(PAGES):
            return
        self.stack.setCurrentIndex(page)
        self.steps.blockSignals(True)
        self.steps.setCurrentRow(page)
        self.steps.blockSignals(False)
        self.back_button.setEnabled(page > 0)
        last = page == len(PAGES) - 1
        self.always.setVisible(last)
        self.counter.setVisible(not last)
        self.next_button.setText(self.t("startDesktop" if self.session else "finish") if last
                                 else self.t("next"))
        self.counter.setText(self.t("stepCounter", current=page + 1, total=len(PAGES)))
        self.message.setText("")

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
        for app in self.apps:
            if source not in app["sources"] or (category != "all" and category != app["category"]):
                continue
            row = self.table.rowCount()
            self.table.insertRow(row)
            check = QTableWidgetItem()
            check.setData(Qt.ItemDataRole.UserRole, app["id"])
            check.setCheckState(Qt.CheckState.Unchecked)
            enabled = source != "apt" or self.availability.get(app["id"], False)
            check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable |
                           (Qt.ItemFlag.ItemIsEnabled if enabled else Qt.ItemFlag.NoItemFlags))
            self.table.setItem(row, 0, check)
            self.table.setItem(row, 1, QTableWidgetItem(app["name"]))
            description = self.t(app["description"])
            if not enabled:
                description += "\n" + self.t("noCandidate")
            self.table.setItem(row, 2, QTableWidgetItem(description))
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
        for widget in (self.refresh_button, self.category_combo, self.source_combo, self.install_button):
            widget.setEnabled(False)
        self.run_commands(commands, self.log, self.finish_install)

    def finish_install(self, success):
        self.message.setText(self.t("installComplete" if success else "installFailed"))
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
        color = QColorDialog.getColor(QColor(self.accent or "#00a887"), self, self.t("accentColor"))
        if color.isValid():
            self.accent = color.name()
            self.color_button.setText(self.accent)

    def choose_wallpaper(self):
        path, _ = QFileDialog.getOpenFileName(self, self.t("chooseFile"), str(Path.home()),
                                             "Images (*.png *.jpg *.jpeg *.webp *.bmp)")
        if path:
            self.wallpaper = path
            self.wallpaper_label.setText(path)
            self.wallpaper_preview.setPixmap(QPixmap(path).scaled(480, 140,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def apply_settings(self):
        if self.busy():
            self.message.setText(self.t("closeBusy"))
            return
        panel, desktop, menu = self.eduka_values()
        orca = desktop["orca_enabled"]
        values = {"eduka": (panel, desktop, menu),
                  "orca": orca if (orca or orca != self.initial_orca) else None,
                  "lxqt": {"icons": self.icon_combo.currentData(), "theme": self.theme_combo.currentData(),
                           "accent": self.accent, "wallpaper": self.wallpaper}}
        self.apply_button.setEnabled(False)
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
        if self.session:
            # Welcome Screen first, then the desktop: start Eduka-Desktop on the way out.
            start_desktop(self.project.get("eduka_desktop", {}))


def launch(language="en", preferences=None, session=False):
    application = QApplication([])
    application.setApplicationName("Edukasaun Welcome")
    application.setDesktopFileName("edukasaun-welcome")
    window = WelcomeWindow(language, preferences, session=session)
    if session:
        # No desktop is running yet, so take the whole screen.
        window.showMaximized()
    else:
        window.show()
    return application.exec()
