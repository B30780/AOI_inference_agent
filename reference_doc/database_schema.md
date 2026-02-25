# AOI Segformer 結果資料庫 Schema 設計

## 概述
此資料庫用於儲存 Segformer 模型對 AOI 圖片的語義分析結果，包括圖片資訊、分類資料和區域詳細資訊。

## 表關係
```
images (1) ─────< classes (N) ─────< regions (N)
```

---

## 表結構

### 1. images 表
儲存每次推理的圖片基本資訊和效能資料

| 欄位名 | 資料型別 | 約束 | 說明 |
|--------|----------|------|------|
| img_unique_id | VARCHAR(255) | PRIMARY KEY | 圖片唯一標識符 |
| image_height | INTEGER | NOT NULL | 圖片高度 (pixels) |
| image_width | INTEGER | NOT NULL | 圖片寬度 (pixels) |
| processing_time_seconds | FLOAT | NOT NULL | 處理時間（秒）|
| timestamp | DATETIME | NOT NULL | 處理時間戳 |
| input_image_path | VARCHAR(500) | NOT NULL | 輸入圖片路徑 |
| result_image_1_path | VARCHAR(500) | NULL | 結果圖片1路徑 |
| result_image_2_path | VARCHAR(500) | NULL | 結果圖片2路徑 |
| result_image_3_path | VARCHAR(500) | NULL | 結果圖片3路徑 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 記錄創建時間 |

**索引:**
- PRIMARY KEY: `img_unique_id`
- INDEX: `timestamp`

---

### 2. classes 表
儲存每張圖片的分類資訊

| 欄位名 | 資料型別 | 約束 | 說明 |
|--------|----------|------|------|
| class_unique_id | VARCHAR(255) | PRIMARY KEY | 類別唯一標識符 (UUID) |
| img_unique_id | VARCHAR(255) | FOREIGN KEY | 關聯的圖片ID |
| class_id | INTEGER | NOT NULL | 類別ID (1-4) |
| class_name | VARCHAR(100) | NOT NULL | 類別名稱 |
| total_regions | INTEGER | NOT NULL | 該類別的區域總數 |
| total_area_pixels | INTEGER | NOT NULL | 該類別的總像素面積 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 記錄創建時間 |

**外鍵:**
- `img_unique_id` REFERENCES `images(img_unique_id)` ON DELETE CASCADE

**索引:**
- PRIMARY KEY: `class_unique_id`
- INDEX: `img_unique_id`
- INDEX: `class_id`

**類別枚舉:**
- 1: PI_Particle
- 2: PR_Peeling
- 3: Copper_Nodule
- 4: Env_Particle

---

### 3. regions 表
儲存每個類別的區域詳細資訊

| 欄位名 | 資料型別 | 約束 | 說明 |
|--------|----------|------|------|
| region_unique_id | VARCHAR(255) | PRIMARY KEY | 區域唯一標識符 (UUID) |
| class_unique_id | VARCHAR(255) | FOREIGN KEY | 關聯的類別ID |
| img_unique_id | VARCHAR(255) | FOREIGN KEY | 關聯的圖片ID |
| region_id | INTEGER | NOT NULL | 類別內的區域ID |
| centroid_x | FLOAT | NOT NULL | 質心X座標 |
| centroid_y | FLOAT | NOT NULL | 質心Y座標 |
| bbox_x | INTEGER | NOT NULL | 邊界框X座標 |
| bbox_y | INTEGER | NOT NULL | 邊界框Y座標 |
| bbox_width | INTEGER | NOT NULL | 邊界框寬度 |
| bbox_height | INTEGER | NOT NULL | 邊界框高度 |
| area_pixels | INTEGER | NOT NULL | 區域像素面積 |
| perimeter | FLOAT | NOT NULL | 周長 |
| major_axis | FLOAT | NOT NULL | 主軸長度 |
| minor_axis | FLOAT | NOT NULL | 次軸長度 |
| circularity | FLOAT | NOT NULL | 圓度 (0-1) |
| aspect_ratio | FLOAT | NOT NULL | 長寬比 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 記錄創建時間 |

