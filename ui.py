"""
ui.py — SimpleLog Material Design dark UI (PyQt6)
"""

from __future__ import annotations

import json
import math
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from PyQt6.QtCore import (
    QAbstractListModel,
    QEvent,
    QModelIndex,
    QPoint,
    QRect,
    QRectF,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDesktopServices,
    QFontMetrics,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPalette,
    QPixmap,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QStyle,
    QStyledItemDelegate,
    QTabBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import i18n

try:
    from PyQt6.QtCore import QByteArray
    from PyQt6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

import azure_utils
import cloudwatch
import datadog_utils
import docker_utils
import elastic_utils
import flyio_utils
import gcp_utils
import kubernetes_utils
import loki_utils
import profiles_store
import railway_utils
import ssh_utils
import vercel_utils
from workers import (
    AzureWorker,
    DatadogWorker,
    DockerComposeWorker,
    DockerContainerWorker,
    DockerExecFileWorker,
    ElasticWorker,
    FileWorker,
    FlyioWorker,
    GCPWorker,
    KubernetesWorker,
    LokiWorker,
    RailwayWorker,
    SSHWorker,
    StdinWorker,
    TailWorker,
    VercelWorker,
)

# ── SVG icon data ──────────────────────────────────────────────────────────────

_SVG_CLOUD = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M19.35 10.04A7.49 7.49 0 0 0 12 4'
    'C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14'
    'c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5'
    ' 0-2.64-2.05-4.78-4.65-4.96z"/>'
    "</svg>"
)

_SVG_FOLDER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2'
    'L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z'
    'm0 12H4V8h16v10z"/>'
    "</svg>"
)

_SVG_WS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5'
    'c0-1.1-.9-2-2-2z"/>'
    "</svg>"
)

_SVG_SSH = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M20 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16'
    'c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zM4 18V8h16v10H4zm2-3h4v-2H6v2z'
    'm6 0h4v-2h-4v2zM6 11h2V9H6v2zm4 0h4V9h-4v2zm6 0h2V9h-2v2z"/>'
    "</svg>"
)

_SVG_DOCKER = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M13.98 8H10V6h3.98V8zm-5.98 0H4.02V6H8V8z'
    'm5.98 2.03H10V8.03h3.98v2zM8 10.03H4.02V8.03H8v2z'
    'm5.98 2H10v-2h3.98v2zM8 12.03H4.02v-2H8v2z'
    'm10 2.03h-4V12h4V14zm4 0h-3.98v2H18v-2z'
    'm3.18 2.5C20.76 6 20 4.53 20 4.53s-1 .47-1.82 1.97'
    'c-.56.99-.18 2.5-.18 2.5H23s.5-1.5-.82-2.5z'
    'M2 14c0 2.21 2.69 4 6 4h8c3.31 0 6-1.79 6-4H2z"/>'
    "</svg>"
)

_SVG_VERCEL = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M12 2L2 19.5h20L12 2z"/>'
    "</svg>"
)

_SVG_GCP = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z'
    'm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z'
    'm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2'
    'c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>'
    "</svg>"
)

_SVG_AZURE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M13.05 4.24L6.56 18.05l14.36.02-1.52-1.46-9.1-1.84 5.2-4.62-3.45-5.91z'
    'M11.4 6.22l-7.88 12.1 2.57-.01 5.29-8.46-.34-1.24 .36-2.39z"/>'
    "</svg>"
)

_SVG_LOKI = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M4 5h2v14H4V5zM8 6h12v2H8V6zM8 11h9v2H8v-2zM8 16h12v2H8v-2z"/>'
    "</svg>"
)

_SVG_DATADOG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M12 2l8.5 4.9v10.2L12 22l-8.5-4.9V6.9L12 2z"/>'
    "</svg>"
)

_SVG_ELASTIC = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z'
    'm1 15H7v-2h6v2zm4-4H7V9h10v2z"/>'
    "</svg>"
)

_SVG_RAILWAY = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M4 16h16v2H4v-2zM4 6h16v2H4V6zm4 5h8v2H8v-2z'
    'M6 19l-2 3h2l1-1.5L8 22h2l-2-3H6zm10 0l-2 3h2l1-1.5 1 1.5h2l-2-3h-2z"/>'
    "</svg>"
)

_SVG_FLYIO = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M12 2C8.13 2 5 5.13 5 9c0 2.74 1.54 5.12 3.82 6.38'
    'L8 20h2l.5-3h3l.5 3h2l-.82-4.62C17.46 14.12 19 11.74 19 9c0-3.87-3.13-7-7-7z'
    'm0 2c2.76 0 5 2.24 5 5s-2.24 5-5 5-5-2.24-5-5 2.24-5 5-5z"/>'
    "</svg>"
)

_SVG_KUBERNETES = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M12 2l9 4.5v9L12 20l-9-4.5v-9L12 2zm0 2.18L5 7.64v8.72'
    'L12 19.82l7-3.46V7.64L12 4.18zm-1 3.32h2v5l-1 1-1-1V7.5zm0 7h2v2h-2v-2z"/>'
    "</svg>"
)

_SVG_REMOTE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2'
    'C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0z'
    'm-4-4 2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/>'
    "</svg>"
)

_SVG_TRASH = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12z'
    'M8 9h8v10H8V9zm7.5-5-1-1h-5l-1 1H5v2h14V4z"/>'
    "</svg>"
)

_SVG_STOP_SQ = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<rect fill="{color}" x="6" y="6" width="12" height="12" rx="2" ry="2"/>'
    "</svg>"
)

_SVG_CLOSE_X = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path stroke="{color}" stroke-width="2.5" stroke-linecap="round"'
    ' fill="none" d="M5 5L19 19M19 5L5 19"/>'
    "</svg>"
)

_SVG_CHEVRON_LEFT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path fill="{color}" d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>'
    "</svg>"
)

_SVG_CHEVRON_RIGHT = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">'
    '<path fill="{color}" d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>'
    "</svg>"
)


def _svg_icon(svg_tmpl: str, color: str, size: int = 16) -> QIcon:
    """Render an SVG template (with {color} placeholder) to a QIcon."""
    if not _HAS_SVG:
        return QIcon()
    svg = svg_tmpl.replace("{color}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    renderer.render(p)
    p.end()
    return QIcon(pm)


# ── Colour constants ───────────────────────────────────────────────────────────

C_BG         = "#0d0d10"
C_RAIL       = "#080810"
C_SIDE       = "#111116"
C_PANEL      = "#14141a"
C_CARD       = "#1a1a24"
C_STATUS     = "#090910"
C_BORDER     = "rgba(255,255,255,18)"
C_ACCENT     = "#5b8fff"
C_ACCENT_DIM = "rgba(91,143,255,38)"
C_TEXT       = "#d4d4e0"
C_MUTED      = "#52526a"
C_SEL_BG     = "rgba(91,143,255,31)"
C_ERR        = "#f07878"
C_WARN       = "#f0c060"
C_INFO       = "#56cf80"
C_DEBUG      = "#5b8fff"
C_TRACE      = "#b07cf0"
C_TS         = "#50c8dc"

# Backwards-compat aliases
C_TOOLBAR  = C_PANEL
C_DIVIDER  = C_BORDER


# ── apply_style ────────────────────────────────────────────────────────────────

def apply_style(app: QApplication) -> None:
    """Apply Material Design dark palette and global stylesheet."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(C_BG))
    palette.setColor(QPalette.ColorRole.WindowText,      QColor(C_TEXT))
    palette.setColor(QPalette.ColorRole.Base,            QColor(C_CARD))
    palette.setColor(QPalette.ColorRole.AlternateBase,   QColor(C_BG))
    palette.setColor(QPalette.ColorRole.Text,            QColor(C_TEXT))
    palette.setColor(QPalette.ColorRole.Button,          QColor(C_CARD))
    palette.setColor(QPalette.ColorRole.ButtonText,      QColor(C_TEXT))
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(C_ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(C_MUTED))
    palette.setColor(QPalette.ColorRole.BrightText,      QColor(C_ERR))
    app.setPalette(palette)

    app.setStyleSheet(f"""
        QWidget {{
            background-color: {C_BG};
            color: {C_TEXT};
            font-family: "Inter", sans-serif;
            font-size: 12px;
        }}
        QLineEdit, QComboBox, QSpinBox {{
            background: {C_BG};
            border: 1px solid rgba(255,255,255,26);
            border-radius: 5px;
            padding: 6px 10px;
            color: {C_TEXT};
            min-height: 20px;
            font-size: 12px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border-color: {C_ACCENT};
            border-width: 1px;
        }}
        QPushButton {{
            background-color: transparent;
            border: 1px solid {C_BORDER};
            border-radius: 6px;
            padding: 7px 14px;
            color: {C_MUTED};
            font-size: 12px;
        }}
        QPushButton:hover {{
            background-color: rgba(255,255,255,10);
            color: {C_TEXT};
        }}
        QPushButton#primary {{
            background-color: {C_ACCENT};
            color: #000000;
            border: none;
            font-weight: bold;
        }}
        QPushButton#primary:hover {{
            background-color: #7aa3ff;
        }}
        QPushButton#danger {{
            color: {C_ERR};
            border-color: rgba(240,120,120,77);
            background: transparent;
        }}
        QPushButton#danger:hover {{
            background: rgba(240,120,120,20);
        }}
        QPushButton:disabled {{
            background-color: rgba(91,143,255,38);
            color: {C_MUTED};
            border: none;
        }}
        QListWidget {{
            background: {C_BG};
            border: 1px solid {C_BORDER};
            border-radius: 6px;
            font-family: "JetBrains Mono", monospace;
            font-size: 11px;
        }}
        QListWidget::item {{
            padding: 6px 10px;
            border-radius: 4px;
        }}
        QListWidget::item:selected {{
            background: {C_SEL_BG};
            color: {C_ACCENT};
        }}
        QListWidget::item:hover {{
            background: rgba(255,255,255,10);
        }}
        QTabWidget::pane {{
            border: none;
        }}
        QTabBar::tab {{
            background: {C_PANEL};
            border: none;
            border-right: 1px solid {C_BORDER};
            padding: 0 14px;
            min-height: 38px;
            color: {C_MUTED};
            font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background: {C_BG};
            color: {C_TEXT};
            border-top: 2px solid {C_ACCENT};
        }}
        QTabBar::tab:hover:!selected {{
            color: {C_TEXT};
            background: rgba(255,255,255,5);
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background: {C_CARD};
            border: 1px solid {C_BORDER};
            selection-background-color: {C_SEL_BG};
            selection-color: {C_ACCENT};
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255,255,255,31);
            border-radius: 3px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: rgba(91,143,255,128);
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background: rgba(255,255,255,31);
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: rgba(91,143,255,128);
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        QCheckBox {{
            spacing: 6px;
            color: {C_MUTED};
            font-size: 11px;
        }}
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border: 1px solid {C_BORDER};
            border-radius: 3px;
            background: {C_BG};
        }}
        QCheckBox::indicator:checked {{
            background: {C_ACCENT};
            border-color: {C_ACCENT};
        }}
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QToolTip {{
            background: {C_CARD};
            color: {C_TEXT};
            border: 1px solid {C_BORDER};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 11px;
        }}
        QStatusBar {{
            background: {C_STATUS};
            border-top: 1px solid {C_BORDER};
            color: {C_MUTED};
            font-family: "JetBrains Mono", monospace;
            font-size: 11px;
        }}
        QMenuBar {{
            background: {C_RAIL};
            color: {C_TEXT};
            border-bottom: 1px solid {C_BORDER};
            font-size: 12px;
            padding: 2px 4px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 5px 12px;
            border-radius: 4px;
        }}
        QMenuBar::item:selected {{
            background: rgba(255,255,255,15);
            color: {C_ACCENT};
        }}
        QMenu {{
            background: {C_CARD};
            border: 1px solid {C_BORDER};
            border-radius: 8px;
            padding: 4px 0;
            font-size: 12px;
        }}
        QMenu::item {{
            padding: 8px 24px 8px 16px;
            color: {C_TEXT};
        }}
        QMenu::item:selected {{
            background: {C_SEL_BG};
            color: {C_ACCENT};
        }}
        QMenu::separator {{
            height: 1px;
            background: {C_BORDER};
            margin: 4px 8px;
        }}
    """)


# ── Tab bar with close-button-on-active-tab only ──────────────────────────────

class _TabCloseBtn(QPushButton):
    """14×14 × close button for tabs — turns red on hover."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setFlat(True)
        self.setStyleSheet(
            "QPushButton { background: transparent; border: none;"
            " border-radius: 3px; padding: 0; }"
            "QPushButton:hover { background: rgba(240,120,120,25); }"
        )
        self.setIcon(_svg_icon(_SVG_CLOSE_X, C_MUTED, 10))
        self.setIconSize(QSize(10, 10))



class _SLTabBar(QTabBar):
    """QTabBar that shows the close button only on the active tab."""

    def tabInserted(self, index: int) -> None:  # noqa: N802
        super().tabInserted(index)
        tab_bar = self
        btn = _TabCloseBtn(self)

        def _req(_=False, _tb=tab_bar, _b=btn):
            for i in range(_tb.count()):
                if _tb.tabButton(i, QTabBar.ButtonPosition.RightSide) is _b:
                    _tb.tabCloseRequested.emit(i)
                    break

        btn.clicked.connect(_req)
        self.setTabButton(index, QTabBar.ButtonPosition.RightSide, btn)
        self._sync_close_buttons()

    def tabRemoved(self, index: int) -> None:  # noqa: N802
        super().tabRemoved(index)
        QTimer.singleShot(0, self._sync_close_buttons)

    def _sync_close_buttons(self) -> None:
        current = self.currentIndex()
        for i in range(self.count()):
            btn = self.tabButton(i, QTabBar.ButtonPosition.RightSide)
            if btn:
                btn.setVisible(i == current)


class _SLTabWidget(QTabWidget):
    """QTabWidget using _SLTabBar so the × only appears on the active tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sl_bar = _SLTabBar(self)
        self.setTabBar(self._sl_bar)
        self.currentChanged.connect(lambda _: self._sl_bar._sync_close_buttons())


# ── Sidebar edge toggle buttons ────────────────────────────────────────────────

class _SidebarEdgeBtn(QPushButton):
    """20×40 floating edge tab that collapses/expands a sidebar panel."""

    def __init__(self, side: str, parent=None):
        super().__init__(parent)
        self._side = side  # 'left' or 'right'
        self._svg = _SVG_CHEVRON_LEFT
        self._hovered = False
        self.setFixedSize(20, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style()

    def set_svg(self, svg: str) -> None:
        self._svg = svg
        self._apply_style()

    def _apply_style(self) -> None:
        bg = C_ACCENT_DIM if self._hovered else C_CARD
        color = C_ACCENT if self._hovered else C_MUTED
        if self._side == "left":
            border_r = (
                "border-top-left-radius: 0px; border-bottom-left-radius: 0px;"
                " border-top-right-radius: 6px; border-bottom-right-radius: 6px;"
            )
            border_css = f"border: 1px solid {C_BORDER}; border-left: none;"
        else:
            border_r = (
                "border-top-left-radius: 6px; border-bottom-left-radius: 6px;"
                " border-top-right-radius: 0px; border-bottom-right-radius: 0px;"
            )
            border_css = f"border: 1px solid {C_BORDER}; border-right: none;"
        self.setStyleSheet(
            f"QPushButton {{ background: {bg}; {border_css} {border_r} padding: 0; }}"
        )
        self.setIcon(_svg_icon(self._svg, color, 10))
        self.setIconSize(QSize(10, 10))

    def enterEvent(self, event) -> None:
        self._hovered = True
        self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        self._apply_style()
        super().leaveEvent(event)


# ── NavButton ──────────────────────────────────────────────────────────────────

class NavButton(QAbstractButton):
    """40×40 nav rail icon button with rounded-rect highlight when checked."""

    def __init__(self, svg_template: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 40)
        self.setToolTip(tooltip)
        self._svg_template = svg_template
        self._renderer_checked: QSvgRenderer | None = None
        self._renderer_unchecked: QSvgRenderer | None = None
        if _HAS_SVG:
            self._renderer_checked   = self._make_renderer(C_ACCENT)
            self._renderer_unchecked = self._make_renderer(C_MUTED)

    def _make_renderer(self, color: str) -> QSvgRenderer:
        svg = self._svg_template.replace("{color}", color)
        renderer = QSvgRenderer()
        renderer.load(QByteArray(svg.encode()))
        return renderer

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # Rounded-rect background when checked
        if self.isChecked():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(91, 143, 255, 38)))  # C_ACCENT_DIM
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, 8, 8)
            p.drawPath(path)
        elif self.underMouse():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 255, 255, 12)))
            path = QPainterPath()
            path.addRoundedRect(0, 0, w, h, 8, 8)
            p.drawPath(path)

        # Icon
        icon_size = 18
        ix = (w - icon_size) // 2
        iy = (h - icon_size) // 2
        try:
            if _HAS_SVG:
                renderer = self._renderer_checked if self.isChecked() else self._renderer_unchecked
                if renderer and renderer.isValid():
                    renderer.render(p, QRectF(ix, iy, icon_size, icon_size))
                    return

            # Fallback: draw coloured square placeholder
            color = C_ACCENT if self.isChecked() else C_MUTED
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(color)))
            p.drawRoundedRect(ix, iy, icon_size, icon_size, 4, 4)
        finally:
            p.end()

    def enterEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.update()
        super().leaveEvent(event)

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(40, 40)


# ── NavRail ────────────────────────────────────────────────────────────────────

# ── Workspace persistence ──────────────────────────────────────────────────────

class WorkspaceManager:
    _path = Path.home() / ".config" / "simplelog" / "workspaces.json"

    @classmethod
    def load(cls) -> list[dict]:
        try:
            return json.loads(cls._path.read_text(encoding="utf-8"))
        except Exception:
            return []

    @classmethod
    def save(cls, workspaces: list[dict]) -> None:
        cls._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cls._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(workspaces, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(cls._path)

    @classmethod
    def add(cls, ws: dict) -> list[dict]:
        workspaces = cls.load()
        workspaces.append(ws)
        cls.save(workspaces)
        return workspaces

    @classmethod
    def remove(cls, ws_id: str) -> list[dict]:
        workspaces = [w for w in cls.load() if w["id"] != ws_id]
        cls.save(workspaces)
        return workspaces

    @classmethod
    def rename(cls, ws_id: str, name: str) -> list[dict]:
        workspaces = cls.load()
        for w in workspaces:
            if w["id"] == ws_id:
                w["name"] = name
                break
        cls.save(workspaces)
        return workspaces


# ── NavRail ────────────────────────────────────────────────────────────────────

class NavRail(QWidget):
    """52px left navigation rail."""

    index_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(52)
        self.setStyleSheet(
            f"background: {C_RAIL};"
            f"border-right: 1px solid {C_BORDER};"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(2)

        # Logo
        logo = QLabel("SL")
        logo.setFixedSize(32, 32)
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(
            f"background: {C_ACCENT}; color: #000; font-weight: 800;"
            "font-size: 12px; border-radius: 8px;"
        )
        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(0, 0, 0, 0)
        logo_row.addStretch()
        logo_row.addWidget(logo)
        logo_row.addStretch()
        layout.addLayout(logo_row)
        layout.addSpacing(10)

        # Divider
        div = QFrame()
        div.setFixedSize(28, 1)
        div.setStyleSheet(f"background: {C_BORDER}; border: none;")
        div_row = QHBoxLayout()
        div_row.setContentsMargins(0, 0, 0, 0)
        div_row.addStretch()
        div_row.addWidget(div)
        div_row.addStretch()
        layout.addLayout(div_row)
        layout.addSpacing(6)

        # Buttons
        self._buttons: list[NavButton] = []

        self._btn_remote = NavButton(_SVG_REMOTE, i18n.tr("remote_title"))
        self._btn_file   = NavButton(_SVG_FOLDER, "Open log file")
        self._btn_ws     = NavButton(_SVG_WS,     "Workspaces")

        for btn in (self._btn_remote, self._btn_file, self._btn_ws):
            btn.clicked.connect(self._on_button_clicked)
            btn_row = QHBoxLayout()
            btn_row.setContentsMargins(0, 0, 0, 0)
            btn_row.addStretch()
            btn_row.addWidget(btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)
            self._buttons.append(btn)

        layout.addStretch()

        # Select first by default
        self._btn_remote.setChecked(True)

    def _on_button_clicked(self):
        sender = self.sender()
        for i, btn in enumerate(self._buttons):
            btn.setChecked(btn is sender)
        idx = self._buttons.index(sender)
        self.index_changed.emit(idx)


# ── make_card helper ───────────────────────────────────────────────────────────

def make_card(title: str | None = None) -> tuple[QFrame, QVBoxLayout, QLabel | None]:
    """Return (frame, layout, title_label | None) for a sidebar card."""
    frame = QFrame()
    frame.setStyleSheet(
        f"QFrame {{ background: {C_CARD}; border: 1px solid rgba(255,255,255,18);"
        f" border-radius: 10px; }}"
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(6)
    title_label: QLabel | None = None
    if title:
        title_label = QLabel(title.upper())
        title_label.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 10px; font-weight: 700;"
            " border: none; background: transparent; margin-bottom: 2px;"
        )
        layout.addWidget(title_label)
    return frame, layout, title_label


# ── Primary button helper ─────────────────────────────────────────────────────

def _primary_btn(text: str = "") -> QPushButton:
    """Create a styled primary (accent-coloured) button."""
    btn = QPushButton(text)
    btn.setObjectName("primary")
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {C_ACCENT};
            color: #000000;
            border: none;
            border-radius: 6px;
            padding: 7px 14px;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #7aa3ff;
        }}
        QPushButton:pressed {{
            background-color: #4a7aee;
        }}
        QPushButton:disabled {{
            background-color: rgba(91,143,255,38);
            color: {C_MUTED};
        }}
    """)
    return btn


def _ghost_btn(text: str = "") -> QPushButton:
    """Create a ghost (outline) button."""
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {C_TEXT};
            border: 1px solid rgba(255,255,255,35);
            border-radius: 6px;
            padding: 7px 14px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background: rgba(255,255,255,10);
            border-color: rgba(255,255,255,60);
        }}
        QPushButton:disabled {{
            color: {C_MUTED};
            border-color: rgba(255,255,255,15);
        }}
    """)
    return btn


class _ProfileBar(QWidget):
    """Compact saved-profile row: [combo ▾] [Load] [✕]
    Hidden automatically when no profiles are saved.
    Pass wrapper= to also show/hide an outer container."""

    profile_loaded = pyqtSignal(dict)

    def __init__(self, service: str, wrapper: QWidget | None = None, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._wrapper = wrapper

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        self._combo = QComboBox()
        self._combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._combo.setMinimumWidth(100)
        self._combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 3px 6px; font-size: 11px;"
        )

        self._load_btn = QPushButton(i18n.tr("remote_open"))
        self._load_btn.setFixedWidth(48)
        self._load_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_ACCENT}; border: 1px solid {C_ACCENT};"
            f"border-radius: 4px; padding: 3px 6px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: rgba(91,143,255,20); }}"
        )
        self._load_btn.clicked.connect(self._on_load)

        self._del_btn = QPushButton("✕")
        self._del_btn.setFixedWidth(28)
        self._del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_ERR}; border: 1px solid {C_ERR};"
            f"border-radius: 4px; padding: 3px 4px; font-size: 11px; }}"
            f"QPushButton:hover {{ background: rgba(240,120,120,20); }}"
        )
        self._del_btn.clicked.connect(self._on_delete)

        lay.addWidget(self._combo, 1)
        lay.addWidget(self._load_btn)
        lay.addWidget(self._del_btn)

        self.reload()

    def reload(self) -> None:
        self._combo.clear()
        for p in profiles_store.load_all(self._service):
            self._combo.addItem(p["name"], userData=p)
        vis = self._combo.count() > 0
        self.setVisible(vis)
        if self._wrapper is not None:
            self._wrapper.setVisible(vis)

    def _on_load(self) -> None:
        p = self._combo.currentData()
        if p:
            self.profile_loaded.emit(p)

    def _on_delete(self) -> None:
        p = self._combo.currentData()
        if not p:
            return
        profiles_store.delete(self._service, p["name"])
        self.reload()


def _danger_btn(text: str = "") -> QPushButton:
    """Create a danger (red outline) button."""
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {C_ERR};
            border: 1px solid rgba(240,120,120,77);
            border-radius: 6px;
            padding: 7px 14px;
            font-size: 12px;
        }}
        QPushButton:hover {{
            background: rgba(240,120,120,20);
        }}
    """)
    return btn


# ── Open-mode segmented button widget ─────────────────────────────────────────

