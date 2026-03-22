import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from midi_export import _parse_chord, _get_chord_intervals

def test_parse_chord():
    assert _parse_chord("C") == ("C", "")
    assert _parse_chord("C#m7") == ("C#", "m7")
    assert _parse_chord("DbM7") == ("Db", "M7")
    assert _parse_chord("F") == ("F", "")
    assert _parse_chord("N.C.") == (None, None)
    assert _parse_chord("---") == (None, None)

def test_get_chord_intervals():
    # 基本のトライアド等
    assert _get_chord_intervals("") == [0, 4, 7] # Major
    assert _get_chord_intervals("m") == [0, 3, 7] # Minor
    
    # セブンスコード
    assert _get_chord_intervals("7") == [0, 4, 7, 10]
    assert _get_chord_intervals("m7") == [0, 3, 7, 10]
    assert _get_chord_intervals("M7") == [0, 4, 7, 11]
    
    # ディミニッシュ、オーギュメント
    assert _get_chord_intervals("dim") == [0, 3, 6]
    assert _get_chord_intervals("aug") == [0, 4, 8]
    
    # エクステンションコード (9th) のフォールバック確認
    assert _get_chord_intervals("m9") == [0, 3, 7, 10, 14]
    assert _get_chord_intervals("9") == [0, 4, 7, 10, 14]
    assert _get_chord_intervals("M7(9)") == [0, 4, 7, 11, 14]
