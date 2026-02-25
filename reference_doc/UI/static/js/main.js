/**
 * FANOUT Shuttle Service AOI 影像辨識系統 JavaScript
 * Author: ITRI EOSL Rachel A30335
 * Date: 2025-12-02
 */

// ========== 全域變數 ==========
let currentAnalysisData = null;
let currentImageFiles = {
    combined: null,
    overlay: null,
    mask: null
};
let currentOriginalFile = null;
let currentMode = 'single'; // 'single' 或 'batch'
let batchResults = null;

// 多檢視器支援
const viewers = {
    original: {
        zoom: 1.0,
        grayscale: false,
        canvas: null,
        context: null
    },
    combined: {
        zoom: 1.0,
        grayscale: false,
        canvas: null,
        context: null
    }
};

// ========== 頁面載入初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log('FANOUT AOI System Initialized');
    
    // 檢查系統狀態
    checkSystemStatus();
    
    // 初始化拖拽功能
    initDragAndDrop();
    
    // 初始化文件選擇處理
    initFileSelection();
    
    // 初始化鍵盤快捷鍵
    initKeyboardShortcuts();
    
    // 顯示歡迎訊息
    showStatus('系統已準備就緒，請上傳 AOI 影像進行瑕疵檢測', 'info');
});

// ========== 系統狀態檢查 ==========
function checkSystemStatus() {
    fetch('/health')
        .then(response => response.json())
        .then(data => {
            updateSystemStatus(data);
        })
        .catch(error => {
            console.error('Health check error:', error);
            updateSystemStatus({
                model_loaded: false,
                device: 'unknown',
                status: 'error'
            });
        });
}

function updateSystemStatus(data) {
    // 更新模型狀態
    const modelStatus = document.getElementById('modelStatus');
    const modelIndicator = document.getElementById('modelIndicator');
    
    if (data.model_loaded) {
        modelStatus.innerHTML = '<span class="status-indicator status-online" id="modelIndicator"></span> 已載入';
        modelIndicator.className = 'status-indicator status-online';
    } else {
        modelStatus.innerHTML = '<span class="status-indicator status-offline" id="modelIndicator"></span> 未載入';
        modelIndicator.className = 'status-indicator status-offline';
    }
    
    // 更新設備狀態
    const deviceStatus = document.getElementById('deviceStatus');
    deviceStatus.textContent = data.device === 'cuda' ? 'GPU (CUDA)' : 'CPU';
}

// ========== 拖拽功能 ==========
function initDragAndDrop() {
    const uploadArea = document.getElementById('uploadArea');
    
    // 防止預設行為
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    // 高亮顯示
    ['dragenter', 'dragover'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.add('drag-over');
        }, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        uploadArea.addEventListener(eventName, () => {
            uploadArea.classList.remove('drag-over');
        }, false);
    });
    
    // 處理檔案放置
    uploadArea.addEventListener('drop', handleDrop, false);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    
    if (files.length > 0) {
        const fileInput = document.getElementById('imageInput');
        fileInput.files = files;
        showStatus(`已選擇文件: ${files[0].name}`, 'info');
    }
}

// ========== 文件選擇處理 ==========
function initFileSelection() {
    const fileInput = document.getElementById('imageInput');
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            currentOriginalFile = file;
            showStatus(`已選擇文件: ${file.name} (${formatFileSize(file.size)})`, 'info');
            
            // 顯示檔案預覽
            previewImage(file);
        }
    });
    
    // 批次檔案選擇
    const batchFileInput = document.getElementById('batchImageInput');
    batchFileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (files.length > 0) {
            displayFileList(files);
            showStatus(`已選擇 ${files.length} 個文件`, 'info');
        }
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function previewImage(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        // 可在此處添加影像預覽功能
        console.log('Image loaded for preview');
    };
    reader.readAsDataURL(file);
}

