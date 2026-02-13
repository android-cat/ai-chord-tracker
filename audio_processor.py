"""Audio processing module for chord estimation (ChordAI-python-main compatible)."""
import librosa
import numpy as np
import json
import os

try:
    from dlchordx import Chord
except ImportError:
    Chord = None

TONES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

KEY_NAMES = [
    "N",
    "C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B",
    "Am", "Bbm", "Bm", "Cm", "C#m", "Dm", "Ebm", "Em", "Fm", "F#m", "Gm", "G#m",
]


def minmax(x, axis=None):
    """Min-max normalize array to [0, 1]."""
    x_min = x.min(axis=axis, keepdims=True)
    x_max = x.max(axis=axis, keepdims=True)
    denom = x_max - x_min
    denom = np.where(denom == 0, 1, denom)
    return (x - x_min) / denom


def cqt(y, sr=22050, n_bins=12 * 3 * 7, bins_per_octave=12 * 3,
         hop_length=512, fmin=32.7, window="hann", Qfactor=20.0, norm=minmax):
    """Compute CQT spectrogram with L+R and L-R channels."""
    mono = True if len(y.shape) == 1 else False

    filter_scale = (1 / bins_per_octave) * Qfactor

    if mono:
        S = np.abs(
            librosa.cqt(
                y, sr=sr, n_bins=n_bins, bins_per_octave=bins_per_octave,
                hop_length=hop_length, filter_scale=filter_scale,
                fmin=fmin, scale=True, window=window)
        ).astype("float32").T
    else:
        S_lr = np.abs(
            librosa.cqt(
                (y[0] * 0.5 + y[1] * 0.5),
                sr=sr, n_bins=n_bins, bins_per_octave=bins_per_octave,
                hop_length=hop_length, filter_scale=filter_scale,
                fmin=fmin, scale=True, window=window)
        ).astype("float32")

        S_lrm = np.abs(
            librosa.cqt(
                (y[0] - y[1]),
                sr=sr, n_bins=n_bins, bins_per_octave=bins_per_octave,
                hop_length=hop_length, filter_scale=filter_scale,
                fmin=fmin, scale=True, window=window)
        ).astype("float32")

        S = np.array((S_lr.T, S_lrm.T))

    if norm is not None:
        S = norm(S)

    return S


def preprocess(path, sr=22050, mono=False):
    """Load and preprocess audio for model input.

    Args:
        path: Path to audio file.
        sr: Target sample rate.
        mono: Whether to force mono loading.

    Returns:
        Tuple of (preprocessed spectrogram, bins_per_second, duration).
    """
    y, sr = librosa.load(path, sr=sr, mono=mono)
    hop_length = 512 + 32
    bins_per_second = sr / hop_length
    duration = librosa.get_duration(y=y)

    if len(y.shape) == 1:
        y = np.array([y, y])

    S = cqt(
        y, sr=sr, n_bins=12 * 3 * 7, bins_per_octave=12 * 3,
        hop_length=hop_length, Qfactor=22.0)

    # Pad to multiple of 8192
    p = 8192 - (S.shape[1] % 8192)
    S_padding = np.zeros((S.shape[0], S.shape[1] + p, S.shape[2]))
    S_padding[:, :S.shape[1], :] = S
    S_padding = S_padding.transpose(1, 2, 0)
    S_padding = np.array([S_padding])

    return S_padding, bins_per_second, duration


def load_audio_for_playback(path, sr=None):
    """Load audio for playback (stereo, original sample rate).

    Args:
        path: Path to audio file.
        sr: Target sample rate (None for original).

    Returns:
        Tuple of (audio array [shape: (samples, channels)], sample rate).
    """
    y, sr = librosa.load(path, sr=sr, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y], axis=-1)
    else:
        y = y.T
    return y, sr


def _lastone(iterable):
    """Yield (item, is_last) for each element in iterable."""
    it = iter(iterable)
    last = next(it)
    for val in it:
        yield last, False
        last = val
    yield last, True