class OpenModeWidget(QWidget):
    """Segmented button group: new tab / vertical split / horizontal split."""

    _MODES = ("tab", "vertical", "horizontal")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 4, 0, 0)
        vbox.setSpacing(6)

        self._lbl = QLabel()
        self._lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; font-weight: 600;"
            " background: transparent; border: none;"
        )
        vbox.addWidget(self._lbl)

        # Segmented button container
        seg = QFrame()
        seg.setStyleSheet(
            f"QFrame {{ background: {C_BG}; border: 1px solid rgba(255,255,255,18);"
            f" border-radius: 6px; }}"
        )
        seg_layout = QVBoxLayout(seg)
        seg_layout.setContentsMargins(0, 0, 0, 0)
        seg_layout.setSpacing(0)

        self._grp = QButtonGroup(self)
        self._btns: dict[str, QPushButton] = {}
        n = len(self._MODES)
        for idx, mode in enumerate(self._MODES):
            btn = QPushButton()
            btn.setCheckable(True)
            if idx == 0:
                r = ("border-top-left-radius: 5px; border-top-right-radius: 5px;"
                     " border-bottom-left-radius: 3px; border-bottom-right-radius: 3px;")
            elif idx == n - 1:
                r = ("border-top-left-radius: 3px; border-top-right-radius: 3px;"
                     " border-bottom-left-radius: 5px; border-bottom-right-radius: 5px;")
            else:
                r = "border-radius: 3px;"
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {C_MUTED};
                    font-size: 12px;
                    padding: 6px 10px;
                    text-align: left;
                    {r}
                }}
                QPushButton:checked {{
                    background: rgba(91,143,255,38);
                    color: {C_ACCENT};
                    font-weight: 600;
                }}
                QPushButton:hover:!checked {{
                    background: rgba(255,255,255,10);
                    color: {C_TEXT};
                }}
            """)
            self._grp.addButton(btn, idx)
            seg_layout.addWidget(btn)
            self._btns[mode] = btn

        self._btns["tab"].setChecked(True)
        vbox.addWidget(seg)

        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))
        self.retranslate()

    def get_mode(self) -> str:
        for mode, btn in self._btns.items():
            if btn.isChecked():
                return mode
        return "tab"

    def retranslate(self) -> None:
        self._lbl.setText(i18n.tr("open_as").upper())
        self._btns["tab"].setText(i18n.tr("open_mode_tab"))
        self._btns["vertical"].setText(i18n.tr("open_mode_vertical"))
        self._btns["horizontal"].setText(i18n.tr("open_mode_horizontal"))


# ── CloudWatchPanel ────────────────────────────────────────────────────────────

class CloudWatchPanel(QWidget):
    open_tab = pyqtSignal(dict, str)  # (cfg, split_mode)

    _REGIONS = [
        "us-east-1", "us-east-2", "us-west-1", "us-west-2",
        "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1",
        "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
        "ap-south-1", "ca-central-1", "sa-east-1",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client = None
        self._all_groups: list[str] = []
        self._build_ui()
        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setStyleSheet(f"background: {C_SIDE};")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 16, 12, 16)
        vbox.setSpacing(12)

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 15px; font-weight: 700;"
            "background: transparent; border: none; margin-bottom: 4px;"
        )
        vbox.addWidget(self._title_lbl)

        # ── Saved configs card ────────────────────────────────────────────────
        saved_card_cw, saved_lay_cw, _ = make_card(i18n.tr("saved_configs"))
        self._cw_profile_bar = _ProfileBar("cloudwatch", wrapper=saved_card_cw)
        self._cw_profile_bar.profile_loaded.connect(self._load_cw_profile)
        saved_lay_cw.addWidget(self._cw_profile_bar)
        vbox.addWidget(saved_card_cw)

        # ── Connection card ───────────────────────────────────────────────────
        card, cl, self._lbl_connection = make_card(i18n.tr("new_config"))
        self._connection_card_lay = cl

        self._lbl_auth_mode = _field_label("")
        self._auth_mode_combo = QComboBox()
        self._auth_mode_combo.currentIndexChanged.connect(self._on_auth_mode_changed)
        cl.addWidget(self._lbl_auth_mode)
        cl.addWidget(self._auth_mode_combo)

        profiles = cloudwatch.list_profiles()
        self.profile_combo = QComboBox()
        self.profile_combo.addItem("(default)")
        self.profile_combo.addItems(list(profiles))
        self._lbl_profile = _field_label("")
        self._profile_widgets = [self._lbl_profile, self.profile_combo]
        cl.addWidget(self._lbl_profile)
        cl.addWidget(self.profile_combo)

        self.access_key_input = QLineEdit()
        self.secret_key_input = QLineEdit()
        self.secret_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._lbl_access_key = _field_label("")
        self._lbl_secret_key = _field_label("")
        self._key_widgets = [
            self._lbl_access_key, self.access_key_input,
            self._lbl_secret_key, self.secret_key_input,
        ]
        for w in self._key_widgets:
            cl.addWidget(w)
            w.setVisible(False)

        # Region section — hidden until credentials validated
        self._region_section = QWidget()
        rs_lay = QVBoxLayout(self._region_section)
        rs_lay.setContentsMargins(0, 0, 0, 0)
        rs_lay.setSpacing(4)
        self._lbl_region = _field_label("")
        self.region_combo = QComboBox()
        self.region_combo.addItems(self._REGIONS)
        self.region_combo.currentIndexChanged.connect(self._on_region_changed)
        rs_lay.addWidget(self._lbl_region)
        rs_lay.addWidget(self.region_combo)
        self._region_section.setVisible(False)
        cl.addWidget(self._region_section)

        self._save_profile_btn_cw = _ghost_btn("Save as profile…")
        self._save_profile_btn_cw.clicked.connect(self._on_save_cw_profile)
        self.connect_btn = _primary_btn()
        self.connect_btn.clicked.connect(self._on_connect)
        cl.addWidget(self._save_profile_btn_cw)
        cl.addWidget(self.connect_btn)
        vbox.addWidget(card)

        # ── Log groups card ───────────────────────────────────────────────────
        card2, gl, self._lbl_groups = make_card(i18n.tr("cw_card_groups"))
        self._card_groups = card2
        self.group_search = QLineEdit()
        self.group_search.textChanged.connect(self._filter_groups)
        self.group_list = QListWidget()
        self.group_list.setFixedHeight(180)
        self.group_list.currentTextChanged.connect(self._on_group_selected)
        gl.addWidget(self.group_search)
        gl.addWidget(self.group_list)
        card2.setVisible(False)
        vbox.addWidget(card2)

        # ── Log streams card ──────────────────────────────────────────────────
        card3, sl, self._lbl_streams = make_card(i18n.tr("cw_card_streams"))
        self._card_streams = card3
        self.stream_list = QListWidget()
        self.stream_list.setFixedHeight(180)
        sl.addWidget(self.stream_list)
        card3.setVisible(False)
        vbox.addWidget(card3)

        # ── Options card ──────────────────────────────────────────────────────
        card4, ol, self._lbl_options = make_card(i18n.tr("cw_card_options"))
        self._card_options = card4

        self.lookback_combo = QComboBox()
        for label, secs in [
            ("15 min", 900), ("1 hour", 3600), ("6 hours", 21600),
            ("24 hours", 86400), ("3 days", 259200), ("7 days", 604800),
        ]:
            self.lookback_combo.addItem(label, secs)
        self.lookback_combo.setCurrentIndex(1)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setValue(3)
        self.interval_spin.setSuffix(" s")

        self.filter_input = QLineEdit()
        self._open_mode_w = OpenModeWidget()
        self._get_open_mode = self._open_mode_w.get_mode
        self.open_btn = _primary_btn()
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._on_open_clicked)

        self._lbl_lookback = _field_label("")
        self._lbl_poll     = _field_label("")
        self._lbl_filter   = _field_label("")
        ol.addWidget(self._lbl_lookback)
        ol.addWidget(self.lookback_combo)
        ol.addWidget(self._lbl_poll)
        ol.addWidget(self.interval_spin)
        ol.addWidget(self._lbl_filter)
        ol.addWidget(self.filter_input)
        ol.addWidget(self._open_mode_w)
        ol.addWidget(self.open_btn)
        card4.setVisible(False)
        vbox.addWidget(card4)

        vbox.addStretch()
        scroll.setWidget(content)
        outer.addWidget(scroll)

        self.retranslate()

    def retranslate(self) -> None:
        self._title_lbl.setText(i18n.tr("cw_title"))
        if self._lbl_connection:
            self._lbl_connection.setText(i18n.tr("cw_card_connection").upper())
        if self._lbl_groups:
            self._lbl_groups.setText(i18n.tr("cw_card_groups").upper())
        if self._lbl_streams:
            self._lbl_streams.setText(i18n.tr("cw_card_streams").upper())
        if self._lbl_options:
            self._lbl_options.setText(i18n.tr("cw_card_options").upper())
        self._lbl_auth_mode.setText(i18n.tr("cw_auth_mode"))
        current_idx = self._auth_mode_combo.currentIndex()
        self._auth_mode_combo.blockSignals(True)
        self._auth_mode_combo.clear()
        self._auth_mode_combo.addItem(i18n.tr("cw_auth_profile"))
        self._auth_mode_combo.addItem(i18n.tr("cw_auth_keys"))
        self._auth_mode_combo.setCurrentIndex(max(0, current_idx))
        self._auth_mode_combo.blockSignals(False)
        self._lbl_profile.setText(i18n.tr("cw_field_profile"))
        self._lbl_access_key.setText(i18n.tr("cw_field_access_key"))
        self._lbl_secret_key.setText(i18n.tr("cw_field_secret_key"))
        self._lbl_region.setText(i18n.tr("cw_field_region"))
        self._lbl_lookback.setText(i18n.tr("cw_field_lookback"))
        self._lbl_poll.setText(i18n.tr("cw_field_poll"))
        self._lbl_filter.setText(i18n.tr("cw_field_filter"))
        self.group_search.setPlaceholderText(i18n.tr("cw_search_groups"))
        self.filter_input.setPlaceholderText(i18n.tr("cw_filter_ph"))
        self.open_btn.setText(i18n.tr("cw_open"))
        # connect_btn: derive label from connection state, not from current text
        if not getattr(self, "_connecting", False):
            self.connect_btn.setText(
                i18n.tr("cw_refresh") if self._client else i18n.tr("cw_connect")
            )

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _load_cw_profile(self, p: dict) -> None:
        if p.get("access_key_id"):
            self._auth_mode_combo.setCurrentIndex(1)
            self.access_key_input.setText(p.get("access_key_id", ""))
            self.secret_key_input.setText(p.get("secret_key", ""))
        else:
            self._auth_mode_combo.setCurrentIndex(0)
            idx = self.profile_combo.findText(p.get("aws_profile", "(default)"))
            if idx >= 0:
                self.profile_combo.setCurrentIndex(idx)
        region_idx = self.region_combo.findText(p.get("region", ""))
        if region_idx >= 0:
            self.region_combo.setCurrentIndex(region_idx)

    def _on_save_cw_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:", text="My account")
        if not ok or not name.strip():
            return
        is_keys = self._auth_mode_combo.currentIndex() == 1
        data: dict = {"region": self.region_combo.currentText()}
        if is_keys:
            data["access_key_id"] = self.access_key_input.text().strip()
            data["secret_key"]    = self.secret_key_input.text().strip()
        else:
            data["aws_profile"] = self.profile_combo.currentText()
        profiles_store.upsert("cloudwatch", name.strip(), data)
        self._cw_profile_bar.reload()

    def _on_auth_mode_changed(self, index: int):
        use_keys = index == 1
        for w in self._profile_widgets:
            w.setVisible(not use_keys)
        for w in self._key_widgets:
            w.setVisible(use_keys)

    def _on_connect(self):
        self._connecting = True
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText(i18n.tr("cw_connecting"))
        try:
            self._make_client(self._REGIONS[0])
            self._region_section.setVisible(True)
            self._load_groups()
            self.connect_btn.setText(i18n.tr("cw_refresh"))
        except Exception as exc:
            self._client = None
            self._region_section.setVisible(False)
            self._card_groups.setVisible(False)
            QMessageBox.critical(self, i18n.tr("err_connection"), str(exc))
            self.connect_btn.setText(i18n.tr("cw_connect"))
        finally:
            self._connecting = False
            self.connect_btn.setEnabled(True)

    def _make_client(self, region: str) -> None:
        if self._auth_mode_combo.currentIndex() == 1:
            ak = self.access_key_input.text().strip()
            sk = self.secret_key_input.text().strip()
            self._client = cloudwatch.make_client(
                region=region,
                access_key_id=ak,
                secret_access_key=sk,
            )
        else:
            profile = self.profile_combo.currentText()
            self._client = cloudwatch.make_client(
                None if profile == "(default)" else profile, region
            )

    def _load_groups(self) -> None:
        region = self.region_combo.currentText()
        try:
            self._make_client(region)
            groups = cloudwatch.list_log_groups(self._client)
            self._all_groups = groups
            self._populate_groups(groups)
            self._card_groups.setVisible(True)
        except Exception as exc:
            QMessageBox.critical(self, i18n.tr("err_connection"), str(exc))

    def _on_region_changed(self) -> None:
        if self._client:
            self._load_groups()

    def _populate_groups(self, groups: list[str]):
        self.group_list.clear()
        for g in groups:
            self.group_list.addItem(g)

    def _filter_groups(self, text: str):
        lo = text.lower()
        self._populate_groups([g for g in self._all_groups if lo in g.lower()])

    def _on_group_selected(self, group: str):
        if not group or not self._client:
            return
        self.stream_list.clear()
        try:
            streams = cloudwatch.list_log_streams(self._client, group)
            all_item = QListWidgetItem("— All streams —")
            all_item.setForeground(QColor(C_ACCENT))
            self.stream_list.addItem(all_item)
            for s in streams:
                self.stream_list.addItem(s)
            self.stream_list.setCurrentRow(0)
        except Exception as exc:
            QMessageBox.warning(self, i18n.tr("err_streams"), str(exc))
        self._card_streams.setVisible(True)
        self._card_options.setVisible(True)
        self.open_btn.setEnabled(True)

    def _on_open_clicked(self):
        group_item  = self.group_list.currentItem()
        stream_item = self.stream_list.currentItem()
        if not self._client or not group_item:
            return
        stream_name = ""
        if stream_item and stream_item.text() != "— All streams —":
            stream_name = stream_item.text()
        self.open_tab.emit({
            "type":      "cloudwatch",
            "client":    self._client,
            "group":     group_item.text(),
            "stream":    stream_name,
            "filter":    self.filter_input.text(),
            "interval":  self.interval_spin.value(),
            "lookback":  self.lookback_combo.currentData(),
            "auth_mode": self._auth_mode_combo.currentIndex(),
            "profile":   self.profile_combo.currentText(),
            "region":    self.region_combo.currentText(),
        }, self._get_open_mode())


# ── FilePanel ──────────────────────────────────────────────────────────────────

class FilePanel(QWidget):
    open_tab = pyqtSignal(str, int, str)  # (path, tail_lines, split_mode)

    _MAX_RECENT = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._recent: list[str] = []
        self._build_ui()
        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(12, 16, 12, 16)
        vbox.setSpacing(12)
        self.setMinimumWidth(200)
        self.setStyleSheet(f"background: {C_SIDE};")

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 15px; font-weight: 700;"
            "background: transparent; border: none; margin-bottom: 4px;"
        )
        vbox.addWidget(self._title_lbl)

        # ── OPEN FILE card ──
        card, cl, self._lbl_card_open = make_card(i18n.tr("file_card_open"))
        self._desc_lbl = QLabel()
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; background: transparent; border: none;"
        )

        # Tail lines selector
        tail_row = QHBoxLayout()
        tail_row.setSpacing(8)
        self._tail_lbl = QLabel()
        self._tail_lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        self._tail_spin = QSpinBox()
        self._tail_spin.setRange(1, 500_000)
        self._tail_spin.setValue(100)
        self._tail_spin.setSingleStep(100)
        tail_row.addWidget(self._tail_lbl)
        tail_row.addWidget(self._tail_spin)
        tail_row.addStretch()

        self._open_mode_w = OpenModeWidget()
        self._get_open_mode = self._open_mode_w.get_mode

        self._browse_btn = _primary_btn()
        self._browse_btn.clicked.connect(self._on_browse)

        cl.addWidget(self._desc_lbl)
        cl.addLayout(tail_row)
        cl.addWidget(self._open_mode_w)
        cl.addWidget(self._browse_btn)
        vbox.addWidget(card)

        # ── RECENT FILES card ──
        card2, rl, self._lbl_card_recent = make_card(i18n.tr("file_card_recent"))
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(120)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_double_click)

        self.empty_label = QLabel()
        self.empty_label.setStyleSheet(
            "color: #4c4c4c; font-size: 12px; background: transparent; border: none;"
        )
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        rl.addWidget(self.recent_list)
        rl.addWidget(self.empty_label)
        vbox.addWidget(card2)

        vbox.addStretch()
        self.retranslate()
        self._refresh_recent_ui()

    def retranslate(self) -> None:
        self._title_lbl.setText(i18n.tr("file_title"))
        if self._lbl_card_open:
            self._lbl_card_open.setText(i18n.tr("file_card_open").upper())
        if self._lbl_card_recent:
            self._lbl_card_recent.setText(i18n.tr("file_card_recent").upper())
        self._desc_lbl.setText(i18n.tr("file_desc"))
        self._tail_lbl.setText(i18n.tr("file_last_lines"))
        self._browse_btn.setText(i18n.tr("file_browse"))
        self.empty_label.setText(i18n.tr("file_no_recent"))

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _on_browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open log file",
            os.path.expanduser("~"),
            "Log files (*.log *.txt *.out *.err *.json);;All files (*)",
        )
        if path:
            self._open_path(path)

    def _on_recent_double_click(self, item: QListWidgetItem):
        path = item.toolTip()
        if os.path.isfile(path):
            self._open_path(path)
        else:
            QMessageBox.warning(
                self,
                i18n.tr("err_file_not_found"),
                i18n.tr("err_cannot_open", path=path),
            )

    def _open_path(self, path: str):
        if path in self._recent:
            self._recent.remove(path)
        self._recent.insert(0, path)
        self._recent = self._recent[: self._MAX_RECENT]
        self._refresh_recent_ui()
        self.open_tab.emit(path, self._tail_spin.value(), self._get_open_mode())

    def _refresh_recent_ui(self):
        self.recent_list.clear()
        if self._recent:
            self.recent_list.show()
            self.empty_label.hide()
            for p in self._recent:
                item = QListWidgetItem(os.path.basename(p))
                item.setToolTip(p)
                self.recent_list.addItem(item)
        else:
            self.recent_list.hide()
            self.empty_label.show()


# ── SSH recent connections manager ────────────────────────────────────────────

class SSHRecentManager:
    _path = Path.home() / ".config" / "simplelog" / "ssh_recents.json"
    _MAX  = 10

    @classmethod
    def load(cls) -> list[dict]:
        try:
            return json.loads(cls._path.read_text(encoding="utf-8"))
        except Exception:
            return []

    @classmethod
    def push(cls, entry: dict) -> None:
        entries = cls.load()
        # deduplicate by host+port+user+path
        key = (entry.get("host"), entry.get("port"), entry.get("user"), entry.get("remote_path"))
        entries = [e for e in entries
                   if (e.get("host"), e.get("port"), e.get("user"), e.get("remote_path")) != key]
        entries.insert(0, entry)
        entries = entries[:cls._MAX]
        try:
            cls._path.parent.mkdir(parents=True, exist_ok=True)
            cls._path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        except Exception:
            pass


# ── SFTP file browser dialog ──────────────────────────────────────────────────

class _SftpBrowserDialog(QDialog):
    """Simple SFTP directory browser. Double-click dirs to navigate, files to select."""

    def __init__(self, client, start_path: str = "/", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Browse remote files")
        self.resize(480, 400)
        self._client   = client
        self._cur_path = start_path
        self._selected : str | None = None

        layout = QVBoxLayout(self)

        self._path_lbl = QLabel()
        self._path_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 12px; font-weight: 600;"
            " background: transparent; padding: 4px 0;"
        )
        layout.addWidget(self._path_lbl)

        self._list = QListWidget()
        self._list.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._list)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self._navigate(start_path)

    def _navigate(self, path: str) -> None:
        self._cur_path = path
        self._path_lbl.setText(path)
        self._list.clear()
        if path != "/":
            up_item = QListWidgetItem("📁  ..")
            up_item.setData(Qt.ItemDataRole.UserRole, ("dir", str(Path(path).parent)))
            self._list.addItem(up_item)
        try:
            entries = ssh_utils.list_remote_dir_full(self._client, path)
        except RuntimeError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        for name, is_dir in entries:
            prefix = "📁  " if is_dir else "📄  "
            item = QListWidgetItem(prefix + name)
            full = path.rstrip("/") + "/" + name
            item.setData(Qt.ItemDataRole.UserRole, ("dir" if is_dir else "file", full))
            self._list.addItem(item)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        kind, full_path = item.data(Qt.ItemDataRole.UserRole)
        if kind == "dir":
            self._navigate(full_path)
        else:
            self._selected = full_path
            self.accept()

    def _on_ok(self) -> None:
        cur = self._list.currentItem()
        if cur:
            kind, full_path = cur.data(Qt.ItemDataRole.UserRole)
            if kind == "file":
                self._selected = full_path
        self.accept()

    def selected_path(self) -> str | None:
        return self._selected


# ── SSH connection worker (runs connect in background) ────────────────────────

class _SSHConnectWorker(QThread):
    success = pyqtSignal(object)   # paramiko.SSHClient
    failure = pyqtSignal(str)

    def __init__(self, host, user, port, key_path, password) -> None:
        super().__init__()
        self._host     = host
        self._user     = user
        self._port     = port
        self._key_path = key_path
        self._password = password

    def run(self) -> None:
        try:
            client = ssh_utils.make_client(
                self._host, self._user, self._port,
                key_path=self._key_path or None,
                password=self._password or None,
            )
            self.success.emit(client)
        except RuntimeError as e:
            self.failure.emit(str(e))


# ── SSHPanel ──────────────────────────────────────────────────────────────────

class SSHPanel(QWidget):
    open_tab = pyqtSignal(dict, str)   # (cfg, split_mode)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._client = None
        self._connect_worker: _SSHConnectWorker | None = None
        self._build_ui()
        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setStyleSheet(f"background: {C_SIDE};")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background: {C_SIDE};")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 16, 12, 16)
        vbox.setSpacing(12)
        scroll.setWidget(content)

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 15px; font-weight: 700;"
            " background: transparent; border: none; margin-bottom: 4px;"
        )
        vbox.addWidget(self._title_lbl)

        # ── Saved configs card ────────────────────────────────────────────────
        saved_card_ssh, saved_lay_ssh, _ = make_card(i18n.tr("saved_configs"))
        self._ssh_profile_bar = _ProfileBar("ssh", wrapper=saved_card_ssh)
        self._ssh_profile_bar.profile_loaded.connect(self._load_ssh_profile)
        saved_lay_ssh.addWidget(self._ssh_profile_bar)
        vbox.addWidget(saved_card_ssh)

        # ── CONNECTION card ───────────────────────────────────────────────────
        card, cl, self._lbl_conn = make_card(i18n.tr("new_config"))
        vbox.addWidget(card)

        # Host
        self._lbl_host = QLabel()
        self._lbl_host.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        self._host_input = QLineEdit()
        self._host_input.setPlaceholderText("hostname or IP")

        # Port
        self._lbl_port = QLabel()
        self._lbl_port.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        port_row = QHBoxLayout()
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1, 65535)
        self._port_spin.setValue(22)
        port_row.addWidget(self._port_spin)
        port_row.addStretch()

        # User
        self._lbl_user = QLabel()
        self._lbl_user.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        self._user_input = QLineEdit()
        self._user_input.setPlaceholderText("ubuntu")

        # Auth mode
        self._lbl_auth = QLabel()
        self._lbl_auth.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        self._auth_combo = QComboBox()

        # Key widgets
        self._lbl_keypath = QLabel()
        self._lbl_keypath.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        key_row = QHBoxLayout()
        key_row.setSpacing(6)
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("~/.ssh/id_rsa")
        self._key_browse_btn = _ghost_btn()
        self._key_browse_btn.setMaximumWidth(90)
        self._key_browse_btn.clicked.connect(self._on_browse_key)
        key_row.addWidget(self._key_input)
        key_row.addWidget(self._key_browse_btn)
        self._key_widget = QWidget()
        kw_layout = QVBoxLayout(self._key_widget)
        kw_layout.setContentsMargins(0, 0, 0, 0)
        kw_layout.setSpacing(4)
        kw_layout.addWidget(self._lbl_keypath)
        kw_layout.addLayout(key_row)

        # Password widgets
        self._lbl_password = QLabel()
        self._lbl_password.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_widget = QWidget()
        pw_layout = QVBoxLayout(self._pass_widget)
        pw_layout.setContentsMargins(0, 0, 0, 0)
        pw_layout.setSpacing(4)
        pw_layout.addWidget(self._lbl_password)
        pw_layout.addWidget(self._password_input)

        self._auth_combo.currentIndexChanged.connect(self._on_auth_mode_changed)

        # Status badge
        self._status_lbl = QLabel()
        self._status_lbl.setStyleSheet(
            "color: transparent; font-size: 11px; background: transparent; border: none;"
        )

        self._connect_btn = _primary_btn()
        self._connect_btn.clicked.connect(self._on_connect)

        self._save_profile_btn_ssh = _ghost_btn("Save as profile…")
        self._save_profile_btn_ssh.clicked.connect(self._on_save_ssh_profile)

        cl.addWidget(self._lbl_host)
        cl.addWidget(self._host_input)
        cl.addWidget(self._lbl_port)
        cl.addLayout(port_row)
        cl.addWidget(self._lbl_user)
        cl.addWidget(self._user_input)
        cl.addWidget(self._lbl_auth)
        cl.addWidget(self._auth_combo)
        cl.addWidget(self._key_widget)
        cl.addWidget(self._pass_widget)
        cl.addWidget(self._save_profile_btn_ssh)
        cl.addWidget(self._status_lbl)
        cl.addWidget(self._connect_btn)

        # ── REMOTE FILE card ──────────────────────────────────────────────────
        card2, fl, self._lbl_file_card = make_card()
        vbox.addWidget(card2)
        self._file_card_frame = card2
        self._file_card_frame.setVisible(False)

        self._lbl_path = QLabel()
        self._lbl_path.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        self._path_input = QLineEdit()
        self._path_input.setPlaceholderText("/var/log/app.log")
        self._browse_remote_btn = _ghost_btn()
        self._browse_remote_btn.setMaximumWidth(90)
        self._browse_remote_btn.clicked.connect(self._on_sftp_browse)
        path_row.addWidget(self._path_input)
        path_row.addWidget(self._browse_remote_btn)

        self._lbl_tail = QLabel()
        self._lbl_tail.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        tail_row2 = QHBoxLayout()
        self._tail_spin = QSpinBox()
        self._tail_spin.setRange(1, 500_000)
        self._tail_spin.setValue(100)
        self._tail_spin.setSingleStep(100)
        tail_row2.addWidget(self._tail_spin)
        tail_row2.addStretch()

        self._open_mode_w = OpenModeWidget()
        self._open_btn = _primary_btn()
        self._open_btn.clicked.connect(self._on_open)

        fl.addWidget(self._lbl_path)
        fl.addLayout(path_row)
        fl.addWidget(self._lbl_tail)
        fl.addLayout(tail_row2)
        fl.addWidget(self._open_mode_w)
        fl.addWidget(self._open_btn)

        # ── RECENT CONNECTIONS card ────────────────────────────────────────────
        card3, rl, self._lbl_recent_card = make_card()
        self._recent_card = card3
        self._recent_list = QListWidget()
        self._recent_list.setMinimumHeight(80)
        self._recent_list.itemDoubleClicked.connect(self._on_recent_double_click)
        self._recent_empty_lbl = QLabel()
        self._recent_empty_lbl.setStyleSheet(
            "color: #4c4c4c; font-size: 12px; background: transparent; border: none;"
        )
        self._recent_empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rl.addWidget(self._recent_list)
        rl.addWidget(self._recent_empty_lbl)
        card3.setVisible(False)
        vbox.addWidget(card3)

        vbox.addStretch()
        self.retranslate()
        self._on_auth_mode_changed(0)
        self._refresh_recents()

    def retranslate(self) -> None:
        self._title_lbl.setText(i18n.tr("ssh_title"))
        if self._lbl_conn:
            self._lbl_conn.setText(i18n.tr("ssh_card_connection").upper())
        if self._lbl_file_card:
            self._lbl_file_card.setText(i18n.tr("ssh_card_file").upper())
        if self._lbl_recent_card:
            self._lbl_recent_card.setText(i18n.tr("ssh_card_recent").upper())
        self._lbl_host.setText(i18n.tr("ssh_field_host"))
        self._lbl_port.setText(i18n.tr("ssh_field_port"))
        self._lbl_user.setText(i18n.tr("ssh_field_user"))
        self._lbl_auth.setText(i18n.tr("ssh_auth_mode"))
        self._lbl_keypath.setText(i18n.tr("ssh_field_keypath"))
        self._lbl_password.setText(i18n.tr("ssh_field_password"))
        self._key_browse_btn.setText(i18n.tr("ssh_browse_key"))
        self._browse_remote_btn.setText(i18n.tr("ssh_browse_remote"))
        self._lbl_path.setText(i18n.tr("ssh_field_path"))
        self._lbl_tail.setText(i18n.tr("ssh_field_tail"))
        self._open_btn.setText(i18n.tr("ssh_open"))
        self._recent_empty_lbl.setText(i18n.tr("ssh_no_recent"))
        cur = self._auth_combo.currentIndex()
        self._auth_combo.blockSignals(True)
        self._auth_combo.clear()
        self._auth_combo.addItem(i18n.tr("ssh_auth_key"))
        self._auth_combo.addItem(i18n.tr("ssh_auth_password"))
        self._auth_combo.setCurrentIndex(cur)
        self._auth_combo.blockSignals(False)
        if not self._connect_btn.isEnabled():
            pass  # keep "connecting" text
        elif self._client is not None:
            self._connect_btn.setText(i18n.tr("ssh_connected"))
        else:
            self._connect_btn.setText(i18n.tr("ssh_connect"))

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_auth_mode_changed(self, idx: int) -> None:
        self._key_widget.setVisible(idx == 0)
        self._pass_widget.setVisible(idx == 1)

    def _on_browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select SSH key file", os.path.expanduser("~/.ssh"), "All files (*)"
        )
        if path:
            self._key_input.setText(path)

    def _on_connect(self) -> None:
        host = self._host_input.text().strip()
        user = self._user_input.text().strip()
        if not host or not user:
            QMessageBox.warning(self, "SSH", "Host and username are required.")
            return
        self._client = None
        self._file_card_frame.setVisible(False)
        self._recent_card.setVisible(False)
        self._connect_btn.setEnabled(False)
        self._connect_btn.setText(i18n.tr("ssh_connecting"))
        self._status_lbl.setText("")

        auth_mode = self._auth_combo.currentIndex()
        key_path  = self._key_input.text().strip() if auth_mode == 0 else ""
        password  = self._password_input.text() if auth_mode == 1 else ""

        self._connect_worker = _SSHConnectWorker(
            host, user, self._port_spin.value(), key_path, password
        )
        self._connect_worker.success.connect(self._on_connect_success)
        self._connect_worker.failure.connect(self._on_connect_failure)
        self._connect_worker.start()

    def _on_connect_success(self, client) -> None:
        self._client = client
        self._connect_btn.setEnabled(True)
        self._connect_btn.setText(i18n.tr("ssh_connected"))
        self._status_lbl.setStyleSheet(
            f"color: {C_INFO}; font-size: 11px; background: transparent; border: none;"
        )
        self._status_lbl.setText("●  " + i18n.tr("ssh_connected"))
        self._file_card_frame.setVisible(True)
        self._recent_card.setVisible(True)

    def _on_connect_failure(self, msg: str) -> None:
        self._connect_btn.setEnabled(True)
        self._connect_btn.setText(i18n.tr("ssh_connect"))
        self._status_lbl.setStyleSheet(
            f"color: {C_ERR}; font-size: 11px; background: transparent; border: none;"
        )
        self._status_lbl.setText("●  " + msg)

    def _load_ssh_profile(self, p: dict) -> None:
        self._host_input.setText(p.get("host", ""))
        self._port_spin.setValue(p.get("port", 22))
        self._user_input.setText(p.get("user", ""))
        self._auth_combo.setCurrentIndex(0 if p.get("auth_mode", "key") == "key" else 1)
        self._key_input.setText(p.get("key_path", ""))
        self._path_input.setText(p.get("remote_path", ""))

    def _on_save_ssh_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:",
                                        text=f"{self._user_input.text()}@{self._host_input.text()}")
        if not ok or not name.strip():
            return
        auth_idx = self._auth_combo.currentIndex()
        profiles_store.upsert("ssh", name.strip(), {
            "host":        self._host_input.text().strip(),
            "port":        self._port_spin.value(),
            "user":        self._user_input.text().strip(),
            "auth_mode":   "key" if auth_idx == 0 else "password",
            "key_path":    self._key_input.text().strip() if auth_idx == 0 else "",
            "remote_path": self._path_input.text().strip(),
        })
        self._ssh_profile_bar.reload()

    def _on_sftp_browse(self) -> None:
        if self._client is None:
            return
        start = self._path_input.text().strip()
        # start from the directory if path already set
        start_dir = str(Path(start).parent) if start else "/"
        dlg = _SftpBrowserDialog(self._client, start_dir, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_path():
            self._path_input.setText(dlg.selected_path())

    def _on_open(self) -> None:
        if self._client is None:
            return
        path = self._path_input.text().strip()
        if not path:
            return
        host     = self._host_input.text().strip()
        user     = self._user_input.text().strip()
        port     = self._port_spin.value()
        auth_idx = self._auth_combo.currentIndex()
        key_path = self._key_input.text().strip() if auth_idx == 0 else ""
        cfg = {
            "type":        "ssh",
            "host":        host,
            "port":        port,
            "user":        user,
            "auth_mode":   "key" if auth_idx == 0 else "password",
            "key_path":    key_path,
            "remote_path": path,
            "tail_lines":  self._tail_spin.value(),
        }
        # Push to recents (never store password)
        recent_entry = {k: v for k, v in cfg.items() if k != "password"}
        SSHRecentManager.push(recent_entry)
        self._refresh_recents()
        # Open a fresh connection for the worker (the panel keeps its own client)
        try:
            worker_client = ssh_utils.make_client(
                host, user, port,
                key_path=key_path or None,
                password=self._password_input.text() if auth_idx == 1 else None,
            )
        except RuntimeError as e:
            QMessageBox.critical(self, i18n.tr("err_connection"), str(e))
            return
        cfg["_client"] = worker_client
        self.open_tab.emit(cfg, self._open_mode_w.get_mode())

    def _on_recent_double_click(self, item: QListWidgetItem) -> None:
        entry = item.data(Qt.ItemDataRole.UserRole)
        if not entry:
            return
        self._host_input.setText(entry.get("host", ""))
        self._port_spin.setValue(entry.get("port", 22))
        self._user_input.setText(entry.get("user", ""))
        auth_mode = entry.get("auth_mode", "key")
        self._auth_combo.setCurrentIndex(0 if auth_mode == "key" else 1)
        self._key_input.setText(entry.get("key_path", ""))
        self._path_input.setText(entry.get("remote_path", ""))
        self._tail_spin.setValue(entry.get("tail_lines", 100))
        if auth_mode == "password":
            self._password_input.clear()
            self._password_input.setFocus()

    def _refresh_recents(self) -> None:
        entries = SSHRecentManager.load()
        self._recent_list.clear()
        if entries:
            self._recent_empty_lbl.hide()
            self._recent_list.show()
            for e in entries:
                label = f"{e.get('user','')}@{e.get('host','')}:{e.get('port',22)}  —  {e.get('remote_path','')}"
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, e)
                self._recent_list.addItem(item)
        else:
            self._recent_list.hide()
            self._recent_empty_lbl.show()


# ── DockerPanel ───────────────────────────────────────────────────────────────

class DockerPanel(QWidget):
    open_tab = pyqtSignal(dict, str)   # (cfg, split_mode)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._build_ui()
        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setStyleSheet(f"background: {C_SIDE};")

        # ── Docker unavailable placeholder ────────────────────────────────────
        if not docker_utils.is_docker_available():
            lbl = QLabel(i18n.tr("docker_not_available"))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color: {C_MUTED}; font-size: 13px; background: transparent; border: none; padding: 24px;"
            )
            outer.addWidget(lbl)
            return

        # Title bar
        title_bar = QWidget()
        title_bar.setStyleSheet(f"background: {C_SIDE};")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 16, 12, 8)
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 15px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        tb_layout.addWidget(self._title_lbl)
        tb_layout.addStretch()
        outer.addWidget(title_bar)

        # ── Inner QTabWidget ──────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {C_SIDE}; }}
            QTabBar::tab {{
                background: transparent; color: {C_MUTED};
                padding: 6px 14px; font-size: 11px; border: none;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {C_ACCENT}; border-bottom: 2px solid {C_ACCENT};
            }}
            QTabBar::tab:hover {{ color: {C_TEXT}; }}
        """)
        outer.addWidget(self._tabs)

        # ── Tab 0: Containers ─────────────────────────────────────────────────
        tab0 = QWidget()
        tab0.setStyleSheet(f"background: {C_SIDE};")
        t0 = QVBoxLayout(tab0)
        t0.setContentsMargins(12, 10, 12, 16)
        t0.setSpacing(12)
        self._tabs.addTab(tab0, "")

        card_c, cl_c, self._lbl_card_containers = make_card()
        # Refresh button header row
        hdr0 = QHBoxLayout()
        self._lbl_running = QLabel()
        self._lbl_running.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 10px; font-weight: 700; background: transparent; border: none;"
        )
        self._refresh_btn0 = _ghost_btn()
        self._refresh_btn0.setMaximumWidth(100)
        self._refresh_btn0.clicked.connect(self._refresh_containers)
        hdr0.addWidget(self._lbl_running)
        hdr0.addStretch()
        hdr0.addWidget(self._refresh_btn0)
        self._container_list = QListWidget()
        self._container_list.setMinimumHeight(120)
        self._no_containers_lbl = QLabel()
        self._no_containers_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_containers_lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        cl_c.addLayout(hdr0)
        cl_c.addWidget(self._container_list)
        cl_c.addWidget(self._no_containers_lbl)
        t0.addWidget(card_c)

        card_co, ol_c, _ = make_card()
        t0.addWidget(card_co)
        self._tail_spin_c = QSpinBox()
        self._tail_spin_c.setRange(1, 500_000)
        self._tail_spin_c.setValue(100)
        self._tail_spin_c.setSingleStep(100)
        self._open_mode_c = OpenModeWidget()
        self._open_btn_c = _primary_btn()
        self._open_btn_c.setEnabled(False)
        self._open_btn_c.clicked.connect(self._on_open_container)
        self._container_list.itemSelectionChanged.connect(
            lambda: self._open_btn_c.setEnabled(bool(self._container_list.selectedItems()))
        )
        tail_row_c = QHBoxLayout()
        self._lbl_tail_c = QLabel()
        self._lbl_tail_c.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        tail_row_c.addWidget(self._lbl_tail_c)
        tail_row_c.addWidget(self._tail_spin_c)
        tail_row_c.addStretch()
        ol_c.addLayout(tail_row_c)
        ol_c.addWidget(self._open_mode_c)
        ol_c.addWidget(self._open_btn_c)
        t0.addStretch()

        # ── Tab 1: Compose ────────────────────────────────────────────────────
        tab1 = QWidget()
        tab1.setStyleSheet(f"background: {C_SIDE};")
        t1 = QVBoxLayout(tab1)
        t1.setContentsMargins(12, 10, 12, 16)
        t1.setSpacing(12)
        self._tabs.addTab(tab1, "")

        card_s, sl, self._lbl_card_stacks = make_card()
        hdr1 = QHBoxLayout()
        self._lbl_stacks = QLabel()
        self._lbl_stacks.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 10px; font-weight: 700; background: transparent; border: none;"
        )
        self._refresh_btn1 = _ghost_btn()
        self._refresh_btn1.setMaximumWidth(100)
        self._refresh_btn1.clicked.connect(self._refresh_stacks)
        hdr1.addWidget(self._lbl_stacks)
        hdr1.addStretch()
        hdr1.addWidget(self._refresh_btn1)
        self._stack_list = QListWidget()
        self._stack_list.setMinimumHeight(120)
        self._no_stacks_lbl = QLabel()
        self._no_stacks_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_stacks_lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        sl.addLayout(hdr1)
        sl.addWidget(self._stack_list)
        sl.addWidget(self._no_stacks_lbl)
        t1.addWidget(card_s)

        card_so, ol_s, _ = make_card()
        t1.addWidget(card_so)
        self._tail_spin_s = QSpinBox()
        self._tail_spin_s.setRange(1, 500_000)
        self._tail_spin_s.setValue(100)
        self._tail_spin_s.setSingleStep(100)
        self._open_mode_s = OpenModeWidget()
        self._open_btn_s = _primary_btn()
        self._open_btn_s.setEnabled(False)
        self._open_btn_s.clicked.connect(self._on_open_stack)
        self._stack_list.itemSelectionChanged.connect(
            lambda: self._open_btn_s.setEnabled(bool(self._stack_list.selectedItems()))
        )
        tail_row_s = QHBoxLayout()
        self._lbl_tail_s = QLabel()
        self._lbl_tail_s.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        tail_row_s.addWidget(self._lbl_tail_s)
        tail_row_s.addWidget(self._tail_spin_s)
        tail_row_s.addStretch()
        ol_s.addLayout(tail_row_s)
        ol_s.addWidget(self._open_mode_s)
        ol_s.addWidget(self._open_btn_s)
        t1.addStretch()

        # ── Tab 2: File in Container ──────────────────────────────────────────
        tab2 = QWidget()
        tab2.setStyleSheet(f"background: {C_SIDE};")
        t2 = QVBoxLayout(tab2)
        t2.setContentsMargins(12, 10, 12, 16)
        t2.setSpacing(12)
        self._tabs.addTab(tab2, "")

        card_ec, ecl, self._lbl_card_exec_c = make_card()
        hdr2 = QHBoxLayout()
        self._lbl_exec_c = QLabel()
        self._lbl_exec_c.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 10px; font-weight: 700; background: transparent; border: none;"
        )
        self._refresh_btn2 = _ghost_btn()
        self._refresh_btn2.setMaximumWidth(100)
        self._refresh_btn2.clicked.connect(self._refresh_containers)
        hdr2.addWidget(self._lbl_exec_c)
        hdr2.addStretch()
        hdr2.addWidget(self._refresh_btn2)
        self._exec_container_list = QListWidget()
        self._exec_container_list.setMinimumHeight(100)
        self._no_exec_lbl = QLabel()
        self._no_exec_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_exec_lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        ecl.addLayout(hdr2)
        ecl.addWidget(self._exec_container_list)
        ecl.addWidget(self._no_exec_lbl)
        t2.addWidget(card_ec)

        card_ef, efl, self._lbl_card_exec_f = make_card()
        t2.addWidget(card_ef)
        self._lbl_exec_path = QLabel()
        self._lbl_exec_path.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        self._exec_path_input = QLineEdit()
        self._exec_path_input.setPlaceholderText("/var/log/app/service.log")
        self._tail_spin_e = QSpinBox()
        self._tail_spin_e.setRange(1, 500_000)
        self._tail_spin_e.setValue(100)
        self._tail_spin_e.setSingleStep(100)
        self._open_mode_e = OpenModeWidget()
        self._open_btn_e = _primary_btn()
        self._open_btn_e.setEnabled(False)
        self._open_btn_e.clicked.connect(self._on_open_exec)

        def _update_exec_btn():
            has_c = bool(self._exec_container_list.selectedItems())
            has_p = bool(self._exec_path_input.text().strip())
            self._open_btn_e.setEnabled(has_c and has_p)

        self._exec_container_list.itemSelectionChanged.connect(_update_exec_btn)
        self._exec_path_input.textChanged.connect(_update_exec_btn)

        tail_row_e = QHBoxLayout()
        self._lbl_tail_e = QLabel()
        self._lbl_tail_e.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        tail_row_e.addWidget(self._lbl_tail_e)
        tail_row_e.addWidget(self._tail_spin_e)
        tail_row_e.addStretch()
        efl.addWidget(self._lbl_exec_path)
        efl.addWidget(self._exec_path_input)
        efl.addLayout(tail_row_e)
        efl.addWidget(self._open_mode_e)
        efl.addWidget(self._open_btn_e)
        t2.addStretch()

        self.retranslate()
        self._refresh_containers()
        self._refresh_stacks()

    def retranslate(self) -> None:
        if not hasattr(self, "_title_lbl"):
            return
        self._title_lbl.setText(i18n.tr("docker_title"))
        self._tabs.setTabText(0, i18n.tr("docker_tab_containers"))
        self._tabs.setTabText(1, i18n.tr("docker_tab_compose"))
        self._tabs.setTabText(2, i18n.tr("docker_tab_exec"))
        self._lbl_running.setText(i18n.tr("docker_tab_containers").upper())
        self._lbl_stacks.setText(i18n.tr("docker_tab_compose").upper())
        self._lbl_exec_c.setText(i18n.tr("docker_tab_containers").upper())
        self._refresh_btn0.setText(i18n.tr("docker_refresh"))
        self._refresh_btn1.setText(i18n.tr("docker_refresh"))
        self._refresh_btn2.setText(i18n.tr("docker_refresh"))
        self._no_containers_lbl.setText(i18n.tr("docker_no_containers"))
        self._no_stacks_lbl.setText(i18n.tr("docker_no_stacks"))
        self._no_exec_lbl.setText(i18n.tr("docker_no_containers"))
        self._lbl_tail_c.setText(i18n.tr("docker_field_tail"))
        self._lbl_tail_s.setText(i18n.tr("docker_field_tail"))
        self._lbl_tail_e.setText(i18n.tr("docker_field_tail"))
        self._lbl_exec_path.setText(i18n.tr("docker_field_path"))
        self._open_btn_c.setText(i18n.tr("docker_open_container"))
        self._open_btn_s.setText(i18n.tr("docker_open_stack"))
        self._open_btn_e.setText(i18n.tr("docker_open_exec"))

    # ── Data refresh ──────────────────────────────────────────────────────────

    def _refresh_containers(self) -> None:
        try:
            containers = docker_utils.list_containers()
        except RuntimeError:
            containers = []
        self._container_list.clear()
        self._exec_container_list.clear()
        if containers:
            self._no_containers_lbl.hide()
            self._no_exec_lbl.hide()
            self._container_list.show()
            self._exec_container_list.show()
            for c in containers:
                label = f"{c['name']}   ({c['image']})"
                for lst in (self._container_list, self._exec_container_list):
                    item = QListWidgetItem(label)
                    item.setData(Qt.ItemDataRole.UserRole, c)
                    if c["compose_project"]:
                        item.setToolTip(f"compose: {c['compose_project']}/{c['compose_service']}")
                    lst.addItem(item)
        else:
            self._no_containers_lbl.show()
            self._no_exec_lbl.show()
            self._container_list.hide()
            self._exec_container_list.hide()

    def _refresh_stacks(self) -> None:
        try:
            stacks = docker_utils.list_compose_stacks()
        except RuntimeError:
            stacks = []
        self._stack_list.clear()
        if stacks:
            self._no_stacks_lbl.hide()
            self._stack_list.show()
            for s in stacks:
                item = QListWidgetItem(f"{s['name']}   ({s['status']})")
                item.setData(Qt.ItemDataRole.UserRole, s)
                item.setToolTip(s.get("config_files", ""))
                self._stack_list.addItem(item)
        else:
            self._no_stacks_lbl.show()
            self._stack_list.hide()

    # ── Open actions ──────────────────────────────────────────────────────────

    def _on_open_container(self) -> None:
        items = self._container_list.selectedItems()
        if not items:
            return
        c = items[0].data(Qt.ItemDataRole.UserRole)
        cfg = {
            "type":           "docker_container",
            "container_id":   c["id"],
            "container_name": c["name"],
            "tail_lines":     self._tail_spin_c.value(),
        }
        self.open_tab.emit(cfg, self._open_mode_c.get_mode())

    def _on_open_stack(self) -> None:
        items = self._stack_list.selectedItems()
        if not items:
            return
        s = items[0].data(Qt.ItemDataRole.UserRole)
        cfg = {
            "type":         "docker_compose",
            "project_name": s["name"],
            "tail_lines":   self._tail_spin_s.value(),
        }
        self.open_tab.emit(cfg, self._open_mode_s.get_mode())

    def _on_open_exec(self) -> None:
        items = self._exec_container_list.selectedItems()
        path  = self._exec_path_input.text().strip()
        if not items or not path:
            return
        c = items[0].data(Qt.ItemDataRole.UserRole)
        cfg = {
            "type":           "docker_exec_file",
            "container_id":   c["id"],
            "container_name": c["name"],
            "remote_path":    path,
            "tail_lines":     self._tail_spin_e.value(),
        }
        self.open_tab.emit(cfg, self._open_mode_e.get_mode())


# ── VercelPanel ───────────────────────────────────────────────────────────────

class _VercelConnectWorker(QThread):
    """Verifies a Vercel token in a background thread."""
    success = pyqtSignal(str)   # username
    failure = pyqtSignal(str)   # error message

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def run(self) -> None:
        try:
            data = vercel_utils.verify_token(self._token)
            name = data.get("user", {}).get("name") or data.get("user", {}).get("email") or "OK"
            self.success.emit(name)
        except RuntimeError as e:
            self.failure.emit(str(e))


