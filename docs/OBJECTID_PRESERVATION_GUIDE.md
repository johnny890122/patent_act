# ObjectId 一致性與關聯保護指南

## 🎯 問題說明

### 關鍵問題
當重新插入或更新法條時，如果使用普通的 `insert` 或 `upsert` 操作，MongoDB 會生成新的 ObjectId，導致所有依賴該 ObjectId 的關聯資料失效。

### 受影響的關聯

```
laws._id (ObjectId)
    ↓
    ├── questions.law_id (String, ObjectId 字串)
    ├── user_law_stars.law_id (String, ObjectId 字串)
    ├── user_law_stats.law_id (String, ObjectId 字串)
    └── i18n_mapping.zh_tw_law_id / en_law_id (String, ObjectId 字串)
```

### 問題場景

```python
# ❌ 錯誤做法 - 會破壞關聯
# 舊法條: _id = ObjectId("507f1f77bcf86cd799439011")
# 相關問題: question.law_id = "507f1f77bcf86cd799439011"

# 如果重新插入法條
laws_collection.insert_one({
    'article_number': '第 1 條',
    'content': '...',
    'type': 'patent-act',
    'lang': 'zh-TW'
})
# 新法條: _id = ObjectId("507f1f77bcf86cd799439999")  # 新的 ID！

# 結果：question.law_id 指向的 ID 不再存在 → 關聯破裂
```

## ✅ 解決方案

### 策略：智能同步保持 ObjectId

使用 [`scripts/sync_with_id_preservation.py`](../scripts/sync_with_id_preservation.py) 工具：

1. **現有法條**: 保持原有 ObjectId，只更新內容
2. **新增法條**: 使用來源資料庫的 ObjectId

### 運作原理

```python
# ✅ 正確做法 - 保持 ObjectId 不變

# 步驟 1: 檢查目標資料庫是否已有此法條
existing = target_laws.find_one({
    'article_number': '第 1 條',
    'lang': 'zh-TW',
    'type': 'patent-act'
})

if existing:
    # 步驟 2: 法條已存在 - 更新內容，保持 _id
    target_laws.update_one(
        {'_id': existing['_id']},  # 使用現有 ID
        {'$set': {
            'content': new_content,
            'chapter': new_chapter,
            # ... 其他欄位
        }}
    )
    # ObjectId 保持不變！所有關聯繼續有效！
else:
    # 步驟 3: 新法條 - 使用來源的 ObjectId
    target_laws.insert_one(source_doc)  # 包含來源的 _id
```

## 🔧 使用方法

### 基本用法

```bash
# 1. 預覽同步計劃（不實際執行）
python scripts/sync_with_id_preservation.py --dry-run

# 2. 同步所有法律類型
python scripts/sync_with_id_preservation.py --law-type all

# 3. 同步特定法律類型
python scripts/sync_with_id_preservation.py --law-type administrative-appeal

# 4. 顯示詳細日誌
python scripts/sync_with_id_preservation.py --law-type all --verbose
```

### 完整工作流程

```bash
# 步驟 1: 診斷當前狀態
python scripts/diagnose_heroku_laws.py

# 步驟 2: 預覽同步計劃
python scripts/sync_with_id_preservation.py --dry-run

# 步驟 3: 執行智能同步（保持 ObjectId）
python scripts/sync_with_id_preservation.py --law-type all

# 步驟 4: 驗證結果
python scripts/diagnose_heroku_laws.py

# 步驟 5: 重啟應用（如果是生產環境）
heroku restart -a your-app-name
```

## 📊 同步結果示例

```
🔄 智能資料庫同步工具 (保持 ObjectId 一致性)
======================================================================
來源: localdb
目標: patent-act

📚 同步 專利法
======================================================================
📖 找到 168 條法條

📊 專利法 同步結果:
   ✅ 新增: 0 條
   🔄 更新: 5 條
   🔒 保持 ID: 168 條       ← 關鍵：所有 ID 保持不變
   ❌ 錯誤: 0 條

💡 優勢：
   • ObjectId 保持不變（168 條）
   • 所有關聯資料保持有效（questions, user_law_stars, user_law_stats）
   • 不需要重建關聯或重新生成問題
```

## 🆚 工具比較

### sync_local_to_remote.py （基礎同步）
```bash
python scripts/sync_local_to_remote.py --law-type all
```

❌ **問題**：
- 每次都生成新的 ObjectId
- 破壞所有關聯資料
- 需要重新生成問題和重建關聯

✅ **適用場景**：
- 全新的目標資料庫（沒有現有資料）
- 沒有任何關聯資料需要保護

### sync_with_id_preservation.py （智能同步）⭐ 推薦
```bash
python scripts/sync_with_id_preservation.py --law-type all
```

