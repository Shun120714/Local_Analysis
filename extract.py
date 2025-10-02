#!/usr/bin/env python3
"""
気象データ抽出プログラム - 日本域ローカル解析データ(LANAL)用
NetCDFファイルから指定地点・時刻の気象データを抽出し、風速・風向も計算します。
"""

import sys
import logging
import argparse
import warnings
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional, Union, Any
import fnmatch

import numpy as np
import pandas as pd
import xarray as xr
import yaml
from pyproj import CRS, Transformer
from scipy.spatial import cKDTree

# 警告を制御
warnings.filterwarnings('ignore', category=RuntimeWarning)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def calculate_wind_speed_direction(u: np.ndarray, v: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    U成分とV成分から風速と風向を計算
    
    Args:
        u: 風のU成分 (東西成分、東が正)
        v: 風のV成分 (南北成分、北が正)
        
    Returns:
        wind_speed: 風速 (m/s)
        wind_direction: 風向 (度、北が0度、時計回り)
    """
    # 風速計算 (ピタゴラスの定理)
    wind_speed = np.sqrt(u**2 + v**2)
    
    # 風向計算 (風が吹いてくる方向)
    # atan2で角度を計算し、気象学的風向に変換
    wind_direction = (np.degrees(np.arctan2(-u, -v)) + 360) % 360
    
    return wind_speed, wind_direction

def add_wind_calculations(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrameにU成分とV成分がある場合、風速と風向を追加計算
    
    Args:
        df: 気象データのDataFrame
        
    Returns:
        風速・風向が追加されたDataFrame
    """
    df_result = df.copy()
    
    # 地上風の計算（カラム名を修正）
    if 'u_ms' in df.columns and 'v_ms' in df.columns:
        wind_speed, wind_direction = calculate_wind_speed_direction(
            df['u_ms'].values, df['v_ms'].values
        )
        df_result['wind_speed'] = wind_speed
        df_result['wind_direction'] = wind_direction
    
    # 等圧面風の計算（レベル別）
    u_cols = [col for col in df.columns if col.startswith('u_') and ('hPa' in col or col.endswith('_C'))]
    
    for u_col in u_cols:
        # 対応するV成分のカラム名を生成
        v_col = u_col.replace('u_', 'v_')
        
        if v_col in df.columns:
            # カラム名からレベルを抽出
            if 'hPa' in u_col:
                level_part = u_col.replace('u_', '').replace('hPa', '')
                speed_col = f'wind_speed_{level_part}hPa'
                dir_col = f'wind_direction_{level_part}hPa'
            else:
                # 地上風のパターン
                level_part = u_col.replace('u_', '')
                speed_col = f'wind_speed_{level_part}'
                dir_col = f'wind_direction_{level_part}'
            
            wind_speed, wind_direction = calculate_wind_speed_direction(
                df[u_col].values, df[v_col].values
            )
            df_result[speed_col] = wind_speed
            df_result[dir_col] = wind_direction
    
    return df_result


class ProjectionHandler:
    """投影座標系の変換を処理するクラス"""
    
    def __init__(self, ds: xr.Dataset):
        """
        データセットから投影情報を取得して初期化
        
        Args:
            ds: xarray Dataset
        """
        self.ds = ds
        self.transformer = None
        self._setup_projection()
    
    def _setup_projection(self):
        """投影情報を設定 - 正確なLambert Conformal Conic投影"""
        # 気象庁MSMモデルの正確なパラメータ
        self.standard_parallel_1 = 30.0  # 30°N
        self.standard_parallel_2 = 60.0  # 60°N
        self.central_meridian = 140.0    # 140°E
        self.reference_latitude = 30.0   # 30°N
        self.grid_spacing = 5000.0       # 5000m
        
        # 基準点の格子座標（1-based → 0-based）
        self.reference_grid_x = 449 - 1  # 448 (0-based)
        self.reference_grid_y = 361 - 1  # 360 (0-based)
        
        # 基準点の地理座標
        self.reference_lon = 140.0
        self.reference_lat = 30.0
        
        logger.info(f"MSM Lambert Conformal Conic projection configured")
        logger.info(f"Standard parallels: {self.standard_parallel_1}°N, {self.standard_parallel_2}°N")
        logger.info(f"Central meridian: {self.central_meridian}°E")
        logger.info(f"Reference point: ({self.reference_lon}°E, {self.reference_lat}°N) = grid[{self.reference_grid_y}, {self.reference_grid_x}]")
        logger.info(f"Grid spacing: {self.grid_spacing}m")
    
    def latlon_to_projection(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        緯度経度を投影座標（メートル）に変換
        MSM Lambert Conformal Conic投影を使用
        """
        import math
        
        # 地球の半径（メートル）
        R = 6371000.0
        
        # ラジアンに変換
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        central_meridian_rad = math.radians(self.central_meridian)
        sp1_rad = math.radians(self.standard_parallel_1)
        sp2_rad = math.radians(self.standard_parallel_2)
        ref_lat_rad = math.radians(self.reference_latitude)
        ref_lon_rad = math.radians(self.reference_lon)
        
        # Lambert Conformal Conic投影の計算
        if abs(self.standard_parallel_1 - self.standard_parallel_2) < 1e-10:
            # 単一基準緯度の場合
            n = math.sin(sp1_rad)
        else:
            # 二重基準緯度の場合
            n = (math.log(math.cos(sp1_rad)) - math.log(math.cos(sp2_rad))) / \
                (math.log(math.tan(math.pi/4 + sp2_rad/2)) - math.log(math.tan(math.pi/4 + sp1_rad/2)))
        
        F = math.cos(sp1_rad) * (math.tan(math.pi/4 + sp1_rad/2))**n / n
        
        # 基準点での投影座標
        rho_ref = R * F / (math.tan(math.pi/4 + ref_lat_rad/2))**n
        
        # 目標点での投影座標
        rho = R * F / (math.tan(math.pi/4 + lat_rad/2))**n
        theta = n * (lon_rad - central_meridian_rad)
        
        # 基準点との相対位置（メートル）
        x = rho * math.sin(theta) - rho_ref * math.sin(n * (ref_lon_rad - central_meridian_rad))
        y = rho_ref * math.cos(n * (ref_lon_rad - central_meridian_rad)) - rho * math.cos(theta)
        
        return x, y


class VariableMapper:
    """変数名マッピングを処理するクラス"""
    
    def __init__(self, config_path: str = "variables.yml"):
        """
        変数マッピング設定を読み込み
        
        Args:
            config_path: 設定ファイルパス
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """設定ファイルを読み込み"""
        if not self.config_path.exists():
            logger.warning(f"設定ファイルが見つかりません: {self.config_path}")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"変数マッピング設定を読み込みました: {self.config_path}")
            return config
        except Exception as e:
            logger.error(f"設定ファイル読み込みエラー: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            'surface': {
                'air_temperature': 'TMP_1D5maboveground',
                'relative_humidity': 'RH_1D5maboveground',
                'u_wind': 'UGRD_10maboveground',
                'v_wind': 'VGRD_10maboveground',
                'surface_pressure': 'PRMSL_meansealevel'
            },
            'isobaric': {
                'air_temperature': 'TMP_{level}mb',
                'relative_humidity': 'RH_{level}mb',
                'u_wind': 'UGRD_{level}mb',
                'v_wind': 'VGRD_{level}mb',
                'geopotential_height': 'HGT_{level}mb'
            }
        }
    
    def get_variable_name(self, ds: xr.Dataset, logical_name: str, 
                         var_type: str, level: Optional[int] = None) -> Optional[str]:
        """
        論理名から実際の変数名を取得
        
        Args:
            ds: データセット
            logical_name: 論理的な変数名
            var_type: 'surface' または 'isobaric'
            level: 気圧面レベル（hPa）
            
        Returns:
            実際の変数名、見つからない場合はNone
        """
        # 設定ファイルから変数名を取得
        if var_type in self.config:
            var_map = self.config[var_type]
            if logical_name in var_map:
                var_name = var_map[logical_name]
                
                # レベルのプレースホルダーを置換
                if level is not None:
                    var_name = var_name.replace('{level}', str(level))
                
                # データセットに存在するかチェック
                if var_name in ds.data_vars:
                    return var_name
        
        # フォールバック: パターンマッチング
        return self._find_variable_by_pattern(ds, logical_name, var_type, level)
    
    def _find_variable_by_pattern(self, ds: xr.Dataset, logical_name: str, 
                                var_type: str, level: Optional[int] = None) -> Optional[str]:
        """パターンマッチングで変数を検索"""
        patterns = self.config.get('fallback_patterns', {}).get(var_type, {}).get(logical_name, [])
        
        for pattern in patterns:
            if level is not None:
                pattern = pattern.replace('{level}', str(level))
            
            # ワイルドカードマッチング
            for var_name in ds.data_vars:
                if fnmatch.fnmatch(var_name, pattern):
                    logger.info(f"パターンマッチで変数を発見: {logical_name} -> {var_name}")
                    return var_name
        
        logger.warning(f"変数が見つかりません: {logical_name} ({var_type})")
        return None


