# AI Chord Tracker

音声ファイルからコード（和音）を自動推定し、タイムライン表示・再生を行うデスクトップアプリケーションです。

このプロジェクトは、[anime-song/auto-chord-tracker](https://github.com/anime-song/auto-chord-tracker) で公開されている学習済みモデル (`chord_estimation_model.h5`) を使用させていただいており、android-cat によって開発・メンテナンスされています。

## 機能

- 音声ファイル（WAV, MP3, FLAC 等）からコードを自動解析
- 波形表示とコードタイムラインの同期表示
- 再生 / 逆再生 / 停止 / シーク操作
- 433種類のコードタイプ + ベース音の推定（N.C. 含む）
- モダンな PySide6 ベースの GUI

## 必要環境

- Python 3.10 以上
- Windows / macOS / Linux

## セットアップ

```bash
# リポジトリをクローン後、プロジェクトディレクトリへ移動
cd ai-chord-tracker

# 仮想環境を作成・有効化
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 依存パッケージをインストール
pip install -r requirements.txt
```

## 使い方

```bash
python main.py
```

1. アプリが起動したら、音声ファイルを開きます
2. 自動的にコード解析が実行されます
3. タイムライン上にコードが表示され、再生しながら確認できます

## プロジェクト構成

```
ai-chord-tracker/
├── main.py                # アプリケーションのエントリーポイント
├── audio_processor.py     # 音声読み込み・CQT前処理・コード変換
├── chord_model.py         # Kerasモデルの読み込みと推論
├── player.py              # sounddevice による音声再生エンジン
├── index.json             # コードインデックス（ID → コード名）
├── requirements.txt       # Python 依存パッケージ
├── model/
│   └── chord_estimation_model.h5  # 学習済みコード推定モデル
└── ui/
    ├── __init__.py
    ├── main_window.py     # メインウィンドウ
    ├── player_controls.py # 再生コントロール UI
    ├── styles.py          # スタイルシート
    ├── timeline_widget.py # コードタイムライン表示
    └── waveform_widget.py # 波形表示ウィジェット
```

## 依存パッケージ

| パッケージ | 用途 |
|---|---|
| PySide6 | GUI フレームワーク |
| TensorFlow | ディープラーニング推論 |
| librosa | 音声読み込み・CQT 計算 |
| NumPy | 数値計算 |
| sounddevice | 音声再生 |
| soundfile | 音声ファイル I/O |

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。詳細は [LICENSE](LICENSE) および [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) を参照してください。
