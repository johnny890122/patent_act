#!/usr/bin/env python3
"""Quick script to verify MongoDB data after seeding."""
from db.models import laws_collection
import json

print("=== 驗證 MongoDB 數據 ===\n")

# Count total documents
count = laws_collection.count_documents({})
print(f"📊 總計法條數量: {count}")

# Fetch all laws
laws = list(laws_collection.find({}, {"_id": 0}))

print("\n📖 所有法條內容:\n")
for i, law in enumerate(laws, 1):
    print(f"{i}. {law['article_number']}")
    print(f"   章節: {law['chapter']}")
    print(f"   內容: {law['content']}")
    print(f"   is_starred: {law['is_starred']}")
    print(f"   avg_score: {law['avg_score']}")
    print()

# Verify schema
print("✅ 架構驗證:")
required_fields = ['article_number', 'content', 'chapter', 'is_starred', 'total_score', 'attempt_count', 'avg_score']
for law in laws:
    for field in required_fields:
        if field not in law:
            print(f"❌ 缺少欄位: {field} in {law.get('article_number', 'unknown')}")
            break
    else:
        print(f"✅ {law['article_number']} - 所有欄位完整")

# Test unique index
print("\n🔍 測試唯一索引 (article_number):")
try:
    duplicate = {
        "article_number": "第1條",
        "content": "重複測試",
        "chapter": "測試",
        "is_starred": False,
        "total_score": 0.0,
        "attempt_count": 0,
        "avg_score": 0.0
    }
    result = laws_collection.insert_one(duplicate)
    print(f"❌ 唯一索引失敗 - 允許插入重複的 article_number")
except Exception as e:
    print(f"✅ 唯一索引正常 - 拒絕重複的 article_number")

print("\n=== 驗證完成 ===")
