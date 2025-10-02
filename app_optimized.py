import logging
from flask import Flask, render_template, request, jsonify, Response
import os
import numpy as np
from datetime import datetime, timedelta, timezone
import yaml
import sys

# パフォーマンス最適化のため、必要な時のみNetCDFライブラリをロード
try:
    from extract import DataExtractor
    NETCDF_AVAILABLE = True
    logging.info("NetCDF libraries loaded successfully")
except ImportError as e:
    NETCDF_AVAILABLE = False
    logging.warning(f"NetCDF libraries not available: {e}")

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# グローバル変数（キャッシュ用）
_extractor_cache = None
_variables_cache = None

def get_variables():
    """変数定義を取得（キャッシュ付き）"""
    global _variables_cache
    if _variables_cache is None:
        try:
            with open('variables.yml', 'r', encoding='utf-8') as f:
                _variables_cache = yaml.safe_load(f)
        except FileNotFoundError:
            # フォールバック用のハードコードされた変数定義
            _variables_cache = {
                'u': {'name': 'u', 'long_name': 'U成分（東西風）', 'units': 'm/s'},
                'v': {'name': 'v', 'long_name': 'V成分（南北風）', 'units': 'm/s'},
                'wind_speed': {'name': 'wind_speed', 'long_name': '風速', 'units': 'm/s'},
                'wind_direction': {'name': 'wind_direction', 'long_name': '風向', 'units': 'degree'},
                't': {'name': 't', 'long_name': '気温', 'units': 'K'},
                'rh': {'name': 'rh', 'long_name': '相対湿度', 'units': '%'}
            }
    return _variables_cache

def get_extractor():
    """DataExtractorのインスタンスを取得（キャッシュ付き）"""
    global _extractor_cache
    if _extractor_cache is None and NETCDF_AVAILABLE:
        try:
            _extractor_cache = DataExtractor('use_nc')
            logger.info("DataExtractor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DataExtractor: {e}")
            _extractor_cache = None
    return _extractor_cache

def get_available_levels():
    """NetCDFファイルから利用可能な高度レベルを取得"""
    if not NETCDF_AVAILABLE:
        return [1000, 925, 850, 700, 500, 300, 200, 100]
    
    try:
        import re
        from pathlib import Path
        import xarray as xr
        
        data_dir = Path('use_nc')
        nc_files = list(data_dir.glob('*.nc'))
        
        if not nc_files:
            return [1000, 925, 850, 700, 500, 300, 200, 100]
        
        # 最初のファイルから変数名を取得
        with xr.open_dataset(nc_files[0]) as ds:
            variables = list(ds.data_vars)
            
            # 高度レベルを変数名から抽出
            levels = set()
            level_pattern = r'_(\d+)mb'
            
            for var in variables:
                match = re.search(level_pattern, var)
                if match:
                    level = int(match.group(1))
                    levels.add(level)
            
            if levels:
                return sorted(levels, reverse=True)  # 高い方から低い方へ
            else:
                return [1000, 925, 850, 700, 500, 300, 200, 100]
                
    except Exception as e:
        logger.error(f"Error extracting levels from NetCDF: {e}")
        return [1000, 925, 850, 700, 500, 300, 200, 100]

@app.route('/')
def index():
    """メインページ"""
    return render_template('index_simple.html')

@app.route('/api/available_levels')
def available_levels():
    """利用可能な高度レベルを返す"""
    logger.info("Levels API called")
    
    try:
        levels = get_available_levels()
        return jsonify({
            'status': 'success',
            'levels': levels
        })
    except Exception as e:
        logger.error(f"Error getting levels: {e}")
        return jsonify({
            'status': 'error',
            'message': f'高度レベル取得エラー: {str(e)}'
        })

