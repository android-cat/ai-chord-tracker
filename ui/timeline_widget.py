"""Chord timeline display widget using QPainter with zoom & scroll."""
import numpy as np
from PySide6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QColor, QFont, QPen, QBrush,
    QLinearGradient, QPolygonF
)

from ui.styles import CHORD_COLORS, CHORD_BORDER_COLORS
from audio_processor import get_chord_root


class TimelineCanvas(QWidget):
    """Inner canvas that draws the timeline at the current zoom level."""

    position_clicked = Signal(float)  # time in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.chords = []
        self.keys = []
        self.duration = 0.0
        self._playhead_time = 0.0
        self._zoom = 1.0
        self.setMinimumHeight(100)
        self.setCursor(Qt.PointingHandCursor)

    def set_chords(self, chords):
        self.chords = chords
        if chords:
            self.duration = max(end for _, end, _ in chords)
        elif self.keys:
            self.duration = max(end for _, end, _ in self.keys)
        else:
            self.duration = 0.0
        self._update_size()
        self.update()

    def set_keys(self, keys):
        self.keys = keys
        if keys and not self.chords:
            self.duration = max(end for _, end, _ in keys)
        self.update()

    def set_playhead(self, time_sec):
        self._playhead_time = time_sec
        self.update()

    def set_zoom(self, zoom):
        self._zoom = max(1.0, min(zoom, 20.0))
        self._update_size()
        self.update()

    def get_zoom(self):
        return self._zoom

    def _update_size(self):
        """Resize canvas width based on zoom level."""
        parent = self.parent()
        if parent:
            base_w = parent.width() - 2  # account for frame border
        else:
            base_w = 800
        new_w = max(base_w, int(base_w * self._zoom))
        self.setFixedWidth(new_w)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor('#FAFBFC'))

        if not self.chords or self.duration <= 0:
            painter.setPen(QColor('#D1D5DB'))
            painter.setFont(QFont('Segoe UI', 11))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter,
                             "コード解析結果がここに表示されます")
            return

        key_lane_h = 18
        margin_top = 4
        margin_bottom = 22
        chord_top = margin_top + key_lane_h + 2
        block_height = h - chord_top - margin_bottom

        # Draw key lane
        if self.keys:
            key_colors = {
                'C': '#EDE9FE', 'Db': '#E0E7FF', 'D': '#DBEAFE',
                'Eb': '#D1FAE5', 'E': '#FEF3C7', 'F': '#FEE2E2',
                'Gb': '#FCE7F3', 'G': '#E9D5FF', 'Ab': '#DDD6FE',
                'A': '#CCFBF1', 'Bb': '#FBCFE8', 'B': '#FFE4E6',
                'Am': '#EDE9FE', 'Bbm': '#E0E7FF', 'Bm': '#DBEAFE',
                'Cm': '#D1FAE5', 'C#m': '#FEF3C7', 'Dm': '#FEE2E2',
                'Ebm': '#FCE7F3', 'Em': '#E9D5FF', 'F#m': '#DDD6FE',
                'Fm': '#CCFBF1', 'Gm': '#FBCFE8', 'G#m': '#FFE4E6',
                'N': '#F3F4F6',
            }
            key_border_colors = {
                'C': '#C4B5FD', 'Db': '#A5B4FC', 'D': '#93C5FD',
                'Eb': '#6EE7B7', 'E': '#FCD34D', 'F': '#FCA5A5',
                'Gb': '#F9A8D4', 'G': '#C4B5FD', 'Ab': '#A78BFA',
                'A': '#5EEAD4', 'Bb': '#F9A8D4', 'B': '#FDA4AF',
                'Am': '#C4B5FD', 'Bbm': '#A5B4FC', 'Bm': '#93C5FD',
                'Cm': '#6EE7B7', 'C#m': '#FCD34D', 'Dm': '#FCA5A5',
                'Ebm': '#F9A8D4', 'Em': '#C4B5FD', 'F#m': '#A78BFA',
                'Fm': '#5EEAD4', 'Gm': '#F9A8D4', 'G#m': '#FDA4AF',
                'N': '#D1D5DB',
            }
            for start, end, key in self.keys:
                if key == 'N':
                    continue
                x1 = (start / self.duration) * w
                x2 = (end / self.duration) * w
                kw = max(x2 - x1, 2)

                bg = key_colors.get(key, '#F3F4F6')
                border = key_border_colors.get(key, '#D1D5DB')

                rect = QRectF(x1, margin_top, kw, key_lane_h)
                painter.setPen(QPen(QColor(border), 1))
                painter.setBrush(QBrush(QColor(bg)))
                painter.drawRoundedRect(rect, 3, 3)

                if kw > 24:
                    painter.setPen(QColor('#6B21A8'))
                    font_size = 8 if kw > 50 else 7
                    painter.setFont(QFont('Segoe UI', font_size, QFont.Bold))
                    text_rect = QRectF(x1 + 2, margin_top, kw - 4, key_lane_h)
                    painter.drawText(text_rect, Qt.AlignCenter, key)

        # Draw chord blocks
        for start, end, chord in self.chords:
            x1 = (start / self.duration) * w
            x2 = (end / self.duration) * w
            block_w = max(x2 - x1, 2)

            root = get_chord_root(chord) or 'N.C.'
            bg_color = CHORD_COLORS.get(root, '#F3F4F6')
            border_color = CHORD_BORDER_COLORS.get(root, '#D1D5DB')

            rect = QRectF(x1, chord_top, block_w, block_height)
            gradient = QLinearGradient(x1, chord_top, x1, chord_top + block_height)
            gradient.setColorAt(0.0, QColor(bg_color))
            bg_darker = QColor(bg_color)
            bg_darker.setAlpha(200)
            gradient.setColorAt(1.0, bg_darker)

            painter.setPen(QPen(QColor(border_color), 1))
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(rect, 4, 4)

            if block_w > 28:
                painter.setPen(QColor('#374151'))
                font_size = 10 if block_w > 60 else 8 if block_w > 40 else 7
                font = QFont('Segoe UI', font_size, QFont.Bold)
                painter.setFont(font)
                text_rect = QRectF(x1 + 3, chord_top, block_w - 6, block_height)
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

            painter.setPen(QPen(QColor(239, 68, 68, 40), 6))
            painter.drawLine(int(px), 0, int(px), h)

            painter.setPen(QPen(QColor('#EF4444'), 2))
            painter.drawLine(int(px), 0, int(px), h)

            painter.setBrush(QColor('#EF4444'))
            painter.setPen(QPen(QColor('#FFFFFF'), 2))
            painter.drawEllipse(QPointF(px, 6), 5, 5)

    def _get_time_interval(self):
        visible_duration = self.duration / self._zoom
        if visible_duration <= 5:
            return 1
        elif visible_duration <= 15:
            return 2
        elif visible_duration <= 30:
            return 5
        elif visible_duration <= 120:
            return 10
        elif visible_duration <= 300:
            return 30
        else:
            return 60

    def mousePressEvent(self, event):
        if self.duration > 0 and event.button() == Qt.LeftButton:
            time_sec = (event.position().x() / self.width()) * self.duration
            time_sec = max(0.0, min(time_sec, self.duration))
            self.position_clicked.emit(time_sec)


