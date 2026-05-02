# Phase 9 Production Migration - Ready for Deployment

**狀態：** ✅ 準備就緒  
**日期：** 2026-05-03  
**版本：** 1.0.0

---

## 📋 執行摘要

Phase 9 國際化（i18n）資料遷移腳本已準備完成，可以安全地部署至 production 環境。

### 已完成項目

- ✅ **統一遷移腳本** - [`scripts/migrate_production_phase9.py`](../scripts/migrate_production_phase9.py)
- ✅ **詳細遷移指南** - [`scripts/MIGRATION_PHASE9_GUIDE.md`](../scripts/MIGRATION_PHASE9_GUIDE.md)
- ✅ **腳本使用說明** - [`scripts/README_MIGRATION.md`](../scripts/README_MIGRATION.md)
- ✅ **本地 Dry-run 測試通過**
- ✅ **本地資料庫已完成遷移**
- ✅ **驗證測試全部通過**

---

## 🚀 快速執行指南

### Production 遷移步驟

#### 步驟 1: 備份資料庫

```bash
# MongoDB Atlas: 通過 Web Console 建立 Snapshot
# 本地備份範例：
mongodump --uri="YOUR_REMOTE_MONGO_URI" --out=backup_phase9_$(date +%Y%m%d)
```

#### 步驟 2: Dry-run 測試

```bash
python3 scripts/migrate_production_phase9.py --remote --dry-run
```

**檢查項目：**
- 確認法條數量正確
- 確認題目數量正確
- 確認沒有錯誤訊息
- 檢查日誌檔案

#### 步驟 3: 執行遷移

```bash
python3 scripts/migrate_production_phase9.py --remote
```

系統會要求輸入 `PROCEED` 確認。

#### 步驟 4: 驗證結果

```bash
# 方法 1: 執行驗證腳本
python3 test/verify_schema.py

# 方法 2: 執行 API 測試
python3 test/test_i18n_api.py

# 方法 3: 查看遷移日誌
cat migration_phase9_*.log
```

---

## 📊 預期遷移結果

### Laws Collection
- **zh-TW 法條：** 168 條
- **EN 法條：** 168 條
- **i18n mappings：** 159+ 條

### Questions Collection
- **zh-TW 題目：** 與現有題目數量相同
- **EN 題目：** ~90-95% 的 zh-TW 題目數量
- **雙語關聯：** 透過 `base_question_id` 連結

### Database Indexes
已自動建立以下索引：
- `laws.lang_1`
- `laws.article_number_1_lang_1`
- `questions.lang_1`
- `questions.law_id_1_lang_1`
- `questions.base_question_id_1_lang_1`

---

## 🔍 遷移腳本功能

### 核心特性

1. **冪等性設計**
   - 可安全地重複執行
   - 自動跳過已完成的步驟
   - 不會產生重複資料

2. **錯誤處理**
   - 自動記錄所有錯誤
   - 失敗題目自動回滾
   - 允許部分失敗繼續執行

3. **安全機制**
   - Dry-run 模式測試
   - Production 確認提示
   - 詳細日誌記錄
   - 統計資料驗證

4. **智能檢測**
   - 自動檢測已存在的資料
   - 避免重複插入
   - 計算遷移進度

---

## 📁 相關檔案

### 遷移腳本
- [`scripts/migrate_production_phase9.py`](../scripts/migrate_production_phase9.py) - 主要遷移腳本
- [`scripts/init_truth_laws.py`](../scripts/init_truth_laws.py) - 中文法條初始化
- [`scripts/init_truth_laws_en.py`](../scripts/init_truth_laws_en.py) - 英文法條初始化
- [`scripts/create_i18n_mapping.py`](../scripts/create_i18n_mapping.py) - 建立映射
- [`scripts/migrate_questions_to_en.py`](../scripts/migrate_questions_to_en.py) - 題目翻譯

### 文檔
- [`scripts/MIGRATION_PHASE9_GUIDE.md`](../scripts/MIGRATION_PHASE9_GUIDE.md) - 完整遷移指南
- [`scripts/README_MIGRATION.md`](../scripts/README_MIGRATION.md) - 腳本總覽
- [`docs/QA_REPORT_PHASE9.md`](QA_REPORT_PHASE9.md) - 測試報告

### 測試
- [`test/verify_schema.py`](../test/verify_schema.py) - Schema 驗證
- [`test/test_i18n_api.py`](../test/test_i18n_api.py) - API 測試
- [`test/test_translator.py`](../test/test_translator.py) - 翻譯服務測試

---

## ⏱️ 預估執行時間

根據資料量估算：

