@echo off
REM ===================================================================
REM 気象データ抽出システム - Windows用セットアップスクリプト
REM Python 3.11仮想環境の自動セットアップ
REM ===================================================================

echo 🛠️  Python 3.11 仮想環境セットアップ (Windows)
echo.

REM Python 3.11の存在確認
python -c "import sys; print('Python version:', sys.version)" 2>nul
if %ERRORLEVEL% neq 0 (
    echo ❌ Pythonが見つかりません。Python 3.11をインストールしてください。
    echo 💡 インストール方法: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Python バージョン確認
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python が利用可能: %PYTHON_VERSION%

REM 仮想環境の作成
if not exist "venv_py311" (
    echo 📦 Python 3.11仮想環境を作成中...
    python -m venv venv_py311
    if %ERRORLEVEL% neq 0 (
        echo ❌ 仮想環境の作成に失敗しました
        pause
        exit /b 1
    )
    echo ✅ 仮想環境が作成されました: venv_py311\
) else (
    echo ✅ 仮想環境は既に存在します: venv_py311\
)

REM 仮想環境のアクティベート
echo 🔧 仮想環境をアクティベート中...
call venv_py311\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ❌ 仮想環境のアクティベートに失敗しました
    pause
    exit /b 1
)

REM pipのアップグレード
echo 📥 pipを最新版にアップグレード中...
python -m pip install --upgrade pip

REM 必要なパッケージのインストール
if exist "requirements_minimal.txt" (
    echo 📦 必要なパッケージをインストール中...
    pip install -r requirements_minimal.txt
    if %ERRORLEVEL% neq 0 (
        echo ❌ パッケージのインストールに失敗しました
        pause
        exit /b 1
    )
    echo ✅ パッケージのインストール完了
) else (
    echo ❌ requirements_minimal.txt が見つかりません
    pause
    exit /b 1
)

REM インストール済みパッケージの確認
echo.
echo 📋 インストール済みパッケージ (主要なもの):
python -c "
import pkg_resources
import sys

packages = ['xarray', 'netCDF4', 'numpy', 'pandas', 'scipy', 'pyproj', 'flask', 'PyYAML', 'pyarrow', 'dask', 'matplotlib']

for package in packages:
    try:
        version = pkg_resources.get_distribution(package).version
        print(f'  ✅ {package}: {version}')
    except pkg_resources.DistributionNotFound:
        print(f'  ❌ {package}: Not installed')
"

echo.
echo 🎉 セットアップ完了！
echo.
echo 📝 使用方法:
echo   起動: start_venv.bat
echo   または: venv_py311\Scripts\activate.bat ^&^& python app_optimized.py
echo.
echo 🌐 アクセスURL: http://localhost:8000
echo.
pause