"""Colours and styling. Bright and friendly, always light (ignores dark mode)."""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

BG = "#fff8e7"
INK = "#2b2b2b"
MUTED = "#7a7062"
SKIN = "#f6e6d2"
GOOD = "#2e9e48"
FIXED = "#e08a00"
BAD = "#e74c3c"

# Same colour for matching fingers on both hands.
FINGER_COLORS = {
    "5": "#f8a5c2",  # pinky
    "4": "#ffcf7a",  # ring
    "3": "#9be7a0",  # middle
    "2": "#8ec5ff",  # pointer
    "T": "#cdb4ff",  # thumb
}

AVATAR_COLORS = ("#ff8a80", "#ffb74d", "#fff176", "#81c784",
                 "#64b5f6", "#ba68c8", "#f06292", "#4db6ac")


def finger_color(finger: str) -> QColor:
    return QColor(FINGER_COLORS[finger[1]])


def mix(a: QColor, b: QColor, t: float) -> QColor:
    """Blend a toward b by t (0..1)."""
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
    )


STYLESHEET = f"""
QPushButton {{
    background: #ffd166; color: {INK}; border: none; border-radius: 14px;
    padding: 10px 22px; font-size: 18px; font-weight: bold;
}}
QPushButton:hover {{ background: #ffc233; }}
QPushButton:pressed {{ background: #f4b400; }}
QPushButton:disabled {{ background: #ebe4d6; color: #aaa294; }}
QPushButton[role="secondary"] {{ background: #efe6d2; font-size: 16px; padding: 8px 16px; }}
QPushButton[role="secondary"]:hover {{ background: #e5d9bf; }}

QPushButton[state="done"] {{ background: #b9e8b0; }}
QPushButton[state="done"]:hover {{ background: #a3df98; }}
QPushButton[state="next"] {{ background: #ffd166; border: 3px solid {INK}; }}
QPushButton[state="open"] {{ background: #ffe7a8; }}
QPushButton[state="locked"] {{ background: #ebe4d6; color: #aaa294; }}

QLabel#Title {{ font-size: 34px; font-weight: bold; }}
QLabel#Heading {{ font-size: 24px; font-weight: bold; }}
QLabel#Subtitle {{ font-size: 17px; color: {MUTED}; }}
QLabel#Instruction {{ font-size: 20px; }}
QLabel#Hint {{ font-size: 20px; font-weight: bold; color: {INK}; }}
QLabel#Hint[error="true"] {{ color: {BAD}; }}
QLabel#Stat {{ font-size: 17px; color: {MUTED}; }}

QProgressBar {{ border: none; background: #efe6d2; border-radius: 8px; max-height: 16px; }}
QProgressBar::chunk {{ background: #81c784; border-radius: 8px; }}

QLineEdit {{
    font-size: 22px; padding: 8px 12px; border: 2px solid #e0d5bd;
    border-radius: 10px; background: white;
}}
QLineEdit:focus {{ border-color: #64b5f6; }}
QScrollArea {{ border: none; background: transparent; }}
QComboBox {{
    font-size: 17px; padding: 8px 12px; border: 2px solid #e0d5bd;
    border-radius: 10px; background: white;
}}
QCheckBox {{ font-size: 17px; spacing: 10px; }}
QCheckBox::indicator {{ width: 22px; height: 22px; }}
QFrame#GamePanel {{ background: white; border: 3px solid #e8dcc2; border-radius: 22px; }}
QFrame#Panel {{ background: #fff1cc; border-radius: 16px; }}
QFrame#Tile {{ background: white; border: 2px solid #e8dcc2; border-radius: 16px; }}
QLabel#TileValue {{ font-size: 26px; font-weight: bold; }}
QPushButton[role="segment"] {{ background: #efe6d2; font-size: 15px; padding: 6px 14px; }}
QPushButton[role="segment"]:checked {{ background: #ffd166; }}
QTableWidget {{
    background: white; border: 2px solid #e8dcc2; border-radius: 12px;
    font-size: 15px; color: {INK};
}}
QTableWidget::item {{ padding: 4px 8px; border-bottom: 1px solid #f3ecdf; }}
QHeaderView::section {{
    background: white; color: {MUTED}; border: none; border-bottom: 2px solid #e8dcc2;
    padding: 6px 8px; font-size: 14px; font-weight: bold;
}}
QLabel#Chip {{
    font-size: 20px; font-weight: bold; border-radius: 10px; padding: 4px 12px;
    border: 2px solid {INK};
}}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle(QStyleFactory.create("Fusion"))
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(INK))
    pal.setColor(QPalette.ColorRole.Base, QColor("white"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(BG))
    pal.setColor(QPalette.ColorRole.Text, QColor(INK))
    pal.setColor(QPalette.ColorRole.Button, QColor("#ffd166"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(INK))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#64b5f6"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("white"))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(INK))
    app.setPalette(pal)
    font = QFont(app.font())
    font.setPointSize(13)
    app.setFont(font)
    app.setStyleSheet(STYLESHEET)


def repolish(widget) -> None:
    """Re-apply the stylesheet after changing a dynamic property."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
