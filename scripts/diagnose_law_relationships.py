#!/usr/bin/env python3
"""
診斷法條關聯問題
檢查 laws, questions, user_law_stats 之間的關聯是否正確
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

def diagnose_relationships():
    """診斷關聯問題"""
    if not REMOTE_MONGO_URI:
        print("❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return False
    
    try:
        print("="*70)
        print("🔍 法條關聯診斷工具")
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
        
        # 統計法條
        print(f"\n{'='*70}")
        print(f"📊 法條統計")
        print(f"{'='*70}")
        
        law_types = defaultdict(int)
        law_ids = set()
        for law in laws.find():
            law_types[law.get('type', 'patent-act')] += 1
            law_ids.add(str(law['_id']))
        
        print(f"總法條數: {len(law_ids)}")
        for law_type, count in law_types.items():
            print(f"  {law_type}: {count} 條")
        
        # 統計題目
        print(f"\n{'='*70}")
        print(f"📝 題目統計")
        print(f"{'='*70}")
        
        total_questions = questions.count_documents({})
        print(f"總題目數: {total_questions}")
        
        # 檢查題目的 law_id 是否存在
        orphan_questions = []
        question_law_ids = set()
        
        for q in questions.find():
            law_id = str(q.get('law_id', ''))
            question_law_ids.add(law_id)
            if law_id not in law_ids:
                orphan_questions.append({
                    'question_id': str(q['_id']),
                    'law_id': law_id,
                    'content': q.get('content', '')[:50]
                })
        
        print(f"題目引用的 law_id 數: {len(question_law_ids)}")
        
        if orphan_questions:
            print(f"\n⚠️  發現 {len(orphan_questions)} 個孤兒題目（law_id 不存在）:")
            for i, q in enumerate(orphan_questions[:5], 1):
                print(f"  {i}. question_id: {q['question_id']}")
                print(f"     law_id: {q['law_id']}")
                print(f"     content: {q['content']}...")
            if len(orphan_questions) > 5:
                print(f"  ... 還有 {len(orphan_questions) - 5} 個")
        else:
            print(f"✅ 所有題目的 law_id 都有效")
        
        # 統計每個法條的題目數
        print(f"\n{'='*70}")
        print(f"📈 每個法條的題目數統計")
        print(f"{'='*70}")
        
        laws_with_questions = defaultdict(int)
        for q in questions.find():
            law_id = str(q.get('law_id', ''))
            if law_id in law_ids:
                laws_with_questions[law_id] += 1
        
        laws_without_questions = len(law_ids) - len(laws_with_questions)
        print(f"有題目的法條: {len(laws_with_questions)}")
        print(f"沒有題目的法條: {laws_without_questions}")
        
        # 顯示前 5 個有最多題目的法條
        top_laws = sorted(laws_with_questions.items(), key=lambda x: x[1], reverse=True)[:5]
        print(f"\n題目最多的法條:")
        for law_id, count in top_laws:
            law = laws.find_one({'_id': ObjectId(law_id)})
            if law:
                print(f"  {law.get('article_number', 'N/A')} ({law.get('type', 'patent-act')}): {count} 題")
        
        # 檢查 user_law_stats
        print(f"\n{'='*70}")
        print(f"📊 用戶法條統計 (user_law_stats)")
        print(f"{'='*70}")
        
        total_stats = user_law_stats.count_documents({})
        print(f"總統計記錄數: {total_stats}")
        
        # 檢查 user_law_stats 的 law_id 是否存在
        orphan_stats = []
        stats_law_ids = set()
        
        for stat in user_law_stats.find():
            law_id = str(stat.get('law_id', ''))
            stats_law_ids.add(law_id)
            if law_id not in law_ids:
                orphan_stats.append({
                    'user_id': stat.get('user_id', 'N/A'),
                    'law_id': law_id,
                    'avg_score': stat.get('avg_score', 0)
                })
        
        print(f"統計引用的 law_id 數: {len(stats_law_ids)}")
        
        if orphan_stats:
            print(f"\n⚠️  發現 {len(orphan_stats)} 個孤兒統計（law_id 不存在）:")
            for i, s in enumerate(orphan_stats[:5], 1):
                print(f"  {i}. user_id: {s['user_id']}")
                print(f"     law_id: {s['law_id']}")
                print(f"     avg_score: {s['avg_score']}")
            if len(orphan_stats) > 5:
                print(f"  ... 還有 {len(orphan_stats) - 5} 個")
        else:
            print(f"✅ 所有統計的 law_id 都有效")
        
        # 交叉檢查：有統計但沒有題目的法條
        print(f"\n{'='*70}")
        print(f"🔄 交叉檢查")
        print(f"{'='*70}")
        
        stats_without_questions = []
        for law_id in stats_law_ids:
            if law_id in law_ids and law_id not in laws_with_questions:
                law = laws.find_one({'_id': ObjectId(law_id)})
                if law:
                    stats_without_questions.append({
                        'law_id': law_id,
                        'article_number': law.get('article_number', 'N/A'),
                        'type': law.get('type', 'patent-act')
                    })
        
        if stats_without_questions:
            print(f"⚠️  發現 {len(stats_without_questions)} 個法條有統計但沒有題目:")
            for i, law_info in enumerate(stats_without_questions[:10], 1):
                print(f"  {i}. {law_info['article_number']} ({law_info['type']})")
                print(f"     law_id: {law_info['law_id']}")
            if len(stats_without_questions) > 10:
                print(f"  ... 還有 {len(stats_without_questions) - 10} 個")
        else:
            print(f"✅ 所有有統計的法條都有題目")
        
        # 總結
        print(f"\n{'='*70}")
        print(f"📋 診斷總結")
        print(f"{'='*70}")
        
        issues = []
        if orphan_questions:
            issues.append(f"❌ {len(orphan_questions)} 個題目的 law_id 無效")
        if orphan_stats:
            issues.append(f"❌ {len(orphan_stats)} 個統計的 law_id 無效")
        if stats_without_questions:
            issues.append(f"⚠️  {len(stats_without_questions)} 個法條有統計但沒有題目")
        
        if issues:
            print("發現以下問題:")
            for issue in issues:
                print(f"  {issue}")
            print(f"\n💡 建議:")
            if orphan_questions or orphan_stats:
                print("  使用 repair_broken_relationships.py 修復 ObjectId 關聯")
        else:
            print("✅ 沒有發現關聯問題，資料完整性良好")
        
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
    success = diagnose_relationships()
    sys.exit(0 if success else 1)
