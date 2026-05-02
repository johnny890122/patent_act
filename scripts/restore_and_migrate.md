# 還原備份並重新執行遷移

## 步驟 1: 還原 Production 資料庫

### 方法 A: 使用 MongoDB Atlas Snapshot（推薦）

如果您在 MongoDB Atlas 上建立了 snapshot：

1. 登入 MongoDB Atlas (https://cloud.mongodb.com)
2. 選擇您的 Cluster
3. 點擊左側 "Backup" 標籤
4. 找到遷移前的 snapshot（應該在今天稍早建立）
5. 點擊 snapshot 右側的 "..." → "Restore"
6. 選擇還原方式：
   - **Download:** 下載後再上傳（較慢）
   - **Restore to Cloud Provider Snapshot:** 快速還原（推薦）
7. 確認並執行還原

### 方法 B: 使用 mongorestore（如果有本地備份）

如果您使用 `mongodump` 備份到本地 `backup_phase9_20260503` 資料夾：

```bash
# 檢查備份檔案
ls -la backup_phase9_20260503/

# 還原到 production database
mongorestore \
  --uri="YOUR_REMOTE_MONGO_URI" \
  --drop \
  backup_phase9_20260503/

# 或者指定特定資料庫
mongorestore \
  --uri="YOUR_REMOTE_MONGO_URI" \
  --nsInclude="patent-act.*" \
  --drop \
  backup_phase9_20260503/patent-act/
```

**參數說明：**
- `--drop`: 還原前刪除現有 collection（清空錯誤狀態）
- `--nsInclude`: 只還原特定資料庫的資料

## 步驟 2: 驗證還原結果

還原完成後，檢查資料：

```bash
# 使用 Python 快速檢查
python3 -c "
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ.get('REMOTE_MONGO_URI'))
db = client.get_database()

print('Laws:', db.laws.count_documents({}))
print('Questions:', db.questions.count_documents({}))
print('i18n_mapping:', db.i18n_mapping.count_documents({}))
print('zh-TW laws:', db.laws.count_documents({'lang': 'zh-TW'}))
print('EN laws:', db.laws.count_documents({'lang': 'en'}))

client.close()
"
```

**預期結果（還原到遷移前狀態）：**
- Laws 總數應該回到原始數量
- 檢查 `lang` 欄位的分布
- i18n_mapping 應該被清空或回到之前狀態

## 步驟 3: 重新執行遷移（使用修復後的腳本）

### 3.1 先 Dry-run 測試

```bash
python3 scripts/migrate_production_phase9.py --remote --dry-run
```

檢查輸出，確認：
- ✅ 資料庫連接成功
- ✅ 顯示正確的法條和題目數量
- ✅ 沒有錯誤訊息
- ✅ 預期的變更看起來合理

### 3.2 執行實際遷移

```bash
python3 scripts/migrate_production_phase9.py --remote
```

系統會提示：
```
⚠️  WARNING: You are about to modify the PRODUCTION database!
⚠️  Please ensure you have:
   1. Created a database backup
   2. Tested the migration with --dry-run
   3. Reviewed the migration logs

Type 'PROCEED' to continue:
```

輸入 `PROCEED` 開始執行。

### 3.3 監控執行過程

觀察以下輸出：

```
STEP 1: Backfill Laws Lang Field
============================================================
✅ Completed

STEP 2: Insert English Laws
============================================================
✅ Completed

STEP 3: Create i18n Mappings  <-- 這裡會使用 drop() 避免索引衝突
============================================================
Dropping i18n_mapping collection...
✅ Collection dropped successfully
✅ Created 168 mappings

STEP 4: Backfill Questions Lang Field
============================================================
✅ Completed

STEP 5: Translate Questions to English
============================================================
Progress: 10/100 (10%)
Progress: 20/100 (20%)
...
✅ Translated X questions

STEP 6: Create Database Indexes
============================================================
✅ All indexes created
```

## 步驟 4: 驗證遷移結果

### 4.1 執行自動驗證

```bash
# Schema 驗證
python3 test/verify_schema.py

# API 測試
python3 test/test_i18n_api.py
```

### 4.2 手動檢查

```python
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ.get('REMOTE_MONGO_URI'))
db = client.get_database()

print("=" * 60)
print("POST-MIGRATION VERIFICATION")
print("=" * 60)

# Laws
total_laws = db.laws.count_documents({})
zh_laws = db.laws.count_documents({'lang': 'zh-TW'})
en_laws = db.laws.count_documents({'lang': 'en'})
laws_no_lang = db.laws.count_documents({'lang': {'$exists': False}})

print(f"\nLaws Collection:")
print(f"  Total: {total_laws}")
print(f"  zh-TW: {zh_laws}")
print(f"  EN: {en_laws}")
print(f"  Without lang: {laws_no_lang} {'✅' if laws_no_lang == 0 else '❌'}")

# Questions
total_q = db.questions.count_documents({})
zh_q = db.questions.count_documents({'lang': 'zh-TW'})
en_q = db.questions.count_documents({'lang': 'en'})
q_no_lang = db.questions.count_documents({'lang': {'$exists': False}})

print(f"\nQuestions Collection:")
print(f"  Total: {total_q}")
print(f"  zh-TW: {zh_q}")
print(f"  EN: {en_q}")
print(f"  Without lang: {q_no_lang} {'✅' if q_no_lang == 0 else '❌'}")
print(f"  Translation rate: {(en_q/zh_q*100):.1f}% {'✅' if en_q/zh_q >= 0.9 else '⚠️'}")

# Mappings
mappings = db.i18n_mapping.count_documents({})
print(f"\ni18n_mapping Collection:")
print(f"  Total mappings: {mappings} {'✅' if mappings >= zh_laws else '❌'}")

print("=" * 60)

client.close()
```

### 4.3 測試前端功能

1. 開啟應用程式
2. 測試法條列表頁面
3. 測試題目生成
4. 確認雙語內容顯示正常

## 預期時間

- **還原：** 5-15 分鐘（取決於資料量和方法）
- **遷移：** 10-30 分鐘（取決於題目數量）
- **驗證：** 5 分鐘

總計約 20-50 分鐘

## 檢查清單

還原前：
- [ ] 確認有正確的備份檔案
- [ ] 確認備份時間正確（遷移前）
- [ ] 確認連接字串正確

還原後：
- [ ] 驗證資料已正確還原
- [ ] 檢查資料完整性
- [ ] 確認應用程式可以連接

遷移前：
- [ ] 執行 dry-run 測試
- [ ] 檢查腳本已更新（使用 drop() 方法）
- [ ] 選擇低流量時段

遷移後：
- [ ] 執行自動驗證測試
- [ ] 檢查日誌檔案
- [ ] 測試前端功能
- [ ] 監控 Heroku logs

## 如果再次遇到問題

1. **查看日誌：** `migration_phase9_*.log`
2. **檢查錯誤：** 具體錯誤訊息
3. **再次還原：** 可以重複還原過程
4. **聯繫支援：** 提供完整錯誤訊息

## 快速命令參考

```bash
# 還原備份（本地備份）
mongorestore --uri="YOUR_URI" --drop backup_phase9_20260503/

# Dry-run 測試
python3 scripts/migrate_production_phase9.py --remote --dry-run

# 執行遷移
python3 scripts/migrate_production_phase9.py --remote

# 驗證結果
python3 test/verify_schema.py
python3 test/test_i18n_api.py

# 查看 Heroku logs（如果部署在 Heroku）
heroku logs --tail --app your-app-name
```

---

**準備好了嗎？開始還原並重新遷移！**

**重要提醒：** 
- 現在的腳本已經修復了 `i18n_mapping` 重複鍵問題
- 使用 `drop()` 而不是 `delete_many({})`，會完全刪除 collection 和所有索引
- 這次執行應該會成功！

如有任何問題，請查看日誌或參考：
- [`MIGRATION_PHASE9_GUIDE.md`](MIGRATION_PHASE9_GUIDE.md)
- [`fix_i18n_duplicate_key.md`](fix_i18n_duplicate_key.md)