✅ **優勢**：
- 保持現有 ObjectId 不變
- 所有關聯資料保持有效
- 不需要重建關聯

✅ **適用場景**：
- 已有資料的資料庫（大多數情況）
- 已有問題、收藏、統計等關聯資料
- 生產環境更新

## 🔍 驗證關聯完整性

### 檢查問題關聯

```python
from pymongo import MongoClient
from bson import ObjectId

client = MongoClient('your_mongo_uri')
db = client.get_database()

# 檢查孤兒問題（law_id 無對應法條）
orphan_questions = []
for question in db.questions.find():
    law_id = question.get('law_id')
    if law_id:
        law = db.laws.find_one({'_id': ObjectId(law_id)})
        if not law:
            orphan_questions.append(question)

print(f"孤兒問題數量: {len(orphan_questions)}")
```

### 檢查收藏關聯

```python
# 檢查孤兒收藏
orphan_stars = []
for star in db.user_law_stars.find():
    law_id = star.get('law_id')
    if law_id:
        law = db.laws.find_one({'_id': ObjectId(law_id)})
        if not law:
            orphan_stars.append(star)

print(f"孤兒收藏數量: {len(orphan_stars)}")
```

## 🚨 重要注意事項

### 1. 不要混用同步工具

```bash
# ❌ 錯誤：先用基礎同步，再用智能同步
python scripts/sync_local_to_remote.py --law-type all  # 破壞 ID
python scripts/sync_with_id_preservation.py --law-type all  # 無法修復

# ✅ 正確：直接使用智能同步
python scripts/sync_with_id_preservation.py --law-type all
```

### 2. 備份關聯資料

在執行任何同步操作前，建議備份關聯資料：

```bash
# 備份問題
mongodump --uri="your_uri" --collection=questions --out=backup/

# 備份收藏和統計
mongodump --uri="your_uri" --collection=user_law_stars --out=backup/
mongodump --uri="your_uri" --collection=user_law_stats --out=backup/
```

### 3. 新法律類型的處理

當添加全新的法律類型時：

```bash
# 新法律類型（如訴願法）- 沒有現有資料，兩種工具都可以
python scripts/sync_with_id_preservation.py --law-type administrative-appeal

# 或
python scripts/sync_local_to_remote.py --law-type administrative-appeal
```

## 🛠️ 修復已破壞的關聯

如果不小心使用了會改變 ObjectId 的操作，導致關聯破裂：

### 選項 1: 重新生成關聯資料（慢，但完整）

```bash
# 1. 刪除舊問題
# 2. 重新生成問題（使用新的 law_id）
# 3. 清空用戶收藏和統計（或手動更新）
```

### 選項 2: 使用 ID 映射更新（快，但複雜）

創建一個 old_id -> new_id 的映射，然後更新所有關聯：

```python
# 建立 ID 映射
id_mapping = {}  # old_id: new_id

# 根據 article_number + lang + type 建立映射
for old_law in old_laws:
    new_law = new_laws.find_one({
        'article_number': old_law['article_number'],
        'lang': old_law['lang'],
        'type': old_law['type']
    })
    if new_law:
        id_mapping[str(old_law['_id'])] = str(new_law['_id'])

# 更新所有問題
for old_id, new_id in id_mapping.items():
    questions.update_many(
        {'law_id': old_id},
        {'$set': {'law_id': new_id}}
    )
```

## 📚 相關工具

1. **[`scripts/sync_with_id_preservation.py`](../scripts/sync_with_id_preservation.py)** - 智能同步（保持 ObjectId）⭐ 推薦
2. **[`scripts/sync_local_to_remote.py`](../scripts/sync_local_to_remote.py)** - 基礎同步
3. **[`scripts/diagnose_heroku_laws.py`](../scripts/diagnose_heroku_laws.py)** - 診斷工具
4. **[`docs/HEROKU_LAW_FIX_GUIDE.md`](HEROKU_LAW_FIX_GUIDE.md)** - 完整修復指南

## 💡 最佳實踐

1. **總是使用智能同步工具**（除非是全新資料庫）
2. **同步前先 dry-run 預覽**
3. **備份重要資料**（特別是生產環境）
4. **同步後驗證關聯完整性**
5. **記錄每次同步操作**

---

**最後更新**: 2026-05-12
**相關文件**: 
- [`docs/HEROKU_LAW_FIX_GUIDE.md`](HEROKU_LAW_FIX_GUIDE.md) - Heroku 問題修復
- [`docs/NEW_LAW_TYPE_SOP.md`](NEW_LAW_TYPE_SOP.md) - 新增法律類型流程
