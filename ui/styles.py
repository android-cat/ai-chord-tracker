"""Modern white theme stylesheet for the application."""

# Color palette
COLORS = {
    'bg': '#FFFFFF',
    'bg_secondary': '#F8F9FA',
    'bg_tertiary': '#F0F2F5',
    'border': '#E4E7EB',
    'border_hover': '#CBD2D9',
    'text': '#1A1A2E',
    'text_secondary': '#6B7280',
    'accent': '#3B82F6',
    'accent_hover': '#2563EB',
    'accent_light': '#EFF6FF',
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'playhead': '#EF4444',
}

# Chord colors by root note (pastel)
CHORD_COLORS = {
    'C': '#DBEAFE',
    'D': '#D1FAE5',
    'E': '#FEF3C7',
    'F': '#FEE2E2',
    'G': '#E9D5FF',
    'A': '#CCFBF1',
    'B': '#FFE4E6',
    'Db': '#C7D2FE',
    'Eb': '#A7F3D0',
    'Gb': '#FDE68A',
    'Ab': '#DDD6FE',
    'Bb': '#FBCFE8',
    'N.C.': '#F3F4F6',
}

CHORD_BORDER_COLORS = {
    'C': '#93C5FD',
    'D': '#6EE7B7',
    'E': '#FCD34D',
    'F': '#FCA5A5',
    'G': '#C4B5FD',
    'A': '#5EEAD4',
    'B': '#FDA4AF',
    'Db': '#A5B4FC',
    'Eb': '#6EE7B7',
    'Gb': '#FCD34D',
    'Ab': '#C4B5FD',
    'Bb': '#F9A8D4',
    'N.C.': '#D1D5DB',
}

STYLESHEET = """
/* ========== Global ========== */
QWidget {
    background-color: #FFFFFF;
    color: #1A1A2E;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
}

/* ========== Main Window ========== */
QMainWindow {
    background-color: #FFFFFF;
}

/* ========== Buttons ========== */
QPushButton {
    background-color: #F8F9FA;
    border: 1px solid #E4E7EB;
    border-radius: 8px;
    padding: 8px 20px;
    font-size: 13px;
    font-weight: 500;
    color: #1A1A2E;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #EFF6FF;
    border-color: #3B82F6;
    color: #3B82F6;
}

QPushButton:pressed {
    background-color: #DBEAFE;
}

QPushButton:disabled {
    background-color: #F3F4F6;
    color: #9CA3AF;
    border-color: #E5E7EB;
}

QPushButton#primaryButton {
    background-color: #3B82F6;
    color: white;
    border: none;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #2563EB;
}

QPushButton#primaryButton:pressed {
    background-color: #1D4ED8;
}

/* ========== Labels ========== */
QLabel {
    background-color: transparent;
    color: #1A1A2E;
}

QLabel#titleLabel {
    font-size: 22px;
    font-weight: 700;
    color: #1A1A2E;
}

QLabel#subtitleLabel {
    font-size: 13px;
    color: #6B7280;
    font-weight: 400;
}

QLabel#timeLabel {
    font-size: 28px;
    font-weight: 300;
    font-family: 'Consolas', 'Courier New', monospace;
    color: #1A1A2E;
}

QLabel#chordLabel {
    font-size: 36px;
    font-weight: 700;
    color: #3B82F6;
}

QLabel#sectionLabel {
    font-size: 11px;
    font-weight: 600;
    color: #9CA3AF;
    letter-spacing: 1px;
}

/* ========== Slider ========== */
QSlider::groove:horizontal {
    border: none;
    height: 4px;
    background: #E5E7EB;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #3B82F6;
    border: 2px solid white;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 8px;
}

QSlider::handle:horizontal:hover {
    background: #2563EB;
    width: 16px;
    height: 16px;
    margin: -7px 0;
    border-radius: 9px;
}

QSlider::sub-page:horizontal {
    background: #3B82F6;
    border-radius: 2px;
}

/* ========== ScrollBar ========== */
QScrollBar:horizontal {
    height: 8px;
    background: transparent;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 4px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}

QScrollBar:vertical {
    width: 8px;
    background: transparent;
}

QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

/* ========== Progress Bar ========== */
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #F3F4F6;
    text-align: center;
    font-size: 11px;
    color: #6B7280;
    min-height: 12px;
    max-height: 12px;
}

QProgressBar::chunk {
    border-radius: 6px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3B82F6, stop:1 #60A5FA);
}

/* ========== Status Bar ========== */
QStatusBar {
    background-color: #F8F9FA;
    border-top: 1px solid #E4E7EB;
    color: #6B7280;
    font-size: 12px;
}

/* ========== Frame ========== */
QFrame#card {
    background-color: #FFFFFF;
    border: 1px solid #E4E7EB;
    border-radius: 12px;
}

QFrame#separator {
    background-color: #E4E7EB;
    max-height: 1px;
}

/* ========== ToolTip ========== */
QToolTip {
    background-color: #1F2937;
    color: white;
    border: none;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}
"""
