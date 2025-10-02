#!/bin/bash

# 気象データ抽出システム起動スクリプト (Python 3.11仮想環境版)

echo "🌤️  気象データ抽出システム v2.0 を起動中..."
echo "📍 プロジェクトディレクトリ: $(pwd)"

# 仮想環境の存在確認
if [ ! -d "venv_py311" ]; then
    echo "❌ 仮想環境が見つかりません。仮想環境を作成してください。"
    echo "   作成方法: python3.11 -m venv venv_py311"
    exit 1
fi

echo "🐍 Python 3.11 仮想環境をアクティベート中..."
source venv_py311/bin/activate

echo "📦 Python環境情報:"
echo "   バージョン: $(python --version)"
echo "   実行ファイル: $(which python)"

echo "🔍 必要なライブラリの確認..."
python -c "
try:
    import xarray, netCDF4, numpy, pandas, scipy, pyproj, flask
    print('✅ すべての必要なライブラリが利用可能です')
except ImportError as e:
    print(f'❌ 必要なライブラリが不足しています: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "📥 必要なパッケージをインストールしてください:"
    echo "   pip install -r requirements_minimal.txt"
    exit 1
fi

echo "🚀 アプリケーションを起動中..."
echo "   アクセスURL: http://localhost:8000"
echo "   停止方法: Ctrl+C"
echo ""

python app_optimized.py