@app.route('/api/available_variables')
def available_variables():
    """利用可能な変数を返す"""
    logger.info("Variables API called")
    
    try:
        variables_config = get_variables()
        
        # 日本語の変数情報を取得
        var_list = []
        
        # 主要な変数を定義（UIで表示される変数）
        main_variables = [
            {
                'name': 'u',
                'long_name': 'U成分（東西風）',
                'units': 'm/s',
                'description': '風のU成分（東向きが正）'
            },
            {
                'name': 'v', 
                'long_name': 'V成分（南北風）',
                'units': 'm/s',
                'description': '風のV成分（北向きが正）'
            },
            {
                'name': 't',
                'long_name': '気温',
                'units': '°C',
                'description': '大気温度'
            },
            {
                'name': 'rh',
                'long_name': '相対湿度',
                'units': '%',
                'description': '相対湿度'
            },
            {
                'name': 'pressure',
                'long_name': '海面更正気圧',
                'units': 'hPa',
                'description': '海面更正気圧（PRMSL）'
            },
            {
                'name': 'wind_speed',
                'long_name': '風速',
                'units': 'm/s', 
                'description': 'U・V成分から計算される風速'
            },
            {
                'name': 'wind_direction',
                'long_name': '風向',
                'units': '度',
                'description': 'U・V成分から計算される風向（気象学的風向）'
            }
        ]
        
        # variables.ymlから追加情報があれば使用
        if variables_config and 'variable_info' in variables_config:
            for var in main_variables:
                var_name = var['name']
                
                # 地上データと気圧面データから情報を取得
                for data_type in ['surface', 'isobaric']:
                    if (data_type in variables_config['variable_info'] and 
                        var_name in variables_config['variable_info'][data_type]):
                        
                        info = variables_config['variable_info'][data_type][var_name]
                        if 'name' in info:
                            var['long_name'] = info['name']
                        if 'unit' in info:
                            var['units'] = info['unit']
                        break
        
        return jsonify({
            'status': 'success',
            'variables': main_variables
        })
    except Exception as e:
        logger.error(f"Error getting variables: {e}")
        return jsonify({
            'status': 'error',
            'message': f'変数取得エラー: {str(e)}'
        })

@app.route('/api/grid_points')
def get_grid_points():
    """格子点情報を取得するAPI"""
    logger.info("Grid points API called")
    
    try:
        # stepパラメータで間引き間隔を指定（デフォルト10）
        step = int(request.args.get('step', 10))
        
        if not NETCDF_AVAILABLE:
            # NetCDFが利用できない場合はデモデータを生成
            return generate_demo_grid_points(step)
        
        extractor = get_extractor()
        if extractor is None:
            return jsonify({
                'status': 'error',
                'message': 'データ抽出器が利用できません'
            })
        
        try:
            extractor.load_data()
            logger.info("NetCDF data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load NetCDF data: {e}")
            return generate_demo_grid_points(step)
        
        # 格子点データを取得
        ds = extractor.get_dataset()
        if ds is None:
            return generate_demo_grid_points(step)
        
        # 緯度・経度データを取得（step間隔で間引き）
        lat_data = ds.latitude.values[::step, ::step]
        lon_data = ds.longitude.values[::step, ::step]
        
        # 格子点リストを作成
        points = []
        for i in range(lat_data.shape[0]):
            for j in range(lat_data.shape[1]):
                points.append({
                    'lat': float(lat_data[i, j]),
                    'lon': float(lon_data[i, j]),
                    'grid_i': i * step,
                    'grid_j': j * step
                })
        
        logger.info(f"Retrieved {len(points)} grid points with step={step}")
        
        return jsonify({
            'status': 'success',
            'points': points,
            'total_points': len(points),
            'step': step
        })
        
    except Exception as e:
        logger.error(f"Error getting grid points: {e}")
        return jsonify({
            'status': 'error',
            'message': f'格子点取得エラー: {str(e)}'
        })

def generate_demo_grid_points(step=10):
    """デモ用の格子点データを生成"""
    points = []
    
    # 日本周辺の格子点をデモとして生成
    lat_range = range(20, 50, step)
    lon_range = range(120, 155, step)
    
    for lat in lat_range:
        for lon in lon_range:
            points.append({
                'lat': float(lat),
                'lon': float(lon),
                'grid_i': (lat - 20) // step,
                'grid_j': (lon - 120) // step
            })
    
    return jsonify({
        'status': 'success',
        'points': points,
        'total_points': len(points),
        'step': step,
        'demo': True
    })

