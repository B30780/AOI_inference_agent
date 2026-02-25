"""
FANOUT Shuttle Service AOI 影像辨識系統
Flask Web API 主程式
Author: ITRI EOSL Rachel A30335
Date: 2025-12-02
Port: 8080
"""

from flask import Flask, render_template, request, jsonify, send_file
from flasgger import Swagger, swag_from
import os
import sys
import cv2
import numpy as np
import torch
import base64
import io
from pathlib import Path
from datetime import datetime
import json
import traceback
from werkzeug.utils import secure_filename

# 添加父目錄到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 導入 SegFormer 模型
from model.segformer_inf_modular import SegformerSegmentation, SegformerTester

# 導入 OneFormer 模型
from model.oneformer_inf_modular import OneFormerSegmentation, OneFormerTester

# 導入 LLM 服務
from llm_service import ollama_service, init_llm_service

# Flask 應用初始化
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 上傳限制
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULT_FOLDER'] = 'results'
app.config['SECRET_KEY'] = 'fanout-aoi-secret-key-2025'

# Swagger UI 配置
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs",
    "swagger_ui_config": {
        "supportedSubmitMethods": ["get", "post", "put", "delete", "patch"],
        "validatorUrl": None,
        "docExpansion": "list",
        "defaultModelsExpandDepth": 3
    },
    "swagger_ui_template_dir": "templates/flasgger"
}

swagger_template = {
    "swagger": "2.0",
    "info": {
        "title": "FANOUT Shuttle Service AOI API",
        "description": "AOI 影像辨識系統 API 文件 - 支援影像上傳、模型切換、瑕疵分析等功能",
        "version": "1.0.0",
        "contact": {
            "name": "ITRI EOSL",
            "email": "rachel.a30335@itri.org.tw"
        }
    },
    "basePath": "/",
    "schemes": ["http", "https"],
    "tags": [
        {
            "name": "System",
            "description": "系統狀態和健康檢查"
        },
        {
            "name": "Model",
            "description": "模型管理和切換"
        },
        {
            "name": "AOI",
            "description": "影像上傳和瑕疵檢測"
        },
        {
            "name": "LLM",
            "description": "AI 輔助分析服務"
        }
    ]
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# 創建必要目錄
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULT_FOLDER'], exist_ok=True)

# 全局變量存儲模型
model_wrapper = None
tester = None
model_loaded = False
llm_available = False
current_model = "segformer"  # 預設使用 segformer，可選 "segformer" 或 "oneformer"

# 模型配置
MODEL_CONFIGS = {
    "segformer": {
        "name": "SegFormer",
        "model_path": "model/segformer_best_sliding.pth",
        "base_size": 1792,
        "patch_size": 512,
        "class_name": (SegformerSegmentation, SegformerTester)
    },
    "oneformer": {
        "name": "OneFormer",
        "model_path": "model/oneformer_best.pth",
        "base_size": 1792,
        "patch_size": 448,
        "class_name": (OneFormerSegmentation, OneFormerTester)
    }
}

# 允許的文件格式
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}


