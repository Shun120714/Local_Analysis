# ===================================================================
# 気象データ抽出システム - Windows PowerShell用起動スクリプト
# Python 3.11仮想環境でアプリケーションを起動
# ===================================================================

$Host.UI.RawUI.WindowTitle = "気象データ抽出システム v2.0"

Write-Host "🌤️  気象データ抽出システム v2.0 を起動中... (PowerShell)" -ForegroundColor Cyan
Write-Host "📍 プロジェクトディレクトリ: $(Get-Location)" -ForegroundColor White
Write-Host ""

# 仮想環境の存在確認
if (-not (Test-Path "venv_py311")) {
    Write-Host "❌ 仮想環境が見つかりません。セットアップを実行してください。" -ForegroundColor Red
    Write-Host "   セットアップ方法: .\setup_venv.ps1" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Enterキーを押して終了..."
    exit 1
}

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

Write-Host "🐍 Python 3.11 仮想環境をアクティベート中..." -ForegroundColor Yellow
try {
    & "venv_py311\Scripts\Activate.ps1"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to activate virtual environment"
    }
} catch {
    Write-Host "❌ 仮想環境のアクティベートに失敗しました" -ForegroundColor Red
    Read-Host "Enterキーを押して終了..."
    exit 1
}

Write-Host "📦 Python環境情報:" -ForegroundColor Cyan
$pythonVersion = python --version
$pythonPath = (Get-Command python).Source
Write-Host "   バージョン: $pythonVersion" -ForegroundColor White
Write-Host "   実行ファイル: $pythonPath" -ForegroundColor White
Write-Host ""

Write-Host "🔍 必要なライブラリの確認..." -ForegroundColor Yellow
python -c @"
try:
    import xarray, netCDF4, numpy, pandas, scipy, pyproj, flask
    print('✅ すべての必要なライブラリが利用可能です')
except ImportError as e:
    print(f'❌ 必要なライブラリが不足しています: {e}')
    print('📥 セットアップを再実行してください: setup_venv.ps1')
    input('Enterキーを押して終了...')
    exit(1)
"@

if ($LASTEXITCODE -ne 0) {
    Write-Host "📥 必要なパッケージをインストールしてください:" -ForegroundColor Yellow
    Write-Host "   pip install -r requirements_minimal.txt" -ForegroundColor White
    Write-Host ""
    Read-Host "Enterキーを押して終了..."
    exit 1
}

Write-Host "🚀 アプリケーションを起動中..." -ForegroundColor Green
Write-Host "   アクセスURL: http://localhost:8000" -ForegroundColor Blue
Write-Host "   停止方法: Ctrl+C" -ForegroundColor White
Write-Host ""
Write-Host "⚠️  注意: このウィンドウを閉じるとアプリケーションが停止します" -ForegroundColor Yellow
Write-Host ""

try {
    python app_optimized.py
} catch {
    Write-Host "❌ アプリケーションの起動に失敗しました" -ForegroundColor Red
} finally {
    Write-Host ""
    Write-Host "🛑 アプリケーションが停止しました" -ForegroundColor Yellow
    Read-Host "Enterキーを押して終了..."
}