class _VercelFetchProjectsWorker(QThread):
    """Fetches project list in background."""
    success = pyqtSignal(list)
    failure = pyqtSignal(str)

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def run(self) -> None:
        try:
            projects = vercel_utils.list_projects(self._token)
            self.success.emit(projects)
        except RuntimeError as e:
            self.failure.emit(str(e))


class _VercelFetchDeployWorker(QThread):
    """Fetches latest deployment for a project in background."""
    success = pyqtSignal(dict)   # deployment dict
    failure = pyqtSignal(str)

    def __init__(self, token: str, project_id: str, target: str) -> None:
        super().__init__()
        self._token      = token
        self._project_id = project_id
        self._target     = target

    def run(self) -> None:
        try:
            deploy = vercel_utils.get_latest_deployment(self._token, self._project_id, self._target)
            if deploy:
                self.success.emit(deploy)
            else:
                self.failure.emit(i18n.tr("vercel_no_deploy"))
        except RuntimeError as e:
            self.failure.emit(str(e))


class VercelPanel(QWidget):
    open_tab = pyqtSignal(dict, str)   # (cfg, split_mode)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._token      = vercel_utils.load_token()
        self._projects:  list[dict] = []
        self._deployment: dict | None = None
        self._connect_worker: _VercelConnectWorker | None = None
        self._projects_worker: _VercelFetchProjectsWorker | None = None
        self._deploy_worker:  _VercelFetchDeployWorker | None = None
        self._build_ui()
        if self._token:
            self._token_input.setText(self._token)
            self._do_connect()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        # ── Saved configs card ────────────────────────────────────────
        saved_card_v, saved_lay_v, _ = make_card(i18n.tr("saved_configs"))
        self._vercel_profile_bar = _ProfileBar("vercel", wrapper=saved_card_v)
        self._vercel_profile_bar.profile_loaded.connect(self._load_vercel_profile)
        saved_lay_v.addWidget(self._vercel_profile_bar)
        vlay.addWidget(saved_card_v)

        # ── Card: API Token ──────────────────────────────────────────
        card_tok, lay_tok, _ = make_card(i18n.tr("new_config"))

        self._token_input = QLineEdit()
        self._token_input.setPlaceholderText(i18n.tr("vercel_field_token"))
        self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_input.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lay_tok.addWidget(self._token_input)

        hint = QLabel(i18n.tr("vercel_token_hint"))
        hint.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
        hint.setWordWrap(True)
        lay_tok.addWidget(hint)

        self._save_profile_btn_vercel = _ghost_btn("Save as profile…")
        self._save_profile_btn_vercel.clicked.connect(self._on_save_vercel_profile)
        self._save_profile_btn_vercel.setEnabled(False)
        lay_tok.addWidget(self._save_profile_btn_vercel)

        self._connect_btn = _primary_btn(i18n.tr("vercel_connect"))
        self._connect_btn.clicked.connect(self._do_connect)
        lay_tok.addWidget(self._connect_btn)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._status_lbl.setWordWrap(True)
        lay_tok.addWidget(self._status_lbl)

        vlay.addWidget(card_tok)

        # ── Card: Project ────────────────────────────────────────────
        card_proj, lay_proj, _ = make_card(i18n.tr("vercel_card_project"))

        refresh_row = QHBoxLayout()
        refresh_row.addStretch()
        self._refresh_btn = _ghost_btn(i18n.tr("vercel_refresh"))
        self._refresh_btn.clicked.connect(self._fetch_projects)
        self._refresh_btn.setEnabled(False)
        refresh_row.addWidget(self._refresh_btn)
        lay_proj.addLayout(refresh_row)

        self._project_list = QListWidget()
        self._project_list.setFixedHeight(160)
        self._project_list.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; font-size: 12px;"
        )
        self._project_list.currentItemChanged.connect(self._on_project_changed)
        lay_proj.addWidget(self._project_list)

        self._card_proj = card_proj
        card_proj.setVisible(False)
        vlay.addWidget(card_proj)

        # ── Card: Deployment ─────────────────────────────────────────
        card_dep, lay_dep, _ = make_card(i18n.tr("vercel_card_deploy"))

        self._target_combo = QComboBox()
        self._target_combo.addItems([
            i18n.tr("vercel_target_prod"),
            i18n.tr("vercel_target_preview"),
            i18n.tr("vercel_target_any"),
        ])
        self._target_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._target_combo.currentIndexChanged.connect(self._on_target_changed)
        lay_dep.addWidget(self._target_combo)

        self._deploy_lbl = QLabel("—")
        self._deploy_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._deploy_lbl.setWordWrap(True)
        lay_dep.addWidget(self._deploy_lbl)

        interval_row = QHBoxLayout()
        interval_lbl = QLabel(i18n.tr("vercel_field_interval"))
        interval_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 60)
        self._interval_spin.setValue(3)
        self._interval_spin.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        interval_row.addWidget(interval_lbl)
        interval_row.addStretch()
        interval_row.addWidget(self._interval_spin)
        lay_dep.addLayout(interval_row)

        self._open_mode = OpenModeWidget()
        lay_dep.addWidget(self._open_mode)

        self._open_btn = _primary_btn(i18n.tr("vercel_open"))
        self._open_btn.clicked.connect(self._on_open)
        self._open_btn.setEnabled(False)
        lay_dep.addWidget(self._open_btn)

        self._card_dep = card_dep
        card_dep.setVisible(False)
        vlay.addWidget(card_dep)
        vlay.addStretch()

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _do_connect(self) -> None:
        token = self._token_input.text().strip()
        if not token:
            return
        self._token = token
        self._connect_btn.setEnabled(False)
        self._status_lbl.setText(i18n.tr("vercel_connecting"))
        self._status_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")

        self._connect_worker = _VercelConnectWorker(token)
        self._connect_worker.success.connect(self._on_connect_ok)
        self._connect_worker.failure.connect(self._on_connect_fail)
        self._connect_worker.start()

    def _on_connect_ok(self, username: str) -> None:
        self._status_lbl.setText(f"{i18n.tr('vercel_connected')} ({username})")
        self._status_lbl.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn.setEnabled(True)
        self._refresh_btn.setEnabled(True)
        self._save_profile_btn_vercel.setEnabled(True)
        self._card_proj.setVisible(True)
        self._fetch_projects()

    def _load_vercel_profile(self, p: dict) -> None:
        self._token_input.setText(p.get("token", ""))

    def _on_save_vercel_profile(self) -> None:
        token = self._token_input.text().strip()
        if not token:
            return
        default_name = f"vercel-{token[:8]}…"
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text=default_name)
        if not ok or not name.strip():
            return
        profiles_store.upsert("vercel", name.strip(), {"token": token})
        self._vercel_profile_bar.reload()

    def _on_connect_fail(self, msg: str) -> None:
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn.setEnabled(True)

    # ── Projects ──────────────────────────────────────────────────────────────

    def _fetch_projects(self) -> None:
        self._project_list.clear()
        self._project_list.addItem("…")
        self._refresh_btn.setEnabled(False)

        self._projects_worker = _VercelFetchProjectsWorker(self._token)
        self._projects_worker.success.connect(self._on_projects_loaded)
        self._projects_worker.failure.connect(self._on_projects_fail)
        self._projects_worker.start()

    def _on_projects_loaded(self, projects: list) -> None:
        self._projects = projects
        self._project_list.clear()
        self._refresh_btn.setEnabled(True)
        if not projects:
            self._project_list.addItem(i18n.tr("vercel_no_projects"))
            return
        for p in projects:
            fw = f"  [{p['framework']}]" if p.get("framework") else ""
            item = QListWidgetItem(f"{p['name']}{fw}")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self._project_list.addItem(item)

    def _on_projects_fail(self, msg: str) -> None:
        self._project_list.clear()
        self._project_list.addItem(msg)
        self._refresh_btn.setEnabled(True)

    def _on_project_changed(self, current, _prev) -> None:
        if not current:
            return
        p = current.data(Qt.ItemDataRole.UserRole)
        if not p:
            return
        self._open_btn.setEnabled(False)
        self._deployment = None
        self._deploy_lbl.setText("…")
        self._card_dep.setVisible(True)
        self._fetch_deployment(p["id"])

    def _on_target_changed(self, _idx: int) -> None:
        items = self._project_list.selectedItems()
        if not items:
            return
        p = items[0].data(Qt.ItemDataRole.UserRole)
        if not p:
            return
        self._open_btn.setEnabled(False)
        self._deployment = None
        self._deploy_lbl.setText("…")
        self._fetch_deployment(p["id"])

    # ── Deployment ────────────────────────────────────────────────────────────

    def _target_key(self) -> str:
        idx = self._target_combo.currentIndex()
        return ["production", "preview", "any"][idx]

    def _fetch_deployment(self, project_id: str) -> None:
        self._deploy_worker = _VercelFetchDeployWorker(self._token, project_id, self._target_key())
        self._deploy_worker.success.connect(self._on_deploy_loaded)
        self._deploy_worker.failure.connect(self._on_deploy_fail)
        self._deploy_worker.start()

    def _on_deploy_loaded(self, deploy: dict) -> None:
        self._deployment = deploy
        url  = deploy.get("url", "")
        state = deploy.get("state", "")
        self._deploy_lbl.setText(f"{url}  [{state}]")
        self._open_btn.setEnabled(True)

    def _on_deploy_fail(self, msg: str) -> None:
        self._deploy_lbl.setText(msg)
        self._deploy_lbl.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._open_btn.setEnabled(False)

    # ── Open tab ──────────────────────────────────────────────────────────────

    def _on_open(self) -> None:
        items = self._project_list.selectedItems()
        if not items or not self._deployment:
            return
        p = items[0].data(Qt.ItemDataRole.UserRole)
        if not p:
            return
        cfg = {
            "type":          "vercel",
            "token":         self._token,
            "project_id":    p["id"],
            "project_name":  p["name"],
            "deployment_id": self._deployment["id"],
            "interval_s":    self._interval_spin.value(),
        }
        self.open_tab.emit(cfg, self._open_mode.get_mode())


# ── GCPPanel ──────────────────────────────────────────────────────────────────

class _GCPConnectWorker(QThread):
    success = pyqtSignal(object)  # gcp client
    failure = pyqtSignal(str)

    def __init__(self, project_id: str, key_path: str | None) -> None:
        super().__init__()
        self._project_id = project_id
        self._key_path   = key_path or None

    def run(self) -> None:
        try:
            client = gcp_utils.make_client(self._project_id, self._key_path)
            # cheap probe: fetch 0 entries to validate auth
            gcp_utils.fetch_entries(client,
                gcp_utils.build_filter(since=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                )),
                max_results=1,
            )
            self.success.emit(client)
        except RuntimeError as e:
            self.failure.emit(str(e))


class _GCPListProjectsWorker(QThread):
    success = pyqtSignal(list)
    failure = pyqtSignal(str)

    def __init__(self, key_path: str | None) -> None:
        super().__init__()
        self._key_path = key_path or None

    def run(self) -> None:
        try:
            self.success.emit(gcp_utils.list_projects(self._key_path))
        except RuntimeError as e:
            self.failure.emit(str(e))


class GCPPanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client: object | None = None
        self._connect_worker:  _GCPConnectWorker | None = None
        self._projects_worker: _GCPListProjectsWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"

        # ── Saved configs card ────────────────────────────────────────
        saved_card_gcp, saved_lay_gcp, _ = make_card(i18n.tr("saved_configs"))
        self._gcp_profile_bar = _ProfileBar("gcp", wrapper=saved_card_gcp)
        self._gcp_profile_bar.profile_loaded.connect(self._load_gcp_profile)
        saved_lay_gcp.addWidget(self._gcp_profile_bar)
        vlay.addWidget(saved_card_gcp)

        # ── Card: Auth ───────────────────────────────────────────────
        card_auth, lay_auth, _ = make_card(i18n.tr("new_config"))

        self._auth_combo = QComboBox()
        self._auth_combo.addItems([i18n.tr("gcp_auth_adc"), i18n.tr("gcp_auth_sa")])
        self._auth_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._auth_combo.currentIndexChanged.connect(self._on_auth_mode_changed)
        lay_auth.addWidget(self._auth_combo)

        # Service account key row (shown only in SA mode)
        self._sa_widget = QWidget()
        sa_lay = QVBoxLayout(self._sa_widget)
        sa_lay.setContentsMargins(0, 4, 0, 0)
        sa_lay.setSpacing(4)
        key_row = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText(i18n.tr("gcp_field_keyfile"))
        self._key_input.setStyleSheet(field_style)
        self._key_browse = _ghost_btn(i18n.tr("gcp_browse_key"))
        self._key_browse.clicked.connect(self._browse_key)
        key_row.addWidget(self._key_input)
        key_row.addWidget(self._key_browse)
        sa_lay.addLayout(key_row)
        self._sa_widget.setVisible(False)
        lay_auth.addWidget(self._sa_widget)

        # Project ID row
        proj_row = QHBoxLayout()
        self._project_input = QLineEdit()
        self._project_input.setPlaceholderText(i18n.tr("gcp_field_project"))
        self._project_input.setStyleSheet(field_style)
        self._list_proj_btn = _ghost_btn(i18n.tr("gcp_list_projects"))
        self._list_proj_btn.clicked.connect(self._list_projects)
        proj_row.addWidget(self._project_input)
        proj_row.addWidget(self._list_proj_btn)
        lay_auth.addLayout(proj_row)

        self._proj_combo = QComboBox()
        self._proj_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._proj_combo.setVisible(False)
        self._proj_combo.currentIndexChanged.connect(self._on_proj_combo_changed)
        lay_auth.addWidget(self._proj_combo)

        self._save_profile_btn_gcp = _ghost_btn("Save as profile…")
        self._save_profile_btn_gcp.clicked.connect(self._on_save_gcp_profile)
        self._save_profile_btn_gcp.setEnabled(False)
        lay_auth.addWidget(self._save_profile_btn_gcp)

        self._connect_btn_gcp = _primary_btn(i18n.tr("gcp_connect"))
        self._connect_btn_gcp.clicked.connect(self._do_connect)
        lay_auth.addWidget(self._connect_btn_gcp)

        self._auth_status = QLabel("")
        self._auth_status.setStyleSheet(lbl_style)
        self._auth_status.setWordWrap(True)
        lay_auth.addWidget(self._auth_status)

        vlay.addWidget(card_auth)

        # ── Card: Filter ─────────────────────────────────────────────
        card_filt, lay_filt, _ = make_card(i18n.tr("gcp_card_filter"))

        lay_filt.addWidget(self._lbl(lbl_style, i18n.tr("gcp_field_resource")))
        self._resource_combo = QComboBox()
        self._resource_combo.addItems(gcp_utils.RESOURCE_TYPES)
        self._resource_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        lay_filt.addWidget(self._resource_combo)

        lay_filt.addWidget(self._lbl(lbl_style, i18n.tr("gcp_field_severity")))
        self._severity_combo = QComboBox()
        self._severity_combo.addItems(gcp_utils.SEVERITIES)
        self._severity_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        lay_filt.addWidget(self._severity_combo)

        lay_filt.addWidget(self._lbl(lbl_style, i18n.tr("gcp_field_custom")))
        self._custom_input = QLineEdit()
        self._custom_input.setPlaceholderText(i18n.tr("gcp_custom_hint"))
        self._custom_input.setStyleSheet(field_style)
        lay_filt.addWidget(self._custom_input)

        lb_row = QHBoxLayout()
        lb_row.addWidget(self._lbl(lbl_style, i18n.tr("gcp_field_lookback")))
        lb_row.addStretch()
        self._lookback_spin = QSpinBox()
        self._lookback_spin.setRange(1, 168)
        self._lookback_spin.setValue(1)
        self._lookback_spin.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        lb_row.addWidget(self._lookback_spin)
        lay_filt.addLayout(lb_row)

        iv_row = QHBoxLayout()
        iv_row.addWidget(self._lbl(lbl_style, i18n.tr("gcp_field_interval")))
        iv_row.addStretch()
        self._interval_spin_gcp = QSpinBox()
        self._interval_spin_gcp.setRange(1, 60)
        self._interval_spin_gcp.setValue(5)
        self._interval_spin_gcp.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row.addWidget(self._interval_spin_gcp)
        lay_filt.addLayout(iv_row)

        self._open_mode_gcp = OpenModeWidget()
        lay_filt.addWidget(self._open_mode_gcp)

        self._open_btn_gcp = _primary_btn(i18n.tr("gcp_open"))
        self._open_btn_gcp.clicked.connect(self._on_open)
        self._open_btn_gcp.setEnabled(False)
        lay_filt.addWidget(self._open_btn_gcp)

        self._card_filt = card_filt
        card_filt.setVisible(False)
        vlay.addWidget(card_filt)
        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _on_auth_mode_changed(self, idx: int) -> None:
        self._sa_widget.setVisible(idx == 1)

    def _browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Service Account Key", "", "JSON (*.json)")
        if path:
            self._key_input.setText(path)

    def _list_projects(self) -> None:
        self._list_proj_btn.setEnabled(False)
        key_path = self._key_input.text().strip() if self._auth_combo.currentIndex() == 1 else None
        self._projects_worker = _GCPListProjectsWorker(key_path)
        self._projects_worker.success.connect(self._on_projects_listed)
        self._projects_worker.failure.connect(lambda e: (
            self._auth_status.setText(e),
            self._list_proj_btn.setEnabled(True),
        ))
        self._projects_worker.start()

    def _on_projects_listed(self, projects: list) -> None:
        self._list_proj_btn.setEnabled(True)
        self._proj_combo.clear()
        if projects:
            for p in projects:
                self._proj_combo.addItem(f"{p['name']}  ({p['id']})", userData=p["id"])
            self._proj_combo.setVisible(True)
            self._project_input.setVisible(False)
        else:
            self._auth_status.setText(i18n.tr("gcp_no_projects"))

    def _on_proj_combo_changed(self, _idx: int) -> None:
        pid = self._proj_combo.currentData()
        if pid:
            self._project_input.setText(pid)

    def _do_connect(self) -> None:
        project_id = self._project_input.text().strip()
        if not project_id:
            self._auth_status.setText(i18n.tr("gcp_field_project"))
            return
        key_path = self._key_input.text().strip() if self._auth_combo.currentIndex() == 1 else None
        self._connect_btn_gcp.setEnabled(False)
        self._auth_status.setText(i18n.tr("gcp_connecting"))
        self._auth_status.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._connect_worker = _GCPConnectWorker(project_id, key_path)
        self._connect_worker.success.connect(self._on_connected)
        self._connect_worker.failure.connect(self._on_connect_fail_gcp)
        self._connect_worker.start()

    def _on_connected(self, client: object) -> None:
        self._client = client
        self._auth_status.setText(i18n.tr("gcp_connected"))
        self._auth_status.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_gcp.setEnabled(True)
        self._open_btn_gcp.setEnabled(True)
        self._save_profile_btn_gcp.setEnabled(True)
        self._card_filt.setVisible(True)

    def _load_gcp_profile(self, p: dict) -> None:
        self._auth_combo.setCurrentIndex(p.get("auth_mode", 0))
        self._key_input.setText(p.get("key_path", ""))
        self._project_input.setText(p.get("project_id", ""))
        self._on_auth_mode_changed(self._auth_combo.currentIndex())

    def _on_save_gcp_profile(self) -> None:
        project_id = self._project_input.text().strip()
        if not project_id:
            return
        default_name = project_id
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text=default_name)
        if not ok or not name.strip():
            return
        profiles_store.upsert("gcp", name.strip(), {
            "auth_mode":  self._auth_combo.currentIndex(),
            "key_path":   self._key_input.text().strip() if self._auth_combo.currentIndex() == 1 else "",
            "project_id": project_id,
        })
        self._gcp_profile_bar.reload()

    def _on_connect_fail_gcp(self, msg: str) -> None:
        self._auth_status.setText(msg)
        self._auth_status.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_gcp.setEnabled(True)

    def _on_open(self) -> None:
        if not self._client:
            return
        project_id = self._project_input.text().strip()
        cfg = {
            "type":          "gcp",
            "project_id":    project_id,
            "auth_mode":     self._auth_combo.currentIndex(),
            "key_path":      self._key_input.text().strip() if self._auth_combo.currentIndex() == 1 else "",
            "resource_type": self._resource_combo.currentText(),
            "severity":      self._severity_combo.currentText(),
            "custom_filter": self._custom_input.text().strip(),
            "lookback_hours": self._lookback_spin.value(),
            "interval_s":    self._interval_spin_gcp.value(),
            "_client":       self._client,
        }
        self.open_tab.emit(cfg, self._open_mode_gcp.get_mode())


# ── AzurePanel ─────────────────────────────────────────────────────────────────

class _AzureConnectWorker(QThread):
    success = pyqtSignal(object, object)  # credential, logs_client
    failure = pyqtSignal(str)

    def __init__(self, tenant_id: str, client_id: str, client_secret: str,
                 workspace_id: str) -> None:
        super().__init__()
        self._tenant    = tenant_id
        self._client_id = client_id
        self._secret    = client_secret
        self._workspace = workspace_id

    def run(self) -> None:
        try:
            cred   = azure_utils.make_credential(self._tenant, self._client_id, self._secret)
            client = azure_utils.make_logs_client(cred)
            azure_utils.verify_credential(cred, self._workspace)
            self.success.emit(cred, client)
        except RuntimeError as e:
            self.failure.emit(str(e))


class AzurePanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    _ALL_TABLES: list[tuple[str, str]] = [
        (cat, tbl)
        for cat, tbls in azure_utils.TABLES.items()
        for tbl in tbls
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._credential = None
        self._logs_client = None
        self._workspace_id = ""
        self._connect_worker: _AzureConnectWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"

        # ── Saved configs card ────────────────────────────────────────
        saved_card_az, saved_lay_az, _ = make_card(i18n.tr("saved_configs"))
        self._az_profile_bar = _ProfileBar("azure", wrapper=saved_card_az)
        self._az_profile_bar.profile_loaded.connect(self._load_az_profile)
        saved_lay_az.addWidget(self._az_profile_bar)
        vlay.addWidget(saved_card_az)

        # ── Card: Auth ───────────────────────────────────────────────
        card_auth, lay_auth, _ = make_card(i18n.tr("new_config"))

        for attr, key, pw in [
            ("_tenant_input",    "azure_field_tenant",    False),
            ("_client_id_input", "azure_field_client",    False),
            ("_secret_input",    "azure_field_secret",    True),
            ("_workspace_input", "azure_field_workspace", False),
        ]:
            fld = QLineEdit()
            fld.setPlaceholderText(i18n.tr(key))
            fld.setStyleSheet(field_style)
            if pw:
                fld.setEchoMode(QLineEdit.EchoMode.Password)
            setattr(self, attr, fld)
            lay_auth.addWidget(fld)

        self._save_profile_btn_az = _ghost_btn("Save as profile…")
        self._save_profile_btn_az.clicked.connect(self._on_save_az_profile)
        self._save_profile_btn_az.setEnabled(False)
        lay_auth.addWidget(self._save_profile_btn_az)

        self._connect_btn_az = _primary_btn(i18n.tr("azure_connect"))
        self._connect_btn_az.clicked.connect(self._do_connect)
        lay_auth.addWidget(self._connect_btn_az)

        self._auth_status_az = QLabel("")
        self._auth_status_az.setStyleSheet(lbl_style)
        self._auth_status_az.setWordWrap(True)
        lay_auth.addWidget(self._auth_status_az)

        vlay.addWidget(card_auth)

        # ── Tabs: Tables / KQL ───────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: none; background: {C_PANEL}; }}"
            f"QTabBar::tab {{ background: {C_PANEL}; color: {C_MUTED};"
            f" padding: 6px 12px; border: none; font-size: 11px; }}"
            f"QTabBar::tab:selected {{ color: {C_TEXT}; border-bottom: 2px solid {C_ACCENT}; }}"
        )
        self._tabs.setVisible(False)
        vlay.addWidget(self._tabs)

        # ── Tab 0: Tables ────────────────────────────────────────────
        tab_tables = QWidget()
        tt_lay = QVBoxLayout(tab_tables)
        tt_lay.setContentsMargins(0, 8, 0, 0)
        tt_lay.setSpacing(8)

        card_tbl, lay_tbl, _ = make_card(i18n.tr("azure_card_table"))

        self._table_search = QLineEdit()
        self._table_search.setPlaceholderText(i18n.tr("azure_search_table"))
        self._table_search.setStyleSheet(field_style)
        self._table_search.textChanged.connect(self._filter_tables)
        lay_tbl.addWidget(self._table_search)

        self._table_list = QListWidget()
        self._table_list.setFixedHeight(220)
        self._table_list.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; font-size: 12px;"
        )
        self._populate_table_list("")
        self._table_list.currentItemChanged.connect(self._on_table_selected)
        lay_tbl.addWidget(self._table_list)

        ts_row = QHBoxLayout()
        ts_row.addWidget(self._lbl(lbl_style, i18n.tr("azure_field_timespan")))
        ts_row.addStretch()
        self._timespan_spin = QSpinBox()
        self._timespan_spin.setRange(1, 720)
        self._timespan_spin.setValue(1)
        self._timespan_spin.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        ts_row.addWidget(self._timespan_spin)
        lay_tbl.addLayout(ts_row)

        iv_row_t = QHBoxLayout()
        iv_row_t.addWidget(self._lbl(lbl_style, i18n.tr("azure_field_interval")))
        iv_row_t.addStretch()
        self._interval_spin_az_t = QSpinBox()
        self._interval_spin_az_t.setRange(5, 300)
        self._interval_spin_az_t.setValue(10)
        self._interval_spin_az_t.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row_t.addWidget(self._interval_spin_az_t)
        lay_tbl.addLayout(iv_row_t)

        self._open_mode_az_t = OpenModeWidget()
        lay_tbl.addWidget(self._open_mode_az_t)

        self._open_btn_az_t = _primary_btn(i18n.tr("azure_open_table"))
        self._open_btn_az_t.clicked.connect(self._on_open_table)
        self._open_btn_az_t.setEnabled(False)
        lay_tbl.addWidget(self._open_btn_az_t)

        tt_lay.addWidget(card_tbl)
        self._tabs.addTab(tab_tables, i18n.tr("azure_tab_tables"))

        # ── Tab 1: KQL ───────────────────────────────────────────────
        tab_kql = QWidget()
        kql_lay = QVBoxLayout(tab_kql)
        kql_lay.setContentsMargins(0, 8, 0, 0)
        kql_lay.setSpacing(8)

        card_kql, lay_kql, _ = make_card(i18n.tr("azure_card_kql"))

        self._kql_edit = QTextEdit()
        self._kql_edit.setPlaceholderText(
            "AppTraces\n| where TimeGenerated > ago(1h)\n| order by TimeGenerated asc"
        )
        self._kql_edit.setFixedHeight(160)
        self._kql_edit.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px; font-family: monospace;"
        )
        lay_kql.addWidget(self._kql_edit)

        hint_kql = QLabel(i18n.tr("azure_kql_hint"))
        hint_kql.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
        hint_kql.setWordWrap(True)
        lay_kql.addWidget(hint_kql)

        ts_row_k = QHBoxLayout()
        ts_row_k.addWidget(self._lbl(lbl_style, i18n.tr("azure_field_timespan")))
        ts_row_k.addStretch()
        self._timespan_spin_kql = QSpinBox()
        self._timespan_spin_kql.setRange(1, 720)
        self._timespan_spin_kql.setValue(1)
        self._timespan_spin_kql.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        ts_row_k.addWidget(self._timespan_spin_kql)
        lay_kql.addLayout(ts_row_k)

        iv_row_k = QHBoxLayout()
        iv_row_k.addWidget(self._lbl(lbl_style, i18n.tr("azure_field_interval")))
        iv_row_k.addStretch()
        self._interval_spin_az_k = QSpinBox()
        self._interval_spin_az_k.setRange(5, 300)
        self._interval_spin_az_k.setValue(10)
        self._interval_spin_az_k.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row_k.addWidget(self._interval_spin_az_k)
        lay_kql.addLayout(iv_row_k)

        self._open_mode_az_k = OpenModeWidget()
        lay_kql.addWidget(self._open_mode_az_k)

        self._open_btn_az_k = _primary_btn(i18n.tr("azure_open_kql"))
        self._open_btn_az_k.clicked.connect(self._on_open_kql)
        self._open_btn_az_k.setEnabled(False)
        lay_kql.addWidget(self._open_btn_az_k)

        kql_lay.addWidget(card_kql)
        self._tabs.addTab(tab_kql, i18n.tr("azure_tab_kql"))

        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _populate_table_list(self, search: str) -> None:
        self._table_list.clear()
        search = search.lower()
        current_cat = None
        for cat, tbl in self._ALL_TABLES:
            if search and search not in tbl.lower() and search not in cat.lower():
                continue
            if cat != current_cat:
                hdr = QListWidgetItem(f"── {cat} ──")
                hdr.setFlags(Qt.ItemFlag.NoItemFlags)
                hdr.setForeground(QColor(C_MUTED))
                self._table_list.addItem(hdr)
                current_cat = cat
            item = QListWidgetItem(f"   {tbl}")
            item.setData(Qt.ItemDataRole.UserRole, tbl)
            self._table_list.addItem(item)

    def _filter_tables(self, text: str) -> None:
        self._populate_table_list(text)

    def _on_table_selected(self, current, _prev) -> None:
        if current and current.data(Qt.ItemDataRole.UserRole):
            self._open_btn_az_t.setEnabled(self._logs_client is not None)

    # ── Auth ──────────────────────────────────────────────────────────────────

    def _do_connect(self) -> None:
        tenant = self._tenant_input.text().strip()
        cid    = self._client_id_input.text().strip()
        secret = self._secret_input.text().strip()
        ws     = self._workspace_input.text().strip()
        if not all([tenant, cid, secret, ws]):
            self._auth_status_az.setText("All fields are required.")
            self._auth_status_az.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
            return
        self._workspace_id = ws
        self._connect_btn_az.setEnabled(False)
        self._auth_status_az.setText(i18n.tr("azure_connecting"))
        self._auth_status_az.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")

        self._connect_worker = _AzureConnectWorker(tenant, cid, secret, ws)
        self._connect_worker.success.connect(self._on_az_connected)
        self._connect_worker.failure.connect(self._on_az_connect_fail)
        self._connect_worker.start()

    def _on_az_connected(self, cred: object, client: object) -> None:
        self._credential  = cred
        self._logs_client = client
        self._auth_status_az.setText(i18n.tr("azure_connected"))
        self._auth_status_az.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_az.setEnabled(True)
        self._tabs.setVisible(True)
        self._open_btn_az_k.setEnabled(True)
        self._save_profile_btn_az.setEnabled(True)

    def _load_az_profile(self, p: dict) -> None:
        self._tenant_input.setText(p.get("tenant_id", ""))
        self._client_id_input.setText(p.get("client_id", ""))
        self._secret_input.setText(p.get("client_secret", ""))
        self._workspace_input.setText(p.get("workspace_id", ""))

    def _on_save_az_profile(self) -> None:
        workspace_id = self._workspace_input.text().strip()
        tenant_id    = self._tenant_input.text().strip()
        if not workspace_id or not tenant_id:
            return
        default_name = f"{tenant_id[:8]}…"
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text=default_name)
        if not ok or not name.strip():
            return
        profiles_store.upsert("azure", name.strip(), {
            "tenant_id":     tenant_id,
            "client_id":     self._client_id_input.text().strip(),
            "client_secret": self._secret_input.text().strip(),
            "workspace_id":  workspace_id,
        })
        self._az_profile_bar.reload()

    def _on_az_connect_fail(self, msg: str) -> None:
        self._auth_status_az.setText(msg)
        self._auth_status_az.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_az.setEnabled(True)

    # ── Open ──────────────────────────────────────────────────────────────────

    def _on_open_table(self) -> None:
        items = self._table_list.selectedItems()
        if not items:
            return
        tbl = items[0].data(Qt.ItemDataRole.UserRole)
        if not tbl:
            return
        query = azure_utils.build_table_query(tbl)
        cfg = {
            "type":          "azure",
            "workspace_id":  self._workspace_id,
            "query":         query,
            "label":         tbl,
            "timespan_hours": self._timespan_spin.value(),
            "interval_s":    self._interval_spin_az_t.value(),
            "_logs_client":  self._logs_client,
        }
        self.open_tab.emit(cfg, self._open_mode_az_t.get_mode())

    def _on_open_kql(self) -> None:
        query = self._kql_edit.toPlainText().strip()
        if not query:
            return
        cfg = {
            "type":          "azure",
            "workspace_id":  self._workspace_id,
            "query":         query,
            "label":         "KQL",
            "timespan_hours": self._timespan_spin_kql.value(),
            "interval_s":    self._interval_spin_az_k.value(),
            "_logs_client":  self._logs_client,
        }
        self.open_tab.emit(cfg, self._open_mode_az_k.get_mode())


# ── LokiPanel ─────────────────────────────────────────────────────────────────

class _LokiConnectWorker(QThread):
    success = pyqtSignal(list)   # label names
    failure = pyqtSignal(str)

    def __init__(self, url: str, username: str, password: str, token: str) -> None:
        super().__init__()
        self._url      = url
        self._username = username
        self._password = password
        self._token    = token

    def run(self) -> None:
        try:
            labels = loki_utils.verify_connection(
                self._url, self._username, self._password, self._token
            )
            self.success.emit(labels)
        except RuntimeError as e:
            self.failure.emit(str(e))


class LokiPanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._labels: list[str] = []
        self._connect_worker: _LokiConnectWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"

        # ── Saved configs card ────────────────────────────────────────
        saved_card_loki, saved_lay_loki, _ = make_card(i18n.tr("saved_configs"))
        self._loki_profile_bar = _ProfileBar("loki", wrapper=saved_card_loki)
        self._loki_profile_bar.profile_loaded.connect(self._load_loki_profile)
        saved_lay_loki.addWidget(self._loki_profile_bar)
        vlay.addWidget(saved_card_loki)

        # ── Card: Connection ─────────────────────────────────────────
        card_conn, lay_conn, _ = make_card(i18n.tr("new_config"))

        lay_conn.addWidget(self._lbl(lbl_style, i18n.tr("loki_field_url")))
        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("http://localhost:3100")
        self._url_input.setStyleSheet(field_style)
        lay_conn.addWidget(self._url_input)

        self._auth_combo = QComboBox()
        self._auth_combo.addItems([
            i18n.tr("loki_auth_none"),
            i18n.tr("loki_auth_basic"),
            i18n.tr("loki_auth_token"),
        ])
        self._auth_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._auth_combo.currentIndexChanged.connect(self._on_auth_mode_changed)
        lay_conn.addWidget(self._auth_combo)

        # Basic auth fields
        self._basic_widget = QWidget()
        basic_lay = QVBoxLayout(self._basic_widget)
        basic_lay.setContentsMargins(0, 4, 0, 0)
        basic_lay.setSpacing(4)
        self._user_input = QLineEdit()
        self._user_input.setPlaceholderText(i18n.tr("loki_field_username"))
        self._user_input.setStyleSheet(field_style)
        basic_lay.addWidget(self._user_input)
        self._pass_input = QLineEdit()
        self._pass_input.setPlaceholderText(i18n.tr("loki_field_password"))
        self._pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass_input.setStyleSheet(field_style)
        basic_lay.addWidget(self._pass_input)
        self._basic_widget.setVisible(False)
        lay_conn.addWidget(self._basic_widget)

        # Token field
        self._token_widget = QWidget()
        token_lay = QVBoxLayout(self._token_widget)
        token_lay.setContentsMargins(0, 4, 0, 0)
        token_lay.setSpacing(0)
        self._token_input = QLineEdit()
        self._token_input.setPlaceholderText(i18n.tr("loki_field_token"))
        self._token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._token_input.setStyleSheet(field_style)
        token_lay.addWidget(self._token_input)
        self._token_widget.setVisible(False)
        lay_conn.addWidget(self._token_widget)

        self._save_profile_btn_loki = _ghost_btn("Save as profile…")
        self._save_profile_btn_loki.clicked.connect(self._on_save_loki_profile)
        self._save_profile_btn_loki.setEnabled(False)
        lay_conn.addWidget(self._save_profile_btn_loki)

        self._connect_btn_loki = _primary_btn(i18n.tr("loki_connect"))
        self._connect_btn_loki.clicked.connect(self._do_connect)
        lay_conn.addWidget(self._connect_btn_loki)

        self._conn_status = QLabel("")
        self._conn_status.setStyleSheet(lbl_style)
        self._conn_status.setWordWrap(True)
        lay_conn.addWidget(self._conn_status)

        vlay.addWidget(card_conn)

        # ── Card: Query ──────────────────────────────────────────────
        card_query, lay_query, _ = make_card(i18n.tr("loki_card_query"))

        lay_query.addWidget(self._lbl(lbl_style, i18n.tr("loki_field_query")))
        query_row = QHBoxLayout()
        self._query_input = QLineEdit()
        self._query_input.setPlaceholderText(i18n.tr("loki_query_hint"))
        self._query_input.setStyleSheet(field_style)
        self._labels_btn = _ghost_btn(i18n.tr("loki_list_labels"))
        self._labels_btn.clicked.connect(self._show_labels_menu)
        query_row.addWidget(self._query_input)
        query_row.addWidget(self._labels_btn)
        lay_query.addLayout(query_row)

        lb_row = QHBoxLayout()
        lb_row.addWidget(self._lbl(lbl_style, i18n.tr("loki_field_lookback")))
        lb_row.addStretch()
        self._lookback_spin = QSpinBox()
        self._lookback_spin.setRange(1, 168)
        self._lookback_spin.setValue(1)
        self._lookback_spin.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        lb_row.addWidget(self._lookback_spin)
        lay_query.addLayout(lb_row)

        iv_row = QHBoxLayout()
        iv_row.addWidget(self._lbl(lbl_style, i18n.tr("loki_field_interval")))
        iv_row.addStretch()
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 60)
        self._interval_spin.setValue(5)
        self._interval_spin.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row.addWidget(self._interval_spin)
        lay_query.addLayout(iv_row)

        self._open_mode_loki = OpenModeWidget()
        lay_query.addWidget(self._open_mode_loki)

        self._open_btn_loki = _primary_btn(i18n.tr("loki_open"))
        self._open_btn_loki.clicked.connect(self._on_open)
        self._open_btn_loki.setEnabled(False)
        lay_query.addWidget(self._open_btn_loki)

        self._card_query = card_query
        card_query.setVisible(False)
        vlay.addWidget(card_query)
        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _on_auth_mode_changed(self, idx: int) -> None:
        self._basic_widget.setVisible(idx == 1)
        self._token_widget.setVisible(idx == 2)

    def _do_connect(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            self._conn_status.setText(i18n.tr("loki_field_url"))
            return
        auth = self._auth_combo.currentIndex()
        username = self._user_input.text().strip() if auth == 1 else ""
        password = self._pass_input.text() if auth == 1 else ""
        token = self._token_input.text().strip() if auth == 2 else ""
        self._connect_btn_loki.setEnabled(False)
        self._conn_status.setText(i18n.tr("loki_connecting"))
        self._conn_status.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._connect_worker = _LokiConnectWorker(url, username, password, token)
        self._connect_worker.success.connect(self._on_connected)
        self._connect_worker.failure.connect(self._on_connect_fail)
        self._connect_worker.start()

    def _on_connected(self, labels: list) -> None:
        self._labels = labels
        self._conn_status.setText(i18n.tr("loki_connected"))
        self._conn_status.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_loki.setEnabled(True)
        self._open_btn_loki.setEnabled(True)
        self._save_profile_btn_loki.setEnabled(True)
        self._card_query.setVisible(True)

    def _on_connect_fail(self, msg: str) -> None:
        self._conn_status.setText(msg)
        self._conn_status.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_loki.setEnabled(True)

    def _show_labels_menu(self) -> None:
        if not self._labels:
            self._conn_status.setText(i18n.tr("loki_no_labels"))
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu {{ background: {C_CARD}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f" border-radius: 6px; padding: 4px; }}"
            f"QMenu::item {{ padding: 4px 16px; border-radius: 4px; }}"
            f"QMenu::item:selected {{ background: {C_SEL_BG}; }}"
        )
        for label in sorted(self._labels):
            act = menu.addAction(label)
            act.triggered.connect(lambda checked, lbl=label: self._insert_label(lbl))
        menu.exec(self._labels_btn.mapToGlobal(self._labels_btn.rect().bottomLeft()))

    def _insert_label(self, label: str) -> None:
        current = self._query_input.text().strip()
        if not current:
            self._query_input.setText(f'{{{label}="..."}}')
        else:
            self._query_input.setText(current + f', {label}=""')

    def _load_loki_profile(self, p: dict) -> None:
        self._url_input.setText(p.get("url", ""))
        auth_mode = p.get("auth_mode", 0)
        self._auth_combo.setCurrentIndex(auth_mode)
        self._user_input.setText(p.get("username", ""))
        self._pass_input.setText(p.get("password", ""))
        self._token_input.setText(p.get("token", ""))
        self._on_auth_mode_changed(auth_mode)

    def _on_save_loki_profile(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            return
        default_name = url.split("//", 1)[-1].split("/")[0]
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text=default_name)
        if not ok or not name.strip():
            return
        auth_mode = self._auth_combo.currentIndex()
        profiles_store.upsert("loki", name.strip(), {
            "url":       url,
            "auth_mode": auth_mode,
            "username":  self._user_input.text().strip() if auth_mode == 1 else "",
            "password":  self._pass_input.text() if auth_mode == 1 else "",
            "token":     self._token_input.text().strip() if auth_mode == 2 else "",
        })
        self._loki_profile_bar.reload()

    def _on_open(self) -> None:
        url = self._url_input.text().strip()
        query = self._query_input.text().strip()
        if not url or not query:
            return
        auth_mode = self._auth_combo.currentIndex()
        label = url.split("//", 1)[-1].split("/")[0]
        cfg = {
            "type":          "loki",
            "url":           url,
            "query":         query,
            "auth_mode":     auth_mode,
            "username":      self._user_input.text().strip() if auth_mode == 1 else "",
            "password":      self._pass_input.text() if auth_mode == 1 else "",
            "token":         self._token_input.text().strip() if auth_mode == 2 else "",
            "lookback_hours": self._lookback_spin.value(),
            "interval_s":    self._interval_spin.value(),
            "label":         label,
        }
        self.open_tab.emit(cfg, self._open_mode_loki.get_mode())


# ── DatadogPanel ──────────────────────────────────────────────────────────────

class _DatadogConnectWorker(QThread):
    success = pyqtSignal()
    failure = pyqtSignal(str)

    def __init__(self, base_url: str, api_key: str, app_key: str) -> None:
        super().__init__()
        self._base_url = base_url
        self._api_key  = api_key
        self._app_key  = app_key

    def run(self) -> None:
        try:
            datadog_utils.verify_connection(self._base_url, self._api_key, self._app_key)
            self.success.emit()
        except RuntimeError as e:
            self.failure.emit(str(e))


class DatadogPanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connected = False
        self._connect_worker: _DatadogConnectWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"

        # ── Saved configs card ────────────────────────────────────────
        saved_card_dd, saved_lay_dd, _ = make_card(i18n.tr("saved_configs"))
        self._dd_profile_bar = _ProfileBar("datadog", wrapper=saved_card_dd)
        self._dd_profile_bar.profile_loaded.connect(self._load_datadog_profile)
        saved_lay_dd.addWidget(self._dd_profile_bar)
        vlay.addWidget(saved_card_dd)

        # ── Card: Auth ───────────────────────────────────────────────
        card_auth, lay_auth, _ = make_card(i18n.tr("new_config"))

        lay_auth.addWidget(self._lbl(lbl_style, i18n.tr("datadog_field_site")))
        self._site_combo = QComboBox()
        self._site_combo.addItems(list(datadog_utils.DD_SITES.keys()))
        self._site_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        lay_auth.addWidget(self._site_combo)

        lay_auth.addWidget(self._lbl(lbl_style, i18n.tr("datadog_field_api_key")))
        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setStyleSheet(field_style)
        lay_auth.addWidget(self._api_key_input)

        lay_auth.addWidget(self._lbl(lbl_style, i18n.tr("datadog_field_app_key")))
        self._app_key_input = QLineEdit()
        self._app_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._app_key_input.setStyleSheet(field_style)
        lay_auth.addWidget(self._app_key_input)

        self._save_profile_btn_dd = _ghost_btn("Save as profile…")
        self._save_profile_btn_dd.clicked.connect(self._on_save_datadog_profile)
        self._save_profile_btn_dd.setEnabled(False)
        lay_auth.addWidget(self._save_profile_btn_dd)

        self._connect_btn_dd = _primary_btn(i18n.tr("datadog_connect"))
        self._connect_btn_dd.clicked.connect(self._do_connect)
        lay_auth.addWidget(self._connect_btn_dd)

        self._auth_status_dd = QLabel("")
        self._auth_status_dd.setStyleSheet(lbl_style)
        self._auth_status_dd.setWordWrap(True)
        lay_auth.addWidget(self._auth_status_dd)

        vlay.addWidget(card_auth)

        # ── Card: Query ──────────────────────────────────────────────
        card_query, lay_query, _ = make_card(i18n.tr("datadog_card_query"))

        lay_query.addWidget(self._lbl(lbl_style, i18n.tr("datadog_field_query")))
        self._dd_query_input = QLineEdit()
        self._dd_query_input.setPlaceholderText(i18n.tr("datadog_query_hint"))
        self._dd_query_input.setStyleSheet(field_style)
        self._dd_query_input.textChanged.connect(self._update_open_btn)
        lay_query.addWidget(self._dd_query_input)

        lb_row = QHBoxLayout()
        lb_row.addWidget(self._lbl(lbl_style, i18n.tr("datadog_field_lookback")))
        lb_row.addStretch()
        self._lookback_spin_dd = QSpinBox()
        self._lookback_spin_dd.setRange(1, 168)
        self._lookback_spin_dd.setValue(1)
        self._lookback_spin_dd.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        lb_row.addWidget(self._lookback_spin_dd)
        lay_query.addLayout(lb_row)

        iv_row = QHBoxLayout()
        iv_row.addWidget(self._lbl(lbl_style, i18n.tr("datadog_field_interval")))
        iv_row.addStretch()
        self._interval_spin_dd = QSpinBox()
        self._interval_spin_dd.setRange(1, 60)
        self._interval_spin_dd.setValue(10)
        self._interval_spin_dd.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row.addWidget(self._interval_spin_dd)
        lay_query.addLayout(iv_row)

        self._open_mode_dd = OpenModeWidget()
        lay_query.addWidget(self._open_mode_dd)

        self._open_btn_dd = _primary_btn(i18n.tr("datadog_open"))
        self._open_btn_dd.clicked.connect(self._on_open)
        self._open_btn_dd.setEnabled(False)
        lay_query.addWidget(self._open_btn_dd)

        self._card_query_dd = card_query
        card_query.setVisible(False)
        vlay.addWidget(card_query)
        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _update_open_btn(self) -> None:
        self._open_btn_dd.setEnabled(
            bool(self._dd_query_input.text().strip()) and self._connected
        )

    def _do_connect(self) -> None:
        site_name = self._site_combo.currentText()
        base_url  = datadog_utils.DD_SITES.get(site_name, "https://api.datadoghq.com")
        api_key   = self._api_key_input.text().strip()
        app_key   = self._app_key_input.text().strip()
        if not api_key or not app_key:
            self._auth_status_dd.setText("API Key and App Key are required")
            self._auth_status_dd.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
            return
        self._connect_btn_dd.setEnabled(False)
        self._auth_status_dd.setText(i18n.tr("datadog_connecting"))
        self._auth_status_dd.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._connect_worker = _DatadogConnectWorker(base_url, api_key, app_key)
        self._connect_worker.success.connect(self._on_connected)
        self._connect_worker.failure.connect(self._on_connect_fail_dd)
        self._connect_worker.start()

    def _on_connected(self) -> None:
        self._connected = True
        self._auth_status_dd.setText(i18n.tr("datadog_connected"))
        self._auth_status_dd.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_dd.setEnabled(True)
        self._save_profile_btn_dd.setEnabled(True)
        self._card_query_dd.setVisible(True)
        self._update_open_btn()

    def _on_connect_fail_dd(self, msg: str) -> None:
        self._auth_status_dd.setText(msg)
        self._auth_status_dd.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_dd.setEnabled(True)

    def _load_datadog_profile(self, p: dict) -> None:
        site_name = p.get("site", "US1 (datadoghq.com)")
        idx = self._site_combo.findText(site_name)
        if idx >= 0:
            self._site_combo.setCurrentIndex(idx)
        self._api_key_input.setText(p.get("api_key", ""))
        self._app_key_input.setText(p.get("app_key", ""))

    def _on_save_datadog_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text="datadog")
        if not ok or not name.strip():
            return
        profiles_store.upsert("datadog", name.strip(), {
            "site":    self._site_combo.currentText(),
            "api_key": self._api_key_input.text().strip(),
            "app_key": self._app_key_input.text().strip(),
        })
        self._dd_profile_bar.reload()

    def _on_open(self) -> None:
        site_name = self._site_combo.currentText()
        base_url  = datadog_utils.DD_SITES.get(site_name, "https://api.datadoghq.com")
        query = self._dd_query_input.text().strip() or "*"
        cfg = {
            "type":          "datadog",
            "base_url":      base_url,
            "query":         query,
            "api_key":       self._api_key_input.text().strip(),
            "app_key":       self._app_key_input.text().strip(),
            "lookback_hours": self._lookback_spin_dd.value(),
            "interval_s":    self._interval_spin_dd.value(),
            "label":         site_name.split(" ")[0],
        }
        self.open_tab.emit(cfg, self._open_mode_dd.get_mode())


# ── ElasticPanel ──────────────────────────────────────────────────────────────

class _ElasticConnectWorker(QThread):
    success = pyqtSignal(list)   # index names
    failure = pyqtSignal(str)

    def __init__(self, url: str, api_key: str, username: str, password: str) -> None:
        super().__init__()
        self._url      = url
        self._api_key  = api_key
        self._username = username
        self._password = password

    def run(self) -> None:
        try:
            elastic_utils.verify_connection(self._url, self._api_key, self._username, self._password)
            indices = elastic_utils.list_indices(self._url, self._api_key, self._username, self._password)
            self.success.emit(indices)
        except RuntimeError as e:
            self.failure.emit(str(e))


class ElasticPanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connect_worker: _ElasticConnectWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"

        # ── Saved configs card ────────────────────────────────────────
        saved_card_es, saved_lay_es, _ = make_card(i18n.tr("saved_configs"))
        self._elastic_profile_bar = _ProfileBar("elastic", wrapper=saved_card_es)
        self._elastic_profile_bar.profile_loaded.connect(self._load_elastic_profile)
        saved_lay_es.addWidget(self._elastic_profile_bar)
        vlay.addWidget(saved_card_es)

        # ── Card: Connection ─────────────────────────────────────────
        card_conn, lay_conn, _ = make_card(i18n.tr("new_config"))

        lay_conn.addWidget(self._lbl(lbl_style, i18n.tr("elastic_field_url")))
        self._es_url_input = QLineEdit()
        self._es_url_input.setPlaceholderText("http://localhost:9200")
        self._es_url_input.setStyleSheet(field_style)
        lay_conn.addWidget(self._es_url_input)

        self._es_auth_combo = QComboBox()
        self._es_auth_combo.addItems([
            i18n.tr("elastic_auth_none"),
            i18n.tr("elastic_auth_apikey"),
            i18n.tr("elastic_auth_basic"),
        ])
        self._es_auth_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._es_auth_combo.currentIndexChanged.connect(self._on_auth_mode_changed_es)
        lay_conn.addWidget(self._es_auth_combo)

        self._es_apikey_widget = QWidget()
        ak_lay = QVBoxLayout(self._es_apikey_widget)
        ak_lay.setContentsMargins(0, 4, 0, 0)
        ak_lay.setSpacing(0)
        self._es_apikey_input = QLineEdit()
        self._es_apikey_input.setPlaceholderText(i18n.tr("elastic_field_apikey"))
        self._es_apikey_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._es_apikey_input.setStyleSheet(field_style)
        ak_lay.addWidget(self._es_apikey_input)
        self._es_apikey_widget.setVisible(False)
        lay_conn.addWidget(self._es_apikey_widget)

        self._es_basic_widget = QWidget()
        bas_lay = QVBoxLayout(self._es_basic_widget)
        bas_lay.setContentsMargins(0, 4, 0, 0)
        bas_lay.setSpacing(4)
        self._es_user_input = QLineEdit()
        self._es_user_input.setPlaceholderText(i18n.tr("elastic_field_username"))
        self._es_user_input.setStyleSheet(field_style)
        bas_lay.addWidget(self._es_user_input)
        self._es_pass_input = QLineEdit()
        self._es_pass_input.setPlaceholderText(i18n.tr("elastic_field_password"))
        self._es_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._es_pass_input.setStyleSheet(field_style)
        bas_lay.addWidget(self._es_pass_input)
        self._es_basic_widget.setVisible(False)
        lay_conn.addWidget(self._es_basic_widget)

        self._save_profile_btn_es = _ghost_btn("Save as profile…")
        self._save_profile_btn_es.clicked.connect(self._on_save_elastic_profile)
        self._save_profile_btn_es.setEnabled(False)
        lay_conn.addWidget(self._save_profile_btn_es)

        self._connect_btn_es = _primary_btn(i18n.tr("elastic_connect"))
        self._connect_btn_es.clicked.connect(self._do_connect)
        lay_conn.addWidget(self._connect_btn_es)

        self._conn_status_es = QLabel("")
        self._conn_status_es.setStyleSheet(lbl_style)
        self._conn_status_es.setWordWrap(True)
        lay_conn.addWidget(self._conn_status_es)

        vlay.addWidget(card_conn)

        # ── Card: Query ──────────────────────────────────────────────
        card_query, lay_query, _ = make_card(i18n.tr("elastic_card_query"))

        lay_query.addWidget(self._lbl(lbl_style, i18n.tr("elastic_field_index")))
        idx_row = QHBoxLayout()
        self._es_index_input = QLineEdit()
        self._es_index_input.setPlaceholderText("logs-*")
        self._es_index_input.setStyleSheet(field_style)
        self._es_index_combo = QComboBox()
        self._es_index_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._es_index_combo.setVisible(False)
        self._es_index_combo.currentTextChanged.connect(
            lambda t: self._es_index_input.setText(t)
        )
        idx_row.addWidget(self._es_index_input)
        idx_row.addWidget(self._es_index_combo)
        lay_query.addLayout(idx_row)

        lay_query.addWidget(self._lbl(lbl_style, i18n.tr("elastic_field_ts")))
        self._es_ts_input = QLineEdit()
        self._es_ts_input.setPlaceholderText("@timestamp")
        self._es_ts_input.setText("@timestamp")
        self._es_ts_input.setStyleSheet(field_style)
        lay_query.addWidget(self._es_ts_input)

        lay_query.addWidget(self._lbl(lbl_style, i18n.tr("elastic_field_query")))
        self._es_query_input = QLineEdit()
        self._es_query_input.setPlaceholderText(i18n.tr("elastic_query_hint"))
        self._es_query_input.setStyleSheet(field_style)
        lay_query.addWidget(self._es_query_input)

        lb_row = QHBoxLayout()
        lb_row.addWidget(self._lbl(lbl_style, i18n.tr("elastic_field_lookback")))
        lb_row.addStretch()
        self._lookback_spin_es = QSpinBox()
        self._lookback_spin_es.setRange(1, 168)
        self._lookback_spin_es.setValue(1)
        self._lookback_spin_es.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        lb_row.addWidget(self._lookback_spin_es)
        lay_query.addLayout(lb_row)

        iv_row = QHBoxLayout()
        iv_row.addWidget(self._lbl(lbl_style, i18n.tr("elastic_field_interval")))
        iv_row.addStretch()
        self._interval_spin_es = QSpinBox()
        self._interval_spin_es.setRange(1, 60)
        self._interval_spin_es.setValue(10)
        self._interval_spin_es.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row.addWidget(self._interval_spin_es)
        lay_query.addLayout(iv_row)

        self._open_mode_es = OpenModeWidget()
        lay_query.addWidget(self._open_mode_es)

        self._open_btn_es = _primary_btn(i18n.tr("elastic_open"))
        self._open_btn_es.clicked.connect(self._on_open)
        self._open_btn_es.setEnabled(False)
        lay_query.addWidget(self._open_btn_es)

        self._card_query_es = card_query
        card_query.setVisible(False)
        vlay.addWidget(card_query)
        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _on_auth_mode_changed_es(self, idx: int) -> None:
        self._es_apikey_widget.setVisible(idx == 1)
        self._es_basic_widget.setVisible(idx == 2)

    def _do_connect(self) -> None:
        url = self._es_url_input.text().strip()
        if not url:
            return
        auth = self._es_auth_combo.currentIndex()
        api_key  = self._es_apikey_input.text().strip() if auth == 1 else ""
        username = self._es_user_input.text().strip()   if auth == 2 else ""
        password = self._es_pass_input.text()           if auth == 2 else ""
        self._connect_btn_es.setEnabled(False)
        self._conn_status_es.setText(i18n.tr("elastic_connecting"))
        self._conn_status_es.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._connect_worker = _ElasticConnectWorker(url, api_key, username, password)
        self._connect_worker.success.connect(self._on_connected_es)
        self._connect_worker.failure.connect(self._on_connect_fail_es)
        self._connect_worker.start()

    def _on_connected_es(self, indices: list) -> None:
        self._conn_status_es.setText(i18n.tr("elastic_connected"))
        self._conn_status_es.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_es.setEnabled(True)
        self._save_profile_btn_es.setEnabled(True)
        self._card_query_es.setVisible(True)
        self._open_btn_es.setEnabled(True)
        if indices:
            self._es_index_combo.clear()
            self._es_index_combo.addItems(indices)
            self._es_index_combo.setVisible(True)
            self._es_index_input.setVisible(False)
        else:
            self._conn_status_es.setText(i18n.tr("elastic_no_indices"))

    def _on_connect_fail_es(self, msg: str) -> None:
        self._conn_status_es.setText(msg)
        self._conn_status_es.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_es.setEnabled(True)

    def _load_elastic_profile(self, p: dict) -> None:
        self._es_url_input.setText(p.get("url", ""))
        auth = p.get("auth_mode", 0)
        self._es_auth_combo.setCurrentIndex(auth)
        self._es_apikey_input.setText(p.get("api_key", ""))
        self._es_user_input.setText(p.get("username", ""))
        self._es_pass_input.setText(p.get("password", ""))
        self._on_auth_mode_changed_es(auth)

    def _on_save_elastic_profile(self) -> None:
        url = self._es_url_input.text().strip()
        if not url:
            return
        default_name = url.split("//", 1)[-1].split("/")[0]
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text=default_name)
        if not ok or not name.strip():
            return
        auth = self._es_auth_combo.currentIndex()
        profiles_store.upsert("elastic", name.strip(), {
            "url":      url,
            "auth_mode": auth,
            "api_key":  self._es_apikey_input.text().strip() if auth == 1 else "",
            "username": self._es_user_input.text().strip()   if auth == 2 else "",
            "password": self._es_pass_input.text()           if auth == 2 else "",
        })
        self._elastic_profile_bar.reload()

    def _on_open(self) -> None:
        url   = self._es_url_input.text().strip()
        index = self._es_index_input.text().strip() or self._es_index_combo.currentText()
        if not url or not index:
            return
        auth = self._es_auth_combo.currentIndex()
        label = f"{url.split('//')[-1].split('/')[0]}/{index}"
        cfg = {
            "type":          "elastic",
            "url":           url,
            "index":         index,
            "query":         self._es_query_input.text().strip() or "*",
            "auth_mode":     auth,
            "api_key":       self._es_apikey_input.text().strip() if auth == 1 else "",
            "username":      self._es_user_input.text().strip()   if auth == 2 else "",
            "password":      self._es_pass_input.text()           if auth == 2 else "",
            "ts_field":      self._es_ts_input.text().strip() or "@timestamp",
            "lookback_hours": self._lookback_spin_es.value(),
            "interval_s":    self._interval_spin_es.value(),
            "label":         label,
        }
        self.open_tab.emit(cfg, self._open_mode_es.get_mode())


# ── RailwayPanel ──────────────────────────────────────────────────────────────

class _RailwayConnectWorker(QThread):
    success = pyqtSignal(list)   # list of project dicts
    failure = pyqtSignal(str)

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def run(self) -> None:
        try:
            projects = railway_utils.list_projects(self._token)
            self.success.emit(projects)
        except RuntimeError as e:
            self.failure.emit(str(e))


class RailwayPanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._projects: list[dict] = []
        self._connect_worker: _RailwayConnectWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"
        list_style = (
            f"QListWidget {{ background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f" border-radius: 4px; font-size: 12px; }}"
            f"QListWidget::item:selected {{ background: {C_SEL_BG}; }}"
        )

        # ── Saved configs card ────────────────────────────────────────
        saved_card_rw, saved_lay_rw, _ = make_card(i18n.tr("saved_configs"))
        self._railway_profile_bar = _ProfileBar("railway", wrapper=saved_card_rw)
        self._railway_profile_bar.profile_loaded.connect(self._load_railway_profile)
        saved_lay_rw.addWidget(self._railway_profile_bar)
        vlay.addWidget(saved_card_rw)

        # ── Card: Auth ───────────────────────────────────────────────
        card_auth, lay_auth, _ = make_card(i18n.tr("new_config"))

        lay_auth.addWidget(self._lbl(lbl_style, i18n.tr("railway_field_token")))
        self._railway_token_input = QLineEdit()
        self._railway_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._railway_token_input.setStyleSheet(field_style)
        lay_auth.addWidget(self._railway_token_input)

        self._save_profile_btn_railway = _ghost_btn("Save as profile…")
        self._save_profile_btn_railway.clicked.connect(self._on_save_railway_profile)
        self._save_profile_btn_railway.setEnabled(False)
        lay_auth.addWidget(self._save_profile_btn_railway)

        self._connect_btn_railway = _primary_btn(i18n.tr("railway_connect"))
        self._connect_btn_railway.clicked.connect(self._do_connect)
        lay_auth.addWidget(self._connect_btn_railway)

        self._conn_status_railway = QLabel("")
        self._conn_status_railway.setStyleSheet(lbl_style)
        self._conn_status_railway.setWordWrap(True)
        lay_auth.addWidget(self._conn_status_railway)

        vlay.addWidget(card_auth)

        # ── Card: Project ────────────────────────────────────────────
        card_proj, lay_proj, _ = make_card(i18n.tr("railway_card_project"))

        self._project_list = QListWidget()
        self._project_list.setMaximumHeight(140)
        self._project_list.setStyleSheet(list_style)
        self._project_list.currentRowChanged.connect(self._on_project_selected)
        lay_proj.addWidget(self._project_list)

        self._card_proj = card_proj
        card_proj.setVisible(False)
        vlay.addWidget(card_proj)

        # ── Card: Service ────────────────────────────────────────────
        card_svc, lay_svc, _ = make_card(i18n.tr("railway_card_service"))

        self._service_list = QListWidget()
        self._service_list.setMaximumHeight(120)
        self._service_list.setStyleSheet(list_style)
        lay_svc.addWidget(self._service_list)

        iv_row = QHBoxLayout()
        iv_row.addWidget(self._lbl(lbl_style, i18n.tr("railway_field_interval")))
        iv_row.addStretch()
        self._interval_spin_railway = QSpinBox()
        self._interval_spin_railway.setRange(1, 60)
        self._interval_spin_railway.setValue(10)
        self._interval_spin_railway.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row.addWidget(self._interval_spin_railway)
        lay_svc.addLayout(iv_row)

        self._open_mode_railway = OpenModeWidget()
        lay_svc.addWidget(self._open_mode_railway)

        self._open_btn_railway = _primary_btn(i18n.tr("railway_open"))
        self._open_btn_railway.clicked.connect(self._on_open)
        self._open_btn_railway.setEnabled(False)
        lay_svc.addWidget(self._open_btn_railway)

        self._card_svc = card_svc
        card_svc.setVisible(False)
        vlay.addWidget(card_svc)
        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _do_connect(self) -> None:
        token = self._railway_token_input.text().strip()
        if not token:
            return
        self._connect_btn_railway.setEnabled(False)
        self._conn_status_railway.setText(i18n.tr("railway_connecting"))
        self._conn_status_railway.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._connect_worker = _RailwayConnectWorker(token)
        self._connect_worker.success.connect(self._on_connected_railway)
        self._connect_worker.failure.connect(self._on_connect_fail_railway)
        self._connect_worker.start()

    def _on_connected_railway(self, projects: list) -> None:
        self._projects = projects
        self._conn_status_railway.setText(i18n.tr("railway_connected"))
        self._conn_status_railway.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_railway.setEnabled(True)
        self._save_profile_btn_railway.setEnabled(True)
        self._project_list.clear()
        if projects:
            for p in projects:
                self._project_list.addItem(p["name"])
            self._card_proj.setVisible(True)
        else:
            self._conn_status_railway.setText(i18n.tr("railway_no_projects"))

    def _on_connect_fail_railway(self, msg: str) -> None:
        self._conn_status_railway.setText(msg)
        self._conn_status_railway.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_railway.setEnabled(True)

    def _on_project_selected(self, row: int) -> None:
        if row < 0 or row >= len(self._projects):
            return
        project = self._projects[row]
        services = project.get("services", [])
        self._service_list.clear()
        if services:
            for svc in services:
                self._service_list.addItem(svc["name"])
            self._service_list.itemSelectionChanged.connect(
                lambda: self._open_btn_railway.setEnabled(
                    self._service_list.currentRow() >= 0
                )
            )
            self._card_svc.setVisible(True)
        else:
            self._card_svc.setVisible(False)
            self._conn_status_railway.setText(i18n.tr("railway_no_services"))

    def _load_railway_profile(self, p: dict) -> None:
        self._railway_token_input.setText(p.get("token", ""))

    def _on_save_railway_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text="railway")
        if not ok or not name.strip():
            return
        profiles_store.upsert("railway", name.strip(), {
            "token": self._railway_token_input.text().strip(),
        })
        self._railway_profile_bar.reload()

    def _on_open(self) -> None:
        token = self._railway_token_input.text().strip()
        proj_row = self._project_list.currentRow()
        svc_row  = self._service_list.currentRow()
        if proj_row < 0 or svc_row < 0:
            return
        project = self._projects[proj_row]
        service = project["services"][svc_row]
        cfg = {
            "type":         "railway",
            "token":        token,
            "project_name": project["name"],
            "service_name": service["name"],
            "service_id":   service["id"],
            "interval_s":   self._interval_spin_railway.value(),
            "label":        f"{project['name']}/{service['name']}",
        }
        self.open_tab.emit(cfg, self._open_mode_railway.get_mode())


# ── FlyioPanel ────────────────────────────────────────────────────────────────

class _FlyioConnectWorker(QThread):
    success = pyqtSignal(list)   # app dicts
    failure = pyqtSignal(str)

    def __init__(self, token: str) -> None:
        super().__init__()
        self._token = token

    def run(self) -> None:
        try:
            apps = flyio_utils.list_apps(self._token)
            self.success.emit(apps)
        except RuntimeError as e:
            self.failure.emit(str(e))


class FlyioPanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._apps: list[dict] = []
        self._connect_worker: _FlyioConnectWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"
        list_style = (
            f"QListWidget {{ background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f" border-radius: 4px; font-size: 12px; }}"
            f"QListWidget::item:selected {{ background: {C_SEL_BG}; }}"
        )

        # ── Saved configs card ────────────────────────────────────────
        saved_card_fly, saved_lay_fly, _ = make_card(i18n.tr("saved_configs"))
        self._flyio_profile_bar = _ProfileBar("flyio", wrapper=saved_card_fly)
        self._flyio_profile_bar.profile_loaded.connect(self._load_flyio_profile)
        saved_lay_fly.addWidget(self._flyio_profile_bar)
        vlay.addWidget(saved_card_fly)

        # ── Card: Auth ───────────────────────────────────────────────
        card_auth, lay_auth, _ = make_card(i18n.tr("new_config"))

        lay_auth.addWidget(self._lbl(lbl_style, i18n.tr("flyio_field_token")))
        self._flyio_token_input = QLineEdit()
        self._flyio_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._flyio_token_input.setStyleSheet(field_style)
        lay_auth.addWidget(self._flyio_token_input)

        hint = QLabel(i18n.tr("flyio_token_hint"))
        hint.setStyleSheet(f"color: {C_MUTED}; font-size: 10.5px; font-style: italic;")
        lay_auth.addWidget(hint)

        self._save_profile_btn_flyio = _ghost_btn("Save as profile…")
        self._save_profile_btn_flyio.clicked.connect(self._on_save_flyio_profile)
        self._save_profile_btn_flyio.setEnabled(False)
        lay_auth.addWidget(self._save_profile_btn_flyio)

        self._connect_btn_flyio = _primary_btn(i18n.tr("flyio_connect"))
        self._connect_btn_flyio.clicked.connect(self._do_connect)
        lay_auth.addWidget(self._connect_btn_flyio)

        self._conn_status_flyio = QLabel("")
        self._conn_status_flyio.setStyleSheet(lbl_style)
        self._conn_status_flyio.setWordWrap(True)
        lay_auth.addWidget(self._conn_status_flyio)

        vlay.addWidget(card_auth)

        # ── Card: Application ────────────────────────────────────────
        card_app, lay_app, _ = make_card(i18n.tr("flyio_card_app"))

        self._flyio_app_list = QListWidget()
        self._flyio_app_list.setMaximumHeight(160)
        self._flyio_app_list.setStyleSheet(list_style)
        self._flyio_app_list.itemSelectionChanged.connect(
            lambda: self._open_btn_flyio.setEnabled(self._flyio_app_list.currentRow() >= 0)
        )
        lay_app.addWidget(self._flyio_app_list)

        iv_row = QHBoxLayout()
        iv_row.addWidget(self._lbl(lbl_style, i18n.tr("flyio_field_interval")))
        iv_row.addStretch()
        self._interval_spin_flyio = QSpinBox()
        self._interval_spin_flyio.setRange(1, 60)
        self._interval_spin_flyio.setValue(5)
        self._interval_spin_flyio.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px; font-size: 12px; max-width: 60px;"
        )
        iv_row.addWidget(self._interval_spin_flyio)
        lay_app.addLayout(iv_row)

        self._open_mode_flyio = OpenModeWidget()
        lay_app.addWidget(self._open_mode_flyio)

        self._open_btn_flyio = _primary_btn(i18n.tr("flyio_open"))
        self._open_btn_flyio.clicked.connect(self._on_open)
        self._open_btn_flyio.setEnabled(False)
        lay_app.addWidget(self._open_btn_flyio)

        self._card_app_flyio = card_app
        card_app.setVisible(False)
        vlay.addWidget(card_app)
        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _do_connect(self) -> None:
        token = self._flyio_token_input.text().strip()
        if not token:
            return
        self._connect_btn_flyio.setEnabled(False)
        self._conn_status_flyio.setText(i18n.tr("flyio_connecting"))
        self._conn_status_flyio.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._connect_worker = _FlyioConnectWorker(token)
        self._connect_worker.success.connect(self._on_connected_flyio)
        self._connect_worker.failure.connect(self._on_connect_fail_flyio)
        self._connect_worker.start()

    def _on_connected_flyio(self, apps: list) -> None:
        self._apps = apps
        self._conn_status_flyio.setText(i18n.tr("flyio_connected"))
        self._conn_status_flyio.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_flyio.setEnabled(True)
        self._save_profile_btn_flyio.setEnabled(True)
        self._flyio_app_list.clear()
        if apps:
            for a in apps:
                status = a.get("status", "")
                label = f"{a['name']}  ({status})" if status else a["name"]
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, a["name"])
                self._flyio_app_list.addItem(item)
            self._card_app_flyio.setVisible(True)
        else:
            self._conn_status_flyio.setText(i18n.tr("flyio_no_apps"))

    def _on_connect_fail_flyio(self, msg: str) -> None:
        self._conn_status_flyio.setText(msg)
        self._conn_status_flyio.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_flyio.setEnabled(True)

    def _load_flyio_profile(self, p: dict) -> None:
        self._flyio_token_input.setText(p.get("token", ""))

    def _on_save_flyio_profile(self) -> None:
        name, ok = QInputDialog.getText(self, "Save profile", "Profile name:", text="flyio")
        if not ok or not name.strip():
            return
        profiles_store.upsert("flyio", name.strip(), {
            "token": self._flyio_token_input.text().strip(),
        })
        self._flyio_profile_bar.reload()

    def _on_open(self) -> None:
        token = self._flyio_token_input.text().strip()
        item  = self._flyio_app_list.currentItem()
        if not item:
            return
        app_name = item.data(Qt.ItemDataRole.UserRole) or item.text().split("  ")[0]
        cfg = {
            "type":       "flyio",
            "token":      token,
            "app_name":   app_name,
            "interval_s": self._interval_spin_flyio.value(),
            "label":      app_name,
        }
        self.open_tab.emit(cfg, self._open_mode_flyio.get_mode())


# ── KubernetesPanel ───────────────────────────────────────────────────────────

class _K8sConnectWorker(QThread):
    success = pyqtSignal(list, list)  # namespaces, contexts
    failure = pyqtSignal(str)

    def __init__(self, context: str) -> None:
        super().__init__()
        self._context = context

    def run(self) -> None:
        try:
            namespaces = kubernetes_utils.list_namespaces(self._context)
            contexts   = kubernetes_utils.list_contexts()
            self.success.emit(namespaces, contexts)
        except RuntimeError as e:
            self.failure.emit(str(e))


class _K8sListPodsWorker(QThread):
    success = pyqtSignal(list)
    failure = pyqtSignal(str)

    def __init__(self, namespace: str, context: str) -> None:
        super().__init__()
        self._namespace = namespace
        self._context   = context

    def run(self) -> None:
        try:
            pods = kubernetes_utils.list_pods(self._namespace, self._context)
            self.success.emit(pods)
        except RuntimeError as e:
            self.failure.emit(str(e))