**外鍵:**
- `class_unique_id` REFERENCES `classes(class_unique_id)` ON DELETE CASCADE
- `img_unique_id` REFERENCES `images(img_unique_id)` ON DELETE CASCADE

**索引:**
- PRIMARY KEY: `region_unique_id`
- INDEX: `class_unique_id`
- INDEX: `img_unique_id`
- INDEX: `region_id`

---

## SQL 創建語句 (PostgreSQL/MySQL)

```sql
-- 創建 images 表
CREATE TABLE images (
    img_unique_id VARCHAR(255) PRIMARY KEY,
    image_height INTEGER NOT NULL,
    image_width INTEGER NOT NULL,
    processing_time_seconds FLOAT NOT NULL,
    timestamp DATETIME NOT NULL,
    input_image_path VARCHAR(500) NOT NULL,
    result_image_1_path VARCHAR(500),
    result_image_2_path VARCHAR(500),
    result_image_3_path VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timestamp (timestamp)
);

-- 創建 classes 表
CREATE TABLE classes (
    class_unique_id VARCHAR(255) PRIMARY KEY,
    img_unique_id VARCHAR(255) NOT NULL,
    class_id INTEGER NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    total_regions INTEGER NOT NULL,
    total_area_pixels INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (img_unique_id) REFERENCES images(img_unique_id) ON DELETE CASCADE,
    INDEX idx_img_id (img_unique_id),
    INDEX idx_class_id (class_id)
);

-- 創建 regions 表
CREATE TABLE regions (
    region_unique_id VARCHAR(255) PRIMARY KEY,
    class_unique_id VARCHAR(255) NOT NULL,
    img_unique_id VARCHAR(255) NOT NULL,
    region_id INTEGER NOT NULL,
    centroid_x FLOAT NOT NULL,
    centroid_y FLOAT NOT NULL,
    bbox_x INTEGER NOT NULL,
    bbox_y INTEGER NOT NULL,
    bbox_width INTEGER NOT NULL,
    bbox_height INTEGER NOT NULL,
    area_pixels INTEGER NOT NULL,
    perimeter FLOAT NOT NULL,
    major_axis FLOAT NOT NULL,
    minor_axis FLOAT NOT NULL,
    circularity FLOAT NOT NULL,
    aspect_ratio FLOAT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_unique_id) REFERENCES classes(class_unique_id) ON DELETE CASCADE,
    FOREIGN KEY (img_unique_id) REFERENCES images(img_unique_id) ON DELETE CASCADE,
    INDEX idx_class_id (class_unique_id),
    INDEX idx_img_id (img_unique_id),
    INDEX idx_region_id (region_id)
);
```

---

## JSON Schema 格式

