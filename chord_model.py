"""Chord estimation model module for ChordAI SavedModel."""
import os
import json
import logging
import warnings

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=Warning)

import tensorflow as tf

tf.get_logger().setLevel(logging.ERROR)
tf.autograph.set_verbosity(0)

# Disable GPU (use CPU only, matching original ChordAI-python)
tf.config.set_visible_devices([], 'GPU')

MODEL_URL = (
    "https://huggingface.co/anime-song/ChordAI/resolve/main/"
    "chordestimation.tar.gz?download=true"
)


class ChordModel:
    """Chord estimation model manager for ChordAI SavedModel."""

    def __init__(self, model_dir=None):
        base_dir = os.path.dirname(os.path.abspath(__file__))

        if model_dir is None:
            model_dir = os.path.join(base_dir, 'model', 'chordestimation')

        self.model_dir = model_dir
        self.index_path = os.path.join(base_dir, 'index.json')

        self.model = None
        self.chord_index = {}
        self._load_index()

    def _load_index(self):
        with open(self.index_path, 'r', encoding='utf-8') as f:
            self.chord_index = json.load(f)

    def _ensure_model(self):
        """Download model from Hugging Face if not present."""
        if os.path.isdir(self.model_dir):
            return

        import urllib.request
        import tarfile

        model_parent = os.path.dirname(self.model_dir)
        os.makedirs(model_parent, exist_ok=True)
        tar_path = os.path.join(model_parent, 'chordestimation.tar.gz')

        print("モデルをダウンロードしています...")
        urllib.request.urlretrieve(MODEL_URL, tar_path)

        print("モデルを展開しています...")
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(path=model_parent)

        if os.path.exists(tar_path):
            os.remove(tar_path)

        print("モデルの準備が完了しました。")

    def load_model(self):
        """Load the TF2 SavedModel via TFSMLayer (Keras 3 compatible)."""
        self._ensure_model()
        import keras
        self.model = keras.layers.TFSMLayer(
            self.model_dir, call_endpoint='serving_default')
        return self.model

    def predict(self, spectrogram):
        """Run chord prediction on preprocessed spectrogram.

        Args:
            spectrogram: Preprocessed CQT spectrogram array (already batched).

        Returns:
            Raw model predictions: list of 3 outputs
            [bass, chord, key], each with argmax-decoded indices.
        """
        if self.model is None:
            self.load_model()

        import numpy as np
        input_tensor = tf.constant(spectrogram, dtype=tf.float32)
        output = self.model(input_tensor)

        # TFSMLayer returns a dict with CRF-decoded outputs:
        #   bc:   bass  indices (1, timesteps) int32
        #   ccf:  chord indices (1, timesteps) int32
        #   kcrf: key   indices (1, timesteps) int32
        # Expand to (1, 1, timesteps) to match original format.
        bass = np.expand_dims(output['bc'].numpy(), axis=1)
        chord = np.expand_dims(output['ccf'].numpy(), axis=1)
        key = np.expand_dims(output['kcrf'].numpy(), axis=1)

        return [bass, chord, key]