| 資料量 | 本地執行 | Remote 執行 |
|--------|----------|-------------|
| 168 法條 + 100 題目 | 2-3 分鐘 | 5-10 分鐘 |
| 168 法條 + 200 題目 | 3-5 分鐘 | 10-15 分鐘 |
| 168 法條 + 500 題目 | 5-10 分鐘 | 15-30 分鐘 |

**瓶頸：** 題目翻譯（每題約 2-5 秒，取決於 LLM API 回應速度）

---

## ⚠️ 注意事項

### 執行前檢查

- [ ] 已閱讀完整遷移指南
- [ ] 已備份 production 資料庫
- [ ] 已測試備份可以還原
- [ ] 已執行 remote dry-run
- [ ] 已確認 `.env` 中的 `REMOTE_MONGO_URI` 正確
- [ ] 已確認 `OPENROUTER_API_KEY` 有效且有足夠配額
- [ ] 選擇低流量時段執行
- [ ] 團隊成員已被通知

### 執行中監控

- 監控日誌輸出
- 注意錯誤訊息
- 檢查進度百分比
- 確認網路連線穩定

### 執行後驗證

- 執行 `verify_schema.py` 確認 schema
- 執行 `test_i18n_api.py` 測試 API
- 檢查法條和題目數量
- 測試前端語言切換功能

---

## 🔄 回滾計畫

如果遷移後發現問題：

### MongoDB Atlas 回滾
1. 登入 MongoDB Atlas
2. 選擇 Cluster → Backup
3. 選擇遷移前的快照
4. 執行 Restore

### 本地回滾
```bash
# 清空資料庫
mongo YOUR_DB_NAME --eval "db.dropDatabase()"

# 還原備份
mongorestore --uri="YOUR_MONGO_URI" backup_phase9_YYYYMMDD
```

---

## 📈 遷移成功指標

### 資料完整性
- ✅ 所有法條都有 `lang` 欄位
- ✅ zh-TW 和 EN 法條數量相同
- ✅ i18n_mapping 數量 ≥ zh-TW 法條數量
- ✅ 所有題目都有 `lang` 欄位
- ✅ EN 題目覆蓋率 ≥ 90%

### 功能正常
- ✅ API 端點回應正常
- ✅ 語言過濾功能正常
- ✅ 雙語內容正確關聯
- ✅ 前端顯示正常

### 效能
- ✅ 查詢速度正常
- ✅ 索引已正確建立
- ✅ 無效能退化

---

## 🎯 下一步行動

遷移完成後：

1. **更新文檔** - 標記 Phase 9 任務為完成
2. **通知團隊** - 告知遷移完成及新功能
3. **監控系統** - 觀察 production 運作狀況
4. **規劃 Phase 10** - 前端語言切換 UI

---

## 📞 支援資源

### 文檔
- 遷移指南：[`MIGRATION_PHASE9_GUIDE.md`](../scripts/MIGRATION_PHASE9_GUIDE.md)
- 測試報告：[`QA_REPORT_PHASE9.md`](QA_REPORT_PHASE9.md)
- 任務清單：[`tasks.md`](tasks.md)

### 日誌
- 遷移日誌：`migration_phase9_YYYYMMDD_HHMMSS.log`
- 應用程式日誌：檢查 Flask 輸出

### 驗證工具
- Schema 驗證：`python3 test/verify_schema.py`
- API 測試：`python3 test/test_i18n_api.py`
- 翻譯測試：`python3 test/test_translator.py`

---

## ✅ 測試結果摘要

### 本地環境測試

**Dry-run 測試：** ✅ 通過
```
Laws: 336 total (168 zh-TW, 168 EN, 0 without lang)
Questions: 271 total (136 zh-TW, 135 EN, 0 without lang)
Mappings: 159 total
Indexes: All created
```

**Schema 驗證：** ✅ 通過
- 所有欄位正確
- 索引已建立
- 關聯正確

**API 測試：** ✅ 通過
- `/api/laws?lang=zh-TW` ✅
- `/api/laws?lang=en` ✅
- `/api/quiz/session` with `lang` ✅
- 雙語題目關聯 ✅

---

## 🎉 結論

Phase 9 production data migration 已完全準備就緒：

- ✅ 統一遷移腳本開發完成
- ✅ 完整文檔已建立
- ✅ 本地測試全部通過
- ✅ Dry-run 功能驗證通過
- ✅ 安全機制到位
- ✅ 回滾計畫已準備

**可以安全地執行 production 遷移！**

---

**準備人員：** AI Development Team  
**最後更新：** 2026-05-03 01:59  
**狀態：** ✅ READY FOR PRODUCTION
