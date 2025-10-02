#!/usr/bin/env python3
"""
WebアプリケーションのAPIテストスクリプト
"""

import requests
import json

def test_api_extraction():
    """API経由でデータ抽出と格子点情報取得をテスト"""
    
    base_url = "http://localhost:8000"
    
    # テストデータ - 平均化方法（半径指定）
    test_data = {
        "lat": 35.6762,
        "lon": 139.6503,
        "dataType": "surface",
        "variables": ["ta", "rh"],
        "method": "mean",
        "radiusKm": 10,
        "timeMode": "single",
        "timeSingle": "2024-07-03T12:00",
        "outputFormat": "json"
    }
    
    print("=== WebアプリケーションAPIテスト ===")
    print(f"テストデータ: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
    
    try:
        # データ抽出API呼び出し
        print("\n1. データ抽出API呼び出し:")
        response = requests.post(f"{base_url}/api/extract", json=test_data, timeout=30)
        
        print(f"ステータスコード: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"レスポンス構造: {list(result.keys())}")
            
            if 'metadata' in result and 'used_grid_points' in result['metadata']:
                grid_points = result['metadata']['used_grid_points']
                print(f"使用格子点数: {len(grid_points)}")
                
                if grid_points:
                    print("最初の格子点:")
                    print(f"  {grid_points[0]}")
                    
                    if len(grid_points) > 1:
                        print("最後の格子点:")
                        print(f"  {grid_points[-1]}")
                else:
                    print("格子点情報が空です")
            else:
                print("格子点情報がメタデータに含まれていません")
        else:
            print(f"APIエラー: {response.text}")
            
    except Exception as e:
        print(f"テストエラー: {e}")

if __name__ == "__main__":
    test_api_extraction()