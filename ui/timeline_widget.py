"""Chord timeline display widget using QPainter."""
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush,
    QLinearGradient, QPolygonF
)

from ui.styles import CHORD_COLORS, CHORD_BORDER_COLORS
from audio_processor import get_chord_root


class TimelineWidget(QWidget):
    """Custom widget displaying chord blocks on a timeline."""

    position_clicked = Signal(float)  # time in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chords = []          # List of [start, end, chord_name]
        self.duration = 0.0
        self._playhead_time = 0.0
        self.setMinimumHeight(80)
        self.setCursor(Qt.PointingHandCursor)

    def set_chords(self, chords):
        """Set chord timeline data."""
        self.chords = chords
        if chords:
            self.duration = max(end for _, end, _ in chords)
        else:
            self.duration = 0.0
        self.update()

    def set_playhead(self, time_sec):
        """Update playhead position."""
        self._playhead_time = time_sec
        self.update()

    def paintEvent(self, event):
        """Draw the timeline."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor('#FAFBFC'))

        # Border
        painter.setPen(QPen(QColor('#E4E7EB'), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        if not self.chords or self.duration <= 0:
            # Draw placeholder
            painter.setPen(QColor('#D1D5DB'))
            painter.setFont(QFont('Segoe UI', 11))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter,
                             "コード解析結果がここに表示されます")
            return

        margin_top = 10
        margin_bottom = 22
        block_height = h - margin_top - margin_bottom

        # Draw chord blocks
        for start, end, chord in self.chords:
            x1 = (start / self.duration) * w
            x2 = (end / self.duration) * w
            block_w = max(x2 - x1, 2)

            root = get_chord_root(chord) or 'N.C.'
            bg_color = CHORD_COLORS.get(root, '#F3F4F6')
            border_color = CHORD_BORDER_COLORS.get(root, '#D1D5DB')

            # Block background with subtle gradient
            rect = QRectF(x1, margin_top, block_w, block_height)
            gradient = QLinearGradient(x1, margin_top, x1, margin_top + block_height)
            gradient.setColorAt(0.0, QColor(bg_color))
            bg_darker = QColor(bg_color)
            bg_darker.setAlpha(200)
            gradient.setColorAt(1.0, bg_darker)

            painter.setPen(QPen(QColor(border_color), 1))
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(rect, 4, 4)

            # Chord name (only if block is wide enough)
            if block_w > 28:
                painter.setPen(QColor('#374151'))
                font_size = 10 if block_w > 60 else 8 if block_w > 40 else 7
                font = QFont('Segoe UI', font_size, QFont.Bold)
                painter.setFont(font)
                text_rect = QRectF(x1 + 3, margin_top, block_w - 6, block_height)
                painter.drawText(text_rect, Qt.AlignCenter, chord)

        # Time markers
        painter.setPen(QColor('#9CA3AF'))
        painter.setFont(QFont('Segoe UI', 7))
        interval = self._get_time_interval()
        t = 0.0
        while t <= self.duration:
            x = (t / self.duration) * w
            painter.setPen(QPen(QColor('#D1D5DB'), 1))
            painter.drawLine(int(x), h - margin_bottom, int(x), h - margin_bottom + 3)
            painter.setPen(QColor('#9CA3AF'))
            mins = int(t // 60)
            secs = t % 60
            painter.drawText(int(x) + 2, h - 6, f"{mins}:{secs:04.1f}")
            t += interval

        # Playhead
        if self._playhead_time >= 0 and self.duration > 0:
            px = (self._playhead_time / self.duration) * w

            # Playhead shadow
            painter.setPen(QPen(QColor(239, 68, 68, 40), 6))
            painter.drawLine(int(px), 0, int(px), h)

            # Playhead line
            painter.setPen(QPen(QColor('#EF4444'), 2))
            painter.drawLine(int(px), 0, int(px), h)

            # Playhead handle (circle at top)
            painter.setBrush(QColor('#EF4444'))
            painter.setPen(QPen(QColor('#FFFFFF'), 2))
            painter.drawEllipse(QPointF(px, 6), 5, 5)

    def _get_time_interval(self):
        """Calculate appropriate time interval for markers."""
        if self.duration <= 15:
            return 2
        elif self.duration <= 30:
            return 5
        elif self.duration <= 120:
            return 10
        elif self.duration <= 300:
            return 30
        else:
            return 60

    def mousePressEvent(self, event):
        """Handle click to seek."""
        if self.duration > 0 and event.button() == Qt.LeftButton:
            time_sec = (event.position().x() / self.width()) * self.duration
            time_sec = max(0.0, min(time_sec, self.duration))
            self.position_clicked.emit(time_sec)