def allowed_file(filename):
    """檢查文件格式是否允許"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def init_models(model_type=None):
    """初始化模型
    
    Args:
        model_type: 模型類型 ("segformer" 或 "oneformer")，None 則使用 current_model
    """
    global model_wrapper, tester, model_loaded, current_model
    
    if model_type is None:
        model_type = current_model
    
    if model_type not in MODEL_CONFIGS:
        print(f"錯誤: 不支援的模型類型 '{model_type}'")
        return False
    
    config = MODEL_CONFIGS[model_type]
    
    try:
        print("="*80)
        print("FANOUT Shuttle Service AOI 影像辨識系統")
        print("="*80)
        print(f"正在載入 {config['name']} 模型...")
        
        # 設定設備
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"使用設備: {device.upper()}")
        
        # 取得模型類別
        ModelClass, TesterClass = config['class_name']
        
        # 初始化模型
        model_wrapper = ModelClass(device=device)
        
        # 模型檔案路徑
        model_path = os.path.join(os.path.dirname(__file__), config['model_path'])
        
        if not os.path.exists(model_path):
            print(f"警告: 模型檔案不存在 - {model_path}")
            print("系統將以未載入模型狀態運行")
            model_loaded = False
            return False
        
        # 初始化測試器
        tester = TesterClass(
            model_wrapper=model_wrapper,
            base_size=config['base_size'],
            patch_size=config['patch_size'],
            model_path=model_path
        )
        
        model_loaded = True
        current_model = model_type
        print(f"✓ {config['name']} 模型載入成功！")
        print(f"配置: base_size={config['base_size']}, patch_size={config['patch_size']}")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"✗ 模型載入失敗: {str(e)}")
        print(traceback.format_exc())
        model_loaded = False
        return False


def switch_model(model_type):
    """切換模型
    
    Args:
        model_type: 目標模型類型 ("segformer" 或 "oneformer")
        
    Returns:
        bool: 切換是否成功
    """
    global current_model
    
    if model_type not in MODEL_CONFIGS:
        return False
    
    if model_type == current_model and model_loaded:
        print(f"已經在使用 {MODEL_CONFIGS[model_type]['name']} 模型")
        return True
    
    print(f"\n正在切換到 {MODEL_CONFIGS[model_type]['name']} 模型...")
    success = init_models(model_type)
    
    if success:
        print(f"✓ 成功切換到 {MODEL_CONFIGS[model_type]['name']} 模型\n")
    else:
        print(f"✗ 切換到 {MODEL_CONFIGS[model_type]['name']} 模型失敗\n")
    
    return success


def process_aoi_image(image_path, output_dir):
    """
    處理 AOI 影像
    
    Args:
        image_path: 輸入影像路徑
        output_dir: 輸出目錄路徑
        
    Returns:
        dict: 包含處理結果的字典
    """
    try:
        import time
        
        # 讀取影像
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "error": "無法讀取影像檔案"}
        
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        original_size = img.shape[:2]
        
        # 計時開始
        start_time = time.perf_counter()
        
        # 調整大小
        img_resized = cv2.resize(img_rgb, (tester.base_size, tester.base_size), 
                                interpolation=cv2.INTER_LINEAR)
        
        # 進行預測
        with torch.no_grad():
            pred_full = tester.predict_image_patches(img_resized)
        
        # 調整回原始大小
        pred_resized = cv2.resize(pred_full.astype(np.uint8), 
                                 (original_size[1], original_size[0]),
                                 interpolation=cv2.INTER_NEAREST)
        
        # 計算處理時間
        processing_time = time.perf_counter() - start_time
        print(f"影像處理完成，耗時: {processing_time:.4f} 秒")
        
        # 建立視覺化
        color_mask, overlay = tester.create_visualization(img, pred_resized)
        
        # 進行瑕疵分析
        analysis_results = tester.analyze_defects(pred_resized)
        
        # 添加文字標註
        overlay_with_text = tester.add_text_annotations(overlay, pred_resized)
        
        # 建立並排圖片
        h1, w1 = img.shape[:2]
        h2, w2 = overlay_with_text.shape[:2]
        
        if h1 != h2:
            overlay_with_text = cv2.resize(overlay_with_text, 
                                          (int(w2 * h1 / h2), h1))
    
        combined = np.hstack([img, overlay_with_text])
        
        # 儲存結果
        img_name = os.path.basename(image_path)
        name_without_ext = os.path.splitext(img_name)[0]
        
        overlay_path = os.path.join(output_dir, f"{name_without_ext}_overlay.png")
        combined_path = os.path.join(output_dir, f"{name_without_ext}_combined.png")
        mask_path = os.path.join(output_dir, f"{name_without_ext}_mask.png")
        json_path = os.path.join(output_dir, f"{name_without_ext}_analysis.json")
        
        cv2.imwrite(overlay_path, overlay_with_text)
        cv2.imwrite(combined_path, combined)
        cv2.imwrite(mask_path, color_mask)
        
        # 添加處理時間到分析結果
        analysis_results["performance"] = {
            "processing_time_seconds": round(processing_time, 4),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # 儲存 JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, indent=2, ensure_ascii=False)
        
        # 統計瑕疵數量
        total_defects = sum(
            cls_data["total_regions"] 
            for cls_data in analysis_results["classes"].values()
        )
        
        return {
            "success": True,
            "overlay_path": overlay_path,
            "combined_path": combined_path,
            "mask_path": mask_path,
            "analysis_path": json_path,
            "total_defects": total_defects,
            "processing_time": processing_time,
            "analysis_results": analysis_results
        }
        
    except Exception as e:
        print(f"處理影像時發生錯誤: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}


def image_to_base64(image_path):
    """將影像轉換為 base64 編碼"""
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        print(f"轉換影像為 base64 時發生錯誤: {str(e)}")
        return None


# ========== 路由定義 ==========

@app.route('/')
def index():
    """主頁面"""
    return render_template('index.html', 
                         current_year=datetime.now().year,
                         model_loaded=model_loaded)


@app.route('/batch-test')
def batch_test():
    """批次上傳測試頁面"""
    return render_template('batch_test.html', 
                         current_year=datetime.now().year,
                         model_loaded=model_loaded)


@app.route('/health', methods=['GET'])
def health_check():
    """系統健康檢查
    ---
    tags:
      - System
    summary: 系統健康檢查
    description: 檢查系統狀態、模型載入情況和設備資訊
    responses:
      200:
        description: 系統狀態正常
        schema:
          type: object
          properties:
            status:
              type: string
              example: ok
            timestamp:
              type: string
              example: "2025-12-26T10:30:00"
            model_loaded:
              type: boolean
              example: true
            device:
              type: string
              example: cuda
            cuda_available:
              type: boolean
              example: true
            system:
              type: string
              example: FANOUT Shuttle Service AOI
    """
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "model_loaded": model_loaded,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "cuda_available": torch.cuda.is_available(),
        "system": "FANOUT Shuttle Service AOI"
    })


@app.route('/upload', methods=['POST'])
def upload_image():
    """上傳影像 API
    ---
    tags:
      - AOI
    summary: 上傳影像進行 AOI 瑕疵檢測
    description: 上傳 PCB 影像，系統會自動進行瑕疵檢測並返回分析結果
    consumes:
      - multipart/form-data
    parameters:
      - name: image
        in: formData
        type: file
        required: true
        description: 要分析的 PCB 影像文件 (支援 png, jpg, jpeg, bmp, tiff, tif)
    responses:
      200:
        description: 影像處理成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            filename:
              type: string
              example: test_pcb.jpg
            overlay_image:
              type: string
              description: base64 編碼的疊加影像
            combined_image:
              type: string
              description: base64 編碼的並排對比影像
            mask_image:
              type: string
              description: base64 編碼的分割遮罩
            total_defects:
              type: integer
              example: 5
            processing_time:
              type: number
              example: 2.345
            analysis_results:
              type: object
              description: 詳細的瑕疵分析結果
            timestamp:
              type: string
              example: "20251226_103045"
      400:
        description: 請求錯誤（無文件或格式不支援）
      503:
        description: 模型尚未載入
      500:
        description: 伺服器處理錯誤
    """
    try:
        # 檢查模型是否載入
        if not model_loaded:
            return jsonify({
                "success": False,
                "error": "模型尚未載入，請檢查系統狀態"
            }), 503
        
        # 檢查是否有文件
        if 'image' not in request.files:
            return jsonify({
                "success": False,
                "error": "未找到上傳的影像文件"
            }), 400
        
        file = request.files['image']
        
        # 檢查文件名
        if file.filename == '':
            return jsonify({
                "success": False,
                "error": "未選擇文件"
            }), 400
        
        # 檢查文件格式
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "error": f"不支援的文件格式，僅支援: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # 儲存上傳的文件
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_folder = datetime.now().strftime("%Y%m%d")  # 日期資料夾 YYYYMMDD
        
        # 建立日期資料夾
        upload_date_dir = os.path.join(app.config['UPLOAD_FOLDER'], date_folder)
        result_date_dir = os.path.join(app.config['RESULT_FOLDER'], date_folder)
        os.makedirs(upload_date_dir, exist_ok=True)
        os.makedirs(result_date_dir, exist_ok=True)
        
        # 儲存上傳檔案到日期資料夾
        unique_filename = f"{timestamp}_{filename}"
        upload_path = os.path.join(upload_date_dir, unique_filename)
        file.save(upload_path)
        
        # 建立輸出目錄（在日期資料夾內）
        output_dir = os.path.join(result_date_dir, timestamp)
        os.makedirs(output_dir, exist_ok=True)
        
        # 處理影像
        result = process_aoi_image(upload_path, output_dir)
        
        if not result["success"]:
            return jsonify(result), 500
        
        # 轉換影像為 base64
        overlay_base64 = image_to_base64(result["overlay_path"])
        combined_base64 = image_to_base64(result["combined_path"])
        mask_base64 = image_to_base64(result["mask_path"])
        
        # 返回結果
        response = {
            "success": True,
            "filename": filename,
            "overlay_image": overlay_base64,
            "combined_image": combined_base64,
            "mask_image": mask_base64,
            "total_defects": result["total_defects"],
            "processing_time": result["processing_time"],
            "analysis_results": result["analysis_results"],
            "timestamp": timestamp
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"上傳處理錯誤: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"伺服器處理錯誤: {str(e)}"
        }), 500


@app.route('/upload/batch', methods=['POST'])
def upload_batch_images():
    """批次上傳影像 API
    ---
    tags:
      - AOI
    summary: 批次上傳多張影像進行 AOI 瑕疵檢測
    description: 一次上傳多張 PCB 影像，系統會依序處理每張影像並返回所有分析結果
    consumes:
      - multipart/form-data
    parameters:
      - name: images
        in: formData
        type: array
        items:
          type: file
        collectionFormat: multi
        required: true
        description: 要分析的多張 PCB 影像文件（支援 png, jpg, jpeg, bmp, tiff, tif）。在文件選擇時按住 Ctrl/Cmd 可選擇多個文件。
    responses:
      200:
        description: 批次處理完成（可能包含部分失敗）
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            total_images:
              type: integer
              example: 5
            processed:
              type: integer
              example: 4
            failed:
              type: integer
              example: 1
            results:
              type: array
              items:
                type: object
                properties:
                  filename:
                    type: string
                  success:
                    type: boolean
                  total_defects:
                    type: integer
                  processing_time:
                    type: number
                  overlay_image:
                    type: string
                  combined_image:
                    type: string
                  mask_image:
                    type: string
                  analysis_results:
                    type: object
                  error:
                    type: string
            batch_id:
              type: string
              example: "20251226_103045"
            total_processing_time:
              type: number
              example: 12.345
            timestamp:
              type: string
      400:
        description: 請求錯誤（無文件）
      503:
        description: 模型尚未載入
    """
    try:
        import time
        batch_start_time = time.perf_counter()
        
        # 檢查模型是否載入
        if not model_loaded:
            return jsonify({
                "success": False,
                "error": "模型尚未載入，請檢查系統狀態"
            }), 503
        
        # 檢查是否有文件
        if 'images' not in request.files:
            return jsonify({
                "success": False,
                "error": "未找到上傳的影像文件"
            }), 400
        
        files = request.files.getlist('images')
        
        if len(files) == 0 or (len(files) == 1 and files[0].filename == ''):
            return jsonify({
                "success": False,
                "error": "未選擇任何文件"
            }), 400
        
        # 建立批次輸出目錄
        batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        date_folder = datetime.now().strftime("%Y%m%d")  # 日期資料夾 YYYYMMDD
        
        # 建立日期資料夾
        upload_date_dir = os.path.join(app.config['UPLOAD_FOLDER'], date_folder)
        result_date_dir = os.path.join(app.config['RESULT_FOLDER'], date_folder)
        os.makedirs(upload_date_dir, exist_ok=True)
        os.makedirs(result_date_dir, exist_ok=True)
        
        # 批次輸出目錄在日期資料夾內
        batch_output_dir = os.path.join(result_date_dir, f"batch_{batch_timestamp}")
        os.makedirs(batch_output_dir, exist_ok=True)
        
        results = []
        processed_count = 0
        failed_count = 0
        
        # 處理每個文件
        for idx, file in enumerate(files, 1):
            try:
                # 檢查文件名
                if file.filename == '':
                    results.append({
                        "filename": f"file_{idx}",
                        "success": False,
                        "error": "文件名為空"
                    })
                    failed_count += 1
                    continue
                
                # 檢查文件格式
                if not allowed_file(file.filename):
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "error": f"不支援的文件格式，僅支援: {', '.join(ALLOWED_EXTENSIONS)}"
                    })
                    failed_count += 1
                    continue
                
                # 儲存上傳的文件到日期資料夾
                filename = secure_filename(file.filename)
                unique_filename = f"{batch_timestamp}_{idx:03d}_{filename}"
                upload_path = os.path.join(upload_date_dir, unique_filename)
                file.save(upload_path)
                
                print(f"正在處理 [{idx}/{len(files)}]: {filename}")
                
                # 建立該文件的輸出目錄
                file_output_dir = os.path.join(batch_output_dir, f"{idx:03d}_{os.path.splitext(filename)[0]}")
                os.makedirs(file_output_dir, exist_ok=True)
                
                # 處理影像
                result = process_aoi_image(upload_path, file_output_dir)
                
                if result["success"]:
                    # 轉換影像為 base64
                    overlay_base64 = image_to_base64(result["overlay_path"])
                    combined_base64 = image_to_base64(result["combined_path"])
                    mask_base64 = image_to_base64(result["mask_path"])
                    
                    results.append({
                        "filename": filename,
                        "success": True,
                        "file_index": idx,
                        "overlay_image": overlay_base64,
                        "combined_image": combined_base64,
                        "mask_image": mask_base64,
                        "total_defects": result["total_defects"],
                        "processing_time": result["processing_time"],
                        "analysis_results": result["analysis_results"],
                        "output_dir": f"{date_folder}/batch_{batch_timestamp}/{idx:03d}_{os.path.splitext(filename)[0]}"
                    })
                    processed_count += 1
                    print(f"✓ [{idx}/{len(files)}] {filename} 處理完成 - 發現 {result['total_defects']} 個瑕疵")
                else:
                    results.append({
                        "filename": filename,
                        "success": False,
                        "file_index": idx,
                        "error": result.get("error", "處理失敗")
                    })
                    failed_count += 1
                    print(f"✗ [{idx}/{len(files)}] {filename} 處理失敗: {result.get('error', '未知錯誤')}")
                    
            except Exception as e:
                error_msg = str(e)
                results.append({
                    "filename": file.filename if file.filename else f"file_{idx}",
                    "success": False,
                    "file_index": idx,
                    "error": error_msg
                })
                failed_count += 1
                print(f"✗ [{idx}/{len(files)}] 處理時發生錯誤: {error_msg}")
        
        # 計算總處理時間
        total_processing_time = time.perf_counter() - batch_start_time
        
        # 儲存批次摘要
        batch_summary = {
            "batch_id": batch_timestamp,
            "total_images": len(files),
            "processed": processed_count,
            "failed": failed_count,
            "total_processing_time": round(total_processing_time, 4),
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        summary_path = os.path.join(batch_output_dir, "batch_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(batch_summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n批次處理完成:")
        print(f"  總數: {len(files)}, 成功: {processed_count}, 失敗: {failed_count}")
        print(f"  總耗時: {total_processing_time:.2f} 秒")
        print(f"  結果目錄: {batch_output_dir}\n")
        
        # 返回結果
        response = {
            "success": True,
            "total_images": len(files),
            "processed": processed_count,
            "failed": failed_count,
            "results": results,
            "batch_id": batch_timestamp,
            "total_processing_time": round(total_processing_time, 4),
            "summary_path": f"{date_folder}/batch_{batch_timestamp}/batch_summary.json",
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(response)
        
    except Exception as e:
        print(f"批次上傳處理錯誤: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": f"伺服器處理錯誤: {str(e)}"
        }), 500


@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """下載結果文件
    ---
    tags:
      - AOI
    summary: 下載檢測結果文件
    description: 下載指定的檢測結果文件（影像或JSON）
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: 文件路徑（相對於 results 目錄）
        example: "20251226_103045/test_pcb_overlay.png"
    responses:
      200:
        description: 文件下載成功
      404:
        description: 文件不存在
    """
    try:
        file_path = os.path.join(app.config['RESULT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({"error": "文件不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/download/batch/<batch_id>', methods=['GET'])
def download_batch_results(batch_id):
    """下載批次檢測結果（打包為 ZIP）
    ---
    tags:
      - AOI
    summary: 下載批次檢測結果
    description: 將指定批次的所有檢測結果打包為 ZIP 文件下載
    parameters:
      - name: batch_id
        in: path
        type: string
        required: true
        description: 批次 ID（時間戳）
        example: "20251226_103045"
    responses:
      200:
        description: ZIP 文件下載成功
        content:
          application/zip:
            schema:
              type: string
              format: binary
      404:
        description: 批次結果不存在
      500:
        description: 打包失敗
    """
    try:
        import zipfile
        
        # 從 batch_id (YYYYMMDD_HHMMSS) 提取日期部分 (YYYYMMDD)
        date_folder = batch_id.split('_')[0]
        
        # 批次目錄在日期資料夾內
        batch_dir = os.path.join(app.config['RESULT_FOLDER'], date_folder, f"batch_{batch_id}")
        
        if not os.path.exists(batch_dir):
            return jsonify({
                "success": False,
                "error": f"批次結果不存在: batch_{batch_id}"
            }), 404
        
        # 建立 ZIP 文件在日期資料夾內
        zip_path = os.path.join(app.config['RESULT_FOLDER'], date_folder, f"batch_{batch_id}.zip")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 遍歷批次目錄
            for root, dirs, files in os.walk(batch_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, app.config['RESULT_FOLDER'])
                    zipf.write(file_path, arcname)
        
        # 返回 ZIP 文件
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"batch_{batch_id}_results.zip",
            mimetype='application/zip'
        )
        
    except Exception as e:
        print(f"打包批次結果時發生錯誤: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/llm/chat', methods=['POST'])
def llm_chat():
    """LLM 聊天介面
    ---
    tags:
      - LLM
    summary: AI 聊天對話
    description: 與 AI 助手進行 AOI 相關的專業對話
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - message
          properties:
            message:
              type: string
              description: 使用者的問題或訊息
              example: "什麼是 PI Particle 瑕疵？"
            context:
              type: object
              description: 可選的上下文資訊
    responses:
      200:
        description: 聊天回應成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            response:
              type: string
              example: "PI Particle（聚酰亞胺微粒）是一種常見的 PCB 表面瑕疵..."
            model:
              type: string
              example: gemma2
            processing_time:
              type: number
              example: 1.234
            timestamp:
              type: string
      400:
        description: 訊息不能為空
      503:
        description: LLM 服務未啟用
    """
    try:
        if not llm_available:
            return jsonify({
                "success": False,
                "error": "LLM 服務未啟用"
            }), 503
        
        data = request.get_json()
        message = data.get('message', '')
        context = data.get('context', None)  # 可選的上下文資訊
        
        if not message:
            return jsonify({
                "success": False,
                "error": "訊息不能為空"
            }), 400
        
        # 使用 Gemma2 進行對話
        result = ollama_service.chat(
            message=message,
            system_prompt="你是一位專業的 AOI 檢測和 PCB 製造專家。請用繁體中文簡潔專業地回答問題。"
        )
        
        if result['success']:
            response = {
                "success": True,
                "response": result['response'],
                "model": result['model'],
                "processing_time": result['total_duration'],
                "timestamp": datetime.now().isoformat()
            }
        else:
            response = {
                "success": False,
                "error": result['error']
            }
        
        return jsonify(response)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/llm/analyze', methods=['POST'])
def llm_analyze_defects():
    """使用 VLM 分析瑕疵檢測結果
    ---
    tags:
      - LLM
    summary: AI 視覺分析瑕疵
    description: 使用視覺語言模型分析 PCB 瑕疵影像
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - image
            - defect_summary
          properties:
            image:
              type: string
              description: base64 編碼的影像
              example: "iVBORw0KGgoAAAANSUhEUgA..."
            defect_summary:
              type: object
              description: 瑕疵摘要資訊
              properties:
                total_defects:
                  type: integer
                  example: 5
                defect_types:
                  type: array
                  items:
                    type: string
                  example: ["PI_Particle", "Scratch"]
    responses:
      200:
        description: 分析成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            analysis:
              type: string
              example: "檢測到 5 個瑕疵區域，主要為 PI Particle..."
            model:
              type: string
              example: llava
            processing_time:
              type: number
              example: 3.456
            timestamp:
              type: string
      400:
        description: 缺少必要參數
      503:
        description: LLM 服務未啟用
    """
    try:
        if not llm_available:
            return jsonify({
                "success": False,
                "error": "LLM 服務未啟用"
            }), 503
        
        data = request.get_json()
        image_base64 = data.get('image', '')
        defect_summary = data.get('defect_summary', {})
        
        if not image_base64 or not defect_summary:
            return jsonify({
                "success": False,
                "error": "缺少必要參數"
            }), 400
        
        # 使用 LLaVA 進行視覺分析
        result = ollama_service.analyze_aoi_defects(image_base64, defect_summary)
        
        if result['success']:
            return jsonify({
                "success": True,
                "analysis": result['response'],
                "model": result['model'],
                "processing_time": result['total_duration'],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error']
            })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/llm/explain/<defect_type>', methods=['GET'])
def llm_explain_defect(defect_type):
    """解釋特定瑕疵類型
    ---
    tags:
      - LLM
    summary: 解釋瑕疵類型
    description: 獲取特定瑕疵類型的詳細說明
    parameters:
      - name: defect_type
        in: path
        type: string
        required: true
        description: 瑕疵類型名稱
        example: PI_Particle
    responses:
      200:
        description: 解釋成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            explanation:
              type: string
              example: "PI Particle 是指聚酰亞胺（Polyimide）微粒..."
            defect_type:
              type: string
              example: PI_Particle
            model:
              type: string
              example: gemma2
            processing_time:
              type: number
              example: 1.123
            timestamp:
              type: string
      503:
        description: LLM 服務未啟用
    """
    try:
        if not llm_available:
            return jsonify({
                "success": False,
                "error": "LLM 服務未啟用"
            }), 503
        
        result = ollama_service.explain_defect_type(defect_type)
        
        if result['success']:
            return jsonify({
                "success": True,
                "explanation": result['response'],
                "defect_type": defect_type,
                "model": result['model'],
                "processing_time": result['total_duration'],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": result['error']
            })
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """獲取系統狀態
    ---
    tags:
      - System
    summary: 獲取完整的系統狀態資訊
    description: 返回系統配置、模型狀態、支援格式等詳細資訊
    responses:
      200:
        description: 系統狀態資訊
        schema:
          type: object
          properties:
            system:
              type: string
              example: FANOUT Shuttle Service AOI
            model_loaded:
              type: boolean
              example: true
            current_model:
              type: string
              example: segformer
            current_model_name:
              type: string
              example: SegFormer
            available_models:
              type: array
              items:
                type: string
              example: ["segformer", "oneformer"]
            llm_available:
              type: boolean
              example: true
            device:
              type: string
              example: cuda
            upload_folder:
              type: string
              example: uploads
            result_folder:
              type: string
              example: results
            supported_formats:
              type: array
              items:
                type: string
              example: ["png", "jpg", "jpeg", "bmp", "tiff", "tif"]
            max_file_size_mb:
              type: integer
              example: 50
            timestamp:
              type: string
    """
    return jsonify({
        "system": "FANOUT Shuttle Service AOI",
        "model_loaded": model_loaded,
        "current_model": current_model,
        "current_model_name": MODEL_CONFIGS[current_model]["name"] if current_model in MODEL_CONFIGS else None,
        "available_models": list(MODEL_CONFIGS.keys()),
        "llm_available": llm_available,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "upload_folder": app.config['UPLOAD_FOLDER'],
        "result_folder": app.config['RESULT_FOLDER'],
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "max_file_size_mb": app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024),
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/model/current', methods=['GET'])
def get_current_model():
    """獲取當前使用的模型資訊
    ---
    tags:
      - Model
    summary: 獲取當前模型資訊
    description: 返回當前正在使用的模型類型和配置
    responses:
      200:
        description: 當前模型資訊
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            current_model:
              type: string
              example: segformer
            model_name:
              type: string
              example: SegFormer
            base_size:
              type: integer
              example: 1792
            patch_size:
              type: integer
              example: 512
            model_path:
              type: string
              example: "2025_12_26_segformer/segformer_best_crop.pth"
            timestamp:
              type: string
      503:
        description: 模型尚未載入
    """
    if not model_loaded:
        return jsonify({
            "success": False,
            "error": "模型尚未載入"
        }), 503
    
    config = MODEL_CONFIGS[current_model]
    return jsonify({
        "success": True,
        "current_model": current_model,
        "model_name": config["name"],
        "base_size": config["base_size"],
        "patch_size": config["patch_size"],
        "model_path": config["model_path"],
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/model/available', methods=['GET'])
def get_available_models():
    """獲取所有可用的模型列表
    ---
    tags:
      - Model
    summary: 獲取可用模型列表
    description: 返回系統中所有可用的模型及其配置資訊
    responses:
      200:
        description: 可用模型列表
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            models:
              type: array
              items:
                type: object
                properties:
                  type:
                    type: string
                    example: segformer
                  name:
                    type: string
                    example: SegFormer
                  base_size:
                    type: integer
                    example: 1792
                  patch_size:
                    type: integer
                    example: 512
                  model_path:
                    type: string
                    example: "2025_12_26_segformer/segformer_best_crop.pth"
                  file_exists:
                    type: boolean
                    example: true
                  is_current:
                    type: boolean
                    example: true
            current_model:
              type: string
              example: segformer
            timestamp:
              type: string
    """
    models_info = []
    for model_type, config in MODEL_CONFIGS.items():
        model_path = os.path.join(os.path.dirname(__file__), config['model_path'])
        models_info.append({
            "type": model_type,
            "name": config["name"],
            "base_size": config["base_size"],
            "patch_size": config["patch_size"],
            "model_path": config["model_path"],
            "file_exists": os.path.exists(model_path),
            "is_current": model_type == current_model
        })
    
    return jsonify({
        "success": True,
        "models": models_info,
        "current_model": current_model,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/model/switch', methods=['POST'])
def switch_model_api():
    """切換模型 API
    ---
    tags:
      - Model
    summary: 切換使用的模型
    description: 在 SegFormer 和 OneFormer 之間切換
    consumes:
      - application/json
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - model
          properties:
            model:
              type: string
              enum: [segformer, oneformer]
              description: 要切換到的模型類型
              example: oneformer
    responses:
      200:
        description: 模型切換成功
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "成功切換到 OneFormer 模型"
            previous_model:
              type: string
              example: segformer
            current_model:
              type: string
              example: oneformer
            model_name:
              type: string
              example: OneFormer
            base_size:
              type: integer
              example: 1792
            patch_size:
              type: integer
              example: 448
            timestamp:
              type: string
      400:
        description: 請求錯誤（未指定模型或不支援的模型類型）
      500:
        description: 模型切換失敗
    """
    try:
        data = request.get_json()
        target_model = data.get('model', '')
        
        if not target_model:
            return jsonify({
                "success": False,
                "error": "請指定要切換的模型類型"
            }), 400
        
        if target_model not in MODEL_CONFIGS:
            return jsonify({
                "success": False,
                "error": f"不支援的模型類型: {target_model}",
                "available_models": list(MODEL_CONFIGS.keys())
            }), 400
        
        # 如果已經是當前模型
        if target_model == current_model and model_loaded:
            return jsonify({
                "success": True,
                "message": f"已經在使用 {MODEL_CONFIGS[target_model]['name']} 模型",
                "current_model": current_model,
                "model_name": MODEL_CONFIGS[current_model]["name"],
                "timestamp": datetime.now().isoformat()
            })
        
        # 切換模型
        success = switch_model(target_model)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"成功切換到 {MODEL_CONFIGS[target_model]['name']} 模型",
                "previous_model": current_model if current_model != target_model else None,
                "current_model": current_model,
                "model_name": MODEL_CONFIGS[current_model]["name"],
                "base_size": MODEL_CONFIGS[current_model]["base_size"],
                "patch_size": MODEL_CONFIGS[current_model]["patch_size"],
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": f"切換到 {MODEL_CONFIGS[target_model]['name']} 模型失敗",
                "current_model": current_model,
                "timestamp": datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.errorhandler(413)
def request_entity_too_large(error):
    """文件過大錯誤處理"""
    return jsonify({
        "success": False,
        "error": "上傳文件過大，請確保文件小於 50MB"
    }), 413


@app.errorhandler(404)
def not_found(error):
    """404 錯誤處理"""
    return jsonify({
        "success": False,
        "error": "請求的資源不存在"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    return jsonify({
        "success": False,
        "error": "伺服器內部錯誤"
    }), 500


# ========== 應用初始化 ==========
# 在模組載入時初始化模型（確保在所有情況下都會載入）
def init_app(model_type=None):
    """
    初始化應用程序
    
    Args:
        model_type: 要載入的模型類型 ('segformer' 或 'oneformer')，None 表示使用預設模型
    """
    print("\n" + "="*80)
    print("FANOUT Shuttle Service AOI 影像辨識系統")
    print("="*80)
    print(f"啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python 版本: {sys.version.split()[0]}")
    print(f"PyTorch 版本: {torch.__version__}")
    print(f"CUDA 可用: {torch.cuda.is_available()}")
    
    # 初始化模型
    init_models(model_type=model_type)
    
    # 初始化 LLM 服務
    global llm_available
    llm_available = init_llm_service()
    
    print("\n" + "="*80)
    print("正在啟動 Flask Web 伺服器...")
    print("服務端口: 8080")
    print("訪問地址: http://localhost:8080")
    print("="*80 + "\n")

# ========== 主程式入口 ==========

if __name__ == '__main__':
    # 初始化應用
    init_app()
    
    # 啟動 Flask 應用
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=True,
        threaded=True,
        use_reloader=False  # 禁用重載器以避免模型重複載入
    )
