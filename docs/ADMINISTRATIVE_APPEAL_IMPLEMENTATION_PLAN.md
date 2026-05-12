# 訴願法新增實施計劃

## 概述
本計劃遵循 Specification-Driven Development (SSD) 工作流程，將 [`knowledge/administrative_appeal_zh.md`](../knowledge/administrative_appeal_zh.md) (訴願法) 作為新法律類型插入系統。

### 法規資訊
- **法規名稱**: 訴願法
- **英文名稱**: Administrative Appeal Act
- **法律類型代碼**: `administrative-appeal`
- **資料來源**: knowledge/administrative_appeal_zh.md
- **修正日期**: 民國 101 年 06 月 27 日
- **條文總數**: 101 條
- **章節結構**: 5 章（總則、訴願審議委員會、訴願程序、再審程序、附則）

---

## 📋 工作流程 (SSD Workflow)

遵循 SSD 三步驟流程：

### Step 1: 更新 requirements.md
定義訴願法支持的功能需求和用戶故事

### Step 2: 更新 design.md  
設計訴願法的技術架構和實施細節

### Step 3: 更新 tasks.md
拆解為具體可執行的開發任務清單

---

## 📝 Step 1: Requirements 更新內容

### 1.1 新增法律類型需求

在 [`docs/requirements.md`](requirements.md) 的 **Section 9.6** (Adding New Law Types) 後添加：

```markdown
### 9.11 訴願法支持 (Administrative Appeal Act Support)

**Story:** As a user preparing for administrative law exams, I want to study the Administrative Appeal Act alongside other laws.

**Scenario:**
- System supports Administrative Appeal Act as a separate law type: `"administrative-appeal"`
- Administrative Appeal Act is structured with 5 main chapters and 101 articles
- Users can switch between different law types including Administrative Appeal Act
- Each article can have associated practice questions
- Progress tracking is independent between all law types
- Search and filtering work across Administrative Appeal Act content

### 9.12 訴願法資料結構

**Story:** As an administrator, I want Administrative Appeal Act data to be properly structured for easy management.

**Scenario:**
- Administrative Appeal articles stored as markdown file in `knowledge/administrative_appeal_zh.md`
- Each article contains:
  - `article_number`: Article identifier (e.g., "第 1 條", "第 2 條")
  - `article_number_int`: Integer for sorting (e.g., 1, 2, 3)
  - `chapter`: Chapter hierarchy (e.g., "第一章 總則")
  - `content`: Full text content (may have multiple paragraphs)
  - `lang`: Language tag (zh-TW)
  - `type`: Set to "administrative-appeal"
- Parsing script extracts structured data from markdown format
- Initialization script imports all Administrative Appeal articles into database
- Same database schema as patent law articles (uses `LawModel`)
```

---

## 🏗️ Step 2: Design 更新內容

### 2.1 更新 LAW_TYPES 定義

在 [`docs/design.md`](design.md) 的 **Section 9.2** (Law Type Definition) 中更新 `LAW_TYPES` 常量：

```python
LAW_TYPES = {
    "patent-act": {
        "name_zh": "專利法",
        "name_en": "Patent Law",
        "code": "patent-act"
    },
    "patent-examination": {
        "name_zh": "專利審查基準",
        "name_en": "Patent Examination Guidelines",
        "code": "patent-examination"
    },
    "administrative-appeal": {
        "name_zh": "訴願法",
        "name_en": "Administrative Appeal Act",
        "code": "administrative-appeal"
    },
    # Future law types...
}
```

### 2.2 訴願法解析器設計

在 [`docs/design.md`](design.md) 添加新的 Section **9.13 訴願法解析與初始化**：

