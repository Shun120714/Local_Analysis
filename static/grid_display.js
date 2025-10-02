/* 格子点表示機能専用JavaScript */

// 格子点表示のための変数（競合を避けるためプレフィックス付き）
let gridAllGridPoints = null;
let gridIsLoadingAllGridPoints = false;
let gridMainPointsLayer = null;
let gridAllPointsLayer = null;
let gridUsedPointsLayer = null;  // 使用された格子点のレイヤー
let gridCurrentDensity = 'auto';
let gridAutoMode = true;
let gridUsedPoints = [];  // 使用された格子点のデータ

// 格子点表示のオン/オフ
function onGridPointsDisplayChange() {
    const showGrid = document.getElementById('showGridPoints').checked;
    const densityOptions = document.getElementById('gridDensityOptions');
    
    console.log('Grid points display changed:', showGrid);
    console.log('Density options element:', densityOptions);
    
    if (showGrid) {
        if (densityOptions) {
            densityOptions.style.display = 'block';
            densityOptions.style.visibility = 'visible';
            console.log('Density options shown, current style:', densityOptions.style.cssText);
        } else {
            console.error('Density options element not found');
        }
        if (!gridAllGridPoints && !gridIsLoadingAllGridPoints) {
            loadAllGridPoints();
        } else if (gridAllGridPoints) {
            displayAllGridPoints();
        }
    } else {
        if (densityOptions) {
            densityOptions.style.display = 'none';
            console.log('Density options hidden');
        }
        hideAllGridPoints();
    }
}

// 全格子点の読み込み
async function loadAllGridPoints() {
    if (gridIsLoadingAllGridPoints) return;
    
    gridIsLoadingAllGridPoints = true;
    console.log('Loading all grid points...');
    
    try {
        const response = await fetch('/api/all_grid_points?format=full');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('API response:', data);
        
        if (data.status === 'success' && data.points) {
            gridAllGridPoints = data.points;
            console.log(`Loaded ${gridAllGridPoints.length} grid points`);
            displayAllGridPoints();
        } else {
            throw new Error(data.message || 'Failed to load grid points');
        }
    } catch (error) {
        console.error('Error loading all grid points:', error);
    } finally {
        gridIsLoadingAllGridPoints = false;
    }
}

// 全格子点の表示
function displayAllGridPoints() {
    if (!gridAllGridPoints || typeof map === 'undefined') {
        console.log('Grid points not loaded or map not available');
        return;
    }
    
    // 既存レイヤーをクリア
    if (gridAllPointsLayer) {
        map.removeLayer(gridAllPointsLayer);
    }
    
    // 密度設定の取得
    const densitySelect = document.getElementById('gridDensity');
    const selectedDensity = densitySelect ? densitySelect.value : 'auto';
    
    console.log(`Displaying all grid points - current density: ${selectedDensity}, auto mode: ${selectedDensity === 'auto'}`);
    
    // ステップサイズの決定
    let step;
    if (selectedDensity === 'auto') {
        const zoom = map.getZoom();
        if (zoom >= 8) step = 1;
        else if (zoom >= 7) step = 2;
        else if (zoom >= 6) step = 4;
        else step = 8;
        console.log(`Auto mode: zoom=${zoom}, step=${step}`);
    } else {
        step = parseInt(selectedDensity);
        console.log(`Manual mode: step=${step}`);
    }
    
    // 使用された格子点のインデックスセットを作成（高速検索用）
    const usedPointsSet = new Set();
    if (gridUsedPoints && gridUsedPoints.length > 0) {
        gridUsedPoints.forEach(point => {
            const key = `${point.grid_i || point.i}_${point.grid_j || point.j}`;
            usedPointsSet.add(key);
        });
    }
    
    // レイヤーグループを作成
    gridAllPointsLayer = L.layerGroup();
    
    let displayedCount = 0;
    let usedCount = 0;
    
    for (let i = 0; i < gridAllGridPoints.length; i += step) {
        const point = gridAllGridPoints[i];
        const pointKey = `${point.grid_i}_${point.grid_j}`;
        const isUsedPoint = usedPointsSet.has(pointKey);
        
        // 使用された格子点は赤色、通常の格子点は青色
        const circle = L.circleMarker([point.lat, point.lon], {
            radius: isUsedPoint ? 4 : 2,
            fillColor: isUsedPoint ? '#ff0000' : '#0066cc',
            color: isUsedPoint ? '#ff0000' : '#0066cc',
            weight: isUsedPoint ? 2 : 1,
            opacity: isUsedPoint ? 0.9 : 0.6,
            fillOpacity: isUsedPoint ? 0.8 : 0.6
        });
        
        const popupContent = isUsedPoint ? 
            `<strong>使用格子点</strong><br>
             緯度: ${point.lat.toFixed(4)}°<br>
             経度: ${point.lon.toFixed(4)}°<br>
             グリッド: [${point.grid_i}, ${point.grid_j}]<br>
             <span style="color: red;">★ データ抽出で使用</span>` :
            `<strong>格子点</strong><br>
             緯度: ${point.lat.toFixed(4)}°<br>
             経度: ${point.lon.toFixed(4)}°<br>
             グリッド: [${point.grid_i}, ${point.grid_j}]`;
        
        circle.bindPopup(popupContent);
        
        gridAllPointsLayer.addLayer(circle);
        displayedCount++;
        
        if (isUsedPoint) {
            usedCount++;
        }
    }
    
    gridAllPointsLayer.addTo(map);
    console.log(`Displayed ${displayedCount} grid points (step=${step}), including ${usedCount} used points in red`);
}

