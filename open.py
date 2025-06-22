import sys
import os
import json
import glob
import webbrowser
from datetime import datetime
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QListView, QAbstractItemView, QLineEdit, QLabel, QComboBox,
    QSpinBox, QSlider, QCheckBox, QDialog, QMenu, QAction, QColorDialog,
    QTabWidget, QCompleter, QSystemTrayIcon, QToolButton, QStyledItemDelegate,
    QProgressBar
)
from PyQt5.QtCore import (
    Qt, QSize, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer,
    QStringListModel, QPoint, QRectF, QSortFilterProxyModel
)
from PyQt5.QtGui import (
    QIcon, QPixmap, QFont, QFontDatabase, QPainter, QBrush, QColor,
    QStandardItem, QStandardItemModel, QPen, QLinearGradient
)
try:
    from win32com.shell import shell, shellcon
    import pythoncom
    import win32gui
    import win32con
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
from PIL import Image
import subprocess
import logging
import keyboard
from fuzzywuzzy import fuzz, process
import hashlib

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler('quantum_launcher.log'),
    logging.StreamHandler()
])

class AppItem(QStandardItem):
    """Custom item for apps/links/recent/pinned with icon and metadata."""
    def __init__(self, name, path, category, item_type, icon=None, font=None, is_favorite=False):
        super().__init__(name)
        self.setData({"name": name, "path": path, "category": category, "type": item_type, "is_favorite": is_favorite}, Qt.UserRole)
        self.setIcon(icon or QIcon())
        self.setFont(font or QFont("Inter", 12))
        self.setEditable(False)