def convert_time_key(pred, bins_per_second, min_time=0.1):
    """Convert key prediction output to key timeline.

    Args:
        pred: Full model prediction (3 outputs: bass, chord, key).
        bins_per_second: Time resolution.
        min_time: Minimum key segment duration in seconds.

    Returns:
        List of [start_time, end_time, key_name] entries.
    """
    key = pred[2][0][0]

    times = []
    before_key = key[0]
    before_time = 0.0
    nframes = len(key)

    for i, is_last in _lastone(range(1, nframes)):
        if before_key != key[i] or is_last:
            current_time = i / bins_per_second

            if current_time - before_time < min_time:
                before_key = key[i]
                continue

            current_key = KEY_NAMES[before_key]

            times.append([
                round(before_time, 3),
                round(current_time, 3),
                current_key
            ])

            before_time = current_time
            before_key = key[i]

    return times


def convert_time(pred, bins_per_second, chord_index, min_time=0.1):
    """Convert model predictions to chord timeline.

    Args:
        pred: Full model prediction (3 outputs: bass, chord, key).
        bins_per_second: Time resolution.
        chord_index: Dictionary mapping index to chord name.
        min_time: Minimum chord duration in seconds.

    Returns:
        List of [start_time, end_time, chord_name] entries.
    """
    chord = pred[1][0][0]
    bass = pred[0][0][0]

    times = []
    before_chord = [chord[0], bass[0]]
    before_time = 0.0
    nframes = len(chord)

    for i in range(1, nframes):
        if (before_chord[0] != chord[i]) or (before_chord[1] != bass[i]):
            current_time = i / bins_per_second

            if current_time - before_time < min_time:
                before_chord = [chord[i], bass[i]]
                continue

            current_chord = before_chord[0]
            current_bass = before_chord[1]

            try:
                chord_text_ = chord_index[str(current_chord)]

                if chord_text_ == "N.C.":
                    raise ValueError()

                if Chord is not None:
                    chord_temp = Chord(chord_text_).reconfigured()
                    chord_text = chord_temp.name

                    if chord_temp.bass.get_interval() != (
                            current_bass - 1) and current_bass != 0:
                        chord_text += "/" + TONES[current_bass - 1]
                        chord_text = Chord(chord_text).reconfigured().name
                else:
                    chord_text = chord_text_
                    if current_bass != 0 and 0 <= current_bass - 1 < len(TONES):
                        root_idx = _get_root_index(chord_text)
                        if root_idx is not None and root_idx != (current_bass - 1):
                            chord_text += "/" + TONES[current_bass - 1]

            except (ValueError, Exception):
                chord_text = chord_index[str(current_chord)]

            times.append([
                round(before_time, 3),
                round(current_time, 3),
                chord_text
            ])

            before_time = current_time
            before_chord = [chord[i], bass[i]]

    return times


def minor_key_to_major_key(key):
    """Convert minor key name to its relative major for accidental lookup."""
    index = KEY_NAMES.index(key)
    if index >= 13:
        index = index - 12
    return KEY_NAMES[index]


def modify_accidentals(chord_times, key_times):
    """Modify chord accidentals based on key estimation.

    Uses dlchordx to adjust sharp/flat notation to match the detected key.

    Args:
        chord_times: List of [start, end, chord_name].
        key_times: List of [start, end, key_name].

    Returns:
        List of [start, end, modified_chord_name].
    """
    if Chord is None:
        return chord_times

    result = []
    for chord_time in chord_times:
        chord_start_time = chord_time[0]
        modified_chord = chord_time[2]

        if modified_chord != "N.C.":
            for key_time in key_times:
                if key_time[2] == "N":
                    continue
                start_time = key_time[0]
                end_time = key_time[1]

                if chord_start_time >= start_time and chord_start_time <= end_time:
                    try:
                        modified_chord = Chord(modified_chord).modified_accidentals(
                            minor_key_to_major_key(key_time[2])).name
                    except Exception:
                        pass
                    break

        result.append([
            chord_time[0],
            chord_time[1],
            modified_chord
        ])

    return result


def _get_root_index(chord_name):
    """Extract root note index from chord name."""
    if not chord_name or chord_name == "N.C.":
        return None
    if len(chord_name) >= 2 and chord_name[1] == 'b':
        root = chord_name[:2]
    else:
        root = chord_name[0]
    try:
        return TONES.index(root)
    except ValueError:
        return None


def get_chord_root(chord_name):
    """Get the root note name from a chord name."""
    if not chord_name or chord_name == "N.C.":
        return None
    if len(chord_name) >= 2 and chord_name[1] == 'b':
        return chord_name[:2]
    return chord_name[0]