@app.route('/api/nearby_grid_points')
def get_nearby_grid_points():
    """指定位置付近の格子点を取得するAPI"""
    logger.info("Nearby grid points API called")
    
    try:
        # パラメータ取得
        target_lat = float(request.args.get('lat'))
        target_lon = float(request.args.get('lon'))
        radius = float(request.args.get('radius', 50))  # km
        max_points = int(request.args.get('max_points', 50))
        
        if not NETCDF_AVAILABLE:
            # NetCDFが利用できない場合はデモデータを生成
            return generate_demo_nearby_grid_points(target_lat, target_lon, radius, max_points)
        
        extractor = get_extractor()
        if extractor is None:
            return jsonify({
                'status': 'error',
                'message': 'データ抽出器が利用できません'
            })
        
        try:
            extractor.load_data()
            logger.info("NetCDF data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load NetCDF data: {e}")
            return generate_demo_nearby_grid_points(target_lat, target_lon, radius, max_points)
        
        # 格子点データを取得
        ds = extractor.get_dataset()
        if ds is None:
            return generate_demo_nearby_grid_points(target_lat, target_lon, radius, max_points)
        
        # 全格子点の緯度・経度データを取得
        lat_data = ds.latitude.values
        lon_data = ds.longitude.values
        
        # 距離を計算して付近の格子点を抽出
        nearby_points = []
        
        for i in range(lat_data.shape[0]):
            for j in range(lat_data.shape[1]):
                grid_lat = float(lat_data[i, j])
                grid_lon = float(lon_data[i, j])
                
                # 距離計算（球面距離の簡易版）
                distance = calculate_distance(target_lat, target_lon, grid_lat, grid_lon)
                
                if distance <= radius:
                    nearby_points.append({
                        'lat': grid_lat,
                        'lon': grid_lon,
                        'distance': distance,
                        'grid_i': i,
                        'grid_j': j
                    })
        
        # 距離でソートして上位max_points点を選択
        nearby_points.sort(key=lambda x: x['distance'])
        nearby_points = nearby_points[:max_points]
        
        logger.info(f"Found {len(nearby_points)} nearby grid points within {radius}km")
        
        return jsonify({
            'status': 'success',
            'points': nearby_points,
            'total_points': len(nearby_points),
            'target_lat': target_lat,
            'target_lon': target_lon,
            'radius': radius,
            'max_points': max_points
        })
        
    except Exception as e:
        logger.error(f"Error getting nearby grid points: {e}")
        return jsonify({
            'status': 'error',
            'message': f'付近格子点取得エラー: {str(e)}'
        })

def calculate_distance(lat1, lon1, lat2, lon2):
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

def generate_demo_nearby_grid_points(target_lat, target_lon, radius, max_points):
    """デモ用の付近格子点データを生成"""
    points = []
    
    # 簡易的に目標点周辺のグリッドを生成
    grid_spacing = 0.05  # 約5km相当
    grid_range = int(radius / (grid_spacing * 111.32)) + 1
    
    for i in range(-grid_range, grid_range + 1):
        for j in range(-grid_range, grid_range + 1):
            lat = target_lat + i * grid_spacing
            lon = target_lon + j * grid_spacing
            
            distance = calculate_distance(target_lat, target_lon, lat, lon)
            
            if distance <= radius:
                points.append({
                    'lat': lat,
                    'lon': lon,
                    'distance': distance,
                    'grid_i': i + grid_range,
                    'grid_j': j + grid_range
                })
    
    # 距離でソートして上位max_points点を選択
    points.sort(key=lambda x: x['distance'])
    points = points[:max_points]
    
    return jsonify({
        'status': 'success',
        'points': points,
        'total_points': len(points),
        'target_lat': target_lat,
        'target_lon': target_lon,
        'radius': radius,
        'max_points': max_points,
        'demo': True
    })