// ========== 影像分析主函數 ==========
function analyzeImage() {
    if (currentMode === 'batch') {
        analyzeBatchImages();
    } else {
        analyzeSingleImage();
    }
}

function analyzeSingleImage() {
    const fileInput = document.getElementById('imageInput');
    const file = fileInput.files[0];
    
    // 驗證文件
    if (!file) {
        showStatus('請先選擇一張影像', 'error');
        return;
    }
    
    // 驗證文件類型
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
        showStatus('不支援的文件格式，請上傳 JPG、PNG、BMP 或 TIFF 格式', 'error');
        return;
    }
    
    // 驗證文件大小 (50MB)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
        showStatus('文件過大，請確保文件小於 50MB', 'error');
        return;
    }
    
    // 儲存原始檔案
    currentOriginalFile = file;
    
    // 建立 FormData
    const formData = new FormData();
    formData.append('image', file);
    
    // 顯示載入狀態
    showLoading(true);
    hideResults();
    
    // 禁用按鈕
    const analyzeBtn = document.getElementById('analyzeBtn');
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 處理中...';
    
    // 更新載入詳情
    updateLoadingDetail('上傳影像中...');
    
    // 發送請求
    fetch('/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || '伺服器錯誤');
            });
        }
        return response.json();
    })
    .then(data => {
        updateLoadingDetail('處理完成，正在顯示結果...');
        
        if (data.success) {
            // 儲存分析數據
            currentAnalysisData = data;
            
            // 顯示結果
            displayResults(data);
            showStatus('分析完成！檢測到 ' + data.total_defects + ' 個瑕疵', 'success');
        } else {
            showStatus('分析失敗: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Analysis error:', error);
        showStatus('處理錯誤: ' + error.message, 'error');
    })
    .finally(() => {
        // 恢復按鈕狀態
        showLoading(false);
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-search"></i> 開始分析';
    });
}

function analyzeBatchImages() {
    const fileInput = document.getElementById('batchImageInput');
    const files = fileInput.files;
    
    // 驗證文件
    if (!files || files.length === 0) {
        showStatus('請先選擇要分析的影像', 'error');
        return;
    }
    
    // 驗證文件類型和大小
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/tiff'];
    const maxSize = 50 * 1024 * 1024;
    
    for (let file of files) {
        if (!allowedTypes.includes(file.type)) {
            showStatus(`文件 ${file.name} 格式不支援`, 'error');
            return;
        }
        if (file.size > maxSize) {
            showStatus(`文件 ${file.name} 過大（超過 50MB）`, 'error');
            return;
        }
    }
    
    // 建立 FormData
    const formData = new FormData();
    for (let file of files) {
        formData.append('images', file);
    }
    
    // 顯示載入狀態
    showLoading(true);
    hideResults();
    
    // 禁用按鈕
    const analyzeBtn = document.getElementById('analyzeBtn');
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 批次處理中...';
    
    // 更新載入詳情
    updateLoadingDetail(`正在處理 ${files.length} 張影像...`);
    
    // 發送請求
    fetch('/upload/batch', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || '伺服器錯誤');
            });
        }
        return response.json();
    })
    .then(data => {
        updateLoadingDetail('批次處理完成，正在顯示結果...');
        
        if (data.success) {
            // 儲存批次結果
            batchResults = data;
            
            // 顯示批次結果
            displayBatchResults(data);
            showStatus(`批次分析完成！成功: ${data.processed}, 失敗: ${data.failed}`, 'success');
        } else {
            showStatus('批次分析失敗: ' + data.error, 'error');
        }
    })
    .catch(error => {
        console.error('Batch analysis error:', error);
        showStatus('批次處理錯誤: ' + error.message, 'error');
    })
    .finally(() => {
        // 恢復按鈕狀態
        showLoading(false);
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="fas fa-search"></i> 開始分析';
    });
}

