#!/usr/bin/env python3
"""
重み付き平均機能のテストスクリプト
"""

import numpy as np
import math
from extract import WeightedAverager

def test_weighted_averager():
    """WeightedAveragerクラスのテスト"""
    
    print("🧪 重み付き平均機能のテスト")
    print("=" * 50)
    
    # テストデータの作成
    target_lat = 35.0
    target_lon = 139.0
    
    # 周辺格子点（東京周辺の仮想データ）
    grid_lats = np.array([34.9, 35.0, 35.1, 34.95, 35.05])
    grid_lons = np.array([138.9, 139.0, 139.1, 139.05, 138.95])
    
    print(f"目標地点: ({target_lat}°, {target_lon}°)")
    print(f"格子点数: {len(grid_lats)}")
    print()
    
    # 距離計算テスト
    print("📏 距離計算テスト")
    print("-" * 30)
    for i in range(len(grid_lats)):
        R = 6371.0  # 地球半径 (km)
        lat1_rad = math.radians(target_lat)
        lon1_rad = math.radians(target_lon)
        lat2_rad = math.radians(grid_lats[i])
        lon2_rad = math.radians(grid_lons[i])
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        print(f"格子点{i+1}: ({grid_lats[i]:.2f}°, {grid_lons[i]:.2f}°) -> {distance:.2f} km")
    print()
    
    # 逆距離重み付けテスト
    print("⚖️  逆距離重み付けテスト")
    print("-" * 30)
    weights = WeightedAverager.calculate_weights(
        target_lat, target_lon, grid_lats, grid_lons, method='inverse_distance'
    )
    
    for i in range(len(weights)):
        print(f"格子点{i+1}: 重み = {weights[i]:.4f}")
    
    print(f"重みの合計: {np.sum(weights):.6f} (1.0に近いか確認)")
    print()
    
    # ガウシアン重み付けテスト
    print("🔔 ガウシアン重み付けテスト")
    print("-" * 30)
    weights_gaussian = WeightedAverager.calculate_weights(
        target_lat, target_lon, grid_lats, grid_lons, method='gaussian'
    )
    
    for i in range(len(weights_gaussian)):
        print(f"格子点{i+1}: 重み = {weights_gaussian[i]:.4f}")
    
    print(f"重みの合計: {np.sum(weights_gaussian):.6f} (1.0に近いか確認)")
    print()
    
    # 等重み（従来方式）テスト
    print("📊 等重み（従来方式）テスト")
    print("-" * 30)
    weights_equal = WeightedAverager.calculate_weights(
        target_lat, target_lon, grid_lats, grid_lons, method='equal'
    )
    
    for i in range(len(weights_equal)):
        print(f"格子点{i+1}: 重み = {weights_equal[i]:.4f}")
    
    print(f"重みの合計: {np.sum(weights_equal):.6f} (1.0に近いか確認)")
    print()
    
    # 重み付き平均の計算例
    print("🧮 重み付き平均計算例")
    print("-" * 30)
    
    # 仮想的な気温データ（°C）
    temperature_data = np.array([25.1, 25.0, 24.9, 25.05, 24.95])
    
    # 各方法での平均値計算
    avg_inverse = np.sum(temperature_data * weights)
    avg_gaussian = np.sum(temperature_data * weights_gaussian)
    avg_equal = np.sum(temperature_data * weights_equal)
    avg_simple = np.mean(temperature_data)
    
    print(f"気温データ: {temperature_data}")
    print(f"逆距離重み平均: {avg_inverse:.3f}°C")
    print(f"ガウシアン重み平均: {avg_gaussian:.3f}°C")
    print(f"等重み平均: {avg_equal:.3f}°C")
    print(f"単純算術平均: {avg_simple:.3f}°C")
    
    print()
    print("✅ 重み付き平均機能テスト完了!")

if __name__ == "__main__":
    test_weighted_averager()