class KubernetesPanel(QWidget):
    open_tab = pyqtSignal(dict, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._context = ""
        self._connect_worker: _K8sConnectWorker | None = None
        self._pods_worker: _K8sListPodsWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        if not kubernetes_utils.is_available():
            lbl = QLabel(i18n.tr("kubernetes_not_available"))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                f"color: {C_MUTED}; font-size: 13px; background: transparent; border: none; padding: 24px;"
            )
            root.addWidget(lbl)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        root.addWidget(scroll)

        inner = QWidget()
        inner.setStyleSheet(f"background: {C_PANEL};")
        scroll.setWidget(inner)

        vlay = QVBoxLayout(inner)
        vlay.setContentsMargins(12, 12, 12, 12)
        vlay.setSpacing(10)

        field_style = (
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 6px 8px; font-size: 12px;"
        )
        lbl_style = f"color: {C_MUTED}; font-size: 11px;"
        list_style = (
            f"QListWidget {{ background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f" border-radius: 4px; font-size: 12px; }}"
            f"QListWidget::item:selected {{ background: {C_SEL_BG}; }}"
        )

        # ── Card: Cluster ────────────────────────────────────────────
        card_cluster, lay_cluster, _ = make_card(i18n.tr("kubernetes_card_cluster"))

        lay_cluster.addWidget(self._lbl(lbl_style, i18n.tr("kubernetes_field_context")))
        self._k8s_context_combo = QComboBox()
        try:
            contexts = kubernetes_utils.list_contexts()
            current  = kubernetes_utils.current_context()
        except RuntimeError:
            contexts, current = [], ""
        self._k8s_context_combo.addItem("(current context)")
        self._k8s_context_combo.addItems(contexts)
        if current:
            idx = self._k8s_context_combo.findText(current)
            if idx >= 0:
                self._k8s_context_combo.setCurrentIndex(idx)
        self._k8s_context_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        lay_cluster.addWidget(self._k8s_context_combo)

        self._connect_btn_k8s = _primary_btn(i18n.tr("kubernetes_connect"))
        self._connect_btn_k8s.clicked.connect(self._do_connect)
        lay_cluster.addWidget(self._connect_btn_k8s)

        self._conn_status_k8s = QLabel("")
        self._conn_status_k8s.setStyleSheet(lbl_style)
        self._conn_status_k8s.setWordWrap(True)
        lay_cluster.addWidget(self._conn_status_k8s)

        vlay.addWidget(card_cluster)

        # ── Card: Namespace / Pod ────────────────────────────────────
        card_pod, lay_pod, _ = make_card(i18n.tr("kubernetes_card_pod"))

        lay_pod.addWidget(self._lbl(lbl_style, i18n.tr("kubernetes_field_ns")))
        self._k8s_ns_combo = QComboBox()
        self._k8s_ns_combo.setStyleSheet(
            f"background: {C_BG}; color: {C_TEXT}; border: 1px solid {C_BORDER};"
            f"border-radius: 4px; padding: 4px 8px; font-size: 12px;"
        )
        self._k8s_ns_combo.currentTextChanged.connect(self._on_ns_changed)
        lay_pod.addWidget(self._k8s_ns_combo)

        self._k8s_pod_list = QListWidget()
        self._k8s_pod_list.setMaximumHeight(150)
        self._k8s_pod_list.setStyleSheet(list_style)
        self._k8s_pod_list.itemSelectionChanged.connect(
            lambda: self._open_btn_k8s.setEnabled(self._k8s_pod_list.currentRow() >= 0)
        )
        lay_pod.addWidget(self._k8s_pod_list)

        lay_pod.addWidget(self._lbl(lbl_style, i18n.tr("kubernetes_field_container")))
        self._k8s_container_input = QLineEdit()
        self._k8s_container_input.setPlaceholderText("(auto)")
        self._k8s_container_input.setStyleSheet(field_style)
        lay_pod.addWidget(self._k8s_container_input)

        self._open_mode_k8s = OpenModeWidget()
        lay_pod.addWidget(self._open_mode_k8s)

        self._open_btn_k8s = _primary_btn(i18n.tr("kubernetes_open"))
        self._open_btn_k8s.clicked.connect(self._on_open)
        self._open_btn_k8s.setEnabled(False)
        lay_pod.addWidget(self._open_btn_k8s)

        self._card_pod = card_pod
        card_pod.setVisible(False)
        vlay.addWidget(card_pod)
        vlay.addStretch()

    @staticmethod
    def _lbl(style: str, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(style)
        return lbl

    def _do_connect(self) -> None:
        ctx_text = self._k8s_context_combo.currentText()
        context  = "" if ctx_text == "(current context)" else ctx_text
        self._context = context
        self._connect_btn_k8s.setEnabled(False)
        self._conn_status_k8s.setText(i18n.tr("kubernetes_connecting"))
        self._conn_status_k8s.setStyleSheet(f"color: {C_MUTED}; font-size: 11px;")
        self._connect_worker = _K8sConnectWorker(context)
        self._connect_worker.success.connect(self._on_connected_k8s)
        self._connect_worker.failure.connect(self._on_connect_fail_k8s)
        self._connect_worker.start()

    def _on_connected_k8s(self, namespaces: list, _contexts: list) -> None:
        self._conn_status_k8s.setText(i18n.tr("kubernetes_connected"))
        self._conn_status_k8s.setStyleSheet(f"color: {C_INFO}; font-size: 11px;")
        self._connect_btn_k8s.setEnabled(True)
        self._k8s_ns_combo.blockSignals(True)
        self._k8s_ns_combo.clear()
        if namespaces:
            self._k8s_ns_combo.addItems(namespaces)
            self._card_pod.setVisible(True)
        else:
            self._conn_status_k8s.setText(i18n.tr("kubernetes_no_ns"))
        self._k8s_ns_combo.blockSignals(False)
        if namespaces:
            self._on_ns_changed(self._k8s_ns_combo.currentText())

    def _on_connect_fail_k8s(self, msg: str) -> None:
        self._conn_status_k8s.setText(msg)
        self._conn_status_k8s.setStyleSheet(f"color: {C_ERR}; font-size: 11px;")
        self._connect_btn_k8s.setEnabled(True)

    def _on_ns_changed(self, ns: str) -> None:
        if not ns:
            return
        self._k8s_pod_list.clear()
        self._open_btn_k8s.setEnabled(False)
        self._pods_worker = _K8sListPodsWorker(ns, self._context)
        self._pods_worker.success.connect(self._on_pods_listed)
        self._pods_worker.failure.connect(
            lambda e: self._conn_status_k8s.setText(e)
        )
        self._pods_worker.start()

    def _on_pods_listed(self, pods: list) -> None:
        self._k8s_pod_list.clear()
        if pods:
            for pod in pods:
                status = pod.get("status", "")
                label  = f"{pod['name']}  ({status})" if status else pod["name"]
                item   = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, pod["name"])
                self._k8s_pod_list.addItem(item)
        else:
            self._conn_status_k8s.setText(i18n.tr("kubernetes_no_pods"))

    def _load_k8s_profile(self, p: dict) -> None:
        ctx = p.get("context", "")
        idx = self._k8s_context_combo.findText(ctx) if ctx else 0
        self._k8s_context_combo.setCurrentIndex(max(0, idx))

    def _on_open(self) -> None:
        ns   = self._k8s_ns_combo.currentText()
        item = self._k8s_pod_list.currentItem()
        if not ns or not item:
            return
        pod       = item.data(Qt.ItemDataRole.UserRole) or item.text().split("  ")[0]
        container = self._k8s_container_input.text().strip()
        ctx_text  = self._k8s_context_combo.currentText()
        context   = "" if ctx_text == "(current context)" else ctx_text
        cfg = {
            "type":      "kubernetes",
            "pod":       pod,
            "namespace": ns,
            "context":   context,
            "container": container,
            "label":     f"{ns}/{pod}",
        }
        self.open_tab.emit(cfg, self._open_mode_k8s.get_mode())


# ── Remote redesign: providers + AddConnectionDialog + RemoteHomePanel ────────

RESULT_OPEN = 2  # custom dialog result: connect without saving

_REMOTE_PROVIDERS: list[tuple[str, str, str, str, str, str]] = [
    ("cloudwatch", "AWS CloudWatch", "☁",  "#ff9900", _SVG_CLOUD,  "AWS CloudWatch Logs"),
    ("gcp",        "Google Cloud",   "⬡",  "#4285f4", _SVG_GCP,    "Google Cloud Logging"),
    ("azure",      "Azure Monitor",  "△",  "#0078d4", _SVG_AZURE,  "Azure Monitor / Log Analytics"),
    ("ssh",        "SSH",            "⌥",  "#56cf80", _SVG_SSH,    "Remote log files over SSH"),
    ("docker",     "Docker",         "◈",  "#2496ed", _SVG_DOCKER, "Remote Docker container logs"),
    ("vercel",     "Vercel",         "▲",  "#e2e2e2", _SVG_VERCEL, "Vercel deployment & runtime logs"),
    ("loki",       "Grafana Loki",   "≡",  "#f46800", _SVG_LOKI,       "Grafana Loki log aggregation"),
    ("datadog",    "Datadog",        "⬡",  "#632ca6", _SVG_DATADOG,    "Datadog Logs"),
    ("elastic",    "Elasticsearch",  "⊙",  "#f04e98", _SVG_ELASTIC,    "Elasticsearch / OpenSearch"),
    ("railway",    "Railway",        "▣",  "#b975f2", _SVG_RAILWAY,    "Railway deployment logs"),
    ("flyio",      "Fly.io",         "⬥",  "#7b3fc4", _SVG_FLYIO,      "Fly.io app logs"),
    ("kubernetes", "Kubernetes",     "⎈",  "#326ce5", _SVG_KUBERNETES, "Kubernetes pod logs"),
]

_PROVIDER_FIELDS: dict[str, list[tuple[str, str, str, bool]]] = {
    "cloudwatch": [
        ("name",       "Connection name", "prod-us-east-1",     False),
        ("region",     "AWS Region",      "us-east-1",          False),
        ("profile",    "AWS Profile",     "default",            False),
        ("access_key", "Access Key ID",   "AKIA… (optional)",   False),
        ("secret_key", "Secret Key",      "",                   True),
    ],
    "gcp": [
        ("name",        "Connection name",      "gcp-staging",               False),
        ("project",     "Project ID",           "my-project-123",            False),
        ("credentials", "Service account JSON", "~/.config/gcloud/key.json", False),
    ],
    "azure": [
        ("name",          "Connection name", "azure-prod",          False),
        ("workspace_id",  "Workspace ID",    "xxxx-xxxx-xxxx-xxxx", False),
        ("tenant_id",     "Tenant ID",       "xxxx-xxxx-xxxx-xxxx", False),
        ("client_id",     "Client ID",       "xxxx-xxxx-xxxx-xxxx", False),
        ("client_secret", "Client secret",   "",                    True),
    ],
    "ssh": [
        ("name",     "Connection name", "prod-server",   False),
        ("host",     "Host",            "192.168.1.10",  False),
        ("port",     "Port",            "22",            False),
        ("user",     "Username",        "ubuntu",        False),
        ("key_path", "SSH key path",    "~/.ssh/id_rsa", False),
    ],
    "docker": [
        ("name",      "Connection name", "docker-remote",       False),
        ("host",      "Docker host",     "tcp://10.0.0.1:2376", False),
        ("cert_path", "TLS cert path",   "/path/to/certs (opt.)", False),
    ],
    "vercel": [
        ("name",  "Connection name", "vercel-prod",      False),
        ("token", "API Token",       "",                 True),
        ("team",  "Team slug",       "acme-corp (opt.)", False),
    ],
    "loki": [
        ("name",     "Connection name", "loki-prod",            False),
        ("url",      "Loki URL",        "http://localhost:3100", False),
        ("username", "Username",        "(optional)",           False),
        ("password", "Password",        "",                     True),
        ("token",    "Bearer token",    "(optional)",           True),
    ],
    "datadog": [
        ("name",    "Connection name", "datadog-prod",          False),
        ("site",    "Site",            "US1 (datadoghq.com)",   False),
        ("api_key", "API Key",         "",                      True),
        ("app_key", "Application Key", "",                      True),
    ],
    "elastic": [
        ("name",     "Connection name", "elastic-prod",         False),
        ("url",      "Elasticsearch URL", "http://localhost:9200", False),
        ("api_key",  "API Key",          "(optional)",          True),
        ("username", "Username",         "(optional)",          False),
        ("password", "Password",         "",                    True),
    ],
    "railway": [
        ("name",  "Connection name", "railway-prod",            False),
        ("token", "API Token",       "",                        True),
    ],
    "flyio": [
        ("name",  "Connection name", "fly-prod",                False),
        ("token", "API Token",       "",                        True),
    ],
    "kubernetes": [
        ("name",      "Connection name", "k8s-prod",            False),
        ("context",   "kubectl context", "(default context)",   False),
        ("namespace", "Namespace",       "default",             False),
    ],
}


class AddConnectionDialog(QDialog):
    """Two-step modal: step 1 = provider picker, step 2 = credential form."""

    tab_requested = pyqtSignal(dict, str)  # emitted by CloudWatch flow only

    def __init__(self, parent=None, preselect: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("remote_add_title"))
        self.setModal(True)
        self.setFixedWidth(500)
        self.setStyleSheet(
            f"QDialog {{ background: #13131a; color: {C_TEXT}; }}"
        )

        self._provider_id: str = ""
        self._fields: dict[str, QLineEdit] = {}
        self._open_btn: QPushButton | None = None
        self._save_open_btn: QPushButton | None = None
        self._cw_embedded_panel: CloudWatchPanel | None = None
        self._cw_save_pending: bool = False
        self._add_header_lbl: QLabel | None = None
        _key = id(self)
        i18n.register(_key, self._retranslate_dlg)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        root.addWidget(self._stack)

        self._stack.addWidget(self._build_step1())

        self._step2_widget = QWidget()
        self._step2_widget.setStyleSheet("background: transparent;")
        self._step2_layout = QVBoxLayout(self._step2_widget)
        self._step2_layout.setContentsMargins(0, 0, 0, 0)
        self._step2_layout.setSpacing(0)
        self._stack.addWidget(self._step2_widget)

        if preselect:
            self._go_step2(preselect)

    # ── Step 1 ────────────────────────────────────────────────────────────────

    def _retranslate_dlg(self) -> None:
        self.setWindowTitle(i18n.tr("remote_add_title"))
        if self._add_header_lbl is not None:
            self._add_header_lbl.setText(i18n.tr("remote_add_header"))

    def _build_step1(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        hdr = QWidget()
        hdr.setStyleSheet(
            "background: #1a1a24; border-bottom: 1px solid rgba(255,255,255,26);"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 16, 20, 16)
        hdr_lay.setSpacing(8)

        titles = QVBoxLayout()
        titles.setSpacing(3)
        self._add_header_lbl = QLabel(i18n.tr("remote_add_header"))
        t1 = self._add_header_lbl
        t1.setStyleSheet(
            f"color: {C_TEXT}; font-size: 14px; font-weight: 700;"
            " border: none; background: transparent;"
        )
        t2 = QLabel(i18n.tr("remote_select_provider"))
        t2.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11.5px; border: none; background: transparent;"
        )
        titles.addWidget(t1)
        titles.addWidget(t2)
        hdr_lay.addLayout(titles, 1)

        close = QPushButton("✕")
        close.setFixedSize(28, 28)
        close.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED};"
            f" border: none; font-size: 14px; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; }}"
        )
        close.clicked.connect(self.reject)
        hdr_lay.addWidget(close)
        lay.addWidget(hdr)

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        grid_lay = QGridLayout(body)
        grid_lay.setContentsMargins(20, 20, 20, 24)
        grid_lay.setSpacing(8)

        for i, (pid, name, icon_char, color, _svg, desc) in enumerate(_REMOTE_PROVIDERS):
            grid_lay.addWidget(
                self._make_provider_card(pid, name, icon_char, color, desc),
                i // 3, i % 3,
            )

        lay.addWidget(body)
        return page

    def _make_provider_card(
        self, pid: str, name: str, icon_char: str, color: str, desc: str
    ) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(140, 105)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: #17171f;
                border: 1px solid rgba(255,255,255,15);
                border-radius: 9px;
            }}
            QPushButton:hover {{
                background: #1e1e2c;
                border-color: {color};
            }}
        """)

        inner = QVBoxLayout(btn)
        inner.setContentsMargins(10, 12, 10, 12)
        inner.setSpacing(0)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon_char)
        icon_lbl.setFixedSize(30, 30)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_lbl.setStyleSheet(
            f"background: {color}20; border: 1px solid {color}35;"
            f" border-radius: 6px; color: {color}; font-size: 15px;"
        )

        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        name_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 11.5px; font-weight: 600;"
            " background: transparent; border: none;"
        )

        inner.addStretch()
        inner.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        inner.addSpacing(8)
        inner.addWidget(name_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        inner.addStretch()

        btn.clicked.connect(lambda _c, p=pid: self._go_step2(p))
        return btn

    # ── Step 2 ────────────────────────────────────────────────────────────────

    def _go_step2(self, provider_id: str) -> None:
        self._provider_id = provider_id
        # Clear previous step2 content
        while self._step2_layout.count():
            item = self._step2_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        prov = next((p for p in _REMOTE_PROVIDERS if p[0] == provider_id), None)
        if not prov:
            return
        _, name, icon_char, color, _svg, _ = prov

        # Header
        hdr = QWidget()
        hdr.setStyleSheet(
            "background: #1a1a24; border-bottom: 1px solid rgba(255,255,255,26);"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(14, 12, 14, 12)
        hdr_lay.setSpacing(8)

        back_btn = QPushButton()
        back_btn.setFixedSize(28, 28)
        back_btn.setIcon(_svg_icon(_SVG_CHEVRON_LEFT, C_MUTED, 14))
        back_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; }"
            "QPushButton:hover { background: rgba(255,255,255,8); border-radius: 4px; }"
        )
        back_btn.clicked.connect(self._go_step1)
        hdr_lay.addWidget(back_btn)

        icon_lbl = QLabel(icon_char)
        icon_lbl.setFixedSize(24, 24)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            f"background: {color}20; border: 1px solid {color}35;"
            f" border-radius: 5px; color: {color}; font-size: 13px;"
        )
        hdr_lay.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 13.5px; font-weight: 700;"
            " background: transparent; border: none;"
        )
        sub_lbl = QLabel(i18n.tr("remote_new_connection"))
        sub_lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
        )
        title_col.addWidget(name_lbl)
        title_col.addWidget(sub_lbl)
        hdr_lay.addLayout(title_col, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED};"
            f" border: none; font-size: 14px; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; }}"
        )
        close_btn.clicked.connect(self.reject)
        hdr_lay.addWidget(close_btn)
        self._step2_layout.addWidget(hdr)

        if provider_id == "cloudwatch":
            self._build_cw_step2()
            self._stack.setCurrentIndex(1)
            return

        # ── Standard: scrollable form + footer (non-CW providers) ──────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        form_widget = QWidget()
        form_widget.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_widget)
        form_lay.setContentsMargins(20, 16, 20, 8)
        form_lay.setSpacing(12)

        self._fields = self._make_form_fields(provider_id, form_lay)
        form_lay.addStretch()
        scroll.setWidget(form_widget)
        self._step2_layout.addWidget(scroll, 1)

        footer = QWidget()
        footer.setStyleSheet(
            "background: #17171f; border-top: 1px solid rgba(255,255,255,26);"
        )
        foot_lay = QVBoxLayout(footer)
        foot_lay.setContentsMargins(20, 14, 20, 16)
        foot_lay.setSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = _ghost_btn(i18n.tr("remote_cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()

        self._open_btn = _ghost_btn(i18n.tr("remote_open"))
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._on_open)
        btn_row.addWidget(self._open_btn)

        self._save_open_btn = _primary_btn(i18n.tr("remote_save_open"))
        self._save_open_btn.setEnabled(False)
        self._save_open_btn.clicked.connect(self._on_save_open)
        btn_row.addWidget(self._save_open_btn)

        foot_lay.addLayout(btn_row)

        hint = QLabel(
            "<b>Open</b> — connect once without saving.  "
            "<b>Save & Open</b> — store for later."
        )
        hint.setStyleSheet(
            f"color: {C_MUTED}; font-size: 10.5px; background: transparent; border: none;"
        )
        foot_lay.addWidget(hint)
        self._step2_layout.addWidget(footer)

        self._stack.setCurrentIndex(1)

        if "name" in self._fields:
            self._fields["name"].textChanged.connect(self._on_name_changed)

    def _make_form_fields(
        self, provider_id: str, lay: QVBoxLayout
    ) -> dict[str, QLineEdit]:
        fields: dict[str, QLineEdit] = {}
        for key, label, placeholder, is_password in _PROVIDER_FIELDS.get(provider_id, []):
            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(5)

            display_label = i18n.tr("remote_connection_name") if key == "name" else label
            lbl = QLabel(display_label.upper())
            lbl.setStyleSheet(
                f"color: {C_ACCENT}; font-size: 10px; font-weight: 700;"
                " letter-spacing: 0.8px; background: transparent; border: none;"
            )
            wl.addWidget(lbl)

            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            if is_password:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
            edit.setStyleSheet(
                f"QLineEdit {{ background: {C_BG}; border: 1px solid rgba(255,255,255,26);"
                f" border-radius: 5px; padding: 6px 10px;"
                f" font-family: 'JetBrains Mono', monospace; font-size: 11.5px;"
                f" color: {C_TEXT}; }}"
                f"QLineEdit:focus {{ border-color: {C_ACCENT}88; }}"
            )
            wl.addWidget(edit)
            lay.addWidget(wrap)
            fields[key] = edit

        return fields

    # ── Navigation & actions ──────────────────────────────────────────────────

    def _go_step1(self) -> None:
        self._provider_id = ""
        self._fields = {}
        self._cw_embedded_panel = None
        self.setMaximumHeight(16777215)
        self.adjustSize()
        self._stack.setCurrentIndex(0)

    def _on_name_changed(self, text: str) -> None:
        enabled = bool(text.strip())
        if self._open_btn:
            self._open_btn.setEnabled(enabled)
        if self._save_open_btn:
            self._save_open_btn.setEnabled(enabled)

    def _on_open(self) -> None:
        if self._provider_id == "cloudwatch" and self._cw_embedded_panel:
            self._cw_save_pending = False
            self._cw_embedded_panel._on_open_clicked()
        else:
            self.done(RESULT_OPEN)

    def _on_save_open(self) -> None:
        if self._provider_id == "cloudwatch" and self._cw_embedded_panel:
            self._cw_save_pending = True
            self._cw_embedded_panel._on_open_clicked()
        else:
            data = self.get_form_data()
            name = data.get("name", "").strip()
            if name and self._provider_id:
                profiles_store.upsert(self._provider_id, name, data)
            self.done(QDialog.DialogCode.Accepted)

    def get_provider(self) -> str:
        return self._provider_id

    def get_form_data(self) -> dict:
        return {k: v.text() for k, v in self._fields.items()}

    # ── CloudWatch: embed CloudWatchPanel directly ───────────────────────────

    def _build_cw_step2(self) -> None:
        """Embed CloudWatchPanel directly — same proven code as AddRemoteDialog."""
        self.setFixedHeight(680)

        # ── Embed CloudWatchPanel ─────────────────────────────────────────────
        panel = CloudWatchPanel(parent=self)
        panel._title_lbl.setVisible(False)
        panel._save_profile_btn_cw.setVisible(False)
        panel.open_btn.setVisible(False)
        panel.open_tab.connect(self._cw_on_panel_tab)
        panel.group_list.currentTextChanged.connect(lambda _: self._cw_update_footer_btns())
        self._cw_embedded_panel = panel

        # ── Inject "Connection name" field at top of panel's connection card ──
        name_lbl = QLabel(i18n.tr("remote_connection_name").upper())
        name_lbl.setStyleSheet(
            f"color: {C_ACCENT}; font-size: 10px; font-weight: 700;"
            " letter-spacing: 0.8px; background: transparent; border: none;"
        )
        name_edit = QLineEdit()
        name_edit.setPlaceholderText(i18n.tr("remote_connection_name"))
        name_edit.setStyleSheet(
            f"QLineEdit {{ background: {C_BG}; border: 1px solid rgba(255,255,255,26);"
            f" border-radius: 5px; padding: 5px 10px;"
            f" font-family: 'JetBrains Mono', monospace; font-size: 11.5px; color: {C_TEXT}; }}"
            f"QLineEdit:focus {{ border-color: {C_ACCENT}88; }}"
        )
        name_edit.textChanged.connect(self._cw_update_footer_btns)
        self._fields["name"] = name_edit
        cl = panel._connection_card_lay
        cl.insertWidget(0, name_edit)
        cl.insertWidget(0, name_lbl)
        self._step2_layout.addWidget(panel, 1)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setStyleSheet(
            "background: #17171f; border-top: 1px solid rgba(255,255,255,26);"
        )
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(20, 12, 20, 12)
        foot_lay.setSpacing(8)
        cancel_btn = _ghost_btn(i18n.tr("remote_cancel"))
        cancel_btn.clicked.connect(self.reject)
        foot_lay.addWidget(cancel_btn)
        foot_lay.addStretch()
        self._open_btn = _ghost_btn(i18n.tr("remote_open"))
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._on_open)
        foot_lay.addWidget(self._open_btn)
        self._save_open_btn = _primary_btn(i18n.tr("remote_save_open"))
        self._save_open_btn.setEnabled(False)
        self._save_open_btn.clicked.connect(self._on_save_open)
        foot_lay.addWidget(self._save_open_btn)
        self._step2_layout.addWidget(footer)

    def _cw_update_footer_btns(self) -> None:
        panel = self._cw_embedded_panel
        panel_ready = bool(panel and panel.open_btn.isEnabled())
        name_ok = bool(self._fields.get("name") and self._fields["name"].text().strip())
        if self._open_btn:
            self._open_btn.setEnabled(panel_ready)
        if self._save_open_btn:
            self._save_open_btn.setEnabled(panel_ready and name_ok)

    def _cw_on_panel_tab(self, cfg: dict, mode: str) -> None:
        if self._cw_save_pending:
            name_edit = self._fields.get("name")
            name = name_edit.text().strip() if name_edit else ""
            if name and self._cw_embedded_panel:
                p = self._cw_embedded_panel
                is_keys = p._auth_mode_combo.currentIndex() == 1
                creds: dict = {"region": p.region_combo.currentText()}
                if is_keys:
                    creds["access_key_id"] = p.access_key_input.text().strip()
                    creds["secret_key"]    = p.secret_key_input.text().strip()
                else:
                    creds["aws_profile"] = p.profile_combo.currentText()
                profiles_store.upsert("cloudwatch", name, creds)
            self.tab_requested.emit(cfg, mode)
            self.done(QDialog.DialogCode.Accepted)
        else:
            self.tab_requested.emit(cfg, mode)
            self.done(RESULT_OPEN)


    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            if self._stack.currentIndex() == 1:
                self._go_step1()
            else:
                self.reject()
        else:
            super().keyPressEvent(event)


# ── AddRemoteDialog ────────────────────────────────────────────────────────────

class AddRemoteDialog(QDialog):
    """Popin de configuration d'une source distante.

    Page 0  : grille de sélection du fournisseur.
    Pages 1+ : panneau de config existant embarqué.
    """

    tab_requested = pyqtSignal(dict, str)

    _PROVIDERS: list[tuple[str, str, str, str]] = [
        ("cloudwatch", "CloudWatch",    _SVG_CLOUD,      C_ACCENT),
        ("ssh",        "SSH",           _SVG_SSH,        C_TRACE),
        ("docker",     "Docker",        _SVG_DOCKER,     C_TS),
        ("vercel",     "Vercel",        _SVG_VERCEL,     C_ERR),
        ("gcp",        "GCP",           _SVG_GCP,        C_INFO),
        ("azure",      "Azure",         _SVG_AZURE,      C_ACCENT_DIM),
        ("loki",       "Loki",          _SVG_LOKI,       "#f46800"),
        ("datadog",    "Datadog",       _SVG_DATADOG,    "#632ca6"),
        ("elastic",    "Elasticsearch", _SVG_ELASTIC,    "#f04e98"),
        ("railway",    "Railway",       _SVG_RAILWAY,    "#b975f2"),
        ("flyio",      "Fly.io",        _SVG_FLYIO,      "#7b3fc4"),
        ("kubernetes", "Kubernetes",    _SVG_KUBERNETES, "#326ce5"),
    ]

    def __init__(self, parent=None,
                 prefill_service: str | None = None,
                 prefill_profile: dict | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(i18n.tr("remote_dialog_title"))
        self.setModal(True)
        self.setFixedSize(560, 680)
        self.setStyleSheet(f"background: {C_PANEL}; color: {C_TEXT};")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(
            f"background: {C_SIDE}; border-bottom: 1px solid {C_BORDER};"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(12, 0, 12, 0)
        h_lay.setSpacing(8)

        self._back_btn = QPushButton(i18n.tr("remote_back"))
        self._back_btn.setFixedHeight(28)
        self._back_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED};"
            f" border: none; font-size: 12px; padding: 0 8px; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; }}"
        )
        self._back_btn.clicked.connect(self._on_back)
        self._back_btn.setVisible(False)
        h_lay.addWidget(self._back_btn)

        self._title_lbl = QLabel(i18n.tr("remote_dialog_header"))
        self._title_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 14px; font-weight: 600;"
            " border: none; background: transparent;"
        )
        h_lay.addWidget(self._title_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED};"
            f" border: none; font-size: 14px; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; }}"
        )
        close_btn.clicked.connect(self.reject)
        h_lay.addWidget(close_btn)

        root.addWidget(header)

        # ── Stack ──────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent;")
        root.addWidget(self._stack, 1)

        # Page 0 — provider picker
        self._stack.addWidget(self._build_picker_page())

        # Pages 1-12 — existing panels
        self._cw_panel         = CloudWatchPanel()
        self._ssh_panel        = SSHPanel()
        self._docker_panel     = DockerPanel()
        self._vercel_panel     = VercelPanel()
        self._gcp_panel        = GCPPanel()
        self._azure_panel      = AzurePanel()
        self._loki_panel       = LokiPanel()
        self._datadog_panel    = DatadogPanel()
        self._elastic_panel    = ElasticPanel()
        self._railway_panel    = RailwayPanel()
        self._flyio_panel      = FlyioPanel()
        self._kubernetes_panel = KubernetesPanel()

        for panel in (self._cw_panel, self._ssh_panel, self._docker_panel,
                      self._vercel_panel, self._gcp_panel, self._azure_panel,
                      self._loki_panel, self._datadog_panel, self._elastic_panel,
                      self._railway_panel, self._flyio_panel, self._kubernetes_panel):
            panel.open_tab.connect(self._on_panel_open_tab)
            self._stack.addWidget(panel)

        self._provider_indices: dict[str, int] = {
            svc: i + 1 for i, (svc, *_) in enumerate(self._PROVIDERS)
        }
        self._load_fns: dict[str, object] = {
            "cloudwatch": self._cw_panel._load_cw_profile,
            "ssh":        self._ssh_panel._load_ssh_profile,
            "vercel":     self._vercel_panel._load_vercel_profile,
            "gcp":        self._gcp_panel._load_gcp_profile,
            "azure":      self._azure_panel._load_az_profile,
            "loki":       self._loki_panel._load_loki_profile,
            "datadog":    self._datadog_panel._load_datadog_profile,
            "elastic":    self._elastic_panel._load_elastic_profile,
            "railway":    self._railway_panel._load_railway_profile,
            "flyio":      self._flyio_panel._load_flyio_profile,
            "kubernetes": self._kubernetes_panel._load_k8s_profile,
        }

        if prefill_service:
            self._go_to_provider(prefill_service)
            if prefill_profile and prefill_service in self._load_fns:
                self._load_fns[prefill_service](prefill_profile)

    # ── Picker page ───────────────────────────────────────────────────────────

    def _build_picker_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background: {C_PANEL};")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        lbl = QLabel(i18n.tr("remote_choose"))
        lbl.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; font-weight: 600;"
        )
        outer.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(12)

        for i, (svc, label, svg, color) in enumerate(self._PROVIDERS):
            btn = self._make_provider_btn(svc, label, svg, color)
            grid.addWidget(btn, i // 3, i % 3)

        outer.addLayout(grid)
        outer.addStretch()
        return page

    def _make_provider_btn(self, svc: str, label: str,
                           svg: str, color: str) -> QPushButton:
        btn = QPushButton()
        btn.setFixedSize(148, 100)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_CARD};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border-color: {color};
                background: rgba(255,255,255,6);
            }}
        """)

        inner = QVBoxLayout(btn)
        inner.setContentsMargins(0, 14, 0, 12)
        inner.setSpacing(6)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel()
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setPixmap(_svg_icon(svg, color, 28).pixmap(28, 28))
        icon_lbl.setStyleSheet("background: transparent; border: none;")

        text_lbl = QLabel(label)
        text_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 12px; font-weight: 600;"
            " background: transparent; border: none;"
        )

        inner.addStretch()
        inner.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        inner.addWidget(text_lbl, 0, Qt.AlignmentFlag.AlignHCenter)
        inner.addStretch()

        btn.clicked.connect(lambda _checked, s=svc: self._go_to_provider(s))
        return btn

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_to_provider(self, svc: str) -> None:
        idx = self._provider_indices.get(svc, 0)
        self._stack.setCurrentIndex(idx)
        label = next((lbl for svc2, lbl, *_ in self._PROVIDERS if svc2 == svc), svc)
        self._title_lbl.setText(f"{i18n.tr('remote_dialog_header')}  ·  {label}")
        self._back_btn.setVisible(True)

    def _on_back(self) -> None:
        self._stack.setCurrentIndex(0)
        self._title_lbl.setText(i18n.tr("remote_dialog_header"))
        self._back_btn.setVisible(False)

    # ── Relay ─────────────────────────────────────────────────────────────────

    def _on_panel_open_tab(self, cfg: dict, split: str) -> None:
        self.tab_requested.emit(cfg, split)
        self.accept()


# ── RemoteHomePanel ────────────────────────────────────────────────────────────

