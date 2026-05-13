#!/usr/bin/env python3
"""
修復已破壞的 ObjectId 關聯
Repair broken ObjectId relationships

當 law 的 ObjectId 已經改變，導致所有關聯失效時使用此工具。

此工具會：
1. 使用來源資料庫（MONGO_URI/localdb）的 ObjectId 作為標準
2. 替換目標資料庫（REMOTE_MONGO_URI/patent-act）中的 law ObjectId
3. 更新所有關聯資料中的 law_id

使用方法:
    python scripts/repair_broken_relationships.py --dry-run
    python scripts/repair_broken_relationships.py --confirm
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId
import argparse
from collections import defaultdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import LAW_TYPES

SOURCE_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
TARGET_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def repair_relationships(source_uri, target_uri, dry_run=True, verbose=False):
    """
    修復破壞的 ObjectId 關聯
    
    策略：
    1. 建立 article_number+lang+type 到正確 ObjectId 的映射（從來源）
    2. 在目標資料庫中，找到每個 law 的舊 ObjectId
    3. 刪除舊 law，用正確的 ObjectId 重新插入
    4. 建立 舊ID -> 新ID 的映射
    5. 更新所有關聯資料的 law_id
    """
    if not target_uri:
        print("❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return False
    
    try:
        # 連接資料庫
        print("="*70)
        print("🔧 破壞關聯修復工具")
        print("="*70)
        
        print(f"\n🔌 連接來源資料庫...")
        source_client = MongoClient(source_uri, serverSelectionTimeoutMS=5000)
        source_client.admin.command('ping')
        source_db = source_client.get_database()
        source_laws = source_db['laws']
        print(f"✅ 來源: {source_db.name}")
        
        print(f"🔌 連接目標資料庫...")
        target_client = MongoClient(target_uri, serverSelectionTimeoutMS=5000)
        target_client.admin.command('ping')
        target_db = target_client.get_database()
        target_laws = target_db['laws']
        target_questions = target_db['questions']
        target_user_law_stars = target_db['user_law_stars']
        target_user_law_stats = target_db['user_law_stats']
        target_i18n_mapping = target_db['i18n_mapping']
        print(f"✅ 目標: {target_db.name}")
        
        # 步驟 1: 建立來源的標準映射
        print(f"\n{'='*70}")
        print(f"📊 步驟 1/5: 分析來源資料庫")
        print(f"{'='*70}")
        
        source_mapping = {}  # (article_number, lang, type) -> ObjectId
        for law in source_laws.find():
            key = (law['article_number'], law['lang'], law['type'])
            source_mapping[key] = law['_id']
        
        print(f"✅ 找到 {len(source_mapping)} 個標準法條 ObjectId")
        
        # 步驟 2: 找到目標資料庫中的舊 ObjectId
        print(f"\n{'='*70}")
        print(f"📊 步驟 2/5: 分析目標資料庫並建立 ID 映射")
        print(f"{'='*70}")
        
        old_to_new_mapping = {}  # 舊 ObjectId (str) -> 新 ObjectId (ObjectId)
        laws_to_fix = []
        skipped_no_type = 0
        
        for target_law in target_laws.find():
            # 處理缺少 type 欄位的舊資料
            if 'type' not in target_law:
                # 預設為 patent-act（舊資料的預設值）
                target_law['type'] = 'patent-act'
                skipped_no_type += 1
            
            # 處理缺少 lang 欄位的舊資料
            if 'lang' not in target_law:
                target_law['lang'] = 'zh-TW'
            
            key = (target_law['article_number'], target_law['lang'], target_law['type'])
            
            if key in source_mapping:
                correct_id = source_mapping[key]
                current_id = target_law['_id']
                
                if correct_id != current_id:
                    # ID 不一致，需要修復
                    old_to_new_mapping[str(current_id)] = correct_id
                    laws_to_fix.append({
                        'old_id': current_id,
                        'correct_id': correct_id,
                        'article_number': target_law['article_number'],
                        'lang': target_law['lang'],
                        'type': target_law['type'],
                        'doc': target_law
                    })
        
        if skipped_no_type > 0:
            print(f"⚠️  發現 {skipped_no_type} 個舊法條缺少 type 欄位，已設為 patent-act")
        
        print(f"⚠️  發現 {len(laws_to_fix)} 個法條的 ObjectId 不正確")
        print(f"✅ 建立了 {len(old_to_new_mapping)} 個 ID 映射")
        
        if verbose and laws_to_fix:
            print(f"\n前 5 個需要修復的法條:")
            for i, law in enumerate(laws_to_fix[:5], 1):
                print(f"   {i}. {law['article_number']} ({law['type']})")
                print(f"      舊 ID: {law['old_id']}")
                print(f"      正確 ID: {law['correct_id']}")
        
        # 步驟 3: 分析受影響的關聯資料
        print(f"\n{'='*70}")
        print(f"📊 步驟 3/5: 分析受影響的關聯資料")
        print(f"{'='*70}")
        
        affected_questions = 0
        affected_stars = 0
        affected_stats = 0
        affected_i18n = 0
        
        for old_id_str in old_to_new_mapping.keys():
            affected_questions += target_questions.count_documents({'law_id': old_id_str})
            affected_stars += target_user_law_stars.count_documents({'law_id': old_id_str})
            affected_stats += target_user_law_stats.count_documents({'law_id': old_id_str})
            affected_i18n += target_i18n_mapping.count_documents({
                '$or': [
                    {'zh_tw_law_id': old_id_str},
                    {'en_law_id': old_id_str}
                ]
            })
        
        print(f"📝 受影響的問題: {affected_questions} 個")
        print(f"⭐ 受影響的收藏: {affected_stars} 個")
        print(f"📊 受影響的統計: {affected_stats} 個")
        print(f"🌐 受影響的 i18n 映射: {affected_i18n} 個")
        
        total_affected = affected_questions + affected_stars + affected_stats + affected_i18n
        print(f"\n⚠️  總共 {total_affected} 筆關聯資料將被更新")
        
        if dry_run:
            print(f"\n{'='*70}")
            print(f"🔍 [DRY RUN] 這是預覽模式")
            print(f"{'='*70}")
            print(f"\n將執行的操作:")
            print(f"1. 修復 {len(laws_to_fix)} 個法條的 ObjectId")
            print(f"2. 更新 {affected_questions} 個問題的 law_id")
            print(f"3. 更新 {affected_stars} 個收藏的 law_id")
            print(f"4. 更新 {affected_stats} 個統計的 law_id")
            print(f"5. 更新 {affected_i18n} 個 i18n 映射的 law_id")
            print(f"\n💡 移除 --dry-run 並加上 --confirm 參數以執行實際修復")
            
            source_client.close()
            target_client.close()
            return True
        
        # 確認操作
        print(f"\n{'='*70}")
        print(f"⚠️  警告：即將執行破壞性操作")
        print(f"{'='*70}")
        print(f"此操作將:")
        print(f"1. 刪除並重新插入 {len(laws_to_fix)} 個法條（使用正確的 ObjectId）")
        print(f"2. 更新 {total_affected} 筆關聯資料")
        print(f"\n建議在生產環境前先備份資料庫！")
        
        response = input("\n是否繼續? 請輸入 'YES' 確認: ")
        if response != 'YES':
            print("❌ 操作已取消")
            source_client.close()
            target_client.close()
            return False
        
        # 步驟 4: 修復 law 的 ObjectId
        print(f"\n{'='*70}")
        print(f"🔧 步驟 4/5: 修復法條 ObjectId")
        print(f"{'='*70}")
        
        fixed_laws = 0
        for law_info in laws_to_fix:
            try:
                # 刪除舊的
                target_laws.delete_one({'_id': law_info['old_id']})
                
                # 準備新文檔（使用正確的 _id）
                new_doc = law_info['doc'].copy()
                new_doc['_id'] = law_info['correct_id']
                
                # 確保必要欄位存在（修復舊資料）
                if 'type' not in new_doc:
                    new_doc['type'] = law_info['type']
                if 'lang' not in new_doc:
                    new_doc['lang'] = law_info['lang']
                if 'article_number_int' not in new_doc:
                    # 嘗試從 article_number 中提取數字
                    import re
                    match = re.search(r'(\d+)', new_doc.get('article_number', ''))
                    new_doc['article_number_int'] = int(match.group(1)) if match else 0
                
                # 插入新的
                target_laws.insert_one(new_doc)
                
                fixed_laws += 1
                if verbose:
                    print(f"   ✅ {law_info['article_number']}: {law_info['old_id']} → {law_info['correct_id']}")
            
            except Exception as e:
                print(f"   ❌ 修復 {law_info['article_number']} 失敗: {e}")
        
        print(f"\n✅ 成功修復 {fixed_laws} 個法條的 ObjectId")
        
        # 步驟 5: 更新所有關聯資料
        print(f"\n{'='*70}")
        print(f"🔧 步驟 5/5: 更新關聯資料")
        print(f"{'='*70}")
        
        updated_questions = 0
        updated_stars = 0
        updated_stats = 0
        updated_i18n = 0
        
        for old_id_str, new_id in old_to_new_mapping.items():
            new_id_str = str(new_id)
            
            # 更新問題
            result = target_questions.update_many(
                {'law_id': old_id_str},
                {'$set': {'law_id': new_id_str}}
            )
            updated_questions += result.modified_count
            
            # 更新收藏
            result = target_user_law_stars.update_many(
                {'law_id': old_id_str},
                {'$set': {'law_id': new_id_str}}
            )
            updated_stars += result.modified_count
            
            # 更新統計
            result = target_user_law_stats.update_many(
                {'law_id': old_id_str},
                {'$set': {'law_id': new_id_str}}
            )
            updated_stats += result.modified_count
            
            # 更新 i18n 映射（兩個欄位）
            result = target_i18n_mapping.update_many(
                {'zh_tw_law_id': old_id_str},
                {'$set': {'zh_tw_law_id': new_id_str}}
            )
            updated_i18n += result.modified_count
            
            result = target_i18n_mapping.update_many(
                {'en_law_id': old_id_str},
                {'$set': {'en_law_id': new_id_str}}
            )
            updated_i18n += result.modified_count
        
        print(f"📝 更新問題: {updated_questions} 個")
        print(f"⭐ 更新收藏: {updated_stars} 個")
        print(f"📊 更新統計: {updated_stats} 個")
        print(f"🌐 更新 i18n 映射: {updated_i18n} 個")
        
        # 最終驗證
        print(f"\n{'='*70}")
        print(f"🔍 最終驗證")
        print(f"{'='*70}")
        
        # 檢查孤兒關聯
        orphan_questions = 0
        for question in target_questions.find():
            law_id = question.get('law_id')
            if law_id and not target_laws.find_one({'_id': ObjectId(law_id)}):
                orphan_questions += 1
        
        orphan_stars = 0
        for star in target_user_law_stars.find():
            law_id = star.get('law_id')
            if law_id and not target_laws.find_one({'_id': ObjectId(law_id)}):
                orphan_stars += 1
        
        orphan_stats = 0
        for stat in target_user_law_stats.find():
            law_id = stat.get('law_id')
            if law_id and not target_laws.find_one({'_id': ObjectId(law_id)}):
                orphan_stats += 1
        
        print(f"📝 孤兒問題: {orphan_questions} 個")
        print(f"⭐ 孤兒收藏: {orphan_stars} 個")
        print(f"📊 孤兒統計: {orphan_stats} 個")
        
        if orphan_questions == 0 and orphan_stars == 0 and orphan_stats == 0:
            print(f"\n✅ 所有關聯都已正確修復！")
            success = True
        else:
            print(f"\n⚠️  仍有孤兒關聯存在，可能需要進一步檢查")
            success = False
        
        source_client.close()
        target_client.close()
        
        return success
        
    except Exception as e:
        print(f"❌ 修復失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='修復已破壞的 ObjectId 關聯'
    )
    parser.add_argument('--dry-run', action='store_true',
                       help='預覽模式，不實際執行（預設）')
    parser.add_argument('--confirm', action='store_true',
                       help='執行實際修復（需要明確指定）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='顯示詳細日誌')
    
    args = parser.parse_args()
    
    # 預設是 dry-run，除非明確指定 --confirm
    dry_run = not args.confirm
    
    print("="*70)
    print("🔧 破壞關聯修復工具")
    print("="*70)
    print(f"來源: MONGO_URI (標準 ObjectId)")
    print(f"目標: REMOTE_MONGO_URI (要修復的資料庫)")
    print("="*70)
    
    if not TARGET_MONGO_URI:
        print("\n❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return 1
    
    if dry_run:
        print("\n🔍 [預覽模式] 將顯示要執行的操作，不會實際修改資料")
        print("💡 使用 --confirm 參數執行實際修復")
    else:
        print("\n⚠️  [執行模式] 將執行實際修復操作")
        print("⚠️  警告：此操作會修改目標資料庫")
    
    success = repair_relationships(
        SOURCE_MONGO_URI,
        TARGET_MONGO_URI,
        dry_run=dry_run,
        verbose=args.verbose
    )
    
    print(f"\n{'='*70}")
    if success:
        if dry_run:
            print("✅ 預覽完成")
            print("\n下一步:")
            print("   python scripts/repair_broken_relationships.py --confirm")
        else:
            print("✅ 修復完成！")
            print("\n建議:")
            print("   1. 執行診斷工具: python scripts/diagnose_heroku_laws.py")
            print("   2. 測試應用程式功能")
            print("   3. 重啟應用: heroku restart -a your-app-name")
    else:
        print("❌ 修復失敗或仍有問題")
    print(f"{'='*70}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