```markdown
### 9.13 訴願法解析與初始化

**資料來源**: 
- Location: `knowledge/administrative_appeal_zh.md`
- Format: Markdown 格式，包含完整法規內容
- Structure: 
  - 法規名稱和修正日期在文件開頭
  - 章節標題格式: `   第 X 章 標題`
  - 節標題格式: `      第 X 節 標題`
  - 條文格式: `第 X 條` (條號) + 條文內容 (可能多段落，每段以數字標記)

**解析邏輯**: `scripts/parse_administrative_appeal.py`

```python
def parse_administrative_appeal_md(file_path: str) -> List[Dict]:
    """
    解析訴願法 markdown 文件，提取結構化法條資料
    
    Args:
        file_path: markdown 文件路徑
    
    Returns:
        List[Dict]: 包含所有法條的列表
    """
    articles = []
    current_chapter = ""
    current_section = ""
    current_article_number = None
    current_content_lines = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.rstrip()
        
        # 跳過空行和法規標題/日期
        if not line or line.startswith('法規名稱') or line.startswith('修正日期'):
            continue
        
        # 檢測章標題 (前面有3個空格)
        if line.startswith('   第 ') and '章' in line:
            current_chapter = line.strip()
            current_section = ""
            continue
        
        # 檢測節標題 (前面有6個空格)
        if line.startswith('      第 ') and '節' in line:
            current_section = line.strip()
            continue
        
        # 檢測條號
        if line.startswith('第 ') and '條' in line:
            # 保存前一條
            if current_article_number is not None:
                save_article(articles, current_article_number,
                           current_chapter, current_section,
                           current_content_lines)
            
            # 開始新條
            current_article_number = extract_article_number(line)
            current_content_lines = []
            continue
        
        # 收集條文內容 (以數字+空格開頭，或純文字)
        if current_article_number is not None:
            # 移除行首的數字標記 (如 "1   ", "2   ")
            content = re.sub(r'^\d+\s+', '', line)
            if content:
                current_content_lines.append(content)
    
    # 保存最後一條
    if current_article_number is not None:
        save_article(articles, current_article_number,
                   current_chapter, current_section,
                   current_content_lines)
    
    return articles
```

**初始化腳本**: `scripts/init_administrative_appeal.py`

```python
#!/usr/bin/env python3
"""
初始化訴願法到資料庫
從 knowledge/administrative_appeal_zh.md 讀取並解析訴願法內容，
插入到資料庫作為 type='administrative-appeal' 的法條。
"""

import sys
import os
from db.models import Database, LawModel
from pymongo.errors import DuplicateKeyError

def init_administrative_appeal(target='local', dry_run=False):
    """
    初始化訴願法到資料庫
    
    Args:
        target: 'local' | 'remote' | 'both'
        dry_run: 如果為 True，只顯示將插入的資料，不實際寫入
    """
    # 解析 markdown 文件
    md_file = 'knowledge/administrative_appeal_zh.md'
    articles = parse_administrative_appeal_md(md_file)
    
    print(f"✅ 成功解析 {len(articles)} 條訴願法條文")
    
    if dry_run:
        print("\n[DRY RUN] 以下資料將被插入:")
        for article in articles[:3]:  # 只顯示前3條
            print(f"  - {article['article_number']}: {article['chapter']}")
        print(f"  ... 共 {len(articles)} 條")
        return
    
    # 連接資料庫
    db = Database()
    laws_collection = db.laws_collection
    
    inserted = 0
    updated = 0
    errors = []
    
    for article in articles:
        try:
            # 設定法律類型
            article['type'] = 'administrative-appeal'
            article['lang'] = 'zh-TW'
            
            # 使用 LawModel 驗證資料
            law_model = LawModel(**article)
            
            # Upsert (複合鍵: article_number + lang + type)
            result = laws_collection.update_one(
                {
                    'article_number': law_model.article_number,
                    'lang': law_model.lang,
                    'type': law_model.type
                },
                {
                    '$set': {
                        'content': law_model.content,
                        'chapter': law_model.chapter,
                        'article_number_int': law_model.article_number_int,
                    }
                },
                upsert=True
            )
            
            if result.upserted_id:
                inserted += 1
            else:
                updated += 1
                
        except Exception as e:
            errors.append(f"{article.get('article_number', 'unknown')}: {str(e)}")
    
    # 輸出統計
    print(f"\n✅ 訴願法初始化完成")
    print(f"   插入: {inserted} 條")
    print(f"   更新: {updated} 條")
    
    if errors:
        print(f"\n⚠️  發生 {len(errors)} 個錯誤:")
        for error in errors[:5]:
            print(f"   - {error}")
    
    # 驗證
    total = laws_collection.count_documents({
        'type': 'administrative-appeal',
        'lang': 'zh-TW'
    })
    print(f"\n📊 資料庫中訴願法條文總數: {total}")
    
    return inserted, updated, len(errors)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='初始化訴願法到資料庫')
    parser.add_argument('--target', choices=['local', 'remote', 'both'],
                       default='local', help='目標資料庫')
    parser.add_argument('--dry-run', action='store_true',
                       help='只顯示將插入的資料，不實際寫入')
    
    args = parser.parse_args()
    init_administrative_appeal(target=args.target, dry_run=args.dry_run)
