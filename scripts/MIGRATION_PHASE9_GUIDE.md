# Phase 9 Production Data Migration Guide

## 概述

這份指南說明如何使用 [`migrate_production_phase9.py`](migrate_production_phase9.py) 腳本將資料庫遷移至支援國際化（i18n）的版本。

## 遷移內容

腳本會執行以下 6 個步驟：

1. **Backfill Laws Lang Field** - 為現有法條添加 `lang='zh-TW'` 欄位
2. **Insert English Laws** - 從 `knowledge/truth_law_en.json` 插入英文法條
3. **Create i18n Mappings** - 建立中英文法條的對應關係
4. **Backfill Questions Lang Field** - 為現有題目添加 `lang='zh-TW'` 欄位
5. **Translate Questions to English** - 將中文題目翻譯成英文並建立關聯
6. **Create Database Indexes** - 建立必要的資料庫索引

## 前置準備

### 1. 確認環境變數設定

確保 `.env` 檔案中包含以下設定：

```bash
# 本地資料庫
MONGO_URI=mongodb://localhost:27017/localdb

# 遠端（production）資料庫
REMOTE_MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/dbname
```

### 2. 確認資料檔案存在

確保以下檔案存在：
- `knowledge/truth_law_en.json` - 英文法條資料

### 3. 備份資料庫 ⚠️

**在執行 production 遷移前，務必先備份資料庫！**

#### MongoDB Atlas 備份方式：
1. 登入 MongoDB Atlas
2. 選擇你的 Cluster
3. 點擊 "Backup" 標籤
4. 建立手動備份快照

#### 本地 MongoDB 備份方式：
```bash
mongodump --uri="mongodb://localhost:27017/localdb" --out=backup_before_phase9
```

## 使用方式

### 階段 1: 本地測試（Dry Run）

首先在本地資料庫進行 dry run 測試：

```bash
python3 scripts/migrate_production_phase9.py --local --dry-run
```

這個命令會：
- ✅ 顯示將要執行的操作
- ✅ 不會修改資料庫
- ✅ 生成詳細的日誌檔案
- ✅ 提供預期的變更統計

檢查輸出日誌，確認：
- 法條和題目數量正確
- 沒有錯誤訊息
- 遷移步驟符合預期

### 階段 2: 本地執行

確認 dry run 結果後，在本地資料庫執行實際遷移：

```bash
python3 scripts/migrate_production_phase9.py --local
```

執行後驗證：
```bash
python3 test/verify_schema.py
```

### 階段 3: Production Dry Run

在 production 資料庫進行 dry run：

```bash
python3 scripts/migrate_production_phase9.py --remote --dry-run
```

⚠️ **重要檢查項目：**
- 確認 production 資料庫的法條和題目數量
- 確認現有資料不會遺失
- 確認翻譯數量合理

### 階段 4: Production 執行

**最後一步：執行 production 遷移**

```bash
python3 scripts/migrate_production_phase9.py --remote
```

系統會要求你確認：
```
⚠️  WARNING: You are about to modify the PRODUCTION database!
⚠️  Please ensure you have:
   1. Created a database backup
   2. Tested the migration with --dry-run
   3. Reviewed the migration logs

Type 'PROCEED' to continue:
```

輸入 `PROCEED` 後才會開始執行。

## 遷移後驗證

執行遷移後，請進行以下驗證：

### 1. 執行 Schema 驗證

```bash
python3 test/verify_schema.py
```

預期結果：
- ✅ zh-TW 和 en 法條數量相同（168 條）
- ✅ 所有法條都有 `lang` 欄位
- ✅ i18n_mapping 有 150+ 個映射
- ✅ 中英文題目數量接近
- ✅ 所有題目都有 `lang` 欄位

### 2. 執行 API 測試

```bash
python3 test/test_i18n_api.py
```

預期結果：
- ✅ GET /api/laws 支援 lang 參數
- ✅ POST /api/quiz/session 支援 lang 參數
- ✅ 雙語題目正確關聯

### 3. 手動檢查資料庫

連接到 MongoDB 並檢查：

```javascript
// 檢查法條
db.laws.countDocuments({lang: 'zh-TW'})  // 應為 168
db.laws.countDocuments({lang: 'en'})     // 應為 168
db.laws.countDocuments({lang: {$exists: false}})  // 應為 0

// 檢查題目
db.questions.countDocuments({lang: 'zh-TW'})
db.questions.countDocuments({lang: 'en'})
db.questions.countDocuments({lang: {$exists: false}})  // 應為 0

// 檢查映射
db.i18n_mapping.countDocuments({})

// 檢查索引
db.laws.getIndexes()
db.questions.getIndexes()
```

