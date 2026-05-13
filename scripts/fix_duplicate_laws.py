#!/usr/bin/env python3
"""
修復重複法條問題
保留有題目關聯的版本，刪除沒有題目關聯的重複版本
補全缺少的 type 欄位
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId
from collections import defaultdict
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

def fix_duplicate_laws(dry_run=True):
    """修復重複法條"""
    if not REMOTE_MONGO_URI:
        print("❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return False
    
    try:
        print("="*70)
        print("🔧 重複法條修復工具")
        print("="*70)
        
        if dry_run:
            print("\n⚠️  DRY RUN 模式 - 不會實際修改資料庫")
            print("使用 --confirm 參數來執行實際修復\n")
        else:
            print("\n🚨 即將修改遠端資料庫！\n")
        
        # 連接資料庫
        print(f"🔌 連接遠端資料庫...")
        client = MongoClient(REMOTE_MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        db = client.get_database()
        print(f"✅ 資料庫: {db.name}")
        
        laws = db['laws']
        questions = db['questions']
        user_law_stats = db['user_law_stats']
        
        # 步驟 1: 找出所有重複的法條
        print(f"\n{'='*70}")
        print(f"步驟 1: 分析重複法條")
        print(f"{'='*70}")
        
        law_groups = defaultdict(list)
        
        for law in laws.find():
            # 處理缺少 type 欄位的舊資料
            law_type = law.get('type', 'patent-act')
            key = (law.get('article_number', ''), law_type, law.get('lang', 'zh-TW'))
            law_groups[key].append({
                '_id': law['_id'],
                'law_id_str': str(law['_id']),
                'article_number': law.get('article_number', ''),
                'type': law_type,
                'has_type_field': 'type' in law,
                'lang': law.get('lang', 'zh-TW'),
                'chapter': law.get('chapter', ''),
                'content': law.get('content', '')
            })
        
        duplicates = {k: v for k, v in law_groups.items() if len(v) > 1}
        
        print(f"總法條數: {laws.count_documents({})}")
        print(f"重複組數: {len(duplicates)}")
        print(f"重複法條數: {sum(len(v) for v in duplicates.values())}")
        print(f"多餘法條數: {sum(len(v) - 1 for v in duplicates.values())}")
        
        # 步驟 2: 決定每組保留哪個版本
        print(f"\n{'='*70}")
        print(f"步驟 2: 決定保留版本")
        print(f"{'='*70}")
        
        laws_to_keep = []
        laws_to_delete = []
        laws_to_update = []  # 需要補上 type 欄位的法條
        
        for (article_num, law_type, lang), laws_list in duplicates.items():
            # 為每個版本統計題目數
            versions_with_stats = []
            for law_info in laws_list:
                law_id = law_info['law_id_str']
                q_count = questions.count_documents({"law_id": law_id})
                s_count = user_law_stats.count_documents({"law_id": law_id})
                
                versions_with_stats.append({
                    **law_info,
                    'question_count': q_count,
                    'stats_count': s_count
                })
            
            # 排序：優先保留有題目的，其次有統計的，最後保留缺少 type 欄位的（舊版本）
            versions_with_stats.sort(
                key=lambda x: (x['question_count'], x['stats_count'], not x['has_type_field']),
                reverse=True
            )
            
            # 保留第一個（有最多關聯的）
            keep = versions_with_stats[0]
            delete = versions_with_stats[1:]
            
            laws_to_keep.append(keep)
            
            # 如果保留的版本缺少 type 欄位，需要補上
            if not keep['has_type_field']:
                laws_to_update.append(keep)
            
            for law_info in delete:
                laws_to_delete.append(law_info)
        
        print(f"保留法條數: {len(laws_to_keep)}")
        print(f"刪除法條數: {len(laws_to_delete)}")
        print(f"需要補 type 欄位: {len(laws_to_update)}")
        
        # 顯示一些例子
        print(f"\n保留版本範例（前 5 個）:")
        for law_info in laws_to_keep[:5]:
            print(f"  {law_info['article_number']} ({law_info['type']}, {law_info['lang']})")
            print(f"    ObjectId: {law_info['law_id_str']}")
            print(f"    題目數: {law_info['question_count']}, 統計數: {law_info['stats_count']}")
            print(f"    有 type 欄位: {law_info['has_type_field']}")
        
        print(f"\n刪除版本範例（前 5 個）:")
        for law_info in laws_to_delete[:5]:
            print(f"  {law_info['article_number']} ({law_info['type']}, {law_info['lang']})")
            print(f"    ObjectId: {law_info['law_id_str']}")
            print(f"    題目數: {law_info['question_count']}, 統計數: {law_info['stats_count']}")
        
        # 步驟 3: 遷移統計數據（如果刪除的版本有統計）
        print(f"\n{'='*70}")
        print(f"步驟 3: 檢查需要遷移的統計數據")
        print(f"{'='*70}")
        
        stats_to_migrate = []
        for law_info in laws_to_delete:
            if law_info['stats_count'] > 0:
                # 找到對應的保留版本
                key = (law_info['article_number'], law_info['type'], law_info['lang'])
                keep_version = next((l for l in laws_to_keep 
                                   if l['article_number'] == law_info['article_number'] 
                                   and l['type'] == law_info['type']
                                   and l['lang'] == law_info['lang']), None)
                
                if keep_version:
                    stats_to_migrate.append({
                        'from_law_id': law_info['law_id_str'],
                        'to_law_id': keep_version['law_id_str'],
                        'article_number': law_info['article_number'],
                        'type': law_info['type']
                    })
        
        print(f"需要遷移統計的法條數: {len(stats_to_migrate)}")
        
        if stats_to_migrate:
            print(f"\n遷移範例（前 5 個）:")
            for migrate_info in stats_to_migrate[:5]:
                print(f"  {migrate_info['article_number']} ({migrate_info['type']})")
                print(f"    從: {migrate_info['from_law_id']}")
                print(f"    到: {migrate_info['to_law_id']}")
        
        # 步驟 4: 執行修復（如果不是 dry run）
        if not dry_run:
            print(f"\n{'='*70}")
            print(f"步驟 4: 執行修復")
            print(f"{'='*70}")
            
            # 4.1 遷移統計數據（如果需要）
            if stats_to_migrate:
                print(f"\n遷移統計數據...")
                migrated_count = 0
                for migrate_info in stats_to_migrate:
                    result = user_law_stats.update_many(
                        {"law_id": migrate_info['from_law_id']},
                        {"$set": {"law_id": migrate_info['to_law_id']}}
                    )
                    migrated_count += result.modified_count
                print(f"✅ 已遷移 {migrated_count} 條統計記錄")
            
            # 4.2 刪除重複的法條（必須在補 type 欄位之前執行，避免唯一索引衝突）
            print(f"\n刪除重複法條...")
            delete_ids = [law_info['_id'] for law_info in laws_to_delete]
            result = laws.delete_many({"_id": {"$in": delete_ids}})
            print(f"✅ 已刪除 {result.deleted_count} 個重複法條")
            
            # 4.3 補上缺少的 type 欄位（必須在刪除重複法條之後執行）
            if laws_to_update:
                print(f"\n補上 type 欄位...")
                for law_info in laws_to_update:
                    laws.update_one(
                        {"_id": law_info['_id']},
                        {"$set": {"type": law_info['type']}}
                    )
                print(f"✅ 已更新 {len(laws_to_update)} 個法條的 type 欄位")
            
            print(f"\n{'='*70}")
            print(f"✅ 修復完成")
            print(f"{'='*70}")
            
            # 驗證結果
            print(f"\n驗證結果:")
            final_law_count = laws.count_documents({})
            print(f"  最終法條數: {final_law_count}")
            
            # 檢查是否還有重複
            final_law_groups = defaultdict(int)
            for law in laws.find():
                law_type = law.get('type', 'patent-act')
                key = (law.get('article_number', ''), law_type, law.get('lang', 'zh-TW'))
                final_law_groups[key] += 1
            
            final_duplicates = {k: v for k, v in final_law_groups.items() if v > 1}
            if final_duplicates:
                print(f"  ⚠️  仍有 {len(final_duplicates)} 組重複")
            else:
                print(f"  ✅ 沒有重複法條")
        else:
            print(f"\n{'='*70}")
            print(f"📋 DRY RUN 總結")
            print(f"{'='*70}")
            print(f"如果執行實際修復，將會:")
            print(f"  1. 補上 {len(laws_to_update)} 個法條的 type 欄位")
            print(f"  2. 遷移 {len(stats_to_migrate)} 個法條的統計數據")
            print(f"  3. 刪除 {len(laws_to_delete)} 個重複法條")
            print(f"\n要執行實際修復，請運行:")
            print(f"  python scripts/fix_duplicate_laws.py --confirm")
        
        return True
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='修復重複法條問題')
    parser.add_argument('--confirm', action='store_true', help='確認執行修復（不加此參數為 dry-run 模式）')
    
    args = parser.parse_args()
    
    success = fix_duplicate_laws(dry_run=not args.confirm)
    sys.exit(0 if success else 1)