```

**驗證腳本**: `scripts/verify_administrative_appeal.py`

```python
#!/usr/bin/env python3
"""
驗證訴願法資料完整性
"""

def verify_administrative_appeal():
    """驗證訴願法資料"""
    db = Database()
    laws_collection = db.laws_collection
    
    # 檢查總數
    total = laws_collection.count_documents({
        'type': 'administrative-appeal',
        'lang': 'zh-TW'
    })
    
    expected_count = 101  # 訴願法共 101 條
    
    print(f"📊 訴願法條文總數: {total}/{expected_count}")
    
    if total != expected_count:
        print(f"⚠️  警告: 預期 {expected_count} 條，實際 {total} 條")
    
    # 檢查章節分布
    chapters = laws_collection.distinct('chapter', {
        'type': 'administrative-appeal',
        'lang': 'zh-TW'
    })
    
    print(f"\n📚 章節數量: {len(chapters)}")
    for chapter in sorted(chapters):
        count = laws_collection.count_documents({
            'type': 'administrative-appeal',
            'lang': 'zh-TW',
            'chapter': chapter
        })
        print(f"   - {chapter}: {count} 條")
    
    # 檢查必要欄位
    missing_fields = laws_collection.count_documents({
        'type': 'administrative-appeal',
        '$or': [
            {'article_number': {'$exists': False}},
            {'article_number_int': {'$exists': False}},
            {'content': {'$exists': False}},
            {'chapter': {'$exists': False}}
        ]
    })
    
    if missing_fields > 0:
        print(f"\n⚠️  {missing_fields} 條法條缺少必要欄位")
    else:
        print(f"\n✅ 所有法條資料完整")
    
    return total == expected_count and missing_fields == 0
```
```

---

## ✅ Step 3: Tasks 更新內容

在 [`docs/tasks.md`](tasks.md) 的 **Phase 9** 後添加新的 **Phase 10**：