class TimelineWidget(QScrollArea):
    """Scrollable timeline with zoom support."""

    position_clicked = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.NoFrame)

        self._canvas = TimelineCanvas()
        self.setWidget(self._canvas)

        self._canvas.position_clicked.connect(self.position_clicked)

    def set_chords(self, chords):
        self._canvas.set_chords(chords)

    def set_keys(self, keys):
        self._canvas.set_keys(keys)

    def set_playhead(self, time_sec):
        self._canvas.set_playhead(time_sec)
        self._auto_scroll(time_sec)

    def zoom_in(self):
        self._canvas.set_zoom(self._canvas.get_zoom() * 1.5)

    def zoom_out(self):
        self._canvas.set_zoom(self._canvas.get_zoom() / 1.5)

    def get_zoom(self):
        return self._canvas.get_zoom()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._canvas._update_size()

    def _auto_scroll(self, time_sec):
        """Keep playhead visible during playback."""
        if self._canvas.duration <= 0:
            return
        canvas_w = self._canvas.width()
        px = (time_sec / self._canvas.duration) * canvas_w
        viewport_w = self.viewport().width()
        scroll_bar = self.horizontalScrollBar()

        # Scroll if playhead is near edges
        visible_left = scroll_bar.value()
        visible_right = visible_left + viewport_w
        margin = viewport_w * 0.15

        if px < visible_left + margin or px > visible_right - margin:
            scroll_bar.setValue(int(px - viewport_w / 2))