// ========== 結果顯示 ==========
function displayResults(data) {
    // 顯示統計卡片
    document.getElementById('totalDefects').textContent = data.total_defects;
    document.getElementById('processingTime').textContent = data.processing_time.toFixed(2) + ' 秒';
    
    // 顯示時間戳
    const timestamp = new Date(data.timestamp);
    document.getElementById('analysisTime').textContent = timestamp.toLocaleString('zh-TW');
    
    // 顯示影像尺寸
    if (data.analysis_results && data.analysis_results.image_shape) {
        const shape = data.analysis_results.image_shape;
        document.getElementById('imageSize').textContent = 
            `${shape.width} × ${shape.height}`;
    }
    
    // 顯示原始影像
    if (currentOriginalFile) {
        const reader = new FileReader();
        reader.onload = function(e) {
            document.getElementById('originalImg').src = e.target.result;
            setTimeout(() => initImageViewer('original'), 100);
        };
        reader.readAsDataURL(currentOriginalFile);
    }
    
    // 顯示分析結果影像
    document.getElementById('combinedImg').src = 'data:image/png;base64,' + data.combined_image;
    document.getElementById('overlayImg').src = 'data:image/png;base64,' + data.overlay_image;
    document.getElementById('maskImg').src = 'data:image/png;base64,' + data.mask_image;
    
    // 儲存 base64 資料供下載使用
    currentImageFiles = {
        combined: data.combined_image,
        overlay: data.overlay_image,
        mask: data.mask_image
    };
    
    // 顯示瑕疵分類統計
    displayDefectSummary(data.analysis_results);
    
    // 顯示結果區域
    showResults();
    
    // 初始化影像檢視器
    setTimeout(() => {
        initImageViewer('combined');
        initMouseWheelZoom('combined');
    }, 100);
}

function displayDefectSummary(analysisResults) {
    const defectList = document.getElementById('defectList');
    defectList.innerHTML = '';
    
    if (!analysisResults || !analysisResults.classes) {
        defectList.innerHTML = '<p>無瑕疵數據</p>';
        return;
    }
    
    // 瑕疵顏色對應
    const defectColors = {
        '1_PI_Particle': '#0000ff',
        '2_PR_Peeling': '#00ff00',
        '3_Copper_Nodule': '#ff0000',
        '4_Env_Particle': '#00ffff'
    };
    
    // 遍歷每個類別
    Object.entries(analysisResults.classes).forEach(([className, classData]) => {
        const defectItem = document.createElement('div');
        defectItem.className = 'defect-item';
        
        const color = defectColors[className] || '#666';
        
        defectItem.innerHTML = `
            <div class="defect-name">
                <i class="fas fa-bug" style="color: ${color};"></i>
                ${className}
            </div>
            <div class="defect-badge">${classData.total_regions}</div>
        `;
        
        defectList.appendChild(defectItem);
    });
}

// ========== 標籤切換 ==========
function switchTab(tabName) {
    // 移除所有 active 類別
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // 添加 active 到選中的標籤
    event.target.classList.add('active');
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // 重新初始化檢視器
    if (tabName === 'original' || tabName === 'combined') {
        setTimeout(() => {
            initImageViewer(tabName);
            initMouseWheelZoom(tabName);
        }, 100);
    }
}

// ========== 下載功能 ==========
function downloadImage(type) {
    if (!currentImageFiles[type]) {
        showStatus('無可下載的影像', 'error');
        return;
    }
    
    // 建立下載連結
    const link = document.createElement('a');
    link.href = 'data:image/png;base64,' + currentImageFiles[type];
    
    const timestamp = currentAnalysisData.timestamp;
    link.download = `AOI_${type}_${timestamp}.png`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showStatus(`已下載 ${type} 影像`, 'success');
}

