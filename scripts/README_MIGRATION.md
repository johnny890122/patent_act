# Phase 9 Data Migration Scripts

## 快速開始

### 對於 Production 資料庫遷移

如果您需要將 production 資料庫遷移至支援國際化（i18n）：

**推薦使用統一遷移腳本：**

```bash
# 1. 先 dry-run 測試
python3 scripts/migrate_production_phase9.py --remote --dry-run

# 2. 確認無誤後執行
python3 scripts/migrate_production_phase9.py --remote
```

詳細說明請參考 → [`MIGRATION_PHASE9_GUIDE.md`](MIGRATION_PHASE9_GUIDE.md)

---

## 腳本總覽

### 🚀 統一遷移腳本（推薦）

#### [`migrate_production_phase9.py`](migrate_production_phase9.py)
**完整的 Phase 9 i18n 遷移腳本**

執行所有 6 個遷移步驟：
1. Backfill laws lang field
2. Insert English laws
3. Create i18n mappings
4. Backfill questions lang field
5. Translate questions to English
6. Create database indexes

**特色：**
- ✅ 一鍵完成所有遷移
- ✅ Dry-run 模式測試
- ✅ 詳細日誌記錄
- ✅ 自動驗證結果
- ✅ 安全確認機制
- ✅ 冪等設計（可重複執行）

**使用方式：**
```bash
# Dry run 測試
python3 scripts/migrate_production_phase9.py --local --dry-run
python3 scripts/migrate_production_phase9.py --remote --dry-run

# 實際執行
python3 scripts/migrate_production_phase9.py --local
python3 scripts/migrate_production_phase9.py --remote
python3 scripts/migrate_production_phase9.py --both
```

---

### 📚 個別遷移腳本（進階使用）

如果需要單獨執行特定步驟，可使用以下腳本：

#### [`init_truth_laws.py`](init_truth_laws.py)
**插入中文法條並 backfill lang 欄位**

從 `knowledge/truth_law.json` 插入 168 條中文法條。

```bash
python3 scripts/init_truth_laws.py --local
python3 scripts/init_truth_laws.py --remote
```

#### [`init_truth_laws_en.py`](init_truth_laws_en.py)
**插入英文法條**

從 `knowledge/truth_law_en.json` 插入 168 條英文法條。

```bash
python3 scripts/init_truth_laws_en.py --local
python3 scripts/init_truth_laws_en.py --remote
```

#### [`create_i18n_mapping.py`](create_i18n_mapping.py)
**建立中英文法條映射**

在 `i18n_mapping` collection 中建立雙向映射關係。

```bash
python3 scripts/create_i18n_mapping.py --local
python3 scripts/create_i18n_mapping.py --remote
```

#### [`migrate_questions_to_en.py`](migrate_questions_to_en.py)
**翻譯題目至英文**

- 為現有題目添加 `lang='zh-TW'` 和 `base_question_id`
- 使用 LLM 翻譯每題至英文
- 建立雙語題目關聯

```bash
# Dry run
python3 scripts/migrate_questions_to_en.py --local --dry-run

# 執行
python3 scripts/migrate_questions_to_en.py --local
python3 scripts/migrate_questions_to_en.py --remote
```

---

## 資料解析腳本

### [`parse_patent_law.py`](parse_patent_law.py)
從 `knowledge/patent_law_zh.md` 解析中文專利法，生成 `knowledge/truth_law.json`。

### [`parse_patent_law_en.py`](parse_patent_law_en.py)
從 `knowledge/patent_law_en.md` 解析英文專利法，生成 `knowledge/truth_law_en.json`。

---

## 測試腳本

### [`test_init.py`](test_init.py)
測試資料庫初始化功能。

---

## 遷移流程建議

### 新專案初始化

```bash
# 1. 解析法條
python3 scripts/parse_patent_law.py
python3 scripts/parse_patent_law_en.py

# 2. 初始化資料庫（使用統一腳本）
python3 scripts/migrate_production_phase9.py --local
```

### 現有專案升級（加入 i18n 支援）

```bash
# 使用統一遷移腳本（推薦）
python3 scripts/migrate_production_phase9.py --remote --dry-run
python3 scripts/migrate_production_phase9.py --remote
```

或者分步執行：

```bash
# Step 1: Backfill zh-TW laws
python3 scripts/init_truth_laws.py --remote

# Step 2: Insert EN laws
python3 scripts/init_truth_laws_en.py --remote

# Step 3: Create mappings
python3 scripts/create_i18n_mapping.py --remote

# Step 4 & 5: Translate questions
python3 scripts/migrate_questions_to_en.py --remote
```

---

## 驗證遷移結果

```bash
# 執行 schema 驗證
python3 test/verify_schema.py

# 執行 API 測試
python3 test/test_i18n_api.py

# 查看完整測試報告
cat docs/QA_REPORT_PHASE9.md
```

---

## 常見問題

### Q: 為什麼推薦使用統一遷移腳本？

A: [`migrate_production_phase9.py`](migrate_production_phase9.py) 提供：
- 完整的遷移流程控制
- 自動化錯誤處理
- 詳細的日誌記錄
- Dry-run 測試模式
- 冪等性設計（可重複執行）

### Q: 已經執行過部分腳本，可以使用統一腳本嗎？

A: 可以！統一腳本會自動檢測已完成的步驟並跳過，只執行未完成的部分。

### Q: 翻譯需要多久時間？

A: 取決於題目數量：
- 100 題 ≈ 3-5 分鐘
- 500 題 ≈ 15-25 分鐘
- 1000 題 ≈ 30-50 分鐘

### Q: 翻譯失敗怎麼辦？

A: 腳本會自動：
- 記錄錯誤訊息
- 回滾失敗的題目
- 繼續處理剩餘題目
- 可以重新執行處理失敗的題目

### Q: 如何回滾遷移？

A: 參考 [`MIGRATION_PHASE9_GUIDE.md`](MIGRATION_PHASE9_GUIDE.md) 的回滾部分，使用資料庫備份還原。

---

## 安全注意事項

⚠️ **遷移 Production 資料庫前必須：**

1. **建立資料庫備份**
2. **執行 dry-run 測試**
3. **在低流量時段執行**
4. **監控執行過程**
5. **準備好回滾方案**

---

## 相關文件

- [`MIGRATION_PHASE9_GUIDE.md`](MIGRATION_PHASE9_GUIDE.md) - 詳細遷移指南
- [`../docs/QA_REPORT_PHASE9.md`](../docs/QA_REPORT_PHASE9.md) - Phase 9 測試報告
- [`../docs/tasks.md`](../docs/tasks.md) - Phase 9 任務清單
- [`../docs/design.md`](../docs/design.md) - 系統設計文件

---

## 腳本參數說明

所有遷移腳本都支援：

| 參數 | 說明 |
|------|------|
| `--local` | 操作本地資料庫 |
| `--remote` | 操作遠端 production 資料庫 |
| `--both` | 同時操作兩個資料庫 |
| `--dry-run` | 測試模式（僅 migrate_production_phase9.py 和 migrate_questions_to_en.py）|

---

## 日誌檔案

遷移腳本會自動生成日誌：

- `migration_phase9_YYYYMMDD_HHMMSS.log` - 統一遷移腳本
- 其他腳本的日誌輸出至 console

---

## 支援與回饋

如遇到問題：
1. 檢查日誌檔案
2. 參考詳細指南
3. 查看測試報告
4. 檢查資料庫連接設定（`.env` 檔案）

---

**最後更新：** 2026-05-03  
**Phase:** 9 - Internationalization