@app.route('/api/extract', methods=['POST'])
def extract():
    """統合データ抽出API（新しいフロントエンド用）"""
    logger.info("Unified data extraction API called")
    
    try:
        data = request.get_json()
        lat = float(data['lat'])
        lon = float(data['lon'])
        data_type = data.get('dataType', 'surface')
        variables = data.get('variables', [])
        method = data.get('method', 'nearest')
        time_mode = data.get('timeMode', 'single')
        output_format = data.get('outputFormat', 'json')
        
        if not variables:
            return jsonify({
                'status': 'error',
                'message': '変数が選択されていません'
            })
        
        logger.info(f"Extracting {data_type} data for variables: {variables}")
        
        if not NETCDF_AVAILABLE:
            # NetCDFが利用できない場合はデモデータを生成
            return generate_demo_extraction(lat, lon, data_type, variables, data)

        # 平均化パラメータの変換（JavaScriptとPythonのキー名を合わせる）
        method_kwargs = {}
        if 'radiusKm' in data:
            method_kwargs['radius_km'] = float(data['radiusKm'])
        if 'kNeighbors' in data:
            method_kwargs['k_neighbors'] = int(data['kNeighbors'])

        extractor = get_extractor()
        if extractor is None:
            return jsonify({
                'status': 'error',
                'message': 'データ抽出器が利用できません'
            })
        
        # DataExtractorを初期化（データロード）
        try:
            extractor.load_data()
            logger.info("NetCDF data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load NetCDF data: {e}")
            return generate_demo_extraction(lat, lon, data_type, variables, data)
        
        # 変数マッピング（APIの変数名からextract.pyの内部変数名へ）
        var_mapping = {
            'u': 'u_wind',
            'v': 'v_wind', 
            't': 'air_temperature',
            'rh': 'relative_humidity',
            'pressure': 'surface_pressure',
            'wind_speed': 'wind_speed',
            'wind_direction': 'wind_direction'
        }
        
        # 内部変数名に変換
        internal_variables = []
        for var in variables:
            if var in var_mapping:
                internal_variables.append(var_mapping[var])
            else:
                internal_variables.append(var)
        
        # 時間パラメータの処理（JST→UTC変換）
        time_params = {}
        JST = timezone(timedelta(hours=9))
        
        if time_mode == 'single':
            time_single = data.get('timeSingle')
            if time_single:
                # JST時刻をUTC時刻に変換してからextract.pyに渡す
                try:
                    jst_time = datetime.fromisoformat(time_single.replace('T', ' '))
                    if jst_time.tzinfo is None:
                        jst_time = jst_time.replace(tzinfo=JST)
                    utc_time = jst_time.astimezone(timezone.utc)
                    time_params['time_sel'] = utc_time.strftime('%Y-%m-%dT%H:%M')
                except:
                    time_params['time_sel'] = time_single
        elif time_mode == 'range':
            time_start = data.get('timeStart')
            time_end = data.get('timeEnd')
            
            if time_start:
                try:
                    jst_time = datetime.fromisoformat(time_start.replace('T', ' '))
                    if jst_time.tzinfo is None:
                        jst_time = jst_time.replace(tzinfo=JST)
                    utc_time = jst_time.astimezone(timezone.utc)
                    time_params['time_start'] = utc_time.strftime('%Y-%m-%dT%H:%M')
                except:
                    time_params['time_start'] = time_start
                    
            if time_end:
                try:
                    jst_time = datetime.fromisoformat(time_end.replace('T', ' '))
                    if jst_time.tzinfo is None:
                        jst_time = jst_time.replace(tzinfo=JST)
                    utc_time = jst_time.astimezone(timezone.utc)
                    time_params['time_end'] = utc_time.strftime('%Y-%m-%dT%H:%M')
                except:
                    time_params['time_end'] = time_end
        
        logger.info(f"Time parameters: {time_params}")
        
        # データ抽出の実行
        try:
            if data_type == 'surface':
                # 地上データ抽出
                df = extractor.extract_surface_data(
                    lat=lat,
                    lon=lon,
                    variables=internal_variables,
                    method=method,
                    **time_params,
                    **method_kwargs
                )
            else:
                # 気圧面データ抽出
                levels = data.get('levels', [1000])
                if not levels:
                    return jsonify({
                        'status': 'error',
                        'message': '気圧面レベルが選択されていません'
                    })
                
                df = extractor.extract_isobaric_data(
                    lat=lat,
                    lon=lon,
                    levels=levels,
                    variables=internal_variables,
                    method=method,
                    **time_params,
                    **method_kwargs
                )
            
            if df.empty:
                logger.warning("No data extracted")
                return generate_demo_extraction(lat, lon, data_type, variables, data, grid_points_info)
            
            logger.info(f"Data extraction successful: {len(df)} records extracted")
            
            # 使用格子点情報を取得
            try:
                logger.info(f"Getting grid points info for lat={lat}, lon={lon}, method={method}, kwargs={method_kwargs}")
                grid_points_info = extractor.get_extraction_grid_points(
                    lat=lat, lon=lon, method=method, **method_kwargs
                )
                logger.info(f"Retrieved {len(grid_points_info)} grid points info")
                if grid_points_info:
                    logger.info(f"Sample grid point: {grid_points_info[0]}")
            except Exception as e:
                logger.warning(f"Failed to get grid points info: {e}")
                logger.exception("Full exception details:")
                grid_points_info = []
            
            # 出力形式に応じてレスポンス
            if output_format == 'csv':
                # CSV形式
                from io import StringIO
                csv_buffer = StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_content = csv_buffer.getvalue()
                
                return Response(
                    csv_content,
                    mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=weather_data.csv'}
                )
            else:
                # JSON形式
                result = {
                    'status': 'success',
                    'data': df.to_dict('records'),
                    'columns': list(df.columns),  # カラム情報を追加
                    'metadata': {
                        'lat': lat,
                        'lon': lon,
                        'data_type': data_type,
                        'variables': variables,
                        'method': method,
                        'extraction_time': df['time'].tolist() if 'time' in df.columns else [],
                        'used_grid_points': grid_points_info
                    },
                    'total_records': len(df)
                }
                return jsonify(result)
                
        except Exception as e:
            logger.error(f"Error during data extraction: {e}")
            # エラー時でも格子点情報は保持する
            return generate_demo_extraction(lat, lon, data_type, variables, data, grid_points_info)
        
    except Exception as e:
        logger.error(f"Data extraction error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'データ抽出エラー: {str(e)}'
        })