## 命令參數說明

| 參數 | 說明 |
|------|------|
| `--local` | 遷移本地資料庫 |
| `--remote` | 遷移遠端 production 資料庫 |
| `--both` | 同時遷移本地和遠端資料庫 |
| `--dry-run` | 測試模式，不修改資料庫 |
| `--skip-confirmation` | 跳過確認提示（自動化時使用）|

## 日誌檔案

每次執行都會生成日誌檔案：
```
migration_phase9_YYYYMMDD_HHMMSS.log
```

日誌包含：
- 詳細的執行步驟
- 錯誤訊息
- 統計資料
- 驗證結果

## 故障排除

### 問題 1: 連接資料庫失敗

**症狀：** `❌ Connection failed: [Errno 61] Connection refused`

**解決方式：**
- 確認 MongoDB 服務正在運行
- 檢查 `.env` 中的 `MONGO_URI` 是否正確
- 對於 MongoDB Atlas，確認 IP 白名單設定

### 問題 2: 翻譯失敗

**症狀：** `Error translating question X`

**解決方式：**
- 檢查 `.env` 中的 `OPENROUTER_API_KEY` 是否有效
- 確認 API 配額足夠
- 查看具體錯誤訊息
- 腳本會自動跳過失敗的題目並繼續

### 問題 3: 英文法條已存在

**症狀：** `Found X existing EN laws. Skipping insertion`

**解決方式：**
- 這是正常的保護機制
- 如果需要重新插入，先刪除現有英文法條：
  ```javascript
  db.laws.deleteMany({lang: 'en'})
  ```
- 然後重新執行腳本

### 問題 4: 部分題目未翻譯

**症狀：** 翻譯覆蓋率 < 90%

**解決方式：**
- 查看日誌中的錯誤訊息
- 可以重新執行腳本，它會自動只處理未翻譯的題目
- 腳本是冪等的（idempotent），多次執行是安全的

## 回滾方式

如果遷移後發現問題，可以使用備份回滾：

### MongoDB Atlas 回滾：
1. 登入 MongoDB Atlas
2. 選擇 Cluster → Backup
3. 選擇遷移前的快照
4. 點擊 "Restore"

### 本地 MongoDB 回滾：
```bash
# 先清空資料庫
mongo localdb --eval "db.dropDatabase()"

# 還原備份
mongorestore --uri="mongodb://localhost:27017/localdb" backup_before_phase9
```

## 執行時間估計

根據資料量：

| 資料量 | 本地執行 | Remote 執行 |
|--------|----------|-------------|
| 168 法條 + 100 題目 | ~2-3 分鐘 | ~5-10 分鐘 |
| 168 法條 + 500 題目 | ~5-10 分鐘 | ~15-30 分鐘 |

翻譯是最耗時的步驟（每題約 2-5 秒）。

## 安全檢查清單

執行 production 遷移前，請確認：

- [ ] 已閱讀並理解本指南
- [ ] 已在本地環境測試成功
- [ ] 已執行 production dry-run
- [ ] 已建立資料庫備份
- [ ] 已確認備份可以還原
- [ ] 已通知團隊成員
- [ ] 選擇低流量時段執行
- [ ] 準備好監控資料庫狀態
- [ ] 了解回滾步驟

## 支援

如有問題，請檢查：
1. 日誌檔案 `migration_phase9_*.log`
2. [`docs/QA_REPORT_PHASE9.md`](../docs/QA_REPORT_PHASE9.md) - Phase 9 測試報告
3. [`docs/tasks.md`](../docs/tasks.md) - Phase 9 任務清單

## 相關腳本

單獨的遷移腳本（如需單獨執行特定步驟）：
- [`init_truth_laws.py`](init_truth_laws.py) - 插入中文法條並 backfill lang
- [`init_truth_laws_en.py`](init_truth_laws_en.py) - 插入英文法條
- [`create_i18n_mapping.py`](create_i18n_mapping.py) - 建立映射
- [`migrate_questions_to_en.py`](migrate_questions_to_en.py) - 翻譯題目

## 版本資訊

- **版本：** 1.0.0
- **日期：** 2026-05-03
- **階段：** Phase 9 - Internationalization
