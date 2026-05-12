#!/usr/bin/env python3
"""
訴願法驗證腳本
Verify Administrative Appeal Act data integrity in database.

驗證訴願法資料完整性，包括條文總數、章節分布、欄位完整性等。

Usage:
    python scripts/verify_administrative_appeal.py
    python scripts/verify_administrative_appeal.py --target remote
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import Database


def verify_administrative_appeal(target='local'):
    """
    驗證訴願法資料完整性
    
    Args:
        target: 'local' | 'remote' | 'both'
    
    Returns:
        bool: 所有檢查是否通過
    """
    print("=" * 60)
    print("✅ 訴願法資料驗證工具")
    print("=" * 60)
    
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
    
    all_passed = True
    
    for db_name, laws_collection in collections:
        print(f"\n{'='*60}")
        print(f"📊 驗證 {db_name} 資料庫")
        print(f"{'='*60}\n")
        
        passed_checks = 0
        failed_checks = 0
        warnings = []
        
        # 1. 檢查條文總數
        print("1️⃣  檢查條文總數...")
        total = laws_collection.count_documents({
            'type': 'administrative-appeal',
            'lang': 'zh-TW'
        })
        
        expected_total = 101
        if total == expected_total:
            print(f"   ✅ 條文總數正確: {total}/{expected_total}")
            passed_checks += 1
        else:
            print(f"   ❌ 條文總數錯誤: {total}/{expected_total}")
            failed_checks += 1
        
        # 2. 檢查章節分布
        print(f"\n2️⃣  檢查章節分布...")
        chapters = laws_collection.distinct('chapter', {
            'type': 'administrative-appeal',
            'lang': 'zh-TW'
        })
        
        expected_chapters = 5  # 訴願法有5章
        main_chapters = set()
        for chapter in chapters:
            # 提取主章節（第X章）
            if '章' in chapter:
                main_chapter = chapter.split('/')[0].strip() if '/' in chapter else chapter.strip()
                # 提取章號
                if '第' in main_chapter and '章' in main_chapter:
                    main_chapters.add(main_chapter.split('章')[0] + '章')
        
        if len(main_chapters) == expected_chapters:
            print(f"   ✅ 章節數量正確: {len(main_chapters)}/{expected_chapters}")
            passed_checks += 1
        else:
            print(f"   ⚠️  章節數量: {len(main_chapters)}/{expected_chapters}")
            warnings.append(f"章節數量異常: {len(main_chapters)}")
        
        print(f"   章節列表:")
        for chapter in sorted(chapters):
            count = laws_collection.count_documents({
                'type': 'administrative-appeal',
                'lang': 'zh-TW',
                'chapter': chapter
            })
            print(f"   - {chapter}: {count} 條")
        
        # 3. 檢查必要欄位完整性
        print(f"\n3️⃣  檢查必要欄位完整性...")
        
        required_fields = ['article_number', 'article_number_int', 'content', 'chapter', 'type', 'lang']
        missing_fields_count = 0
        
        for field in required_fields:
            missing = laws_collection.count_documents({
                'type': 'administrative-appeal',
                'lang': 'zh-TW',
                field: {'$exists': False}
            })
            if missing > 0:
                print(f"   ❌ {field}: {missing} 條缺少此欄位")
                missing_fields_count += missing
                failed_checks += 1
        
        if missing_fields_count == 0:
            print(f"   ✅ 所有必要欄位完整")
            passed_checks += 1
        
        # 4. 檢查內容不為空
        print(f"\n4️⃣  檢查內容完整性...")
        empty_content = laws_collection.count_documents({
            'type': 'administrative-appeal',
            'lang': 'zh-TW',
            '$or': [
                {'content': ''},
                {'content': None}
            ]
        })
        
        if empty_content == 0:
            print(f"   ✅ 所有條文內容非空")
            passed_checks += 1
        else:
            print(f"   ❌ {empty_content} 條內容為空")
            failed_checks += 1
        
        # 5. 檢查 article_number_int 範圍
        print(f"\n5️⃣  檢查條號範圍...")
        articles = list(laws_collection.find(
            {'type': 'administrative-appeal', 'lang': 'zh-TW'},
            {'article_number_int': 1, 'article_number': 1}
        ).sort('article_number_int', 1))
        
        if articles:
            min_num = articles[0]['article_number_int']
            max_num = articles[-1]['article_number_int']
            
            if min_num == 1 and max_num == 101:
                print(f"   ✅ 條號範圍正確: {min_num}-{max_num}")
                passed_checks += 1
            else:
                print(f"   ⚠️  條號範圍: {min_num}-{max_num} (預期: 1-101)")
                warnings.append(f"條號範圍異常: {min_num}-{max_num}")
        
        # 6. 檢查 type 欄位正確性
        print(f"\n6️⃣  檢查 type 欄位...")
        wrong_type = laws_collection.count_documents({
            'type': {'$ne': 'administrative-appeal'},
            'article_number': {'$regex': '^第 \\d+ 條$'},
            'chapter': {'$regex': '第.章'}
        })
        
        if wrong_type == 0:
            print(f"   ✅ 所有訴願法條文 type 正確")
            passed_checks += 1
        else:
            print(f"   ⚠️  {wrong_type} 條可能 type 設置錯誤")
            warnings.append(f"{wrong_type} 條 type 設置錯誤")
        
        # 7. 檢查重複條文
        print(f"\n7️⃣  檢查重複條文...")
        pipeline = [
            {
                '$match': {
                    'type': 'administrative-appeal',
                    'lang': 'zh-TW'
                }
            },
            {
                '$group': {
                    '_id': '$article_number',
                    'count': {'$sum': 1}
                }
            },
            {
                '$match': {
                    'count': {'$gt': 1}
                }
            }
        ]
        
        duplicates = list(laws_collection.aggregate(pipeline))
        
        if len(duplicates) == 0:
            print(f"   ✅ 無重複條文")
            passed_checks += 1
        else:
            print(f"   ❌ 發現 {len(duplicates)} 個重複條號:")
            for dup in duplicates:
                print(f"      - {dup['_id']}: {dup['count']} 次")
            failed_checks += 1
        
        # 總結
        print(f"\n{'='*60}")
        print(f"📊 {db_name}資料庫驗證總結")
        print(f"{'='*60}")
        print(f"   ✅ 通過檢查: {passed_checks}")
        print(f"   ❌ 失敗檢查: {failed_checks}")
        print(f"   ⚠️  警告數量: {len(warnings)}")
        
        if warnings:
            print(f"\n⚠️  警告列表:")
            for warning in warnings:
                print(f"   - {warning}")
        
        if failed_checks == 0:
            print(f"\n✅ {db_name}資料庫驗證通過！")
        else:
            print(f"\n❌ {db_name}資料庫驗證失敗")
            all_passed = False
    
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 所有資料庫驗證通過！")
    else:
        print("❌ 部分資料庫驗證失敗")
    print(f"{'='*60}\n")
    
    return all_passed


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='驗證訴願法資料完整性')
    parser.add_argument('--target', choices=['local', 'remote', 'both'],
                       default='local',
                       help='目標資料庫 (預設: local)')
    
    args = parser.parse_args()
    
    try:
        success = verify_administrative_appeal(target=args.target)
        
        if success:
            sys.exit(0)
        else:
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