function downloadJSON() {
    if (!currentAnalysisData) {
        showStatus('無可下載的分析報告', 'error');
        return;
    }
    
    // 建立 JSON 字串
    const jsonStr = JSON.stringify(currentAnalysisData.analysis_results, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    // 建立下載連結
    const link = document.createElement('a');
    link.href = url;
    link.download = `AOI_analysis_${currentAnalysisData.timestamp}.json`;
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    URL.revokeObjectURL(url);
    showStatus('已下載分析報告', 'success');
}

// ========== 清除結果 ==========
function clearResults() {
    // 清除文件選擇
    document.getElementById('imageInput').value = '';
    
    // 隱藏結果
    hideResults();
    
    // 清除狀態訊息
    hideStatus();
    
    // 重置數據
    currentAnalysisData = null;
    currentOriginalFile = null;
    currentImageFiles = {
        combined: null,
        overlay: null,
        mask: null
    };
    
    // 重置檢視器狀態
    viewers.original.zoom = 1.0;
    viewers.original.grayscale = false;
    viewers.combined.zoom = 1.0;
    viewers.combined.grayscale = false;
    
    showStatus('已清除結果', 'info');
}

// ========== UI 輔助函數 ==========
function showLoading(show) {
    const loading = document.getElementById('loading');
    if (show) {
        loading.classList.add('show');
    } else {
        loading.classList.remove('show');
    }
}

function updateLoadingDetail(message) {
    const loadingDetail = document.getElementById('loadingDetail');
    if (loadingDetail) {
        loadingDetail.textContent = message;
    }
}

function showResults() {
    const results = document.getElementById('results');
    results.classList.add('show');
    results.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function hideResults() {
    const results = document.getElementById('results');
    results.classList.remove('show');
}

function showStatus(message, type) {
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.textContent = message;
    statusMessage.className = 'status-message show ' + type;
    
    // 自動隱藏成功和資訊訊息
    if (type === 'success' || type === 'info') {
        setTimeout(() => {
            hideStatus();
        }, 5000);
    }
}

function hideStatus() {
    const statusMessage = document.getElementById('statusMessage');
    statusMessage.classList.remove('show');
}

// ========== 鍵盤快捷鍵 ==========
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + Enter: 開始分析
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            analyzeImage();
        }
        
        // Escape: 清除狀態
        if (e.key === 'Escape') {
            hideStatus();
        }
        
        // Ctrl/Cmd + Delete: 清除結果
        if ((e.ctrlKey || e.metaKey) && e.key === 'Delete') {
            e.preventDefault();
            clearResults();
        }
    });
}

// ========== LLM 功能 (預留) ==========
function sendLLMMessage(message) {
    // TODO: 實作 LLM 聊天功能
    console.log('LLM message:', message);
    
    fetch('/llm/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: message })
    })
    .then(response => response.json())
    .then(data => {
        console.log('LLM response:', data);
    })
    .catch(error => {
        console.error('LLM error:', error);
    });
}

// ========== 工具函數 ==========
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// ========== 影像檢視器功能 ==========