```json
{
  "database": "aoi_segformer_results",
  "tables": [
    {
      "name": "images",
      "description": "儲存圖片基本資訊和效能資料",
      "columns": [
        {
          "name": "img_unique_id",
          "type": "VARCHAR(255)",
          "constraints": ["PRIMARY KEY"],
          "description": "圖片唯一標識符"
        },
        {
          "name": "image_height",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "圖片高度"
        },
        {
          "name": "image_width",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "圖片寬度"
        },
        {
          "name": "processing_time_seconds",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "處理時間（秒）"
        },
        {
          "name": "timestamp",
          "type": "DATETIME",
          "constraints": ["NOT NULL"],
          "description": "處理時間戳"
        },
        {
          "name": "input_image_path",
          "type": "VARCHAR(500)",
          "constraints": ["NOT NULL"],
          "description": "輸入圖片路徑"
        },
        {
          "name": "result_image_1_path",
          "type": "VARCHAR(500)",
          "constraints": ["NULL"],
          "description": "結果圖片1路徑"
        },
        {
          "name": "result_image_2_path",
          "type": "VARCHAR(500)",
          "constraints": ["NULL"],
          "description": "結果圖片2路徑"
        },
        {
          "name": "result_image_3_path",
          "type": "VARCHAR(500)",
          "constraints": ["NULL"],
          "description": "結果圖片3路徑"
        },
        {
          "name": "created_at",
          "type": "DATETIME",
          "constraints": ["DEFAULT CURRENT_TIMESTAMP"],
          "description": "記錄創建時間"
        }
      ],
      "indexes": [
        {
          "name": "idx_timestamp",
          "columns": ["timestamp"]
        }
      ]
    },
    {
      "name": "classes",
      "description": "儲存分類資訊",
      "columns": [
        {
          "name": "class_unique_id",
          "type": "VARCHAR(255)",
          "constraints": ["PRIMARY KEY"],
          "description": "類別唯一標識符"
        },
        {
          "name": "img_unique_id",
          "type": "VARCHAR(255)",
          "constraints": ["FOREIGN KEY -> images(img_unique_id)", "NOT NULL"],
          "description": "關聯的圖片ID"
        },
        {
          "name": "class_id",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "類別ID (1-4)"
        },
        {
          "name": "class_name",
          "type": "VARCHAR(100)",
          "constraints": ["NOT NULL"],
          "description": "類別名稱"
        },
        {
          "name": "total_regions",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "區域總數"
        },
        {
          "name": "total_area_pixels",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "總像素面積"
        },
        {
          "name": "created_at",
          "type": "DATETIME",
          "constraints": ["DEFAULT CURRENT_TIMESTAMP"],
          "description": "記錄創建時間"
        }
      ],
      "indexes": [
        {
          "name": "idx_img_id",
          "columns": ["img_unique_id"]
        },
        {
          "name": "idx_class_id",
          "columns": ["class_id"]
        }
      ]
    },
    {
      "name": "regions",
      "description": "儲存區域詳細資訊",
      "columns": [
        {
          "name": "region_unique_id",
          "type": "VARCHAR(255)",
          "constraints": ["PRIMARY KEY"],
          "description": "區域唯一標識符"
        },
        {
          "name": "class_unique_id",
          "type": "VARCHAR(255)",
          "constraints": ["FOREIGN KEY -> classes(class_unique_id)", "NOT NULL"],
          "description": "關聯的類別ID"
        },
        {
          "name": "img_unique_id",
          "type": "VARCHAR(255)",
          "constraints": ["FOREIGN KEY -> images(img_unique_id)", "NOT NULL"],
          "description": "關聯的圖片ID"
        },
        {
          "name": "region_id",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "類別內的區域ID"
        },
        {
          "name": "centroid_x",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "質心X座標"
        },
        {
          "name": "centroid_y",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "質心Y座標"
        },
        {
          "name": "bbox_x",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "邊界框X座標"
        },
        {
          "name": "bbox_y",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "邊界框Y座標"
        },
        {
          "name": "bbox_width",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "邊界框寬度"
        },
        {
          "name": "bbox_height",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "邊界框高度"
        },
        {
          "name": "area_pixels",
          "type": "INTEGER",
          "constraints": ["NOT NULL"],
          "description": "區域像素面積"
        },
        {
          "name": "perimeter",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "周長"
        },
        {
          "name": "major_axis",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "主軸長度"
        },
        {
          "name": "minor_axis",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "次軸長度"
        },
        {
          "name": "circularity",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "圓度 (0-1)"
        },
        {
          "name": "aspect_ratio",
          "type": "FLOAT",
          "constraints": ["NOT NULL"],
          "description": "長寬比"
        },
        {
          "name": "created_at",
          "type": "DATETIME",
          "constraints": ["DEFAULT CURRENT_TIMESTAMP"],
          "description": "記錄創建時間"
        }
      ],
      "indexes": [
        {
          "name": "idx_class_id",
          "columns": ["class_unique_id"]
        },
        {
          "name": "idx_img_id",
          "columns": ["img_unique_id"]
        },
        {
          "name": "idx_region_id",
          "columns": ["region_id"]
        }
      ]
    }
  ],
  "relationships": [
    {
      "from": "classes.img_unique_id",
      "to": "images.img_unique_id",
      "type": "many-to-one",
      "on_delete": "CASCADE"
    },
    {
      "from": "regions.class_unique_id",
      "to": "classes.class_unique_id",
      "type": "many-to-one",
      "on_delete": "CASCADE"
    },
    {
      "from": "regions.img_unique_id",
      "to": "images.img_unique_id",
      "type": "many-to-one",
      "on_delete": "CASCADE"
    }
  ]
}
```