```markdown
## Phase 10: 訴願法支持 (Administrative Appeal Act Support)

### Task 10.1: 更新 LAW_TYPES 常量
**File**: [`db/models.py`](../db/models.py)

- [ ] 在 `LAW_TYPES` 字典中添加 `"administrative-appeal"` 定義：
  ```python
  "administrative-appeal": {
      "name_zh": "訴願法",
      "name_en": "Administrative Appeal Act",
      "code": "administrative-appeal"
  }
  ```

**Validation**:
- 確認常量定義正確
- 驗證系統能識別新的法律類型

---

### Task 10.2: 建立訴願法解析腳本
**File**: `scripts/parse_administrative_appeal.py` (新建)

- [ ] 建立解析腳本檔案
- [ ] 實作主要解析函數 `parse_administrative_appeal_md()`:
  - [ ] 讀取 markdown 文件
  - [ ] 識別章標題（前綴3個空格 + "第 X 章"）
  - [ ] 識別節標題（前綴6個空格 + "第 X 節"）
  - [ ] 識別條號（"第 X 條"）
  - [ ] 提取條文內容（處理多段落，移除數字前綴）
  - [ ] 生成 `article_number_int` 用於排序
  - [ ] 組合完整章節路徑（章 + 節）
- [ ] 實作輔助函數:
  - [ ] `extract_article_number()`: 從條號提取數字
  - [ ] `save_article()`: 保存單條法條資料
  - [ ] `format_chapter_path()`: 格式化章節完整路徑
- [ ] 添加錯誤處理（文件不存在、格式錯誤等）
- [ ] 添加單元測試

**Validation**:
- 解析完成後應有 101 條法條
- 驗證章節結構正確（5章）
- 確認條文內容完整無遺漏
- 運行: `python scripts/parse_administrative_appeal.py --test`

---

### Task 10.3: 建立訴願法初始化腳本
**File**: `scripts/init_administrative_appeal.py` (新建)

- [ ] 建立初始化腳本檔案
- [ ] 實作主要功能：
  - [ ] 調用解析函數獲取法條資料
  - [ ] 為每個條文設定 `type = "administrative-appeal"`
  - [ ] 確保 `lang = "zh-TW"` 欄位存在
  - [ ] 使用 `LawModel` 驗證資料結構
  - [ ] 使用複合鍵 `(article_number, lang, type)` 進行 upsert
  - [ ] 統計插入和更新數量
- [ ] 添加命令列參數支持：
  - [ ] `--target`: 選擇資料庫 (local/remote/both)
  - [ ] `--dry-run`: 測試模式，不實際寫入
  - [ ] `--verbose`: 詳細輸出模式
- [ ] 添加詳細的日誌輸出
- [ ] 添加錯誤處理和回滾機制

**Validation**:
- 在本地測試資料庫執行腳本
- 驗證所有 101 條法條都被正確插入
- 確認資料庫中的法條有正確的 `type` 和 `lang` 欄位
- 執行 `db.laws.find({type: "administrative-appeal"}).count()` 驗證總數為 101

---

### Task 10.4: 建立訴願法驗證腳本
**File**: `scripts/verify_administrative_appeal.py` (新建)

- [ ] 建立驗證腳本檔案
- [ ] 實作驗證功能：
  - [ ] 驗證條文總數 (應為 101 條)
  - [ ] 驗證章節分布 (應有 5 章)
  - [ ] 檢查必要欄位完整性
  - [ ] 驗證 `article_number_int` 連續性
  - [ ] 檢查內容不為空
  - [ ] 統計各章條文數量
- [ ] 生成詳細的驗證報告
- [ ] 如有問題，輸出具體錯誤資訊

**Validation**:
- 執行驗證腳本應通過所有檢查
- 運行: `python scripts/verify_administrative_appeal.py`

---

### Task 10.5: 測試訴願法資料整合
**File**: `test/test_administrative_appeal.py` (新建)

- [ ] 建立測試檔案
- [ ] 測試解析功能：
  - [ ] 測試 markdown 解析正確性
  - [ ] 測試章節識別
  - [ ] 測試條文內容提取
  - [ ] 測試 `article_number_int` 生成
- [ ] 測試資料載入：
  - [ ] 驗證所有訴願法條文正確插入
  - [ ] 檢查資料結構完整性
  - [ ] 確認 `type = "administrative-appeal"`
  - [ ] 確認章節層級正確
- [ ] 測試查詢功能：
  - [ ] 依法律類型過濾查詢
  - [ ] 依章節過濾查詢
  - [ ] 搜尋功能測試
  - [ ] 排序功能測試（使用 article_number_int）
- [ ] 執行測試：`pytest test/test_administrative_appeal.py -v`

---

### Task 10.6: 驗證與現有系統整合
**Checklist**:

- [ ] 驗證訴願法條文可在法條瀏覽頁面顯示
- [ ] 測試法律類型切換器能正確切換到訴願法
- [ ] 確認訴願法條文可以生成題目
- [ ] 驗證進度追蹤在訴願法下正常運作
- [ ] 測試搜尋功能在訴願法範圍內正確運作
- [ ] 確認統計數據按法律類型正確隔離
- [ ] 驗證章節過濾功能正常
- [ ] 測試法條詳情頁面顯示正確

---

### Task 10.7: 更新文檔
**Files**:
- [`README.md`](../README.md)
- [`docs/requirements.md`](requirements.md)
- [`docs/design.md`](design.md)

- [ ] 更新 README：
  - [ ] 在支援的法律類型列表中添加訴願法
  - [ ] 更新功能說明
  - [ ] 添加訴願法初始化指令範例
- [ ] 更新 requirements.md：
  - [ ] 添加訴願法支持的用戶故事
  - [ ] 更新法律類型列表
- [ ] 更新 design.md：
  - [ ] 更新 LAW_TYPES 常量定義
  - [ ] 添加訴願法解析與初始化設計
  - [ ] 更新資料流程圖（如有）

---

### Task 10.8: 執行生產部署（可選）
**Steps**:

- [ ] 在 staging 環境測試訴願法初始化
- [ ] 建立生產資料庫備份
- [ ] 執行 `python scripts/init_administrative_appeal.py --target remote`
- [ ] 執行驗證: `python scripts/verify_administrative_appeal.py --target remote`
- [ ] 驗證生產環境資料正確
- [ ] 監控系統運行狀態
- [ ] 記錄部署結果

---

### 完成檢查清單 (Administrative Appeal Completion Checklist)

#### 資料完整性
- [ ] 所有 101 條訴願法條文成功載入
- [ ] 訴願法條文總數正確 (101 條)
- [ ] 所有條文有正確的 `type = "administrative-appeal"`
- [ ] 章節層級結構完整 (5章)
- [ ] 所有條文內容不為空

#### 功能完整性
- [ ] 法律類型選擇器包含訴願法
- [ ] 可切換到訴願法並正確顯示條文
- [ ] 搜尋功能在訴願法範圍內正常
- [ ] 可為訴願法條文生成題目
- [ ] 進度追蹤與訴願法正確關聯

#### 測試覆蓋
- [ ] 解析腳本測試通過
- [ ] 初始化腳本測試通過
- [ ] 驗證腳本測試通過
- [ ] 系統整合測試通過

---

## 預估工時

- **Task 10.1**: LAW_TYPES 更新 - 0.5 小時
- **Task 10.2**: 解析腳本開發 - 4-6 小時
- **Task 10.3**: 初始化腳本開發 - 2-3 小時
- **Task 10.4**: 驗證腳本開發 - 1-2 小時
- **Task 10.5**: 測試開發 - 2-3 小時
- **Task 10.6**: 系統整合驗證 - 2-3 小時
- **Task 10.7**: 文檔更新 - 1-2 小時
- **Task 10.8**: 生產部署 - 1-2 小時

**總計**: 約 14-22 小時
```

