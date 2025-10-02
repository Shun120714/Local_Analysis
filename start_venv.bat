@echo off
REM ===================================================================
REM 気象データ抽出システム - Windows用起動スクリプト
REM Python 3.11仮想環境でアプリケーションを起動
REM ===================================================================

title 気象データ抽出システム v2.0

echo 🌤️  気象データ抽出システム v2.0 を起動中... (Windows)
echo 📍 プロジェクトディレクトリ: %CD%
echo.

REM 仮想環境の存在確認
if not exist "venv_py311" (
    echo ❌ 仮想環境が見つかりません。セットアップを実行してください。
    echo    セットアップ方法: setup_venv.bat
    echo.
    pause
    exit /b 1
)

echo 🐍 Python 3.11 仮想環境をアクティベート中...
call venv_py311\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ❌ 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)

echo 📦 Python環境情報:
for /f "tokens=*" %%i in ('python --version') do echo    バージョン: %%i
for /f "tokens=*" %%i in ('where python') do echo    実行ファイル: %%i
echo.

echo 🔍 必要なライブラリの確認...
python -c "
try:
    import xarray, netCDF4, numpy, pandas, scipy, pyproj, flask
    print('✅ すべての必要なライブラリが利用可能です')
except ImportError as e:
    print(f'❌ 必要なライブラリが不足しています: {e}')
    print('📥 セットアップを再実行してください: setup_venv.bat')
    input('Enterキーを押して終了...')
    exit(1)
"

if %ERRORLEVEL% neq 0 (
    echo 📥 必要なパッケージをインストールしてください:
    echo    pip install -r requirements_minimal.txt
    echo.
    pause
    exit /b 1
)

echo 🚀 アプリケーションを起動中...
echo    アクセスURL: http://localhost:8000
echo    停止方法: Ctrl+C
echo.
echo ⚠️  注意: このウィンドウを閉じるとアプリケーションが停止します
echo.

python app_optimized.py

echo.
echo 🛑 アプリケーションが停止しました
pause