class RemoteHomePanel(QWidget):
    """Sidebar panel: collapsible provider groups + new AddConnectionDialog."""

    tab_requested = pyqtSignal(dict, str)

    _PROVIDER_ORDER = [
        "cloudwatch", "gcp", "azure", "ssh", "docker", "vercel",
        "loki", "datadog", "elastic", "railway", "flyio", "kubernetes",
    ]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._expanded: dict[str, bool] = {}
        self._build_ui()
        self.reload()
        _key = id(self)
        i18n.register(_key, self.retranslate)

    def retranslate(self) -> None:
        self._remote_title_lbl.setText(i18n.tr("remote_title"))
        self._remote_add_btn.setText(i18n.tr("remote_add_btn"))

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(48)
        header.setStyleSheet(
            f"background: {C_SIDE}; border-bottom: 1px solid {C_BORDER};"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 0, 14, 0)
        h_lay.setSpacing(10)

        self._remote_title_lbl = QLabel(i18n.tr("remote_title"))
        self._remote_title_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 15px; font-weight: 700;"
        )
        h_lay.addWidget(self._remote_title_lbl, 1)

        self._remote_add_btn = _primary_btn(i18n.tr("remote_add_btn"))
        self._remote_add_btn.clicked.connect(self._on_add)
        h_lay.addWidget(self._remote_add_btn)
        root.addWidget(header)

        # Scrollable provider groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")

        self._groups_widget = QWidget()
        self._groups_widget.setStyleSheet(f"background: {C_PANEL};")
        self._groups_lay = QVBoxLayout(self._groups_widget)
        self._groups_lay.setContentsMargins(0, 0, 0, 0)
        self._groups_lay.setSpacing(0)
        self._groups_lay.addStretch()

        scroll.setWidget(self._groups_widget)
        root.addWidget(scroll, 1)

    # ── Reload ────────────────────────────────────────────────────────────────

    def reload(self) -> None:
        lay = self._groups_lay
        while lay.count() > 1:
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        any_conn = False
        for svc in self._PROVIDER_ORDER:
            profiles = profiles_store.load_all(svc)
            if profiles:
                any_conn = True
            lay.insertWidget(lay.count() - 1, self._make_provider_group(svc, profiles))

        if not any_conn:
            lay.insertWidget(lay.count() - 1, self._make_empty_state())

    # ── Empty state ───────────────────────────────────────────────────────────

    def _make_empty_state(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(20, 40, 20, 40)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(8)

        icon_lbl = QLabel()
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setPixmap(_svg_icon(_SVG_REMOTE, C_MUTED, 32).pixmap(32, 32))
        icon_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(icon_lbl)

        lbl1 = QLabel(i18n.tr("remote_no_connections"))
        lbl1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl1.setStyleSheet(
            f"color: {C_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        lay.addWidget(lbl1)

        lbl2 = QLabel(i18n.tr("remote_no_connections_sub"))
        lbl2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl2.setStyleSheet(
            "color: #3a3a4a; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(lbl2)
        return w

    # ── Provider group ────────────────────────────────────────────────────────

    def _make_provider_group(self, svc: str, profiles: list[dict]) -> QWidget:
        prov = next((p for p in _REMOTE_PROVIDERS if p[0] == svc), None)
        if not prov:
            return QWidget()
        _, name, icon_char, color, _svg, _ = prov

        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        w_lay = QVBoxLayout(wrapper)
        w_lay.setContentsMargins(0, 0, 0, 0)
        w_lay.setSpacing(0)

        # Header button
        hdr_btn = QPushButton()
        hdr_btn.setFixedHeight(36)
        hdr_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        hdr_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_CARD};
                border: none;
                border-bottom: 1px solid {C_BORDER};
                text-align: left;
            }}
            QPushButton:hover {{ background: rgba(255,255,255,8); }}
        """)
        hdr_inner = QHBoxLayout(hdr_btn)
        hdr_inner.setContentsMargins(10, 0, 10, 0)
        hdr_inner.setSpacing(8)

        icon_box = QLabel(icon_char)
        icon_box.setFixedSize(20, 20)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_box.setStyleSheet(
            f"background: {color}18; border: 1px solid {color}30;"
            f" border-radius: 4px; color: {color}; font-size: 11px;"
        )
        hdr_inner.addWidget(icon_box)

        name_lbl = QLabel(name)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        name_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 12px; font-weight: 600;"
            " background: transparent; border: none;"
        )
        hdr_inner.addWidget(name_lbl, 1)

        if profiles:
            count_lbl = QLabel(str(len(profiles)))
            count_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            count_lbl.setStyleSheet(
                f"color: {C_MUTED}; font-size: 10px; background: transparent; border: none;"
            )
            hdr_inner.addWidget(count_lbl)

        is_expanded = self._expanded.get(svc, bool(profiles))
        chev = QLabel("▼" if is_expanded else "▶")
        chev.setFixedWidth(14)
        chev.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        chev.setStyleSheet(
            f"color: {C_MUTED}; font-size: 9px; background: transparent; border: none;"
        )
        hdr_inner.addWidget(chev)
        w_lay.addWidget(hdr_btn)

        # Expandable content
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        content.setVisible(is_expanded)
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        for profile in profiles:
            c_lay.addWidget(self._make_conn_row(svc, profile))

        c_lay.addWidget(self._make_add_inline_row(svc))
        w_lay.addWidget(content)

        def _toggle() -> None:
            exp = not content.isVisible()
            content.setVisible(exp)
            self._expanded[svc] = exp
            chev.setText("▼" if exp else "▶")

        hdr_btn.clicked.connect(_toggle)
        return wrapper

    # ── Connection row ────────────────────────────────────────────────────────

    def _make_conn_row(self, svc: str, profile: dict) -> QWidget:
        row = QFrame()
        row.setFixedHeight(32)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setStyleSheet(
            "QFrame { background: rgba(17,17,22,150);"
            " border-top: 1px solid rgba(255,255,255,13); }"
            "QFrame:hover { background: rgba(255,255,255,8); }"
        )
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(38, 0, 8, 0)
        row_lay.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(5, 5)
        dot.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        dot.setStyleSheet(
            f"background: {C_INFO}; border-radius: 3px; border: none;"
        )
        row_lay.addWidget(dot)

        conn_name = profile.get("name", "—")
        name_lbl = QLabel(conn_name)
        name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        name_lbl.setStyleSheet(
            "color: #b0b0c0; font-size: 11.5px;"
            " font-family: 'JetBrains Mono', monospace;"
            " background: transparent; border: none;"
        )
        row_lay.addWidget(name_lbl)

        subtitle = self._get_subtitle(svc, profile)
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            sub_lbl.setStyleSheet(
                f"color: {C_MUTED}; font-size: 10px; background: transparent; border: none;"
            )
            row_lay.addWidget(sub_lbl)

        row_lay.addStretch()

        # Delete button with two-click confirm
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(22, 22)
        del_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED};"
            f" border: none; font-size: 11px; }}"
            f"QPushButton:hover {{ color: {C_ERR}; }}"
        )
        row_lay.addWidget(del_btn)

        _confirmed = [False]
        _timer: list[QTimer | None] = [None]

        def _reset_del() -> None:
            _confirmed[0] = False
            del_btn.setText("✕")
            del_btn.setStyleSheet(
                f"QPushButton {{ background: transparent; color: {C_MUTED};"
                f" border: none; font-size: 11px; }}"
                f"QPushButton:hover {{ color: {C_ERR}; }}"
            )

        def _on_del_clicked() -> None:
            if not _confirmed[0]:
                _confirmed[0] = True
                del_btn.setText("!")
                del_btn.setStyleSheet(
                    f"QPushButton {{ background: {C_ERR}20; color: {C_ERR};"
                    f" border: 1px solid {C_ERR}40; border-radius: 3px;"
                    f" font-size: 9px; font-weight: 700; }}"
                    f"QPushButton:hover {{ background: {C_ERR}30; }}"
                )
                t = QTimer()
                t.setSingleShot(True)
                t.timeout.connect(_reset_del)
                t.start(3000)
                _timer[0] = t
            else:
                if _timer[0]:
                    _timer[0].stop()
                profiles_store.delete(svc, conn_name)
                self.reload()

        del_btn.clicked.connect(_on_del_clicked)

        row.mousePressEvent = lambda e, s=svc, p=profile: (
            self._on_open_profile(s, p)
            if e.button() == Qt.MouseButton.LeftButton
            else None
        )
        return row

    # ── Inline "add connection" row ───────────────────────────────────────────

    def _make_add_inline_row(self, svc: str) -> QLabel:
        row = QLabel(i18n.tr("remote_add_connection"))
        row.setFixedHeight(28)
        row.setContentsMargins(38, 0, 10, 0)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setStyleSheet(
            f"QLabel {{ color: {C_MUTED}; font-size: 11px;"
            f" background: transparent;"
            f" border-top: 1px solid rgba(255,255,255,8); }}"
            f"QLabel:hover {{ color: {C_ACCENT};"
            f" background: rgba(91,143,255,13); }}"
        )
        row.mousePressEvent = lambda _e, s=svc: self._on_add(preselect=s)
        return row

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _get_subtitle(svc: str, profile: dict) -> str:
        key = {
            "cloudwatch": "region",
            "gcp":        "project",
            "azure":      "workspace_id",
            "ssh":        "host",
            "docker":     "host",
            "vercel":     "team",
        }.get(svc, "")
        return profile.get(key, "")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_add(self, preselect: str | None = None) -> None:
        dlg = AddConnectionDialog(parent=self, preselect=preselect)
        dlg.tab_requested.connect(self.tab_requested)
        result = dlg.exec()
        provider_id = dlg.get_provider()
        form_data = dlg.get_form_data()
        if result in (QDialog.DialogCode.Accepted, RESULT_OPEN) and provider_id:
            if provider_id == "cloudwatch":
                pass  # tab already opened via tab_requested signal
            elif form_data.get("name", "").strip():
                open_dlg = AddRemoteDialog(
                    parent=self,
                    prefill_service=provider_id,
                    prefill_profile=form_data,
                )
                open_dlg.tab_requested.connect(self.tab_requested)
                open_dlg.exec()
        self.reload()

    def _on_open_profile(self, svc: str, profile: dict) -> None:
        dlg = AddRemoteDialog(
            parent=self,
            prefill_service=svc,
            prefill_profile=profile,
        )
        dlg.tab_requested.connect(self.tab_requested)
        dlg.exec()
        self.reload()


# ── WorkspacePanel ─────────────────────────────────────────────────────────────

class WorkspacePanel(QWidget):
    save_workspace   = pyqtSignal(str)        # name
    open_workspace   = pyqtSignal(dict)       # full workspace dict
    delete_workspace = pyqtSignal(str)        # ws id
    rename_workspace = pyqtSignal(str, str)   # ws_id, new_name

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setStyleSheet(f"background: {C_SIDE};")
        vbox = QVBoxLayout(content)
        vbox.setContentsMargins(12, 16, 12, 16)
        vbox.setSpacing(12)

        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet(
            f"color: {C_TEXT}; font-size: 15px; font-weight: 700;"
            "background: transparent; border: none; margin-bottom: 4px;"
        )
        vbox.addWidget(self._title_lbl)

        # ── Save card ──
        save_card, cl, _ = make_card()
        self._name_input = QLineEdit()
        self._name_input.returnPressed.connect(self._on_save)
        self._save_btn = _primary_btn("")
        self._save_btn.clicked.connect(self._on_save)
        cl.addWidget(self._name_input)
        cl.addWidget(self._save_btn)
        vbox.addWidget(save_card)

        # ── List container ──
        # Give it stretch 1 so it expands within the vbox (no extra spacer needed)
        self._list_container = QVBoxLayout()
        self._list_container.setSpacing(8)
        self._list_container.setContentsMargins(0, 0, 0, 0)
        self._list_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        vbox.addLayout(self._list_container, 1)

        scroll.setWidget(content)
        outer.addWidget(scroll)

        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

        self.retranslate()
        self.reload()

    def reload(self) -> None:
        while self._list_container.count():
            item = self._list_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for ws in WorkspaceManager.load():
            self._list_container.addWidget(self._make_ws_card(ws))

    def _make_ws_card(self, ws: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {C_CARD}; border: 1px solid rgba(255,255,255,18);"
            " border-radius: 10px; }"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(14, 12, 14, 12)
        vl.setSpacing(4)

        # Name row with inline rename
        name_stack = QStackedWidget()
        name_stack.setFixedHeight(28)

        name_lbl = QLabel(ws["name"])
        name_lbl.setStyleSheet(
            f"font-weight: bold; color: {C_TEXT}; background: transparent; border: none;"
        )
        name_edit = QLineEdit(ws["name"])
        name_edit.setStyleSheet(f"background: {C_SIDE}; color: {C_TEXT}; border-radius: 4px;")

        name_stack.addWidget(name_lbl)   # index 0
        name_stack.addWidget(name_edit)  # index 1

        def _start_rename():
            name_edit.setText(name_lbl.text())
            name_stack.setCurrentIndex(1)
            name_edit.setFocus()
            name_edit.selectAll()

        def _commit_rename():
            new_name = name_edit.text().strip()
            if new_name:
                name_lbl.setText(new_name)
                self.rename_workspace.emit(ws["id"], new_name)
            name_stack.setCurrentIndex(0)

        name_lbl.mouseDoubleClickEvent = lambda _ev: _start_rename()
        name_edit.returnPressed.connect(_commit_rename)
        name_edit.editingFinished.connect(_commit_rename)

        vl.addWidget(name_stack)

        dt_str = ws.get("created_at", "")[:10]
        date_lbl = QLabel(dt_str)
        date_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(date_lbl)

        n = len(ws.get("logs", []))
        s = "s" if n != 1 else ""
        count_lbl = QLabel(i18n.tr("ws_logs_count", n=n, s=s))
        count_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px; border: none; background: transparent;")
        vl.addWidget(count_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        open_btn = _primary_btn(i18n.tr("ws_open"))
        open_btn.setFixedHeight(28)
        open_btn.clicked.connect(lambda _=False, w=ws: self.open_workspace.emit(w))
        ren_btn = _ghost_btn(i18n.tr("ws_rename"))
        ren_btn.setFixedHeight(28)
        ren_btn.clicked.connect(_start_rename)
        del_btn = _danger_btn(i18n.tr("ws_delete"))
        del_btn.setFixedHeight(28)
        del_btn.clicked.connect(lambda _=False, w=ws: self._on_delete(w))
        btn_row.addWidget(open_btn)
        btn_row.addWidget(ren_btn)
        btn_row.addWidget(del_btn)
        vl.addLayout(btn_row)

        card.setMaximumHeight(120)
        return card

    def retranslate(self) -> None:
        self._title_lbl.setText(i18n.tr("ws_title").upper())
        self._name_input.setPlaceholderText(i18n.tr("ws_name_ph"))
        self._save_btn.setText(i18n.tr("ws_save_btn"))
        self.reload()

    def _on_save(self) -> None:
        name = self._name_input.text().strip()
        if not name:
            self._name_input.setPlaceholderText(i18n.tr("ws_name_required"))
            return
        self.save_workspace.emit(name)
        self._name_input.clear()

    def _on_delete(self, ws: dict) -> None:
        self.delete_workspace.emit(ws["id"])
        self.reload()


# ── SideStack ─────────────────────────────────────────────────────────────────

class SideStack(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(160)
        self.setMaximumWidth(480)
        self.setStyleSheet(
            f"background: {C_SIDE};"
            f"border-right: 1px solid {C_BORDER};"
        )


# ── Filter / search data model ─────────────────────────────────────────────────

@dataclass
class TermRow:
    text: str
    operator: str  # "AND" | "OR" | "" — empty string for the first term (ignored)
    key: str = ""  # non-empty → JSON key=value match mode


def _line_matches(line: str, terms: list[TermRow]) -> bool:
    """Return True if *line* satisfies the AND/OR chain of *terms* (case-insensitive)."""
    if not terms:
        return True

    def _term_hit(term: TermRow) -> bool:
        if not term.key:
            # Plain text match
            return term.text.lower() in line.lower()
        # Key=value match: parse line as JSON, check data[key] contains text
        # Try the full line first, then search for an embedded JSON object
        data = None
        stripped = line.strip()
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, dict):
                data = parsed
        except (json.JSONDecodeError, ValueError):
            pass
        if data is None:
            # Try to find an embedded JSON object in the line
            start = line.find("{")
            if start != -1:
                try:
                    parsed = json.loads(line[start:])
                    if isinstance(parsed, dict):
                        data = parsed
                except (json.JSONDecodeError, ValueError):
                    pass
        if data is None or term.key not in data:
            return False
        if term.text == "":
            return True  # key presence check
        return term.text.lower() in str(data[term.key]).lower()

    result = _term_hit(terms[0])
    for term in terms[1:]:
        hit = _term_hit(term)
        result = (result and hit) if term.operator == "AND" else (result or hit)
    return result


def _extract_json_keys(line: str) -> set[str]:
    """Extract top-level JSON keys from *line*. Best-effort; never raises."""
    try:
        obj = json.loads(line)
        if isinstance(obj, dict):
            return set(obj.keys())
    except (json.JSONDecodeError, ValueError):
        pass
    # Fallback: regex for "key": patterns (handles JSON embedded in a longer line)
    return set(re.findall(r'"([\w_-]+)"\s*:', line))


# ── JSON parsing + line classification ─────────────────────────────────────────

def _try_parse_json(message: str) -> dict | None:
    """Try to parse message as a JSON object. Returns dict or None."""
    stripped = message.strip()
    if not stripped.startswith("{"):
        return None
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


_CLASSIFY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("error", re.compile(r"\b(CRITICAL|FATAL|ERROR|ERR)\b", re.IGNORECASE)),
    ("warn",  re.compile(r"\b(WARN(?:ING)?)\b",             re.IGNORECASE)),
    ("info",  re.compile(r"\bINFO\b",                       re.IGNORECASE)),
    ("debug", re.compile(r"\bDEBUG\b",                      re.IGNORECASE)),
    ("trace", re.compile(r"\bTRACE\b",                      re.IGNORECASE)),
]


def _classify_line(text: str) -> str:
    """Return severity level string for a log line."""
    for level, pattern in _CLASSIFY_PATTERNS:
        if pattern.search(text):
            return level
    return "plain"


_MAIN_KEYS = (
    "message", "msg", "error", "err", "data", "content", "text",
    "body", "log", "description", "details", "payload", "result", "output", "value",
)


def _resolve_main_key(data: dict) -> str | None:
    """Return the first priority key found in data, or None."""
    for k in _MAIN_KEYS:
        if k in data:
            return k
    return None


# ── LogItem + LogModel ─────────────────────────────────────────────────────────

@dataclass
class LogItem:
    ts_ms: int
    message: str
    is_json: bool
    json_data: dict | None
    main_key: str | None
    expanded: bool = False
    visible: bool = True
    is_break: bool = False


_ITEM_ROLE     = Qt.ItemDataRole.UserRole + 1
_EXPANDED_ROLE = Qt.ItemDataRole.UserRole + 2


class LogModel(QAbstractListModel):
    rows_appended     = pyqtSignal()
    json_keys_updated = pyqtSignal(set)
    filter_applied    = pyqtSignal()

    _MAX_LINES = 10_000

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[LogItem] = []
        self._visible: list[LogItem] = []   # references into _items
        self._json_keys: set[str] = set()
        self._current_filter_terms: list[TermRow] = []

    # ── QAbstractListModel interface ──────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: B008
        return 0 if parent.isValid() else len(self._visible)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._visible):
            return None
        item = self._visible[index.row()]
        if role == _ITEM_ROLE:
            return item
        if role == Qt.ItemDataRole.DisplayRole:
            return item.message
        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole) -> bool:
        if role == _EXPANDED_ROLE and index.isValid():
            item = self._visible[index.row()]
            item.expanded = bool(value)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ── Public API ────────────────────────────────────────────────────────────

    def append_events(self, events: list[tuple[int, str]]) -> None:
        if not events:
            return
        new_keys: set[str] = set()
        appended: list[LogItem] = []

        for ts_ms, message in events:
            json_data = _try_parse_json(message)
            main_key  = _resolve_main_key(json_data) if json_data else None
            item = LogItem(
                ts_ms=ts_ms,
                message=message,
                is_json=json_data is not None,
                json_data=json_data,
                main_key=main_key,
                visible=_line_matches(message, self._current_filter_terms),
            )
            self._items.append(item)
            appended.append(item)
            if json_data:
                new_keys |= set(json_data.keys())

        # Enforce MAX_LINES — bulk trim + reset if over limit
        if len(self._items) > self._MAX_LINES:
            self._items = self._items[-self._MAX_LINES:]
            self.beginResetModel()
            self._visible = [it for it in self._items if it.visible]
            self.endResetModel()
            self.rows_appended.emit()
        else:
            newly_visible = [it for it in appended if it.visible]
            if newly_visible:
                first = len(self._visible)
                self.beginInsertRows(QModelIndex(), first, first + len(newly_visible) - 1)
                self._visible.extend(newly_visible)
                self.endInsertRows()
                self.rows_appended.emit()

        if new_keys - self._json_keys:
            self._json_keys |= new_keys
            self.json_keys_updated.emit(self._json_keys.copy())

    def insert_break(self) -> None:
        dt = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        label = f"══════════════  {dt}  ══════════════"
        item = LogItem(
            ts_ms=0, message=label, is_json=False, json_data=None,
            main_key=None, visible=True, is_break=True,
        )
        self._items.append(item)
        first = len(self._visible)
        self.beginInsertRows(QModelIndex(), first, first)
        self._visible.append(item)
        self.endInsertRows()
        self.rows_appended.emit()

    def apply_filter(self, terms: list[TermRow]) -> None:
        self._current_filter_terms = terms
        self.beginResetModel()
        self._visible = []
        for item in self._items:
            item.visible = item.is_break or _line_matches(item.message, self._current_filter_terms)
            if item.visible:
                self._visible.append(item)
        self.endResetModel()
        self.filter_applied.emit()

    def clear(self) -> None:
        self.beginResetModel()
        self._items.clear()
        self._visible.clear()
        self._json_keys.clear()
        self.endResetModel()

    def get_json_keys(self) -> set[str]:
        return self._json_keys.copy()

    def visible_count(self) -> int:
        return len(self._visible)


# ── LogDelegate ────────────────────────────────────────────────────────────────

_ROW_H         = 24   # px — plain / JSON-collapsed row height (normal density)
_TABLE_HEAD_H  = 22   # px — table header row height
_TABLE_ROW_H   = 18   # px — each key/value data row height
_TABLE_PAD_B   = 6    # px — padding below last table row
_ARROW_W       = 16   # px — width reserved for ▶/▼ toggle
_BADGE_COL_W   = 52   # px — level badge column width
_TS_COL_W      = 92   # px — timestamp column width

_LEVEL_COLORS = {
    "error": C_ERR,
    "warn":  C_WARN,
    "info":  C_INFO,
    "debug": C_DEBUG,
    "trace": C_TRACE,
    "plain": C_TEXT,
}

_LEVEL_BG = {
    "error": QColor(240, 120, 120, 26),   # 10% opacity
    "warn":  QColor(240, 192, 96, 20),
    "info":  QColor(86, 207, 128, 18),
    "debug": QColor(91, 143, 255, 20),
    "trace": QColor(176, 124, 240, 20),
    "plain": QColor(0, 0, 0, 0),
}

_LEVEL_BADGE_TEXT = {
    "error": "ERROR",
    "warn":  "WARN",
    "info":  "INFO",
    "debug": "DEBUG",
    "trace": "TRACE",
    "plain": "",
}


class LogDelegate(QStyledItemDelegate):
    """Paints log rows. JSON rows are collapsible; plain rows use level colors."""

    def __init__(self, viewer, parent=None):
        super().__init__(parent)
        # viewer is the LogViewer — used to read show_timestamps flag
        self._viewer = viewer
        self._search_highlights: dict[int, list[tuple[int, int]]] = {}
        self._focused_match: tuple[int, int, int] | None = None  # (vis_idx, start, len)

    def set_search_highlights(
        self,
        highlights: dict[int, list[tuple[int, int]]],
    ) -> None:
        self._search_highlights = highlights

    def set_focused_match(self, vis_idx: int, char_start: int, char_len: int) -> None:
        self._focused_match = (vis_idx, char_start, char_len)

    # ── QStyledItemDelegate interface ─────────────────────────────────────────

    def sizeHint(self, option, index):
        item = index.data(_ITEM_ROLE)
        if item is None:
            return QSize(option.rect.width(), _ROW_H)
        if item.is_break:
            return QSize(option.rect.width(), 28)
        if item.is_json and item.expanded and item.json_data:
            n = len(item.json_data)
            return QSize(
                option.rect.width(),
                _ROW_H + _TABLE_HEAD_H + _TABLE_ROW_H * n + _TABLE_PAD_B,
            )
        if not item.is_json:
            fm = QFontMetrics(option.font)
            vp_w = self._viewer._list_view.viewport().width()
            ts_w = _TS_COL_W if (self._viewer.show_timestamps and item.ts_ms) else 0
            x_offset = _BADGE_COL_W + ts_w
            avail_w = max(1, vp_w - x_offset - 14)
            br = fm.boundingRect(QRect(0, 0, avail_w, 0), Qt.TextFlag.TextWordWrap, item.message)
            return QSize(vp_w, max(_ROW_H, br.height() + 6))
        return QSize(option.rect.width(), _ROW_H)

    def paint(self, painter, option, index):
        item = index.data(_ITEM_ROLE)
        if item is None:
            return

        painter.save()
        painter.setClipRect(option.rect)

        if item.is_break:
            self._paint_break(painter, option, item)
        else:
            # Selection background
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, QColor("#1a3a6e55"))
            if item.is_json:
                self._paint_json(painter, option, index, item)
            else:
                self._paint_plain(painter, option, index, item)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            item = index.data(_ITEM_ROLE)
            if item and item.is_json and item.json_data:
                model.setData(index, not item.expanded, _EXPANDED_ROLE)
                return True
        return False

    # ── Private paint helpers ─────────────────────────────────────────────────

    def _baseline(self, rect: QRect, fm: QFontMetrics, row_h: int = _ROW_H) -> int:
        """Return y baseline for text vertically centered in a row."""
        return rect.top() + (row_h - fm.height()) // 2 + fm.ascent()

    def _draw_segments(
        self,
        painter,
        x: int,
        y: int,
        segments: list[tuple[str, str]],
        fm: QFontMetrics,
    ) -> int:
        """Draw (text, color) segments left-to-right. Returns x after last segment."""
        for text, color in segments:
            painter.setPen(QColor(color))
            painter.drawText(x, y, text)
            x += fm.horizontalAdvance(text)
        return x

    def _paint_break(self, painter, option, item: LogItem) -> None:
        rect = option.rect
        painter.fillRect(rect, QColor("#111111"))
        mid_y = rect.top() + rect.height() // 2
        painter.setPen(QColor(C_DIVIDER))
        painter.drawLine(rect.left(), mid_y, rect.right(), mid_y)
        fm = painter.fontMetrics()
        text_w = fm.horizontalAdvance(item.message)
        tx = rect.left() + (rect.width() - text_w) // 2
        ty = self._baseline(rect, fm, rect.height())
        painter.fillRect(QRect(tx - 6, rect.top(), text_w + 12, rect.height()), QColor("#111111"))
        painter.setPen(QColor(C_MUTED))
        painter.drawText(tx, ty, item.message)

    def _paint_plain(self, painter, option, index, item: LogItem) -> None:
        fm    = painter.fontMetrics()
        rect  = option.rect
        level = _classify_line(item.message)
        color = _LEVEL_COLORS.get(level, C_TEXT)

        vis_idx = index.row()
        # Compute message x start for search bg
        msg_x = rect.left() + _BADGE_COL_W
        if self._viewer.show_timestamps and item.ts_ms:
            msg_x += _TS_COL_W
        self._draw_search_bg(painter, rect, msg_x, item.message, vis_idx, fm)

        # Level badge column
        self._paint_level_badge(painter, rect, level, fm)

        x = rect.left() + _BADGE_COL_W

        # Timestamp column
        if self._viewer.show_timestamps and item.ts_ms:
            ts = datetime.fromtimestamp(item.ts_ms / 1000, tz=UTC).strftime("%H:%M:%S")
            ts_rect = QRect(x, rect.top(), _TS_COL_W, rect.height())
            painter.setPen(QColor(C_TS))
            painter.drawText(ts_rect,
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             ts)
            x += _TS_COL_W

        # Message column
        text_rect = QRect(x, rect.top() + 3, rect.right() - x - 14, rect.height() - 6)
        painter.setPen(QColor(color))
        painter.drawText(text_rect,
                         Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignTop,
                         item.message)

    def _paint_level_badge(self, painter, rect: QRect, level: str, _fm=None) -> None:
        """Draw the level badge in the left column."""
        badge_text = _LEVEL_BADGE_TEXT.get(level, "")
        if not badge_text:
            return
        color = QColor(_LEVEL_COLORS.get(level, C_TEXT))
        bg    = _LEVEL_BG.get(level, QColor(0, 0, 0, 0))

        # Save font, set smaller bold badge font
        orig_font = painter.font()
        badge_font = painter.font()
        badge_font.setPointSize(max(6, badge_font.pointSize() - 1))
        badge_font.setBold(True)
        painter.setFont(badge_font)
        badge_fm = QFontMetrics(badge_font)

        badge_w = badge_fm.horizontalAdvance(badge_text) + 10  # 5px each side
        badge_h = badge_fm.height() + 2
        bx = rect.left() + 14
        by = rect.top() + (rect.height() - badge_h) // 2

        # Draw badge background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg))
        path = QPainterPath()
        path.addRoundedRect(bx, by, badge_w, badge_h, 3, 3)
        painter.drawPath(path)

        # Draw badge text
        painter.setPen(color)
        painter.drawText(
            QRect(bx, by, badge_w, badge_h),
            Qt.AlignmentFlag.AlignCenter,
            badge_text,
        )

        # Restore font
        painter.setFont(orig_font)

    def _paint_json(self, painter, option, index, item: LogItem) -> None:
        fm   = painter.fontMetrics()
        rect = option.rect
        y    = self._baseline(rect, fm)
        level = _classify_line(item.message)
        color = _LEVEL_COLORS.get(level, C_TEXT)

        # Level badge column
        self._paint_level_badge(painter, rect, level, fm)

        # Restore full font after badge
        font = self._viewer._list_view.font()
        painter.setFont(font)
        fm = painter.fontMetrics()

        x = rect.left() + _BADGE_COL_W

        # Timestamp column
        if self._viewer.show_timestamps and item.ts_ms:
            ts = datetime.fromtimestamp(item.ts_ms / 1000, tz=UTC).strftime("%H:%M:%S")
            x = self._draw_segments(painter, x, y, [(ts + "  ", C_TS)], fm)
        else:
            x += 0  # no ts column when disabled

        # ▸/▾ toggle arrow (C_TRACE color)
        arrow = "▾" if item.expanded else "▸"
        x = self._draw_segments(painter, x, y, [(arrow + " ", C_TRACE)], fm)

        # Main message value
        if item.main_key and item.json_data:
            main_val = str(item.json_data[item.main_key])[:80]
            x = self._draw_segments(painter, x, y, [(main_val, color)], fm)
        elif item.json_data:
            pairs = list(item.json_data.items())[:2]
            for k, v in pairs:
                x = self._draw_segments(painter, x, y,
                    [(f" {k}", C_DEBUG), ("=", C_MUTED), (str(v)[:20], C_INFO)], fm)

        # Summary of remaining keys (collapsed only)
        if not item.expanded and item.json_data:
            shown_keys = {item.main_key} if item.main_key else set()
            if not item.main_key:
                shown_keys = {k for k, _ in list(item.json_data.items())[:2]}
            rest = [k for k in item.json_data if k not in shown_keys]
            for k in rest[:3]:
                x = self._draw_segments(painter, x, y,
                    [("  ", C_MUTED), (k, C_DEBUG), ("=", C_MUTED),
                     (str(item.json_data[k])[:20], C_INFO)], fm)
            if len(rest) > 3:
                x = self._draw_segments(painter, x, y,
                    [(f"  +{len(rest)-3}", C_MUTED)], fm)

        # Expanded block
        if item.expanded and item.json_data:
            self._paint_json_expanded(painter, rect, item, fm)

    def _paint_json_expanded(self, painter, rect: QRect, item: LogItem, fm: QFontMetrics) -> None:
        """Render expanded JSON as indented key: value lines below the collapsed row."""
        block_x = rect.left() + _BADGE_COL_W + 12
        block_y = rect.top() + _ROW_H + 4
        block_w = rect.width() - _BADGE_COL_W - 26

        # Block background
        n = len(item.json_data)
        block_h = n * _TABLE_ROW_H + 8
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(C_BG)))
        border_path = QPainterPath()
        border_path.addRoundedRect(block_x, block_y, block_w, block_h, 6, 6)
        painter.drawPath(border_path)
        painter.setPen(QColor(80, 80, 100, 60))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(border_path)

        key_col_w = 110
        x_key = block_x + 12
        x_colon = x_key + key_col_w
        x_val   = x_colon + fm.horizontalAdvance(": ")

        for i, (k, v) in enumerate(item.json_data.items()):
            row_top  = block_y + 4 + i * _TABLE_ROW_H
            row_base = row_top + ((_TABLE_ROW_H - fm.height()) // 2) + fm.ascent()

            painter.setPen(QColor(C_DEBUG))
            painter.drawText(x_key, row_base, str(k)[:20])

            painter.setPen(QColor(C_MUTED))
            painter.drawText(x_colon, row_base, ": ")

            val_color = self._value_color(v)
            painter.setPen(QColor(val_color))
            painter.drawText(x_val, row_base, str(v)[:80])

    def _value_color(self, v) -> str:
        if isinstance(v, bool):
            return C_TRACE
        if isinstance(v, (int, float)):
            return C_WARN
        if v is None:
            return C_MUTED
        return C_TEXT

    def _draw_search_bg(
        self,
        painter,
        row_rect: QRect,
        text_x: int,
        text: str,
        vis_idx: int,
        fm: QFontMetrics,
    ) -> None:
        """Draw yellow background rects behind search match characters."""
        highlights = self._search_highlights.get(vis_idx, [])
        if not highlights:
            return
        y = row_rect.top() + 2
        h = row_rect.height() - 4
        for char_start, char_len in highlights:
            prefix_w = fm.horizontalAdvance(text[:char_start])
            match_w  = fm.horizontalAdvance(text[char_start:char_start + char_len])
            color = "#ffd54f66"
            focused = self._focused_match
            if focused and focused[0] == vis_idx and focused[1] == char_start:
                color = "#ffd54faa"
            painter.fillRect(QRect(text_x + prefix_w, y, match_w, h), QColor(color))


# ── LogViewer ─────────────────────────────────────────────────────────────────

class _LogListView(QListView):
    """QListView that triggers item-size recalculation on every resize."""
    focus_in = pyqtSignal()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.scheduleDelayedItemsLayout()

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        self.focus_in.emit()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            m = self.model()
            if isinstance(m, LogModel):
                m.insert_break()
        else:
            super().keyPressEvent(event)


_SOURCE_COLORS = {
    "cloudwatch":       C_ACCENT,
    "file":             C_INFO,
    "stdin":            C_WARN,
    "ssh":              C_TRACE,
    "docker":           C_TS,
    "docker_compose":   C_TS,
    "docker_exec_file": C_TS,
    "vercel":           C_ERR,
    "gcp":              C_INFO,
    "azure":            C_ACCENT,
    "loki":             "#f46800",
    "datadog":          "#632ca6",
    "elastic":          "#f04e98",
    "railway":          "#b975f2",
    "flyio":            "#7b3fc4",
    "kubernetes":       "#326ce5",
}


class LogViewer(QWidget):
    stop_requested       = pyqtSignal()
    json_keys_updated    = pyqtSignal(set)
    lines_appended       = pyqtSignal()
    filter_applied       = pyqtSignal()
    pane_activated       = pyqtSignal()
    pane_close_requested = pyqtSignal()

    _MAX_LINES = 10_000

    def __init__(self, source_type: str = "cloudwatch", parent=None):
        super().__init__(parent)
        self._source_type = source_type
        self._search_highlights: dict[int, list[tuple[int, int]]] = {}
        self._ws_meta: dict = {}

        self._model = LogModel(self)
        self._model.json_keys_updated.connect(self.json_keys_updated)
        self._model.rows_appended.connect(self._on_rows_appended)
        self._model.filter_applied.connect(self.filter_applied)
        self._model._MAX_LINES = self._MAX_LINES

        self._build_ui()

        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    @property
    def show_timestamps(self) -> bool:
        return self.timestamps_cb.isChecked()

    def _on_rows_appended(self) -> None:
        if self.autoscroll_cb.isChecked():
            self._list_view.scrollToBottom()
        self.lines_appended.emit()
        self.line_badge.setText(i18n.tr("viewer_lines", n=self._model.visible_count()))

    def _build_ui(self):
        self.setMinimumSize(50, 50)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Toolbar ──
        toolbar = QWidget()
        toolbar.setFixedHeight(34)
        toolbar.setStyleSheet(
            f"background: {C_PANEL}; border-bottom: 1px solid {C_BORDER};"
        )
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 0, 12, 0)
        tb.setSpacing(8)

        src_color = _SOURCE_COLORS.get(self._source_type, C_TEXT)
        self._source_badge = QLabel(self._source_type.upper())
        self._source_badge.setStyleSheet(
            f"background: rgba(91,143,255,31); color: {src_color}; border-radius: 8px;"
            "padding: 1px 8px; font-size: 10px; font-weight: bold; border: none;"
        )

        self.title_label = QLabel("—")
        self.title_label.setStyleSheet(
            f"font-size: 12px; color: {C_MUTED}; background: transparent; border: none;"
            "font-family: 'JetBrains Mono', monospace;"
        )

        self.line_badge = QLabel(i18n.tr("viewer_lines", n=0))
        self.line_badge.setStyleSheet(
            f"color: {C_MUTED}; border: none; background: transparent;"
            "font-size: 11px;"
        )

        self.autoscroll_cb = QCheckBox()
        self.autoscroll_cb.setChecked(True)

        self.timestamps_cb = QCheckBox()
        self.timestamps_cb.setChecked(True)
        self.timestamps_cb.stateChanged.connect(
            lambda _: self._list_view.viewport().update()
        )

        _icon_btn_style = (
            f"QPushButton {{ background: transparent; border: 1px solid {C_BORDER};"
            f" border-radius: 5px; padding: 0; }}"
            f"QPushButton:hover {{ border-color: {C_ACCENT}; background: {C_ACCENT_DIM}; }}"
            f"QPushButton:disabled {{ opacity: 0.4; }}"
        )
        _danger_icon_style = (
            "QPushButton { background: transparent; border: 1px solid rgba(240,120,120,80);"
            " border-radius: 5px; padding: 0; }"
            "QPushButton:hover { background: rgba(240,120,120,30); }"
        )

        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("danger")
        self.clear_btn.setFixedSize(26, 26)
        self.clear_btn.setIcon(_svg_icon(_SVG_TRASH, C_ERR, 14))
        self.clear_btn.setIconSize(QSize(14, 14))
        self.clear_btn.setStyleSheet(_danger_icon_style)
        self.clear_btn.clicked.connect(self.clear)

        self.stop_btn = QPushButton()
        self.stop_btn.setFixedSize(26, 26)
        self.stop_btn.setIcon(_svg_icon(_SVG_STOP_SQ, C_MUTED, 14))
        self.stop_btn.setIconSize(QSize(14, 14))
        self.stop_btn.setStyleSheet(_icon_btn_style)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_requested)

        self.close_pane_btn = QPushButton()
        self.close_pane_btn.setFixedSize(26, 26)
        self.close_pane_btn.setIcon(_svg_icon(_SVG_CLOSE_X, C_MUTED, 12))
        self.close_pane_btn.setIconSize(QSize(12, 12))
        self.close_pane_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; border-radius: 5px; padding: 0; }"
            "QPushButton:hover { background: rgba(240,120,120,25); }"
        )
        self.close_pane_btn.clicked.connect(self.pane_close_requested)

        tb.addWidget(self._source_badge)
        tb.addWidget(self.title_label)
        tb.addStretch()
        tb.addWidget(self.line_badge)
        tb.addWidget(self.autoscroll_cb)
        tb.addWidget(self.timestamps_cb)
        tb.addWidget(self.clear_btn)
        tb.addWidget(self.stop_btn)
        tb.addWidget(self.close_pane_btn)
        layout.addWidget(toolbar)

        # ── List view ──
        self._delegate = LogDelegate(viewer=self)
        self._list_view = _LogListView()
        self._list_view.setModel(self._model)
        self._list_view.setItemDelegate(self._delegate)
        self._list_view.setUniformItemSizes(False)
        self._list_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list_view.setStyleSheet(
            f"QListView {{ background: {C_BG}; border: none; border-radius: 0; }}"
            f"QListView::item:selected {{ background: rgba(91,143,255,20); }}"
            f"QListView::item:hover {{ background: rgba(255,255,255,5); }}"
        )
        font = self._list_view.font()
        font.setFamily("JetBrains Mono, Fira Code, Cascadia Code, monospace")
        font.setPointSize(9)
        self._list_view.setFont(font)
        layout.addWidget(self._list_view)
        self._list_view.focus_in.connect(self.pane_activated)

        self.retranslate()

    def retranslate(self) -> None:
        src_key = f"src_{self._source_type}"
        self._source_badge.setText(i18n.tr(src_key))
        self.autoscroll_cb.setText(i18n.tr("viewer_autoscroll"))
        self.timestamps_cb.setText(i18n.tr("viewer_timestamps"))
        self.clear_btn.setToolTip(i18n.tr("viewer_clear"))
        self.stop_btn.setToolTip(i18n.tr("viewer_stop"))
        self.line_badge.setText(i18n.tr("viewer_lines", n=self._model.visible_count()))

    def set_title(self, text: str) -> None:
        self.title_label.setText(text)

    def append_events(self, events: list[tuple[int, str]]) -> None:
        self._model.append_events(events)

    def apply_filter(self, terms: list) -> None:
        self._model.apply_filter(terms)
        self.line_badge.setText(i18n.tr("viewer_lines", n=self._model.visible_count()))

    def apply_search(self, terms: list) -> list:
        """Return (visible_row_idx, char_start, char_len) for every match."""
        self._search_highlights.clear()
        active = [t for t in terms if t.text.strip() and not t.key]
        if not active:
            self._delegate.set_search_highlights({})
            self._list_view.viewport().update()
            return []

        results: list[tuple[int, int, int]] = []
        highlights: dict[int, list[tuple[int, int]]] = {}

        for vis_idx in range(self._model.rowCount()):
            item = self._model.data(self._model.index(vis_idx), _ITEM_ROLE)
            if item is None:
                continue
            for term in active:
                pattern = re.compile(re.escape(term.text), re.IGNORECASE)
                for m in pattern.finditer(item.message):
                    results.append((vis_idx, m.start(), m.end() - m.start()))
                    highlights.setdefault(vis_idx, []).append(
                        (m.start(), m.end() - m.start())
                    )

        self._search_highlights = highlights
        self._delegate.set_search_highlights(highlights)
        self._list_view.viewport().update()
        return sorted(results, key=lambda t: (t[0], t[1]))

    def scroll_to_search_match(self, vis_idx: int, char_start: int, char_len: int) -> None:
        idx = self._model.index(vis_idx)
        self._list_view.scrollTo(idx, QAbstractItemView.ScrollHint.EnsureVisible)
        self._delegate.set_focused_match(vis_idx, char_start, char_len)
        self._list_view.viewport().update()

    def clear(self) -> None:
        self._model.clear()
        self._search_highlights.clear()
        self._delegate.set_search_highlights({})
        self.line_badge.setText(i18n.tr("viewer_lines", n=0))

    def get_json_keys(self) -> set:
        return self._model.get_json_keys()

    def insert_break(self) -> None:
        self._model.insert_break()

    def focus_list(self) -> None:
        self._list_view.setFocus()

    def copy(self) -> None:
        """Copy selected rows' text to clipboard."""
        indexes = self._list_view.selectedIndexes()
        if not indexes:
            return
        texts = []
        for idx in sorted(indexes, key=lambda i: i.row()):
            item = self._model.data(idx, _ITEM_ROLE)
            if item:
                texts.append(item.message)
        QApplication.clipboard().setText("\n".join(texts))


