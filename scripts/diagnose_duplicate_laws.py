#!/usr/bin/env python3
"""
診斷重複法條問題
檢查為什麼同一個法條有多個 ObjectId
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

def diagnose_duplicate_laws():
    """診斷重複法條問題"""
    if not REMOTE_MONGO_URI:
        print("❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return False
    
    try:
        print("="*70)
        print("🔍 重複法條診斷工具")
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
        
        # 檢查用戶提到的兩個 ObjectId
        print(f"\n{'='*70}")
        print(f"🔍 檢查用戶提到的兩個法條 ObjectId")
        print(f"{'='*70}")
        
        id1 = "69f5ad839b36b5575cee9d71"
        id2 = "6a034b9f74cf1bf15b83e4ee"
        
        for law_id in [id1, id2]:
            print(f"\n檢查 ObjectId: {law_id}")
            try:
                law = laws.find_one({"_id": ObjectId(law_id)})
                if law:
                    print(f"  ✅ 找到法條")
                    print(f"     條號: {law.get('article_number', 'N/A')}")
                    print(f"     類型: {law.get('type', 'N/A')}")
                    print(f"     語言: {law.get('lang', 'N/A')}")
                    print(f"     章節: {law.get('chapter', 'N/A')}")
                    print(f"     內容: {law.get('content', '')[:50]}...")
                    
                    # 檢查題目
                    q_count = questions.count_documents({"law_id": law_id})
                    print(f"     關聯題目數: {q_count}")
                    
                    # 檢查統計
                    s_count = user_law_stats.count_documents({"law_id": law_id})
                    print(f"     用戶統計數: {s_count}")
                    
                else:
                    print(f"  ❌ 找不到法條")
            except Exception as e:
                print(f"  ❌ 錯誤: {e}")
        
        # 查找所有重複的法條
        print(f"\n{'='*70}")
        print(f"🔍 查找所有重複的法條")
        print(f"{'='*70}")
        
        # 按 (article_number, type, lang) 分組
        law_groups = defaultdict(list)
        
        for law in laws.find():
            key = (law.get('article_number', ''), law.get('type', 'patent-act'), law.get('lang', 'zh-TW'))
            law_groups[key].append({
                '_id': str(law['_id']),
                'article_number': law.get('article_number', 'N/A'),
                'type': law.get('type', 'patent-act'),
                'lang': law.get('lang', 'zh-TW'),
                'chapter': law.get('chapter', 'N/A'),
                'content_preview': law.get('content', '')[:30]
            })
        
        # 找出重複的
        duplicates = {k: v for k, v in law_groups.items() if len(v) > 1}
        
        if duplicates:
            print(f"⚠️  發現 {len(duplicates)} 組重複法條:")
            
            for (article_num, law_type, lang), laws_list in sorted(duplicates.items())[:10]:
                print(f"\n📄 {article_num} ({law_type}, {lang}) - {len(laws_list)} 個版本:")
                
                for i, law_info in enumerate(laws_list, 1):
                    law_id = law_info['_id']
                    
                    # 檢查每個版本的關聯數據
                    q_count = questions.count_documents({"law_id": law_id})
                    s_count = user_law_stats.count_documents({"law_id": law_id})
                    
                    print(f"  版本 {i}:")
                    print(f"    ObjectId: {law_id}")
                    print(f"    章節: {law_info['chapter']}")
                    print(f"    內容預覽: {law_info['content_preview']}...")
                    print(f"    題目數: {q_count}")
                    print(f"    統計數: {s_count}")
                    
                    if q_count > 0:
                        print(f"    ✅ 這個版本有題目關聯（正確版本）")
                    if s_count > 0:
                        print(f"    📊 這個版本有用戶統計")
            
            if len(duplicates) > 10:
                print(f"\n... 還有 {len(duplicates) - 10} 組重複")
            
            # 統計分析
            print(f"\n{'='*70}")
            print(f"📊 重複問題分析")
            print(f"{'='*70}")
            
            total_duplicate_laws = sum(len(v) for v in duplicates.values())
            extra_laws = total_duplicate_laws - len(duplicates)
            
            print(f"總重複法條數: {total_duplicate_laws}")
            print(f"多餘的法條數: {extra_laws}")
            print(f"（每組重複應該只保留 1 個，目前有 {total_duplicate_laws} 個）")
            
            # 分析哪些是應該刪除的
            laws_with_questions = []
            laws_without_questions = []
            
            for (article_num, law_type, lang), laws_list in duplicates.items():
                for law_info in laws_list:
                    law_id = law_info['_id']
                    q_count = questions.count_documents({"law_id": law_id})
                    
                    if q_count > 0:
                        laws_with_questions.append({
                            'law_id': law_id,
                            'article_number': article_num,
                            'type': law_type,
                            'q_count': q_count
                        })
                    else:
                        laws_without_questions.append({
                            'law_id': law_id,
                            'article_number': article_num,
                            'type': law_type
                        })
            
            print(f"\n有題目關聯的法條: {len(laws_with_questions)}")
            print(f"沒有題目關聯的法條: {len(laws_without_questions)}")
            
            print(f"\n{'='*70}")
            print(f"💡 推薦修復方案")
            print(f"{'='*70}")
            
            print(f"\n方案 1: 刪除沒有題目關聯的重複法條")
            print(f"  - 保留有題目關聯的版本（{len(laws_with_questions)} 個）")
            print(f"  - 刪除沒有題目關聯的版本（{len(laws_without_questions)} 個）")
            print(f"  - 更新 user_law_stats 使用正確的 law_id")
            
            print(f"\n方案 2: 使用 repair_broken_relationships.py")
            print(f"  - 從本地資料庫同步正確的 ObjectId")
            print(f"  - 刪除並重新插入所有 laws，確保 ObjectId 正確")
            print(f"  - 自動更新所有關聯數據")
            
            print(f"\n方案 3: 手動合併重複法條")
            print(f"  - 對每組重複，選擇有題目的版本作為主版本")
            print(f"  - 將其他版本的統計數據遷移到主版本")
            print(f"  - 刪除其他版本")
            
        else:
            print(f"✅ 沒有發現重複的法條")
        
        # 檢查為什麼會產生重複
        print(f"\n{'='*70}")
        print(f"🔍 可能的重複原因")
        print(f"{'='*70}")
        
        print(f"1. 多次運行初始化腳本但沒有清理舊數據")
        print(f"2. 使用不同的資料庫作為來源（MONGO_URI vs REMOTE_MONGO_URI）")
        print(f"3. laws model 更新時創建了新的 ObjectId")
        print(f"4. 同步腳本沒有正確處理 ObjectId 保留")
        
        print(f"\n{'='*70}")
        print(f"✅ 診斷完成")
        print(f"{'='*70}")
        
        return len(duplicates) == 0
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = diagnose_duplicate_laws()
    sys.exit(0 if success else 1)
