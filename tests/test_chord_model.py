import pytest
import numpy as np
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chord_model import ChordModel

def test_chord_model_init(mocker):
    # index.jsonのファイルロードをモック化
    mocker.patch("builtins.open", mocker.mock_open(read_data='{"0": "C", "1": "Am"}'))
    
    model = ChordModel(model_dir="/dummy/dir")
    
    assert model.model_dir == "/dummy/dir"
    assert model.chord_index == {"0": "C", "1": "Am"}

def test_chord_model_predict(mocker):
    # index.jsonモック
    mocker.patch("builtins.open", mocker.mock_open(read_data='{"0": "C", "1": "Am"}'))
    model = ChordModel(model_dir="/dummy/dir")
    
    # TensorFlowのモデルロード処理・予測呼び出しをモック化
    class MockOutput:
        def __init__(self, data):
            self._data = data
        def numpy(self):
            return self._data
            
    mock_tf_model = mocker.MagicMock()
    # モデル出力の想定形式（TFSMLayerの場合）
    mock_tf_model.return_value = {
        'bc': MockOutput(np.array([[0, 0, 1]])),   # bass
        'ccf': MockOutput(np.array([[0, 1, 1]])),  # chord
        'kcrf': MockOutput(np.array([[1, 1, 1]]))  # key
    }
    model.model = mock_tf_model
    
    dummy_input = np.zeros((1, 100, 12)) 
    res = model.predict(dummy_input)
    
    # 結果として [bass, chord, key] のリストが返り、
    # 各要素が (1, 1, timesteps) の形状になっていることを確認する
    assert len(res) == 3
    assert res[0].shape == (1, 1, 3) # bass
    assert res[1].shape == (1, 1, 3) # chord
    assert res[2].shape == (1, 1, 3) # key
    
    # モックデータの中身が正しく反映されているか
    assert res[0][0, 0, 2] == 1  # bassのインデックス2は1になっているはず
