"""Chord estimation model module with TF2/Keras3 compatibility."""
import os
import json
import numpy as np
import h5py

try:
    import keras
    from keras import ops, Layer
except ImportError:
    import tensorflow.keras as keras
    from tensorflow.keras import layers
    Layer = layers.Layer

import tensorflow as tf


def mish(inputs):
    """Mish activation function."""
    return inputs * tf.math.tanh(tf.math.softplus(inputs))


class CRF(Layer):
    """Minimal CRF layer compatible with keras_contrib CRF for inference.

    This layer reproduces the weight structure of the original keras_contrib CRF
    so that saved model weights can be loaded. During inference, it applies
    a dense projection (equivalent to the CRF emission scores).
    """

    def __init__(self, units, learn_mode='join', test_mode='viterbi',
                 sparse_target=False, use_boundary=False, use_bias=True,
                 activation='linear', kernel_initializer='glorot_uniform',
                 chain_initializer='orthogonal', boundary_initializer='zeros',
                 bias_initializer='zeros', kernel_regularizer=None,
                 chain_regularizer=None, boundary_regularizer=None,
                 bias_regularizer=None, kernel_constraint=None,
                 chain_constraint=None, boundary_constraint=None,
                 bias_constraint=None, **kwargs):
        # Remove legacy kwargs
        kwargs.pop('input_dim', None)
        kwargs.pop('unroll', None)
        super().__init__(**kwargs)
        self.units = units
        self.learn_mode = learn_mode
        self.test_mode = test_mode
        self.sparse_target = sparse_target
        self.use_boundary = use_boundary
        self.use_bias = use_bias
        self._activation_str = activation
        self.activation_fn = keras.activations.get(activation)

    def build(self, input_shape):
        input_dim = int(input_shape[-1])
        # Weight creation order must be alphabetical by name to match
        # the order Keras uses when loading weights from legacy h5 files.
        if self.use_bias:
            self.bias = self.add_weight(
                name='bias', shape=(self.units,),
                initializer='zeros')
        self.chain_kernel = self.add_weight(
            name='chain_kernel', shape=(self.units, self.units),
            initializer='orthogonal')
        self.kernel = self.add_weight(
            name='kernel', shape=(input_dim, self.units),
            initializer='glorot_uniform')
        if self.use_boundary:
            self.left_boundary = self.add_weight(
                name='left_boundary', shape=(self.units,),
                initializer='zeros')
            self.right_boundary = self.add_weight(
                name='right_boundary', shape=(self.units,),
                initializer='zeros')
        self.built = True

    def call(self, inputs):
        # Compute emission scores only: (batch, timesteps, units)
        # Viterbi decoding is applied as post-processing in ChordModel.predict()
        # because Keras 3 functional model construction requires graph-compatible ops.
        emissions = tf.matmul(inputs, self.kernel)
        if self.use_bias:
            emissions = emissions + self.bias
        emissions = self.activation_fn(emissions)
        return emissions

    def compute_output_shape(self, input_shape):
        return input_shape[:-1] + (self.units,)

    def get_config(self):
        config = super().get_config()
        config.update({
            'units': self.units,
            'learn_mode': self.learn_mode,
            'test_mode': self.test_mode,
            'sparse_target': self.sparse_target,
            'use_boundary': self.use_boundary,
            'use_bias': self.use_bias,
            'activation': self._activation_str,
        })
        return config


