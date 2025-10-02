#!/bin/bash

# 仮想環境セットアップスクリプト

echo "🛠️  Python 3.11 仮想環境セットアップ"

# Python 3.11の存在確認
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11が見つかりません。インストールしてください。"
    exit 1
fi

echo "✅ Python 3.11が利用可能: $(python3.11 --version)"

# 仮想環境の作成
if [ ! -d "venv_py311" ]; then
    echo "📦 Python 3.11仮想環境を作成中..."
    python3.11 -m venv venv_py311
    echo "✅ 仮想環境が作成されました: venv_py311/"
else
    echo "✅ 仮想環境は既に存在します: venv_py311/"
fi

# 仮想環境のアクティベート
echo "🔧 仮想環境をアクティベート中..."
source venv_py311/bin/activate

# pipのアップグレード
echo "📥 pipを最新版にアップグレード中..."
pip install --upgrade pip

# 必要なパッケージのインストール
if [ -f "requirements_minimal.txt" ]; then
    echo "📦 必要なパッケージをインストール中..."
    pip install -r requirements_minimal.txt
    echo "✅ パッケージのインストール完了"
else
    echo "❌ requirements_minimal.txt が見つかりません"
    exit 1
fi

# インストール済みパッケージの確認
echo ""
echo "📋 インストール済みパッケージ (主要なもの):"
python -c "
import pkg_resources

packages = ['xarray', 'netCDF4', 'numpy', 'pandas', 'scipy', 'pyproj', 'flask', 'PyYAML', 'pyarrow', 'dask', 'matplotlib']

for package in packages:
    try:
        version = pkg_resources.get_distribution(package).version
        print(f'  ✅ {package}: {version}')
    except pkg_resources.DistributionNotFound:
        print(f'  ❌ {package}: Not installed')
"

echo ""
echo "🎉 セットアップ完了！"
echo ""
echo "📝 使用方法:"
echo "  起動: ./start_venv.sh"
echo "  または: source venv_py311/bin/activate && python app_optimized.py"
echo ""
echo "🌐 アクセスURL: http://localhost:8000"