def generate_demo_extraction(lat, lon, data_type, variables, request_data, grid_points_info=None):
    """統合デモデータ生成"""
    import pandas as pd
    from datetime import datetime, timedelta, timezone
    
    # JST（日本標準時）タイムゾーンを定義 (UTC+9)
    JST = timezone(timedelta(hours=9))
    
    # 時間軸生成
    time_mode = request_data.get('timeMode', 'single')
    times = []
    
    if time_mode == 'single':
        # 単一時刻の場合
        time_single = request_data.get('timeSingle')
        if time_single:
            try:
                # ISO形式をパース（JSTとして扱う）
                single_time = datetime.fromisoformat(time_single.replace('T', ' '))
                if single_time.tzinfo is None:
                    single_time = single_time.replace(tzinfo=JST)
                times = [single_time]
            except:
                # パースに失敗した場合はデフォルト時刻（JST）
                times = [datetime(2024, 7, 3, 12, tzinfo=JST)]
        else:
            times = [datetime(2024, 7, 3, 12, tzinfo=JST)]
    else:
        # 時間範囲の場合
        time_start = request_data.get('timeStart')
        time_end = request_data.get('timeEnd')
        
        try:
            if time_start and time_end:
                start_time = datetime.fromisoformat(time_start.replace('T', ' '))
                end_time = datetime.fromisoformat(time_end.replace('T', ' '))
                
                # JSTタイムゾーンを適用
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=JST)
                if end_time.tzinfo is None:
                    end_time = end_time.replace(tzinfo=JST)
                
                # 1時間間隔で生成
                current_time = start_time
                while current_time <= end_time:
                    times.append(current_time)
                    current_time += timedelta(hours=1)
            else:
                # デフォルトで6時間分（JST）
                base_time = datetime(2024, 7, 3, 9, tzinfo=JST)
                for i in range(7):
                    times.append(base_time + timedelta(hours=i))
        except:
            # パースに失敗した場合はデフォルト（JST）
            base_time = datetime(2024, 7, 3, 9, tzinfo=JST)
            for i in range(7):
                times.append(base_time + timedelta(hours=i))
    
    logger.info(f"Generated {len(times)} time points for demo data")
    
    # 基本データフレーム
    data_rows = []
    
    if data_type == 'surface':
        # 地上データ
        for time in times:
            row = {
                'time': time,
                'lat': lat,
                'lon': lon,
                'method': request_data.get('method', 'nearest'),
                'n_points': 1
            }
            
            # 変数値生成
            for var in variables:
                if var == 'u':
                    row['u_ms'] = 5.0 * np.sin(time.hour * np.pi / 12) + np.random.normal(0, 1)
                elif var == 'v':
                    row['v_ms'] = 3.0 * np.cos(time.hour * np.pi / 12) + np.random.normal(0, 0.8)
                elif var == 't':
                    row['ta_C'] = 15 + 10 * np.sin((time.hour - 6) * np.pi / 12) + np.random.normal(0, 0.5)
                elif var == 'rh':
                    row['rh_%'] = 60 + 20 * np.cos((time.hour - 6) * np.pi / 12) + np.random.normal(0, 2)
                elif var == 'pressure':
                    row['ps_hPa'] = 1013.25 + 5 * np.sin((time.hour - 12) * np.pi / 12) + np.random.normal(0, 1)
                elif var == 'wind_speed':
                    if 'u_ms' in row and 'v_ms' in row:
                        row['wind_speed_ms'] = np.sqrt(row['u_ms']**2 + row['v_ms']**2)
                    else:
                        row['wind_speed_ms'] = np.random.uniform(2, 8)
                elif var == 'wind_direction':
                    if 'u_ms' in row and 'v_ms' in row:
                        row['wind_direction_deg'] = (270 - np.degrees(np.arctan2(row['v_ms'], row['u_ms']))) % 360
                    else:
                        row['wind_direction_deg'] = np.random.uniform(0, 360)
            
            data_rows.append(row)
    else:
        # 気圧面データ
        levels = request_data.get('levels', [1000])
        for time in times:
            for level in levels:
                row = {
                    'time': time,
                    'lat': lat,
                    'lon': lon,
                    'level_hPa': level,
                    'method': request_data.get('method', 'nearest'),
                    'n_points': 1
                }
                
                # 高度による補正
                alt_factor = 1.0 - (1000 - level) / 1000 * 0.3
                
                # 変数値生成
                for var in variables:
                    if var == 'u':
                        row['u_ms'] = (5.0 * np.sin(time.hour * np.pi / 12) + np.random.normal(0, 1)) * alt_factor
                    elif var == 'v':
                        row['v_ms'] = (3.0 * np.cos(time.hour * np.pi / 12) + np.random.normal(0, 0.8)) * alt_factor
                    elif var == 't':
                        row['ta_C'] = (15 + 10 * np.sin((time.hour - 6) * np.pi / 12)) * alt_factor + np.random.normal(0, 0.5)
                    elif var == 'rh':
                        row['rh_%'] = 60 + 20 * np.cos((time.hour - 6) * np.pi / 12) + np.random.normal(0, 2)
                    elif var == 'pressure':
                        # 気圧面データでは、レベルがそのまま気圧
                        row['pres_hPa'] = level
                    elif var == 'wind_speed':
                        if 'u_ms' in row and 'v_ms' in row:
                            row['wind_speed_ms'] = np.sqrt(row['u_ms']**2 + row['v_ms']**2)
                        else:
                            row['wind_speed_ms'] = np.random.uniform(2, 8) * alt_factor
                    elif var == 'wind_direction':
                        if 'u_ms' in row and 'v_ms' in row:
                            row['wind_direction_deg'] = (270 - np.degrees(np.arctan2(row['v_ms'], row['u_ms']))) % 360
                        else:
                            row['wind_direction_deg'] = np.random.uniform(0, 360)
                
                data_rows.append(row)
    
    df = pd.DataFrame(data_rows)
    
    # 出力形式に応じてレスポンス
    output_format = request_data.get('outputFormat', 'json')
    if output_format == 'csv':
        from io import StringIO
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        return Response(
            csv_content,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=weather_data_demo.csv'}
        )
    else:
        # JSON形式のレスポンス
        result = {
            'status': 'success',
            'data': df.to_dict('records'),
            'columns': list(df.columns),
            'metadata': {
                'lat': lat,
                'lon': lon,
                'data_type': data_type,
                'variables': variables,
                'method': request_data.get('method', 'nearest'),
                'extraction_time': df['time'].tolist() if 'time' in df.columns else [],
                'used_grid_points': grid_points_info if grid_points_info else [],
                'is_demo_data': True  # デモデータであることを示すフラグ
            },
            'total_records': len(df)
        }
        return jsonify(result)
    """データ抽出API"""
    logger.info("Data extraction API called")
    
    try:
        data = request.get_json()
        lat = float(data['lat'])
        lon = float(data['lon'])
        level = int(data['level'])
        variables = data['variables']
        
        if not NETCDF_AVAILABLE:
            # NetCDFが利用できない場合はデモデータを生成
            return generate_demo_data(lat, lon, level, variables)
        
        extractor = get_extractor()
        if extractor is None:
            return jsonify({
                'status': 'error',
                'message': 'データ抽出器が利用できません'
            })
        
        # DataExtractorを初期化（データロード）
        try:
            extractor.load_data()
            logger.info("NetCDF data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load NetCDF data: {e}")
            return generate_demo_data(lat, lon, level, variables)
        
        # 変数マッピング（APIの変数名からextract.pyの内部変数名へ）
        var_mapping = {
            'u': 'u_wind',
            'v': 'v_wind', 
            't': 'air_temperature',
            'rh': 'relative_humidity',
            'wind_speed': 'wind_speed',
            'wind_direction': 'wind_direction'
        }
        
        # 内部変数名に変換
        internal_variables = []
        for var in variables:
            if var in var_mapping:
                internal_variables.append(var_mapping[var])
            else:
                internal_variables.append(var)
        
        # データ抽出実行
        try:
            # isobaric dataを抽出
            df = extractor.extract_isobaric_data(
                lat=lat,
                lon=lon,
                levels=[level],
                variables=internal_variables
            )
            
            if df.empty:
                logger.warning("No data extracted")
                return generate_demo_data(lat, lon, level, variables)
            
            # 結果をAPI形式に変換
            results = {}
            times = df['time'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
            
            for var in variables:
                # 出力カラム名を推定
                if var == 'u':
                    col_name = 'u_ms'
                elif var == 'v':
                    col_name = 'v_ms'
                elif var == 't':
                    col_name = 'ta_C'
                elif var == 'rh':
                    col_name = 'rh_%'
                elif var == 'wind_speed':
                    col_name = 'wind_speed_ms'
                elif var == 'wind_direction':
                    col_name = 'wind_direction_deg'
                else:
                    col_name = var
                
                if col_name in df.columns:
                    results[var] = {
                        'times': times,
                        'values': df[col_name].tolist(),
                        'location': {'lat': lat, 'lon': lon},
                        'level': level
                    }
                else:
                    logger.warning(f"Column {col_name} not found in extracted data")
                    # フォールバックでデモデータ
                    demo_result = generate_demo_data(lat, lon, level, [var])
                    demo_data = demo_result.get_json()
                    if 'data' in demo_data and var in demo_data['data']:
                        results[var] = demo_data['data'][var]
            
            return jsonify({
                'status': 'success',
                'data': results
            })
            
        except Exception as e:
            logger.error(f"Error during data extraction: {e}")
            return generate_demo_data(lat, lon, level, variables)
        
    except Exception as e:
        logger.error(f"Data extraction error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'データ抽出エラー: {str(e)}'
        })

