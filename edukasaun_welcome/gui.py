"""Native six-page Welcome Screen for Edukasaun OS; all system operations are asynchronous."""
import shlex
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
from PyQt6.QtCore import QDateTime, QProcess, QThread, QTimer, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFontDatabase, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDateTimeEdit, QDialog, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QMessageBox, QPushButton, QScrollArea, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget,
)
from .catalog import load_project, recommendations, install_commands
from .desktop import apply_desktop, open_tool, theme_choices
from .i18n import Translator
from .inventory import Inventory, apt_available, scan_inventory, write_inventory
from .preferences import load_preferences, save_preferences
from .session import start_desktop
from .timesettings import (
    DEFAULT_TIMEZONE, current_timezone, format_clock, time_commands, timezone_choices, utc_offset,
)

PAGES = ["stepWelcome", "stepTime", "stepSuite", "stepDesktop", "stepApps", "stepFinish"]

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
    completed = pyqtSignal(str)

    def __init__(self, values, parent):
        super().__init__(parent)
        self.values = values

    def run(self):
        try:
            apply_desktop(self.values)
            self.completed.emit("")
        except Exception as error:
            self.completed.emit(str(error))


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
                          self.apps_page, self.finish_page]:
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
        layout.addWidget(label(self.t("upstreamThanks"), "note"))
        layout.addStretch()
        return widget

    # Page 4: Personalize ----------------------------------------------------

    def desktop_page(self):
        widget, layout = self.page("makeItYours", "desktopTitle", "desktopLead")
        form = QFormLayout()
        form.setSpacing(12)
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
        self.apply_button = button(self.t("apply"), self.apply_settings, True)
        row = QHBoxLayout()
        row.addWidget(self.apply_button)
        row.addStretch()
        layout.addLayout(row)
        layout.addWidget(label(self.t("desktopWarning"), "note"))
        layout.addWidget(label(self.t("moreSettings"), "eyebrow"))
        tools = QHBoxLayout()
        tools.addWidget(button(self.t("openAppearance"), lambda: self.run_tool("appearance")))
        tools.addWidget(button(self.t("openDesktop"), lambda: self.run_tool("desktop")))
        tools.addWidget(button(self.t("openEffects"), lambda: self.run_tool("effects")))
        tools.addStretch()
        layout.addLayout(tools)
        layout.addWidget(label(self.t("effectsNote"), "note"))
        layout.addStretch()
        return widget

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

    # Page 6: Community and finish -------------------------------------------

    def finish_page(self):
        widget, layout = self.page("journeyStarts", "finishTitle", "finishLead")
        links = QHBoxLayout()
        for field, text in [("website", self.t("officialWebsite")), ("facebook", "Facebook"),
                            ("whatsapp", self.t("whatsappChannel")), ("github", "GitHub")]:
            link_button = button(text, lambda checked=False, field=field: self.open_link(field))
            link_button.setEnabled(bool(self.project.get(field)))
            if field == "github" and not self.project.get(field):
                link_button.setToolTip(self.t("githubPending"))
            links.addWidget(link_button)
        links.addStretch()
        layout.addLayout(links)
        layout.addWidget(label(self.t("ourGoals"), "eyebrow"))
        layout.addLayout(self.grid([self.card(self.t(key), self.t(key + "Body"))
                                    for key in ("goalEducation", "goalAccess", "goalSkills")], 3))
        credits = [self.card(self.t(key), "\n".join(self.project.get(field, [])) or self.t("pendingCredits"))
                   for field, key in [("developers", "developmentTeam"), ("sponsors", "sponsors"),
                                      ("partners", "partners")]]
        layout.addLayout(self.grid(credits, 3))
        layout.addWidget(self.card(self.t("supportProject"),
                                   self.t("donationBody") + " " + self.t("donationOptional"),
                                   button(self.t("donatePayPal"), lambda: self.open_link("paypal"))))
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
            self.wallpaper_preview.setPixmap(QPixmap(path).scaled(480, 180,
                Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def apply_settings(self):
        if self.busy():
            self.message.setText(self.t("closeBusy"))
            return
        self.apply_button.setEnabled(False)
        self.desktop_worker = DesktopWorker({"icons": self.icon_combo.currentData(),
            "theme": self.theme_combo.currentData(), "accent": self.accent,
            "wallpaper": self.wallpaper}, self)
        self.desktop_worker.completed.connect(self.desktop_finished)
        self.desktop_worker.finished.connect(self.desktop_thread_finished)
        self.desktop_worker.start()

    def desktop_finished(self, error):
        if error:
            self.error(error)
        else:
            self.message.setText(self.t("desktopApplied"))

    def desktop_thread_finished(self):
        self.desktop_worker.deleteLater()
        self.desktop_worker = None
        self.apply_button.setEnabled(True)

    # Misc -------------------------------------------------------------------

    def run_tool(self, key):
        if not open_tool(self.project.get("suite_tools", {}).get(key, [])):
            self.message.setText(self.t("notInstalledApp"))

    def open_link(self, key):
        url = self.project.get(key, "")
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