# ── Sidebar helper: one term input row ────────────────────────────────────────

class _TermRowWidget(QWidget):
    """A single filter/search term row: [op toggle] [input(s)] [×]."""

    changed          = pyqtSignal()
    remove_requested = pyqtSignal()

    def __init__(self, operator: str = "", mode: str = "text", parent=None):
        super().__init__(parent)
        self._operator = operator
        self._mode = mode  # "text" | "kv"

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        # Operator toggle (AND ↔ OR), hidden for first row
        self._op_btn = QPushButton(operator or "AND")
        self._op_btn.setFixedSize(36, 20)
        self._op_btn.setVisible(bool(operator))
        self._op_btn.setStyleSheet(
            f"QPushButton {{ background: rgba(120,217,236,26); color: {C_TS}; "
            f"border-radius: 3px; font-size: 9px; font-weight: bold; border: none; }}"
            f"QPushButton:hover {{ background: rgba(120,217,236,51); }}"
        )
        self._op_btn.clicked.connect(self._toggle_operator)
        row.addWidget(self._op_btn)

        # Spacer when no op button (aligns inputs across rows)
        self._op_spacer = QWidget()
        self._op_spacer.setFixedSize(36, 20)
        self._op_spacer.setVisible(not bool(operator))
        row.addWidget(self._op_spacer)

        _input_style = (
            f"background: transparent; color: {C_TEXT}; border: none; "
            "padding: 0 4px; font-size: 11px;"
        )

        if mode == "kv":
            self._key_input = QLineEdit()
            self._key_input.setFixedWidth(60)
            self._key_input.setStyleSheet(
                f"background: transparent; color: {C_TRACE}; border: none; "
                "padding: 0 4px; font-size: 11px;"
            )
            self._key_input.textChanged.connect(self.changed)
            row.addWidget(self._key_input)

            eq_lbl = QLabel("=")
            eq_lbl.setStyleSheet(f"color: {C_MUTED}; font-size: 11px; background: transparent;")
            eq_lbl.setFixedWidth(10)
            row.addWidget(eq_lbl)

            self._val_input = QLineEdit()
            self._val_input.setStyleSheet(_input_style)
            self._val_input.textChanged.connect(self.changed)
            row.addWidget(self._val_input, stretch=1)

            # Alias for common API (set_placeholder, focus_input target val)
            self._input = self._val_input
        else:
            self._input = QLineEdit()
            self._input.setStyleSheet(_input_style)
            self._input.textChanged.connect(self.changed)
            row.addWidget(self._input, stretch=1)

        # Remove button
        self._rm_btn = QPushButton("×")
        self._rm_btn.setFixedSize(20, 20)
        self._rm_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {C_MUTED}; "
            "border: none; font-size: 14px; padding: 0; }"
            f"QPushButton:hover {{ color: {C_ERR}; }}"
        )
        self._rm_btn.clicked.connect(self.remove_requested)
        row.addWidget(self._rm_btn)

    def _toggle_operator(self) -> None:
        self._operator = "OR" if self._operator == "AND" else "AND"
        self._op_btn.setText(self._operator)
        self.changed.emit()

    def to_term_row(self) -> TermRow:
        if self._mode == "kv":
            return TermRow(
                text=self._val_input.text(),
                operator=self._operator,
                key=self._key_input.text(),
            )
        return TermRow(text=self._input.text(), operator=self._operator)

    def set_placeholder(self, text: str) -> None:
        self._input.setPlaceholderText(text)

    def focus_input(self) -> None:
        self._input.setFocus()

    def focus_value_input(self) -> None:
        """Focus the value input (kv mode) or the regular input (text mode)."""
        self._input.setFocus()

    def set_text(self, text: str) -> None:
        """In kv mode, sets the key field. In text mode, sets the single input."""
        if self._mode == "kv":
            self._key_input.setText(text)
        else:
            self._input.setText(text)


# ── Right sidebar: filter + search + JSON keys ─────────────────────────────────

