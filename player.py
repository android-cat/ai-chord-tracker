"""Audio playback engine using sounddevice."""
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, QTimer


class AudioPlayer(QObject):
    """Audio player with play, reverse play, and stop functionality."""

    position_changed = Signal(float)   # current time in seconds
    playback_finished = Signal()
    state_changed = Signal(str)        # 'playing', 'stopped', 'reverse'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio_data = None
        self.sr = 22050
        self._position = 0        # in samples
        self._playing = False
        self._reverse = False
        self._stream = None
        self._volume = 1.0        # 0.0 – 1.0

        # Timer for position updates (~30fps)
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._update_position)

    @property
    def volume(self):
        """Current volume level (0.0 – 1.0)."""
        return self._volume

    @volume.setter
    def volume(self, value):
        """Set volume level (clamped to 0.0 – 1.0)."""
        self._volume = max(0.0, min(1.0, float(value)))

    def load(self, audio_data, sr):
        """Load audio data for playback."""
        self.stop()
        self.audio_data = audio_data.astype(np.float32)
        self.sr = sr
        self._position = 0

    @property
    def duration(self):
        """Total duration in seconds."""
        if self.audio_data is None:
            return 0.0
        return len(self.audio_data) / self.sr

    @property
    def current_time(self):
        """Current playback position in seconds."""
        return self._position / self.sr

    @current_time.setter
    def current_time(self, t):
        """Set playback position in seconds."""
        self._position = int(t * self.sr)
        if self.audio_data is not None:
            self._position = max(0, min(self._position, len(self.audio_data)))

    def _audio_callback(self, outdata, frames, time_info, status):
        """Sounddevice callback for audio output."""
        if self.audio_data is None or not self._playing:
            outdata.fill(0)
            return

        if self._reverse:
            start = self._position - frames
            if start < 0:
                chunk_len = self._position
                if chunk_len <= 0:
                    outdata.fill(0)
                    self._position = 0
                    self._playing = False
                    return
                chunk = self.audio_data[0:self._position][::-1]
                outdata[:chunk_len, 0] = chunk * self._volume
                outdata[chunk_len:] = 0
                self._position = 0
                self._playing = False
                return
            chunk = self.audio_data[start:self._position][::-1]
            self._position = start
        else:
            end = self._position + frames
            if end > len(self.audio_data):
                chunk_len = len(self.audio_data) - self._position
                if chunk_len <= 0:
                    outdata.fill(0)
                    self._position = len(self.audio_data)
                    self._playing = False
                    return
                chunk = self.audio_data[self._position:]
                outdata[:chunk_len, 0] = chunk * self._volume
                outdata[chunk_len:] = 0
                self._position = len(self.audio_data)
                self._playing = False
                return
            chunk = self.audio_data[self._position:end]
            self._position = end

        outdata[:, 0] = chunk * self._volume

    def play(self):
        """Start forward playback."""
        if self.audio_data is None:
            return

        self.stop()
        self._playing = True
        self._reverse = False

        if self._position >= len(self.audio_data):
            self._position = 0

        self._stream = sd.OutputStream(
            samplerate=self.sr,
            channels=1,
            callback=self._audio_callback,
            blocksize=1024,
            dtype='float32'
        )
        self._stream.start()
        self._timer.start()
        self.state_changed.emit('playing')

    def play_reverse(self):
        """Start reverse playback."""
        if self.audio_data is None:
            return

        self.stop()
        self._playing = True
        self._reverse = True

        if self._position <= 0:
            self._position = len(self.audio_data)

        self._stream = sd.OutputStream(
            samplerate=self.sr,
            channels=1,
            callback=self._audio_callback,
            blocksize=1024,
            dtype='float32'
        )
        self._stream.start()
        self._timer.start()
        self.state_changed.emit('reverse')

    def stop(self):
        """Stop playback."""
        self._playing = False
        self._timer.stop()

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        self.state_changed.emit('stopped')

    def seek(self, time_sec):
        """Seek to a specific time in seconds."""
        was_playing = self._playing
        was_reverse = self._reverse

        if was_playing:
            self.stop()

        self.current_time = time_sec
        self.position_changed.emit(self.current_time)

        if was_playing:
            if was_reverse:
                self.play_reverse()
            else:
                self.play()

    def _update_position(self):
        """Timer callback to emit position updates."""
        if not self._playing:
            self._timer.stop()
            self.playback_finished.emit()
            self.state_changed.emit('stopped')
            return

        self.position_changed.emit(self.current_time)

    def cleanup(self):
        """Clean up resources."""
        self.stop()
