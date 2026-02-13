"""Audio processing module for chord estimation."""
import librosa
import numpy as np


TONES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


def standard(x):
    """Standardize array to zero mean and unit variance."""
    return (x - np.mean(x)) / (np.std(x) + 1e-8)


def preprocess(path, sr=22050, hop_length=512):
    """Load and preprocess audio for model input.

    Args:
        path: Path to audio file.
        sr: Target sample rate.
        hop_length: Hop length for CQT.

    Returns:
        Tuple of (preprocessed spectrogram, bins per second).
    """
    y, sr = librosa.load(path, sr=sr, mono=False)

    # Handle mono files
    if y.ndim == 1:
        y = np.array([y, y])

    S_l = np.abs(
        librosa.cqt(y[0], sr=sr, hop_length=hop_length,
                     n_bins=12 * 3 * 7, bins_per_octave=12 * 3)
    ).astype("float32")

    S_r = np.abs(
        librosa.cqt(y[1], sr=sr, hop_length=hop_length,
                     n_bins=12 * 3 * 7, bins_per_octave=12 * 3)
    ).astype("float32")

    S = np.array((S_l.T, S_r.T))
    S = standard(S)
    S = np.concatenate((S[0], S[1], (S[0] - S[1])), axis=-1)

    bins_per_seconds = S.shape[-2] / (y.shape[-1] / sr)

    return S, bins_per_seconds


def load_audio_for_playback(path, sr=None):
    """Load audio for playback (mono, original or specified sample rate).

    Args:
        path: Path to audio file.
        sr: Target sample rate (None for original).

    Returns:
        Tuple of (audio array, sample rate).
    """
    y, sr = librosa.load(path, sr=sr, mono=True)
    return y, sr


def convert_time(pred, bins_per_seconds, chord_index, min_time=0.1):
    """Convert model predictions to chord timeline.

    Args:
        pred: Model prediction output (chord_quality, bass).
        bins_per_seconds: Time resolution.
        chord_index: Dictionary mapping index to chord name.
        min_time: Minimum chord duration in seconds.

    Returns:
        List of [start_time, end_time, chord_name] entries.
    """
    result = pred[0][0]
    bass_result = pred[1][0]

    times = []

    s_time = 0.0
    e_time = 0.0
    last = 0
    now_chord = ""
    chord = ""

    # Find last non-silent frame
    for i, t in enumerate(result):
        if np.argmax(bass_result[i]) != 0:
            last = i

    for i, t in enumerate(result):
        bass_line = np.argmax(bass_result[i])

        if bass_line != 0:
            chord = chord_index[str(np.argmax(t))]
            if chord != "N.C.":
                root_idx = _get_root_index(chord)
                if root_idx is not None and root_idx != (bass_line - 1):
                    if 0 <= bass_line - 1 < len(TONES):
                        chord += "/{}".format(TONES[bass_line - 1])

        if i == 0:
            now_chord = chord
            continue

        if now_chord != chord or i == last or i == len(result) - 1:
            e_time = i / bins_per_seconds

            if abs(s_time - e_time) > min_time:
                if len(times) > 1 and times[-1][-1] == now_chord:
                    times[-1][-2] = e_time
                else:
                    if now_chord:
                        times.append([s_time, e_time, now_chord])

                s_time = e_time
            now_chord = chord

    return times


def _get_root_index(chord_name):
    """Extract root note index from chord name."""
    if not chord_name or chord_name == "N.C.":
        return None

    # Check for flat (e.g., "Db", "Eb")
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
