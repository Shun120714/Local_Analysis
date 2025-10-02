# 仮想環境セットアップガイド

## 🐍 Python仮想環境について

このプロジェクトでは、Python 3.11.13の仮想環境を使用して、依存関係を分離し、安定した動作環境を提供します。

## 🚀 クイックスタート

### 1. 自動セットアップ (推奨)
```bash
# 仮想環境の作成と必要パッケージのインストール
./setup_venv.sh

# アプリケーションの起動
./start_venv.sh
```

### 2. 手動セットアップ
```bash
# 1. 仮想環境の作成
python3.11 -m venv venv_py311

# 2. 仮想環境のアクティベート
source venv_py311/bin/activate

# 3. pipのアップグレード
pip install --upgrade pip

# 4. 必要なパッケージのインストール
pip install -r requirements_minimal.txt

# 5. アプリケーションの起動
python app_optimized.py
```

## 📦 仮想環境の構成

### Python環境
- **バージョン**: Python 3.11.13
- **場所**: `venv_py311/`
- **メリット**: 安定性・互換性・分離性

### インストール済みパッケージ
```
xarray>=2025.9.1      # NetCDFファイル処理
netCDF4>=1.7.2        # NetCDF4ライブラリ
numpy>=2.3.3          # 数値計算
pandas>=2.3.3         # データフレーム操作
scipy>=1.16.2         # 科学計算 (KDTree等)
pyproj>=3.7.2         # 座標変換・投影処理
Flask>=3.1.2          # Webフレームワーク
Flask-Cors>=6.0.1     # CORS対応
PyYAML>=6.0.3         # YAML設定ファイル
pyarrow>=21.0.0       # Parquet形式サポート
dask>=2025.9.1        # 大規模データ処理
matplotlib>=3.10.6    # グラフ描画
```

## 🛠️ 日常的な使用方法

### アプリケーション起動
```bash
# 簡単起動（推奨）
./start_venv.sh

# 手動起動
source venv_py311/bin/activate
python app_optimized.py
```

### 仮想環境の管理
```bash
# 仮想環境のアクティベート
source venv_py311/bin/activate

# 仮想環境の非アクティベート
deactivate

# 現在の仮想環境確認
which python
python --version
```

### パッケージ管理
```bash
# インストール済みパッケージ一覧
pip list

# パッケージの追加インストール
pip install パッケージ名

# requirements.txtの更新
pip freeze > requirements_full.txt
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### Python 3.11が見つからない
```bash
# Homebrewでインストール (macOS)
brew install python@3.11

# 公式サイトからダウンロード
# https://www.python.org/downloads/
```

#### 仮想環境が作成できない
```bash
# 既存の仮想環境を削除して再作成
rm -rf venv_py311
python3.11 -m venv venv_py311
```

#### パッケージインストールでエラー
```bash
# pipを最新版にアップグレード
pip install --upgrade pip

# キャッシュクリア
pip cache purge

# 個別インストール
pip install パッケージ名 --no-cache-dir
```

#### アプリケーションが起動しない
```bash
# 仮想環境がアクティベートされているか確認
which python  # venv_py311/bin/python と表示されるべき

# 必要なファイルの存在確認
ls -la app_optimized.py extract.py variables.yml

# ポート8000が使用中の場合
lsof -ti:8000 | xargs kill -9
```

## 📊 環境比較

| 項目 | システムPython | 仮想環境 |
|------|---------------|----------|
| バージョン | 3.13.x | 3.11.13 |
| 安定性 | 新しいため不安定 | 実績あり安定 |
| 分離性 | システム全体に影響 | プロジェクト独立 |
| 管理 | 混在しやすい | 明確な管理 |
| 推奨度 | ❌ | ✅ |

## 🎯 推奨される開発フロー

1. **プロジェクト開始時**:
   ```bash
   ./setup_venv.sh
   ```

2. **日々の開発時**:
   ```bash
   ./start_venv.sh
   ```

3. **新しいパッケージが必要な時**:
   ```bash
   source venv_py311/bin/activate
   pip install 新しいパッケージ
   pip freeze > requirements_updated.txt
   ```

4. **他の人と共有時**:
   - `requirements_minimal.txt` を提供
   - `setup_venv.sh` で環境構築

## 📝 注意事項

- 仮想環境は `venv_py311/` ディレクトリ内に作成されます
- アプリケーション実行前に必ず仮想環境をアクティベートしてください
- 異なる環境間でのパッケージバージョン差異に注意
- Git管理では `venv_py311/` ディレクトリは除外することを推奨

---

この仮想環境セットアップにより、安定した開発・実行環境が確保されます。