---

## 查詢範例

### 查詢某張圖片的所有分析結果
```sql
SELECT 
    i.img_unique_id,
    i.timestamp,
    c.class_name,
    c.total_regions,
    r.region_id,
    r.centroid_x,
    r.centroid_y,
    r.area_pixels
FROM images i
LEFT JOIN classes c ON i.img_unique_id = c.img_unique_id
LEFT JOIN regions r ON c.class_unique_id = r.class_unique_id
WHERE i.img_unique_id = 'your_image_id'
ORDER BY c.class_id, r.region_id;
```

### 統計某個時間段內各類別的檢出數量
```sql
SELECT 
    c.class_name,
    COUNT(DISTINCT c.img_unique_id) as image_count,
    SUM(c.total_regions) as total_regions,
    SUM(c.total_area_pixels) as total_area
FROM classes c
JOIN images i ON c.img_unique_id = i.img_unique_id
WHERE i.timestamp BETWEEN '2026-02-24 00:00:00' AND '2026-02-24 23:59:59'
GROUP BY c.class_name;
```

### 查詢包含特定缺陷的所有圖片
```sql
SELECT DISTINCT
    i.img_unique_id,
    i.timestamp,
    i.input_image_path
FROM images i
JOIN classes c ON i.img_unique_id = c.img_unique_id
WHERE c.class_name = 'PR_Peeling'
    AND c.total_regions > 0
ORDER BY i.timestamp DESC;
```

---

## 設計說明

### 主鍵策略
- **img_unique_id**: 可以使用推理時生成的ID（例如：`20260224_173819_3DKQA001_...`）
- **class_unique_id**: 建議使用 UUID 或 `{img_unique_id}_{class_id}` 組合
- **region_unique_id**: 建議使用 UUID 或 `{class_unique_id}_{region_id}` 組合

### 資料完整性
- 使用外鍵約束確保引用完整性
- `ON DELETE CASCADE` 確保刪除圖片時自動刪除相關的 classes 和 regions

### 效能優化
- 在常用查詢欄位上建立索引（timestamp, img_unique_id, class_id）
- 考慮對大量資料進行分區（按日期）

### 擴展性
- 可以添加 `batch_id` 欄位來關聯同一批次處理的多張圖片
- 可以添加 `model_version` 欄位來追蹤使用的模型版本
- 可以添加 `user_id` 或 `operator` 欄位來記錄操作者

---

## 資料插入範例 (Python)

```python
import uuid
from datetime import datetime

# 插入圖片記錄
img_id = "20260224_173819_3DKQA001_RDL1_M1_ADI_G3_PR_Shadow_Arrow_30304.-129549.t"
cursor.execute("""
    INSERT INTO images (
        img_unique_id, image_height, image_width,
        processing_time_seconds, timestamp,
        input_image_path, result_image_1_path, 
        result_image_2_path, result_image_3_path
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    img_id, 1792, 1792, 0.6743,
    datetime.strptime("2026-02-24 17:38:20", "%Y-%m-%d %H:%M:%S"),
    "/path/to/input.jpg",
    "/path/to/result1.jpg",
    "/path/to/result2.jpg",
    "/path/to/result3.jpg"
))

# 插入類別記錄
class_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO classes (
        class_unique_id, img_unique_id, class_id,
        class_name, total_regions, total_area_pixels
    ) VALUES (%s, %s, %s, %s, %s, %s)
""", (
    class_id, img_id, 1,
    "PI_Particle", 5, 213
))

# 插入區域記錄
region_id = str(uuid.uuid4())
cursor.execute("""
    INSERT INTO regions (
        region_unique_id, class_unique_id, img_unique_id,
        region_id, centroid_x, centroid_y,
        bbox_x, bbox_y, bbox_width, bbox_height,
        area_pixels, perimeter, major_axis, minor_axis,
        circularity, aspect_ratio
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", (
    region_id, class_id, img_id,
    1, 1655.904761904762, 1508.0,
    1653, 1506, 7, 5,
    14, 15.313708305358887, 5.750073432922363, 3.9162988662719727,
    0.750200171090617, 1.4682417326326294
))
```
