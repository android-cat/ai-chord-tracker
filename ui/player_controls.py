"""Playback control widgets."""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSlider, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal


class PlayerControls(QWidget):
    """Play / Reverse / Fast-forward controls with seek slider."""

    play_clicked = Signal()
    stop_clicked = Signal()
    reverse_clicked = Signal()
    fast_forward_clicked = Signal()
    seek_requested = Signal(float)   # time in seconds
    volume_changed = Signal(float)   # 0.0 – 1.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration = 0.0
        self._is_playing = False
        self._seeking = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(12)

        # Common style for all transport buttons
        btn_style = self._get_button_style()

        # Reverse button
        self.reverse_btn = QPushButton("◀◀")
        self.reverse_btn.setFixedSize(44, 44)
        self.reverse_btn.setToolTip("逆再生")
        self.reverse_btn.setCursor(Qt.PointingHandCursor)
        self.reverse_btn.setStyleSheet(btn_style)
        layout.addWidget(self.reverse_btn)

        # Play / Stop button
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(52, 52)
        self.play_btn.setToolTip("再生")
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet(self._get_button_style(font_size=20, radius=26))
        layout.addWidget(self.play_btn)

        # Fast-forward button
        self.ff_btn = QPushButton("▶▶")
        self.ff_btn.setFixedSize(44, 44)
        self.ff_btn.setToolTip("早送り")
        self.ff_btn.setCursor(Qt.PointingHandCursor)
        self.ff_btn.setStyleSheet(btn_style)
        layout.addWidget(self.ff_btn)

        layout.addSpacing(8)

        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        layout.addWidget(self.seek_slider, 1)

        layout.addSpacing(12)

        # Volume icon
        self.vol_icon = QLabel("🔊")
        self.vol_icon.setFixedWidth(24)
        self.vol_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.vol_icon)

        # Volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(100)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.setToolTip("音量")
        layout.addWidget(self.volume_slider)

        # Volume label
        self.vol_label = QLabel("100%")
        self.vol_label.setFixedWidth(40)
        self.vol_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.vol_label)

        # Connect signals
        self.play_btn.clicked.connect(self._on_play_clicked)
        self.ff_btn.clicked.connect(self._on_ff_clicked)
        self.reverse_btn.clicked.connect(self._on_reverse_clicked)
        self.seek_slider.sliderPressed.connect(self._on_slider_pressed)
        self.seek_slider.sliderReleased.connect(self._on_slider_released)
        self.seek_slider.sliderMoved.connect(self._on_slider_moved)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)

    # ── public API ──────────────────────────────────────────────

    def set_duration(self, duration):
        self._duration = duration

    def set_position(self, time_sec):
        """Update slider position (called by timer, not user)."""
        if not self._seeking and self._duration > 0:
            value = int((time_sec / self._duration) * 1000)
            self.seek_slider.setValue(value)

    def set_playing(self, is_playing):
        self._is_playing = is_playing
        self.play_btn.setText("■" if is_playing else "▶")
        self.play_btn.setToolTip("停止" if is_playing else "再生")

    # ── slots ───────────────────────────────────────────────────

    def _on_play_clicked(self):
        if self._is_playing:
            self.stop_clicked.emit()
            self.set_playing(False)
        else:
            self.play_clicked.emit()
            self.set_playing(True)

    def _on_ff_clicked(self):
        self.fast_forward_clicked.emit()

    def _on_reverse_clicked(self):
        self.reverse_clicked.emit()
        self.set_playing(True)

    def _on_slider_pressed(self):
        self._seeking = True

    def _on_slider_released(self):
        self._seeking = False
        if self._duration > 0:
            time_sec = (self.seek_slider.value() / 1000) * self._duration
            self.seek_requested.emit(time_sec)

    def _on_slider_moved(self, value):
        if self._duration > 0:
            time_sec = (value / 1000) * self._duration
            self.seek_requested.emit(time_sec)

    def _on_volume_changed(self, value):
        vol = value / 100.0
        self.volume_changed.emit(vol)
        self.vol_label.setText(f"{value}%")
        if value == 0:
            self.vol_icon.setText("🔇")
        elif value < 50:
            self.vol_icon.setText("🔉")
        else:
            self.vol_icon.setText("🔊")

    # ── styles ──────────────────────────────────────────────────

    @staticmethod
    def _get_button_style(font_size=16, radius=22):
        return f"""
            QPushButton {{
                background-color: #3B82F6;
                color: white;
                border: none;
                border-radius: {radius}px;
                font-size: {font_size}px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: #2563EB;
            }}
            QPushButton:pressed {{
                background-color: #1D4ED8;
            }}
            QPushButton:disabled {{
                background-color: #93C5FD;
                color: rgba(255,255,255,0.6);
            }}
        """