// 全格子点の非表示
function hideAllGridPoints() {
    if (gridAllPointsLayer && typeof map !== 'undefined') {
        map.removeLayer(gridAllPointsLayer);
        gridAllPointsLayer = null;
        console.log('All grid points hidden');
    }
    
    // 使用された格子点レイヤーも非表示
    hideUsedGridPoints();
}

// 使用された格子点を更新
function updateUsedGridPoints(usedPoints) {
    gridUsedPoints = usedPoints || [];
    console.log(`Updated used grid points: ${gridUsedPoints.length} points`);
    
    // 全格子点が表示されている場合は再描画
    if (gridAllPointsLayer && document.getElementById('showGridPoints').checked) {
        displayAllGridPoints();
    }
}

// 使用された格子点レイヤーを表示
function displayUsedGridPoints() {
    if (!gridUsedPoints || gridUsedPoints.length === 0 || typeof map === 'undefined') {
        return;
    }
    
    // 既存の使用済み格子点レイヤーをクリア
    if (gridUsedPointsLayer) {
        map.removeLayer(gridUsedPointsLayer);
    }
    
    gridUsedPointsLayer = L.layerGroup();
    
    gridUsedPoints.forEach((point, index) => {
        const circle = L.circleMarker([point.lat, point.lon], {
            radius: 4,
            fillColor: '#ff0000',  // 赤色
            color: '#ff0000',
            weight: 2,
            opacity: 0.9,
            fillOpacity: 0.8
        });
        
        circle.bindPopup(`
            <strong>使用格子点 #${index + 1}</strong><br>
            緯度: ${point.lat.toFixed(4)}°<br>
            経度: ${point.lon.toFixed(4)}°<br>
            グリッド: [${point.grid_i || point.i || 'N/A'}, ${point.grid_j || point.j || 'N/A'}]<br>
            距離: ${point.distance ? point.distance.toFixed(1) + ' km' : 'N/A'}<br>
            抽出方法: ${point.method || 'N/A'}
        `);
        
        gridUsedPointsLayer.addLayer(circle);
    });
    
    gridUsedPointsLayer.addTo(map);
    console.log(`Displayed ${gridUsedPoints.length} used grid points in red`);
}

// 使用された格子点レイヤーを非表示
function hideUsedGridPoints() {
    if (gridUsedPointsLayer && typeof map !== 'undefined') {
        map.removeLayer(gridUsedPointsLayer);
        gridUsedPointsLayer = null;
        console.log('Used grid points hidden');
    }
}

// 初期化
document.addEventListener('DOMContentLoaded', function() {
    console.log('Grid display script loaded');
    
    // 要素の存在確認
    const showGridElement = document.getElementById('showGridPoints');
    const densityOptionsElement = document.getElementById('gridDensityOptions');
    const densitySelectElement = document.getElementById('gridDensity');
    
    console.log('showGridPoints element:', showGridElement);
    console.log('gridDensityOptions element:', densityOptionsElement);
    console.log('gridDensity element:', densitySelectElement);
    
    if (densityOptionsElement) {
        console.log('Density options current style:', densityOptionsElement.style.display);
    }
    
    // 格子点表示のイベントリスナー
    if (showGridElement) {
        showGridElement.addEventListener('change', onGridPointsDisplayChange);
        console.log('Grid points display event listener added');
    } else {
        console.error('showGridPoints element not found');
    }
    
    // 格子密度選択のイベントリスナー
    if (densitySelectElement) {
        densitySelectElement.addEventListener('change', function() {
            console.log('Grid density changed to:', this.value);
            if (gridAllGridPoints && document.getElementById('showGridPoints').checked) {
                console.log('Redisplaying grid points with new density');
                displayAllGridPoints();
            } else {
                console.log('Grid points not loaded or not displayed');
            }
        });
        console.log('Grid density event listener added');
    } else {
        console.error('gridDensity element not found');
    }
    
    console.log('Grid display initialization completed');
});

// デバッグ用：密度オプションを強制表示
function forceShowDensityOptions() {
    const densityOptions = document.getElementById('gridDensityOptions');
    if (densityOptions) {
        densityOptions.style.display = 'block';
        densityOptions.style.visibility = 'visible';
        console.log('Density options forced to show');
    } else {
        console.error('Density options element not found');
    }
}

// グローバル関数として公開（他のスクリプトから呼び出し可能）
window.updateUsedGridPoints = updateUsedGridPoints;
window.displayUsedGridPoints = displayUsedGridPoints;
window.hideUsedGridPoints = hideUsedGridPoints;