def generate_demo_data(lat, lon, level, variables):
    """デモデータ生成"""
    # 時間軸生成（24時間）
    times = []
    base_time = datetime(2024, 7, 3, 0)
    for i in range(24):
        times.append((base_time + timedelta(hours=i)).strftime('%Y-%m-%d %H:%M:%S'))
    
    results = {}
    
    for var in variables:
        if var == 'u':
            # U成分（東西風）: 正弦波 + ノイズ
            values = [5.0 * np.sin(i * np.pi / 12) + np.random.normal(0, 1) for i in range(24)]
        elif var == 'v':
            # V成分（南北風）: コサイン波 + ノイズ  
            values = [3.0 * np.cos(i * np.pi / 12) + np.random.normal(0, 0.8) for i in range(24)]
        elif var == 'wind_speed':
            # 風速は計算で求める
            continue
        elif var == 'wind_direction':
            # 風向は計算で求める
            continue
        elif var == 't':
            # 気温: 日変化パターン
            values = [288.15 + 10 * np.sin((i - 6) * np.pi / 12) + np.random.normal(0, 0.5) for i in range(24)]
        elif var == 'rh':
            # 相対湿度: 逆相関パターン
            values = [60 + 20 * np.cos((i - 6) * np.pi / 12) + np.random.normal(0, 2) for i in range(24)]
        else:
            # その他の変数
            values = [np.random.normal(10, 2) for _ in range(24)]
        
        if var not in ['wind_speed', 'wind_direction']:
            results[var] = {
                'times': times,
                'values': values,
                'location': {'lat': lat, 'lon': lon},
                'level': level
            }
    
    # 風速・風向計算
    if 'u' in results and 'v' in results:
        wind_data = calculate_wind_from_results(results['u'], results['v'])
        if 'wind_speed' in variables:
            results['wind_speed'] = wind_data['wind_speed']
        if 'wind_direction' in variables:
            results['wind_direction'] = wind_data['wind_direction']
    
    return jsonify({
        'status': 'success',
        'data': results
    })

