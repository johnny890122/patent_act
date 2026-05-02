# 修復 i18n_mapping 重複鍵錯誤

## 問題描述

執行 production 遷移時遇到錯誤：
```
DuplicateKeyError: E11000 duplicate key error collection: patent-act.i18n_mapping 
index: article_number_1 dup key: { article_number: "157" }
```

## 原因

`i18n_mapping` collection 存在一個唯一索引 `article_number_1`，導致無法插入重複的 article_number。

## 解決方案

### 方法 1: 使用 MongoDB Atlas Web Console（推薦）

1. 登入 MongoDB Atlas (https://cloud.mongodb.com)
2. 選擇你的 Cluster
3. 點擊 "Browse Collections"
4. 找到 `patent-act` 資料庫
5. 找到 `i18n_mapping` collection
6. 點擊右上角的 "..." → "Drop Collection"
7. 確認刪除

### 方法 2: 使用 MongoDB Compass

1. 開啟 MongoDB Compass
2. 連接到你的 production database
3. 找到 `patent-act.i18n_mapping` collection
4. 右鍵點擊 collection → "Drop Collection"
5. 確認刪除

### 方法 3: 使用 MongoDB Shell（命令列）

如果你有 `mongosh` 命令列工具：

```bash
# 連接到 production database
mongosh "YOUR_MONGODB_CONNECTION_STRING"

# 在 shell 中執行
use patent-act
db.i18n_mapping.drop()
exit
```

### 方法 4: 使用 Python 腳本

創建並執行以下腳本：

```python
#!/usr/bin/env python3
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# 確保 .env 檔案中有 REMOTE_MONGO_URI
remote_uri = os.environ.get('REMOTE_MONGO_URI')

if not remote_uri:
    print("❌ 錯誤：.env 檔案中找不到 REMOTE_MONGO_URI")
    exit(1)

print(f"連接到 production database...")
client = MongoClient(remote_uri, serverSelectionTimeoutMS=5000)
db = client.get_database()

# 刪除 i18n_mapping collection
print("刪除 i18n_mapping collection...")
db.i18n_mapping.drop()
print("✅ 完成！")

client.close()
```

儲存為 `fix_mapping.py`，然後執行：
```bash
python3 fix_mapping.py
```

## 重新執行遷移

刪除 collection 後，重新執行遷移腳本：

```bash
python3 scripts/migrate_production_phase9.py --remote
```

遷移腳本會重新創建 `i18n_mapping` collection（不帶唯一索引）。

## 為什麼會發生這個問題？

1. 之前可能手動創建過 `i18n_mapping` collection
2. 手動創建時可能添加了 `article_number` 的唯一索引
3. 遷移腳本使用 `delete_many({})` 清空資料，但不會刪除索引
4. 當有重複的 article_number 時就會失敗

## 預防措施

遷移腳本已更新，現在會在步驟 3 完全刪除並重建 collection，避免索引衝突。

## 驗證修復

刪除 collection 後，檢查是否成功：

```python
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
client = MongoClient(os.environ.get('REMOTE_MONGO_URI'))
db = client.get_database()

# 應該返回 0
count = db.i18n_mapping.count_documents({})
print(f"i18n_mapping count: {count}")

# 檢查是否還有索引（collection 不存在時會報錯）
try:
    indexes = db.i18n_mapping.index_information()
    print(f"Indexes: {list(indexes.keys())}")
except:
    print("Collection 不存在（正常）")

client.close()
```

## 需要幫助？

如果遇到問題：
1. 確認已備份資料庫
2. 檢查 MongoDB 連接字串是否正確
3. 確認有權限刪除 collection
4. 查看完整的錯誤訊息

---

**最後更新：** 2026-05-03  
**相關文件：** [`MIGRATION_PHASE9_GUIDE.md`](MIGRATION_PHASE9_GUIDE.md)