class CustomItemDelegate(QStyledItemDelegate):
    """Custom delegate for rendering list/grid/compact items with modern effects."""
    def __init__(self, view_mode="list", icon_size=32, border_radius=8, parent=None):
        super().__init__(parent)
        self.view_mode = view_mode
        self.icon_size = icon_size
        self.border_radius = border_radius

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        rect = option.rect
        data = index.data(Qt.UserRole)
        if not data:
            painter.restore()
            return super().paint(painter, option, index)

        # Card-like background with hover/selection effects
        if option.state & option.widget.style().State_Selected:
            painter.setBrush(QBrush(QColor(30, 144, 255)))
            painter.setPen(QPen(QColor(100, 149, 237), 1))
        elif option.state & option.widget.style().State_MouseOver:
            painter.setBrush(QBrush(QColor(50, 50, 50)))
            painter.setPen(QPen(QColor(100, 100, 100), 1))
        else:
            painter.setBrush(QBrush(QColor(30, 30, 30)))
            painter.setPen(Qt.NoPen)

        if self.view_mode == "grid":
            painter.drawRoundedRect(rect.adjusted(6, 6, -6, -6), self.border_radius, self.border_radius)
            icon = index.data(Qt.DecorationRole)
            if icon:
                painter.drawPixmap(rect.left() + (rect.width() - self.icon_size) // 2, rect.top() + 10, icon.pixmap(QSize(self.icon_size, self.icon_size)))
            painter.setPen(QColor(220, 220, 220))
            painter.setFont(QFont("Inter", 11, QFont.Bold))
            painter.drawText(rect.adjusted(8, self.icon_size + 20, -8, -8), Qt.AlignTop | Qt.AlignHCenter | Qt.TextWordWrap, data["name"])
            if data["is_favorite"]:
                painter.setPen(QColor(255, 215, 0))
                painter.drawText(rect.adjusted(8, 10, -8, -8), Qt.AlignTop | Qt.AlignLeft, "★")
            if data["type"] != "app":
                badge_rect = QRect(rect.right() - 34, rect.top() + 10, 24, 16)
                painter.setBrush(QBrush(QColor(30, 144, 255)))
                painter.drawRoundedRect(badge_rect, 6, 6)
                painter.setPen(QColor(255, 255, 255))
                painter.setFont(QFont("Inter", 8))
                painter.drawText(badge_rect, Qt.AlignCenter, data["type"].upper())
        elif self.view_mode == "list":
            painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), self.border_radius, self.border_radius)
            icon = index.data(Qt.DecorationRole)
            if icon:
                painter.drawPixmap(rect.left() + 10, rect.top() + (rect.height() - self.icon_size) // 2, icon.pixmap(QSize(self.icon_size, self.icon_size)))
            painter.setPen(QColor(220, 220, 220))
            painter.setFont(QFont("Inter", 12))
            painter.drawText(rect.adjusted(self.icon_size + 15, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, data["name"])
            if data["is_favorite"]:
                painter.setPen(QColor(255, 215, 0))
                painter.drawText(rect.adjusted(10, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, "★")
            if data["type"] != "app":
                painter.setFont(QFont("Inter", 9))
                painter.drawText(rect.adjusted(self.icon_size + 15, 0, -8, 0), Qt.AlignVCenter | Qt.AlignRight, data["type"].upper())
        else:  # compact
            painter.drawRoundedRect(rect.adjusted(4, 4, -4, -4), self.border_radius, self.border_radius)
            icon = index.data(Qt.DecorationRole)
            if icon:
                painter.drawPixmap(rect.left() + 8, rect.top() + (rect.height() - self.icon_size) // 2, icon.pixmap(QSize(self.icon_size, self.icon_size)))
            painter.setPen(QColor(220, 220, 220))
            painter.setFont(QFont("Inter", 11))
            painter.drawText(rect.adjusted(self.icon_size + 10, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, data["name"])
            if data["is_favorite"]:
                painter.setPen(QColor(255, 215, 0))
                painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, "★")

        painter.restore()

    def sizeHint(self, option, index):
        if self.view_mode == "grid":
            return QSize(160, 160)
        elif self.view_mode == "list":
            return QSize(100, 56)
        else:  # compact
            return QSize(100, 40)

class AppLoaderThread(QThread):
    appsLoaded = pyqtSignal(dict)
    statusUpdate = pyqtSignal(str)
    progressUpdate = pyqtSignal(int)
    errorSignal = pyqtSignal(str)

    def run(self):
        try:
            apps = {}
            start_menu_paths = [
                Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
                Path("C:/ProgramData/Microsoft/Windows/Start Menu/Programs")
            ]
            total = sum(len(glob.glob(str(path / "**/*.lnk"), recursive=True)) for path in start_menu_paths if path.exists())
            processed = 0
            for path in start_menu_paths:
                if path.exists():
                    for shortcut in glob.glob(str(path / "**/*.lnk"), recursive=True):
                        app_path = Path(shortcut)
                        app_name = app_path.stem
                        category = app_path.parent.relative_to(path).as_posix() if app_path.parent != path else "General"
                        apps.setdefault(category, {})[app_name] = shortcut
                        processed += 1
                        self.progressUpdate.emit(int((processed / total) * 100) if total else 100)
            self.appsLoaded.emit(apps)
            self.statusUpdate.emit("Ready")
        except Exception as e:
            self.errorSignal.emit(f"Failed to load apps: {str(e)}")

class NotificationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setStyleSheet("background: #2a2a2a; color: #ffffff; border: 1px solid #4682b4; border-radius: 8px; padding: 10px; font: 12px Inter;")
        self.layout = QVBoxLayout(self)
        self.label = QLabel("")
        self.label.setStyleSheet("color: #ffffff; font: 12px Inter;")
        self.layout.addWidget(self.label)
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)

    def show_message(self, message, duration=3000):
        self.label.setText(message)
        self.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        pos = screen.bottomRight() - QPoint(self.width() + 20, self.height() + 20)
        self.move(pos)
        anim = QPropertyAnimation(self, b"opacity")
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()
        self.show()
        self.timer.start(duration)

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 550)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet("""
            QDialog { background: #1e1e1e; border: 1px solid #4682b4; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); }
            QLabel { color: #dcdcdc; font: bold 13px Inter; }
            QComboBox, QSpinBox, QSlider, QLineEdit { background: #2a2a2a; color: #dcdcdc; border: 1px solid #4682b4; border-radius: 8px; padding: 6px; font: 12px Inter; }
            QPushButton { background: #4682b4; color: #ffffff; border-radius: 8px; padding: 8px; font: bold 12px Inter; }
            QPushButton:hover { background: #5a9bd4; }
            QCheckBox { color: #dcdcdc; font: 12px Inter; }
            QTabWidget::pane { border: 1px solid #4682b4; background: #252525; }
            QTabWidget::tab-bar { alignment: center; }
            QTabBar::tab { background: #2a2a2a; color: #dcdcdc; padding: 8px 16px; border: none; font: bold 12px Inter; }
            QTabBar::tab:selected { background: #4682b4; color: #ffffff; }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title_label = QLabel("Settings")
        title_label.setStyleSheet("font: bold 16px Inter; color: #4682b4;")
        layout.addWidget(title_label)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Appearance Tab
        appearance_widget = QWidget()
        appearance_layout = QVBoxLayout(appearance_widget)
        appearance_layout.setSpacing(8)

        appearance_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "High Contrast", "Custom"])
        self.theme_combo.setCurrentText(self.parent.theme_mode.capitalize())
        self.theme_combo.currentTextChanged.connect(self.on_theme_change)
        appearance_layout.addWidget(self.theme_combo)

        appearance_layout.addWidget(QLabel("Background Color:"))
        self.bg_color_btn = QPushButton("Pick Color")
        self.bg_color_btn.clicked.connect(self.pick_bg_color)
        appearance_layout.addWidget(self.bg_color_btn)

        appearance_layout.addWidget(QLabel("Accent Color:"))
        self.accent_color_btn = QPushButton("Pick Color")
        self.accent_color_btn.clicked.connect(self.pick_accent_color)
        appearance_layout.addWidget(self.accent_color_btn)

        appearance_layout.addWidget(QLabel("Font Size:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 18)
        self.font_size.setValue(self.parent.font_settings['size'])
        self.font_size.valueChanged.connect(self.on_font_size_change)
        appearance_layout.addWidget(self.font_size)

        appearance_layout.addWidget(QLabel("Icon Size:"))
        self.icon_size = QSpinBox()
        self.icon_size.setRange(16, 128)
        self.icon_size.setValue(self.parent.icon_size)
        self.icon_size.valueChanged.connect(self.on_icon_size_change)
        appearance_layout.addWidget(self.icon_size)

        appearance_layout.addWidget(QLabel("Border Radius:"))
        self.border_radius = QSpinBox()
        self.border_radius.setRange(4, 16)
        self.border_radius.setValue(self.parent.border_radius)
        self.border_radius.valueChanged.connect(self.on_border_radius_change)
        appearance_layout.addWidget(self.border_radius)

        tabs.addTab(appearance_widget, "Appearance")

        # Behavior Tab
        behavior_widget = QWidget()
        behavior_layout = QVBoxLayout(behavior_widget)
        behavior_layout.setSpacing(8)

        behavior_layout.addWidget(QLabel("Animation Speed (ms):"))
        self.anim_speed = QSlider(Qt.Horizontal)
        self.anim_speed.setRange(0, 500)
        self.anim_speed.setValue(self.parent.anim_speed)
        self.anim_speed.valueChanged.connect(self.on_anim_speed_change)
        behavior_layout.addWidget(self.anim_speed)

        behavior_layout.addWidget(QLabel("Animation Curve:"))
        self.anim_curve = QComboBox()
        self.anim_curve.addItems(["InOutQuad", "InOutCubic", "Linear", "OutBounce"])
        self.anim_curve.setCurrentText(self.parent.anim_curve)
        self.anim_curve.currentTextChanged.connect(self.on_anim_curve_change)
        behavior_layout.addWidget(self.anim_curve)

        behavior_layout.addWidget(QLabel("Grid Columns:"))
        self.grid_columns = QSpinBox()
        self.grid_columns.setRange(2, 8)
        self.grid_columns.setValue(self.parent.grid_columns)
        self.grid_columns.valueChanged.connect(self.on_grid_columns_change)
        behavior_layout.addWidget(self.grid_columns)

        self.minimize_to_tray = QCheckBox("Minimize to System Tray")
        self.minimize_to_tray.setChecked(self.parent.minimize_to_tray)
        self.minimize_to_tray.stateChanged.connect(self.on_minimize_to_tray_change)
        behavior_layout.addWidget(self.minimize_to_tray)

        self.show_tray_icon = QCheckBox("Show System Tray Icon")
        self.show_tray_icon.setChecked(self.parent.show_tray_icon)
        self.show_tray_icon.stateChanged.connect(self.on_show_tray_icon_change)
        behavior_layout.addWidget(self.show_tray_icon)

        self.enable_animations = QCheckBox("Enable Animations")
        self.enable_animations.setChecked(self.parent.enable_animations)
        self.enable_animations.stateChanged.connect(self.on_enable_animations_change)
        behavior_layout.addWidget(self.enable_animations)

        tabs.addTab(behavior_widget, "Behavior")

        # Advanced Tab
        advanced_widget = QWidget()
        advanced_layout = QVBoxLayout(advanced_widget)
        advanced_layout.setSpacing(8)

        advanced_layout.addWidget(QLabel("Global Hotkey:"))
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setPlaceholderText("e.g., ctrl+alt+q")
        self.hotkey_input.setText(self.parent.hotkey)
        self.hotkey_input.textChanged.connect(self.on_hotkey_change)
        advanced_layout.addWidget(self.hotkey_input)

        advanced_layout.addWidget(QLabel("Cache Size Limit (MB):"))
        self.cache_limit = QSpinBox()
        self.cache_limit.setRange(10, 1000)
        self.cache_limit.setValue(self.parent.cache_limit)
        self.cache_limit.valueChanged.connect(self.on_cache_limit_change)
        advanced_layout.addWidget(self.cache_limit)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_settings)
        advanced_layout.addWidget(reset_btn)

        tabs.addTab(advanced_widget, "Advanced")

        close_btn = QPushButton("Close")
        close_btn.setToolTip("Close settings")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def pick_bg_color(self):
        color = QColorDialog.getColor(QColor(self.parent.custom_colors['bg']), self)
        if color.isValid():
            self.parent.custom_colors['bg'] = color.name()
            self.parent.theme_mode = "custom"
            self.theme_combo.setCurrentText("Custom")
            self.parent.apply_styles()
            self.parent.save_settings()
            self.parent.show_notification("Background color updated.", 2000)

    def pick_accent_color(self):
        color = QColorDialog.getColor(QColor(self.parent.custom_colors['accent']), self)
        if color.isValid():
            self.parent.custom_colors['accent'] = color.name()
            self.parent.theme_mode = "custom"
            self.theme_combo.setCurrentText("Custom")
            self.parent.apply_styles()
            self.parent.save_settings()
            self.parent.show_notification("Accent color updated.", 2000)

    def on_theme_change(self, theme):
        try:
            self.parent.change_theme(theme)
            self.parent.show_notification(f"Theme changed to {theme}.", 2000)
        except Exception as e:
            logging.error(f"Theme change failed: {str(e)}")
            self.parent.show_notification("Error changing theme.", 3000)

    def on_font_size_change(self, size):
        try:
            self.parent.change_font_size(size)
            self.parent.show_notification(f"Font size changed to {size}.", 2000)
        except Exception as e:
            logging.error(f"Font size change failed: {str(e)}")
            self.parent.show_notification("Error changing font size.", 3000)

    def on_icon_size_change(self, size):
        try:
            self.parent.change_icon_size(size)
            self.parent.show_notification(f"Icon size changed to {size}.", 2000)
        except Exception as e:
            logging.error(f"Icon size change failed: {str(e)}")
            self.parent.show_notification("Error changing icon size.", 3000)

    def on_border_radius_change(self, radius):
        try:
            self.parent.change_border_radius(radius)
            self.parent.show_notification(f"Border radius changed to {radius}.", 2000)
        except Exception as e:
            logging.error(f"Border radius change failed: {str(e)}")
            self.parent.show_notification("Error changing border radius.", 3000)

    def on_anim_speed_change(self, speed):
        try:
            self.parent.change_anim_speed(speed)
            self.parent.show_notification(f"Animation speed set to {speed}ms.", 2000)
        except Exception as e:
            logging.error(f"Animation speed change failed: {str(e)}")
            self.parent.show_notification("Error changing animation speed.", 3000)

    def on_anim_curve_change(self, curve):
        try:
            self.parent.change_anim_curve(curve)
            self.parent.show_notification(f"Animation curve set to {curve}.", 2000)
        except Exception as e:
            logging.error(f"Animation curve change failed: {str(e)}")
            self.parent.show_notification("Error changing animation curve.", 3000)

    def on_grid_columns_change(self, columns):
        try:
            self.parent.change_grid_columns(columns)
            self.parent.show_notification(f"Grid columns set to {columns}.", 2000)
        except Exception as e:
            logging.error(f"Grid columns change failed: {str(e)}")
            self.parent.show_notification("Error changing grid columns.", 3000)

    def on_hotkey_change(self, hotkey):
        try:
            self.parent.set_hotkey(hotkey.strip())
            self.parent.show_notification(f"Hotkey set to {hotkey}.", 2000)
        except Exception as e:
            logging.error(f"Hotkey change failed: {str(e)}")
            self.parent.show_notification("Error changing hotkey.", 3000)

    def on_minimize_to_tray_change(self, state):
        try:
            self.parent.minimize_to_tray = bool(state)
            self.parent.save_settings()
            self.parent.show_notification(f"Minimize to tray {'enabled' if state else 'disabled'}.", 2000)
        except Exception as e:
            logging.error(f"Minimize to tray toggle failed: {str(e)}")
            self.parent.show_notification("Error toggling minimize to tray.", 3000)

    def on_show_tray_icon_change(self, state):
        try:
            self.parent.show_tray_icon = bool(state)
            self.parent.setup_system_tray()
            self.parent.save_settings()
            self.parent.show_notification(f"System tray icon {'shown' if state else 'hidden'}.", 2000)
        except Exception as e:
            logging.error(f"Show tray icon toggle failed: {str(e)}")
            self.parent.show_notification("Error toggling tray icon.", 3000)

    def on_enable_animations_change(self, state):
        try:
            self.parent.enable_animations = bool(state)
            self.parent.save_settings()
            self.parent.show_notification(f"Animations {'enabled' if state else 'disabled'}.", 2000)
        except Exception as e:
            logging.error(f"Enable animations toggle failed: {str(e)}")
            self.parent.show_notification("Error toggling animations.", 3000)

    def on_cache_limit_change(self, limit):
        try:
            self.parent.change_cache_limit(limit)
            self.parent.show_notification(f"Cache limit set to {limit}MB.", 2000)
        except Exception as e:
            logging.error(f"Cache limit change failed: {str(e)}")
            self.parent.show_notification("Error changing cache limit.", 3000)

    def reset_settings(self):
        try:
            self.parent.reset_settings()
            self.theme_combo.setCurrentText(self.parent.theme_mode.capitalize())
            self.font_size.setValue(self.parent.font_settings['size'])
            self.icon_size.setValue(self.parent.icon_size)
            self.border_radius.setValue(self.parent.border_radius)
            self.anim_speed.setValue(self.parent.anim_speed)
            self.anim_curve.setCurrentText(self.parent.anim_curve)
            self.grid_columns.setValue(self.parent.grid_columns)
            self.minimize_to_tray.setChecked(self.parent.minimize_to_tray)
            self.show_tray_icon.setChecked(self.parent.show_tray_icon)
            self.enable_animations.setChecked(self.parent.enable_animations)
            self.hotkey_input.setText(self.parent.hotkey)
            self.cache_limit.setValue(self.parent.cache_limit)
            self.parent.show_notification("Settings reset to defaults.", 2000)
        except Exception as e:
            logging.error(f"Reset settings failed: {str(e)}")
            self.parent.show_notification("Error resetting settings.", 3000)

class AppLauncher(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Launcher")
        self.setMinimumSize(750, 550)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAcceptDrops(True)

        # Initialize variables
        self.apps = {}
        self.links = self.load_links()
        self.recent_items = self.load_recent()
        self.pinned_items = self.load_pinned()
        self.selected_apps = set()
        self.selected_links = set()
        self.selected_recent = set()
        self.selected_pinned = set()
        self.settings = self.load_settings()
        self.theme_mode = self.settings.get('theme', 'dark')
        self.custom_colors = self.settings.get('colors', {
            'bg': '#1e1e1e', 'fg': '#dcdcdc', 'accent': '#4682b4',
            'pane': '#252525', 'list_text': '#dcdcdc', 'list_bg': '#252525'
        })
        self.font_settings = self.settings.get('font', {'family': 'Inter', 'size': 12})
        self.anim_speed = self.settings.get('anim_speed', 250)
        self.anim_curve = self.settings.get('anim_curve', 'InOutQuad')
        self.icon_size = self.settings.get('icon_size', 32)
        self.border_radius = self.settings.get('border_radius', 8)
        self.grid_columns = self.settings.get('grid_columns', 4)
        self.minimize_to_tray = self.settings.get('minimize_to_tray', True)
        self.show_tray_icon = self.settings.get('show_tray_icon', True)
        self.enable_animations = self.settings.get('enable_animations', True)
        self.hotkey = self.settings.get('hotkey', 'ctrl+alt+q')
        self.cache_limit = self.settings.get('cache_limit', 100)
        self.icon_cache = {}
        self.icon_cache_dir = Path("icon_cache")
        self.icon_cache_dir.mkdir(exist_ok=True)
        self.drag_pos = None
        self.is_maximized = False
        self.view_mode = "list"
        self.sort_mode = "name"
        self.current_tab = 0
        self.notification_widget = NotificationWidget(self)
        self.stats_label = QLabel("Initializing...")
        self.stats_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setTextVisible(False)
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.filter_all)
        self.search_cache = {}

        # Initialize UI components
        self.setup_fonts()
        self.setup_system_tray()
        self.setup_hotkey()
        self.setup_ui()
        self.load_apps_async()
        self.center_on_screen()

    def setup_fonts(self):
        font_db = QFontDatabase()
        available_fonts = font_db.families()
        if "Inter" in available_fonts:
            self.font_settings['family'] = "Inter"
        else:
            self.font_settings['family'] = "Arial"

    def setup_system_tray(self):
        if not self.show_tray_icon:
            if hasattr(self, 'tray_icon'):
                self.tray_icon.hide()
            return
        tray_icon = QIcon.fromTheme("system-software-install")
        if tray_icon.isNull():
            tray_icon = QIcon.fromTheme("application")
            logging.warning("System tray icon 'system-software-install' not found, using 'application'.")
        self.tray_icon = QSystemTrayIcon(tray_icon, self)
        tray_menu = QMenu()
        tray_menu.addAction("Show", self.show)
        tray_menu.addAction("Quit", QApplication.quit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def setup_hotkey(self):
        try:
            keyboard.remove_hotkey(self.hotkey)
        except:
            pass
        try:
            keyboard.add_hotkey(self.hotkey, self.toggle_visibility)
        except Exception as e:
            logging.warning(f"Failed to set hotkey {self.hotkey}: {str(e)}")
            self.show_notification("Failed to set hotkey.", 3000)

    def set_hotkey(self, hotkey):
        try:
            keyboard.remove_hotkey(self.hotkey)
            keyboard.add_hotkey(hotkey, self.toggle_visibility)
            self.hotkey = hotkey
            self.save_settings()
        except Exception as e:
            logging.error(f"Failed to set hotkey {hotkey}: {str(e)}")
            self.show_notification(f"Failed to set hotkey: {str(e)}.", 3000)

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Title Bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(48)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(16, 0, 16, 0)
        title_layout.setSpacing(8)

        # App Icon and Title
        app_icon = QLabel()
        app_icon.setPixmap(QIcon.fromTheme("system-software-install").pixmap(28, 28))
        title_layout.addWidget(app_icon)
        title_label = QLabel("Quantum Launcher")
        title_label.setStyleSheet("font: bold 16px Inter; color: #dcdcdc;")
        title_layout.addWidget(title_label)
        title_layout.addSpacing(20)

        # Tab Buttons
        self.tab_buttons = []
        for text, slot in [
            ("Apps", lambda: self.show_content(0)),
            ("Links", lambda: self.show_content(1)),
            ("Recent", lambda: self.show_content(2)),
            ("Pinned", lambda: self.show_content(3)),
            ("Settings", self.show_settings)
        ]:
            btn = QToolButton()
            btn.setText(text)
            btn.setToolTip(f"Switch to {text} view")
            btn.setFixedSize(100, 36)
            btn.setCheckable(True)
            btn.clicked.connect(slot)
            title_layout.addWidget(btn)
            self.tab_buttons.append(btn)
        self.tab_buttons[0].setChecked(True)
        title_layout.addStretch()

        # Window Controls
        minimize_btn = QToolButton()
        minimize_btn.setText("−")
        minimize_btn.setToolTip("Minimize")
        minimize_btn.setFixedSize(36, 36)

        maximize_btn = QToolButton()
        maximize_btn.setText("↔")
        maximize_btn.setToolTip("Maximize/Restore")
        maximize_btn.setFixedSize(36, 36)

        close_btn = QToolButton()
        close_btn.setText("✕")
        close_btn.setToolTip("Close")
        close_btn.setFixedSize(36, 36)

        for btn in [minimize_btn, maximize_btn, close_btn]:
            btn.setStyleSheet("""
                QToolButton { background: #2a2a2a; color: #dcdcdc; border: none; border-radius: 18px; font: bold 14px; }
                QToolButton:hover { background: #4682b4; color: #ffffff; }
            """)
        minimize_btn.clicked.connect(self.showMinimized)
        maximize_btn.clicked.connect(self.toggle_maximize)
        close_btn.clicked.connect(self.close_window)
        title_layout.addWidget(minimize_btn)
        title_layout.addWidget(maximize_btn)
        title_layout.addWidget(close_btn)
        main_layout.addWidget(self.title_bar)

        # Main Content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        main_layout.addWidget(content_widget)

        # Search Bar
        search_layout = QHBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search apps, links, or pinned items...")
        self.search_bar.setFixedHeight(40)
        self.search_bar.setStyleSheet("""
            QLineEdit { background: #2a2a2a; color: #dcdcdc; border: 1px solid #4682b4; border-radius: 20px; padding: 8px 32px 8px 32px; font: 13px Inter; }
            QLineEdit:focus { border: 2px solid #4682b4; background: #2a2a2a; }
        """)
        self.search_bar.setTextMargins(20, 0, 20, 0)
        self.search_bar.textChanged.connect(self.debounce_search)
        self.setup_completer()
        search_layout.addWidget(self.search_bar)

        # Search Icon
        search_icon = QLabel()
        search_icon.setPixmap(QIcon.fromTheme("edit-find").pixmap(20, 20))
        search_icon.setStyleSheet("background: none; padding: 0px;")
        search_icon.setFixedSize(20, 20)
        search_layout.addWidget(search_icon, alignment=Qt.AlignLeft | Qt.AlignVCenter)
        search_layout.setAlignment(search_icon, Qt.AlignLeft | Qt.AlignVCenter)
        search_icon.setGeometry(20, 10, 20, 20)  # Position inside search bar

        # Clear Button
        clear_btn = QToolButton()
        clear_btn.setText("×")
        clear_btn.setToolTip("Clear search")
        clear_btn.setFixedSize(20, 20)
        clear_btn.setStyleSheet("background: none; color: #dcdcdc; font: bold 14px;")
        clear_btn.clicked.connect(self.search_bar.clear)
        search_layout.addWidget(clear_btn, alignment=Qt.AlignRight | Qt.AlignVCenter)

        # Sort Combo
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Category"])
        self.sort_combo.setFixedWidth(130)
        self.sort_combo.setToolTip("Sort items")
        self.sort_combo.currentTextChanged.connect(lambda text: self.set_sort_mode(text.lower()))
        search_layout.addWidget(self.sort_combo)
        content_layout.addLayout(search_layout)

        # Action Bar
        self.action_bar = QWidget()
        action_layout = QHBoxLayout(self.action_bar)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        run_btn = QPushButton("Run")
        run_btn.setToolTip("Run selected items (Ctrl+R)")
        run_btn.setFixedSize(90, 36)
        run_btn.clicked.connect(self.run_selected)
        action_layout.addWidget(run_btn)
        add_link_btn = QPushButton("Add Link")
        add_link_btn.setToolTip("Add a new link (Ctrl+L)")
        add_link_btn.setFixedSize(90, 36)
        add_link_btn.clicked.connect(self.add_link_popup)
        action_layout.addWidget(add_link_btn)
        view_btn = QPushButton("View")
        view_btn.setToolTip("Cycle view mode")
        view_btn.setFixedSize(90, 36)
        view_btn.clicked.connect(self.toggle_view_mode)
        action_layout.addWidget(view_btn)
        action_layout.addStretch()
        content_layout.addWidget(self.action_bar)

        # Content List
        self.content_list = QListView()
        self.content_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.content_list.setViewMode(QListView.ListMode)
        self.content_list.setIconSize(QSize(self.icon_size, self.icon_size))
        self.content_model = QStandardItemModel()
        self.content_list.setModel(self.content_model)
        self.content_list.setItemDelegate(CustomItemDelegate(self.view_mode, self.icon_size, self.border_radius))
        self.content_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.content_list.customContextMenuRequested.connect(self.show_context_menu)
        self.content_list.selectionModel().selectionChanged.connect(self.update_selection)
        self.content_list.setMouseTracking(True)
        content_layout.addWidget(self.content_list)

        # Status Bar
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(8, 4, 8, 4)
        status_layout.addWidget(self.stats_label)
        status_layout.addWidget(self.progress_bar)
        status_layout.addStretch()
        content_layout.addWidget(status_bar)

        # Shortcuts
        self.add_shortcut('Ctrl+1', lambda: self.show_content(0))
        self.add_shortcut('Ctrl+2', lambda: self.show_content(1))
        self.add_shortcut('Ctrl+3', lambda: self.show_content(2))
        self.add_shortcut('Ctrl+4', lambda: self.show_content(3))
        self.add_shortcut('Ctrl+5', self.show_settings)
        self.add_shortcut('Ctrl+R', self.run_selected)
        self.add_shortcut('Ctrl+L', self.add_link_popup)
        self.add_shortcut('Ctrl+T', self.toggle_view_mode)

        self.apply_styles()

    def setup_completer(self):
        completer = QCompleter()
        self.completer_model = QStringListModel()
        completer.setModel(self.completer_model)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.search_bar.setCompleter(completer)
        self.update_completer()

    def update_completer(self):
        completer_list = []
        for category in self.apps:
            completer_list.extend(self.apps[category].keys())
        completer_list.extend(link["name"] for link in self.links)
        completer_list.extend(item["name"] for item in self.recent_items)
        completer_list.extend(item["name"] for item in self.pinned_items)
        self.completer_model.setStringList(completer_list)

    def debounce_search(self, text):
        self.search_timer.start(100)

    def apply_styles(self):
        bg = self.custom_colors['bg']
        fg = self.custom_colors['fg']
        accent = self.custom_colors['accent']
        pane = self.custom_colors['pane']
        list_text = self.custom_colors['list_text']
        list_bg = self.custom_colors['list_bg']
        font = f"{self.font_settings['family']} {self.font_settings['size']}pt"

        if self.theme_mode == "light":
            self.custom_colors.update({
                'bg': '#f5f5f5', 'fg': '#1a1a1a', 'accent': '#0077b6',
                'pane': '#e0e0e0', 'list_text': '#1a1a1a', 'list_bg': '#e0e0e0'
            })
        elif self.theme_mode == "highcontrast":
            self.custom_colors.update({
                'bg': '#000000', 'fg': '#00ff00', 'accent': '#00ff00',
                'pane': '#111111', 'list_text': '#00ff00', 'list_bg': '#111111'
            })
        bg, fg, accent, pane, list_text, list_bg = (
            self.custom_colors['bg'], self.custom_colors['fg'], self.custom_colors['accent'],
            self.custom_colors['pane'], self.custom_colors['list_text'], self.custom_colors['list_bg']
        )

        self.setStyleSheet(f"""
            QMainWindow {{ background: {bg}; border: 1px solid {accent}; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); }}
            QLineEdit {{ background: {pane}; color: {fg}; border: 1px solid {accent}; border-radius: 20px; padding: 8px 32px; font: {font}; }}
            QLineEdit:focus {{ border: 2px solid {accent}; background: {pane}; }}
            QListView {{ background: {list_bg}; color: {list_text}; border: none; padding: 12px; font: {font}; }}
            QToolButton {{ background: {pane}; color: {fg}; border: none; border-radius: 8px; font: bold 13px Inter; }}
            QToolButton:checked, QToolButton:hover {{ background: {accent}; color: #ffffff; }}
            QPushButton {{ background: {accent}; color: #ffffff; border-radius: 8px; padding: 8px; font: bold 13px Inter; }}
            QPushButton:hover {{ background: #5a9bd4; }}
            QComboBox {{ background: {pane}; color: {fg}; border: 1px solid {accent}; border-radius: 8px; padding: 6px; font: 12px Inter; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{ image: none; }}
            QLabel {{ color: {fg}; font: 12px Inter; padding: 4px; }}
            QProgressBar {{ background: {pane}; border: 1px solid {accent}; border-radius: 2px; }}
            QProgressBar::chunk {{ background: {accent}; }}
        """)
        gradient = QLinearGradient(0, 0, 0, 48)
        gradient.setColorAt(0, QColor(pane))
        gradient.setColorAt(1, QColor(self.adjust_color(pane, -20)))
        self.title_bar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {pane}, stop:1 {self.adjust_color(pane, -20)});
            border-bottom: 1px solid {accent};
        """)
        self.stats_label.setStyleSheet(f"color: {fg}; font: 11px Inter;")
        self.action_bar.setStyleSheet(f"background: {pane}; border-radius: 8px; padding: 6px;")

    def adjust_color(self, color, delta):
        c = QColor(color)
        return QColor(max(0, c.red() + delta), max(0, c.green() + delta), max(0, c.blue() + delta)).name()

    def show_content(self, index):
        for btn in self.tab_buttons:
            btn.setChecked(False)
        self.tab_buttons[index].setChecked(True)
        self.current_tab = index
        self.update_content()
        if self.enable_animations:
            self.animate_pane()
            self.fade_in_content()

    def update_content(self):
        self.content_model.clear()
        font = QFont(self.font_settings['family'], self.font_settings['size'])
        filter_text = self.search_bar.text().lower()

        items = []
        cache_key = f"{self.current_tab}_{filter_text}"
        if cache_key in self.search_cache:
            items = self.search_cache[cache_key]
        else:
            if self.current_tab == 0:  # Apps
                for category in sorted(self.apps.keys()):
                    app_list = [(app_name, self.apps[category][app_name], category) for app_name in self.apps[category]]
                    if filter_text:
                        app_list = [(name, path, cat) for name, path, cat in app_list if fuzz.partial_ratio(filter_text, name.lower()) > 90]
                    items.extend([(name, path, cat, "app", False) for name, path, cat in app_list])
            elif self.current_tab == 1:  # Links
                for link in self.links:
                    if filter_text and fuzz.partial_ratio(filter_text, link["name"].lower()) <= 90:
                        continue
                    items.append((link["name"], link["url"], link.get("category", "General"), "link", link.get("is_favorite", False)))
            elif self.current_tab == 2:  # Recent
                for item in self.recent_items:
                    if filter_text and fuzz.partial_ratio(filter_text, item["name"].lower()) <= 90:
                        continue
                    items.append((f"{item['name']} ({item['type']})", item["path"], item.get("category", "General"), item["type"], item.get("is_favorite", False)))
            elif self.current_tab == 3:  # Pinned
                for item in self.pinned_items:
                    if filter_text and fuzz.partial_ratio(filter_text, item["name"].lower()) <= 90:
                        continue
                    items.append((f"{item['name']} ({item['type']})", item["path"], item.get("category", "General"), item["type"], item.get("is_favorite", False)))
            self.search_cache[cache_key] = items
            if len(self.search_cache) > 100:
                self.search_cache.pop(next(iter(self.search_cache)))

        if self.sort_mode == "category":
            items.sort(key=lambda x: (x[2], x[0]))
        elif self.sort_mode == "lastused" and self.current_tab in (2, 3):
            items.sort(key=lambda x: next((i.get("timestamp", "") for i in self.recent_items if i["name"] == x[0].split(" (")[0] and i["type"] == x[3]), ""), reverse=True)
        else:  # name
            items.sort(key=lambda x: x[0])

        for name, path, category, item_type, is_favorite in items:
            icon = self.get_app_icon(path) if item_type == "app" else (QIcon.fromTheme("link") if item_type == "link" else QIcon.fromTheme("pinned"))
            item = AppItem(name, path, category, item_type, icon, font, is_favorite)
            self.content_model.appendRow(item)

        self.content_list.setItemDelegate(CustomItemDelegate(self.view_mode, self.icon_size, self.border_radius))
        self.content_list.setIconSize(QSize(self.icon_size, self.icon_size))
        self.update_stats()
        self.update_completer()

    def animate_pane(self):
        if not self.enable_animations:
            return
        animation = QPropertyAnimation(self.content_list, b"pos")
        animation.setDuration(self.anim_speed)
        animation.setStartValue(QPoint(-20, self.content_list.pos().y()))
        animation.setEndValue(QPoint(0, self.content_list.pos().y()))
        animation.setEasingCurve(getattr(QEasingCurve, self.anim_curve))
        animation.start()

    def fade_in_content(self):
        if not self.enable_animations:
            return
        self.content_list.setProperty("opacity", 0.0)
        anim = QPropertyAnimation(self.content_list, b"opacity")
        anim.setDuration(self.anim_speed)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(getattr(QEasingCurve, self.anim_curve))
        anim.start()

    def show_context_menu(self, point):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu { background: #2a2a2a; color: #dcdcdc; border: 1px solid #4682b4; border-radius: 8px; }
            QMenu::item:selected { background: #4682b4; color: #ffffff; }
        """)
        if self.current_tab == 0:
            menu.addAction("Refresh Apps", self.refresh_apps)
            menu.addAction("Open File Location", self.open_app_location)
            menu.addAction("Pin", self.pin_selected)
        elif self.current_tab == 1:
            menu.addAction("Delete Link", self.delete_selected)
            menu.addAction("Edit Category", self.edit_link_category)
            menu.addAction("Copy URL", self.copy_link_url)
            menu.addAction("Pin", self.pin_selected)
            menu.addAction("Toggle Favorite", self.toggle_favorite)
        elif self.current_tab == 2:
            menu.addAction("Clear Recent", self.clear_recent)
            menu.addAction("Pin", self.pin_selected)
            menu.addAction("Toggle Favorite", self.toggle_favorite)
        elif self.current_tab == 3:
            menu.addAction("Unpin", self.unpin_selected)
            menu.addAction("Toggle Favorite", self.toggle_favorite)

        sort_menu = menu.addMenu("Sort By")
        sort_menu.addAction("Name", lambda: self.set_sort_mode("name")).setCheckable(True)
        sort_menu.addAction("Category", lambda: self.set_sort_mode("category")).setCheckable(True)
        if self.current_tab in (2, 3):
            sort_menu.addAction("Last Used", lambda: self.set_sort_mode("lastused")).setCheckable(True)
        for action in sort_menu.actions():
            action.setChecked(action.text().lower() == self.sort_mode)

        menu.exec_(self.content_list.mapToGlobal(point))

    def set_sort_mode(self, mode):
        self.sort_mode = mode.lower()
        self.update_content()
        self.show_notification(f"Sorted by {mode}.", 2000)

    def toggle_favorite(self):
        for name in self.selected_links:
            for link in self.links:
                if link["name"] == name:
                    link["is_favorite"] = not link.get("is_favorite", False)
        for name in self.selected_recent:
            for item in self.recent_items:
                if item["name"] == name.split(" (")[0]:
                    item["is_favorite"] = not item.get("is_favorite", False)
        for name in self.selected_pinned:
            for item in self.pinned_items:
                if item["name"] == name.split(" (")[0]:
                    item["is_favorite"] = not item.get("is_favorite", False)
        self.save_links()
        self.save_recent()
        self.save_pinned()
        self.update_content()
        self.show_notification("Favorite status toggled.", 2000)

    def update_stats(self):
        self.stats_label.setText(
            f"Apps: {sum(len(apps) for apps in self.apps.values())} | "
            f"Links: {len(self.links)} | "
            f"Recent: {len(self.recent_items)} | "
            f"Pinned: {len(self.pinned_items)} | "
            f"Selected: {len(self.selected_apps) + len(self.selected_links) + len(self.selected_recent) + len(self.selected_pinned)}"
        )

    def update_selection(self, selected, deselected):
        self.selected_apps.clear()
        self.selected_links.clear()
        self.selected_recent.clear()
        self.selected_pinned.clear()
        for index in self.content_list.selectedIndexes():
            data = self.content_model.itemFromIndex(index).data(Qt.UserRole)
            name = data["name"].split(" (")[0] if self.current_tab in (2, 3) else data["name"]
            if self.current_tab == 0:
                self.selected_apps.add(name)
            elif self.current_tab == 1:
                self.selected_links.add(name)
            elif self.current_tab == 2:
                self.selected_recent.add(name)
            elif self.current_tab == 3:
                self.selected_pinned.add(name)
        self.update_stats()

    def add_shortcut(self, key, slot):
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QShortcut
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(slot)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = self.content_list.width()
        if self.view_mode == "grid":
            columns = self.grid_columns
            self.content_list.setGridSize(QSize(width // columns, 160))
        else:
            self.content_list.setGridSize(QSize())
        self.center_on_screen()

    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def toggle_view_mode(self):
        modes = ["grid", "list", "compact"]
        current_idx = modes.index(self.view_mode)
        self.view_mode = modes[(current_idx + 1) % len(modes)]
        self.content_list.setViewMode(QListView.IconMode if self.view_mode == "grid" else QListView.ListMode)
        self.update_content()
        self.show_notification(f"View mode: {self.view_mode.title()}.", 2000)

    def change_theme(self, theme):
        self.theme_mode = theme.lower().replace(" ", "")
        self.apply_styles()
        self.save_settings()

    def change_font_size(self, size):
        self.font_settings['size'] = size
        self.apply_styles()
        self.update_content()
        self.save_settings()

    def change_icon_size(self, size):
        self.icon_size = size
        self.update_content()
        self.save_settings()

    def change_border_radius(self, radius):
        self.border_radius = radius
        self.update_content()
        self.save_settings()

    def change_anim_speed(self, speed):
        self.anim_speed = speed
        self.save_settings()

    def change_anim_curve(self, curve):
        self.anim_curve = curve
        self.save_settings()

    def change_grid_columns(self, columns):
        self.grid_columns = columns
        self.resizeEvent(None)
        self.save_settings()

    def change_cache_limit(self, limit):
        self.cache_limit = limit
        self.cleanup_icon_cache()
        self.save_settings()

    def reset_settings(self):
        self.settings = {
            'theme': 'dark',
            'colors': {
                'bg': '#1e1e1e', 'fg': '#dcdcdc', 'accent': '#4682b4',
                'pane': '#252525', 'list_text': '#dcdcdc', 'list_bg': '#252525'
            },
            'font': {'family': 'Inter', 'size': 12},
            'anim_speed': 250,
            'anim_curve': 'InOutQuad',
            'icon_size': 32,
            'border_radius': 8,
            'grid_columns': 4,
            'minimize_to_tray': True,
            'show_tray_icon': True,
            'enable_animations': True,
            'hotkey': 'ctrl+alt+q',
            'cache_limit': 100
        }
        self.theme_mode = self.settings['theme']
        self.custom_colors = self.settings['colors']
        self.font_settings = self.settings['font']
        self.anim_speed = self.settings['anim_speed']
        self.anim_curve = self.settings['anim_curve']
        self.icon_size = self.settings['icon_size']
        self.border_radius = self.settings['border_radius']
        self.grid_columns = self.settings['grid_columns']
        self.minimize_to_tray = self.settings['minimize_to_tray']
        self.show_tray_icon = self.settings['show_tray_icon']
        self.enable_animations = self.settings['enable_animations']
        self.hotkey = self.settings['hotkey']
        self.cache_limit = self.settings['cache_limit']
        self.apply_styles()
        self.update_content()
        self.setup_system_tray()
        self.setup_hotkey()
        self.save_settings()

    def load_apps_async(self):
        self.progress_bar.setValue(0)
        self.loader_thread = AppLoaderThread()
        self.loader_thread.appsLoaded.connect(self.update_apps)
        self.loader_thread.statusUpdate.connect(self.stats_label.setText)
        self.loader_thread.progressUpdate.connect(self.progress_bar.setValue)
        self.loader_thread.errorSignal.connect(self.show_notification)
        self.loader_thread.start()

    def update_apps(self, apps):
        self.apps = apps
        self.update_content()
        self.update_stats()
        self.progress_bar.setValue(100)

    def load_links(self):
        try:
            with open("links.json", "r") as f:
                links = json.load(f)
            return [item for item in links if isinstance(item, dict) and "name" in item and "url" in item]
        except (FileNotFoundError, json.JSONDecodeError):
            return [{"name": "Example", "url": "https://example.com", "category": "General", "is_favorite": False}]

    def save_links(self):
        try:
            with open("links.json", "w") as f:
                json.dump(self.links, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save links: {str(e)}")
            self.show_notification(f"Failed to save links: {str(e)}.", 3000)

    def load_recent(self):
        try:
            with open("recent.json", "r") as f:
                recent = json.load(f)
            return [item for item in recent[:50] if isinstance(item, dict) and "name" in item and "path" in item and "type" in item]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_recent(self):
        try:
            with open("recent.json", "w") as f:
                json.dump(self.recent_items, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save recent items: {str(e)}")
            self.show_notification(f"Failed to save recent items: {str(e)}.", 3000)

    def load_pinned(self):
        try:
            with open("pinned.json", "r") as f:
                pinned = json.load(f)
            return [item for item in pinned if isinstance(item, dict) and "name" in item and "path" in item and "type" in item]
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_pinned(self):
        try:
            with open("pinned.json", "w") as f:
                json.dump(self.pinned_items, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save pinned items: {str(e)}")
            self.show_notification(f"Failed to save pinned items: {str(e)}.", 3000)

    def load_settings(self):
        default_settings = {
            'theme': 'dark',
            'colors': {
                'bg': '#1e1e1e', 'fg': '#dcdcdc', 'accent': '#4682b4',
                'pane': '#252525', 'list_text': '#dcdcdc', 'list_bg': '#252525'
            },
            'font': {'family': 'Inter', 'size': 12},
            'anim_speed': 250,
            'anim_curve': 'InOutQuad',
            'icon_size': 32,
            'border_radius': 8,
            'grid_columns': 4,
            'minimize_to_tray': True,
            'show_tray_icon': True,
            'enable_animations': True,
            'hotkey': 'ctrl+alt+q',
            'cache_limit': 100
        }
        try:
            with open("settings.json", "r") as f:
                loaded_settings = json.load(f)
                if 'colors' in loaded_settings:
                    loaded_settings['colors'] = {**default_settings['colors'], **loaded_settings['colors']}
                return {**default_settings, **loaded_settings}
        except (FileNotFoundError, json.JSONDecodeError):
            return default_settings

    def save_settings(self):
        settings = {
            'theme': self.theme_mode,
            'colors': self.custom_colors,
            'font': self.font_settings,
            'anim_speed': self.anim_speed,
            'anim_curve': self.anim_curve,
            'icon_size': self.icon_size,
            'border_radius': self.border_radius,
            'grid_columns': self.grid_columns,
            'minimize_to_tray': self.minimize_to_tray,
            'show_tray_icon': self.show_tray_icon,
            'enable_animations': self.enable_animations,
            'hotkey': self.hotkey,
            'cache_limit': self.cache_limit
        }
        try:
            with open("settings.json", "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save settings: {str(e)}")
            self.show_notification(f"Failed to save settings: {str(e)}.", 3000)

    def cleanup_icon_cache(self):
        cache_size = sum(f.stat().st_size for f in self.icon_cache_dir.glob("*.png")) / (1024 * 1024)
        if cache_size > self.cache_limit:
            files = sorted(self.icon_cache_dir.glob("*.png"), key=lambda x: x.stat().st_mtime)
            while cache_size > self.cache_limit and files:
                files.pop(0).unlink()
                cache_size = sum(f.stat().st_size for f in self.icon_cache_dir.glob("*.png")) / (1024 * 1024)
            self.icon_cache.clear()

    def get_app_icon(self, shortcut_path):
        if shortcut_path in self.icon_cache:
            return self.icon_cache[shortcut_path]
        if not HAS_WIN32 or not os.path.exists(str(shortcut_path)):
            return QIcon.fromTheme("application-x-executable")

        cache_file = self.icon_cache_dir / f"{hashlib.md5(str(shortcut_path).encode()).hexdigest()}.png"
        if cache_file.exists():
            icon = QIcon(str(cache_file))
            if not icon.isNull():
                self.icon_cache[shortcut_path] = icon
                return icon

        try:
            pythoncom.CoInitialize()
            shortcut = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
            shortcut.QueryInterface(pythoncom.IID_IPersistFile).Load(str(shortcut_path))
            icon_path, icon_index = shortcut.GetIconLocation()
            if not icon_path:
                target_path = shortcut.GetPath(shell.SLGP_RAWPATH)[0]
                if os.path.exists(target_path):
                    icon_path = target_path
                else:
                    return QIcon.fromTheme("application-x-executable")

            icon = QIcon(icon_path)
            if not icon.isNull():
                pixmap = icon.pixmap(max(self.icon_size, 64))
                img = Image.fromqpixmap(pixmap)
                img.save(str(cache_file))
                self.icon_cache[shortcut_path] = icon
                self.cleanup_icon_cache()
                return icon
        except Exception as e:
            logging.debug(f"Failed to extract icon for {shortcut_path}: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

        return QIcon.fromTheme("application-x-executable")

    def filter_all(self):
        self.update_content()

    def show_settings(self):
        try:
            dialog = SettingsDialog(self)
            if self.enable_animations:
                dialog.setProperty("opacity", 0.0)
                dialog.show()
                anim = QPropertyAnimation(dialog, b"opacity")
                anim.setDuration(self.anim_speed)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(getattr(QEasingCurve, self.anim_curve))
                anim.start()
            else:
                dialog.exec_()
            self.tab_buttons[4].setChecked(False)
        except Exception as e:
            logging.error(f"Settings dialog failed: {e}")
            self.show_notification("Unable to open settings.", 3000)

    def run_selected(self):
        errors = []
        timestamp = datetime.now().isoformat()
        for name in self.selected_apps.copy():
            for category in self.apps:
                if name in self.apps[category]:
                    path = self.apps[category][name]
                    try:
                        self.launch_item(path, "app")
                        self.add_recent_item(name, path, category, "app", timestamp)
                    except Exception as e:
                        errors.append(f"Failed to open {name}: {str(e)}")
        for name in self.selected_links.copy():
            link = next((l for l in self.links if l["name"] == name), None)
            if link:
                try:
                    self.launch_item(link["url"], "link")
                    self.add_recent_item(name, link["url"], link.get("category", "General"), "link", timestamp)
                except Exception as e:
                    errors.append(f"Failed to open {name}: {str(e)}")
        for name in self.selected_recent.copy():
            item = next((i for i in self.recent_items if i["name"] == name.split(" (")[0]), None)
            if item:
                try:
                    self.launch_item(item["path"], item["type"])
                    self.add_recent_item(name.split(" (")[0], item["path"], item.get("category", "General"), item["type"], timestamp)
                except Exception as e:
                    errors.append(f"Failed to open {name}: {str(e)}")
        for name in self.selected_pinned.copy():
            item = next((i for i in self.pinned_items if i["name"] == name.split(" (")[0]), None)
            if item:
                try:
                    self.launch_item(item["path"], item["type"])
                    self.add_recent_item(name.split(" (")[0], item["path"], item.get("category", "General"), item["type"], timestamp)
                except Exception as e:
                    errors.append(f"Failed to open {name}: {str(e)}")
        if errors:
            self.show_notification("\n".join(errors), 5000)
        self.clear_selection()
        self.update_content()

    def launch_item(self, path, item_type):
        try:
            if item_type == "app":
                subprocess.Popen(path, shell=True)
            else:
                if path.startswith(("http://", "https://")):
                    webbrowser.open(path)
                else:
                    os.startfile(path)
            logging.info(f"Launched {item_type}: {path}")
            self.show_notification(f"Launched {item_type}: {Path(path).name}", 2000)
        except Exception as e:
            logging.error(f"Failed to launch {path}: {str(e)}")
            self.show_notification(f"Failed to launch {item_type}: {str(e)}.", 4000)

    def add_recent_item(self, name, path, category, item_type, timestamp):
        self.recent_items = [i for i in self.recent_items if not (i["name"] == name and i["type"] == item_type)]
        self.recent_items.insert(0, {
            "name": name,
            "path": path,
            "category": category,
            "type": item_type,
            "timestamp": timestamp,
            "is_favorite": any(i["name"] == name and i["type"] == item_type and i.get("is_favorite", False) for i in self.pinned_items + self.links)
        })
        self.recent_items = self.recent_items[:50]
        self.save_recent()
        self.update_stats()

    def pin_selected(self):
        for name in self.selected_apps:
            for category in self.apps:
                if name in self.apps[category]:
                    if not any(i["name"] == name and i["type"] == "app" for i in self.pinned_items):
                        self.pinned_items.append({"name": name, "path": self.apps[category][name], "category": category, "type": "app", "is_favorite": False})
        for name in self.selected_links:
            link = next((l for l in self.links if l["name"] == name), None)
            if link and not any(i["name"] == name and i["type"] == "link" for i in self.pinned_items):
                self.pinned_items.append({"name": name, "path": link["url"], "category": link.get("category", "General"), "type": "link", "is_favorite": link.get("is_favorite", False)})
        for name in self.selected_recent:
            item = next((i for i in self.recent_items if i["name"] == name.split(" (")[0]), None)
            if item and not any(i["name"] == name.split(" (")[0] and i["type"] == item["type"] for i in self.pinned_items):
                self.pinned_items.append({"name": name.split(" (")[0], "path": item["path"], "category": item.get("category", "General"), "type": item["type"], "is_favorite": item.get("is_favorite", False)})
        self.save_pinned()
        self.update_content()
        self.show_notification("Items pinned.", 2000)

    def unpin_selected(self):
        self.pinned_items = [item for item in self.pinned_items if item["name"] not in [n.split(" (")[0] for n in self.selected_pinned]]
        self.save_pinned()
        self.update_content()
        self.show_notification("Items unpinned.", 2000)

    def clear_selection(self):
        self.content_list.clearSelection()
        self.selected_apps.clear()
        self.selected_links.clear()
        self.selected_recent.clear()
        self.selected_pinned.clear()
        self.update_stats()

    def add_link_popup(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Link")
        dialog.setFixedSize(350, 240)
        dialog.setStyleSheet(f"""
            QDialog {{ background: {self.custom_colors['bg']}; border: 1px solid {self.custom_colors['accent']}; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); }}
            QLabel {{ color: {self.custom_colors['fg']}; font: bold 13px Inter; }}
            QLineEdit {{ background: {self.custom_colors['pane']}; color: {self.custom_colors['fg']}; border: 1px solid {self.custom_colors['accent']}; border-radius: 8px; padding: 6px; font: 12px Inter; }}
            QPushButton {{ background: {self.custom_colors['accent']}; color: #ffffff; border-radius: 8px; padding: 8px; font: bold 12px Inter; }}
            QPushButton:hover {{ background: #5a9bd4; }}
        """)
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Link Name:"))
        name_entry = QLineEdit()
        name_entry.setToolTip("Enter the name for the link")
        layout.addWidget(name_entry)
        layout.addWidget(QLabel("URL or Path:"))
        url_entry = QLineEdit()
        url_entry.setToolTip("Enter the URL or file path")
        layout.addWidget(url_entry)
        save_btn = QPushButton("Save")
        save_btn.setToolTip("Save link")
        save_btn.clicked.connect(lambda: self.save_link(dialog, name_entry.text(), url_entry.text(), "General"))
        layout.addWidget(save_btn)
        if self.enable_animations:
            dialog.setProperty("opacity", 0.0)
            dialog.show()
            anim = QPropertyAnimation(dialog, b"opacity")
            anim.setDuration(self.anim_speed)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(getattr(QEasingCurve, self.anim_curve))
            anim.start()
        else:
            dialog.exec_()

    def save_link(self, dialog, name, url, category):
        if not name.strip() or not url.strip():
            self.show_notification("Please enter name and URL.", 3000)
            return
        if any(link["name"] == name.strip() for link in self.links):
            self.show_notification("Link name already exists.", 3000)
            return
        self.links.append({"name": name.strip(), "url": url.strip(), "category": category, "is_favorite": False})
        self.save_links()
        self.update_content()
        self.show_notification("Link added.", 2000)
        dialog.accept()

    def delete_selected(self):
        if self.selected_links:
            for link_name in self.selected_links.copy():
                self.links = [link for link in self.links if link["name"] != link_name]
                self.recent_items = [item for item in self.recent_items if item["name"] != link_name or item["type"] != "link"]
                self.pinned_items = [item for item in self.pinned_items if item["name"] != link_name or item["type"] != "link"]
            self.save_links()
            self.save_recent()
            self.save_pinned()
            self.update_content()
            self.show_notification("Links deleted.", 2000)

    def edit_link_category(self):
        if self.selected_links:
            link_name = next(iter(self.selected_links))
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit Category")
            dialog.setFixedSize(350, 200)
            dialog.setStyleSheet(f"""
                QDialog {{ background: {self.custom_colors['bg']}; border: 1px solid {self.custom_colors['accent']}; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); }}
                QLabel {{ color: {self.custom_colors['fg']}; font: bold 13px Inter; }}
                QComboBox {{ background: {self.custom_colors['pane']}; color: {self.custom_colors['fg']}; border: 1px solid {self.custom_colors['accent']}; border-radius: 8px; padding: 6px; font: 12px Inter; }}
                QPushButton {{ background: {self.custom_colors['accent']}; color: #ffffff; border-radius: 8px; padding: 8px; font: bold 12px Inter; }}
                QPushButton:hover {{ background: #5a9bd4; }}
            """)
            layout = QVBoxLayout(dialog)
            layout.setSpacing(12)
            layout.addWidget(QLabel("Category:"))
            category_combo = QComboBox()
            category_combo.addItems(["General"] + sorted({l.get("category", "General") for l in self.links}))
            category_combo.setEditable(True)
            category_combo.setToolTip("Select or enter a category")
            layout.addWidget(category_combo)
            save_btn = QPushButton("Save")
            save_btn.setToolTip("Save category changes")
            save_btn.clicked.connect(lambda: self.save_link_category(dialog, link_name, category_combo.currentText()))
            layout.addWidget(save_btn)
            if self.enable_animations:
                dialog.setProperty("opacity", 0.0)
                dialog.show()
                anim = QPropertyAnimation(dialog, b"opacity")
                anim.setDuration(self.anim_speed)
                anim.setStartValue(0.0)
                anim.setEndValue(1.0)
                anim.setEasingCurve(getattr(QEasingCurve, self.anim_curve))
                anim.start()
            else:
                dialog.exec_()

    def save_link_category(self, dialog, link_name, category):
        try:
            for link in self.links:
                if link["name"] == link_name:
                    link["category"] = category.strip() or "General"
            for item in self.recent_items + self.pinned_items:
                if item["name"] == link_name and item["type"] == "link":
                    item["category"] = category.strip() or "General"
            self.save_links()
            self.save_recent()
            self.save_pinned()
            self.update_content()
            self.show_notification(f"Category updated to {category}.", 2000)
            dialog.accept()
        except Exception as e:
            logging.error(f"Failed to update category: {str(e)}")
            self.show_notification(f"Error updating category: {str(e)}.", 3000)

    def copy_link_url(self):
        try:
            if self.selected_links:
                link = next((l for l in self.links if l["name"] in self.selected_links), None)
                if link:
                    QApplication.clipboard().setText(link["url"])
                    self.show_notification("URL copied to clipboard.", 2000)
        except Exception as e:
            logging.error(f"Failed to copy URL: {str(e)}")
            self.show_notification(f"Error copying URL: {str(e)}.", 3000)

    def open_app_location(self):
        try:
            for name in self.selected_apps:
                for category in self.apps:
                    if name in self.apps[category]:
                        path = self.apps[category][name]
                        folder = str(Path(path).parent)
                        subprocess.Popen(f'explorer.exe /select,"{path}"', shell=True)
                        self.show_notification(f"Opened location for {name}.", 2000)
                        break
        except Exception as e:
            logging.error(f"Failed to open app location: {str(e)}")
            self.show_notification(f"Error opening location: {str(e)}.", 3000)

    def clear_recent(self):
        try:
            self.recent_items = []
            self.save_recent()
            self.update_content()
            self.show_notification("Recent items cleared.", 2000)
        except Exception as e:
            logging.error(f"Failed to clear recent items: {str(e)}")
            self.show_notification(f"Error clearing recent items: {str(e)}.", 3000)

    def refresh_apps(self):
        try:
            self.load_apps_async()
            self.show_notification("Apps refreshed.", 2000)
        except Exception as e:
            logging.error(f"Failed to refresh apps: {str(e)}")
            self.show_notification(f"Error refreshing apps: {str(e)}.", 3000)

    def show_notification(self, message, duration=3000):
        try:
            self.notification_widget.show_message(message, duration)
        except Exception as e:
            logging.error(f"Failed to show notification: {str(e)}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.title_bar.geometry().contains(event.pos()):
            self.drag_pos = event.globalPos() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = None
            event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        try:
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith(('.lnk', '.url')):
                    name = Path(path).stem
                    category = "Dropped"
                    if path.lower().endswith('.url'):
                        with open(path, 'r') as f:
                            content = f.read()
                            import re
                            url_match = re.search(r'URL=(.+)', content)
                            if url_match:
                                self.links.append({"name": name, "url": url_match.group(1), "category": category, "is_favorite": False})
                                self.save_links()
                    else:
                        self.add_recent_item(name, path, category, "app", datetime.now().isoformat())
                    self.show_notification(f"Added {name}.", 2000)
            self.update_content()
        except Exception as e:
            logging.error(f"Failed to process dropped item: {str(e)}")
            self.show_notification(f"Error adding item: {str(e)}.", 3000)

    def toggle_maximize(self):
        if self.is_maximized:
            self.showNormal()
            self.is_maximized = False
        else:
            self.showMaximized()
            self.is_maximized = True

    def close_window(self):
        if self.minimize_to_tray:
            self.hide()
        else:
            QApplication.quit()

    def closeEvent(self, event):
        if self.minimize_to_tray:
            event.ignore()
            self.hide()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    launcher = AppLauncher()
    launcher.show()
    sys.exit(app.exec_())
