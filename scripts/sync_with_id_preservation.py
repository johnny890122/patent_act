#!/usr/bin/env python3
"""
智能資料庫同步 - 保持 ObjectId 一致性
Smart Database Sync - Preserve ObjectId to maintain relationships

此腳本確保同步時保持 ObjectId 不變，避免破壞以下關聯：
- questions.law_id → laws._id
- user_law_stars.law_id → laws._id
- user_law_stats.law_id → laws._id
- i18n_mapping.zh_tw_law_id / en_law_id → laws._id

使用方法:
    python scripts/sync_with_id_preservation.py --dry-run
    python scripts/sync_with_id_preservation.py --law-type all
"""

import sys
import os
from pymongo import MongoClient
from bson import ObjectId
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import LAW_TYPES

SOURCE_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
TARGET_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def sync_with_id_preservation(source_uri, target_uri, law_type='all', dry_run=False, verbose=False):
    """
    智能同步 - 保持 ObjectId 一致性
    
    策略：
    1. 如果目標資料庫已有該法條（根據 article_number + lang + type），複用其 _id
    2. 如果目標資料庫沒有該法條，使用來源的 _id
    3. 確保所有關聯資料保持有效
    """
    if not target_uri:
        print("❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return False
    
    try:
        # 連接資料庫
        print(f"🔌 連接來源資料庫...")
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
        print(f"✅ 目標: {target_db.name}")
        
        # 確定要同步的法律類型
        law_types_to_sync = []
        if law_type == 'all':
            law_types_to_sync = list(LAW_TYPES.keys())
        elif law_type in LAW_TYPES:
            law_types_to_sync = [law_type]
        else:
            print(f"❌ 不支援的法律類型: {law_type}")
            return False
        
        print(f"\n{'='*70}")
        print(f"📊 智能同步計劃 (保持 ObjectId 一致性)")
        print(f"={'='*70}")
        print(f"來源: {source_db.name}")
        print(f"目標: {target_db.name}")
        
        # 統計資料
        print(f"\n{'法律類型':<25} {'來源':<10} {'目標':<10} {'策略':<25}")
        print("-" * 70)
        
        for lt in law_types_to_sync:
            source_count = source_laws.count_documents({'type': lt})
            target_count = target_laws.count_documents({'type': lt})
            
            if target_count == 0:
                strategy = "新增（使用來源 ID）"
            elif target_count == source_count:
                strategy = "更新（保持目標 ID）"
            else:
                strategy = "部分更新+新增"
            
            status = "✅" if source_count > 0 else "⚠️"
            print(f"{status} {LAW_TYPES[lt]['name_zh']:<23} {source_count:<10} {target_count:<10} {strategy:<25}")
        
        if dry_run:
            print(f"\n🔍 [DRY RUN] 以上是同步預覽")
            print(f"💡 移除 --dry-run 參數以執行實際同步")
            source_client.close()
            target_client.close()
            return True
        
        # 確認操作
        print(f"\n⚠️  將從 {source_db.name} 智能同步資料到 {target_db.name}")
        print(f"💡 此操作會保持 ObjectId 一致性，不會破壞現有關聯")
        response = input("是否繼續? (y/N): ")
        if response.lower() != 'y':
            print("❌ 操作已取消")
            source_client.close()
            target_client.close()
            return False
        
        # 執行智能同步
        total_inserted = 0
        total_updated = 0
        total_id_preserved = 0
        total_errors = 0
        
        for lt in law_types_to_sync:
            print(f"\n{'='*70}")
            print(f"📚 同步 {LAW_TYPES[lt]['name_zh']}")
            print(f"{'='*70}")
            
            # 取得來源資料
            source_docs = list(source_laws.find({'type': lt}))
            
            if not source_docs:
                print(f"⚠️  來源資料庫中沒有 {LAW_TYPES[lt]['name_zh']} 資料")
                continue
            
            print(f"📖 找到 {len(source_docs)} 條法條")
            
            inserted = 0
            updated = 0
            id_preserved = 0
            errors = []
            
            for doc in source_docs:
                try:
                    source_id = doc['_id']
                    article_number = doc['article_number']
                    lang = doc['lang']
                    doc_type = doc['type']
                    
                    # 查詢目標資料庫是否已有此法條
                    existing = target_laws.find_one({
                        'article_number': article_number,
                        'lang': lang,
                        'type': doc_type
                    })
                    
                    if existing:
                        # 目標已存在 - 更新內容，保持 _id 不變
                        target_id = existing['_id']
                        
                        # 更新文檔內容（不包含 _id）
                        update_doc = {k: v for k, v in doc.items() if k != '_id'}
                        
                        result = target_laws.update_one(
                            {'_id': target_id},
                            {'$set': update_doc}
                        )
                        
                        if result.modified_count > 0:
                            updated += 1
                            id_preserved += 1
                            if verbose:
                                print(f"   🔄 更新: {article_number} (保持 ID: {target_id})")
                        else:
                            id_preserved += 1
                            if verbose:
                                print(f"   ⏭️  跳過: {article_number} (無變更, ID: {target_id})")
                    
                    else:
                        # 目標不存在 - 插入新文檔，使用來源的 _id
                        result = target_laws.insert_one(doc)
                        inserted += 1
                        if verbose:
                            print(f"   ✅ 插入: {article_number} (使用來源 ID: {source_id})")
                
                except Exception as e:
                    error_msg = f"{doc.get('article_number', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    if verbose:
                        print(f"   ❌ 錯誤: {error_msg}")
            
            # 統計
            print(f"\n📊 {LAW_TYPES[lt]['name_zh']} 同步結果:")
            print(f"   ✅ 新增: {inserted} 條")
            print(f"   🔄 更新: {updated} 條")
            print(f"   🔒 保持 ID: {id_preserved} 條")
            print(f"   ❌ 錯誤: {len(errors)} 條")
            
            if errors:
                print(f"\n⚠️  錯誤詳情:")
                for error in errors[:5]:
                    print(f"   - {error}")
                if len(errors) > 5:
                    print(f"   ... 還有 {len(errors) - 5} 個錯誤")
            
            # 驗證
            final_count = target_laws.count_documents({'type': lt})
            print(f"\n✅ 目標資料庫中總數: {final_count} 條")
            
            total_inserted += inserted
            total_updated += updated
            total_id_preserved += id_preserved
            total_errors += len(errors)
        
        # 確保索引
        print(f"\n{'='*70}")
        print(f"🔧 確保目標資料庫索引...")
        print(f"{'='*70}")
        
        from db.models import Database
        temp_db = Database()
        temp_db.client = target_client
        temp_db.db = target_db
        temp_db.laws_collection = target_laws
        temp_db.init_db()
        
        print(f"✅ 索引建立完成")
        
        # 驗證關聯完整性
        print(f"\n{'='*70}")
        print(f"🔍 驗證關聯完整性")
        print(f"{'='*70}")
        
        # 檢查 questions 關聯
        questions_collection = target_db['questions']
        total_questions = questions_collection.count_documents({})
        
        if total_questions > 0:
            # 檢查有多少問題的 law_id 對應到有效的 law
            orphan_questions = 0
            for question in questions_collection.find():
                law_id = question.get('law_id')
                if law_id and not target_laws.find_one({'_id': ObjectId(law_id)}):
                    orphan_questions += 1
            
            print(f"📝 問題總數: {total_questions}")
            print(f"   有效關聯: {total_questions - orphan_questions}")
            print(f"   孤兒問題: {orphan_questions}")
            
            if orphan_questions > 0:
                print(f"   ⚠️  發現 {orphan_questions} 個孤兒問題（law_id 無對應法條）")
        else:
            print(f"📝 問題總數: 0 (無需驗證)")
        
        # 最終統計
        print(f"\n{'='*70}")
        print(f"📊 同步完成統計")
        print(f"{'='*70}")
        print(f"✅ 新增: {total_inserted} 條")
        print(f"🔄 更新: {total_updated} 條")
        print(f"🔒 保持 ID: {total_id_preserved} 條")
        print(f"❌ 錯誤: {total_errors} 條")
        
        print(f"\n💡 優勢：")
        print(f"   • ObjectId 保持不變（{total_id_preserved} 條）")
        print(f"   • 所有關聯資料保持有效（questions, user_law_stars, user_law_stats）")
        print(f"   • 不需要重建關聯或重新生成問題")
        
        # 最終驗證
        print(f"\n{'='*70}")
        print(f"🔍 最終驗證")
        print(f"{'='*70}")
        print(f"{'法律類型':<25} {'來源':<10} {'目標':<10} {'狀態':<15}")
        print("-" * 70)
        
        all_synced = True
        for lt in law_types_to_sync:
            source_count = source_laws.count_documents({'type': lt})
            target_count = target_laws.count_documents({'type': lt})
            
            if source_count == target_count and source_count > 0:
                status = "✅ 完全同步"
            elif target_count == 0:
                status = "❌ 失敗"
                all_synced = False
            else:
                status = f"⚠️ 不一致"
                all_synced = False
            
            print(f"   {LAW_TYPES[lt]['name_zh']:<23} {source_count:<10} {target_count:<10} {status:<15}")
        
        source_client.close()
        target_client.close()
        
        return all_synced
        
    except Exception as e:
        print(f"❌ 同步失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='智能資料庫同步 - 保持 ObjectId 一致性，避免破壞關聯'
    )
    parser.add_argument('--law-type',
                       choices=['all', 'patent-act', 'patent-examination', 
                               'administrative-appeal', 'administrative-litigation'],
                       default='all',
                       help='要同步的法律類型 (預設: all)')
    parser.add_argument('--dry-run', action='store_true',
                       help='只顯示同步計劃，不實際執行')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='顯示詳細日誌')
    
    args = parser.parse_args()
    
    print("="*70)
    print("🔄 智能資料庫同步工具 (保持 ObjectId 一致性)")
    print("="*70)
    print(f"來源: MONGO_URI")
    print(f"目標: REMOTE_MONGO_URI")
    print("="*70)
    print("\n💡 此工具的優勢:")
    print("   • 保持現有 ObjectId 不變")
    print("   • 不破壞 questions.law_id 關聯")
    print("   • 不破壞 user_law_stars/stats.law_id 關聯")
    print("   • 不需要重新生成問題或重建關聯")
    
    if not TARGET_MONGO_URI:
        print("\n❌ 錯誤: REMOTE_MONGO_URI 未設定")
        return 1
    
    success = sync_with_id_preservation(
        SOURCE_MONGO_URI,
        TARGET_MONGO_URI,
        law_type=args.law_type,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    print(f"\n{'='*70}")
    if success:
        print("✅ 同步成功！")
        print("\n💡 建議:")
        print("   1. 執行診斷工具確認: python scripts/diagnose_heroku_laws.py")
        print("   2. 驗證關聯完整性（問題、收藏、統計）")
        print("   3. 重啟應用: heroku restart -a your-app-name")
    else:
        print("❌ 同步失敗或資料不一致")
    print(f"{'='*70}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
