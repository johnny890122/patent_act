# 新增法典標準作業流程 (SOP)
## Standard Operating Procedure for Adding New Law Types

基於訴願法成功上線的經驗總結，本文檔提供標準化流程，用於未來新增其他法典（如商標法、著作權法、行政訴訟法等）。

---

## 📋 目錄

1. [前置準備](#前置準備)
2. [SSD 三步驟工作流程](#ssd-三步驟工作流程)
3. [核心實施步驟](#核心實施步驟)
4. [常見問題與解決方案](#常見問題與解決方案)
5. [檢查清單](#檢查清單)
6. [參考範例](#參考範例)

---

## 🎯 前置準備

### 1. 確認法典資訊

在開始前，請確認以下資訊：

- [ ] **法典名稱**：中文全名（如：訴願法）
- [ ] **英文名稱**：英文全名（如：Administrative Appeal Act）
- [ ] **法典代碼**：系統內部識別碼（如：`administrative-appeal`）
- [ ] **條文總數**：預期條數（如：101 條）
- [ ] **章節結構**：章節層級（如：5 章 12 節）
- [ ] **資料來源格式**：JSON / Markdown / PDF 等

### 2. 準備原始資料

- [ ] 確保資料檔案完整且格式正確
- [ ] 建議路徑：`knowledge/<law_type>_zh.md` 或 `knowledge/<law_type>/`
- [ ] 確認資料編碼為 UTF-8

### 3. 環境檢查

```bash
# 確認資料庫連接正常
python -c "from db.models import Database; db = Database(); print('✅ DB OK')"

# 確認現有法律類型
python -c "from db.models import LAW_TYPES; print(LAW_TYPES.keys())"
```

---

## 🔄 SSD 三步驟工作流程

### Step 1: 更新 Requirements（需求文檔）

**文件**: [`docs/requirements.md`](requirements.md)

**位置**: 在現有的 Section 9 後添加新的 subsection

**模板**:
```markdown
### 9.X [法典名稱]支持 ([English Name] Support)

**Story:** As a user preparing for [考試名稱], I want to study [法典名稱] alongside other laws.

**Scenario:**
- System supports [法典名稱] as a separate law type: `"<law-type-code>"`
- [法典名稱] is structured with X chapters and Y articles
- Users can switch between different law types including [法典名稱]
- Each article can have associated practice questions
- Progress tracking is independent between all law types
- Search and filtering work across [法典名稱] content

### 9.X+1 [法典名稱]資料結構 ([English Name] Data Structure)

**Story:** As an administrator, I want [法典名稱] data to be properly structured for easy management.

**Scenario:**
- [法典名稱] articles stored as [格式說明]
- Organized with X chapters and Y articles
- Each article contains:
  - `article_number`: Article identifier (e.g., "第 1 條")
  - `article_number_int`: Integer for sorting
  - `chapter`: Full chapter hierarchy
  - `content`: Full text content
  - `lang`: Language tag (zh-TW)
  - `type`: Set to "<law-type-code>"
- Parsing script extracts structured data
- Same database schema as patent law articles (uses `LawModel`)
```

---

### Step 2: 更新 Design（設計文檔）

**文件**: [`docs/design.md`](design.md)

#### 2.1 更新 LAW_TYPES 定義

**位置**: Section 9.2

```python
LAW_TYPES = {
    # ... 現有法律類型 ...
    "<law-type-code>": {
        "name_zh": "<中文名稱>",
        "name_en": "<English Name>",
        "code": "<law-type-code>"
    }
}
```

#### 2.2 添加解析與初始化設計

**位置**: 在 Section 9 增加新的 subsection

**模板**:
```markdown
### 9.X [法典名稱]解析與初始化

**資料來源**: 
- Location: `knowledge/<filename>`
- Format: [格式說明]
- Structure: [結構說明]
- Total: Y articles, X chapters

**解析邏輯**: `scripts/parse_<law_type>.py`
[詳細解析邏輯說明]

**初始化腳本**: `scripts/init_<law_type>.py`
[腳本功能說明]

**驗證腳本**: `scripts/verify_<law_type>.py`
[驗證項目清單]
```

---

### Step 3: 更新 Tasks（任務清單）

**文件**: [`docs/tasks.md`](tasks.md)

**位置**: 添加新的 Phase

**模板**: 參考 [Phase 10](tasks.md#phase-10-訴願法支持) 的結構

---

## 🛠️ 核心實施步驟

### Step 4: 更新 LAW_TYPES 常量

**文件**: [`db/models.py`](../db/models.py)

**位置**: Line 11-37

```python
# 在 LAW_TYPES 字典中添加
"<law-type-code>": {
    "name_zh": "<中文名稱>",
    "name_en": "<English Name>",
    "code": "<law-type-code>"
}
```

**驗證**:
```bash
python -c "from db.models import LAW_TYPES; print('<law-type-code>' in LAW_TYPES)"
# 應輸出: True
```

---

### Step 5: 建立解析腳本

**文件**: `scripts/parse_<law_type>.py`

**參考範例**: [`scripts/parse_administrative_appeal.py`](../scripts/parse_administrative_appeal.py)

**核心函數**:
```python
def parse_<law_type>_md(file_path: str) -> List[Dict]:
    """
    解析 [法典名稱] 文件，提取結構化法條資料
    
    Returns:
        List[Dict]: 包含所有法條的列表，每個字典包含：
            - article_number: 條號字串
            - article_number_int: 條號整數
            - chapter: 完整章節路徑
            - content: 條文內容
    """
    # 實作解析邏輯
    pass
```

**必要功能**:
- [ ] 讀取原始資料檔案
- [ ] 識別章節結構
- [ ] 提取條號和內容
- [ ] 生成 `article_number_int` 用於排序
- [ ] 命令列支持（`--test`, `--output`）
- [ ] 錯誤處理和日誌輸出

**測試**:
```bash
python scripts/parse_<law_type>.py --test
# 應顯示: ✅ 成功解析 X 條
```

---

### Step 6: 建立初始化腳本

**文件**: `scripts/init_<law_type>.py`

**參考範例**: [`scripts/init_administrative_appeal.py`](../scripts/init_administrative_appeal.py)

**核心函數**:
```python
def init_<law_type>(target='local', dry_run=False, verbose=False):
    """
    初始化 [法典名稱] 到資料庫
    
    Args:
        target: 'local' | 'remote' | 'both'
        dry_run: 測試模式
        verbose: 詳細日誌
    
    Returns:
        (inserted_count, updated_count, error_count)
    """
    # 1. 調用解析函數
    articles = parse_<law_type>_md('knowledge/<filename>')
    
    # 2. 設定 type 和 lang
    for article in articles:
        article['type'] = '<law-type-code>'
        article['lang'] = 'zh-TW'
    
    # 3. 使用 LawModel 驗證
    # 4. Upsert 到資料庫
    # 5. 統計結果
```

**命令列參數**:
- `--target`: 目標資料庫（local/remote/both）
- `--dry-run`: 測試模式
- `--verbose`: 詳細輸出

**測試**:
```bash
# Dry run
python scripts/init_<law_type>.py --target local --dry-run

# 實際執行
python scripts/init_<law_type>.py --target local
# 應顯示: ✅ 插入: X 條
```

---

### Step 7: 建立驗證腳本

**文件**: `scripts/verify_<law_type>.py`

**參考範例**: [`scripts/verify_administrative_appeal.py`](../scripts/verify_administrative_appeal.py)

**驗證項目**:
1. ✅ 條文總數（應為預期數量）
2. ✅ 章節分布（章節數量正確）
3. ✅ 必要欄位完整性（6個必要欄位）
4. ✅ 內容完整性（無空內容）
5. ✅ 條號範圍（連續且正確）
6. ✅ Type 欄位正確（all = `<law-type-code>`）
7. ✅ 無重複條文

**測試**:
```bash
python scripts/verify_<law_type>.py
# 應顯示: 🎉 所有資料庫驗證通過！
```

---

### Step 8: 確認前端自動整合

**前端已完全動態化，無需修改！**

驗證點：
- [ ] [`templates/base.html`](../templates/base.html:35-41) - 選擇器為動態載入
- [ ] [`static/js/main.js`](../static/js/main.js:147-176) - `populateLawTypeSelector()` 自動載入

**如何驗證**:
1. 啟動應用：`flask run`
2. 開啟瀏覽器開發者工具 → Network
3. 檢查 `/api/law-types` 請求
4. 確認新法典出現在回應中

---

## ⚠️ 常見問題與解決方案

### 問題 1: 索引衝突錯誤

**錯誤訊息**:
```
DuplicateKeyError: E11000 duplicate key error ... 
index: article_number_1_lang_1
```

**原因**: 
舊的兩欄位索引導致不同法律類型無法有相同條號。

**解決方案**:
```bash
# 執行索引修復工具
python scripts/fix_laws_index.py --target local

# 確認 db/models.py 已使用三欄位索引
# Line ~147-162 應為:
# create_index([('article_number', 1), ('lang', 1), ('type', 1)], unique=True)
```

**預防措施**:
- ✅ [`db/models.py`](../db/models.py:147-162) 已正確配置三欄位索引
- ✅ [`scripts/fix_laws_index.py`](../scripts/fix_laws_index.py) 工具可重複使用

---

### 問題 2: 解析失敗或條文數量不正確

**可能原因**:
1. 資料格式不一致
2. 編碼問題（非 UTF-8）
3. 章節識別邏輯錯誤

**除錯步驟**:
```bash
# 1. 手動檢查原始文件
head -50 knowledge/<filename>

# 2. 測試解析腳本
python scripts/parse_<law_type>.py --test --output test_output.json

# 3. 檢查輸出
cat test_output.json | jq '. | length'  # 條文數量
cat test_output.json | jq '.[0]'        # 第一條內容

# 4. 人工驗證前10條、中10條、後10條
```

---

### 問題 3: 前端選擇器未顯示新法典

**檢查清單**:
1. ✅ LAW_TYPES 已更新？
   ```bash
   python -c "from db.models import LAW_TYPES; print(LAW_TYPES.keys())"
   ```

2. ✅ 資料已插入資料庫？
   ```bash
   python scripts/verify_<law_type>.py
   ```

3. ✅ API 回應包含新法典？
   ```bash
   curl http://localhost:5000/api/law-types | jq
   ```

4. ✅ 瀏覽器已刷新（硬重整）？
   - Windows: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

---

### 問題 4: 應用啟動報錯

**常見錯誤**:
- Module import error → 確認 Python 環境和依賴
- Database connection error → 檢查 MongoDB 運行狀態
- Index creation error → 執行 `fix_laws_index.py`

**除錯方法**:
```bash
# 檢查 Python 環境
python --version
pip list | grep pymongo

# 檢查 MongoDB
mongosh  # 或 mongo
# 執行: show dbs

# 檢查應用日誌
flask run 2>&1 | tee app.log
```

---

## ✅ 完整檢查清單

### 規劃階段
- [ ] 確認法典資訊（名稱、代碼、條數、結構）
- [ ] 準備原始資料檔案
- [ ] 建立實施計劃文檔

### SSD 工作流程
- [ ] 更新 `docs/requirements.md`（Section 9.X）
- [ ] 更新 `docs/design.md`（LAW_TYPES + Section 9.X）
- [ ] 更新 `docs/tasks.md`（新增 Phase）

### 核心實施
- [ ] 更新 `db/models.py` 的 LAW_TYPES 常量
- [ ] 建立 `scripts/parse_<law_type>.py`
- [ ] 建立 `scripts/init_<law_type>.py`
- [ ] 建立 `scripts/verify_<law_type>.py`
- [ ] 執行解析測試
- [ ] 執行初始化（dry-run）
- [ ] 執行初始化（實際）
- [ ] 執行驗證檢查

### 系統驗證
- [ ] 資料庫驗證通過（7/7）
- [ ] 應用可正常啟動
- [ ] API 回應包含新法典
- [ ] 前端選擇器顯示新法典
- [ ] 可切換到新法典並瀏覽條文
- [ ] 搜尋功能正常
- [ ] 可生成題目（可選）

### 文檔與部署
- [ ] 更新 README（如需要）
- [ ] 建立 CHANGELOG 記錄
- [ ] 準備生產環境部署腳本
- [ ] 執行生產環境部署（可選）

---

## 📚 參考範例

### 訴願法實施案例

完整的訴願法插入流程可作為範本參考：

**文檔**:
- 實施計劃：[`docs/ADMINISTRATIVE_APPEAL_IMPLEMENTATION_PLAN.md`](ADMINISTRATIVE_APPEAL_IMPLEMENTATION_PLAN.md)
- 需求更新：[`docs/requirements.md#section-910-911`](requirements.md#910-訴願法支持-administrative-appeal-act-support)
- 設計更新：[`docs/design.md#section-911`](design.md#911-訴願法解析與初始化-administrative-appeal-act-parsing-and-initialization)
- 任務清單：[`docs/tasks.md#phase-10`](tasks.md#phase-10-訴願法支持-administrative-appeal-act-support)

**腳本**:
- 解析：[`scripts/parse_administrative_appeal.py`](../scripts/parse_administrative_appeal.py)
- 初始化：[`scripts/init_administrative_appeal.py`](../scripts/init_administrative_appeal.py)
- 驗證：[`scripts/verify_administrative_appeal.py`](../scripts/verify_administrative_appeal.py)

**測試結果**:
- ✅ 101 條訴願法全部成功插入
- ✅ 7/7 驗證檢查通過
- ✅ 前後端完全整合
- ✅ 零錯誤、零警告

---

## 🎯 快速開始模板

### 新法典快速啟動清單

```bash
# 1. 準備資料
mkdir -p knowledge/<law_type>
# 放置資料檔案到 knowledge/

# 2. 更新常量
# 編輯 db/models.py，添加到 LAW_TYPES

# 3. 建立腳本（從範本複製）
cp scripts/parse_administrative_appeal.py scripts/parse_<law_type>.py
cp scripts/init_administrative_appeal.py scripts/init_<law_type>.py
cp scripts/verify_administrative_appeal.py scripts/verify_<law_type>.py

# 4. 修改腳本內容
# - 更新檔案路徑
# - 更新 law type 代碼
# - 調整解析邏輯（如需要）

# 5. 測試流程
python scripts/parse_<law_type>.py --test
python scripts/init_<law_type>.py --dry-run
python scripts/init_<law_type>.py --target local
python scripts/verify_<law_type>.py

# 6. 啟動應用驗證
flask run --port 5001
# 開啟瀏覽器檢查法律類型選擇器
```

---

## 📊 預估時間表

基於訴願法實施經驗：

| 階段 | 預估時間 | 說明 |
|------|----------|------|
| 規劃與文檔 | 2-3 小時 | Requirements + Design + Tasks |
| 解析腳本開發 | 3-5 小時 | 依資料格式複雜度而定 |
| 初始化腳本 | 1-2 小時 | 模板化，快速 |
| 驗證腳本 | 1-2 小時 | 模板化，快速 |
| 測試與除錯 | 2-4 小時 | 依資料品質而定 |
| 文檔完善 | 1-2 小時 | README, CHANGELOG |
| **總計** | **10-18 小時** | 約 1.5-2.5 個工作日 |

---

## 🏆 最佳實踐

### 1. 遵循 SSD 規範
始終按照 Requirements → Design → Tasks → Implementation 的順序進行。

### 2. 先測試後執行
所有腳本都先用 `--dry-run` 或 `--test` 參數驗證。

### 3. 使用版本控制
每個階段完成後提交 Git：
```bash
git add .
git commit -m "feat: add <law-type> - <stage>"
```

### 4. 保持文檔同步
代碼和文檔同步更新，避免文檔過時。

### 5. 充分驗證
至少執行 7 項驗證檢查，確保資料完整性。

### 6. 模組化設計
腳本保持獨立，可單獨測試和重用。

---

## 📞 支援與維護

### 遇到問題？

1. **檢查本 SOP 文檔**：大多數問題已記錄解決方案
2. **參考訴願法案例**：完整的實施範例
3. **執行驗證腳本**：快速定位問題
4. **查看應用日誌**：詳細錯誤訊息

### 維護更新

本 SOP 應隨著系統演進持續更新：
- 新增常見問題和解決方案
- 優化腳本範本
- 記錄新的最佳實踐

---

## 🎊 總結

遵循本 SOP，您可以：

✅ **標準化流程**：每次新增法典都遵循相同步驟  
✅ **減少錯誤**：預防已知問題，快速除錯  
✅ **提高效率**：模板化腳本，快速開發  
✅ **確保品質**：完整驗證，資料可靠  
✅ **易於維護**：文檔完整，便於交接  

**下次新增法典時，只需按照本 SOP 執行即可！**

---

*最後更新：2026-05-12*  
*基於訴願法成功上線經驗編寫*
