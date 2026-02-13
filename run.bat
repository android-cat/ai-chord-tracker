@chcp 65001 >nul
@echo off
cd /d %~dp0

REM Pythonの確認
python --version >nul 2>&1
if errorlevel 1 (
    echo Pythonが見つからないか、PATHが通っていません。
    pause
    exit /b 1
)

REM 仮想環境の確認・作成
if not exist venv (
    echo 仮想環境を作成しています...
    python -m venv venv
)

REM 仮想環境の有効化
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo 仮想環境の有効化に失敗しました。
    pause
    exit /b 1
)

REM 依存ライブラリの確認（PySide6で簡易チェック）
pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo 依存ライブラリをインストールしています...
    pip install -r requirements.txt
)

REM アプリケーション実行
echo AI Chord Trackerを起動しています...
python main.py
pause
