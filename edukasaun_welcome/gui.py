"""Native six-page welcome wizard; all package operations are asynchronous."""
import json
import os
import shlex
import shutil
from pathlib import Path
from urllib.parse import urlparse
from PyQt6.QtCore import Qt, QThread, QTimer, QProcess, QUrl, pyqtSignal
from PyQt6.QtGui import QColor, QDesktopServices, QFontDatabase, QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QFileDialog,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QScrollArea, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QHeaderView,
)
from . import __version__
from .catalog import DATA, load_catalog, recommendations, install_commands
from .desktop import apply_desktop, open_tool, theme_choices
from .i18n import Translator
from .inventory import Inventory, apt_available, scan_inventory, write_inventory
from .preferences import load_preferences, save_preferences, config_home

STYLE = """
QWidget { font-family: sans-serif; font-size: 14px; color: #173d37; }
QWidget#shell { background: #f4faf7; }
QWidget#page { background: #f4faf7; }
QFrame#rail { background: #0b6355; border-radius: 18px; }
QFrame#rail QLabel { color: #ffffff; }
QLabel#brand { font-size: 22px; font-weight: 700; }
QLabel#title { font-size: 30px; font-weight: 700; color: #0b6355; }
QLabel#lead { color: #4d6963; font-size: 15px; }
QLabel#eyebrow { color: #008c70; font-weight: 700; font-size: 12px; }
QFrame#card { background: white; border: 1px solid #d7e7df; border-radius: 12px; }
QPushButton { background: #ffffff; border: 1px solid #b9d2c7; border-radius: 8px; padding: 10px 16px; }
QPushButton:hover { background: #e4f4ec; }
QPushButton#primary { background: #00856e; color: white; border: 1px solid #00856e; font-weight: 700; }
QPushButton#primary:hover { background: #006c59; }
QPushButton:disabled { color: #768983; background: #edf2ef; }
QComboBox, QLineEdit { border: 1px solid #bad2c7; border-radius: 6px; background: white; padding: 8px; }
QListWidget { background: transparent; border: 0; color: white; outline: 0; }
QListWidget::item { padding: 15px 8px; border-radius: 8px; }
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


class WelcomeWindow(QWidget):
    def __init__(self, language="system", preferences=None, auto_scan=True):
        super().__init__()
        self.preferences = preferences if preferences is not None else load_preferences()
        self.language = language
        self.t = Translator(language)
        self.project = json.loads((DATA / "project.json").read_text(encoding="utf-8"))
        overrides = config_home() / "edukasaun-welcome/project.json"
        if overrides.is_file():
            try:
                self.project.update(json.loads(overrides.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
        self.inventory = Inventory()
        self.apps = []
        self.availability = {}
        self.scanned = False
        self.worker = None
        self.desktop_worker = None
        self.process = None
        self.commands = []
        self.pending = None
        self.wallpaper = ""
        self.accent = ""
        self.setObjectName("shell")
        self.resize(1080, 760)
        self.setMinimumSize(820, 620)
        self.setWindowIcon(QIcon(str(Path(__file__).parent / "data/icon.svg")))
        self.setStyleSheet(STYLE)
        self.build()
        if auto_scan:
            QTimer.singleShot(100, self.start_scan)

    def build(self, page=0):
        self.setWindowTitle(self.t("nativeTitle"))
        outer = self.layout()
        if outer is None:
            outer = QHBoxLayout(self)
            outer.setContentsMargins(18, 18, 18, 18)
            outer.setSpacing(22)
        else:
            while outer.count():
                item = outer.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        rail = QFrame()
        rail.setObjectName("rail")
        rail.setFixedWidth(235)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(20, 26, 20, 22)
        rail_layout.addWidget(label("Edukasaun", "brand"))
        rail_layout.addWidget(label(self.t("firstSteps")))
        self.steps = QListWidget()
        for i, key in enumerate(["stepWelcome", "stepDiscover", "stepDesktop", "stepApps", "stepCommunity", "stepReady"]):
            self.steps.addItem(f"{i + 1:02d}   {self.t(key)}")
        self.steps.currentRowChanged.connect(self.navigate)
        rail_layout.addWidget(self.steps, 1)
        rail_layout.addWidget(label(self.t("educationFirst")))
        rail_layout.addWidget(label("Edukasaun Welcome  " + __version__))
        outer.addWidget(rail)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 4, 0, 0)
        toolbar = QHBoxLayout()
        toolbar.addWidget(label(self.t("nativeTitle")), 1)
        self.locale_combo = QComboBox()
        for name, key in [(self.t("followSystem"), "system"), ("English", "en"), ("Tetun", "tet"),
                          ("Português", "pt"), ("Bahasa Indonesia", "id")]:
            self.locale_combo.addItem(name, key)
        self.locale_combo.setCurrentIndex(max(0, self.locale_combo.findData(self.language)))
        self.locale_combo.setAccessibleName(self.t("language"))
        self.locale_combo.currentIndexChanged.connect(self.change_language)
        toolbar.addWidget(self.locale_combo)
        content_layout.addLayout(toolbar)
        self.stack = QStackedWidget()
        for make_page in [self.welcome_page, self.discover_page, self.desktop_page, self.apps_page,
                          self.community_page, self.ready_page]:
            body = make_page()
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(body)
            self.stack.addWidget(scroll)
        content_layout.addWidget(self.stack, 1)
        self.message = label("")
        content_layout.addWidget(self.message)
        footer = QHBoxLayout()
        self.back_button = button(self.t("back"), lambda: self.navigate(self.stack.currentIndex() - 1))
        footer.addWidget(self.back_button)
        self.counter = label("")
        footer.addWidget(self.counter, 1, Qt.AlignmentFlag.AlignCenter)
        self.next_button = button(self.t("next"), self.next_page, True)
        footer.addWidget(self.next_button)
        content_layout.addLayout(footer)
        outer.addWidget(content, 1)
        self.navigate(page)
        self.populate_apps()

    def page(self, eyebrow, title, lead):
        widget = QWidget()
        widget.setObjectName("page")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 26, 8, 10)
        layout.setSpacing(18)
        layout.addWidget(label(self.t(eyebrow), "eyebrow"))
        layout.addWidget(label(self.t(title), "title"))
        layout.addWidget(label(self.t(lead), "lead"))
        return widget, layout

    def card(self, title, body):
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        heading = label(title)
        heading.setStyleSheet("font-size: 17px; font-weight: 700")
        layout.addWidget(heading)
        layout.addWidget(label(body, "lead"))
        return frame

    def welcome_page(self):
        widget, layout = self.page("educationFirst", "welcomeTitle", "welcomeLead")
        greeting = label(self.t("mainGreeting"))
        greeting.setStyleSheet("font-size: 27px; font-weight: 700; padding: 22px; background: #dcf4e6; border-radius: 12px")
        layout.addWidget(greeting)
        systems = QFontDatabase.WritingSystem
        international = ["Welcome", "Bienvenue", "Bienvenido", "Willkommen", "Добро пожаловать",
            script_greeting("مرحبًا", "Marhaban", systems.Arabic),
            script_greeting("欢迎", "Huanying", systems.SimplifiedChinese),
            script_greeting("स्वागत है", "Swagat hai", systems.Devanagari)]
        layout.addWidget(self.card(self.t("international"), " · ".join(international)))
        layout.addWidget(self.card("CPLP · Português / Tetun", "Bem-vindo · Bem-vinda · Benvindu"))
        asean = ["Selamat datang", "Maligayang pagdating",
            script_greeting("ยินดีต้อนรับ", "Yindi tonrap", systems.Thai), "Chào mừng",
            script_greeting("សូមស្វាគមន៍", "Soum sva kum", systems.Khmer),
            script_greeting("ຍິນດີຕ້ອນຮັບ", "Nyin di ton hap", systems.Lao),
            script_greeting("ကြိုဆိုပါတယ်", "Kyo so par", systems.Myanmar), "Welcome", "Benvindu"]
        layout.addWidget(self.card(self.t("asean"), " · ".join(asean)))
        self.always = QCheckBox(self.t("alwaysShow"))
        self.always.setChecked(self.preferences.get("always_show", True))
        self.always.toggled.connect(self.update_always)
        layout.addWidget(self.always)
        layout.addStretch()
        return widget

    def discover_page(self):
        widget, layout = self.page("madeTogether", "discoverTitle", "discoverLead")
        try:
            release = Path("/etc/os-release").read_text()
            fields = dict(line.split("=", 1) for line in release.splitlines() if "=" in line and not line.startswith("#"))
            layout.addWidget(label(fields.get("PRETTY_NAME", "").strip('"')))
        except OSError:
            pass
        layout.addWidget(label(self.t("suiteTitle"), "eyebrow"))
        for name, key in [("Eduka-Desktop", "suiteDesktop"), ("Eduka-Menu", "suiteMenu"),
                          ("Eduka-Panel", "suitePanel"), ("Eduka-Menu-Settings", "suiteSettings")]:
            layout.addWidget(self.card(name, self.t(key)))
        layout.addWidget(self.card(self.t("projectTools"), self.t("relatedTools")))
        for field, key in [("developers", "developmentTeam"), ("sponsors", "sponsors"), ("partners", "partners")]:
            layout.addWidget(self.card(self.t(key), "\n".join(self.project.get(field, [])) or self.t("pendingCredits")))
        layout.addWidget(button(self.t("about"), self.show_about))
        layout.addWidget(label(self.t("upstreamThanks"), "lead"))
        layout.addStretch()
        return widget

    def desktop_page(self):
        widget, layout = self.page("makeItYours", "desktopTitle", "desktopLead")
        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.icon_combo = QComboBox()
        for combo, kind, key in [(self.theme_combo, "theme", "theme"), (self.icon_combo, "icons", "icons")]:
            combo.addItem(self.t("keepCurrentSettings"), "")
            for name in theme_choices(kind):
                combo.addItem(name, name)
            combo.setAccessibleName(self.t(key))
            form.addRow(self.t(key), combo)
        self.color_button = button(self.t("accentColor"), self.choose_color)
        form.addRow(self.t("accentColor"), self.color_button)
        file_row = QHBoxLayout()
        self.wallpaper_label = label(self.wallpaper or self.t("wallpaperEmpty"))
        file_row.addWidget(self.wallpaper_label, 1)
        file_row.addWidget(button(self.t("chooseFile"), self.choose_wallpaper))
        form.addRow(self.t("wallpaper"), file_row)
        layout.addLayout(form)
        self.wallpaper_preview = label("")
        self.wallpaper_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.wallpaper_preview)
        self.reduce_motion = QCheckBox(self.t("reducedMotion"))
        self.reduce_motion.setChecked(self.preferences.get("reduced_motion", True))
        self.reduce_motion.toggled.connect(self.update_motion)
        layout.addWidget(self.reduce_motion)
        layout.addWidget(label(self.t("reducedMotionNote"), "lead"))
        self.apply_button = button(self.t("apply"), self.apply_settings, True)
        layout.addWidget(self.apply_button)
        layout.addWidget(label(self.t("desktopWarning"), "lead"))
        layout.addWidget(button(self.t("openAppearance"), lambda: self.run_tool("appearance")))
        layout.addWidget(button(self.t("openDesktop"), lambda: self.run_tool("desktop")))
        layout.addWidget(button(self.t("openEffects"), lambda: self.run_tool("effects")))
        layout.addWidget(label(self.t("effectsNote"), "lead"))
        layout.addStretch()
        return widget

    def apps_page(self):
        widget, layout = self.page("toolsForEveryday", "appsTitle", "appsLead")
        filters = QHBoxLayout()
        self.category_combo = QComboBox()
        self.category_combo.addItem(self.t("allCategories"), "all")
        categories = ["educationGames", "internetMail", "officeDocuments", "audioVideo",
                      "graphicsDesign", "systemTools", "developmentTools", "accessibility"]
        for key in categories:
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
        self.scan_status = label(self.t("scanProgress"), "lead")
        layout.addWidget(self.scan_status)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["", self.t("stepApps"), self.t("about")])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setWordWrap(True)
        self.table.setMinimumHeight(285)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        self.consent = QCheckBox()
        layout.addWidget(self.consent)
        actions = QHBoxLayout()
        self.install_button = button(self.t("installSelected"), self.request_install, True)
        actions.addWidget(self.install_button)
        actions.addWidget(button(self.t("viewCommands"), self.show_commands))
        layout.addLayout(actions)
        layout.addWidget(label(self.t("catalogFreshness"), "lead"))
        layout.addWidget(button(self.t("exportInventory"), self.export_inventory))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(2000)
        self.log.setAccessibleName(self.t("log"))
        self.log.setMinimumHeight(150)
        self.log.setMaximumHeight(220)
        layout.addWidget(self.log)
        layout.addStretch()
        return widget

    def community_page(self):
        widget, layout = self.page("growTogether", "communityTitle", "communityLead")
        for field, key in [("website", "officialWebsite"), ("facebook", "Facebook"),
                           ("whatsapp", "whatsappChannel"), ("github", "GitHub")]:
            text = self.t(key) if key not in ("Facebook", "GitHub") else key
            link_button = button(text, lambda checked=False, field=field: self.open_link(field))
            link_button.setEnabled(bool(self.project.get(field)))
            layout.addWidget(link_button)
            if field == "github" and not self.project.get(field):
                layout.addWidget(label(self.t("githubPending"), "lead"))
        layout.addWidget(label(self.t("ourGoals"), "eyebrow"))
        for key in ("goalEducation", "goalAccess", "goalSkills"):
            layout.addWidget(self.card(self.t(key), self.t(key + "Body")))
        layout.addStretch()
        return widget

    def ready_page(self):
        widget, layout = self.page("journeyStarts", "thanksTitle", "thanksLead")
        layout.addWidget(self.card(self.t("supportProject"), self.t("donationBody")))
        layout.addWidget(label(self.t("donationOptional"), "lead"))
        layout.addWidget(button(self.t("donatePayPal"), lambda: self.open_link("paypal")))
        layout.addStretch()
        return widget

    def navigate(self, page):
        if not hasattr(self, "stack") or not 0 <= page < 6:
            return
        self.stack.setCurrentIndex(page)
        self.steps.blockSignals(True)
        self.steps.setCurrentRow(page)
        self.steps.blockSignals(False)
        self.back_button.setEnabled(page > 0)
        self.next_button.setText(self.t("close") if page == 5 else self.t("next"))
        self.counter.setText(f"{page + 1} / 6")
        self.message.setText("")

    def next_page(self):
        page = self.stack.currentIndex()
        self.close() if page == 5 else self.navigate(page + 1)

    def change_language(self):
        if self.busy():
            return
        language = self.locale_combo.currentData()
        if language == self.language:
            return
        self.language = language
        self.preferences["language"] = language
        self.persist()
        self.t = Translator(language)
        self.build(self.stack.currentIndex())

    def update_always(self, value):
        self.preferences["always_show"] = value
        self.persist()

    def update_motion(self, value):
        self.preferences["reduced_motion"] = value
        self.persist()

    def persist(self):
        try:
            save_preferences(self.preferences)
        except OSError as error:
            self.error(error)

    def busy(self):
        return bool(self.worker is not None or self.desktop_worker is not None or self.process is not None)

    def start_scan(self):
        if self.busy():
            return
        self.scan_status.setText(self.t("scanProgress"))
        self.install_button.setEnabled(False)
        self.refresh_button.setEnabled(False)
        self.locale_combo.setEnabled(False)
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
        self.locale_combo.setEnabled(True)
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
                raise RuntimeError("Install Edukasaun Welcome with scripts/install.sh before installing applications.")
            self.commands = install_commands(apps, source, self.install_consent, self.install_consent)
            self.log.clear()
            self.locale_combo.setEnabled(False)
            self.refresh_button.setEnabled(False)
            self.category_combo.setEnabled(False)
            self.source_combo.setEnabled(False)
            self.install_button.setEnabled(False)
            self.run_next_command()
        except (OSError, ValueError, RuntimeError) as error:
            self.error(error)

    def run_next_command(self):
        if not self.commands:
            self.finish_install(True)
            return
        arguments = self.commands.pop(0)
        self.log.append("$ " + shlex.join(arguments))
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.finished.connect(self.command_finished)
        self.process.errorOccurred.connect(self.command_error)
        self.process.start(arguments[0], arguments[1:])

    def read_output(self):
        if self.process:
            text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
            self.log.moveCursor(self.log.textCursor().MoveOperation.End)
            self.log.insertPlainText(text)
            self.log.ensureCursorVisible()

    def command_finished(self, code, status):
        if self.process is None:
            return
        self.read_output()
        self.process.deleteLater()
        self.process = None
        if code == 0 and status == QProcess.ExitStatus.NormalExit:
            self.run_next_command()
        else:
            self.finish_install(False)

    def command_error(self, error):
        if error == QProcess.ProcessError.FailedToStart and self.process:
            self.log.append(self.process.errorString())
            self.process.deleteLater()
            self.process = None
            self.finish_install(False)

    def finish_install(self, success):
        self.commands = []
        self.message.setText(self.t("installComplete" if success else "installFailed"))
        self.category_combo.setEnabled(True)
        self.source_combo.setEnabled(True)
        self.locale_combo.setEnabled(True)
        self.refresh_button.setEnabled(True)
        self.start_scan()

    def show_commands(self):
        try:
            commands = install_commands(self.selected_apps(), self.source_combo.currentData(),
                                        self.consent.isChecked(), self.consent.isChecked())
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
        except ValueError as error:
            self.error(error)

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
        self.locale_combo.setEnabled(False)
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
        self.locale_combo.setEnabled(True)

    def run_tool(self, key):
        if not open_tool(self.project.get("suite_tools", {}).get(key, [])):
            self.message.setText(self.t("notInstalledApp"))

    def open_link(self, key):
        url = self.project.get(key, "")
        parsed = urlparse(url)
        if parsed.scheme == "https" and parsed.netloc:
            QDesktopServices.openUrl(QUrl(url))

    def show_about(self):
        QMessageBox.about(self, self.t("about"), self.t("nativeTitle") + " " + __version__ +
                          "\n\n" + self.t("discoverLead") + "\n\nGPL-3.0-or-later · Python / Qt 6")

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
        else:
            event.accept()


def launch(language="system", preferences=None):
    application = QApplication([])
    application.setApplicationName("Edukasaun Welcome")
    application.setDesktopFileName("edukasaun-welcome")
    window = WelcomeWindow(language, preferences)
    window.show()
    return application.exec()
