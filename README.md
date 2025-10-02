# NetCDF気象データ抽出プログラム

Lambert Conformal Conic投影のNetCDFファイルから気象データを抽出するPython 3.11.5対応プログラムです。
コマンドライン版とWebブラウザ版の両方を提供しています。

## 💻 動作確認済み環境

- **macOS** 14+ (M1/M2チップ対応) ✅
- **Ubuntu** 20.04+ ✅  
- **CentOS** 8+ ✅
- **Windows** 10/11 ✨新サポート ✅

Python 3.11以上が必要です。

**動作確認コマンド：**
```bash
python3 check_platform.py  # macOS/Linux
python check_platform.py   # Windows
```

## 🌐 Webインターフェース版

### 特徴
- **インタラクティブマップ**: Leaflet.jsによる直感的な地点選択
- **リアルタイムグラフ**: Chart.jsによる時系列データの可視化
- **格子点可視化**: MSM格子点の表示と密度制御
- **赤点表示**: データ抽出に使用した格子点のハイライト表示

### 🚀 クイックスタート

#### macOS/Linux
1. **アプリケーションを起動**：
```bash
cd /Users/ishizu/Desktop/Local_Analysis
python3 app_optimized.py
```

#### Windows
1. **アプリケーションを起動**：
```cmd
cd C:\path\to\Local_Analysis
python app_optimized.py
```

#### 仮想環境使用（推奨）

**macOS/Linux:**
```bash
./start_venv.sh
```

**Windows:**
```cmd
start_venv.bat
```

**PowerShell:**
```powershell
.\start_venv.ps1
```

2. **ブラウザでアクセス**：
```
http://localhost:8000
```

### 📊 主要機能

#### マップ機能
- **地点選択**: マップクリックで緯度・経度を自動入力
- **格子点表示**: 633×521 MSM格子点の可視化
- **密度制御**: ズームレベルに応じた表示密度の自動調整
- **使用格子点表示**: 抽出に使用した格子点を赤色でハイライト

#### データ抽出機能
- **抽出方法**: 
  - `最近傍`: 最も近い1点を選択
  - `平均化`: 指定範囲内の格子点を平均
- **平均化オプション**:
  - 半径指定（km）
  - k近傍点数指定
- **データタイプ**: 地表面データ・等圧面データ
- **変数選択**: 気温・湿度・風・気圧など
- **時間選択**: 単一時刻・時間範囲

#### 可視化機能
- **テーブル表示**: 抽出データの詳細表示
- **時系列グラフ**: 自動的な折れ線グラフ生成（JSON表示時）
- **マルチグラフ**: 各変数ごとの個別グラフ
- **日本語対応**: グラフタイトル・軸ラベルの日本語表示

#### 出力形式
- **JSON**: ブラウザ表示 + グラフ描画
- **CSV**: ファイルダウンロード

## 💻 コマンドライン版

### 機能

#### 抽出対象データ
- **地上データ**: 気温・相対湿度・風（u/v成分と風速/風向）・気圧
- **等圧面データ**: 気温・相対湿度・風（u/v成分と風速/風向）・ジオポテンシャル高度

#### 地点選択方法
- `nearest`: 最も近い格子点1点を選択
- `mean`: 近傍の格子点を平均化
  - `--radius-km`: 指定半径（km）内の全格子点を平均
  - `--k-neighbors`: k個の最近傍格子点を平均

#### 時間選択
- `--time`: 単一時刻での抽出
- `--time-start`/`--time-end`: 時間範囲での抽出

#### 気圧面選択
- `--levels`: 抽出する気圧面レベル（hPa）を指定

#### 出力形式
- Parquet形式（推奨）またはCSV形式
- 単位変換：温度（K→°C）、湿度（0-1→%）、気圧（Pa→hPa）

### 必要なライブラリ

```bash
pip install xarray netCDF4 numpy pandas pyproj scipy pyyaml pyarrow dask flask
```

### 使用方法

#### 基本的な使用例

##### 1. 地上データ（単一時刻・最近傍）
```bash
python extract.py --lat 35.0 --lon 139.0 --time 2024-07-03T12:00:00 --surface --method nearest --out surface_data.parquet
```

##### 2. 等圧面データ（単一時刻・最近傍）
```bash
python extract.py --lat 35.0 --lon 139.0 --time 2024-07-03T12:00:00 --levels 1000 850 500 300 100 --isobaric --method nearest --out isobaric_data.parquet
```

##### 3. 時間範囲での抽出（半径平均）
```bash
python extract.py --lat 35.0 --lon 139.0 --time-start 2024-07-03T00:00:00 --time-end 2024-07-03T23:00:00 --surface --method mean --radius-km 10 --out surface_timeseries.parquet
```

##### 4. k近傍平均での抽出
```bash
python extract.py --lat 35.0 --lon 139.0 --time 2024-07-03T12:00:00 --levels 1000 850 500 --isobaric --method mean --k-neighbors 5 --out isobaric_knn.parquet
```

## 📋 出力データ形式

### 地上データ
| カラム名 | 説明 | 単位 |
|----------|------|------|
| time | 時刻 | - |
| lat | 緯度 | 度 |
| lon | 経度 | 度 |
| method | 抽出方法 | - |
| n_points | 使用格子点数 | - |
| tas_C | 気温 | °C |
| rh_% | 相対湿度 | % |
| u_ms | 風のu成分 | m/s |
| v_ms | 風のv成分 | m/s |
| ps_hPa | 気圧 | hPa |
| wind_speed_ms | 風速 | m/s |
| wind_direction_deg | 風向 | 度 |