class FilterSearchSidebar(QWidget):
    """Global right sidebar. Call set_active_viewer() when the active tab changes."""

    # SVG templates for the 3 tab icons
    _TAB_SVGS = [
        # Search (magnifier)
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none">'
        '<circle cx="6.5" cy="6.5" r="4" stroke="{color}" stroke-width="1.5"/>'
        '<path d="M10 10L14 14" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>'
        '</svg>',
        # Filter (3 horizontal lines, decreasing)
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none">'
        '<path d="M2 4h12M4 8h8M6 12h4" stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>'
        '</svg>',
        # JSON Keys (curly braces)
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none">'
        '<path d="M5 2C3.5 2 3 2.8 3 4v2c0 .7-.5 1.2-1 1.5.5.3 1 .8 1 1.5v2c0 1.2.5 2 2 2'
        'M11 2c1.5 0 2 .8 2 2v2c0 .7.5 1.2 1 1.5-.5.3-1 .8-1 1.5v2c0 1.2-.5 2-2 2"'
        ' stroke="{color}" stroke-width="1.5" stroke-linecap="round"/>'
        '</svg>',
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(180)
        self.setMaximumWidth(520)
        self.setStyleSheet(
            f"FilterSearchSidebar {{ background: {C_PANEL}; "
            f"border-left: 1px solid {C_BORDER}; }}"
        )

        self._active_viewer: LogViewer | None = None
        self._search_matches: list[tuple[int, int, int]] = []
        self._search_match_index: int = -1
        self._search_term_widgets: list[_TermRowWidget] = []
        self._filter_term_widgets: list[_TermRowWidget] = []
        self._active_tab: int = 0

        # Debounce timers
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(150)
        self._filter_timer.timeout.connect(self._apply_filter_now)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(150)
        self._search_timer.timeout.connect(self._apply_search_now)

        self._lines_timer = QTimer(self)
        self._lines_timer.setSingleShot(True)
        self._lines_timer.setInterval(300)
        self._lines_timer.timeout.connect(self._apply_search_now)

        self._build_ui()

        _key = id(self)
        i18n.register(_key, self.retranslate)
        self.destroyed.connect(lambda _=None, k=_key: i18n.unregister(k))

    # ── UI construction ───────────────────────────────────────────────────────

    def _make_tab_icon(self, svg_tmpl: str, color: str) -> QIcon:
        if not _HAS_SVG:
            return QIcon()
        svg = svg_tmpl.replace("{color}", color)
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        pm = QPixmap(16, 16)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        renderer.render(p)
        p.end()
        return QIcon(pm)

    def _set_tab(self, idx: int) -> None:
        self._active_tab = idx
        self._content_stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._tab_btns):
            active = i == idx
            btn.setIcon(self._make_tab_icon(
                self._TAB_SVGS[i],
                C_ACCENT if active else C_MUTED,
            ))
            if active:
                btn.setStyleSheet(
                    f"QPushButton {{ background: {C_BG}; border: none; "
                    f"border-bottom: 2px solid {C_ACCENT}; border-radius: 0; "
                    f"padding: 0; }}"
                    f"QPushButton:hover {{ background: {C_BG}; }}"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: transparent; border: none; "
                    "border-radius: 0; padding: 0; }"
                    "QPushButton:hover { background: rgba(255,255,255,8); }"
                )

    def _and_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: {C_ACCENT}; color: #000; border: none; "
            f"border-radius: 5px; font-size: 11px; font-weight: 700; padding: 4px 10px; }}"
            f"QPushButton:hover {{ background: #7aa3ff; }}"
        )

    def _or_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: rgba(176,124,240,51); color: {C_TRACE}; "
            f"border: 1px solid rgba(176,124,240,77); border-radius: 5px; "
            f"font-size: 11px; font-weight: 700; padding: 4px 10px; }}"
            f"QPushButton:hover {{ background: rgba(176,124,240,77); }}"
        )

    def _add_btn_style(self) -> str:
        return self._and_btn_style()

    def _nav_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: transparent; color: {C_MUTED}; "
            f"border: 1px solid {C_BORDER}; border-radius: 5px;"
            f"font-size: 11px; padding: 3px 10px; }}"
            f"QPushButton:hover {{ color: {C_TEXT}; border-color: rgba(255,255,255,51); }}"
        )

    def _term_block_style(self) -> str:
        return (
            f"background: {C_BG}; border: 1px solid {C_BORDER}; border-radius: 5px;"
        )

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Icon tab strip ────────────────────────────────────────────────────
        tab_bar = QWidget()
        tab_bar.setFixedHeight(40)
        tab_bar.setStyleSheet(
            f"QWidget {{ background: {C_PANEL}; border-bottom: 1px solid {C_BORDER}; }}"
        )
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(6, 6, 6, 0)
        tab_layout.setSpacing(0)

        self._tab_btns: list[QPushButton] = []
        for i in range(3):
            btn = QPushButton()
            btn.setFixedHeight(32)
            btn.setIconSize(QSize(16, 16))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, idx=i: self._set_tab(idx))
            self._tab_btns.append(btn)
            tab_layout.addWidget(btn, 1)

        outer.addWidget(tab_bar)

        # ── Stacked content pages ─────────────────────────────────────────────
        self._content_stack = QStackedWidget()
        self._content_stack.setStyleSheet(
            f"QStackedWidget {{ background: {C_PANEL}; border: none; }}"
        )

        for build_fn in (
            self._build_search_content,
            self._build_filter_content,
            self._build_json_content,
        ):
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(
                f"QScrollArea {{ border: none; background: {C_PANEL}; }}"
            )
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            page = QWidget()
            page.setStyleSheet(f"QWidget {{ background: {C_PANEL}; }}")
            build_fn(page)
            if page.layout():
                page.layout().addStretch()
            scroll.setWidget(page)
            self._content_stack.addWidget(scroll)

        outer.addWidget(self._content_stack, 1)

        # Ctrl+F: focus search tab
        sc = QShortcut(QKeySequence("Ctrl+F"), self)
        sc.setContext(Qt.ShortcutContext.WindowShortcut)
        sc.activated.connect(self._focus_first_search)

        self._set_tab(0)
        self.retranslate()

    def _build_search_content(self, parent: QWidget) -> None:
        vbox = QVBoxLayout(parent)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(4)

        # Term rows block
        self._search_block = QWidget()
        self._search_block.setStyleSheet(self._term_block_style())
        self._search_rows_layout = QVBoxLayout(self._search_block)
        self._search_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._search_rows_layout.setSpacing(0)
        vbox.addWidget(self._search_block)
        self._add_search_row("")   # initial empty row

        # Add AND/OR buttons
        add_row = QHBoxLayout()
        add_row.setSpacing(4)
        add_row.setContentsMargins(0, 0, 0, 0)
        self._btn_add_search_and = QPushButton()
        self._btn_add_search_and.clicked.connect(lambda: self._add_search_row("AND"))
        self._btn_add_search_and.setFixedHeight(24)
        self._btn_add_search_and.setStyleSheet(self._and_btn_style())
        self._btn_add_search_or = QPushButton()
        self._btn_add_search_or.clicked.connect(lambda: self._add_search_row("OR"))
        self._btn_add_search_or.setFixedHeight(24)
        self._btn_add_search_or.setStyleSheet(self._or_btn_style())
        add_row.addWidget(self._btn_add_search_and)
        add_row.addWidget(self._btn_add_search_or)
        add_row.addStretch()
        vbox.addLayout(add_row)

        # Prev / Next / hits inline
        nav_row = QHBoxLayout()
        nav_row.setSpacing(4)
        nav_row.setContentsMargins(0, 2, 0, 0)
        self._btn_prev = QPushButton()
        self._btn_next = QPushButton()
        self._lbl_hits = QLabel()
        self._lbl_hits.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
        for btn in (self._btn_prev, self._btn_next):
            btn.setFixedHeight(22)
            btn.setStyleSheet(self._nav_btn_style())
        self._btn_prev.clicked.connect(self._search_prev)
        self._btn_next.clicked.connect(self._search_next_match)
        nav_row.addWidget(self._btn_prev)
        nav_row.addWidget(self._btn_next)
        nav_row.addWidget(self._lbl_hits)
        nav_row.addStretch()
        vbox.addLayout(nav_row)

    def _build_filter_content(self, parent: QWidget) -> None:
        vbox = QVBoxLayout(parent)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(4)

        self._filter_block = QWidget()
        self._filter_block.setStyleSheet(self._term_block_style())
        self._filter_rows_layout = QVBoxLayout(self._filter_block)
        self._filter_rows_layout.setContentsMargins(0, 0, 0, 0)
        self._filter_rows_layout.setSpacing(0)
        vbox.addWidget(self._filter_block)
        self._add_filter_row("")   # initial empty row

        add_row = QHBoxLayout()
        add_row.setSpacing(4)
        add_row.setContentsMargins(0, 0, 0, 0)
        self._btn_add_filter_and = QPushButton()
        self._btn_add_filter_and.clicked.connect(lambda: self._add_filter_row("AND"))
        self._btn_add_filter_and.setFixedHeight(24)
        self._btn_add_filter_and.setStyleSheet(self._and_btn_style())
        self._btn_add_filter_or = QPushButton()
        self._btn_add_filter_or.clicked.connect(lambda: self._add_filter_row("OR"))
        self._btn_add_filter_or.setFixedHeight(24)
        self._btn_add_filter_or.setStyleSheet(self._or_btn_style())
        self._btn_add_filter_kv = QPushButton()
        self._btn_add_filter_kv.clicked.connect(lambda: self._add_filter_row("AND", mode="kv"))
        self._btn_add_filter_kv.setFixedHeight(24)
        self._btn_add_filter_kv.setStyleSheet(self._nav_btn_style())
        add_row.addWidget(self._btn_add_filter_and)
        add_row.addWidget(self._btn_add_filter_or)
        add_row.addWidget(self._btn_add_filter_kv)
        add_row.addStretch()
        vbox.addLayout(add_row)

        live_row = QHBoxLayout()
        live_row.setContentsMargins(0, 2, 0, 0)
        self._cb_live = QCheckBox()
        self._cb_live.setChecked(True)
        self._cb_live.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
        self._cb_live.stateChanged.connect(lambda _: self._filter_timer.start())
        live_row.addWidget(self._cb_live)
        live_row.addStretch()
        vbox.addLayout(live_row)

    def _build_json_content(self, parent: QWidget) -> None:
        vbox = QVBoxLayout(parent)
        vbox.setContentsMargins(10, 8, 10, 10)
        vbox.setSpacing(4)

        self._json_container = QWidget()
        self._json_container.setStyleSheet("background: transparent;")
        self._json_layout = QVBoxLayout(self._json_container)
        self._json_layout.setContentsMargins(0, 0, 0, 0)
        self._json_layout.setSpacing(4)
        self._lbl_json_ph = QLabel()
        self._lbl_json_ph.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
        self._json_layout.addWidget(self._lbl_json_ph)
        vbox.addWidget(self._json_container)

    # ── Term row management ───────────────────────────────────────────────────

    def _add_search_row(self, operator: str) -> None:
        if self._search_term_widgets:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #2c2c2c; max-height: 1px;")
            self._search_rows_layout.addWidget(sep)
        row = _TermRowWidget(operator, parent=self)
        row.setContentsMargins(8, 4, 4, 4)
        row.changed.connect(self._on_search_changed)
        row.remove_requested.connect(lambda r=row: self._remove_search_row(r))
        self._search_term_widgets.append(row)
        self._search_rows_layout.addWidget(row)
        row.set_placeholder(i18n.tr("sidebar_term_ph"))

    def _rebuild_row_block(
        self,
        block: QWidget,
        layout: QVBoxLayout,
        widgets: list,
        section: str,
    ) -> None:
        """Clear layout and re-insert all term rows with separators between them."""
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w and w not in widgets:
                w.deleteLater()
        for i, w in enumerate(widgets):
            if i > 0:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setStyleSheet("color: #2c2c2c; max-height: 1px;")
                layout.addWidget(sep)
            layout.addWidget(w)

    def _remove_search_row(self, row: _TermRowWidget) -> None:
        if len(self._search_term_widgets) == 1:
            return  # always keep at least one row
        self._search_term_widgets.remove(row)
        self._search_rows_layout.removeWidget(row)
        row.deleteLater()
        self._rebuild_row_block(
            self._search_block,
            self._search_rows_layout,
            self._search_term_widgets,
            "search",
        )
        self._on_search_changed()

    def _add_filter_row(self, operator: str, mode: str = "text", prefill_key: str = "") -> None:
        if self._filter_term_widgets:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("color: #2c2c2c; max-height: 1px;")
            self._filter_rows_layout.addWidget(sep)
        row = _TermRowWidget(operator, mode=mode, parent=self)
        row.setContentsMargins(8, 4, 4, 4)
        row.changed.connect(self._on_filter_changed)
        row.remove_requested.connect(lambda r=row: self._remove_filter_row(r))
        self._filter_term_widgets.append(row)
        self._filter_rows_layout.addWidget(row)
        row.set_placeholder(i18n.tr("sidebar_term_ph"))
        if prefill_key:
            row.set_text(prefill_key)

    def _remove_filter_row(self, row: _TermRowWidget) -> None:
        if len(self._filter_term_widgets) == 1:
            return
        self._filter_term_widgets.remove(row)
        self._filter_rows_layout.removeWidget(row)
        row.deleteLater()
        self._rebuild_row_block(
            self._filter_block,
            self._filter_rows_layout,
            self._filter_term_widgets,
            "filter",
        )
        self._on_filter_changed()

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_search_changed(self) -> None:
        self._search_timer.start()

    def _on_filter_changed(self) -> None:
        if self._cb_live.isChecked():
            self._filter_timer.start()
        self._update_filter_badge()

    def _on_json_keys_updated(self, keys: set) -> None:
        self._rebuild_json_chips(keys)

    def _on_lines_appended(self) -> None:
        self._lines_timer.start()   # debounced search re-scan

    # ── Active viewer management ──────────────────────────────────────────────

    def set_active_viewer(self, viewer: LogViewer | None) -> None:
        if self._active_viewer is not None:
            self._active_viewer.json_keys_updated.disconnect(self._on_json_keys_updated)
            self._active_viewer.lines_appended.disconnect(self._on_lines_appended)
            self._active_viewer.filter_applied.disconnect(self._refresh_search)
        self._active_viewer = viewer
        if viewer is not None:
            viewer.json_keys_updated.connect(self._on_json_keys_updated)
            viewer.lines_appended.connect(self._on_lines_appended)
            viewer.filter_applied.connect(self._refresh_search)
            self._on_json_keys_updated(viewer.get_json_keys())
            viewer.apply_filter(self._current_filter_terms())
            # _refresh_search is triggered by filter_applied signal

    def _current_filter_terms(self) -> list[TermRow]:
        return [w.to_term_row() for w in self._filter_term_widgets]

    def _current_search_terms(self) -> list[TermRow]:
        return [w.to_term_row() for w in self._search_term_widgets]

    # ── Apply filter / search ─────────────────────────────────────────────────

    def _apply_filter_now(self) -> None:
        if self._active_viewer:
            self._active_viewer.apply_filter(self._current_filter_terms())

    def _apply_search_now(self) -> None:
        self._refresh_search()

    def _refresh_search(self) -> None:
        if self._active_viewer is None:
            self._search_matches = []
            self._search_match_index = -1
            self._update_hits_label()
            return
        terms = self._current_search_terms()
        self._search_matches = self._active_viewer.apply_search(terms)
        self._search_match_index = 0 if self._search_matches else -1
        self._update_hits_label()
        if self._search_matches:
            self._scroll_to_match(0)

    def _search_prev(self) -> None:
        if not self._search_matches:
            return
        self._search_match_index = (self._search_match_index - 1) % len(self._search_matches)
        self._scroll_to_match(self._search_match_index)
        self._update_hits_label()

    def _search_next_match(self) -> None:
        if not self._search_matches:
            return
        self._search_match_index = (self._search_match_index + 1) % len(self._search_matches)
        self._scroll_to_match(self._search_match_index)
        self._update_hits_label()

    def _scroll_to_match(self, index: int) -> None:
        if self._active_viewer is None or not self._search_matches:
            return
        vis_idx, char_start, char_len = self._search_matches[index]
        self._active_viewer.scroll_to_search_match(vis_idx, char_start, char_len)

    def _update_hits_label(self) -> None:
        n = len(self._search_matches)
        if n == 0:
            self._lbl_hits.setText(i18n.tr("sidebar_no_hits"))
        else:
            self._lbl_hits.setText(i18n.tr("sidebar_hits", n=n))
        self._update_search_badge()

    def _update_search_badge(self) -> None:
        pass  # badges removed in tab design

    def _update_filter_badge(self) -> None:
        pass

    def _update_json_badge(self) -> None:
        pass

    # ── JSON chips ────────────────────────────────────────────────────────────

    def _rebuild_json_chips(self, keys: set) -> None:
        # Clear existing chips, but do NOT delete the placeholder label widget
        while self._json_layout.count():
            item = self._json_layout.takeAt(0)
            w = item.widget()
            if w and w is not self._lbl_json_ph:
                w.deleteLater()

        sorted_keys = sorted(keys)[:50]  # cap at 50
        if not sorted_keys:
            self._json_layout.addWidget(self._lbl_json_ph)
            return

        for key in sorted_keys:
            btn = QPushButton(key)
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton {{ background: {C_BG}; color: {C_DEBUG}; "
                f"border: 1px solid {C_BORDER}; border-radius: 5px; font-size: 11px; "
                f"font-family: 'JetBrains Mono', monospace; "
                f"padding: 2px 8px; text-align: left; }}"
                f"QPushButton:hover {{ border-color: {C_ACCENT}; }}"
            )
            btn.clicked.connect(lambda checked=False, k=key: self._add_filter_from_key(k))
            self._json_layout.addWidget(btn)
        self._update_json_badge()

    def _add_filter_from_key(self, key: str) -> None:
        self._set_tab(1)  # switch to Filter tab
        self._add_filter_row("AND", mode="kv", prefill_key=key)
        self._filter_term_widgets[-1].focus_value_input()
        if self._cb_live.isChecked():
            self._filter_timer.start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _focus_first_search(self) -> None:
        self._set_tab(0)
        if self._search_term_widgets:
            self._search_term_widgets[0].focus_input()
        self.show()

    def retranslate(self) -> None:
        self._btn_add_search_and.setText(i18n.tr("sidebar_add_and"))
        self._btn_add_search_or.setText(i18n.tr("sidebar_add_or"))
        self._btn_prev.setText("▲ Prev")
        self._btn_next.setText("▼ Next")
        self._btn_add_filter_and.setText(i18n.tr("sidebar_add_and"))
        self._btn_add_filter_or.setText(i18n.tr("sidebar_add_or"))
        self._btn_add_filter_kv.setText("+ key=val")
        self._cb_live.setText(i18n.tr("sidebar_live_filter"))
        self._lbl_json_ph.setText(i18n.tr("sidebar_json_ph"))
        for w in self._search_term_widgets + self._filter_term_widgets:
            w.set_placeholder(i18n.tr("sidebar_term_ph"))
        self._update_hits_label()


# ── MainWindow ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SimpleLog")
        self.resize(1380, 860)
        self._workers: dict[int, object] = {}
        self._cur_viewer: LogViewer | None = None
        self._splitter_style: str = ""
        self._update_worker = None  # UpdateWorker instance (kept alive)
        self._left_sidebar_width: int = 326
        self._right_sidebar_width: int = 240
        self._build_ui()
        self._build_menubar()

    def _build_ui(self):
        # Central container
        central = QWidget()
        central.setStyleSheet(f"background: {C_BG};")
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Nav rail
        self._nav = NavRail()
        self._nav.index_changed.connect(self._on_nav_index_changed)
        root.addWidget(self._nav)

        # Side stack
        self._side_stack = SideStack()

        self._remote_panel = RemoteHomePanel()
        self._remote_panel.tab_requested.connect(self._dispatch_open_tab)
        self._side_stack.addWidget(self._remote_panel)  # index 0

        self._file_panel = FilePanel()
        self._file_panel.open_tab.connect(self.open_file_tab)
        self._side_stack.addWidget(self._file_panel)    # index 1

        self._ws_panel = WorkspacePanel()
        self._ws_panel.save_workspace.connect(self._save_current_as_workspace)
        self._ws_panel.open_workspace.connect(self._open_workspace)
        self._ws_panel.delete_workspace.connect(self._on_delete_workspace)
        self._ws_panel.rename_workspace.connect(self._on_rename_workspace)
        self._side_stack.addWidget(self._ws_panel)      # index 2

        self._splitter_style = (
            f"QSplitter::handle {{ background: {C_BORDER}; }}"
            f"QSplitter::handle:horizontal {{ width: 4px; }}"
            f"QSplitter::handle:vertical {{ height: 4px; }}"
            f"QSplitter::handle:hover {{ background: {C_ACCENT}; }}"
        )

        # Top-level browser-style tab widget: each tab takes the full space
        self._top_tabs = _SLTabWidget()
        self._top_tabs.setTabsClosable(True)
        self._top_tabs.setDocumentMode(True)
        self._top_tabs.setStyleSheet(
            f"QTabWidget::pane {{ border: none; background: {C_BG}; border-top: 1px solid {C_BORDER}; }}"
            f"QTabBar::tab {{ background: {C_PANEL}; color: {C_MUTED};"
            f" padding: 0 16px 0 14px; min-height: 38px; border: none;"
            f" border-right: 1px solid {C_BORDER}; }}"
            f"QTabBar::tab:selected {{ background: {C_BG}; color: {C_TEXT};"
            f" border-top: 2px solid {C_ACCENT}; }}"
            f"QTabBar::tab:hover:!selected {{ color: {C_TEXT};"
            f" background: rgba(255,255,255,5); }}"
        )
        self._top_tabs.tabCloseRequested.connect(self._close_tab_at)
        self._top_tabs.currentChanged.connect(self._on_top_tab_changed)

        self._sidebar = FilterSearchSidebar(self)

        # Outer splitter: content area | sidebar
        self._outer_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._outer_splitter.setChildrenCollapsible(False)
        self._outer_splitter.setStyleSheet(self._splitter_style)
        self._outer_splitter.addWidget(self._top_tabs)
        self._outer_splitter.addWidget(self._sidebar)
        self._outer_splitter.setSizes([10000, 240])
        self._outer_splitter.setStretchFactor(0, 1)
        self._outer_splitter.setStretchFactor(1, 0)
        self._outer_splitter.splitterMoved.connect(lambda *_: self._reposition_toggles())

        # Main splitter: left panel | content+right-sidebar
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setChildrenCollapsible(False)
        self._main_splitter.setStyleSheet(self._splitter_style)
        self._main_splitter.addWidget(self._side_stack)
        self._main_splitter.addWidget(self._outer_splitter)
        self._main_splitter.setSizes([326, 10000])
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)
        self._main_splitter.splitterMoved.connect(lambda *_: self._reposition_toggles())
        root.addWidget(self._main_splitter, stretch=1)

        # Floating edge toggle buttons (overlaid on central widget)
        self._btn_left_toggle = _SidebarEdgeBtn("left", central)
        self._btn_left_toggle.set_svg(_SVG_CHEVRON_LEFT)
        self._btn_left_toggle.setToolTip("Toggle sidebar  (Ctrl+\\)")
        self._btn_left_toggle.clicked.connect(self._toggle_left_sidebar)
        self._btn_left_toggle.show()

        self._btn_right_toggle = _SidebarEdgeBtn("right", central)
        self._btn_right_toggle.set_svg(_SVG_CHEVRON_RIGHT)
        self._btn_right_toggle.setToolTip("Toggle search panel  (Ctrl+Shift+F)")
        self._btn_right_toggle.clicked.connect(self._toggle_right_sidebar)
        self._btn_right_toggle.show()

        sc_toggle = QShortcut(QKeySequence("Ctrl+Shift+F"), self)
        sc_toggle.activated.connect(self._toggle_right_sidebar)

        sc_left = QShortcut(QKeySequence("Ctrl+\\"), self)
        sc_left.activated.connect(self._toggle_left_sidebar)

        # Status bar
        self._status = QStatusBar()
        self._status.setFixedHeight(26)
        self._status.setStyleSheet(
            f"QStatusBar {{ background: {C_STATUS}; border-top: 1px solid {C_BORDER};"
            f" color: {C_MUTED}; font-family: 'JetBrains Mono', monospace; font-size: 11px; }}"
        )
        self.setStatusBar(self._status)
        self._status.showMessage(i18n.tr("status_ready"))

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _build_menubar(self) -> None:
        mb = self.menuBar()

        # ── File ──
        self._menu_file = mb.addMenu("")
        self._act_open = QAction(self)
        self._act_open.setShortcut(QKeySequence("Ctrl+O"))
        self._act_open.triggered.connect(self._action_open_file)
        self._menu_file.addAction(self._act_open)

        self._act_close_all = QAction(self)
        self._act_close_all.setShortcut(QKeySequence("Ctrl+W"))
        self._act_close_all.triggered.connect(self._action_close_all_logs)
        self._menu_file.addAction(self._act_close_all)

        self._menu_file.addSeparator()

        self._act_update = QAction(self)
        self._act_update.triggered.connect(self._action_check_update)
        self._menu_file.addAction(self._act_update)

        self._menu_file.addSeparator()

        self._act_quit = QAction(self)
        self._act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        self._act_quit.triggered.connect(self.close)
        self._menu_file.addAction(self._act_quit)

        # ── Edit ──
        self._menu_edit = mb.addMenu("")
        self._act_copy = QAction(self)
        self._act_copy.setShortcut(QKeySequence("Ctrl+C"))
        self._act_copy.triggered.connect(self._action_copy)
        self._menu_edit.addAction(self._act_copy)

        self._menu_edit.addSeparator()

        self._act_break = QAction(self)
        self._act_break.setShortcut(QKeySequence("Return"))
        self._act_break.triggered.connect(self._action_break)
        self._menu_edit.addAction(self._act_break)

        # ── Language ──
        self._menu_lang = mb.addMenu("")
        ag = QButtonGroup(self)  # not actually needed but keeps logic tidy
        ag  # noqa: B018

        self._act_lang_en = QAction(self)
        self._act_lang_en.setCheckable(True)
        self._act_lang_en.triggered.connect(lambda: self._action_set_language("en"))
        self._menu_lang.addAction(self._act_lang_en)

        self._act_lang_fr = QAction(self)
        self._act_lang_fr.setCheckable(True)
        self._act_lang_fr.triggered.connect(lambda: self._action_set_language("fr"))
        self._menu_lang.addAction(self._act_lang_fr)

        self._act_lang_de = QAction(self)
        self._act_lang_de.setCheckable(True)
        self._act_lang_de.triggered.connect(lambda: self._action_set_language("de"))
        self._menu_lang.addAction(self._act_lang_de)

        self._act_lang_es = QAction(self)
        self._act_lang_es.setCheckable(True)
        self._act_lang_es.triggered.connect(lambda: self._action_set_language("es"))
        self._menu_lang.addAction(self._act_lang_es)

        self._act_lang_zh = QAction(self)
        self._act_lang_zh.setCheckable(True)
        self._act_lang_zh.triggered.connect(lambda: self._action_set_language("zh"))
        self._menu_lang.addAction(self._act_lang_zh)

        # ── Help ──
        self._menu_help = mb.addMenu("")
        self._act_help_ref = QAction(self)
        self._act_help_ref.triggered.connect(self._action_help)
        self._menu_help.addAction(self._act_help_ref)

        self._menu_help.addSeparator()

        self._act_about = QAction(self)
        self._act_about.triggered.connect(self._action_about)
        self._menu_help.addAction(self._act_about)

        self._retranslate_menubar()

    def _retranslate_menubar(self) -> None:
        locale = i18n.get_locale()
        self._menu_file.setTitle(i18n.tr("menu_file"))
        self._act_open.setText(i18n.tr("action_open"))
        self._act_close_all.setText(i18n.tr("action_close_all"))
        self._act_update.setText(i18n.tr("action_update"))
        self._act_quit.setText(i18n.tr("action_quit"))
        self._menu_edit.setTitle(i18n.tr("menu_edit"))
        self._act_copy.setText(i18n.tr("action_copy"))
        self._act_break.setText(i18n.tr("action_break"))
        self._menu_lang.setTitle(i18n.tr("menu_language"))
        self._act_lang_en.setText(i18n.tr("lang_english"))
        self._act_lang_en.setChecked(locale == "en")
        self._act_lang_fr.setText(i18n.tr("lang_french"))
        self._act_lang_fr.setChecked(locale == "fr")
        self._act_lang_de.setText(i18n.tr("lang_german"))
        self._act_lang_de.setChecked(locale == "de")
        self._act_lang_es.setText(i18n.tr("lang_spanish"))
        self._act_lang_es.setChecked(locale == "es")
        self._act_lang_zh.setText(i18n.tr("lang_chinese"))
        self._act_lang_zh.setChecked(locale == "zh")
        self._menu_help.setTitle(i18n.tr("menu_help"))
        self._act_help_ref.setText(i18n.tr("action_help_ref"))
        self._act_about.setText(i18n.tr("action_about"))

    # ── Menu action handlers ───────────────────────────────────────────────────

    def _action_open_file(self) -> None:
        """File → Open: browse and open a log file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            i18n.tr("action_open"),
            os.path.expanduser("~"),
            "Log files (*.log *.txt *.out *.err *.json);;All files (*)",
        )
        if path and os.path.isfile(path):
            self.open_file_tab(path)
            # Also update FilePanel's recent list
            self._file_panel._open_path(path)

    def _action_check_update(self) -> None:
        """File → Check for Updates: async GitHub release check."""
        from version import __version__
        from workers import UpdateWorker

        self._update_worker = UpdateWorker(__version__)
        self._update_worker.up_to_date.connect(self._on_up_to_date)
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.error.connect(
            lambda msg: QMessageBox.warning(
                self, i18n.tr("update_title"), i18n.tr("update_error", error=msg)
            )
        )
        self._act_update.setEnabled(False)
        self._update_worker.finished.connect(lambda: self._act_update.setEnabled(True))
        self._update_worker.start()

    def _action_about(self) -> None:
        from version import __version__
        QMessageBox.about(
            self,
            i18n.tr("action_about"),
            f"<b>SimpleLog</b> v{__version__}<br><br>"
            f"Fast multi-source log viewer",
        )

    def _on_up_to_date(self, version: str) -> None:
        QMessageBox.information(
            self,
            i18n.tr("update_title"),
            i18n.tr("update_up_to_date", version=version),
        )

    def _on_update_available(self, latest: str, url: str) -> None:
        from version import __version__
        box = QMessageBox(self)
        box.setWindowTitle(i18n.tr("update_title"))
        box.setText(i18n.tr("update_available", latest=latest, current=__version__))

        can_auto = self._auto_update_asset_url(latest) is not None
        if can_auto:
            action_btn = box.addButton(i18n.tr("update_install"), QMessageBox.ButtonRole.AcceptRole)
        else:
            action_btn = box.addButton(i18n.tr("update_download"), QMessageBox.ButtonRole.AcceptRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is not action_btn:
            return
        if can_auto:
            self._install_update(latest)
        else:
            QDesktopServices.openUrl(QUrl(url))

    def _auto_update_asset_url(self, tag: str) -> str | None:
        """Return the direct download URL for this platform+tag, or None if auto-update is unsupported."""
        base = f"https://github.com/sindus/simplelog/releases/download/{tag}"
        if os.environ.get("APPIMAGE"):
            return f"{base}/simplelog-x86_64.AppImage"
        if getattr(sys, "frozen", False) and platform.system() == "Darwin":
            return f"{base}/SimpleLog-macOS.dmg"
        if getattr(sys, "frozen", False) and platform.system() == "Linux" and shutil.which("pkexec"):
            return f"{base}/simplelog_amd64.deb"
        return None

    def _install_update(self, tag: str) -> None:
        from version import __version__
        from workers import DownloadWorker

        asset_url = self._auto_update_asset_url(tag)
        if asset_url is None:
            return

        if asset_url.endswith(".AppImage"):
            suffix = ".AppImage"
        elif asset_url.endswith(".deb"):
            suffix = ".deb"
        else:
            suffix = ".dmg"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)

        progress = QProgressDialog(i18n.tr("update_downloading"), None, 0, 100, self)
        progress.setWindowTitle(i18n.tr("update_title"))
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setCancelButton(None)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        self._dl_worker = DownloadWorker(asset_url, tmp_path, __version__)
        self._dl_worker.progress.connect(progress.setValue)
        self._dl_worker.error.connect(lambda msg: (
            progress.close(),
            QMessageBox.warning(self, i18n.tr("update_title"), i18n.tr("update_install_error", error=msg)),
        ))
        self._dl_worker.finished.connect(lambda path: self._apply_update(path, progress))
        self._dl_worker.start()

    def _apply_update(self, tmp_path: str, progress: QProgressDialog) -> None:
        progress.close()

        if tmp_path.endswith(".deb"):
            # Run pkexec without capture_output so polkit can show its
            # authentication dialog and communicate with the session agent.
            log_path = os.path.join(tempfile.gettempdir(), "simplelog-update.log")
            with open(log_path, "w") as log_f:
                result = subprocess.run(  # noqa: S603
                    ["pkexec", "dpkg", "-i", tmp_path],
                    stdout=log_f, stderr=log_f,
                )
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            if result.returncode != 0:
                try:
                    error_detail = open(log_path).read(500)  # noqa: SIM115
                except OSError:
                    error_detail = f"exit code {result.returncode}"
                QMessageBox.warning(
                    self, i18n.tr("update_title"),
                    i18n.tr("update_install_error", error=error_detail),
                )
                return
            QMessageBox.information(self, i18n.tr("update_title"), i18n.tr("update_restarting"))
            # Use a background script so the new binary starts after we exit
            pid = os.getpid()
            exe = sys.executable
            fd, script_path = tempfile.mkstemp(suffix=".sh")
            script = (
                f"#!/bin/sh\n"
                f"while kill -0 {pid} 2>/dev/null; do sleep 0.1; done\n"
                f"setsid '{exe}' >/dev/null 2>&1 &\n"
                f"rm -- \"$0\"\n"
            )
            os.write(fd, script.encode())
            os.close(fd)
            os.chmod(script_path, stat.S_IRWXU)
            subprocess.Popen(["/bin/sh", script_path], close_fds=True)  # noqa: S603
            QApplication.quit()
            return

        QMessageBox.information(self, i18n.tr("update_title"), i18n.tr("update_restarting"))

        pid = os.getpid()
        if tmp_path.endswith(".AppImage"):
            old_path = os.environ["APPIMAGE"]
            script = (
                f"#!/bin/sh\n"
                f"while kill -0 {pid} 2>/dev/null; do sleep 0.2; done\n"
                f"cp -f '{tmp_path}' '{old_path}'\n"
                f"chmod +x '{old_path}'\n"
                f"rm -f '{tmp_path}'\n"
                f"setsid '{old_path}' >/dev/null 2>&1 &\n"
                f"rm -- \"$0\"\n"
            )
        else:
            # macOS: replace .app bundle from mounted DMG
            app_bundle = os.path.abspath(
                os.path.join(os.path.dirname(sys.executable), "..", "..", "..")
            )
            app_dir = os.path.dirname(app_bundle)
            script = (
                f"#!/bin/sh\n"
                f"while kill -0 {pid} 2>/dev/null; do sleep 0.1; done\n"
                f"MOUNT=$(hdiutil attach '{tmp_path}' -nobrowse -quiet | awk 'END{{print $NF}}')\n"
                f"rm -rf '{app_bundle}'\n"
                f"cp -R \"$MOUNT/SimpleLog.app\" '{app_dir}/'\n"
                f"hdiutil detach \"$MOUNT\" -quiet\n"
                f"rm '{tmp_path}'\n"
                f"open '{app_bundle}'\n"
                f"rm -- \"$0\"\n"
            )

        fd, script_path = tempfile.mkstemp(suffix=".sh")
        os.write(fd, script.encode())
        os.close(fd)
        os.chmod(script_path, stat.S_IRWXU)
        subprocess.Popen(["/bin/sh", script_path], close_fds=True)  # noqa: S603
        QApplication.quit()

    def _action_copy(self) -> None:
        """Edit → Copy: copy selected text from active viewer."""
        viewer = self._active_viewer()
        if viewer:
            viewer.copy()

    def _action_break(self) -> None:
        viewer = self._active_viewer()
        if viewer:
            viewer.insert_break()

    def _action_help(self) -> None:
        """Help → CLI Reference: show documentation dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle(i18n.tr("help_title"))
        dlg.resize(560, 480)
        dlg.setStyleSheet(f"background: {C_BG}; color: {C_TEXT};")

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(i18n.tr("help_content"))
        text.setStyleSheet(
            f"background: {C_CARD}; border: 1px solid {C_DIVIDER}; border-radius: 8px;"
            "font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px;"
            f"color: {C_TEXT}; padding: 12px;"
        )
        layout.addWidget(text)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.accept)
        btns.setStyleSheet(f"color: {C_TEXT};")
        layout.addWidget(btns)

        dlg.exec()

    def _action_set_language(self, locale: str) -> None:
        i18n.set_locale(locale)
        i18n.save_locale()
        i18n.retranslate_all()
        self._retranslate_menubar()
        self._status.showMessage(i18n.tr("status_ready"))

    def _active_viewer(self) -> LogViewer | None:
        return self._cur_viewer

    # ── Tab / pane management ─────────────────────────────────────────────────

    _MAX_PANES = 9

    def _make_tab_splitter(self, orient: Qt.Orientation = Qt.Orientation.Horizontal) -> QSplitter:
        s = QSplitter(orient)
        s.setChildrenCollapsible(False)
        s.setStyleSheet(self._splitter_style)
        return s

    def _current_tab_splitter(self) -> QSplitter | None:
        w = self._top_tabs.currentWidget()
        return w if isinstance(w, QSplitter) else None

    def _first_viewer_in(self, spl: QSplitter) -> LogViewer | None:
        for i in range(spl.count()):
            w = spl.widget(i)
            if isinstance(w, LogViewer):
                return w
            if isinstance(w, QSplitter):
                v = self._first_viewer_in(w)
                if v:
                    return v
        return None

    def _count_viewers_in(self, spl: QSplitter) -> int:
        total = 0
        for i in range(spl.count()):
            w = spl.widget(i)
            if isinstance(w, LogViewer):
                total += 1
            elif isinstance(w, QSplitter):
                total += self._count_viewers_in(w)
        return total

    def _stop_all_in_splitter(self, spl: QSplitter) -> None:
        for i in range(spl.count()):
            w = spl.widget(i)
            if isinstance(w, LogViewer):
                self._stop_viewer(w)
            elif isinstance(w, QSplitter):
                self._stop_all_in_splitter(w)

    def _collect_ws_meta(self, spl: QSplitter, logs: list) -> None:
        for i in range(spl.count()):
            w = spl.widget(i)
            if isinstance(w, LogViewer) and w._ws_meta:
                logs.append(w._ws_meta.copy())
            elif isinstance(w, QSplitter):
                self._collect_ws_meta(w, logs)

    def _set_active_viewer(self, viewer: LogViewer | None) -> None:
        self._cur_viewer = viewer
        self._sidebar.set_active_viewer(viewer)
        if viewer:
            viewer.focus_list()

    def _on_top_tab_changed(self, _idx: int) -> None:
        spl = self._current_tab_splitter()
        viewer = self._first_viewer_in(spl) if spl else None
        self._set_active_viewer(viewer)

    def _add_viewer_to_current_tab(
        self, viewer: LogViewer, orientation: Qt.Orientation, title: str
    ) -> None:
        spl = self._current_tab_splitter()
        if spl is None:
            spl = self._make_tab_splitter(orientation)
            idx = self._top_tabs.addTab(spl, title)
            self._top_tabs.setCurrentIndex(idx)
            spl.addWidget(viewer)
            return

        if self._count_viewers_in(spl) >= self._MAX_PANES:
            return

        active = self._cur_viewer
        parent_spl = active.parent() if active else None

        if isinstance(parent_spl, QSplitter) and parent_spl.orientation() == orientation:
            # Capture total before inserting so the window doesn't grow
            old_sizes = parent_spl.sizes()
            total = sum(old_sizes)
            idx = parent_spl.indexOf(active)
            parent_spl.insertWidget(idx + 1, viewer)
            n = parent_spl.count()
            if total > 0:
                share = total // n
                new_sizes = [share] * n
                new_sizes[-1] += total - sum(new_sizes)  # give remainder to last
                parent_spl.setSizes(new_sizes)
        elif isinstance(parent_spl, QSplitter):
            idx = parent_spl.indexOf(active)
            parent_sizes = parent_spl.sizes()
            sub = self._make_tab_splitter(orientation)
            active.setParent(None)
            sub.addWidget(active)
            sub.addWidget(viewer)
            sub.setStretchFactor(0, 1)
            sub.setStretchFactor(1, 1)
            parent_spl.insertWidget(idx, sub)
            parent_spl.setSizes(parent_sizes)
        else:
            spl.addWidget(viewer)

    def _close_tab_at(self, idx: int) -> None:
        spl = self._top_tabs.widget(idx)
        if isinstance(spl, QSplitter):
            self._stop_all_in_splitter(spl)
        self._top_tabs.removeTab(idx)
        if spl:
            spl.deleteLater()
        spl2 = self._current_tab_splitter()
        viewer = self._first_viewer_in(spl2) if spl2 else None
        self._set_active_viewer(viewer)

    def _close_pane(self, viewer: LogViewer) -> None:
        self._stop_viewer(viewer)
        parent = viewer.parent()
        viewer.setParent(None)
        viewer.deleteLater()
        if isinstance(parent, QSplitter):
            self._cleanup_empty_splitters(parent)
        spl = self._current_tab_splitter()
        self._set_active_viewer(self._first_viewer_in(spl) if spl else None)

    def _cleanup_empty_splitters(self, spl: QSplitter) -> None:
        if spl.count() > 0:
            return
        tab_idx = self._top_tabs.indexOf(spl)
        if tab_idx >= 0:
            self._top_tabs.removeTab(tab_idx)
            spl.deleteLater()
            return
        parent = spl.parent()
        spl.setParent(None)
        spl.deleteLater()
        if isinstance(parent, QSplitter):
            self._cleanup_empty_splitters(parent)

    # ── Nav ───────────────────────────────────────────────────────────────────

    def _on_nav_index_changed(self, idx: int):
        self._side_stack.setCurrentIndex(idx)
        if not self._side_stack.isVisible():
            self._toggle_left_sidebar()

    def _dispatch_open_tab(self, cfg: dict, split: str = "tab") -> None:
        dispatch = {
            "cloudwatch":       self.open_cloudwatch_tab,
            "ssh":              self.open_ssh_tab,
            "docker_container": self.open_docker_tab,
            "docker_compose":   self.open_docker_tab,
            "docker_exec_file": self.open_docker_tab,
            "vercel":           self.open_vercel_tab,
            "gcp":              self.open_gcp_tab,
            "azure":            self.open_azure_tab,
            "loki":             self.open_loki_tab,
            "datadog":          self.open_datadog_tab,
            "elastic":          self.open_elastic_tab,
            "railway":          self.open_railway_tab,
            "flyio":            self.open_flyio_tab,
            "kubernetes":       self.open_kubernetes_tab,
        }
        fn = dispatch.get(cfg.get("type", ""))
        if fn:
            fn(cfg, split)

    def _toggle_left_sidebar(self) -> None:
        visible = self._side_stack.isVisible()
        if visible:
            sizes = self._main_splitter.sizes()
            if sizes[0] > 0:
                self._left_sidebar_width = sizes[0]
            self._side_stack.setVisible(False)
        else:
            self._side_stack.setVisible(True)
            total = sum(self._main_splitter.sizes())
            self._main_splitter.setSizes([
                self._left_sidebar_width,
                max(1, total - self._left_sidebar_width),
            ])
        now_visible = not visible
        self._btn_left_toggle.set_svg(_SVG_CHEVRON_LEFT if now_visible else _SVG_CHEVRON_RIGHT)
        QTimer.singleShot(0, self._reposition_toggles)

    def _toggle_right_sidebar(self) -> None:
        visible = self._sidebar.isVisible()
        if visible:
            sizes = self._outer_splitter.sizes()
            if sizes[1] > 0:
                self._right_sidebar_width = sizes[1]
            self._sidebar.setVisible(False)
        else:
            self._sidebar.setVisible(True)
            total = sum(self._outer_splitter.sizes())
            self._outer_splitter.setSizes([
                max(1, total - self._right_sidebar_width),
                self._right_sidebar_width,
            ])
        now_visible = not visible
        self._btn_right_toggle.set_svg(_SVG_CHEVRON_RIGHT if now_visible else _SVG_CHEVRON_LEFT)
        QTimer.singleShot(0, self._reposition_toggles)

    def _reposition_toggles(self) -> None:
        central = self.centralWidget()
        if central is None:
            return
        btn_h = 40
        cy = (central.height() - btn_h) // 2

        # Left toggle: on the right edge of the side stack (or nav rail when hidden)
        anchor = self._side_stack if self._side_stack.isVisible() else self._nav
        pt = anchor.mapTo(central, QPoint(anchor.width(), 0))
        self._btn_left_toggle.move(pt.x() - 10, cy)
        self._btn_left_toggle.raise_()

        # Right toggle: on the left edge of the sidebar (or content-area right edge when hidden)
        if self._sidebar.isVisible():
            pt2 = self._sidebar.mapTo(central, QPoint(0, 0))
            rx = pt2.x() - 10
        else:
            rx = central.width() - 20
        self._btn_right_toggle.move(rx, cy)
        self._btn_right_toggle.raise_()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self._reposition_toggles)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_btn_left_toggle"):
            self._reposition_toggles()

    # ── Workspace management ──────────────────────────────────────────────────

    def _save_current_as_workspace(self, name: str) -> None:
        logs = []
        for i in range(self._top_tabs.count()):
            spl = self._top_tabs.widget(i)
            if isinstance(spl, QSplitter):
                self._collect_ws_meta(spl, logs)
        if not logs:
            self._status.showMessage(i18n.tr("ws_no_logs"), 4000)
            return
        ws = {
            "id":         str(uuid.uuid4()),
            "name":       name,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "logs":       logs,
        }
        WorkspaceManager.add(ws)
        self._ws_panel.reload()
        self._status.showMessage(i18n.tr("ws_saved", name=name, n=len(logs)), 4000)

    def _open_workspace(self, ws: dict) -> None:
        # ── 1. Pre-filter valid entries ──────────────────────────────────────
        valid: list[dict] = []
        skipped = 0
        for entry in ws.get("logs", []):
            if entry["type"] == "cloudwatch" and entry.get("auth_mode", 0) == 1:
                skipped += 1
                continue
            if entry["type"] == "file" and not os.path.exists(entry.get("path", "")):
                self._status.showMessage(
                    i18n.tr("ws_file_missing", path=entry.get("path", "")), 3000
                )
                skipped += 1
                continue
            valid.append(entry)

        n = len(valid)
        if n == 0:
            self._status.showMessage(i18n.tr("ws_no_logs_to_open", name=ws["name"]), 3000)
            return

        # ── 2. Build viewers/workers for every entry ──────────────────────────
        items: list[tuple[str, LogViewer, object]] = []
        opened = 0
        for entry in valid:
            if entry["type"] == "cloudwatch":
                try:
                    profile = entry["profile"]
                    client = cloudwatch.make_client(
                        None if profile == "(default)" else profile,
                        entry["region"],
                    )
                    worker = TailWorker(
                        client, entry["group"], entry.get("stream", ""),
                        entry.get("filter", ""), entry.get("interval", 3),
                        entry.get("lookback", 3600),
                    )
                    viewer = LogViewer(source_type="cloudwatch")
                    stream_label = entry.get("stream", "") or "(all streams)"
                    viewer.set_title(f"{entry['group']}  ›  {stream_label}")
                    tab_title = (entry.get("stream", "") or entry["group"]).split("/")[-1]
                    viewer._ws_meta = {
                        "type":      "cloudwatch",
                        "auth_mode": entry.get("auth_mode", 0),
                        "profile":   profile,
                        "region":    entry["region"],
                        "group":     entry["group"],
                        "stream":    entry.get("stream", ""),
                        "filter":    entry.get("filter", ""),
                        "interval":  entry.get("interval", 3),
                        "lookback":  entry.get("lookback", 3600),
                    }
                    items.append((tab_title, viewer, worker))
                    opened += 1
                except Exception as exc:
                    self._status.showMessage(i18n.tr("ws_cw_error", error=exc), 5000)
                    skipped += 1
            elif entry["type"] == "file":
                worker = FileWorker(entry["path"], tail_lines=entry.get("tail_lines", 100))
                viewer = LogViewer(source_type="file")
                viewer.set_title(entry["path"])
                viewer._ws_meta = {
                    "type":       "file",
                    "path":       entry["path"],
                    "tail_lines": entry.get("tail_lines", 100),
                }
                items.append((os.path.basename(entry["path"]), viewer, worker))
                opened += 1
            elif entry["type"] == "ssh":
                if entry.get("auth_mode") == "password":
                    skipped += 1
                    continue
                try:
                    client = ssh_utils.make_client(
                        entry["host"], entry["user"],
                        entry.get("port", 22),
                        key_path=entry.get("key_path") or None,
                    )
                    worker = SSHWorker(client, entry["remote_path"], entry.get("tail_lines", 100))
                    viewer = LogViewer(source_type="ssh")
                    viewer.set_title(f"{entry['user']}@{entry['host']}:{entry['remote_path']}")
                    viewer._ws_meta = entry.copy()
                    tab_title = entry["remote_path"].rsplit("/", 1)[-1] or entry["host"]
                    items.append((tab_title, viewer, worker))
                    opened += 1
                except RuntimeError as e:
                    self._status.showMessage(f"SSH: {e}", 5000)
                    skipped += 1
            elif entry["type"] == "docker_container":
                worker = DockerContainerWorker(entry["container_id"], entry.get("tail_lines", 100))
                viewer = LogViewer(source_type="docker")
                viewer.set_title(f"docker  ›  {entry.get('container_name', entry['container_id'][:12])}")
                viewer._ws_meta = entry.copy()
                items.append((entry.get("container_name", entry["container_id"][:12]), viewer, worker))
                opened += 1
            elif entry["type"] == "docker_compose":
                worker = DockerComposeWorker(entry["project_name"], entry.get("tail_lines", 100))
                viewer = LogViewer(source_type="docker_compose")
                viewer.set_title(f"compose  ›  {entry['project_name']}")
                viewer._ws_meta = entry.copy()
                items.append((entry["project_name"], viewer, worker))
                opened += 1
            elif entry["type"] == "docker_exec_file":
                worker = DockerExecFileWorker(entry["container_id"], entry["remote_path"], entry.get("tail_lines", 100))
                viewer = LogViewer(source_type="docker_exec_file")
                viewer.set_title(f"{entry.get('container_name', '')}  ›  {entry['remote_path']}")
                viewer._ws_meta = entry.copy()
                tab_title = entry["remote_path"].rsplit("/", 1)[-1] or entry.get("container_name", "docker")
                items.append((tab_title, viewer, worker))
                opened += 1

        if not items:
            self._status.showMessage(i18n.tr("ws_no_logs_to_open", name=ws["name"]), 3000)
            return

        # ── 3. Build a grid layout inside one new tab ─────────────────────────
        cols = math.ceil(math.sqrt(len(items)))
        ws_spl = self._make_tab_splitter(Qt.Orientation.Horizontal)
        ws_tab_idx = self._top_tabs.addTab(ws_spl, ws["name"])
        self._top_tabs.setCurrentIndex(ws_tab_idx)

        for c in range(cols):
            col_items = [vw for idx, vw in enumerate(items) if idx % cols == c]
            if not col_items:
                break
            if len(col_items) == 1:
                _title, viewer, _worker = col_items[0]
                ws_spl.addWidget(viewer)
            else:
                vspl = self._make_tab_splitter(Qt.Orientation.Vertical)
                for _title, viewer, _worker in col_items:
                    vspl.addWidget(viewer)
                vspl.setSizes([1] * len(col_items))
                ws_spl.addWidget(vspl)

        ws_spl.setSizes([1] * ws_spl.count())

        # ── 4. Wire signals and start workers ────────────────────────────────
        for _title, viewer, worker in items:
            self._wire_viewer(viewer, worker)
            worker.start()

        self._set_active_viewer(self._first_viewer_in(ws_spl))

        msg = i18n.tr("ws_opened", name=ws["name"], opened=opened)
        if skipped:
            msg += i18n.tr("ws_skipped", n=skipped)
        self._status.showMessage(msg, 5000)

    def _on_delete_workspace(self, ws_id: str) -> None:
        WorkspaceManager.remove(ws_id)
        self._ws_panel.reload()

    def _on_rename_workspace(self, ws_id: str, name: str) -> None:
        WorkspaceManager.rename(ws_id, name)

    # ── Tab factories ─────────────────────────────────────────────────────────

    def open_cloudwatch_tab(self, cfg: dict, split: str = "tab"):
        worker = TailWorker(
            cfg["client"], cfg["group"], cfg["stream"],
            cfg["filter"], cfg["interval"], cfg["lookback"],
        )
        viewer = LogViewer(source_type="cloudwatch")
        stream_label = cfg["stream"] or "(all streams)"
        viewer.set_title(f"{cfg['group']}  ›  {stream_label}")
        tab_title = (cfg["stream"] or cfg["group"]).split("/")[-1]
        if cfg.get("auth_mode", 0) == 0:  # profile mode only
            viewer._ws_meta = {
                "type":      "cloudwatch",
                "auth_mode": cfg.get("auth_mode", 0),
                "profile":   cfg.get("profile", "(default)"),
                "region":    cfg.get("region", "us-east-1"),
                "group":     cfg["group"],
                "stream":    cfg.get("stream", ""),
                "filter":    cfg.get("filter", ""),
                "interval":  cfg.get("interval", 3),
                "lookback":  cfg.get("lookback", 3600),
            }
        self._add_tab(tab_title, viewer, worker, split=split)

    def open_file_tab(self, path: str, tail_lines: int = 100, split: str = "tab"):
        worker = FileWorker(path, tail_lines=tail_lines)
        viewer = LogViewer(source_type="file")
        viewer.set_title(path)
        viewer._ws_meta = {
            "type":       "file",
            "path":       path,
            "tail_lines": tail_lines,
        }
        self._add_tab(os.path.basename(path), viewer, worker, split=split)

    def open_stdin_tab(self):
        worker = StdinWorker()
        viewer = LogViewer(source_type="stdin")
        viewer.set_title("stdin — piped input")
        self._add_tab("stdin", viewer, worker, split="tab")

    def open_ssh_tab(self, cfg: dict, split: str = "tab"):
        client = cfg.pop("_client", None)
        if client is None:
            try:
                client = ssh_utils.make_client(
                    cfg["host"], cfg["user"], cfg.get("port", 22),
                    key_path=cfg.get("key_path") or None,
                    password=cfg.get("password") or None,
                )
            except RuntimeError as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "SSH Error", str(e))
                return
        worker = SSHWorker(client, cfg["remote_path"], cfg.get("tail_lines", 100))
        viewer = LogViewer(source_type="ssh")
        viewer.set_title(f"{cfg['user']}@{cfg['host']}:{cfg['remote_path']}")
        viewer._ws_meta = {k: v for k, v in cfg.items() if k != "password"}
        viewer._ws_meta["type"] = "ssh"
        tab_title = cfg["remote_path"].rsplit("/", 1)[-1] or cfg["host"]
        self._add_tab(tab_title, viewer, worker, split)

    def open_docker_tab(self, cfg: dict, split: str = "tab"):
        dtype = cfg["type"]
        if dtype == "docker_container":
            worker = DockerContainerWorker(cfg["container_id"], cfg.get("tail_lines", 100))
            viewer = LogViewer(source_type="docker")
            viewer.set_title(f"docker  ›  {cfg.get('container_name', cfg['container_id'][:12])}")
            tab_title = cfg.get("container_name", cfg["container_id"][:12])
        elif dtype == "docker_compose":
            worker = DockerComposeWorker(cfg["project_name"], cfg.get("tail_lines", 100))
            viewer = LogViewer(source_type="docker_compose")
            viewer.set_title(f"compose  ›  {cfg['project_name']}")
            tab_title = cfg["project_name"]
        else:  # docker_exec_file
            worker = DockerExecFileWorker(cfg["container_id"], cfg["remote_path"], cfg.get("tail_lines", 100))
            viewer = LogViewer(source_type="docker_exec_file")
            viewer.set_title(f"{cfg.get('container_name', '')}  ›  {cfg['remote_path']}")
            tab_title = cfg["remote_path"].rsplit("/", 1)[-1] or cfg.get("container_name", "docker")
        viewer._ws_meta = cfg.copy()
        self._add_tab(tab_title, viewer, worker, split)

    def open_vercel_tab(self, cfg: dict, split: str = "tab"):
        worker = VercelWorker(
            cfg["token"], cfg["project_id"], cfg["project_name"],
            cfg["deployment_id"], interval_s=cfg.get("interval_s", 3),
        )
        viewer = LogViewer(source_type="vercel")
        viewer.set_title(f"vercel  ›  {cfg['project_name']}")
        viewer._ws_meta = {k: v for k, v in cfg.items() if k != "token"}
        viewer._ws_meta["type"] = "vercel"
        self._add_tab(cfg["project_name"], viewer, worker, split)

    def open_gcp_tab(self, cfg: dict, split: str = "tab"):
        client = cfg.pop("_client", None)
        if client is None:
            try:
                client = gcp_utils.make_client(
                    cfg["project_id"],
                    cfg.get("key_path") or None,
                )
            except RuntimeError as e:
                QMessageBox.critical(self, "GCP Error", str(e))
                return
        worker = GCPWorker(
            client, cfg["project_id"],
            cfg.get("resource_type", "(all)"),
            cfg.get("severity", "ALL"),
            cfg.get("custom_filter", ""),
            lookback_hours=cfg.get("lookback_hours", 1),
            interval_s=cfg.get("interval_s", 5),
        )
        viewer = LogViewer(source_type="gcp")
        viewer.set_title(f"gcp  ›  {cfg['project_id']}")
        viewer._ws_meta = {k: v for k, v in cfg.items() if not k.startswith("_")}
        viewer._ws_meta["type"] = "gcp"
        self._add_tab(cfg["project_id"], viewer, worker, split)

    def open_azure_tab(self, cfg: dict, split: str = "tab"):
        logs_client = cfg.pop("_logs_client", None)
        if logs_client is None:
            try:
                cred = azure_utils.make_credential(
                    cfg["tenant_id"], cfg["client_id"], cfg["client_secret"]
                )
                logs_client = azure_utils.make_logs_client(cred)
            except RuntimeError as e:
                QMessageBox.critical(self, "Azure Error", str(e))
                return
        label = cfg.get("label", "azure")
        worker = AzureWorker(
            logs_client, cfg["workspace_id"], cfg["query"],
            label=label,
            timespan_hours=cfg.get("timespan_hours", 1),
            interval_s=cfg.get("interval_s", 10),
        )
        viewer = LogViewer(source_type="azure")
        viewer.set_title(f"azure  ›  {label}")
        viewer._ws_meta = {k: v for k, v in cfg.items() if not k.startswith("_")}
        viewer._ws_meta["type"] = "azure"
        self._add_tab(label, viewer, worker, split)

    def open_loki_tab(self, cfg: dict, split: str = "tab"):
        url   = cfg["url"]
        query = cfg["query"]
        auth  = cfg.get("auth_mode", 0)
        label = cfg.get("label", url.split("//", 1)[-1].split("/")[0])
        worker = LokiWorker(
            url, query,
            username=cfg.get("username", "") if auth == 1 else "",
            password=cfg.get("password", "") if auth == 1 else "",
            token=cfg.get("token", "")    if auth == 2 else "",
            lookback_hours=cfg.get("lookback_hours", 1),
            interval_s=cfg.get("interval_s", 5),
        )
        viewer = LogViewer(source_type="loki")
        viewer.set_title(f"loki  ›  {label}")
        viewer._ws_meta = {k: v for k, v in cfg.items()
                           if k not in ("password", "token")}
        viewer._ws_meta["type"] = "loki"
        self._add_tab(label, viewer, worker, split)

    def open_datadog_tab(self, cfg: dict, split: str = "tab"):
        label = cfg.get("label", cfg.get("base_url", "datadog"))
        worker = DatadogWorker(
            cfg["base_url"], cfg.get("query", "*"),
            cfg["api_key"], cfg["app_key"],
            lookback_hours=cfg.get("lookback_hours", 1),
            interval_s=cfg.get("interval_s", 10),
        )
        viewer = LogViewer(source_type="datadog")
        viewer.set_title(f"datadog  ›  {label}")
        viewer._ws_meta = {k: v for k, v in cfg.items()
                           if k not in ("api_key", "app_key")}
        viewer._ws_meta["type"] = "datadog"
        self._add_tab(label, viewer, worker, split)

    def open_elastic_tab(self, cfg: dict, split: str = "tab"):
        label = cfg.get("label", cfg.get("url", "elastic"))
        auth  = cfg.get("auth_mode", 0)
        worker = ElasticWorker(
            cfg["url"], cfg["index"], cfg.get("query", "*"),
            api_key=cfg.get("api_key", "")  if auth == 1 else "",
            username=cfg.get("username", "") if auth == 2 else "",
            password=cfg.get("password", "") if auth == 2 else "",
            ts_field=cfg.get("ts_field", "@timestamp"),
            lookback_hours=cfg.get("lookback_hours", 1),
            interval_s=cfg.get("interval_s", 10),
        )
        viewer = LogViewer(source_type="elastic")
        viewer.set_title(f"elastic  ›  {label}")
        viewer._ws_meta = {k: v for k, v in cfg.items()
                           if k not in ("api_key", "password")}
        viewer._ws_meta["type"] = "elastic"
        self._add_tab(label, viewer, worker, split)

    def open_railway_tab(self, cfg: dict, split: str = "tab"):
        label = cfg.get("label", cfg.get("service_name", "railway"))
        worker = RailwayWorker(
            cfg["token"], cfg["project_name"], cfg["service_name"],
            cfg["service_id"], interval_s=cfg.get("interval_s", 10),
        )
        viewer = LogViewer(source_type="railway")
        viewer.set_title(f"railway  ›  {label}")
        viewer._ws_meta = {k: v for k, v in cfg.items() if k != "token"}
        viewer._ws_meta["type"] = "railway"
        self._add_tab(label, viewer, worker, split)

    def open_flyio_tab(self, cfg: dict, split: str = "tab"):
        label = cfg.get("label", cfg.get("app_name", "fly.io"))
        worker = FlyioWorker(
            cfg["token"], cfg["app_name"],
            interval_s=cfg.get("interval_s", 5),
        )
        viewer = LogViewer(source_type="flyio")
        viewer.set_title(f"fly.io  ›  {label}")
        viewer._ws_meta = {k: v for k, v in cfg.items() if k != "token"}
        viewer._ws_meta["type"] = "flyio"
        self._add_tab(label, viewer, worker, split)

    def open_kubernetes_tab(self, cfg: dict, split: str = "tab"):
        label = cfg.get("label", cfg.get("pod", "k8s"))
        worker = KubernetesWorker(
            cfg["pod"], cfg["namespace"],
            context=cfg.get("context", ""),
            container=cfg.get("container", ""),
        )
        viewer = LogViewer(source_type="kubernetes")
        viewer.set_title(f"k8s  ›  {label}")
        viewer._ws_meta = {k: v for k, v in cfg.items()}
        viewer._ws_meta["type"] = "kubernetes"
        self._add_tab(label, viewer, worker, split)

    # ── Internal tab management ───────────────────────────────────────────────

    def _wire_viewer(self, viewer: LogViewer, worker) -> None:
        worker.new_lines.connect(viewer.append_events)
        worker.status.connect(self._status.showMessage)
        worker.error.connect(lambda msg, v=viewer: self._on_error(msg, v))
        if hasattr(worker, "history_done"):
            worker.history_done.connect(
                lambda n: self._status.showMessage(i18n.tr("history_loaded", n=n))
            )
        viewer.stop_requested.connect(lambda v=viewer: self._stop_viewer(v))
        viewer.pane_close_requested.connect(lambda v=viewer: self._close_pane(v))
        viewer.pane_activated.connect(lambda v=viewer: self._set_active_viewer(v))
        viewer.stop_btn.setEnabled(True)
        self._workers[id(viewer)] = worker

    def _add_tab(self, title: str, viewer: LogViewer, worker, split: str = "tab"):
        self._wire_viewer(viewer, worker)

        if split == "vertical":
            self._add_viewer_to_current_tab(viewer, Qt.Orientation.Horizontal, title)
        elif split == "horizontal":
            self._add_viewer_to_current_tab(viewer, Qt.Orientation.Vertical, title)
        else:
            spl = self._make_tab_splitter()
            spl.addWidget(viewer)
            idx = self._top_tabs.addTab(spl, title)
            self._top_tabs.setCurrentIndex(idx)

        self._set_active_viewer(viewer)
        worker.start()

    def _action_close_all_logs(self):
        while self._top_tabs.count() > 0:
            self._close_tab_at(0)

    def _stop_viewer(self, viewer: LogViewer):
        worker = self._workers.pop(id(viewer), None)
        if worker and worker.isRunning():
            worker.stop()
            worker.wait(3000)
        if viewer:
            viewer.stop_btn.setEnabled(False)

    def _on_error(self, msg: str, viewer: LogViewer):
        self._stop_viewer(viewer)
        self._status.showMessage(i18n.tr("err_prefix", msg=msg))
        QMessageBox.critical(self, i18n.tr("err_worker"), msg)

    def closeEvent(self, event):  # noqa: N802
        for worker in list(self._workers.values()):
            if worker.isRunning():
                worker.stop()
                worker.wait(2000)
        event.accept()


# ── Tiny helpers ──────────────────────────────────────────────────────────────

def _field_label(text: str) -> QLabel:
    """Small field caption label."""
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {C_MUTED}; font-size: 11px; background: transparent; border: none;"
    )
    return lbl
