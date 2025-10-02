# ===================================================================
# 気象データ抽出システム - Windows PowerShell用セットアップスクリプト
# Python 3.11仮想環境の自動セットアップ
# ===================================================================

Write-Host "🛠️  Python 3.11 仮想環境セットアップ (PowerShell)" -ForegroundColor Cyan
Write-Host ""

# 実行ポリシーの確認
$executionPolicy = Get-ExecutionPolicy
if ($executionPolicy -eq "Restricted") {
    Write-Host "⚠️  PowerShellの実行ポリシーが制限されています" -ForegroundColor Yellow
    Write-Host "   以下のコマンドを管理者権限で実行してください:" -ForegroundColor Yellow
    Write-Host "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor White
    Write-Host ""
    Read-Host "Enterキーを押して終了..."
    exit 1
}

# Python 3.11の存在確認
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Host "✅ Python が利用可能: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Pythonが見つかりません。Python 3.11をインストールしてください。" -ForegroundColor Red
    Write-Host "💡 インストール方法: https://www.python.org/downloads/" -ForegroundColor Blue
    Read-Host "Enterキーを押して終了..."
    exit 1
}

# 仮想環境の作成
if (-not (Test-Path "venv_py311")) {
    Write-Host "📦 Python 3.11仮想環境を作成中..." -ForegroundColor Yellow
    python -m venv venv_py311
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ 仮想環境の作成に失敗しました" -ForegroundColor Red
        Read-Host "Enterキーを押して終了..."
        exit 1
    }
    Write-Host "✅ 仮想環境が作成されました: venv_py311\" -ForegroundColor Green
} else {
    Write-Host "✅ 仮想環境は既に存在します: venv_py311\" -ForegroundColor Green
}

# 仮想環境のアクティベート
Write-Host "🔧 仮想環境をアクティベート中..." -ForegroundColor Yellow
& "venv_py311\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ 仮想環境のアクティベートに失敗しました" -ForegroundColor Red
    Read-Host "Enterキーを押して終了..."
    exit 1
}

# pipのアップグレード
Write-Host "📥 pipを最新版にアップグレード中..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# 必要なパッケージのインストール
if (Test-Path "requirements_minimal.txt") {
    Write-Host "📦 必要なパッケージをインストール中..." -ForegroundColor Yellow
    pip install -r requirements_minimal.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ パッケージのインストールに失敗しました" -ForegroundColor Red
        Read-Host "Enterキーを押して終了..."
        exit 1
    }
    Write-Host "✅ パッケージのインストール完了" -ForegroundColor Green
} else {
    Write-Host "❌ requirements_minimal.txt が見つかりません" -ForegroundColor Red
    Read-Host "Enterキーを押して終了..."
    exit 1
}

# インストール済みパッケージの確認
Write-Host ""
Write-Host "📋 インストール済みパッケージ (主要なもの):" -ForegroundColor Cyan
python -c @"
import pkg_resources

packages = ['xarray', 'netCDF4', 'numpy', 'pandas', 'scipy', 'pyproj', 'flask', 'PyYAML', 'pyarrow', 'dask', 'matplotlib']

for package in packages:
    try:
        version = pkg_resources.get_distribution(package).version
        print(f'  ✅ {package}: {version}')
    except pkg_resources.DistributionNotFound:
        print(f'  ❌ {package}: Not installed')
"@

Write-Host ""
Write-Host "🎉 セットアップ完了！" -ForegroundColor Green
Write-Host ""
Write-Host "📝 使用方法:" -ForegroundColor Cyan
Write-Host "  起動: .\start_venv.ps1" -ForegroundColor White
Write-Host "  または: .\venv_py311\Scripts\Activate.ps1; python app_optimized.py" -ForegroundColor White
Write-Host ""
Write-Host "🌐 アクセスURL: http://localhost:8000" -ForegroundColor Blue
Write-Host ""
Read-Host "Enterキーを押して終了..."