### 等圧面データ
| カラム名 | 説明 | 単位 |
|----------|------|------|
| time | 時刻 | - |
| lat | 緯度 | 度 |
| lon | 経度 | 度 |
| level_hPa | 気圧面 | hPa |
| method | 抽出方法 | - |
| n_points | 使用格子点数 | - |
| ta_C | 気温 | °C |
| rh_% | 相対湿度 | % |
| u_ms | 風のu成分 | m/s |
| v_ms | 風のv成分 | m/s |
| z_gpm | ジオポテンシャル高度 | gpm |
| wind_speed_ms | 風速 | m/s |
| wind_direction_deg | 風向 | 度 |

## ⚙️ 設定ファイル

### variables.yml
変数名マッピングを定義します。データセット内の変数名を論理名にマップします。

```yaml
surface:
  air_temperature: "TMP_1D5maboveground"
  relative_humidity: "RH_1D5maboveground"
  u_wind: "UGRD_10maboveground"
  v_wind: "VGRD_10maboveground"
  surface_pressure: "PRMSL_meansealevel"

isobaric:
  air_temperature: "TMP_{level}mb"
  relative_humidity: "RH_{level}mb"
  u_wind: "UGRD_{level}mb"
  v_wind: "VGRD_{level}mb"
  geopotential_height: "HGT_{level}mb"
```

## 🗺️ 座標系について

- **水平座標**: Lambert Conformal Conic投影
  - MSM格子系（633×521）、5km解像度
  - 標準緯線: 30°N, 60°N
  - 中央経線: 140°E
  - 基準点: (140°E, 30°N) = 格子[360, 448]
- **鉛直座標**: 等圧面座標（hPa）
- **時間座標**: 1時間間隔（JST）

## ⚠️ 重要な注意事項

### 時間指定について（JST対応）

**重要**: 全ての時間指定は**JST（日本標準時、UTC+9）**で行います。

- NetCDFファイルの時間データはJSTとして解釈されます
- 入力時刻もJSTで指定してください
- 時間フィルタリング時もJSTベースで処理されます

例：
```bash
--start_time "2024-07-03T09:00"  # JST 2024年7月3日 9時
--end_time "2024-07-03T21:00"    # JST 2024年7月3日 21時
```

### その他の注意事項

1. **ファイル破損**: サイズが小さすぎるファイル（<1MB）は自動的に除外されます
2. **投影変換**: Lambert Conformal Conic投影パラメータは格子の範囲から自動推定されます
3. **時間フィルタリング**: ファイル名から時刻を抽出して時間範囲でフィルタリングします
4. **メモリ使用量**: 大量のファイルを読み込む場合は`--chunks`オプションでチャンクサイズを調整してください

## 🔧 トラブルシューティング

### よくあるエラー

1. **"Variable not found"**: `variables.yml`の設定を確認してください
2. **"No valid NetCDF files"**: ファイルパスとファイル形式を確認してください
3. **"Memory error"**: チャンクサイズを小さくするか、時間範囲を狭めてください
4. **"Address already in use"**: 既存のプロセスを終了してください：`lsof -ti:8000 | xargs kill -9`

### デバッグ

```bash
# 詳細ログを出力
python extract.py --verbose [other options]

# 変数確認のみ実行
python extract.py --dry-run [other options]
```

## 👨‍💻 開発者向け情報

### アーキテクチャ
- **Webインターフェース**: Flask + HTML/CSS/JavaScript
- **データ処理**: xarray + pandas + scipy
- **可視化**: Chart.js + Leaflet.js
- **空間処理**: scipy.spatial.cKDTree

### 主要クラス
- `ProjectionHandler`: Lambert Conformal Conic投影の処理
- `VariableMapper`: 変数名マッピングの処理
- `GridPointSelector`: 格子点選択とKDTree処理
- `DataExtractor`: データ抽出の統合処理

### 主要ライブラリ
- `xarray`: NetCDFファイル読み込み・処理
- `pyproj`: 座標変換
- `scipy.spatial.cKDTree`: 最近傍検索
- `pandas`: データフレーム操作
- `flask`: Webアプリケーションフレームワーク

### APIエンドポイント
- `GET /`: Webインターフェース
- `POST /api/extract`: データ抽出
- `GET /api/available_variables`: 利用可能変数一覧
- `GET /api/available_levels`: 利用可能気圧面一覧
- `GET /api/grid_points`: 格子点情報（密度制御付き）
- `GET /api/all_grid_points`: 全格子点情報
- `GET /api/nearby_grid_points`: 近傍格子点検索

## 📈 最新の改善点

### v2.0 (2025年10月)
- ✅ インタラクティブなWebインターフェース追加
- ✅ リアルタイム時系列グラフ描画機能
- ✅ MSM格子点の可視化と密度制御
- ✅ 使用格子点の赤色ハイライト表示
- ✅ 平均化機能の距離計算修正
- ✅ 格子範囲表示機能の削除（UI簡素化）

### システム要件
- Python 3.11.5以上
- 8GB以上のRAM推奨
- ブラウザ: Chrome/Firefox/Safari最新版
- ネットワーク: ローカル環境での動作