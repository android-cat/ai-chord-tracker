import pytest
import numpy as np
import sys
import os

# プロジェクトルートにパスを通す
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audio_processor import minmax, _get_root_index, convert_time, KEY_NAMES, TONES

def test_minmax():
    # 正常な[0, 1]に正規化されるかの確認
    x = np.array([[-5.0, 0.0, 5.0]])
    res = minmax(x, axis=1)
    assert np.allclose(res, [[0.0, 0.5, 1.0]]), "minmax should normalize to [0, 1]"

    # 最大最小が同じ場合（0除算回避）
    x2 = np.array([[2.0, 2.0]])
    res2 = minmax(x2, axis=1)
    assert np.allclose(res2, [[0.0, 0.0]]), "Div by zero should be handled gracefully"

def test_get_root_index():
    assert _get_root_index("C") == 0
    assert _get_root_index("Db") == 1
    assert _get_root_index("N.C.") is None
    assert _get_root_index("Gb") == 6
    assert _get_root_index("Am") == 9  # A is index 9
    assert _get_root_index("B") == 11
    
def test_convert_time(mocker):
    # dlchordx.Chordが動的インポートされるため、影響を受けないようにモック化する
    mocker.patch("audio_processor.Chord", None)

    # pred形式は [bass, chord, key]. それぞれ要素はshape=(1, 1, timesteps)を想定
    # 6フレームのデータを作成（最後に変化点を作って以前のブロックを吐き出させる）
    bass = np.array([[[0, 0, 0, 0, 0, 0]]])
    chord = np.array([[[0, 0, 0, 1, 1, 2]]])  # フレーム3でコード変化、フレーム5で終端変化
    pred = [bass, chord, None]
    
    chord_index = {"0": "C", "1": "G", "2": "N.C."}
    bins_per_second = 10.0  # 1フレームあたり0.1秒とする
    
    # 変換関数実行
    times = convert_time(pred, bins_per_second, chord_index, min_time=0.0)
    
    # [start_time, end_time, chord_name] のリストが返ることを期待
    assert isinstance(times, list)
    assert len(times) == 2  # C と G の2つのブロックに分かれるはず
    assert times[0] == [0.0, 0.3, "C"]  # frame0〜2が一つにまとまる
    assert times[1] == [0.3, 0.5, "G"]  # frame3のコード変化からframe5（終端での変化）まで
