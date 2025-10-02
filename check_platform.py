#!/usr/bin/env python3
"""
クロスプラットフォーム対応確認スクリプト
Windows/macOS/Linuxでの動作を確認
"""

import sys
import platform
import os
from pathlib import Path

def check_platform():
    """プラットフォーム情報の表示"""
    print("🖥️  システム情報")
    print("=" * 50)
    print(f"OS: {platform.system()} {platform.release()}")
    print(f"アーキテクチャ: {platform.machine()}")
    print(f"Python: {platform.python_version()}")
    print(f"Python実行ファイル: {sys.executable}")
    print()

def check_scripts():
    """起動スクリプトの存在確認"""
    print("📁 起動スクリプト確認")
    print("=" * 50)
    
    scripts = {
        "Unix系 (macOS/Linux)": ["setup_venv.sh", "start_venv.sh"],
        "Windows (バッチ)": ["setup_venv.bat", "start_venv.bat"],
        "Windows (PowerShell)": ["setup_venv.ps1", "start_venv.ps1"]
    }
    
    for platform_name, script_list in scripts.items():
        print(f"\n{platform_name}:")
        for script in script_list:
            if Path(script).exists():
                print(f"  ✅ {script}")
            else:
                print(f"  ❌ {script} (見つかりません)")

def check_dependencies():
    """必要な依存関係の確認"""
    print("\n📦 依存関係確認")
    print("=" * 50)
    
    required_packages = [
        'xarray', 'netCDF4', 'numpy', 'pandas', 
        'scipy', 'pyproj', 'flask', 'PyYAML'
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (インストールが必要)")

def recommend_setup():
    """プラットフォーム別推奨セットアップの表示"""
    print("\n🚀 推奨セットアップ方法")
    print("=" * 50)
    
    system = platform.system()
    
    if system == "Windows":
        print("Windows環境:")
        print("  1. setup_venv.bat  (推奨)")
        print("  2. setup_venv.ps1  (PowerShell)")
        print("\n起動方法:")
        print("  1. start_venv.bat  (推奨)")
        print("  2. start_venv.ps1  (PowerShell)")
        print("\n詳細ガイド: WINDOWS_SETUP.md")
        
    elif system == "Darwin":  # macOS
        print("macOS環境:")
        print("  1. ./setup_venv.sh")
        print("\n起動方法:")
        print("  1. ./start_venv.sh")
        print("\n詳細ガイド: VENV_SETUP.md")
        
    elif system == "Linux":
        print("Linux環境:")
        print("  1. ./setup_venv.sh")
        print("\n起動方法:")
        print("  1. ./start_venv.sh")
        print("\n詳細ガイド: VENV_SETUP.md")
        
    else:
        print(f"未サポートOS: {system}")
        print("手動セットアップが必要です")

def check_venv():
    """仮想環境の確認"""
    print("\n🐍 仮想環境確認")
    print("=" * 50)
    
    venv_path = Path("venv_py311")
    
    if venv_path.exists():
        print("✅ 仮想環境が存在します: venv_py311/")
        
        # アクティベーションスクリプトの確認
        system = platform.system()
        if system == "Windows":
            activate_script = venv_path / "Scripts" / "activate.bat"
            ps_script = venv_path / "Scripts" / "Activate.ps1"
            print(f"  バッチファイル: {'✅' if activate_script.exists() else '❌'}")
            print(f"  PowerShell: {'✅' if ps_script.exists() else '❌'}")
        else:
            activate_script = venv_path / "bin" / "activate"
            print(f"  アクティベーションスクリプト: {'✅' if activate_script.exists() else '❌'}")
    else:
        print("❌ 仮想環境が見つかりません")
        print("   セットアップスクリプトを実行してください")

def main():
    """メイン実行関数"""
    print("🌤️  MSM気象データ抽出システム - クロスプラットフォーム対応確認")
    print("=" * 70)
    print()
    
    check_platform()
    check_scripts()
    check_venv()
    check_dependencies()
    recommend_setup()
    
    print("\n" + "=" * 70)
    print("確認完了！推奨されたセットアップ方法をご利用ください。")

if __name__ == "__main__":
    main()