// 初始化影像檢視器
function initImageViewer(viewerType = 'original') {
    const viewer = viewers[viewerType];
    const img = document.getElementById(`${viewerType}Img`);
    const wrapper = document.getElementById(`${viewerType}Wrapper`);
    
    if (!img || !wrapper) {
        console.log(`Viewer ${viewerType} not found`);
        return;
    }
    
    // 建立隱藏的 canvas 用於讀取像素值
    if (!viewer.canvas) {
        viewer.canvas = document.createElement('canvas');
        viewer.context = viewer.canvas.getContext('2d');
    }
    
    // 當影像載入完成時，更新 canvas
    const updateCanvas = function() {
        const currentImg = document.getElementById(`${viewerType}Img`);
        if (currentImg && currentImg.complete && currentImg.naturalWidth > 0) {
            viewer.canvas.width = currentImg.naturalWidth;
            viewer.canvas.height = currentImg.naturalHeight;
            viewer.context.drawImage(currentImg, 0, 0);
            console.log(`Canvas updated for ${viewerType}: ${currentImg.naturalWidth}x${currentImg.naturalHeight}`);
        }
    };
    
    img.onload = updateCanvas;
    
    // 如果圖片已經載入，立即更新 canvas
    if (img.complete && img.naturalWidth > 0) {
        updateCanvas();
    }
    
    // 只有原始影像需要座標顯示
    if (viewerType === 'original') {
        const coordDisplay = document.getElementById('originalCoordinateDisplay');
        
        if (coordDisplay) {
            // 滑鼠移動事件
            const mouseMoveHandler = function(e) {
                const currentImg = document.getElementById(`${viewerType}Img`);
                const rect = currentImg.getBoundingClientRect();
                const x = Math.floor((e.clientX - rect.left) / viewer.zoom);
                const y = Math.floor((e.clientY - rect.top) / viewer.zoom);
                
                // 確保座標在影像範圍內
                if (x >= 0 && x < currentImg.naturalWidth && y >= 0 && y < currentImg.naturalHeight) {
                    try {
                        const pixelData = viewer.context.getImageData(x, y, 1, 1).data;
                        const grayscale = Math.round(0.299 * pixelData[0] + 0.587 * pixelData[1] + 0.114 * pixelData[2]);
                        coordDisplay.textContent = `X: ${x}, Y: ${y} | 灰階: ${grayscale}`;
                    } catch (err) {
                        console.log('Canvas read error:', err);
                        coordDisplay.textContent = `X: ${x}, Y: ${y} | 灰階: -`;
                    }
                }
            };
            
            // 滑鼠離開時重置座標
            const mouseLeaveHandler = function() {
                coordDisplay.textContent = 'X: -, Y: - | 灰階: -';
            };
            
            // 移除舊的事件監聽器（如果存在）
            wrapper.removeEventListener('mousemove', wrapper._mouseMoveHandler);
            wrapper.removeEventListener('mouseleave', wrapper._mouseLeaveHandler);
            
            // 添加新的事件監聽器
            wrapper.addEventListener('mousemove', mouseMoveHandler);
            wrapper.addEventListener('mouseleave', mouseLeaveHandler);
            
            // 保存引用以便之後移除
            wrapper._mouseMoveHandler = mouseMoveHandler;
            wrapper._mouseLeaveHandler = mouseLeaveHandler;
            
            console.log(`Coordinate tracking initialized for ${viewerType}`);
        }
    }
}

// 放大功能
function zoomIn(viewerType = 'original') {
    const viewer = viewers[viewerType];
    viewer.zoom = Math.min(viewer.zoom + 0.25, 5.0);
    applyZoom(viewerType);
}

// 縮小功能
function zoomOut(viewerType = 'original') {
    const viewer = viewers[viewerType];
    viewer.zoom = Math.max(viewer.zoom - 0.25, 0.5);
    applyZoom(viewerType);
}

// 重置縮放
function resetZoom(viewerType = 'original') {
    const viewer = viewers[viewerType];
    viewer.zoom = 1.0;
    applyZoom(viewerType);
}

// 套用縮放
function applyZoom(viewerType) {
    const viewer = viewers[viewerType];
    const img = document.getElementById(`${viewerType}Img`);
    const zoomLevel = document.getElementById(`${viewerType}ZoomLevel`);
    
    if (img) {
        img.style.transform = `scale(${viewer.zoom})`;
    }
    
    if (zoomLevel) {
        zoomLevel.textContent = `${Math.round(viewer.zoom * 100)}%`;
    }
}

// 切換灰階模式
function toggleGrayscale(viewerType = 'original') {
    const viewer = viewers[viewerType];
    viewer.grayscale = !viewer.grayscale;
    
    const img = document.getElementById(`${viewerType}Img`);
    const btn = document.getElementById(`${viewerType}GrayscaleBtn`);
    
    if (img) {
        img.style.filter = viewer.grayscale ? 'grayscale(100%)' : 'none';
    }
    
    if (btn) {
        if (viewer.grayscale) {
            btn.style.background = 'var(--secondary-color)';
            btn.style.color = 'white';
        } else {
            btn.style.background = 'white';
            btn.style.color = '#495057';
        }
    }
}

