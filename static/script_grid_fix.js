// 格子点表示機能の修正版

// 格子点表示関連の変数
let allGridPoints = null;
let gridPointsLayer = null;
let nearbyGridPointsLayer = null;
let isLoadingAllGridPoints = false;

// 格子点表示のオン/オフ
function onGridPointsDisplayChange() {
    const showGrid = document.getElementById('showGridPoints').checked;
    const densityOptions = document.getElementById('gridDensityOptions');
    
    if (showGrid) {
        if (densityOptions) densityOptions.style.display = 'block';
        if (!allGridPoints && !isLoadingAllGridPoints) {
            loadAllGridPoints();
        } else if (allGridPoints) {
            displayAllGridPoints();
        }
    } else {
        if (densityOptions) densityOptions.style.display = 'none';
        hideAllGridPoints();
    }
}

// 格子密度が変更された時の処理
function onGridDensityChange() {
    if (allGridPoints && document.getElementById('showGridPoints').checked) {
        displayAllGridPoints();
    }
}

// 全格子点を読み込み
async function loadAllGridPoints() {
    if (isLoadingAllGridPoints) return;
    
    isLoadingAllGridPoints = true;
    
    try {
        console.log('全格子点を読み込み中...');
        
        // 座標のみの軽量形式で取得
        const response = await fetch('/api/all_grid_points?format=coordinates&coords=true');
        const data = await response.json();
        
        if (data.status === 'success') {
            allGridPoints = data;
            console.log(`格子点読み込み完了: ${data.count}点 (${data.grid_info.dimensions.x}×${data.grid_info.dimensions.y})`);
            displayAllGridPoints();
        } else {
            console.error(`格子点読み込みエラー: ${data.message}`);
        }
    } catch (error) {
        console.error(`格子点読み込みエラー: ${error.message}`);
    } finally {
        isLoadingAllGridPoints = false;
    }
}

// 全格子点を地図に表示（修正版）
function displayAllGridPoints() {
    if (!allGridPoints || !map) return;
    
    hideAllGridPoints(); // 既存のレイヤーを削除
    
    const points = allGridPoints.points;
    const markers = [];
    
    // 密度設定を取得
    const densitySelect = document.getElementById('gridDensity');
    const currentZoom = map.getZoom();
    let step = 1;
    
    if (densitySelect && densitySelect.value !== 'auto') {
        // 手動設定
        step = parseInt(densitySelect.value);
    } else {
        // 自動設定（ズーム連動、5km格子に最適化）
        if (currentZoom < 7) step = 8;         // 約40km間隔
        else if (currentZoom < 9) step = 4;    // 約20km間隔  
        else if (currentZoom < 11) step = 2;   // 約10km間隔
        else step = 1;                         // 5km間隔（全表示）
    }
    
    for (let i = 0; i < points.length; i += step) {
        const point = points[i];
        
        // ズームレベルに応じてマーカーサイズを調整
        let radius = 2;
        if (currentZoom >= 11) radius = 3;
        else if (currentZoom >= 9) radius = 2.5;
        
        const marker = L.circleMarker([point.lat, point.lon], {
            radius: radius,
            fillColor: '#3388ff',
            color: '#ffffff',
            weight: 1,
            opacity: 0.8,
            fillOpacity: 0.6
        });
        
        marker.bindPopup(`
            格子点 [${point.i}, ${point.j}]<br>
            緯度: ${point.lat.toFixed(4)}°<br>
            経度: ${point.lon.toFixed(4)}°<br>
            格子間隔: 約5km
        `);
        
        markers.push(marker);
    }
    
    gridPointsLayer = L.layerGroup(markers).addTo(map);
    
    // 格子点密度情報を表示
    const displayedPoints = Math.ceil(points.length / step);
    const gridSpacing = step * 5; // km
    console.log(`格子点表示: ${displayedPoints}点, 表示間隔: 約${gridSpacing}km`);
    
    // ズーム変更時に再描画（自動モードのみ）
    map.off('zoomend.gridpoints');
    if (!densitySelect || densitySelect.value === 'auto') {
        map.on('zoomend.gridpoints', () => {
            if (document.getElementById('showGridPoints').checked) {
                displayAllGridPoints();
            }
        });
    }
}

// 全格子点表示を非表示
function hideAllGridPoints() {
    if (gridPointsLayer) {
        map.removeLayer(gridPointsLayer);
        gridPointsLayer = null;
    }
    map.off('zoomend.gridpoints');
}

// イベントリスナーの追加
document.addEventListener('DOMContentLoaded', function() {
    // 格子点表示チェックボックス
    const showGridCheckbox = document.getElementById('showGridPoints');
    if (showGridCheckbox) {
        showGridCheckbox.addEventListener('change', onGridPointsDisplayChange);
    }
    
    // 格子密度選択
    const gridDensitySelect = document.getElementById('gridDensity');
    if (gridDensitySelect) {
        gridDensitySelect.addEventListener('change', onGridDensityChange);
    }
});