#!/usr/bin/env python3
"""
修復 laws collection 的索引問題
Fix laws collection index to support multiple law types with same article numbers.

問題：舊的 article_number 單一欄位唯一索引導致不同法律類型無法有相同條號
解決：移除舊索引，建立 (article_number, lang, type) 複合唯一索引

Usage:
    python scripts/fix_laws_index.py --target local
    python scripts/fix_laws_index.py --target both --dry-run
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import Database


def fix_laws_index(target='local', dry_run=False):
    """
    修復 laws collection 的索引
    
    Args:
        target: 'local' | 'remote' | 'both'
        dry_run: 如果為 True，只顯示操作，不實際執行
    
    Returns:
        bool: 是否成功
    """
    print("=" * 60)
    print("🔧 Laws Collection 索引修復工具")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY RUN 模式：不會實際修改索引\n")
    
    # 連接資料庫
    if target == 'local':
        db = Database()
        collections = [('本地', db.laws_collection)]
    elif target == 'remote':
        db = Database()
        db.connect_remote()
        collections = [('遠端', db.laws_collection)]
    elif target == 'both':
        db_local = Database()
        db_remote = Database()
        db_remote.connect_remote()
        collections = [('本地', db_local.laws_collection), ('遠端', db_remote.laws_collection)]
    else:
        print(f"❌ 無效的 target 參數: {target}")
        return False
    
    all_success = True
    
    for db_name, laws_collection in collections:
        print(f"\n{'='*60}")
        print(f"📊 處理 {db_name} 資料庫")
        print(f"{'='*60}\n")
        
        try:
            # 1. 檢查當前索引
            print("1️⃣  檢查當前索引...")
            indexes = list(laws_collection.list_indexes())
            
            print(f"   找到 {len(indexes)} 個索引:")
            for idx in indexes:
                print(f"   - {idx['name']}: {idx.get('key', {})}")
            
            # 檢查舊索引是否存在
            old_index_1_exists = any(idx['name'] == 'article_number_1' for idx in indexes)
            old_index_2_exists = any(idx['name'] == 'article_number_1_lang_1' for idx in indexes)
            new_index_exists = any(
                'article_number' in idx.get('key', {}) and
                'lang' in idx.get('key', {}) and
                'type' in idx.get('key', {})
                for idx in indexes
            )
            
            print(f"\n   舊索引 (article_number_1): {'存在 ⚠️' if old_index_1_exists else '不存在 ✅'}")
            print(f"   舊索引 (article_number_1_lang_1): {'存在 ⚠️' if old_index_2_exists else '不存在 ✅'}")
            print(f"   新索引 (article_number+lang+type): {'存在 ✅' if new_index_exists else '不存在 ⚠️'}")
            
            # 2. 移除舊索引
            removed_count = 0
            print(f"\n2️⃣  移除舊索引...")
            
            if old_index_1_exists:
                if not dry_run:
                    laws_collection.drop_index('article_number_1')
                    print("   ✅ 已移除 article_number_1")
                    removed_count += 1
                else:
                    print("   [DRY RUN] 將移除 article_number_1")
            
            if old_index_2_exists:
                if not dry_run:
                    laws_collection.drop_index('article_number_1_lang_1')
                    print("   ✅ 已移除 article_number_1_lang_1")
                    removed_count += 1
                else:
                    print("   [DRY RUN] 將移除 article_number_1_lang_1")
            
            if not old_index_1_exists and not old_index_2_exists:
                print("   跳過（已不存在衝突索引）")
            
            # 3. 建立新索引
            if not new_index_exists:
                print(f"\n3️⃣  建立新的複合唯一索引...")
                if not dry_run:
                    laws_collection.create_index(
                        [
                            ('article_number', 1),
                            ('lang', 1),
                            ('type', 1)
                        ],
                        unique=True,
                        name='article_number_lang_type_unique'
                    )
                    print("   ✅ 新索引已建立")
                else:
                    print("   [DRY RUN] 將建立複合索引 (article_number, lang, type)")
            else:
                print(f"\n3️⃣  跳過建立新索引（已存在）")
            
            # 4. 驗證最終狀態
            print(f"\n4️⃣  驗證索引...")
            if not dry_run:
                indexes_final = list(laws_collection.list_indexes())
                print(f"   最終索引數量: {len(indexes_final)}")
                for idx in indexes_final:
                    if 'article_number' in idx.get('key', {}):
                        print(f"   ✅ {idx['name']}: {idx.get('key', {})}")
            else:
                print("   [DRY RUN] 跳過驗證")
            
            print(f"\n✅ {db_name}資料庫索引修復完成")
            
        except Exception as e:
            print(f"\n❌ {db_name}資料庫處理失敗: {e}")
            import traceback
            traceback.print_exc()
            all_success = False
    
    print(f"\n{'='*60}")
    if all_success:
        print("🎉 所有資料庫索引修復完成！")
    else:
        print("⚠️  部分資料庫處理失敗")
    print(f"{'='*60}\n")
    
    return all_success


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='修復 laws collection 索引')
    parser.add_argument('--target', choices=['local', 'remote', 'both'],
                       default='local',
                       help='目標資料庫 (預設: local)')
    parser.add_argument('--dry-run', action='store_true',
                       help='測試模式，不實際修改索引')
    
    args = parser.parse_args()
    
    try:
        success = fix_laws_index(target=args.target, dry_run=args.dry_run)
        
        if success:
            print("✅ 完成！現在可以執行 init_administrative_appeal.py 了")
            sys.exit(0)
        else:
            print("❌ 處理失敗")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  被用戶中斷")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 執行失敗: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