def calculate_wind_from_results(u_result, v_result):
    """U、V成分の結果から風速・風向を計算"""
    u_values = np.array(u_result['values'])
    v_values = np.array(v_result['values'])
    
    # 風速計算: √(u² + v²)
    wind_speed = np.sqrt(u_values**2 + v_values**2)
    
    # 風向計算: atan2を使用（気象学的な風向）
    # 風向は風が吹いてくる方向を表す
    wind_direction = (270 - np.degrees(np.arctan2(v_values, u_values))) % 360
    
    return {
        'wind_speed': {
            'times': u_result['times'],
            'values': wind_speed.tolist(),
            'location': u_result['location'],
            'level': u_result['level']
        },
        'wind_direction': {
            'times': u_result['times'],
            'values': wind_direction.tolist(),
            'location': u_result['location'],
            'level': u_result['level']
        }
    }

@app.route('/api/all_grid_points')
def get_all_grid_points():
    """全格子点を取得するAPI（ランベルト正角円錐座標、5km格子 633×521）"""
    logger.info("All grid points API called")
    
    try:
        # フォーマットオプション（json or coordinates）
        output_format = request.args.get('format', 'coordinates')
        include_coords = request.args.get('coords', 'true').lower() == 'true'
        
        if not NETCDF_AVAILABLE:
            return jsonify({
                'status': 'error',
                'message': 'NetCDFライブラリが利用できません'
            })
        
        extractor = get_extractor()
        if extractor is None:
            return jsonify({
                'status': 'error',
                'message': 'データ抽出器が利用できません'
            })
        
        try:
            extractor.load_data()
            logger.info("NetCDF data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load NetCDF data: {e}")
            return jsonify({
                'status': 'error',
                'message': f'データ読み込みエラー: {str(e)}'
            })
        
        # 格子点データを取得
        ds = extractor.get_dataset()
        if ds is None:
            return jsonify({
                'status': 'error',
                'message': 'データセットが利用できません'
            })
        
        # 全格子点の緯度・経度データを取得
        lat_data = ds.latitude.values  # 形状: (521, 633)
        lon_data = ds.longitude.values  # 形状: (521, 633)
        
        grid_info = {
            'grid_system': 'ランベルト正角円錐座標',
            'resolution': '5km',
            'dimensions': {
                'x': 633,  # 東西方向
                'y': 521   # 南北方向
            },
            'total_points': 633 * 521
        }
        
        if output_format == 'info':
            # 格子情報のみを返す
            return jsonify({
                'status': 'success',
                'grid_info': grid_info
            })
        
        elif output_format == 'coordinates':
            # 座標のみの軽量形式
            points = []
            for i in range(lat_data.shape[0]):  # Y軸方向（521）
                for j in range(lat_data.shape[1]):  # X軸方向（633）
                    if include_coords:
                        points.append({
                            'i': i,    # Y軸インデックス
                            'j': j,    # X軸インデックス
                            'lat': float(lat_data[i, j]),
                            'lon': float(lon_data[i, j])
                        })
                    else:
                        points.append([i, j])  # インデックスのみ
            
            return jsonify({
                'status': 'success',
                'grid_info': grid_info,
                'points': points,
                'count': len(points)
            })
        
        else:  # full format
            # 詳細な格子点情報
            points = []
            for i in range(lat_data.shape[0]):  # Y軸方向（521）
                for j in range(lat_data.shape[1]):  # X軸方向（633）
                    points.append({
                        'grid_i': i,
                        'grid_j': j,
                        'lat': float(lat_data[i, j]),
                        'lon': float(lon_data[i, j]),
                        'x_index': j,  # X軸インデックス（東西方向）
                        'y_index': i   # Y軸インデックス（南北方向）
                    })
            
            logger.info(f"Retrieved all {len(points)} grid points (633×521)")
            
            return jsonify({
                'status': 'success',
                'grid_info': grid_info,
                'points': points,
                'count': len(points)
            })
        
    except Exception as e:
        logger.error(f"Error getting all grid points: {e}")
        return jsonify({
            'status': 'error',
            'message': f'全格子点取得エラー: {str(e)}'
        })