---

## 🔧 技術實施細節

### 解析邏輯關鍵點

1. **章節識別**:
   - 章標題: 行首有3個空格 + "第 X 章"
   - 節標題: 行首有6個空格 + "第 X 節"
   - 需要維護當前章和節的狀態

2. **條號提取**:
   - 條號格式: "第 X 條"
   - X 可能是 1-101 的任意數字
   - `article_number_int` 直接使用條號數字

3. **內容處理**:
   - 條文內容可能有多個段落
   - 每段以數字+空格開頭 (如 "1   ", "2   ")
   - 需要移除數字標記但保留段落結構
   - 段落之間用換行符分隔

4. **章節路徑**:
   - 如果有節: "第X章 XXX / 第X節 XXX"
   - 如果無節: "第X章 XXX"

### 資料庫索引

訴願法使用現有索引，無需額外建立：
- `laws.type` (單一索引)
- `laws.(type, lang)` (複合索引)
- `laws.(type, article_number_int)` (複合索引，用於排序)

### 錯誤處理

1. **文件不存在**: 提供清晰的錯誤訊息
2. **格式錯誤**: 記錄問題行號和內容
3. **資料庫錯誤**: 實施重試機制
4. **部分失敗**: 記錄詳細日誌，繼續處理其他條文

---

