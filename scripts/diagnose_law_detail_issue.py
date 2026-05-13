#!/usr/bin/env python3
"""
診斷法條詳情頁面問題
檢查為什麼題目連結和數據統計消失
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

def diagnose_law_detail():
    """診斷法條詳情頁面問題"""
    if not REMOTE_MONGO_URI:
        print("❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return False
    
    try:
        print("="*70)
        print("🔍 法條詳情頁面診斷工具")
        print("="*70)
        
        # 連接資料庫
        print(f"\n🔌 連接遠端資料庫...")
        client = MongoClient(REMOTE_MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client.get_database()
        print(f"✅ 資料庫: {db.name}")
        
        laws = db['laws']
        questions = db['questions']
        user_law_stats = db['user_law_stats']
        user_progress = db['user_progress']
        users = db['users']
        
        # 獲取用戶列表
        print(f"\n{'='*70}")
        print(f"👥 用戶列表")
        print(f"{'='*70}")
        
        all_users = list(users.find())
        if not all_users:
            print("❌ 沒有找到任何用戶")
            return False
        
        print(f"找到 {len(all_users)} 個用戶:")
        for i, user in enumerate(all_users, 1):
            print(f"  {i}. {user.get('username', 'N/A')} (ID: {user['_id']})")
        
        # 選擇第一個用戶進行診斷
        user = all_users[0]
        user_id = user['_id']
        username = user.get('username', 'N/A')
        
        print(f"\n使用用戶 '{username}' (ID: {user_id}) 進行診斷")
        
        # 檢查有統計但沒有對應題目的情況
        print(f"\n{'='*70}")
        print(f"🔍 檢查用戶統計與題目的匹配情況")
        print(f"{'='*70}")
        
        # 獲取用戶的所有統計
        user_stats = list(user_law_stats.find({"user_id": user_id}))
        print(f"用戶統計記錄數: {len(user_stats)}")
        
        # 對每個統計，檢查是否有對應的題目和進度
        issues = []
        for stat in user_stats[:10]:  # 檢查前 10 個
            law_id = stat['law_id']
            
            # 檢查法條是否存在
            try:
                law = laws.find_one({"_id": ObjectId(law_id)})
            except:
                law = None
            
            if not law:
                issues.append({
                    'law_id': law_id,
                    'issue': 'law_not_found',
                    'stats': stat
                })
                continue
            
            # 檢查該法條是否有題目
            question_count = questions.count_documents({"law_id": law_id})
            
            # 檢查用戶是否有該法條相關題目的作答記錄
            if question_count > 0:
                question_ids = [str(q['_id']) for q in questions.find({"law_id": law_id})]
                progress_count = user_progress.count_documents({
                    "user_id": user_id,
                    "question_id": {"$in": question_ids}
                })
            else:
                progress_count = 0
            
            print(f"\n法條: {law.get('article_number', 'N/A')} ({law.get('type', 'N/A')})")
            print(f"  law_id: {law_id}")
            print(f"  統計: 平均分 {stat.get('avg_score', 0):.2f}, 作答 {stat.get('attempt_count', 0)} 次")
            print(f"  題目數: {question_count}")
            print(f"  進度記錄: {progress_count}")
            
            if stat.get('attempt_count', 0) > 0 and progress_count == 0:
                issues.append({
                    'law_id': law_id,
                    'article_number': law.get('article_number', 'N/A'),
                    'type': law.get('type', 'N/A'),
                    'issue': 'has_stats_but_no_progress',
                    'stats': stat,
                    'question_count': question_count
                })
            elif question_count == 0 and stat.get('attempt_count', 0) > 0:
                issues.append({
                    'law_id': law_id,
                    'article_number': law.get('article_number', 'N/A'),
                    'type': law.get('type', 'N/A'),
                    'issue': 'has_stats_but_no_questions',
                    'stats': stat
                })
        
        # 報告問題
        print(f"\n{'='*70}")
        print(f"📋 問題總結")
        print(f"{'='*70}")
        
        if issues:
            print(f"⚠️  發現 {len(issues)} 個潛在問題:")
            
            for issue in issues:
                print(f"\n{issue.get('article_number', 'N/A')} ({issue.get('type', 'N/A')})")
                print(f"  law_id: {issue['law_id']}")
                
                if issue['issue'] == 'law_not_found':
                    print(f"  ❌ 法條不存在（統計中的 law_id 無效）")
                elif issue['issue'] == 'has_stats_but_no_progress':
                    print(f"  ⚠️  有統計但沒有進度記錄")
                    print(f"      - 統計顯示作答 {issue['stats'].get('attempt_count', 0)} 次")
                    print(f"      - 但沒有找到對應的 user_progress 記錄")
                    print(f"      - 題目數: {issue.get('question_count', 0)}")
                elif issue['issue'] == 'has_stats_but_no_questions':
                    print(f"  ⚠️  有統計但沒有題目")
                    print(f"      - 統計顯示作答 {issue['stats'].get('attempt_count', 0)} 次")
                    print(f"      - 但該法條沒有任何題目")
            
            print(f"\n{'='*70}")
            print(f"💡 可能的原因:")
            print(f"{'='*70}")
            print(f"1. 更新 laws model 時，law 的 ObjectId 改變了")
            print(f"2. questions 中的 law_id 還是舊的 ObjectId")
            print(f"3. user_law_stats 是基於舊的關聯重建的，所以使用了舊的 law_id")
            print(f"4. 導致法條詳情頁面找不到對應的題目（因為 law_id 不匹配）")
            
            print(f"\n{'='*70}")
            print(f"🔧 建議的修復方案:")
            print(f"{'='*70}")
            print(f"選項 1: 重建 user_law_stats")
            print(f"  - 從 user_progress 重新計算統計")
            print(f"  - 使用 questions 中的 law_id 作為關聯")
            print(f"  - 確保使用最新的 law ObjectId")
            print(f"  指令: python scripts/rebuild_user_law_stats.py --confirm")
            
            print(f"\n選項 2: 使用 repair_broken_relationships.py")
            print(f"  - 修復所有 ObjectId 關聯")
            print(f"  - 從本地資料庫同步正確的 ObjectId")
            print(f"  指令: python scripts/repair_broken_relationships.py --dry-run")
            
        else:
            print("✅ 沒有發現明顯問題")
            print("\n可能的其他原因:")
            print("1. 前端緩存問題 - 嘗試清除瀏覽器緩存")
            print("2. API 請求問題 - 檢查瀏覽器開發者工具的 Network 標籤")
            print("3. 用戶權限問題 - 確認用戶登入狀態")
        
        # 測試一個具體的法條詳情 API 邏輯
        print(f"\n{'='*70}")
        print(f"🧪 模擬法條詳情 API 邏輯")
        print(f"{'='*70}")
        
        # 找一個有統計的法條
        if user_stats:
            test_stat = user_stats[0]
            test_law_id = test_stat['law_id']
            
            print(f"測試 law_id: {test_law_id}")
            
            # 模擬 API: get_law_questions
            try:
                law = laws.find_one({"_id": ObjectId(test_law_id)})
                if law:
                    print(f"✅ 找到法條: {law.get('article_number', 'N/A')}")
                else:
                    print(f"❌ 找不到法條")
                    
                # 查找題目
                all_questions = list(questions.find({"law_id": test_law_id}))
                print(f"該法條的總題目數: {len(all_questions)}")
                
                # 查找用戶進度
                question_ids = [str(q['_id']) for q in all_questions]
                progress_records = list(user_progress.find({
                    "user_id": user_id,
                    "question_id": {"$in": question_ids}
                }))
                print(f"用戶已作答的題目數: {len(progress_records)}")
                
                # API 只返回已作答的題目
                print(f"\n根據當前 API 邏輯 (/api/laws/<law_id>/questions):")
                print(f"  - 會返回 {len(progress_records)} 個題目（只包含已作答的）")
                print(f"  - 未作答的 {len(all_questions) - len(progress_records)} 個題目不會顯示")
                
                if len(all_questions) > 0 and len(progress_records) == 0:
                    print(f"\n⚠️  關鍵發現:")
                    print(f"  - 該法條有 {len(all_questions)} 個題目")
                    print(f"  - 但用戶沒有任何作答記錄")
                    print(f"  - 因此法條詳情頁面會顯示「尚無相關題目」")
                    print(f"  - 但統計顯示用戶作答了 {test_stat.get('attempt_count', 0)} 次")
                    print(f"\n這說明統計數據與實際進度不匹配！")
                    
            except Exception as e:
                print(f"❌ 測試出錯: {e}")
        
        print(f"\n{'='*70}")
        print(f"✅ 診斷完成")
        print(f"{'='*70}")
        
        return len(issues) == 0
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = diagnose_law_detail()
    sys.exit(0 if success else 1)
