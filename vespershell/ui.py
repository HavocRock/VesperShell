"""VesperShell v0.3.5 native UI — themes, TurtleHide, TurtleFlip and offline Help.

No network access, external graphics, downloaded fonts, or animations required.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import time

from PySide6.QtCore import (QDateTime, QEvent, QLockFile, QPoint, QRect, QRectF, QUrl,
                            Qt, QStandardPaths, QTime, QTimer)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import (
    QAction, QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QKeySequence, QLinearGradient,
    QPainter, QPen, QPixmap, QShortcut,
)
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDateTimeEdit, QDialog, QDialogButtonBox,
    QFormLayout, QFrame, QHBoxLayout, QLabel, QMenu, QMessageBox,
    QPlainTextEdit, QProgressBar, QSizeGrip, QSpinBox, QStackedWidget,
    QSystemTrayIcon, QTimeEdit, QToolButton, QVBoxLayout, QWidget,
)

from .model import (
    NotesDataError, NotesStore, SettingsStore, migrate_legacy_folder, backup_before_schedule_upgrade,
    backup_before_theme_upgrade, countdown_text, make_timer,
    make_daily_schedule, make_once_schedule, new_note, progress,
    remaining_seconds, schedule_phase, urgency_color,
)
from . import startup
from .helpfile import locate_help_file
from .themes import CLASSIC_THEMES, DEFAULT_THEME, SIGNATURE_THEMES, THEMES, get_theme


def turtle_icon() -> QIcon:
    """Use the included VesperShell icon in source and packaged builds.

    Fall back to the original, Qt-drawn turtle if the image is missing.
    """
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    artwork = root / "assets" / "vespershell_icon.png"
    if artwork.is_file():
        icon_from_file = QIcon(str(artwork))
        if not icon_from_file.isNull():
            return icon_from_file
    icon = QPixmap(64, 64)
    icon.fill(Qt.GlobalColor.transparent)
    painter = QPainter(icon)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#75B48A"))
    for x, y in ((13, 15), (40, 15), (13, 44), (40, 44)):
        painter.drawEllipse(x, y, 12, 11)
    painter.drawEllipse(46, 25, 15, 15)
    painter.setBrush(QColor("#306D57"))
    painter.drawEllipse(9, 13, 45, 39)
    painter.setBrush(QColor("#A6D5A7"))
    painter.drawEllipse(15, 18, 33, 29)
    painter.setPen(QPen(QColor("#448A67"), 2))
    painter.drawLine(32, 18, 32, 46)
    painter.drawLine(16, 32, 48, 32)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#183D30"))
    painter.drawEllipse(54, 29, 3, 3)
    painter.end()
    return QIcon(icon)


def open_offline_help(parent: QWidget | None = None) -> bool:
    """Open the local manual in the default browser, never a network URL."""
    manual = locate_help_file()
    if manual is None:
        QMessageBox.information(parent, "VesperShell Help not found",
            "The offline help file could not be found.\n\n"
            "Expected: docs\\VesperShell-Help.html beside VesperShell.exe "
            "(or in the project's docs folder when running from source).\n\n"
            "You can restore the docs folder from the release package.")
        return False
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(manual))):
        QMessageBox.warning(parent, "Could not open VesperShell Help",
            f"The help file exists but Windows could not open it:\n{manual}\n\n"
            "Try opening it directly in File Explorer with your browser.")
        return False
    return True


def preferred_editor_font() -> QFont:
    """Prefer an installed font that supports Devanagari/Indic shaping.

    Never bundle fonts or assume that replacing a font repairs corrupt text.
    """
    families = ["Nirmala UI", "Mangal", "Noto Sans Devanagari", "Segoe UI", "Arial"]
    installed = set(QFontDatabase.families())
    prioritized = [name for name in families if name in installed]
    face = prioritized[0] if prioritized else "Segoe UI"
    font = QFont(face, 11)
    if hasattr(font, "setFamilies"):
        font.setFamilies(prioritized or ["Segoe UI", "Arial"])
    return font


def accessible_geometry(data: dict) -> QRect:
    """Reposition an existing note after a monitor is removed or resized."""
    rect = QRect(data["x"], data["y"], data["width"], data["height"])
    screens = QApplication.screens()
    if not screens:
        return rect
    screen = next((s for s in screens if s.availableGeometry().intersects(rect)), screens[0])
    area = screen.availableGeometry()
    width = min(rect.width(), max(280, area.width()))
    height = min(rect.height(), max(180, area.height()))
    x = max(area.left(), min(rect.x(), area.right() - width + 1))
    y = max(area.top(), min(rect.y(), area.bottom() - height + 1))
    return QRect(x, y, width, height)


class DragBar(QFrame):
    """A drag handle, not a double/triple-click gesture target."""
    def __init__(self, window: "NoteWindow"):
        super().__init__(window)
        self.window = window
        self.point = None
        self._origin = None
        self._dragged = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, event):
        self.mousePressEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mousePressEvent(event)
        self.point = event.globalPosition().toPoint()
        self._origin = self.point
        self._dragged = False
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        event.accept()

    def mouseMoveEvent(self, event):
        if self.point is None or not event.buttons() & Qt.MouseButton.LeftButton:
            return super().mouseMoveEvent(event)
        position = event.globalPosition().toPoint()
        if (position - self._origin).manhattanLength() >= QApplication.startDragDistance():
            self._dragged = True
        if self._dragged:
            self.window.move(self.window.pos() + position - self.point)
            self.point = position
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or self.point is None:
            return super().mouseReleaseEvent(event)
        self.point = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        event.accept()


class CountdownDialog(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("TurtleTick · Quiet countdown")
        self.setMinimumWidth(315)
        self.setModal(True)
        layout = QVBoxLayout(self)
        label = QLabel("How long should TurtleTick count down?")
        label.setWordWrap(True)
        layout.addWidget(label)
        controls = QHBoxLayout()
        self.hours = QSpinBox()
        self.hours.setRange(0, 999)
        self.hours.setSuffix(" hours")
        self.minutes = QSpinBox()
        self.minutes.setRange(0, 59)
        self.minutes.setValue(25)
        self.minutes.setSuffix(" minutes")
        controls.addWidget(self.hours)
        controls.addWidget(self.minutes)
        layout.addLayout(controls)
        footer = QLabel("Silent by default. No notifications, flashing, or sounds.")
        footer.setWordWrap(True)
        footer.setStyleSheet("color: #596672;")
        layout.addWidget(footer)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Start countdown")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _validate(self):
        if not self.hours.value() and not self.minutes.value():
            QMessageBox.information(self, "Choose a duration", "Please select at least one minute.")
            return
        self.accept()


class ScheduleDialog(QDialog):
    """A compact schedule editor, using local wall clock time."""
    def __init__(self, parent: QWidget, existing: dict | None):
        super().__init__(parent)
        self.setWindowTitle("TurtleHide · Visibility schedule")
        self.setMinimumWidth(375)
        layout = QVBoxLayout(self)
        explain = QLabel("Hide this note automatically, then bring it back.\n"
                         "The application must be running for automatic changes.")
        explain.setWordWrap(True)
        layout.addWidget(explain)
        self.mode = QComboBox()
        self.mode.addItem("Once — specific dates and times", "once")
        self.mode.addItem("Every day — same hours", "daily")
        layout.addWidget(self.mode)
        self.pages = QStackedWidget()
        one_page = QWidget()
        form = QFormLayout(one_page)
        self.once_hide = QDateTimeEdit(QDateTime.currentDateTime().addSecs(600))
        self.once_show = QDateTimeEdit(QDateTime.currentDateTime().addSecs(4200))
        for field in (self.once_hide, self.once_show):
            field.setCalendarPopup(True)
            field.setDisplayFormat("dd MMM yyyy   hh:mm AP")
        form.addRow("Disappear:", self.once_hide)
        form.addRow("Reappear:", self.once_show)
        self.pages.addWidget(one_page)
        daily_page = QWidget()
        daily_form = QFormLayout(daily_page)
        self.daily_hide = QTimeEdit(QTime(18, 0))
        self.daily_show = QTimeEdit(QTime(20, 0))
        for field in (self.daily_hide, self.daily_show):
            field.setDisplayFormat("hh:mm AP")
        daily_form.addRow("Hide at:", self.daily_hide)
        daily_form.addRow("Show at:", self.daily_show)
        self.pages.addWidget(daily_page)
        self.mode.currentIndexChanged.connect(self.pages.setCurrentIndex)
        layout.addWidget(self.pages)
        if existing:
            if existing["mode"] == "once":
                self.once_hide.setDateTime(QDateTime.fromSecsSinceEpoch(int(existing["hide_at"])))
                self.once_show.setDateTime(QDateTime.fromSecsSinceEpoch(int(existing["show_at"])))
            else:
                self.mode.setCurrentIndex(1)
                h, m = divmod(existing["hide_minute"], 60)
                self.daily_hide.setTime(QTime(h, m))
                h, m = divmod(existing["show_minute"], 60)
                self.daily_show.setTime(QTime(h, m))
        note = QLabel("Quiet by default. Existing notes and countdowns are unaffected.\n"
                      "Manual Show now is allowed; the next schedule transition resumes control.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #657077;")
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Save schedule")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def chosen_schedule(self) -> dict:
        if self.mode.currentData() == "daily":
            hide = self.daily_hide.time().hour() * 60 + self.daily_hide.time().minute()
            show = self.daily_show.time().hour() * 60 + self.daily_show.time().minute()
            return make_daily_schedule(hide, show)
        return make_once_schedule(self.once_hide.dateTime().toSecsSinceEpoch(),
                                  self.once_show.dateTime().toSecsSinceEpoch())

    def _validate(self):
        try:
            schedule = self.chosen_schedule()
            if schedule["mode"] == "once" and schedule["show_at"] <= time.time():
                raise ValueError("Choose an end time in the future")
        except ValueError as exc:
            QMessageBox.information(self, "Check schedule", str(exc))
            return
        self.accept()


class NoteWindow(QWidget):
    def __init__(self, controller: "NotesController", data: dict):
        super().__init__(None)
        self.controller = controller
        self.data = data
        self.ready = False
        self._allow_close = False
        self._last_timer_style = None
        self.last_edit_monotonic = float("-inf")
        flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        if data["pinned"]:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("VesperShell · " + get_theme(data["color"]).name)
        self.setWindowIcon(controller.icon)
        self.setMinimumSize(290, 190)
        self.setGeometry(accessible_geometry(data["geometry"]))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 11)
        layout.setSpacing(6)

        header = DragBar(self)
        header.setObjectName("noteHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(2)
        self.title = QLabel("🐢 Notes")
        self.title.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        h.addWidget(self.title)
        h.addStretch(1)

        self.new_button = self.make_button("+", "New note (Ctrl+N)")
        self.new_button.clicked.connect(lambda _checked=False: controller.create_note())
        self.pin_button = self.make_button("⌃", "Always on top")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(data["pinned"])
        self.pin_button.setToolTip("Unpin note" if data["pinned"] else "Keep note above other windows")
        self.pin_button.clicked.connect(self.toggle_pin)
        self.palette_button = self.make_button("◉", "Change note theme")
        self.palette_button.clicked.connect(lambda _checked=False: self.open_themes())
        self.timer_button = self.make_button("◷", "Set quiet countdown")
        self.timer_button.clicked.connect(lambda _checked=False: self.set_timer())
        self.menu_button = self.make_button("⋯", "More options")
        self.menu_button.clicked.connect(lambda _checked=False: self.open_menu())
        self.close_button = self.make_button("×", "Hide note (not delete)")
        self.close_button.clicked.connect(lambda _checked=False: controller.hide_note(data["id"]))
        for b in (self.new_button, self.pin_button, self.palette_button, self.timer_button,
                  self.menu_button, self.close_button):
            h.addWidget(b)
        layout.addWidget(header)

        self.editor = QPlainTextEdit(self)
        self.editor.setObjectName("noteEditor")
        self.editor.setFrameShape(QFrame.Shape.NoFrame)
        self.editor.setPlaceholderText("A thought worth keeping…")
        self.editor.setFont(preferred_editor_font())
        self.editor.setPlainText(data["text"])
        self.editor.textChanged.connect(self.text_changed)
        layout.addWidget(self.editor, 1)

        self.timer_area = QWidget(self)
        self.timer_area.setObjectName("timerArea")
        timer_layout = QVBoxLayout(self.timer_area)
        timer_layout.setContentsMargins(3, 1, 3, 0)
        timer_layout.setSpacing(4)
        row = QHBoxLayout()
        self.timer_label = QLabel("Quiet countdown")
        self.timer_label.setObjectName("timerHint")
        self.timer_label.setFont(QFont("Segoe UI", 8))
        self.timer_value = QLabel("00:00:00")
        self.timer_value.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        row.addWidget(self.timer_label)
        row.addStretch()
        row.addWidget(self.timer_value)
        timer_layout.addLayout(row)
        self.timer_bar = QProgressBar(self)
        self.timer_bar.setRange(0, 1000)
        self.timer_bar.setTextVisible(False)
        self.timer_bar.setFixedHeight(6)
        timer_layout.addWidget(self.timer_bar)
        layout.addWidget(self.timer_area)

        footer = QHBoxLayout()
        footer.setContentsMargins(2, 0, 0, 0)
        self.status = QLabel("Saved locally")
        self.status.setToolTip("Notes stay on this device · No cloud")
        self.status.setFont(QFont("Segoe UI", 8))
        footer.addWidget(self.status)
        self.schedule_marker = QLabel("⏲")
        self.schedule_marker.setToolTip("Scheduled hide / reappear")
        self.schedule_marker.setFont(QFont("Segoe UI", 8))
        footer.addWidget(self.schedule_marker)
        self.schedule_marker.setVisible(data["schedule"] is not None)
        footer.addStretch()
        self.send_back_button = QToolButton(self)
        self.send_back_button.setObjectName("sendBackButton")
        self.send_back_button.setText("↓ Send back")
        self.send_back_button.setToolTip("Move behind other windows; restore from the tray")
        self.send_back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_back_button.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.send_back_button.setFixedHeight(23)
        self.send_back_button.clicked.connect(lambda _checked=False: self.send_to_back())
        footer.addWidget(self.send_back_button)
        self.grip = QSizeGrip(self)
        self.grip.setToolTip("Drag to resize")
        footer.addWidget(self.grip)
        layout.addLayout(footer)

        self.add_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.add_shortcut.activated.connect(controller.create_note)
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(controller.save_now)
        self.apply_theme()
        self.update_countdown(time.time())
        self.ready = True

    def make_button(self, glyph: str, description: str) -> QToolButton:
        b = QToolButton(self)
        b.setText(glyph)
        b.setToolTip(description)
        b.setFixedSize(27, 27)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFont(QFont("Segoe UI Symbol", 12))
        return b

    def paintEvent(self, event):
        theme = get_theme(self.data["color"])
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(1.1, 1.1, max(2, self.width() - 2.2), max(2, self.height() - 2.2))
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, QColor(theme.background))
        grad.setColorAt(1, QColor(theme.surface))
        p.setBrush(grad)
        p.setPen(QPen(QColor(theme.border), 1.15))
        p.drawRoundedRect(rect, theme.radius, theme.radius)
        # A faint internal halo only on the active note: static painting, not an
        # animation or a GPU-heavy shadow. It stays inside the window bounds.
        if self.isActiveWindow():
            p.setBrush(Qt.BrushStyle.NoBrush)
            for inset, alpha, thickness in ((2.5, 66, 2.3), (5.8, 30, 2.0)):
                glow = QColor(theme.accent)
                glow.setAlpha(alpha)
                p.setPen(QPen(glow, thickness))
                inner = rect.adjusted(inset, inset, -inset, -inset)
                r = max(2, theme.radius - inset)
                p.drawRoundedRect(inner, r, r)
        # Quiet, inexpensive decoration: a thematic accent and faint circles.
        accent = QColor(theme.accent)
        accent.setAlpha(195)
        p.setPen(QPen(accent, 2.6))
        p.drawLine(17, 3, min(94, self.width() - 18), 3)
        p.setPen(Qt.PenStyle.NoPen)
        ornament = QColor(theme.decoration)
        ornament.setAlpha(18)
        p.setBrush(ornament)
        for rad, dx, dy in ((34, 60, 55), (24, 30, 30), (12, 76, 16)):
            p.drawEllipse(self.width() - dx, self.height() - dy, rad, rad)
        p.end()
        super().paintEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange:
            self.update()  # Repaint halo when focus changes; no animation loop.

    def apply_theme(self):
        theme = get_theme(self.data["color"])
        self.setWindowTitle("VesperShell · " + theme.name)
        self.setToolTip(theme.name)
        self.setStyleSheet(f"""
          QFrame#noteHeader {{ background: transparent; border: 0; }}
          QWidget#timerArea {{ background: transparent; border: 0; }}
          QPlainTextEdit#noteEditor {{ background: transparent; border: 0;
              color: {theme.text}; selection-background-color: {theme.hover};
              selection-color: {theme.text}; }}
          QLabel {{ background: transparent; border: 0; color: {theme.text}; }}
          QToolButton {{ background: transparent; border: 0; border-radius: 7px;
              color: {theme.text}; }}
          QToolButton:hover {{ background: {theme.hover}; }}
          QToolButton:checked {{ background: {theme.border}; color: {theme.text}; }}
          QToolButton#sendBackButton {{ border: 1px solid {theme.border};
              border-radius: 6px; padding: 1px 5px; }}
          QToolButton#sendBackButton:hover {{ background: {theme.hover}; }}
        """)
        self.status.setStyleSheet(f"color: {theme.muted};")
        self.timer_label.setStyleSheet(f"color: {theme.muted};")
        self.schedule_marker.setStyleSheet(f"color: {theme.accent};")
        self._last_timer_style = None
        self.update_countdown(time.time())
        self.update()

    def text_changed(self):
        self.data["text"] = self.editor.toPlainText()
        self.last_edit_monotonic = time.monotonic()
        self.controller.schedule_save()

    def _remember_geometry(self):
        if not self.ready:
            return
        g = self.geometry()
        self.data["geometry"] = {"x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()}
        self.controller.schedule_save()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._remember_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._remember_geometry()

    def _style_menu(self, menu: QMenu):
        theme = get_theme(self.data["color"])
        menu.setStyleSheet(f"""
          QMenu {{ background: {theme.background}; color: {theme.text};
                  border: 1px solid {theme.border}; padding: 6px; }}
          QMenu::item {{ padding: 6px 20px 6px 24px; border-radius: 4px; }}
          QMenu::item:selected {{ background: {theme.hover}; }}
        """)

    def _theme_actions(self, menu: QMenu, themes: dict):
        for theme_id, theme in themes.items():
            act = QAction(theme.name, menu)
            swatch = QPixmap(14, 14)
            swatch.fill(QColor(theme.accent))
            act.setIcon(QIcon(swatch))
            act.setCheckable(True)
            act.setChecked(self.data["color"] == theme_id)
            act.triggered.connect(lambda _checked=False, name=theme_id: self.set_theme(name))
            menu.addAction(act)

    def open_themes(self):
        menu = QMenu(self)
        self._style_menu(menu)
        menu.addSection("Mood themes")
        self._theme_actions(menu, SIGNATURE_THEMES)
        menu.addSeparator()
        classics = menu.addMenu("Classic colors")
        self._style_menu(classics)
        self._theme_actions(classics, CLASSIC_THEMES)
        menu.exec(self.palette_button.mapToGlobal(QPoint(0, self.palette_button.height())))

    def set_theme(self, theme_id: str):
        if theme_id not in THEMES:
            return
        self.data["color"] = theme_id
        self.apply_theme()
        self.controller.schedule_save()
        self.controller.refresh_tray_menu()

    def set_pin_state(self, pinned: bool, *, send_behind: bool = False):
        geometry = self.geometry()
        self.data["pinned"] = pinned
        self.pin_button.blockSignals(True)
        self.pin_button.setChecked(pinned)
        self.pin_button.blockSignals(False)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, pinned)
        self.setGeometry(geometry)
        self.pin_button.setToolTip("Unpin note" if pinned else "Keep note above other windows")
        self.show()  # Window flags recreate native window; apply placement again.
        if send_behind:
            self.lower()
        else:
            self.raise_()
            self.activateWindow()
        self.controller.schedule_save()

    def toggle_pin(self, pinned: bool):
        self.set_pin_state(pinned)

    def send_to_back(self):
        """Lower this note rather than hiding it."""
        self.set_pin_state(False, send_behind=True)

    def set_schedule(self):
        if not self.controller.tray_available():
            QMessageBox.information(self, "System tray needed",
                "Automatic hiding requires a working system tray so hidden notes stay accessible.")
            return
        dlg = ScheduleDialog(self, self.data["schedule"])
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.data["schedule"] = dlg.chosen_schedule()
            self.schedule_marker.show()
            self.controller.schedule_save()
            self.controller.process_schedules(time.time())

    def clear_schedule(self):
        self.data["schedule"] = None
        self.schedule_marker.hide()
        self.controller.schedule_save()


    def set_timer(self):
        dlg = CountdownDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.data["timer"] = make_timer(dlg.minutes.value(), dlg.hours.value())
            self.update_countdown(time.time())
            self.controller.schedule_save()

    def clear_timer(self):
        self.data["timer"] = None
        self.update_countdown(time.time())
        self.controller.schedule_save()

    def update_countdown(self, now: float):
        timer = self.data["timer"]
        self.timer_area.setVisible(timer is not None)
        if timer is None:
            return
        seconds = remaining_seconds(timer, now=now)
        fraction = progress(timer, now=now)
        color = urgency_color(fraction)
        self.timer_value.setText(countdown_text(seconds) if seconds else "Time's up")
        self.timer_value.setStyleSheet(f"color: {color};")
        self.timer_label.setText("Quiet countdown" if seconds else "Deadline reached")
        self.timer_bar.setValue(round(fraction * 1000))
        key = (color, seconds == 0, self.data["color"])
        if self._last_timer_style != key:
            self._last_timer_style = key
            bg = color if seconds == 0 else get_theme(self.data["color"]).border
            self.timer_bar.setStyleSheet(
                f"QProgressBar {{ background: {bg}; border: 0; border-radius: 3px; }}"
                f"QProgressBar::chunk {{ background: {color}; border: 0; border-radius: 3px; }}")

    def open_menu(self):
        menu = QMenu(self)
        self._style_menu(menu)
        menu.addAction("New note", lambda _checked=False: self.controller.create_note())
        menu.addAction("Show all notes", lambda _checked=False: self.controller.show_all())
        menu.addAction("↓ Send this note back", lambda _checked=False: self.send_to_back())
        menu.addSeparator()
        menu.addAction("Set countdown", lambda _checked=False: self.set_timer())
        clear = menu.addAction("Clear countdown", lambda _checked=False: self.clear_timer())
        clear.setEnabled(self.data["timer"] is not None)
        menu.addSeparator()
        menu.addAction("Schedule hide / reappear…", lambda _checked=False: self.set_schedule())
        cancel_schedule = menu.addAction("Remove visibility schedule", lambda _checked=False: self.clear_schedule())
        cancel_schedule.setEnabled(self.data["schedule"] is not None)
        menu.addSeparator()
        menu.addAction("Save now    Ctrl+S", lambda _checked=False: self.controller.save_now())
        menu.addAction("Delete this note…", lambda _checked=False: self.confirm_delete())
        menu.addAction("Hide this note", lambda _checked=False: self.controller.hide_note(self.data["id"]))
        menu.addSeparator()
        menu.addAction("Help · Offline guide", lambda _checked=False: open_offline_help(self))
        menu.addSeparator()
        menu.addAction("Quit VesperShell", lambda _checked=False: self.controller.quit_application())
        menu.exec(self.menu_button.mapToGlobal(QPoint(0, self.menu_button.height())))

    def confirm_delete(self):
        result = QMessageBox.question(
            self, "Delete note?", "Delete this note and its countdown permanently?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self.controller.delete_note(self.data["id"])

    def closeEvent(self, event):
        if self._allow_close:
            event.accept()
        else:
            event.ignore()
            self.controller.hide_note(self.data["id"])


class NotesController:
    def __init__(self, app: QApplication, store: NotesStore, settings: SettingsStore,
                 *, qa_mode: bool = False, startup_data_dir: Path | None = None):
        self.app, self.store, self.settings = app, store, settings
        self.qa_mode = qa_mode
        self.startup_data_dir = startup_data_dir
        self.icon = turtle_icon()
        app.setWindowIcon(self.icon)
        preferences = settings.load_preferences()
        self.default_theme = preferences["default_theme"]
        self.stack_clicks = preferences["stack_clicks"]
        self.notes: dict[str, dict] = {n["id"]: n for n in store.load()}
        self.windows: dict[str, NoteWindow] = {}
        self.failed_save_message_shown = False
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(450)
        self.save_timer.timeout.connect(self.save_now)
        self.clock_timer = QTimer()
        self.clock_timer.setInterval(1000)
        self.clock_timer.timeout.connect(self.update_clocks)
        self.tray = None
        self.tray_menu = None
        self._tray_refresh_pending = False
        self._quitting = False
        self.setup_tray()
        for note in self.notes.values():
            win = NoteWindow(self, note)
            self.windows[note["id"]] = win
            if note["visible"]:
                win.show()
        if not self.notes:
            self.create_note()
        elif not self.tray_available() and not any(n["visible"] for n in self.notes.values()):
            self.show_all()  # Avoid leaving user without a way to reopen hidden notes.
        self.process_schedules(time.time())
        self.update_clocks()
        self.clock_timer.start()
        self.refresh_tray_menu()

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self.app)
        self.tray.setToolTip("VesperShell · Vesper keeps notes on this device")
        self.tray_menu = QMenu()
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self._tray_activation)
        self.tray.show()

    def tray_available(self):
        return self.tray is not None and QSystemTrayIcon.isSystemTrayAvailable()

    def recover_controls(self):
        if self._quitting:
            return
        if self.tray_available():
            self.tray.hide()
            self.tray.show()
        # Keep intentionally hidden notes private. The tray menu offers Show all.
        visible = [w for w in self.windows.values() if w.data["visible"]]
        if visible:
            win = visible[0]
            if not win.isVisible():
                win.show()
            win.raise_()
            win.activateWindow()

    def _tray_activation(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_all()

    def refresh_tray_menu(self):
        # Defer rebuilding until actions have finished triggering. Clearing a
        # currently open native tray menu synchronously can invalidate actions.
        if self.tray_menu is None or self._tray_refresh_pending:
            return
        self._tray_refresh_pending = True
        QTimer.singleShot(0, self._build_tray_menu)

    def _build_tray_menu(self):
        self._tray_refresh_pending = False
        if self.tray_menu is None:
            return
        m = self.tray_menu
        m.clear()
        m.addAction("New note", lambda _checked=False: self.create_note())
        menu_new = m.addMenu("New note in theme")
        for theme_id, theme in SIGNATURE_THEMES.items():
            menu_new.addAction(theme.name, lambda _checked=False, tid=theme_id: self.create_note(theme=tid))
        m.addAction("Show all notes", lambda _checked=False: self.show_all())
        m.addSeparator()
        menu_default = m.addMenu("Default theme for new notes")
        for theme_id, theme in SIGNATURE_THEMES.items():
            act = menu_default.addAction(theme.name, lambda _checked=False, tid=theme_id: self.change_default_theme(tid))
            act.setCheckable(True)
            act.setChecked(self.default_theme == theme_id)
        if self.default_theme in CLASSIC_THEMES:
            menu_default.addAction("Keep classic: " + get_theme(self.default_theme).name).setEnabled(False)
        if startup.windows_supported():
            m.addSeparator()
            start_action = m.addAction("Start VesperShell with Windows")
            start_action.setCheckable(True)
            if self.qa_mode:
                start_action.setEnabled(False)
                start_action.setToolTip("Disabled in QA mode; tests cannot change Windows startup")
            else:
                try:
                    entry = startup.registered_command()
                    target = startup.startup_command(self.startup_data_dir)
                    start_action.setChecked(startup.is_enabled_for_this_install(self.startup_data_dir) or entry is not None)
                    if entry is not None and entry != target:
                        start_action.setToolTip("Older startup path found. Uncheck, then recheck to update it.")
                    else:
                        start_action.setToolTip("Optional: launch VesperShell when you sign in to Windows")
                    start_action.toggled.connect(self.set_windows_startup)
                except OSError:
                    start_action.setEnabled(False)
                    start_action.setToolTip("Could not read Windows startup settings")
        if self.notes:
            m.addSeparator()
            m.addSection("Bring forward and pin note")
            for note in list(self.notes.values())[:20]:
                first = next((line.strip() for line in note["text"].splitlines() if line.strip()), "Untitled")
                title = (first[:27] + "…" if len(first) > 28 else first)
                m.addAction(title + " · " + get_theme(note["color"]).name,
                            lambda _checked=False, nid=note["id"]: self.bring_front_and_pin(nid))
        m.addSeparator()
        m.addAction("Help · Offline guide", lambda _checked=False: open_offline_help())
        m.addSeparator()
        m.addAction("Quit VesperShell", lambda _checked=False: self.quit_application())

    def set_windows_startup(self, enabled: bool):
        """Handle deliberate opt-in/out; never touch registry from QA mode."""
        if self.qa_mode:
            return
        try:
            startup.set_enabled(enabled, self.startup_data_dir)
        except OSError as exc:
            QMessageBox.warning(None, "Windows startup update needs attention",
                                f"Could not update Start with Windows.\n\n{exc}")
        self.refresh_tray_menu()

    def bring_front_and_pin(self, note_id: str):
        self.show_note(note_id)
        win = self.windows.get(note_id)
        if win is not None:
            win.set_pin_state(True)

    def change_default_theme(self, theme: str):
        try:
            self.settings.save(theme)
        except NotesDataError as exc:
            QMessageBox.critical(None, "Cannot save theme preference", str(exc))
            return
        self.default_theme = theme
        self.refresh_tray_menu()

    def _new_position(self) -> tuple[int, int]:
        screen = self.app.primaryScreen()
        if screen is None:
            return (150, 150)
        area = screen.availableGeometry()
        offset = (len(self.notes) % 7) * 24
        return (area.left() + max(0, (area.width() - 350) // 2) + offset,
                area.top() + max(0, (area.height() - 288) // 2) + offset)

    def create_note(self, *, theme: str | None = None):
        x, y = self._new_position()
        note = new_note(x, y, theme=theme or self.default_theme)
        self.notes[note["id"]] = note
        win = NoteWindow(self, note)
        self.windows[note["id"]] = win
        win.show()
        win.raise_()
        win.editor.setFocus()
        self.schedule_save()
        self.refresh_tray_menu()

    def show_note(self, note_id: str):
        win = self.windows.get(note_id)
        if win is None:
            return
        self.notes[note_id]["visible"] = True
        win.show()
        win.update_countdown(time.time())
        win.raise_()
        win.activateWindow()
        self.schedule_save()

    def show_all(self):
        for note_id in list(self.windows):
            self.show_note(note_id)

    def hide_note(self, note_id: str):
        if note_id not in self.notes:
            return
        if not self.tray_available() and sum(n["visible"] for n in self.notes.values()) <= 1:
            QMessageBox.information(self.windows[note_id], "Keep one note open",
                                    "The system tray is unavailable. Keep one note open so you can restore the others.")
            return
        self.notes[note_id]["visible"] = False
        self.windows[note_id].hide()
        self.schedule_save()

    def delete_note(self, note_id: str):
        win = self.windows.pop(note_id, None)
        self.notes.pop(note_id, None)
        if win is not None:
            win._allow_close = True
            win.close()
            win.deleteLater()
        if not self.notes:
            self.create_note()
        elif not self.tray_available() and not any(n["visible"] for n in self.notes.values()):
            self.show_all()
        self.schedule_save()
        self.refresh_tray_menu()

    def _status(self, message: str):
        for win in self.windows.values():
            win.status.setText(message)

    def schedule_save(self):
        self._status("Saving locally…")
        self.save_timer.start()

    def save_now(self) -> bool:
        self.save_timer.stop()
        for nid, win in self.windows.items():
            if win.isVisible():
                g = win.geometry()
                self.notes[nid]["geometry"] = {
                    "x": g.x(), "y": g.y(), "width": g.width(), "height": g.height()}
        try:
            self.store.save(list(self.notes.values()))
            self.failed_save_message_shown = False
            self._status("Saved locally · No cloud")
            self.refresh_tray_menu()
            return True
        except NotesDataError as exc:
            self._status("NOT SAVED — check storage")
            if not self.failed_save_message_shown:
                self.failed_save_message_shown = True
                QMessageBox.critical(None, "Cannot save notes", "Your recent changes are not saved.\n\n" + str(exc))
            return False

    def process_schedules(self, now: float):
        """Apply due transitions; preserve manual changes until the next phase change.

        We do not mark a hide transition applied until the editor is idle, so
        it cannot suddenly vanish in the middle of typing.
        """
        for note_id, note in list(self.notes.items()):
            schedule = note.get("schedule")
            if schedule is None:
                continue
            wanted = schedule_phase(schedule, now=now)
            if wanted == schedule["phase"]:
                continue
            win = self.windows[note_id]
            if wanted == "hidden":
                if win.isVisible() and time.monotonic() - win.last_edit_monotonic < 4.0:
                    continue
                if not self.tray_available() and sum(n["visible"] for n in self.notes.values()) <= 1:
                    continue  # Never strand the final visible note.
                note["visible"] = False
                win.hide()
            elif wanted == "shown":
                note["visible"] = True
                win.show()
                win.raise_()
                win.update_countdown(now)
            # "before" does not force manually hidden notes to show.
            schedule["phase"] = wanted
            self.schedule_save()

    def update_clocks(self):
        now = time.time()
        self.process_schedules(now)
        for win in self.windows.values():
            if win.isVisible():
                win.update_countdown(now)

    def quit_application(self):
        if self._quitting:
            return
        if not self.save_now():
            choice = QMessageBox.question(
                None, "Unsaved notes", "Saving failed. Quit anyway and risk losing changes?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if choice != QMessageBox.StandardButton.Yes:
                return
        if self.tray:
            self.tray.hide()
        self._quitting = True
        self.clock_timer.stop()
        self.save_timer.stop()
        for win in self.windows.values():
            win._allow_close = True
            win.close()
        self.app.quit()


def recovery_server_name(folder: Path) -> str:
    # One endpoint per canonical data directory; no note contents cross IPC.
    import os
    key = os.path.normcase(str(folder.resolve())).encode("utf-8")
    return "vespershell-" + hashlib.sha256(key).hexdigest()[:32]


def request_recovery(name: str) -> bool:
    socket = QLocalSocket()
    socket.connectToServer(name)
    if not socket.waitForConnected(500):
        return False
    socket.write(b"recover\n")
    acknowledged = socket.waitForReadyRead(1500) and bytes(socket.readLine()) == b"ok\n"
    socket.disconnectFromServer()
    return acknowledged


def start_recovery_server(name: str, controller):
    # Caller already owns the data lock: removing a stale endpoint is safe.
    QLocalServer.removeServer(name)
    server = QLocalServer(controller.app)
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    def accept():
        while server.hasPendingConnections():
            socket = server.nextPendingConnection()
            def receive(socket=socket):
                if socket.canReadLine():
                    if bytes(socket.readLine(32)) == b"recover\n":
                        controller.recover_controls()
                        socket.write(b"ok\n")
                    socket.disconnectFromServer()
            socket.readyRead.connect(receive)
            socket.disconnected.connect(socket.deleteLater)
            receive()
    server.newConnection.connect(accept)
    if not server.listen(name):
        raise OSError("Cannot open local recovery controls: " + server.errorString())
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VesperShell — quiet private desktop notes")
    parser.add_argument("--data-dir", type=Path, help="Save notes to this user-selected folder")
    parser.add_argument("--qa-mode", action="store_true", help="Do not allow Windows startup changes")
    opts = parser.parse_args(argv)
    if opts.qa_mode and not opts.data_dir:
        parser.error("--qa-mode requires --data-dir for isolated test notes")
    app = QApplication(sys.argv[:1])
    app.setOrganizationName("TurtleWorks")

    # Ask Qt for the ORIGINAL application data path before changing the public
    # application name. This avoids guessing Windows AppData path conventions.
    app.setApplicationName("TurtleNotes")
    legacy_folder = Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation))
    app.setApplicationName("VesperShell")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    default_folder = Path(QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppLocalDataLocation))
    folder = opts.data_dir.expanduser().resolve() if opts.data_dir else default_folder

    endpoint = recovery_server_name(folder)
    if request_recovery(endpoint):
        return 0

    # A legacy lock is held throughout the VesperShell session, preventing a
    # concurrent old executable from editing divergent copies during migration.
    old_lock = None
    migration_lock = None
    new_lock = None
    try:
        if opts.data_dir is None:
            if legacy_folder.is_dir():
                old_lock = QLockFile(str(legacy_folder / "turtlenotes.lock"))
                if not old_lock.tryLock(150):
                    QMessageBox.warning(None, "Close the old app first",
                        "An older TurtleNotes copy is using its data folder.\n"
                        "Close it before starting VesperShell to protect your notes.")
                    return 2
            folder.parent.mkdir(parents=True, exist_ok=True)
            migration_lock = QLockFile(str(folder.parent / "vespershell-migration.lock"))
            if not migration_lock.tryLock(2000):
                QMessageBox.warning(None, "VesperShell startup in progress",
                    "Another VesperShell instance may be preparing the data folder.\n"
                    "Please close other copies and try again.")
                return 2
            migrate_legacy_folder(legacy_folder, folder)
        folder.mkdir(parents=True, exist_ok=True)
        new_lock = QLockFile(str(folder / "vespershell.lock"))
        if not new_lock.tryLock(150):
            QMessageBox.information(None, "VesperShell already running",
                "A VesperShell instance may already use this data folder.\n"
                "Check the Windows system tray. To protect your notes, this copy won't start.")
            return 2
        # Release migration-specific lock after the new data directory is
        # created and locked. Keep the legacy lock for the whole session.
        if migration_lock:
            migration_lock.unlock()
            migration_lock = None
        try:
            backup_before_theme_upgrade(folder)
            backup_before_schedule_upgrade(folder)
            controller = NotesController(app, NotesStore(folder / "notes.json"),
                                         SettingsStore(folder / "settings.json"),
                                         qa_mode=opts.qa_mode,
                                         startup_data_dir=folder if opts.data_dir else None)
        except NotesDataError as exc:
            QMessageBox.critical(None, "Notes were not modified",
                f"VesperShell could not safely read its data.\n\n{exc}\n\n"
                "Back up the data file before attempting any repair.")
            return 1
        app._vespershell_controller = controller
        server = start_recovery_server(endpoint, controller)
        app.aboutToQuit.connect(server.close)
        app.aboutToQuit.connect(lambda: None if controller._quitting else controller.save_now())
        return app.exec()
    except (OSError, NotesDataError) as exc:
        QMessageBox.critical(None, "VesperShell could not start",
            f"Your existing notes were not deleted.\n\n{exc}\n\n"
            "Check your data directory and permissions.")
        return 1
    finally:
        if new_lock:
            new_lock.unlock()
        if migration_lock:
            migration_lock.unlock()
        if old_lock:
            old_lock.unlock()