class ChordModel:
    """Chord estimation model manager."""

    def __init__(self, model_dir=None):
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'model')

        self.model_path = os.path.join(model_dir, 'chord_estimation_model.h5')
        self.index_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'index.json')

        self.model = None
        self.chord_index = {}
        self._load_index()

    def _load_index(self):
        with open(self.index_path, 'r', encoding='utf-8') as f:
            self.chord_index = json.load(f)

    def load_model(self):
        """Load the Keras model with custom objects.

        The original model was saved with TF1 + Keras 2.3 + keras_contrib.
        We reconstruct the model from h5 config and manually load weights
        by name for robust compatibility with Keras 3.
        """
        from keras.src.models.functional import Functional
        custom_objects = {
            'CRF': CRF,
            'mish': mish,
            'LSTM': keras.layers.LSTM,
            'Functional': Functional,
        }

        # --- Step 1: Load model architecture from h5 config ---
        with h5py.File(self.model_path, 'r') as f:
            model_config_json = f.attrs.get('model_config')
            if isinstance(model_config_json, bytes):
                model_config_json = model_config_json.decode('utf-8')
            model_config = json.loads(model_config_json)

        # Keras 2 saves Functional models as class_name='Model',
        # but Keras 3 expects 'Functional'.
        def _fix_config(cfg):
            if isinstance(cfg, dict):
                if cfg.get('class_name') == 'Model':
                    cfg['class_name'] = 'Functional'
                for v in cfg.values():
                    _fix_config(v)
            elif isinstance(cfg, list):
                for item in cfg:
                    _fix_config(item)
        _fix_config(model_config)

        with keras.utils.custom_object_scope(custom_objects):
            self.model = keras.models.model_from_json(
                json.dumps(model_config)
            )

        # --- Step 2: Manually load weights by name from h5 ---
        with h5py.File(self.model_path, 'r') as f:
            weights_group = f['model_weights']
            for layer in self.model.layers:
                layer_name = layer.name
                if layer_name not in weights_group:
                    continue
                layer_grp = weights_group[layer_name]
                # In legacy h5, weights are under layer_name/layer_name/
                if layer_name in layer_grp:
                    layer_grp = layer_grp[layer_name]

                # Check if this is a wrapper layer (e.g. Bidirectional)
                # by looking for sub-groups instead of direct datasets.
                sub_groups = []
                direct_weights = {}
                for k in layer_grp:
                    item = layer_grp[k]
                    if hasattr(item, 'shape'):
                        # Direct dataset
                        clean = k.replace(':0', '')
                        direct_weights[clean] = np.array(item)
                    else:
                        sub_groups.append(k)

                if sub_groups and not direct_weights:
                    # Wrapper layer (e.g. Bidirectional with forward/backward).
                    # Keras 3 Bidirectional stores weights as:
                    #   [forward_kernel, forward_recurrent_kernel, forward_bias,
                    #    backward_kernel, backward_recurrent_kernel, backward_bias]
                    # Identify forward/backward groups and load in order.
                    fwd_groups = sorted([g for g in sub_groups if 'forward' in g])
                    bwd_groups = sorted([g for g in sub_groups if 'backward' in g])
                    ordered_groups = fwd_groups + bwd_groups
                    if not ordered_groups:
                        ordered_groups = sorted(sub_groups)

                    weight_values = []
                    for sg_name in ordered_groups:
                        sg = layer_grp[sg_name]
                        # Collect weights in this sub-group by name
                        sg_weights = {}
                        for wname in sg:
                            clean = wname.replace(':0', '')
                            sg_weights[clean] = np.array(sg[wname])
                        # LSTM weight order in Keras 3: kernel, recurrent_kernel, bias
                        for expected in ['kernel', 'recurrent_kernel', 'bias']:
                            if expected in sg_weights:
                                weight_values.append(sg_weights[expected])
                    layer.set_weights(weight_values)
                else:
                    # Flat layer: match weights by name
                    weight_values = []
                    for w in layer.weights:
                        w_short = w.name.split('/')[-1].replace(':0', '')
                        if w_short in direct_weights:
                            weight_values.append(direct_weights[w_short])
                        else:
                            raise ValueError(
                                f"Weight '{w_short}' not found in h5 for "
                                f"layer '{layer_name}'. "
                                f"Available: {list(direct_weights.keys())}"
                            )
                    if weight_values:
                        layer.set_weights(weight_values)

        return self.model

    def predict(self, spectrogram):
        """Run chord prediction on preprocessed spectrogram.

        Applies Viterbi decoding as post-processing to reproduce the
        original keras_contrib CRF behavior.

        Args:
            spectrogram: Preprocessed CQT spectrogram array.

        Returns:
            Raw model predictions (chord quality, bass), with Viterbi
            decoding applied to CRF output layers.
        """
        if self.model is None:
            self.load_model()

        pred = self.model.predict(np.expand_dims(spectrogram, 0), verbose=0)

        # Apply Viterbi decoding to CRF layer outputs
        pred = self._apply_viterbi(pred)

        return pred

    def _apply_viterbi(self, pred):
        """Apply Viterbi decoding using CRF chain_kernel weights.

        The model's CRF layers output raw emission scores. This method
        applies Viterbi decoding with the learned transition matrix
        to produce temporally coherent predictions.
        """
        # Find CRF layers and their chain kernels
        crf_layers = [l for l in self.model.layers if isinstance(l, CRF)]
        if not crf_layers:
            return pred

        # pred can be a list of arrays (multi-output model)
        if not isinstance(pred, list):
            pred = [pred]

        result = []
        crf_idx = 0
        for p in pred:
            if crf_idx < len(crf_layers):
                crf = crf_layers[crf_idx]
                chain = crf.chain_kernel.numpy()  # (num_classes, num_classes)
                left_b = crf.left_boundary.numpy() if crf.use_boundary else None
                right_b = crf.right_boundary.numpy() if crf.use_boundary else None
                decoded = self._viterbi_numpy(p, chain, left_b, right_b)
                result.append(decoded)
                crf_idx += 1
            else:
                result.append(p)

        return result

    @staticmethod
    def _viterbi_numpy(emissions, trans, left_boundary=None, right_boundary=None):
        """NumPy Viterbi decoding matching keras_contrib CRF behavior.

        The original keras_contrib CRF uses an energy-based formulation where
        lower energy = higher probability. The Viterbi finds the path that
        MINIMIZES total energy.

        Key differences from a standard score-based Viterbi:
        - Uses MIN/ARGMIN (energy minimization) instead of MAX/ARGMAX.
        - Emission is placed on the FROM-state side of the transition,
          matching the original CRF's step() function.
        - Boundary energies are added directly to emissions before recursion.

        Args:
            emissions: (batch, timesteps, num_classes) emission energies.
            trans: (num_classes, num_classes) transition matrix (chain_kernel).
            left_boundary: optional (num_classes,) start boundary energy.
            right_boundary: optional (num_classes,) end boundary energy.

        Returns:
            One-hot encoded best path: (batch, timesteps, num_classes).
        """
        batch_size, timesteps, num_classes = emissions.shape

        # Add boundary energies to emissions (like original CRF's
        # add_boundary_energy before recursion).
        em = emissions.copy()
        if left_boundary is not None:
            em[:, 0, :] += left_boundary
        if right_boundary is not None:
            em[:, -1, :] += right_boundary

        result = np.zeros_like(emissions)

        for b in range(batch_size):
            # Forward pass: prev starts at zeros (matching original CRF init).
            prev = np.zeros(num_classes)
            argmin_tables = np.zeros((timesteps, num_classes), dtype=np.int32)

            for t in range(timesteps):
                # Original CRF step (return_logZ=False):
                #   energy = chain_energy + expand_dims(input_energy_t + prev, 2)
                #   min_energy = K.min(energy, axis=1)
                #   argmin_table = K.argmin(energy, axis=1)
                #
                # energy[i, j] = trans[i, j] + em[t, i] + prev[i]
                # Emission is on the FROM-state (i) side.
                val = em[b, t] + prev                     # (num_classes,)
                energy = trans + val[:, None]              # (num_classes, num_classes)
                argmin_tables[t] = np.argmin(energy, axis=0)  # best FROM for each TO
                prev = np.min(energy, axis=0)                 # min energy for each TO

            # Backward pass: trace back through argmin tables.
            # Match the original keras_contrib CRF backward trace exactly:
            # It starts with a "phantom" TO state (j=0), looks up the best
            # FROM state, then uses that as the starting point for the path.
            path = np.zeros(timesteps, dtype=np.int32)
            initial = argmin_tables[timesteps - 1, 0]
            path[timesteps - 1] = argmin_tables[timesteps - 1, initial]

            for t in range(timesteps - 2, -1, -1):
                path[t] = argmin_tables[t, path[t + 1]]

            # Convert to one-hot
            result[b] = np.eye(num_classes)[path]

        return result
