"""
重建 user_law_stats 集合
從 user_progress 記錄中重新計算每個用戶對每個法條的統計數據
"""
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict

# MongoDB 連接
uri = 'mongodb+srv://admin:03ra64XqDM8sOBdV@cluster0.lsu6m2w.mongodb.net/patent-act?retryWrites=true&w=majority'
client = MongoClient(uri)
db = client['patent-act']

print("=== 重建 user_law_stats ===\n")

# 1. 清空現有的 user_law_stats（可選）
print("1. 清空現有的 user_law_stats...")
result = db.user_law_stats.delete_many({})
print(f"   已刪除 {result.deleted_count} 條記錄\n")

# 2. 獲取所有 user_progress 記錄
print("2. 讀取 user_progress 記錄...")
all_progress = list(db.user_progress.find({}))
print(f"   找到 {len(all_progress)} 條 progress 記錄\n")

# 3. 按 (user_id, law_id) 分組統計
print("3. 計算統計數據...")
stats_dict = defaultdict(lambda: {'total_score': 0.0, 'attempt_count': 0})

for progress in all_progress:
    user_id = progress.get('user_id')
    question_id = progress.get('question_id')
    last_score = progress.get('last_score', 0.0)
    
    if not user_id or not question_id:
        continue
    
    # 獲取問題對應的法條ID
    try:
        question = db.questions.find_one({'_id': ObjectId(question_id)})
        if not question:
            continue
        
        law_id = question.get('law_id')
        if not law_id:
            continue
        
        # 統計數據
        key = (user_id, law_id)
        stats_dict[key]['total_score'] += last_score
        stats_dict[key]['attempt_count'] += 1
        
    except Exception as e:
        print(f"   警告: 處理 question {question_id} 時出錯: {e}")
        continue

print(f"   計算完成，共 {len(stats_dict)} 個統計記錄\n")

# 4. 寫入 user_law_stats
print("4. 寫入 user_law_stats...")
inserted_count = 0
for (user_id, law_id), stats in stats_dict.items():
    total_score = stats['total_score']
    attempt_count = stats['attempt_count']
    avg_score = total_score / attempt_count if attempt_count > 0 else 0.0
    
    db.user_law_stats.insert_one({
        'user_id': user_id,  # 保持原有類型（ObjectId）
        'law_id': law_id,    # 保持原有類型（String）
        'total_score': total_score,
        'attempt_count': attempt_count,
        'avg_score': avg_score
    })
    inserted_count += 1
    
    if inserted_count % 10 == 0:
        print(f"   已處理 {inserted_count} 條記錄...")

print(f"\n✅ 完成！共插入 {inserted_count} 條統計記錄\n")

# 5. 驗證
print("5. 驗證結果:")
total_stats = db.user_law_stats.count_documents({})
print(f"   user_law_stats 總記錄數: {total_stats}")

# 顯示樣本
sample_stats = list(db.user_law_stats.find().limit(5))
print(f"\n   樣本記錄:")
for i, stat in enumerate(sample_stats, 1):
    print(f"   {i}. user_id={stat.get('user_id')}, law_id={stat.get('law_id')[:20]}...")
    print(f"      avg_score={stat.get('avg_score'):.2f}, attempt_count={stat.get('attempt_count')}")

client.close()
print("\n✅ 遷移完成！")