@app.route('/api/system_info')
def get_system_info():
    """システム・Python環境情報を取得するAPI"""
    import platform
    import pkg_resources
    
    try:
        # Python環境情報
        python_info = {
            'version': sys.version,
            'version_info': {
                'major': sys.version_info.major,
                'minor': sys.version_info.minor,
                'micro': sys.version_info.micro
            },
            'executable': sys.executable,
            'platform': platform.platform(),
            'architecture': platform.architecture(),
            'processor': platform.processor()
        }
        
        # インストール済みパッケージ情報（主要なもののみ）
        key_packages = [
            'xarray', 'netCDF4', 'numpy', 'pandas', 'scipy', 
            'pyproj', 'flask', 'pyyaml', 'pyarrow', 'dask'
        ]
        
        packages_info = {}
        for package in key_packages:
            try:
                version = pkg_resources.get_distribution(package).version
                packages_info[package] = version
            except pkg_resources.DistributionNotFound:
                packages_info[package] = 'Not installed'
        
        # NetCDF処理状況
        netcdf_status = {
            'available': NETCDF_AVAILABLE,
            'extract_module': 'extract.py' if NETCDF_AVAILABLE else 'Not available'
        }
        
        return jsonify({
            'status': 'success',
            'python': python_info,
            'packages': packages_info,
            'netcdf': netcdf_status,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return jsonify({
            'status': 'error',
            'message': f'システム情報取得エラー: {str(e)}'
        })

if __name__ == '__main__':
    logger.info("Starting optimized weather app...")
    
    # NetCDF利用可能性をログ出力
    if NETCDF_AVAILABLE:
        logger.info("NetCDF processing enabled")
    else:
        logger.info("Running in demo mode (NetCDF not available)")
    
    app.run(debug=True, host='127.0.0.1', port=8000)