class GridPointSelector:
    """格子点選択を処理するクラス"""
    
    def __init__(self, ds: xr.Dataset, proj_handler: ProjectionHandler):
        """
        初期化
        
        Args:
            ds: データセット
            proj_handler: 投影変換ハンドラー
        """
        self.ds = ds
        self.proj_handler = proj_handler
        self._setup_kdtree()
    
    def _setup_kdtree(self):
        """KDTreeを構築 - MSM格子座標系対応"""
        # MSMの格子座標系では、緯度・経度が2次元配列として格納されている
        # 投影座標での距離計算ではなく、地理座標での距離計算を使用
        
        # 緯度・経度の2次元配列を取得
        lat_2d = self.ds.latitude.values  # shape: (521, 633)
        lon_2d = self.ds.longitude.values  # shape: (521, 633)
        
        # 全格子点の緯度・経度をKDTree用に準備
        coords = np.column_stack([lat_2d.ravel(), lon_2d.ravel()])
        
        self.kdtree = cKDTree(coords)
        self.lat_2d = lat_2d
        self.lon_2d = lon_2d
        self.shape = lat_2d.shape  # (521, 633)
        
        # 基準点の格子座標（MSMの仕様）
        self.reference_grid_y = 360  # 361番目（1-based）-> 360（0-based）
        self.reference_grid_x = 448  # 449番目（1-based）-> 448（0-based）
        
        logger.info(f"MSM格子座標系でKDTree構築完了: {len(coords)} 点")
        logger.info(f"格子形状: {self.shape} (Y軸×X軸)")
        logger.info(f"基準点格子座標: [{self.reference_grid_y}, {self.reference_grid_x}]")
    
    def find_nearest_points(self, target_lat: float, target_lon: float, 
                          method: str = 'nearest', **kwargs) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        指定地点に最も近い格子点を検索
        
        Args:
            target_lat: 目標緯度
            target_lon: 目標経度
            method: 選択方法 ('nearest' または 'mean')
            **kwargs: 追加パラメータ
            
        Returns:
            (y_indices, x_indices, n_points): インデックス配列と点数
        """
        # 目標地点を投影座標に変換
        target_x, target_y = self.proj_handler.latlon_to_projection(target_lat, target_lon)
        
        if method == 'nearest':
            return self._find_nearest_single(target_lat, target_lon)
        elif method == 'mean':
            return self._find_nearest_multiple(target_lat, target_lon, **kwargs)
        else:
            raise ValueError(f"未対応の選択方法: {method}")
    
    def get_used_grid_points_info(self, target_lat: float, target_lon: float, 
                                method: str = 'nearest', **kwargs) -> List[Dict]:
        """
        使用される格子点の詳細情報を取得
        
        Args:
            target_lat: 目標緯度
            target_lon: 目標経度
            method: 選択方法
            **kwargs: 追加パラメータ
            
        Returns:
            格子点情報のリスト
        """
        y_indices, x_indices, n_points = self.find_nearest_points(
            target_lat, target_lon, method, **kwargs
        )
        
        grid_points = []
        
        if hasattr(self.ds, 'latitude') and hasattr(self.ds, 'longitude'):
            # 2次元座標の場合
            lat_data = self.ds.latitude.values
            lon_data = self.ds.longitude.values
            
            for i in range(len(y_indices)):
                y_idx = y_indices[i]
                x_idx = x_indices[i]
                
                # 距離を計算
                grid_lat = float(lat_data[y_idx, x_idx])
                grid_lon = float(lon_data[y_idx, x_idx])
                distance = self._calculate_distance(target_lat, target_lon, grid_lat, grid_lon)
                
                grid_points.append({
                    'lat': grid_lat,
                    'lon': grid_lon,
                    'grid_i': int(y_idx),  # Y軸インデックス（北から）
                    'grid_j': int(x_idx),  # X軸インデックス（西から）
                    'distance': distance,
                    'method': method
                })
        
        return grid_points
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """2点間の距離を計算（km）"""
        import math
        
        # 地球の半径 (km)
        R = 6371.0
        
        # ラジアンに変換
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # ハヴァーサイン公式
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _find_nearest_multiple(self, target_lat: float, target_lon: float, **kwargs) -> Tuple[np.ndarray, np.ndarray, int]:
        """複数点を検索 - 地理座標版"""
        if 'radius_km' in kwargs:
            return self._find_within_radius(target_lat, target_lon, kwargs['radius_km'])
        elif 'k_neighbors' in kwargs:
            return self._find_k_neighbors(target_lat, target_lon, kwargs['k_neighbors'])
        else:
            logger.warning("meanメソッドにはradius_kmまたはk_neighborsが必要です")
            return self._find_nearest_single(target_lat, target_lon)
    
    def _find_nearest_single(self, target_lat: float, target_lon: float) -> Tuple[np.ndarray, np.ndarray, int]:
        """最近傍1点を検索 - 地理座標版"""
        distance, index = self.kdtree.query([target_lat, target_lon])
        
        # インデックスを2D座標に変換
        y_idx, x_idx = np.unravel_index(index, self.shape)
        
        # 実際の格子点座標を取得して確認
        actual_lat = self.lat_2d[y_idx, x_idx]
        actual_lon = self.lon_2d[y_idx, x_idx]
        
        logger.info(f"最近傍点: 格子[{y_idx}, {x_idx}] = ({actual_lat:.4f}°, {actual_lon:.4f}°)")
        
        return np.array([y_idx]), np.array([x_idx]), 1
    
    def _find_within_radius(self, target_x: float, target_y: float, 
                          radius_km: float) -> Tuple[np.ndarray, np.ndarray, int]:
        """半径内の全ての点を検索"""
        # KDTreeは [lat, lon] 座標で構築されているため、target_x=lat, target_y=lon
        target_lat = target_x
        target_lon = target_y
        
        # 度単位での近似的な距離計算のため、kmを度に変換
        # 緯度1度 ≈ 111.32 km
        # 経度1度 ≈ 111.32 * cos(緯度) km
        lat_deg_km = 111.32
        lon_deg_km = 111.32 * np.cos(np.radians(target_lat))
        
        # 半径をkmから度に変換（楕円形を円形で近似）
        # より保守的な変換として、小さい方の値を使用
        min_deg_km = min(lat_deg_km, lon_deg_km)
        radius_deg = radius_km / min_deg_km
        
        # 半径内の点を検索（度単位）
        indices = self.kdtree.query_ball_point([target_lat, target_lon], radius_deg)
        
        if not indices:
            logger.warning(f"半径 {radius_km} km 内に格子点が見つかりません")
            return np.array([]), np.array([]), 0
        
        # インデックスを2D座標に変換
        y_indices, x_indices = np.unravel_index(indices, self.shape)
        
        logger.info(f"半径 {radius_km} km 内の点数: {len(indices)}")
        
        return y_indices, x_indices, len(indices)
    
    def _find_k_neighbors(self, target_x: float, target_y: float, 
                        k: int) -> Tuple[np.ndarray, np.ndarray, int]:
        """k近傍点を検索"""
        distances, indices = self.kdtree.query([target_x, target_y], k=k)
        
        # スカラーの場合は配列に変換
        if np.isscalar(indices):
            indices = [indices]
            distances = [distances]
        
        # インデックスを2D座標に変換
        y_indices, x_indices = np.unravel_index(indices, self.shape)
        
        logger.info(f"{k}近傍点を選択, 最大距離: {max(distances):.1f} m")
        
        return y_indices, x_indices, len(indices)


class DataExtractor:
    """データ抽出のメインクラス"""
    
    def __init__(self, data_dir: str, config_path: str = "variables.yml"):
        """
        初期化
        
        Args:
            data_dir: NetCDFファイルのディレクトリ
            config_path: 変数マッピング設定ファイル
        """
        self.data_dir = Path(data_dir)
        self.var_mapper = VariableMapper(config_path)
        self.ds = None
        self.proj_handler = None
        self.grid_selector = None
    
    def load_data(self, time_start: Optional[str] = None, 
                 time_end: Optional[str] = None, chunks: Optional[Dict] = None):
        """
        NetCDFデータを読み込み
        
        Args:
            time_start: 開始時刻 (ISO8601)
            time_end: 終了時刻 (ISO8601)
            chunks: chunksパラメータ
        """
        # NetCDFファイルパターン
        nc_files = list(self.data_dir.glob("*.nc"))
        
        if not nc_files:
            raise FileNotFoundError(f"NetCDFファイルが見つかりません: {self.data_dir}")
        
        # ファイルサイズでフィルタリング（破損ファイルを除外）
        valid_files = []
        min_size = 1000000  # 1MB未満のファイルは破損とみなす
        
        for file in nc_files:
            try:
                if file.stat().st_size > min_size:
                    # ファイルが実際に読み込めるかテスト
                    test_ds = xr.open_dataset(file, engine='netcdf4')
                    test_ds.close()
                    valid_files.append(file)
                else:
                    logger.warning(f"ファイルサイズが小さすぎます (破損の可能性): {file.name}")
            except Exception as e:
                logger.warning(f"ファイル読み込みテストに失敗: {file.name} - {e}")
        
        if not valid_files:
            raise FileNotFoundError(f"有効なNetCDFファイルが見つかりません: {self.data_dir}")
        
        logger.info(f"有効なNetCDFファイル数: {len(valid_files)} / {len(nc_files)}")
        
        # 時間範囲でファイルをフィルタリング（ファイル名から推定）
        if time_start or time_end:
            valid_files = self._filter_files_by_time(valid_files, time_start, time_end)
        
        # データセットを開く
        try:
            if len(valid_files) == 1:
                self.ds = xr.open_dataset(valid_files[0], chunks=chunks, engine='netcdf4')
            else:
                self.ds = xr.open_mfdataset(valid_files, combine='by_coords', chunks=chunks, engine='netcdf4')
            
            logger.info(f"データセット読み込み完了: {self.ds.dims}")
            
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            raise
        
        # 投影ハンドラーを初期化
        self.proj_handler = ProjectionHandler(self.ds)
        self.grid_selector = GridPointSelector(self.ds, self.proj_handler)
    
    def get_dataset(self) -> Optional[xr.Dataset]:
        """
        読み込まれたデータセットを取得
        
        Returns:
            読み込まれたxarray.Dataset（未読み込みの場合はNone）
        """
        return self.ds
    
    def get_extraction_grid_points(self, lat: float, lon: float, method: str = 'nearest', **kwargs) -> List[Dict]:
        """
        データ抽出で使用される格子点の情報を取得
        
        Args:
            lat: 目標緯度
            lon: 目標経度
            method: 抽出方法
            **kwargs: 追加パラメータ
            
        Returns:
            使用格子点の情報リスト
        """
        if self.grid_selector is None:
            raise ValueError("データが読み込まれていません")
        
        return self.grid_selector.get_used_grid_points_info(lat, lon, method, **kwargs)
    
    def _filter_files_by_time(self, files: List[Path], 
                            time_start: Optional[str], 
                            time_end: Optional[str]) -> List[Path]:
        """ファイル名に基づいて時間範囲でフィルタリング"""
        # ファイル名から時刻を抽出（例: LANAL_2024070300.nc -> 2024-07-03 00:00）
        filtered_files = []
        
        # JST（日本標準時）タイムゾーンを定義 (UTC+9)
        JST = timezone(timedelta(hours=9))
        
        for file in files:
            try:
                # ファイル名から日時を抽出
                filename = file.stem
                if 'LANAL_' in filename:
                    date_part = filename.split('LANAL_')[1]
                    if len(date_part) >= 10:
                        year = int(date_part[:4])
                        month = int(date_part[4:6])
                        day = int(date_part[6:8])
                        hour = int(date_part[8:10])
                        
                        # NetCDFファイルの時間はUTCとして解釈
                        file_time = datetime(year, month, day, hour, tzinfo=timezone.utc)
                        
                        # 時間範囲チェック
                        if time_start:
                            start_time = datetime.fromisoformat(time_start.replace('Z', '+00:00'))
                            if start_time.tzinfo is None:
                                # タイムゾーン情報がない場合はJSTとして解釈
                                start_time = start_time.replace(tzinfo=JST)
                            else:
                                # UTCからJSTに変換
                                start_time = start_time.astimezone(JST)
                            if file_time < start_time:
                                continue
                        
                        if time_end:
                            end_time = datetime.fromisoformat(time_end.replace('Z', '+00:00'))
                            if end_time.tzinfo is None:
                                # タイムゾーン情報がない場合はJSTとして解釈
                                end_time = end_time.replace(tzinfo=JST)
                            else:
                                # UTCからJSTに変換
                                end_time = end_time.astimezone(JST)
                            if file_time > end_time:
                                continue
                        
                        filtered_files.append(file)
                        
            except (ValueError, IndexError) as e:
                logger.warning(f"ファイル名の時刻解析に失敗: {file.name}")
                # 解析に失敗した場合は含める
                filtered_files.append(file)
        
        logger.info(f"時間フィルタリング後のファイル数: {len(filtered_files)}")
        return filtered_files
    
    def extract_surface_data(self, lat: float, lon: float, 
                           time_sel: Optional[str] = None,
                           time_start: Optional[str] = None,
                           time_end: Optional[str] = None,
                           method: str = 'nearest',
                           variables: Optional[List[str]] = None,
                           **method_kwargs) -> pd.DataFrame:
        """
        地上データを抽出
        
        Args:
            lat: 緯度
            lon: 経度
            time_sel: 単一時刻選択
            time_start: 時間範囲開始
            time_end: 時間範囲終了
            method: 格子点選択方法
            variables: 抽出する変数リスト（Noneの場合は全て）
            **method_kwargs: 格子点選択の追加パラメータ
            
        Returns:
            抽出結果のDataFrame
        """
        # 格子点を選択
        y_indices, x_indices, n_points = self.grid_selector.find_nearest_points(
            lat, lon, method, **method_kwargs
        )
        
        if n_points == 0:
            logger.warning("選択された格子点がありません")
            return pd.DataFrame()
        
        # 変数を抽出
        if variables is None:
            # デフォルトですべての地上変数を抽出
            variables = ['air_temperature', 'relative_humidity', 'u_wind', 'v_wind', 'surface_pressure']
        else:
            # 風速・風向が要求された場合、U/V成分も自動的に追加
            if 'wind_speed' in variables or 'wind_direction' in variables:
                if 'u_wind' not in variables:
                    variables.append('u_wind')
                if 'v_wind' not in variables:
                    variables.append('v_wind')
        
        results = []
        
        for var_name in variables:
            # 計算変数をスキップ（後で別途処理）
            if var_name in ['wind_speed', 'wind_direction']:
                continue
                
            nc_var_name = self.var_mapper.get_variable_name(self.ds, var_name, 'surface')
            if nc_var_name is None:
                logger.warning(f"地上変数が見つかりません: {var_name}")
                continue
            
            # データを抽出
            data = self.ds[nc_var_name]
            
            # 時間選択
            if time_sel:
                data = data.sel(time=time_sel, method='nearest')
            elif time_start or time_end:
                data = data.sel(time=slice(time_start, time_end))
            
            # 空間選択と平均化
            if method == 'nearest':
                extracted = data.isel(y=y_indices[0], x=x_indices[0])
            else:
                extracted = data.isel(y=xr.DataArray(y_indices), x=xr.DataArray(x_indices)).mean()
            
            # 単位変換
            converted_data = self._convert_units(extracted, var_name, 'surface')
            
            # 結果に追加
            if hasattr(converted_data, 'time'):
                # 時間次元があるかチェック
                if 'time' in converted_data.dims:
                    time_size = converted_data.sizes['time']
                    for t in range(time_size):
                        if t >= len(results):
                            # UTC時刻をJSTに変換
                            utc_time = pd.to_datetime(converted_data.time.isel(time=t).values)
                            if utc_time.tz is None:
                                # タイムゾーン情報がない場合はUTCとして扱う
                                utc_time = utc_time.tz_localize('UTC')
                            jst_time = utc_time.tz_convert('Asia/Tokyo')
                            
                            results.append({
                                'time': jst_time,
                                'lat': lat,
                                'lon': lon,
                                'method': method,
                                'n_points': n_points
                            })
                        
                        # 変数名に対応するカラム名を設定
                        col_name = self._get_output_column_name(var_name, 'surface')
                        results[t][col_name] = float(converted_data.isel(time=t).values)
                else:
                    # 時間がスカラーまたは0次元の場合
                    if not results:
                        # UTC時刻をJSTに変換
                        utc_time = pd.to_datetime(converted_data.time.values)
                        if utc_time.tz is None:
                            # タイムゾーン情報がない場合はUTCとして扱う
                            utc_time = utc_time.tz_localize('UTC')
                        jst_time = utc_time.tz_convert('Asia/Tokyo')
                        
                        results.append({
                            'time': jst_time,
                            'lat': lat,
                            'lon': lon,
                            'method': method,
                            'n_points': n_points
                        })
                    
                    col_name = self._get_output_column_name(var_name, 'surface')
                    results[0][col_name] = float(converted_data.values)
            else:
                # 時間次元がない場合
                if not results:
                    results.append({
                        'time': pd.NaT,
                        'lat': lat,
                        'lon': lon,
                        'method': method,
                        'n_points': n_points
                    })
                
                col_name = self._get_output_column_name(var_name, 'surface')
                results[0][col_name] = float(converted_data.values)
        
        df = pd.DataFrame(results)
        
        # 風速・風向を計算（気象学的風向）
        df = add_wind_calculations(df)
        
        # 要求されていない計算変数のカラムを削除
        original_variables = set(variables) if variables else set()
        calculated_vars = {'wind_speed', 'wind_direction'}
        requested_calculated = original_variables & calculated_vars
        unrequested_calculated = calculated_vars - requested_calculated
        
        # 要求されていない計算変数のカラムを削除
        for var in unrequested_calculated:
            col_name = self._get_output_column_name(var, 'surface')
            if col_name in df.columns:
                df = df.drop(columns=[col_name])
        
        return df
    
    def extract_isobaric_data(self, lat: float, lon: float,
                            levels: List[int],
                            time_sel: Optional[str] = None,
                            time_start: Optional[str] = None,
                            time_end: Optional[str] = None,
                            method: str = 'nearest',
                            variables: Optional[List[str]] = None,
                            **method_kwargs) -> pd.DataFrame:
        """
        等圧面データを抽出
        
        Args:
            lat: 緯度
            lon: 経度
            levels: 気圧面リスト（hPa）
            time_sel: 単一時刻選択
            time_start: 時間範囲開始
            time_end: 時間範囲終了
            method: 格子点選択方法
            variables: 抽出する変数リスト（Noneの場合は全て）
            **method_kwargs: 格子点選択の追加パラメータ
            
        Returns:
            抽出結果のDataFrame
        """
        # 格子点を選択
        y_indices, x_indices, n_points = self.grid_selector.find_nearest_points(
            lat, lon, method, **method_kwargs
        )
        
        if n_points == 0:
            logger.warning("選択された格子点がありません")
            return pd.DataFrame()
        
        # 変数リスト
        if variables is None:
            # デフォルトですべての等圧面変数を抽出
            variables = ['air_temperature', 'relative_humidity', 'u_wind', 'v_wind', 'geopotential_height']
        else:
            # 風速・風向が要求された場合、U/V成分も自動的に追加
            if 'wind_speed' in variables or 'wind_direction' in variables:
                if 'u_wind' not in variables:
                    variables.append('u_wind')
                if 'v_wind' not in variables:
                    variables.append('v_wind')
        
        results = []
        
        for level in levels:
            for var_name in variables:
                # 計算変数をスキップ（後で別途処理）
                if var_name in ['wind_speed', 'wind_direction']:
                    continue
                    
                nc_var_name = self.var_mapper.get_variable_name(
                    self.ds, var_name, 'isobaric', level
                )
                if nc_var_name is None:
                    logger.warning(f"等圧面変数が見つかりません: {var_name} at {level}hPa")
                    continue
                
                # データを抽出
                data = self.ds[nc_var_name]
                
                # 時間選択
                if time_sel:
                    data = data.sel(time=time_sel, method='nearest')
                elif time_start or time_end:
                    data = data.sel(time=slice(time_start, time_end))
                
                # 空間選択と平均化
                if method == 'nearest':
                    extracted = data.isel(y=y_indices[0], x=x_indices[0])
                else:
                    extracted = data.isel(y=xr.DataArray(y_indices), x=xr.DataArray(x_indices)).mean()
                
                # 単位変換
                converted_data = self._convert_units(extracted, var_name, 'isobaric')
                
                # 結果に追加
                if hasattr(converted_data, 'time'):
                    # 時間次元があるかチェック
                    if 'time' in converted_data.dims:
                        time_size = converted_data.sizes['time']
                        for t in range(time_size):
                            # 該当する結果行を検索
                            result_idx = None
                            # UTC時刻をJSTに変換
                            utc_time = pd.to_datetime(converted_data.time.isel(time=t).values)
                            if utc_time.tz is None:
                                # タイムゾーン情報がない場合はUTCとして扱う
                                utc_time = utc_time.tz_localize('UTC')
                            jst_time = utc_time.tz_convert('Asia/Tokyo')
                            
                            for i, result in enumerate(results):
                                if (result['time'] == jst_time and 
                                    result['level_hPa'] == level):
                                    result_idx = i
                                    break
                            
                            if result_idx is None:
                                results.append({
                                    'time': jst_time,
                                    'lat': lat,
                                    'lon': lon,
                                    'level_hPa': level,
                                    'method': method,
                                    'n_points': n_points
                                })
                                result_idx = len(results) - 1
                            
                            col_name = self._get_output_column_name(var_name, 'isobaric')
                            results[result_idx][col_name] = float(converted_data.isel(time=t).values)
                    else:
                        # 時間がスカラーまたは0次元の場合
                        result_idx = None
                        # UTC時刻をJSTに変換
                        utc_time = pd.to_datetime(converted_data.time.values)
                        if utc_time.tz is None:
                            # タイムゾーン情報がない場合はUTCとして扱う
                            utc_time = utc_time.tz_localize('UTC')
                        jst_time = utc_time.tz_convert('Asia/Tokyo')
                        
                        for i, result in enumerate(results):
                            if (result['time'] == jst_time and result['level_hPa'] == level):
                                result_idx = i
                                break
                        
                        if result_idx is None:
                            results.append({
                                'time': jst_time,
                                'lat': lat,
                                'lon': lon,
                                'level_hPa': level,
                                'method': method,
                                'n_points': n_points
                            })
                            result_idx = len(results) - 1
                        
                        col_name = self._get_output_column_name(var_name, 'isobaric')
                        results[result_idx][col_name] = float(converted_data.values)
                else:
                    # 時間次元がない場合
                    result_idx = None
                    for i, result in enumerate(results):
                        if result['level_hPa'] == level:
                            result_idx = i
                            break
                    
                    if result_idx is None:
                        results.append({
                            'time': pd.NaT,
                            'lat': lat,
                            'lon': lon,
                            'level_hPa': level,
                            'method': method,
                            'n_points': n_points
                        })
                        result_idx = len(results) - 1
                    
                    col_name = self._get_output_column_name(var_name, 'isobaric')
                    results[result_idx][col_name] = float(converted_data.values)
        
        df = pd.DataFrame(results)
        
        # 風速・風向を計算（気象学的風向）
        df = add_wind_calculations(df)
        
        # 要求されていない計算変数のカラムを削除
        original_variables = set(variables) if variables else set()
        calculated_vars = {'wind_speed', 'wind_direction'}
        requested_calculated = original_variables & calculated_vars
        unrequested_calculated = calculated_vars - requested_calculated
        
        # 要求されていない計算変数のカラムを削除
        for var in unrequested_calculated:
            col_name = self._get_output_column_name(var, 'isobaric')
            if col_name in df.columns:
                df = df.drop(columns=[col_name])
        
        return df
    
    def _convert_units(self, data: xr.DataArray, var_name: str, var_type: str) -> xr.DataArray:
        """単位変換"""
        if var_name == 'air_temperature':
            # K → °C
            if hasattr(data, 'units') and data.units == 'K':
                return data - 273.15
            elif np.nanmean(data.values) > 100:  # 推定でK
                return data - 273.15
            else:
                return data
        
        elif var_name == 'relative_humidity':
            # 0-1 → %
            if np.nanmax(data.values) <= 1.0:
                return data * 100
            else:
                return data
        
        elif var_name in ['u_wind', 'v_wind']:
            # m/s（そのまま）
            return data
        
        elif var_name == 'surface_pressure':
            # Pa → hPa
            if hasattr(data, 'units') and data.units == 'Pa':
                return data / 100
            elif np.nanmean(data.values) > 10000:  # 推定でPa
                return data / 100
            else:
                return data
        
        elif var_name == 'geopotential_height':
            # m（そのまま、ジオポテンシャル高度はgpm単位とみなす）
            return data
        
        else:
            return data
    
    def _get_output_column_name(self, var_name: str, var_type: str) -> str:
        """出力カラム名を取得"""
        column_map = {
            'air_temperature': 'tas_C' if var_type == 'surface' else 'ta_C',
            'relative_humidity': 'rh_%',
            'u_wind': 'u_ms',
            'v_wind': 'v_ms',
            'surface_pressure': 'ps_hPa',
            'geopotential_height': 'z_gpm'
        }
        return column_map.get(var_name, var_name)
    
    def dry_run(self, surface: bool = False, isobaric: bool = False, 
               levels: Optional[List[int]] = None):
        """
        ドライラン: 変数の存在確認とメタデータ表示
        
        Args:
            surface: 地上データを確認
            isobaric: 等圧面データを確認
            levels: 確認する気圧面レベル
        """
        logger.info("=== ドライラン: 変数確認 ===")
        
        if surface:
            logger.info("\n--- 地上変数 ---")
            surface_vars = ['air_temperature', 'relative_humidity', 'u_wind', 'v_wind', 'surface_pressure']
            for var_name in surface_vars:
                nc_var = self.var_mapper.get_variable_name(self.ds, var_name, 'surface')
                if nc_var:
                    logger.info(f"✓ {var_name}: {nc_var}")
                else:
                    logger.error(f"✗ {var_name}: 見つかりません")
        
        if isobaric and levels:
            logger.info("\n--- 等圧面変数 ---")
            isobaric_vars = ['air_temperature', 'relative_humidity', 'u_wind', 'v_wind', 'geopotential_height']
            for level in levels:
                logger.info(f"\n{level}hPa:")
                for var_name in isobaric_vars:
                    nc_var = self.var_mapper.get_variable_name(self.ds, var_name, 'isobaric', level)
                    if nc_var:
                        logger.info(f"  ✓ {var_name}: {nc_var}")
                    else:
                        logger.error(f"  ✗ {var_name}: 見つかりません")
        
        # データセット情報
        logger.info(f"\n--- データセット情報 ---")
        logger.info(f"時間範囲: {self.ds.time.min().values} - {self.ds.time.max().values}")
        logger.info(f"格子サイズ: {self.ds.dims}")
        logger.info(f"座標範囲:")
        logger.info(f"  緯度: {float(self.ds.latitude.min()):.3f} - {float(self.ds.latitude.max()):.3f}")
        logger.info(f"  経度: {float(self.ds.longitude.min()):.3f} - {float(self.ds.longitude.max()):.3f}")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="NetCDF気象データ抽出プログラム",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  地上データ（単一時刻・最近傍）:
    python extract.py --lat 35.0 --lon 139.0 --time 2024-07-03T12:00:00 --surface --method nearest --out out_surface.parquet

  等圧面データ（時間範囲・半径平均）:
    python extract.py --lat 35.0 --lon 139.0 --time-start 2024-07-03T00:00:00 --time-end 2024-07-03T23:00:00 --levels 1000 850 500 --isobaric --method mean --radius-km 10 --out out_isobaric.parquet

  ドライラン:
    python extract.py --lat 35.0 --lon 139.0 --surface --isobaric --levels 1000 500 --dry-run
        """
    )
    
    # 位置引数
    parser.add_argument('--lat', type=float, required=True, help='緯度')
    parser.add_argument('--lon', type=float, required=True, help='経度')
    
    # 時間選択
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--time', type=str, help='単一時刻（ISO8601形式）')
    parser.add_argument('--time-start', type=str, help='時間範囲開始（ISO8601形式）')
    parser.add_argument('--time-end', type=str, help='時間範囲終了（ISO8601形式）')
    
    # データタイプ
    parser.add_argument('--surface', action='store_true', help='地上データを抽出')
    parser.add_argument('--isobaric', action='store_true', help='等圧面データを抽出')
    parser.add_argument('--levels', type=int, nargs='+', help='気圧面レベル（hPa）')
    
    # 格子点選択
    parser.add_argument('--method', choices=['nearest', 'mean'], default='nearest',
                       help='格子点選択方法')
    parser.add_argument('--radius-km', type=float, help='平均化半径（km）')
    parser.add_argument('--k-neighbors', type=int, help='k近傍点数')
    
    # 出力
    parser.add_argument('--out', type=str, help='出力ファイル名')
    parser.add_argument('--format', choices=['parquet', 'csv'], default='parquet',
                       help='出力形式')
    
    # その他
    parser.add_argument('--data-dir', type=str, default='use_nc',
                       help='NetCDFファイルディレクトリ')
    parser.add_argument('--config', type=str, default='variables.yml',
                       help='変数マッピング設定ファイル')
    parser.add_argument('--dry-run', action='store_true',
                       help='ドライラン（変数確認のみ）')
    parser.add_argument('--chunks', type=str, help='chunksパラメータ（JSON形式）')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細ログ')
    
    args = parser.parse_args()
    
    # ログレベル設定
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 引数検証
    if not args.surface and not args.isobaric:
        parser.error("--surface または --isobaric のいずれかを指定してください")
    
    if args.isobaric and not args.levels:
        parser.error("--isobaric には --levels の指定が必要です")
    
    if args.method == 'mean' and not args.radius_km and not args.k_neighbors:
        parser.error("--method mean には --radius-km または --k-neighbors が必要です")
    
    if args.time_start and not args.time_end:
        parser.error("--time-start には --time-end の指定が必要です")
    
    if args.time_end and not args.time_start:
        parser.error("--time-end には --time-start の指定が必要です")
    
    try:
        # データ抽出器を初期化
        extractor = DataExtractor(args.data_dir, args.config)
        
        # chunksパラメータ
        chunks = None
        if args.chunks:
            import json
            chunks = json.loads(args.chunks)
        
        # データ読み込み
        extractor.load_data(args.time_start, args.time_end, chunks)
        
        # ドライランモード
        if args.dry_run:
            extractor.dry_run(args.surface, args.isobaric, args.levels)
            return
        
        # 格子点選択パラメータ
        method_kwargs = {}
        if args.radius_km:
            method_kwargs['radius_km'] = args.radius_km
        if args.k_neighbors:
            method_kwargs['k_neighbors'] = args.k_neighbors
        
        results = []
        
        # 地上データ抽出
        if args.surface:
            logger.info("地上データを抽出中...")
            surface_df = extractor.extract_surface_data(
                args.lat, args.lon,
                args.time, args.time_start, args.time_end,
                args.method, **method_kwargs
            )
            
            if not surface_df.empty:
                logger.info(f"地上データ抽出完了: {len(surface_df)} 行")
                results.append(('surface', surface_df))
            else:
                logger.warning("地上データが抽出されませんでした")
        
        # 等圧面データ抽出
        if args.isobaric:
            logger.info("等圧面データを抽出中...")
            isobaric_df = extractor.extract_isobaric_data(
                args.lat, args.lon, args.levels,
                args.time, args.time_start, args.time_end,
                args.method, **method_kwargs
            )
            
            if not isobaric_df.empty:
                logger.info(f"等圧面データ抽出完了: {len(isobaric_df)} 行")
                results.append(('isobaric', isobaric_df))
            else:
                logger.warning("等圧面データが抽出されませんでした")
        
        # 結果を保存
        if results:
            for data_type, df in results:
                # 出力ファイル名
                if args.out:
                    if len(results) > 1:
                        # 複数タイプの場合はタイプ名を付加
                        base_name = Path(args.out).stem
                        ext = Path(args.out).suffix
                        if not ext:
                            ext = f'.{args.format}'
                        output_file = f"{base_name}_{data_type}{ext}"
                    else:
                        output_file = args.out
                        if not Path(output_file).suffix:
                            output_file += f'.{args.format}'
                else:
                    output_file = f"out_{data_type}.{args.format}"
                
                # ファイル保存
                if args.format == 'parquet':
                    df.to_parquet(output_file, index=False)
                else:
                    df.to_csv(output_file, index=False)
                
                logger.info(f"結果を保存しました: {output_file}")
                
                # サマリー表示
                logger.info(f"\n=== {data_type.upper()} データサマリー ===")
                logger.info(f"行数: {len(df)}")
                logger.info(f"カラム: {list(df.columns)}")
                if not df.empty:
                    logger.info(f"時間範囲: {df['time'].min()} - {df['time'].max()}")
                    logger.info(f"最初の数行:")
                    print(df.head())
        else:
            logger.warning("抽出されたデータがありません")
            
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()