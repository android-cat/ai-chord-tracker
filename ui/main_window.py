"""Main application window."""
import os

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QProgressBar,
    QFrame, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal, Slot, QThread

from ui.waveform_widget import WaveformWidget
from ui.timeline_widget import TimelineWidget
from ui.player_controls import PlayerControls
from player import AudioPlayer


class AnalysisWorker(QThread):
    """Background worker for audio analysis."""

    finished = Signal(list)              # chord timeline
    error = Signal(str)
    progress = Signal(str)               # status message
    audio_loaded = Signal(object, int)   # audio_data, sample_rate

    def __init__(self, filepath, chord_model):
        super().__init__()
        self.filepath = filepath
        self.chord_model = chord_model

    def run(self):
        try:
            from audio_processor import preprocess, convert_time, load_audio_for_playback

            self.progress.emit("音声ファイル読み込み中...")
            audio_data, sr = load_audio_for_playback(self.filepath)
            self.audio_loaded.emit(audio_data, sr)

            self.progress.emit("スペクトログラム計算中...")
            S, bins_per_seconds = preprocess(self.filepath)

            self.progress.emit("コード推定中...")
            pred = self.chord_model.predict(S)

            self.progress.emit("タイムライン生成中...")
            times = convert_time(pred, bins_per_seconds,
                                 self.chord_model.chord_index)

            self.finished.emit(times)
        except Exception as e:
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Chord Tracker")
        self.setMinimumSize(1100, 750)
        self.resize(1280, 800)

        # Core components
        self.player = AudioPlayer(self)
        self._init_model_lazy = True    # load model on first use
        self._chord_model = None
        self.chord_timeline = []
        self.current_filepath = None
        self._worker = None

        self._setup_ui()
        self._connect_signals()

    # ── lazy model loading ──────────────────────────────────────

    @property
    def chord_model(self):
        if self._chord_model is None:
            from chord_model import ChordModel
            self._chord_model = ChordModel()
        return self._chord_model

    # ── UI Setup ────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 20, 24, 16)
        main_layout.setSpacing(16)

        # Header
        header = self._create_header()
        main_layout.addLayout(header)

        # Separator
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.HLine)
        main_layout.addWidget(sep)

        # Current chord + Time display
        chord_row = self._create_chord_display()
        main_layout.addLayout(chord_row)

        # Waveform section
        wf_label = QLabel("WAVEFORM")
        wf_label.setObjectName("sectionLabel")
        main_layout.addWidget(wf_label)

        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setMinimumHeight(140)
        self.waveform_widget.setMaximumHeight(200)
        main_layout.addWidget(self.waveform_widget)

        # Timeline section
        tl_label = QLabel("CHORD TIMELINE")
        tl_label.setObjectName("sectionLabel")
        main_layout.addWidget(tl_label)

        self.timeline_widget = TimelineWidget()
        self.timeline_widget.setMinimumHeight(90)
        self.timeline_widget.setMaximumHeight(130)
        main_layout.addWidget(self.timeline_widget)

        # Player controls
        self.player_controls = PlayerControls()
        self.player_controls.setEnabled(False)  # 最初は無効化
        main_layout.addWidget(self.player_controls)

        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)   # indeterminate
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "音声ファイルを選択してコード解析を開始してください")

    def _create_header(self):
        layout = QHBoxLayout()

        # Title
        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("AI Chord Tracker")
        title.setObjectName("titleLabel")
        title_col.addWidget(title)
        subtitle = QLabel("AI-powered automatic chord estimation")
        subtitle.setObjectName("subtitleLabel")
        title_col.addWidget(subtitle)
        layout.addLayout(title_col)

        layout.addStretch()

        # Open file button
        self.open_button = QPushButton("  ファイルを開く")
        self.open_button.setObjectName("primaryButton")
        self.open_button.setFixedHeight(42)
        self.open_button.setMinimumWidth(180)
        self.open_button.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self.open_button)

        # Export button
        self.export_button = QPushButton("  テキスト出力")
        self.export_button.setObjectName("primaryButton")
        self.export_button.setFixedHeight(42)
        self.export_button.setMinimumWidth(160)
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.setEnabled(False)
        layout.addWidget(self.export_button)

        return layout

    def _create_chord_display(self):
        layout = QHBoxLayout()
        layout.setSpacing(24)

        # Current chord
        chord_col = QVBoxLayout()
        chord_col.setSpacing(2)
        cl_title = QLabel("CURRENT CHORD")
        cl_title.setObjectName("sectionLabel")
        chord_col.addWidget(cl_title)
        self.current_chord_label = QLabel("---")
        self.current_chord_label.setObjectName("chordLabel")
        self.current_chord_label.setMinimumWidth(200)
        chord_col.addWidget(self.current_chord_label)
        layout.addLayout(chord_col)

        layout.addStretch()

        # Time display
        time_col = QVBoxLayout()
        time_col.setSpacing(2)
        time_col.setAlignment(Qt.AlignRight)
        tl_title = QLabel("TIME")
        tl_title.setObjectName("sectionLabel")
        tl_title.setAlignment(Qt.AlignRight)
        time_col.addWidget(tl_title)
        self.time_display = QLabel("0:00.0 / 0:00.0")
        self.time_display.setObjectName("timeLabel")
        self.time_display.setAlignment(Qt.AlignRight)
        time_col.addWidget(self.time_display)
        layout.addLayout(time_col)

        return layout

    # ── Signal wiring ───────────────────────────────────────────

    def _connect_signals(self):
        self.open_button.clicked.connect(self._on_open_file)
        self.export_button.clicked.connect(self._on_export_text)

        # Player → UI
        self.player.position_changed.connect(self._on_position_changed)
        self.player.playback_finished.connect(self._on_playback_finished)

        # Controls → Player
        self.player_controls.play_clicked.connect(self._on_play)
        self.player_controls.stop_clicked.connect(self._on_stop)
        self.player_controls.reverse_clicked.connect(self._on_reverse)
        self.player_controls.fast_forward_clicked.connect(self._on_fast_forward)
        self.player_controls.seek_requested.connect(self._on_seek)
        self.player_controls.volume_changed.connect(self._on_volume_changed)

        # Click‑to‑seek on waveform / timeline
        self.waveform_widget.position_clicked.connect(self._on_seek)
        self.timeline_widget.position_clicked.connect(self._on_seek)

    # ── Slots ───────────────────────────────────────────────────

    def _on_open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "音声ファイルを選択",
            "",
            "音声ファイル (*.wav *.mp3 *.ogg);;All Files (*)"
        )
        if not filepath:
            return

        self.current_filepath = filepath

        # Stop playback and reset position to 0
        self.player.stop()
        self.player_controls.set_playing(False)
        self._update_ui_position(0.0)

        self.open_button.setEnabled(False)
        self.progress_bar.show()
        self.player_controls.setEnabled(False)

        self._worker = AnalysisWorker(filepath, self.chord_model)
        self._worker.progress.connect(self._on_progress)
        self._worker.audio_loaded.connect(self._on_audio_loaded)
        self._worker.finished.connect(self._on_analysis_finished)
        self._worker.error.connect(self._on_analysis_error)
        self._worker.start()

    @Slot(str)
    def _on_progress(self, msg):
        self.status_bar.showMessage(msg)

    @Slot(object, int)
    def _on_audio_loaded(self, audio_data, sr):
        self.player.load(audio_data, sr)
        self.waveform_widget.set_audio(audio_data, sr)

    @Slot(list)
    def _on_analysis_finished(self, times):
        self.chord_timeline = times
        self.timeline_widget.set_chords(times)

        duration = self.player.duration
        self.player_controls.set_duration(duration)

        self.progress_bar.hide()
        self.open_button.setEnabled(True)
        self.player_controls.setEnabled(True)

        fname = os.path.basename(self.current_filepath or '')
        self.status_bar.showMessage(
            f"解析完了: {fname}  ({len(times)} コード検出)")
        self._update_time_display(0.0)
        self.export_button.setEnabled(True)

    @Slot(str)
    def _on_analysis_error(self, err):
        self.progress_bar.hide()
        self.open_button.setEnabled(True)
        QMessageBox.critical(
            self, "エラー",
            f"解析中にエラーが発生しました:\n{err}")
        self.status_bar.showMessage("エラーが発生しました")

    @Slot()
    def _on_play(self):
        self.player.play()

    @Slot()
    def _on_stop(self):
        self.player.stop()

    @Slot()
    def _on_reverse(self):
        self.player.play_reverse()

    @Slot()
    def _on_fast_forward(self):
        """Skip forward 5 seconds."""
        new_time = min(self.player.current_time + 5.0, self.player.duration)
        self.player.seek(new_time)
        self._update_ui_position(new_time)

    @Slot(float)
    def _on_volume_changed(self, vol):
        self.player.volume = vol

    @Slot(float)
    def _on_seek(self, time_sec):
        self.player.seek(time_sec)
        self._update_ui_position(time_sec)

    @Slot(float)
    def _on_position_changed(self, time_sec):
        self._update_ui_position(time_sec)

    @Slot()
    def _on_playback_finished(self):
        self.player_controls.set_playing(False)

    # ── Helpers ─────────────────────────────────────────────────

    def _update_ui_position(self, time_sec):
        self.waveform_widget.set_playhead(time_sec)
        self.timeline_widget.set_playhead(time_sec)
        self.player_controls.set_position(time_sec)
        self._update_time_display(time_sec)
        self._update_current_chord(time_sec)

    def _update_time_display(self, time_sec):
        duration = self.player.duration
        self.time_display.setText(
            f"{self._fmt(time_sec)} / {self._fmt(duration)}")

    def _update_current_chord(self, time_sec):
        chord = "---"
        for s, e, c in self.chord_timeline:
            if s <= time_sec < e:
                chord = c
                break
        self.current_chord_label.setText(chord)

    @Slot()
    def _on_export_text(self):
        """Export chord timeline as a text file with millisecond timestamps."""
        if not self.chord_timeline:
            QMessageBox.information(self, "情報", "エクスポートするコードデータがありません。")
            return

        # Default filename based on the audio file
        default_name = ""
        if self.current_filepath:
            base = os.path.splitext(os.path.basename(self.current_filepath))[0]
            default_dir = os.path.dirname(self.current_filepath)
            default_name = os.path.join(default_dir, f"{base}_chords.txt")

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "コードタイムラインを保存",
            default_name,
            "テキストファイル (*.txt);;All Files (*)"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                for start, end, chord in self.chord_timeline:
                    start_ms = int(round(start * 1000))
                    end_ms = int(round(end * 1000))
                    f.write(f"{start_ms}\t{end_ms}\t{chord}\n")

            self.status_bar.showMessage(
                f"テキスト出力完了: {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.critical(
                self, "エラー",
                f"ファイルの保存に失敗しました:\n{e}")

    @staticmethod
    def _fmt(seconds):
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m}:{s:04.1f}"

    def closeEvent(self, event):
        self.player.cleanup()
        super().closeEvent(event)