## 📊 驗證標準

### 解析驗證
- ✅ 條文總數 = 101
- ✅ 章節數量 = 5
- ✅ 每條都有 article_number
- ✅ article_number_int 範圍: 1-101
- ✅ 所有 content 非空

### 資料庫驗證
- ✅ `type = "administrative-appeal"` 的文檔數 = 101
- ✅ 所有必要欄位存在
- ✅ 可以依 chapter 分組查詢
- ✅ 可以依 article_number_int 排序

### 系統整合驗證
- ✅ 法律類型選擇器顯示訴願法
- ✅ 切換到訴願法顯示 101 條
- ✅ 搜尋"訴願"返回相關條文
- ✅ 可以開始訴願法測驗
- ✅ 進度追蹤正常

---

## 🎯 執行順序建議

### 開發階段
1. **Day 1**: 
   - 更新 requirements.md (Task 10.1-相關)
   - 更新 design.md (Task 10.1-相關)
   - 更新 LAW_TYPES 常量

2. **Day 2-3**: 
   - 開發解析腳本 (Task 10.2)
   - 開發初始化腳本 (Task 10.3)
   - 測試解析邏輯

3. **Day 4**: 
   - 開發驗證腳本 (Task 10.4)
   - 編寫單元測試 (Task 10.5)
   - 本地測試完整流程

4. **Day 5**: 
   - 系統整合測試 (Task 10.6)
   - 更新文檔 (Task 10.7)
   - 準備部署

### 部署階段
5. **Day 6**: 
   - Staging 環境測試
   - 生產環境部署 (Task 10.8)
   - 驗證與監控

---

## ⚠️ 風險與緩解

### 風險 1: Markdown 格式不一致
**緩解策略**:
- 先手動檢查 markdown 文件格式
- 編寫健壯的解析邏輯處理邊界情況
- 充分的單元測試覆蓋

### 風險 2: 條文內容提取錯誤
**緩解策略**:
- 人工抽查解析結果（前10條、中間10條、後10條）
- 比對原始 markdown 與解析結果
- 使用驗證腳本自動檢查

### 風險 3: 資料庫衝突
**緩解策略**:
- 使用 upsert 避免重複插入
- 先在本地測試，再部署到生產
- 準備 rollback 腳本

### 風險 4: 與現有系統不相容
**緩解策略**:
- 完整的整合測試
- 確保遵循現有多法律支持架構
- 漸進式部署

---

## 📚 參考資料

- [`docs/requirements.md`](requirements.md) - 功能需求文檔
- [`docs/design.md`](design.md) - 系統設計文檔
- [`docs/tasks.md`](tasks.md) - 任務清單
- [`knowledge/administrative_appeal_zh.md`](../knowledge/administrative_appeal_zh.md) - 訴願法原始資料
- [`scripts/parse_patent_law.py`](../scripts/parse_patent_law.py) - 專利法解析範例
- [`scripts/init_examination_guidelines.py`](../scripts/init_examination_guidelines.py) - 審查基準初始化範例
- [`db/models.py`](../db/models.py) - 資料模型定義

---

## ✨ 總結

本實施計劃完全遵循 SSD 工作流程，確保：

1. ✅ **需求先行**: 在 requirements.md 中明確定義訴願法支持需求
2. ✅ **設計規劃**: 在 design.md 中詳細設計技術實施方案
3. ✅ **任務拆解**: 在 tasks.md 中分解為可執行的開發任務
4. ✅ **向後相容**: 利用現有多法律支持架構，無需修改核心邏輯
5. ✅ **可驗證性**: 每個階段都有明確的驗證標準
6. ✅ **文檔完整**: 完整的技術文檔和實施指南

遵循此計劃，可以安全、高效地將訴願法整合到現有系統中。
