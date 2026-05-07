"""
清理 laws 集合中的舊統計欄位
在引入多用戶支持後，這些欄位已遷移到 user_law_stats 集合
"""
from pymongo import MongoClient

# MongoDB 連接
uri = 'mongodb+srv://admin:03ra64XqDM8sOBdV@cluster0.lsu6m2w.mongodb.net/patent-act?retryWrites=true&w=majority'
client = MongoClient(uri)
db = client['patent-act']

print("=== 清理 laws 集合中的舊欄位 ===\n")

# 1. 檢查有哪些 law 文檔包含舊欄位
print("1. 檢查現有的舊欄位...")
old_fields = ['attempt_count', 'avg_score', 'total_score', 'is_starred']

sample_law = db.laws.find_one({})
if sample_law:
    found_fields = []
    for field in old_fields:
        if field in sample_law:
            found_fields.append(field)
    
    if found_fields:
        print(f"   發現舊欄位: {', '.join(found_fields)}")
        
        # 統計有這些欄位的文檔數量
        for field in found_fields:
            count = db.laws.count_documents({field: {'$exists': True}})
            print(f"   - {field}: {count} 個文檔")
    else:
        print("   ✓ 沒有發現舊欄位")
else:
    print("   警告: laws 集合為空")

# 2. 移除舊欄位
print("\n2. 移除舊欄位...")
fields_to_remove = {}
for field in old_fields:
    fields_to_remove[field] = ""

result = db.laws.update_many(
    {},
    {'$unset': fields_to_remove}
)

print(f"   更新了 {result.modified_count} 個文檔")

# 3. 驗證清理結果
print("\n3. 驗證清理結果...")
sample_law_after = db.laws.find_one({})
if sample_law_after:
    remaining_old_fields = []
    for field in old_fields:
        if field in sample_law_after:
            remaining_old_fields.append(field)
    
    if remaining_old_fields:
        print(f"   ⚠️  仍然存在的舊欄位: {', '.join(remaining_old_fields)}")
    else:
        print("   ✓ 所有舊欄位已成功移除")
        
    # 顯示保留的欄位
    print(f"\n   保留的欄位: {', '.join(sample_law_after.keys())}")
else:
    print("   警告: laws 集合為空")

# 4. 檢查多用戶統計是否正常
print("\n4. 檢查多用戶統計數據...")
stats_count = db.user_law_stats.count_documents({})
print(f"   user_law_stats 記錄數: {stats_count}")

if stats_count > 0:
    sample_stat = db.user_law_stats.find_one({})
    print(f"   樣本統計: user_id={sample_stat.get('user_id')}, avg_score={sample_stat.get('avg_score'):.2f}")

client.close()
print("\n✅ 清理完成！")
