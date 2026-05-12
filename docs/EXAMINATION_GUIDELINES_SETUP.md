# 專利審查基準設定指南

## 概述

本文檔說明如何將專利審查基準（Patent Examination Guidelines）資料插入到 patent_act 系統資料庫。

## 資料來源

- **目錄位置**: [`knowledge/examination/`](../knowledge/examination/)
- **資料結構**: 按章節組織在子目錄中 (01-06)
- **檔案格式**: JSON 格式，每個檔案包含一個條文陣列
- **總檔案數**: 54 個 JSON 檔案
- **總條文數**: 1,214 條審查基準

## 資料結構

每條審查基準遵循與專利法相同的資料結構：

```json
{
  "article_number": "1.1 文件",
  "article_number_int": 1102,
  "chapter": "第一篇程序審查及專利權管理 第一章 申請專利及辦理有關專利事項之程序",
  "content": "申請專利及辦理有關專利事項所需文件...",
  "lang": "zh-TW",
  "type": "patent-examination"
}
```

### 關鍵欄位說明

| 欄位 | 說明 | 範例 |
|------|------|------|
| `article_number` | 條文編號 | "1.1 文件" |
| `article_number_int` | 排序用整數 | 1102 |
| `chapter` | 完整章節階層 | "第一篇程序審查及專利權管理 第一章..." |
| `content` | 條文內容 | 完整的法條文本 |
| `lang` | 語言標籤 | "zh-TW" |
| `type` | 法律類型 | "patent-examination" |

## 初始化步驟

### 1. 測試模式（推薦先執行）

```bash
python scripts/init_examination_guidelines.py --dry-run
```

此命令會驗證所有資料但不實際寫入資料庫。

### 2. 插入到本地資料庫

```bash
python scripts/init_examination_guidelines.py --local
```

### 3. 插入到遠端資料庫

```bash
python scripts/init_examination_guidelines.py --remote
```

**注意**: 需要在 `.env` 檔案中設定 `REMOTE_MONGO_URI`

### 4. 同時插入本地和遠端

```bash
python scripts/init_examination_guidelines.py --both
```

## 驗證資料

### 檢查插入結果

```bash
python -c "
from db.models import Database
db = Database()

# 統計審查基準數量
count = db.laws_collection.count_documents({
    'type': 'patent-examination',
    'lang': 'zh-TW'
})
print(f'審查基準總數: {count} 條')

# 查看章節分布
chapters = db.laws_collection.distinct('chapter', {
    'type': 'patent-examination'
})
print(f'章節數量: {len(chapters)}')
"
```

### 預期結果

- **審查基準總數**: 1,073 條（實際插入成功的條文）
- **處理檔案數**: 54 個 JSON 檔案
- **總處理條文**: 1,214 條（包含重複或更新的條文）

## 系統整合

### 法律類型定義

審查基準已註冊為系統支援的法律類型：

```python
# db/models.py
LAW_TYPES = {
    "patent-examination": {
        "name_zh": "專利審查基準",
        "name_en": "Patent Examination Guidelines",
        "code": "patent-examination"
    }
}
```

### 使用方式

插入成功後，審查基準將自動整合到系統中：

1. **法條瀏覽**: 在法條瀏覽頁面可以選擇「專利審查基準」
2. **題目生成**: 可以為審查基準條文生成練習題
3. **進度追蹤**: 用戶學習進度獨立於專利法追蹤
4. **搜尋功能**: 支援在審查基準範圍內搜尋

## 資料更新

如果需要更新審查基準資料：

1. 更新 `knowledge/examination/` 中的 JSON 檔案
2. 重新執行初始化腳本：
   ```bash
   python scripts/init_examination_guidelines.py --local
   ```
3. 腳本會自動進行 upsert 操作（存在則更新，不存在則插入）

## 常見問題

### Q: 執行腳本時出現 "找到 0 個 JSON 檔案"

**A**: 檢查 `knowledge/examination/` 目錄是否存在且包含子目錄和 JSON 檔案。

### Q: 部分條文顯示為「已更新」而非「新插入」

**A**: 這表示該條文之前已存在，腳本更新了其內容。這是正常行為。

### Q: 如何查看特定章節的條文？

**A**: 使用以下查詢：

```python
from db.models import Database
db = Database()

articles = db.laws_collection.find({
    'type': 'patent-examination',
    'chapter': {'$regex': '第一篇程序審查'}
})

for article in articles:
    print(f"{article['article_number']}: {article['content'][:50]}...")
```

### Q: 審查基準支援英文版本嗎？

**A**: 目前審查基準**僅支援中文版本**（zh-TW）。因此：
- 當用戶選擇「審查基準」時，前端會**自動隱藏語言切換器**
- 只有選擇「專利法」時才顯示語言切換功能（中|EN）

如果未來有英文版本審查基準，可以：
1. 添加英文 JSON 檔案
2. 設定 `lang: "en"`
3. 執行初始化腳本
4. 前端邏輯會自動支援語言切換

### Q: 初始化後如何在前端使用？

**A**: 系統會自動識別 `type: "patent-examination"` 的法條。在法律類型選擇器中選擇「專利審查基準」即可切換到審查基準模式。

## 技術細節

### 腳本特性

- ✅ **冪等性**: 可以安全地重複執行
- ✅ **資料驗證**: 使用 `LawModel` dataclass 驗證資料結構
- ✅ **錯誤處理**: 完整的錯誤捕獲和日誌記錄
- ✅ **進度追蹤**: 詳細的統計和日誌輸出
- ✅ **測試模式**: `--dry-run` 模式驗證資料而不寫入

### 資料庫索引

審查基準使用與專利法相同的索引：

- `type`: 用於過濾法律類型
- `(type, lang)`: 複合索引用於多語言查詢
- `(type, article_number_int)`: 用於排序查詢
- `(article_number, lang, type)`: 複合唯一鍵用於 upsert

## 相關文檔

- [`requirements.md`](requirements.md) - 功能需求（§9.8, §9.9）
- [`design.md`](design.md) - 技術設計（§9.8）
- [`tasks.md`](tasks.md) - 實作任務（Phase 9）
- [`scripts/init_examination_guidelines.py`](../scripts/init_examination_guidelines.py) - 初始化腳本

## 維護建議

1. **定期備份**: 在執行大規模更新前備份資料庫
2. **版本控制**: JSON 檔案納入 Git 版本控制
3. **資料驗證**: 新增或修改 JSON 檔案後先執行 `--dry-run` 測試
4. **監控日誌**: 注意執行日誌中的錯誤和警告訊息

---

📝 **更新日期**: 2026-05-11  
👤 **維護者**: 系統管理員
