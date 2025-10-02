# Windows用セットアップガイド

## 🪟 MSM気象データ抽出システム v2.0 - Windows版

このシステムはWindows環境でもご利用いただけます。以下の手順でセットアップ・起動してください。

## 📋 必要な環境

### システム要件
- **OS**: Windows 10/11 (64bit)
- **メモリ**: 8GB以上推奨
- **ストレージ**: 5GB以上の空き容量
- **Python**: 3.11以上

### 必要なソフトウェア
- **Python 3.11+**: [公式サイト](https://www.python.org/downloads/)からダウンロード
- **Git** (オプション): [Git for Windows](https://git-scm.com/download/win)

## 🚀 クイックスタート

### 1. リポジトリの取得
```cmd
# Git使用の場合
git clone https://github.com/Shun120714/Local_Analysis.git
cd Local_Analysis

# または、ZIPファイルをダウンロードして展開
```

### 2. NetCDFデータの配置
```
use_nc/
├── LANAL_2024070300.nc
├── LANAL_2024070301.nc
├── LANAL_2024070302.nc
└── ...
```

### 3. 自動セットアップ（推奨）

#### 方法A: バッチファイル使用
```cmd
# コマンドプロンプトで実行
setup_venv.bat
```

#### 方法B: PowerShell使用
```powershell
# PowerShellで実行
.\setup_venv.ps1
```

### 4. アプリケーション起動

#### 方法A: バッチファイル使用
```cmd
start_venv.bat
```

#### 方法B: PowerShell使用
```powershell
.\start_venv.ps1
```

## 🔧 詳細セットアップ手順

### Python環境の確認
```cmd
python --version
```
Python 3.11以上が表示されることを確認してください。

### 手動セットアップ（上級者向け）
```cmd
# 1. 仮想環境作成
python -m venv venv_py311

# 2. 仮想環境アクティベート
venv_py311\Scripts\activate.bat

# 3. パッケージインストール
pip install -r requirements_minimal.txt

# 4. アプリケーション起動
python app_optimized.py
```

## 🌐 アクセス方法

アプリケーション起動後、Webブラウザで以下のURLにアクセス：
```
http://localhost:8000
```

## 📁 ファイル構成

### Windows用スクリプト
- `setup_venv.bat` - バッチファイル版セットアップ
- `start_venv.bat` - バッチファイル版起動スクリプト
- `setup_venv.ps1` - PowerShell版セットアップ
- `start_venv.ps1` - PowerShell版起動スクリプト

### Linux/macOS用スクリプト
- `setup_venv.sh` - Unix系セットアップスクリプト
- `start_venv.sh` - Unix系起動スクリプト

## ⚠️ トラブルシューティング

### PowerShell実行ポリシーエラー
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Pythonが見つからない場合
1. [Python公式サイト](https://www.python.org/downloads/)からPython 3.11+をダウンロード
2. インストール時に「Add Python to PATH」にチェック
3. コマンドプロンプトを再起動

### パッケージインストールエラー
```cmd
# pipのアップグレード
python -m pip install --upgrade pip

# Microsoftビルドツールのインストール（必要に応じて）
# https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

### ポート8000が使用中の場合
```cmd
# プロセスの確認
netstat -ano | findstr 8000

# プロセスの強制終了
taskkill /PID <プロセスID> /F
```

## 🔒 セキュリティ注意事項

- **開発サーバー**: 本システムは開発用サーバーです
- **ローカル使用**: localhost（127.0.0.1）でのみ動作
- **ファイアウォール**: 外部からのアクセスは自動的にブロックされます

## 📊 パフォーマンス最適化

### Windows固有の設定
- **Windows Defender**: プロジェクトフォルダをスキャン対象から除外
- **メモリ**: 大量データ処理時は8GB以上のRAM推奨
- **ストレージ**: SSDでの動作を推奨

## 🆘 サポート

### よくある質問
1. **Q**: 起動が遅い
   **A**: Windows Defenderのリアルタイム保護を一時無効化

2. **Q**: グラフが表示されない
   **A**: JSON形式での出力を選択していることを確認

3. **Q**: NetCDFファイルエラー
   **A**: ファイルサイズが1MB以上であることを確認

### ログファイル確認
```cmd
# アプリケーションログ
type app.log

# Pythonエラーログ
# コンソール出力を確認
```

## 🔄 アップデート方法

```cmd
# Git使用の場合
git pull origin main

# 依存関係の更新
venv_py311\Scripts\activate.bat
pip install -r requirements_minimal.txt --upgrade
```

---

## 📋 まとめ

Windows環境でのMSM気象データ抽出システムは、自動セットアップスクリプトにより簡単に利用開始できます。バッチファイルまたはPowerShellスクリプトを使用して、数分でシステムを起動可能です。

**推奨環境**:
- Windows 10/11 64bit
- Python 3.11+
- 8GB以上のRAM
- SSDストレージ