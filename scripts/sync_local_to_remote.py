#!/usr/bin/env python3
"""
從本地/生產資料庫同步到遠端資料庫
Sync data from MONGO_URI (localdb) to REMOTE_MONGO_URI (patent-act)

使用方法:
    python scripts/sync_local_to_remote.py --law-type all
    python scripts/sync_local_to_remote.py --law-type administrative-appeal
    python scripts/sync_local_to_remote.py --dry-run
"""

import sys
import os
from pymongo import MongoClient
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import LAW_TYPES

# 來源資料庫 (完整資料)
SOURCE_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')

# 目標資料庫 (需要同步)
TARGET_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def sync_laws(source_uri, target_uri, law_type='all', dry_run=False, verbose=False):
    """
    同步法條資料
    
    Args:
        source_uri: 來源資料庫 URI
        target_uri: 目標資料庫 URI
        law_type: 法律類型 ('all' 或特定類型)
        dry_run: 只顯示要同步的資料，不實際寫入
        verbose: 顯示詳細日誌
        
    Returns:
        bool: 是否成功
    """
    if not target_uri:
        print("❌ 錯誤: REMOTE_MONGO_URI 未設定")
        print("\n請在 .env 檔案中設定:")
        print("  REMOTE_MONGO_URI=mongodb+srv://...")
        return False
    
    try:
        # 連接來源資料庫
        print(f"🔌 連接來源資料庫...")
        source_client = MongoClient(source_uri, serverSelectionTimeoutMS=5000)
        source_client.admin.command('ping')
        source_db = source_client.get_database()
        source_laws = source_db['laws']
        print(f"✅ 來源: {source_db.name}")
        
        # 連接目標資料庫
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
        
        print(f"\n{'='*60}")
        print(f"📊 同步計劃")
        print(f"{'='*60}")
        print(f"來源: {source_db.name}")
        print(f"目標: {target_db.name}")
        print(f"法律類型: {', '.join([LAW_TYPES[t]['name_zh'] for t in law_types_to_sync])}")
        
        # 統計資料
        total_source = 0
        total_target = 0
        
        print(f"\n{'法律類型':<25} {'來源':<10} {'目標':<10} {'需同步':<10}")
        print("-" * 60)
        
        for lt in law_types_to_sync:
            source_count = source_laws.count_documents({'type': lt})
            target_count = target_laws.count_documents({'type': lt})
            to_sync = source_count - target_count
            
            total_source += source_count
            total_target += target_count
            
            status = "✅" if source_count > 0 else "⚠️"
            print(f"{status} {LAW_TYPES[lt]['name_zh']:<23} {source_count:<10} {target_count:<10} {to_sync:<10}")
        
        print("-" * 60)
        print(f"   {'總計':<23} {total_source:<10} {total_target:<10} {total_source - total_target:<10}")
        
        if dry_run:
            print(f"\n🔍 [DRY RUN] 以上是同步預覽，實際未執行")
            print(f"💡 移除 --dry-run 參數以執行實際同步")
            source_client.close()
            target_client.close()
            return True
        
        # 確認操作
        print(f"\n⚠️  將從 {source_db.name} 同步資料到 {target_db.name}")
        response = input("是否繼續? (y/N): ")
        if response.lower() != 'y':
            print("❌ 操作已取消")
            source_client.close()
            target_client.close()
            return False
        
        # 執行同步
        total_inserted = 0
        total_updated = 0
        total_skipped = 0
        total_errors = 0
        
        for lt in law_types_to_sync:
            print(f"\n{'='*60}")
            print(f"📚 同步 {LAW_TYPES[lt]['name_zh']}")
            print(f"{'='*60}")
            
            # 取得來源資料
            source_docs = list(source_laws.find({'type': lt}))
            
            if not source_docs:
                print(f"⚠️  來源資料庫中沒有 {LAW_TYPES[lt]['name_zh']} 資料")
                continue
            
            print(f"📖 找到 {len(source_docs)} 條法條")
            
            inserted = 0
            updated = 0
            skipped = 0
            errors = []
            
            for doc in source_docs:
                try:
                    # 移除 _id 讓 MongoDB 自動生成
                    doc_id = doc.pop('_id')
                    
                    # Upsert
                    result = target_laws.update_one(
                        {
                            'article_number': doc['article_number'],
                            'lang': doc['lang'],
                            'type': doc['type']
                        },
                        {'$set': doc},
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        inserted += 1
                        if verbose:
                            print(f"   ✅ 插入: {doc['article_number']}")
                    elif result.modified_count > 0:
                        updated += 1
                        if verbose:
                            print(f"   🔄 更新: {doc['article_number']}")
                    else:
                        skipped += 1
                        if verbose:
                            print(f"   ⏭️  跳過: {doc['article_number']} (無變更)")
                
                except Exception as e:
                    error_msg = f"{doc.get('article_number', 'unknown')}: {str(e)}"
                    errors.append(error_msg)
                    if verbose:
                        print(f"   ❌ 錯誤: {error_msg}")
            
            # 統計
            print(f"\n📊 {LAW_TYPES[lt]['name_zh']} 同步結果:")
            print(f"   插入: {inserted} 條")
            print(f"   更新: {updated} 條")
            print(f"   跳過: {skipped} 條")
            print(f"   錯誤: {len(errors)} 條")
            
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
            total_skipped += skipped
            total_errors += len(errors)
        
        # 確保索引
        print(f"\n{'='*60}")
        print(f"🔧 確保目標資料庫索引...")
        print(f"{'='*60}")
        
        from db.models import Database
        temp_db = Database()
        temp_db.client = target_client
        temp_db.db = target_db
        temp_db.laws_collection = target_laws
        temp_db.init_db()
        
        print(f"✅ 索引建立完成")
        
        # 最終統計
        print(f"\n{'='*60}")
        print(f"📊 同步完成統計")
        print(f"{'='*60}")
        print(f"✅ 插入: {total_inserted} 條")
        print(f"🔄 更新: {total_updated} 條")
        print(f"⏭️  跳過: {total_skipped} 條")
        print(f"❌ 錯誤: {total_errors} 條")
        
        # 最終驗證
        print(f"\n{'='*60}")
        print(f"🔍 最終驗證")
        print(f"{'='*60}")
        print(f"{'法律類型':<25} {'來源':<10} {'目標':<10} {'狀態':<10}")
        print("-" * 60)
        
        all_synced = True
        for lt in law_types_to_sync:
            source_count = source_laws.count_documents({'type': lt})
            target_count = target_laws.count_documents({'type': lt})
            
            if source_count == target_count and source_count > 0:
                status = "✅ 完成"
            elif target_count == 0:
                status = "❌ 失敗"
                all_synced = False
            else:
                status = f"⚠️ 不一致"
                all_synced = False
            
            print(f"   {LAW_TYPES[lt]['name_zh']:<23} {source_count:<10} {target_count:<10} {status:<10}")
        
        source_client.close()
        target_client.close()
        
        return all_synced
        
    except Exception as e:
        print(f"❌ 同步失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='從 MONGO_URI 同步資料到 REMOTE_MONGO_URI')
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
    
    print("="*60)
    print("🔄 資料庫同步工具")
    print("="*60)
    print(f"來源: MONGO_URI")
    print(f"目標: REMOTE_MONGO_URI")
    print("="*60)
    
    if not TARGET_MONGO_URI:
        print("\n❌ 錯誤: REMOTE_MONGO_URI 未設定")
        print("\n請在 .env 檔案中設定:")
        print("  REMOTE_MONGO_URI=mongodb+srv://...")
        return 1
    
    success = sync_laws(
        SOURCE_MONGO_URI,
        TARGET_MONGO_URI,
        law_type=args.law_type,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    print(f"\n{'='*60}")
    if success:
        print("✅ 同步成功！")
        print("\n💡 建議執行診斷工具確認:")
        print("   python scripts/diagnose_heroku_laws.py")
    else:
        print("❌ 同步失敗或資料不一致")
    print(f"{'='*60}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