// 滾輪縮放
function initMouseWheelZoom(viewerType = 'original') {
    const wrapper = document.getElementById(`${viewerType}Wrapper`);
    if (!wrapper) return;
    
    const wheelHandler = function(e) {
        if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            
            if (e.deltaY < 0) {
                zoomIn(viewerType);
            } else {
                zoomOut(viewerType);
            }
        }
    };
    
    // 移除舊的事件監聽器（如果存在）
    if (wrapper._wheelHandler) {
        wrapper.removeEventListener('wheel', wrapper._wheelHandler);
    }
    
    // 添加新的事件監聽器
    wrapper.addEventListener('wheel', wheelHandler, { passive: false });
    
    // 保存引用以便之後移除
    wrapper._wheelHandler = wheelHandler;
    
    console.log(`Wheel zoom initialized for ${viewerType}`);
}

// ========== 匯出函數供 HTML 使用 ==========
window.analyzeImage = analyzeImage;
window.clearResults = clearResults;
window.switchTab = switchTab;
window.downloadImage = downloadImage;
window.downloadJSON = downloadJSON;
window.sendLLMMessage = sendLLMMessage;
window.zoomIn = zoomIn;
window.zoomOut = zoomOut;
window.resetZoom = resetZoom;
window.toggleGrayscale = toggleGrayscale;

// ========== 批次檢測功能 ==========

// 模式切換
function switchMode(mode) {
    currentMode = mode;
    
    const singleModeBtn = document.getElementById('singleModeBtn');
    const batchModeBtn = document.getElementById('batchModeBtn');
    const uploadArea = document.getElementById('uploadArea');
    const batchUploadArea = document.getElementById('batchUploadArea');
    const analyzeBtn = document.getElementById('analyzeBtn');
    
    if (mode === 'single') {
        singleModeBtn.classList.add('active');
        batchModeBtn.classList.remove('active');
        uploadArea.style.display = 'block';
        batchUploadArea.style.display = 'none';
        analyzeBtn.innerHTML = '<i class="fas fa-search"></i> 開始分析';
    } else {
        singleModeBtn.classList.remove('active');
        batchModeBtn.classList.add('active');
        uploadArea.style.display = 'none';
        batchUploadArea.style.display = 'block';
        analyzeBtn.innerHTML = '<i class="fas fa-tasks"></i> 批次分析';
    }
    
    // 清除結果
    clearResults();
}

// 顯示檔案列表
function displayFileList(files) {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '<h4>已選擇的文件：</h4>';
    
    const ul = document.createElement('ul');
    ul.style.listStyle = 'none';
    ul.style.padding = '0';
    
    for (let i = 0; i < files.length; i++) {
        const li = document.createElement('li');
        li.style.padding = '5px';
        li.style.borderBottom = '1px solid #eee';
        li.innerHTML = `
            <i class="fas fa-image" style="color: #4CAF50;"></i>
            <strong>${files[i].name}</strong>
            <span style="color: #666; font-size: 0.9em;"> (${formatFileSize(files[i].size)})</span>
        `;
        ul.appendChild(li);
    }
    
    fileList.appendChild(ul);
}

