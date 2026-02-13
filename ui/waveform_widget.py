"""Waveform display widget using QPainter."""
import numpy as np
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QLinearGradient, QPolygonF


class WaveformWidget(QWidget):
    """Widget displaying audio waveform with playhead."""

    position_clicked = Signal(float)  # time in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_data = None
        self._display_data = None
        self.sr = 22050
        self.duration = 0.0
        self._playhead_time = 0.0
        self._peaks_pos = None
        self._peaks_neg = None
        self.setMinimumHeight(120)
        self.setCursor(Qt.PointingHandCursor)

    def set_audio(self, audio_data, sr):
        """Set audio data and precompute peaks for display."""
        # Convert stereo to mono for waveform display
        if audio_data.ndim == 2:
            self._display_data = np.mean(audio_data, axis=1)
        else:
            self._display_data = audio_data
        self.audio_data = audio_data
        self.sr = sr
        self.duration = len(self._display_data) / sr
        self._compute_peaks()
        self.update()

    def _compute_peaks(self):
        """Precompute positive and negative peaks for efficient rendering."""
        if self._display_data is None:
            return

        data_1d = self._display_data
        num_bins = min(2000, len(data_1d))
        samples_per_bin = max(1, len(data_1d) // num_bins)
        n = samples_per_bin * num_bins
        data = data_1d[:n].reshape(num_bins, samples_per_bin)
        self._peaks_pos = np.max(data, axis=1)
        self._peaks_neg = np.min(data, axis=1)

    def set_playhead(self, time_sec):
        """Update playhead position."""
        self._playhead_time = time_sec
        self.update()

    def paintEvent(self, event):
        """Draw the waveform."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin_bottom = 20

        # Background
        painter.fillRect(0, 0, w, h, QColor('#FAFBFC'))

        # Border
        painter.setPen(QPen(QColor('#E4E7EB'), 1))
        painter.drawRoundedRect(0, 0, w - 1, h - 1, 8, 8)

        if self._peaks_pos is None:
            # Placeholder text
            painter.setPen(QColor('#D1D5DB'))
            painter.setFont(QFont('Segoe UI', 11))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignCenter,
                             "波形がここに表示されます")
            return

        mid_y = (h - margin_bottom) / 2
        max_amp = max(
            np.max(np.abs(self._peaks_pos)),
            np.max(np.abs(self._peaks_neg))
        ) * 1.1

        if max_amp < 1e-8:
            max_amp = 1.0

        num_bins = len(self._peaks_pos)
        bar_width = max(1, w / num_bins)

        # Draw waveform bars
        for i in range(num_bins):
            x = (i / num_bins) * w
            y_top = mid_y - (self._peaks_pos[i] / max_amp) * (mid_y - 8)
            y_bottom = mid_y - (self._peaks_neg[i] / max_amp) * (mid_y - 8)

            # Gradient fill
            gradient = QLinearGradient(x, y_top, x, y_bottom)
            gradient.setColorAt(0.0, QColor('#93C5FD'))
            gradient.setColorAt(0.5, QColor('#3B82F6'))
            gradient.setColorAt(1.0, QColor('#93C5FD'))

            painter.setPen(Qt.NoPen)
            painter.setBrush(gradient)
            bar_h = max(1, y_bottom - y_top)
            painter.drawRoundedRect(QRectF(x, y_top, bar_width + 0.5, bar_h), 1, 1)

        # Center line
        painter.setPen(QPen(QColor('#E4E7EB'), 1, Qt.DashLine))
        painter.drawLine(0, int(mid_y), w, int(mid_y))

        # Time markers
        painter.setPen(QColor('#9CA3AF'))
        painter.setFont(QFont('Segoe UI', 7))
        interval = self._get_time_interval()
        t = 0.0
        while t <= self.duration:
            x = (t / self.duration) * w if self.duration > 0 else 0
            painter.setPen(QPen(QColor('#E4E7EB'), 1))
            painter.drawLine(int(x), h - margin_bottom, int(x), h - margin_bottom + 4)
            painter.setPen(QColor('#9CA3AF'))
            mins = int(t // 60)
            secs = t % 60
            painter.drawText(int(x) + 2, h - 4, f"{mins}:{secs:04.1f}")
            t += interval

        # Playhead
        if self.duration > 0 and self._playhead_time >= 0:
            px = (self._playhead_time / self.duration) * w

            # Playhead shadow
            painter.setPen(QPen(QColor(239, 68, 68, 40), 6))
            painter.drawLine(int(px), 0, int(px), h - margin_bottom)

            # Playhead line
            painter.setPen(QPen(QColor('#EF4444'), 2))
            painter.drawLine(int(px), 0, int(px), h - margin_bottom)

            # Playhead handle (triangle at top)
            painter.setBrush(QColor('#EF4444'))
            painter.setPen(Qt.NoPen)
            triangle = QPolygonF([
                QPointF(px - 5, 0),
                QPointF(px + 5, 0),
                QPointF(px, 8),
            ])
            painter.drawPolygon(triangle)

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
