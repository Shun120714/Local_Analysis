#!/usr/bin/env python3
"""
格子点表示のテストスクリプト
"""

import sys
from pathlib import Path
from extract import DataExtractor

def test_grid_points():
    """平均化時の格子点情報取得をテスト"""
    
    # DataExtractorを初期化
    extractor = DataExtractor('use_nc')
    
    # データを読み込み
    extractor.load_data()
    
    # テスト地点: 東京
    lat = 35.6762
    lon = 139.6503
    
    print(f"=== 格子点情報取得テスト ===")
    print(f"対象地点: 緯度 {lat}, 経度 {lon}")
    
    # 1. 最近傍法
    print(f"\n1. 最近傍法:")
    try:
        grid_points = extractor.get_extraction_grid_points(lat, lon, 'nearest')
        print(f"格子点数: {len(grid_points)}")
        for i, point in enumerate(grid_points):
            print(f"  {i+1}: {point}")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 2. 半径平均法 (10km)
    print(f"\n2. 半径平均法 (10km):")
    try:
        grid_points = extractor.get_extraction_grid_points(lat, lon, 'mean', radius_km=10)
        print(f"格子点数: {len(grid_points)}")
        for i, point in enumerate(grid_points[:3]):  # 最初の3点のみ表示
            print(f"  {i+1}: {point}")
        if len(grid_points) > 3:
            print(f"  ... (他 {len(grid_points) - 3} 点)")
    except Exception as e:
        print(f"エラー: {e}")
    
    # 3. k近傍法 (5点)
    print(f"\n3. k近傍法 (5点):")
    try:
        grid_points = extractor.get_extraction_grid_points(lat, lon, 'mean', k_neighbors=5)
        print(f"格子点数: {len(grid_points)}")
        for i, point in enumerate(grid_points):
            print(f"  {i+1}: {point}")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    test_grid_points()