// 顯示批次結果
function displayBatchResults(data) {
    const results = document.getElementById('results');
    results.innerHTML = `
        <h2><i class="fas fa-chart-bar"></i> 批次分析結果</h2>
        
        <!-- 批次統計卡片 -->
        <div class="stats-cards">
            <div class="stat-card">
                <div class="stat-icon" style="background: #4CAF50;">
                    <i class="fas fa-images"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">總影像數</div>
                    <div class="stat-value">${data.total_images}</div>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon" style="background: #2196F3;">
                    <i class="fas fa-check-circle"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">成功處理</div>
                    <div class="stat-value">${data.processed}</div>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon" style="background: #ff6b6b;">
                    <i class="fas fa-times-circle"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">處理失敗</div>
                    <div class="stat-value">${data.failed}</div>
                </div>
            </div>
            
            <div class="stat-card">
                <div class="stat-icon" style="background: #4ecdc4;">
                    <i class="fas fa-clock"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-label">總處理時間</div>
                    <div class="stat-value">${data.total_processing_time.toFixed(2)} 秒</div>
                </div>
            </div>
        </div>
        
        <!-- 批次 ID 和下載按鈕 -->
        <div class="batch-info" style="margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px;">
            <p style="margin: 0 0 10px 0;"><strong>批次 ID:</strong> ${data.batch_id}</p>
            <button onclick="downloadBatchResults('${data.batch_id}')" class="btn btn-download">
                <i class="fas fa-download"></i> 下載所有結果 (ZIP)
            </button>
        </div>
        
        <!-- 個別結果列表 -->
        <div class="batch-results-list">
            <h3><i class="fas fa-list"></i> 個別影像結果</h3>
            <div id="batchResultItems"></div>
        </div>
    `;
    
    // 顯示每個影像的結果
    const batchResultItems = document.getElementById('batchResultItems');
    data.results.forEach((result, index) => {
        const resultItem = document.createElement('div');
        resultItem.className = 'batch-result-item';
        resultItem.style.cssText = 'border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: white;';
        
        if (result.success) {
            const totalDefects = result.total_defects || 0;
            resultItem.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0 0 5px 0;">
                            <i class="fas fa-check-circle" style="color: #4CAF50;"></i>
                            ${result.filename}
                        </h4>
                        <p style="margin: 0; color: #666;">
                            檢測到 <strong style="color: #ff6b6b;">${totalDefects}</strong> 個瑕疵 | 
                            處理時間: ${result.processing_time.toFixed(2)} 秒
                        </p>
                    </div>
                    <button onclick="viewBatchResult(${index})" class="btn btn-primary" style="min-width: 100px;">
                        <i class="fas fa-eye"></i> 查看詳情
                    </button>
                </div>
            `;
        } else {
            resultItem.innerHTML = `
                <div>
                    <h4 style="margin: 0 0 5px 0;">
                        <i class="fas fa-times-circle" style="color: #ff6b6b;"></i>
                        ${result.filename}
                    </h4>
                    <p style="margin: 0; color: #dc3545;">
                        <strong>錯誤:</strong> ${result.error}
                    </p>
                </div>
            `;
        }
        
        batchResultItems.appendChild(resultItem);
    });
    
    showResults();
}

// 查看批次結果中的單一影像
function viewBatchResult(index) {
    const result = batchResults.results[index];
    
    if (!result.success) {
        showStatus('此影像處理失敗', 'error');
        return;
    }
    
    // 轉換為單張結果格式
    const singleResult = {
        success: true,
        filename: result.filename,
        overlay_image: result.overlay_image,
        combined_image: result.combined_image,
        mask_image: result.mask_image,
        total_defects: result.total_defects,
        processing_time: result.processing_time,
        analysis_results: result.analysis_results,
        timestamp: batchResults.batch_id
    };
    
    // 顯示結果
    currentAnalysisData = singleResult;
    displayResults(singleResult);
    
    // 滾動到結果
    document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
}

// 下載批次結果
function downloadBatchResults(batchId) {
    showStatus('正在打包批次結果...', 'info');
    
    window.location.href = `/download/batch/${batchId}`;
    
    setTimeout(() => {
        showStatus('批次結果下載完成', 'success');
    }, 1000);
}

// 匯出批次功能
window.switchMode = switchMode;
window.viewBatchResult = viewBatchResult;
window.downloadBatchResults = downloadBatchResults;

console.log('FANOUT AOI WebUI JavaScript loaded successfully');
