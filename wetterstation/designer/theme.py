"""Quiet desktop chrome and vector toolbar symbols; no display-style changes."""
from PySide6.QtCore import Qt,QRectF
from pathlib import Path
from PySide6.QtGui import QIcon,QPixmap,QPainter,QPen,QColor,QPainterPath,QTransform

LIGHT='''
QWidget { background:#fafbfc; color:#25272b; font-size:13px; }
QMainWindow { background:#f4f5f7; }
QWidget#pagesPanel, QWidget#inspectorPanel { background:#fafbfc; }
QToolBar { background:#fafbfc; border:0; border-bottom:1px solid #e5e7eb; padding:9px; spacing:8px; }
QPushButton,QToolButton { background:#eceef2; border:0; border-radius:8px; padding:7px 10px; }
QPushButton:hover,QToolButton:hover { background:#e0eafa; }
QPushButton:pressed,QToolButton:pressed,QToolButton:checked { background:#dceaff; color:#0060d6; }
QPushButton:disabled,QToolButton:disabled { color:#a2a7b0; background:#f0f1f4; }
QToolButton[primary="true"] { background:#007aff; color:white; padding:8px 16px; }
QToolButton#inspectorSectionHeader { background:transparent; color:#566176; }
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox { background:#eef0f4; border:1px solid transparent; border-radius:7px; padding:6px 8px; selection-background-color:#007aff; }
QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus { border-color:#70adff; }
QComboBox::drop-down { border:0; width:22px; }
QAbstractSpinBox::up-button,QAbstractSpinBox::down-button { border:0; background:transparent; width:17px; }
QAbstractSpinBox::up-button:hover,QAbstractSpinBox::down-button:hover { background:#dceaff; }
QListWidget { background:transparent; border:0; outline:0; padding:4px; }
QListWidget::item { padding:8px; margin:3px; border-radius:10px; }
QListWidget::item:selected { background:#e1edff; color:#005bc9; }
QTabBar { background:#e9ebf0; border-radius:10px; }
QTabBar::tab { background:transparent; color:#69717d; border:0; border-radius:8px; margin:3px; padding:9px 16px; }
QTabBar::tab:selected { background:white; color:#15181e; }
QScrollArea { border:0; background:transparent; }
QScrollBar:vertical { background:transparent; width:8px; margin:2px; }
QScrollBar::handle:vertical { background:#c5cad3; min-height:32px; border-radius:4px; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:transparent; }
QStatusBar { background:#fafbfc; color:#69717d; border-top:1px solid #e5e7eb; }
QSplitter::handle { background:#e4e7ec; width:1px; }
QSlider::groove:horizontal { height:3px; background:#d5dbe4; border-radius:1px; }
QSlider::handle:horizontal { background:#007aff; width:12px; margin:-5px 0; border-radius:6px; }
QCheckBox { spacing:7px; }
QCheckBox::indicator { width:15px; height:15px; border:1px solid #bcc5d2; border-radius:4px; background:white; }
QCheckBox::indicator:checked { border-color:#007aff; background:#007aff; }
QMenu { background:#fafbfc; border:1px solid #e0e5ec; padding:5px; }
QMenu::item { padding:7px 20px; border-radius:5px; }
QMenu::item:selected { background:#e1edff; }
'''
LIGHT+='''
QComboBox::down-arrow { image:url("$icons/chevron.svg"); width:11px; height:8px; }
QCheckBox::indicator:checked { image:url("$icons/check.svg"); }
'''
LIGHT=LIGHT.replace('$icons',(Path(__file__).parent/'icons').as_posix())
DARK='''
QWidget { background:#272b33; color:#e8ebf0; }
QMainWindow { background:#1f2228; }
QWidget#pagesPanel,QWidget#inspectorPanel,QToolBar,QStatusBar,QMenu { background:#272b33; border-color:#343a46; }
QPushButton,QToolButton,QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox { background:#343a46; color:#edf0f5; }
QPushButton:hover,QToolButton:hover,QToolButton:checked { background:#3b506b; }
QPushButton:disabled,QToolButton:disabled { background:#292e38; color:#758093; }
QTabBar { background:#1e232b; }
QTabBar::tab { color:#a4afc0; }
QTabBar::tab:selected { background:#414a59; color:white; }
QMenuBar,QMenuBar::item { background:#272b33; color:#e8ebf0; }
QMenuBar::item:selected { background:#3b506b; }
QToolButton#inspectorSectionHeader { background:transparent; color:#b4bfd1; }
QListWidget::item:selected,QMenu::item:selected { background:#284b75; color:#e3efff; }
QScrollBar::handle:vertical { background:#586273; }
QSplitter::handle { background:#343a46; }
QCheckBox::indicator { background:#343a46; border-color:#637087; }
QCheckBox::indicator:checked { background:#007aff; border-color:#007aff; }
'''


def icon(name):
    pix=QPixmap(40,40);pix.fill(Qt.GlobalColor.transparent);p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.scale(2,2)
    p.setPen(QPen(QColor('#788698'),1.6,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
    if name in ('left','center','right'):
        for y,length in ((5,14),(10,9),(15,12)):
            x=3 if name=='left' else (20-length)/2 if name=='center' else 17-length;p.drawLine(int(x),y,int(x+length),y)
    elif name in ('top','middle','bottom'):
        for x,height in ((4,12),(10,8),(16,10)):
            y=3 if name=='top' else (20-height)/2 if name=='middle' else 17-height;p.drawLine(x,int(y),x,int(y+height))
    elif name in ('undo','redo'):
        path=QPainterPath();path.moveTo(4,7);path.cubicTo(19,3,19,17,7,16);p.drawPath(path);p.drawLine(4,7,8,3);p.drawLine(4,7,9,10)
        if name=='redo':p.end();return QIcon(pix.transformed(QTransform().scale(-1,1)))
    elif name in ('distribute_x','distribute_y'):
        if name.endswith('y'):p.translate(20,0);p.rotate(90)
        for x in (3,9,15):p.drawRect(QRectF(x,5,2,10))
    elif name in ('add','remove'):
        p.drawLine(4,10,16,10)
        if name=='add':p.drawLine(10,4,10,16)
    else:
        if name=='down':p.translate(20,20);p.rotate(180)
        p.drawLine(5,12,10,7);p.drawLine(10,7,15,12)
    p.end();return QIcon(pix)
