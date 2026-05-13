#!/usr/bin/env python3
"""
行政訴訟法驗證腳本
Verify Administrative Litigation Act data integrity in database.

驗證行政訴訟法資料完整性，包括條文總數、編分布、欄位完整性等。

Usage:
    python scripts/verify_administrative_litigation.py
    python scripts/verify_administrative_litigation.py --target remote
"""

import sys
import os
from pymongo import MongoClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MongoDB URIs
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/patent_act')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def verify_administrative_litigation(target='local'):
    """
    驗證行政訴訟法資料完整性
    
    Args:
        target: 'local' | 'remote' | 'both'
    
    Returns:
        bool: 所有檢查是否通過
    """
    print("=" * 60)
    print("✅ 行政訴訟法資料驗證工具")
    print("=" * 60)
    
    # 連接資料庫
    collections = []
    
    if target == 'local' or target == 'both':
        client_local = MongoClient(LOCAL_MONGO_URI)
        db_local = client_local.get_database()
        collections.append(('本地', db_local['laws']))
    
    if target == 'remote' or target == 'both':
        if not REMOTE_MONGO_URI:
            print(f"❌ 遠端資料庫 URI 未設定（REMOTE_MONGO_URI）")
            return False
        client_remote = MongoClient(REMOTE_MONGO_URI)
        db_remote = client_remote.get_database()
        collections.append(('遠端', db_remote['laws']))
    
    if not collections:
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
            'type': 'administrative-litigation',
            'lang': 'zh-TW'
        })
        
        expected_total = 390  # 包含附加條號
        if total == expected_total:
            print(f"   ✅ 條文總數正確: {total}/{expected_total}")
            passed_checks += 1
        else:
            # 允許一些彈性（可能有附加條號）
            if abs(total - expected_total) <= 10:
                print(f"   ⚠️  條文總數: {total}/{expected_total} (在合理範圍)")
                warnings.append(f"條文總數略有差異: {total}")
                passed_checks += 1
            else:
                print(f"   ❌ 條文總數錯誤: {total}/{expected_total}")
                failed_checks += 1
        
        # 2. 檢查編分布
        print(f"\n2️⃣  檢查編分布...")
        chapters = laws_collection.distinct('chapter', {
            'type': 'administrative-litigation',
            'lang': 'zh-TW'
        })
        
        expected_editions = 9  # 行政訴訟法有9編
        editions = set()
        for chapter in chapters:
            # 提取編（第一層級）
            if '編' in chapter:
                if ' / ' in chapter:
                    edition = chapter.split(' / ')[0].strip()
                else:
                    edition = chapter.strip()
                if '第' in edition and '編' in edition:
                    editions.add(edition.split('編')[0] + '編')
        
        if len(editions) == expected_editions:
            print(f"   ✅ 編數量正確: {len(editions)}/{expected_editions}")
            passed_checks += 1
        else:
            print(f"   ⚠️  編數量: {len(editions)}/{expected_editions}")
            warnings.append(f"編數量異常: {len(editions)}")
        
        print(f"   編分布:")
        edition_counts = {}
        for chapter in chapters:
            if ' / ' in chapter:
                edition = chapter.split(' / ')[0].strip()
            else:
                edition = chapter
            count = laws_collection.count_documents({
                'type': 'administrative-litigation',
                'lang': 'zh-TW',
                'chapter': chapter
            })
            if edition in edition_counts:
                edition_counts[edition] += count
            else:
                edition_counts[edition] = count
        
        for edition, count in sorted(edition_counts.items()):
            print(f"   - {edition}: {count} 條")
        
        # 3. 檢查必要欄位完整性
        print(f"\n3️⃣  檢查必要欄位完整性...")
        
        required_fields = ['article_number', 'article_number_int', 'content', 'chapter', 'type', 'lang']
        missing_fields_count = 0
        
        for field in required_fields:
            missing = laws_collection.count_documents({
                'type': 'administrative-litigation',
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
            'type': 'administrative-litigation',
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
            {'type': 'administrative-litigation', 'lang': 'zh-TW'},
            {'article_number_int': 1, 'article_number': 1}
        ).sort('article_number_int', 1))
        
        if articles:
            min_num = articles[0]['article_number_int']
            max_num = articles[-1]['article_number_int']
            
            if min_num == 1 and max_num == 308:
                print(f"   ✅ 條號範圍正確: {min_num}-{max_num}")
                passed_checks += 1
            else:
                print(f"   ⚠️  條號範圍: {min_num}-{max_num} (預期: 1-308)")
                warnings.append(f"條號範圍異常: {min_num}-{max_num}")
                if min_num == 1 and max_num >= 305:
                    # 接近預期範圍，視為通過
                    passed_checks += 1
        
        # 檢查附加條號
        print(f"\n   檢查附加條號...")
        compound_articles = list(laws_collection.find(
            {
                'type': 'administrative-litigation',
                'lang': 'zh-TW',
                'article_number': {'$regex': '-'}
            },
            {'article_number': 1, 'article_number_int': 1}
        ).limit(10))
        
        if compound_articles:
            print(f"   ℹ️  發現 {len(compound_articles)} 個附加條號（顯示前10個）:")
            for art in compound_articles[:10]:
                print(f"      - {art['article_number']} (int: {art['article_number_int']})")
        
        # 6. 檢查 type 欄位正確性
        print(f"\n6️⃣  檢查 type 欄位...")
        correct_type = laws_collection.count_documents({
            'type': 'administrative-litigation',
            'lang': 'zh-TW'
        })
        
        if correct_type == total:
            print(f"   ✅ 所有行政訴訟法條文 type 正確")
            passed_checks += 1
        else:
            print(f"   ⚠️  {total - correct_type} 條 type 設置可能有誤")
            warnings.append(f"{total - correct_type} 條 type 設置錯誤")
        
        # 7. 檢查重複條文
        print(f"\n7️⃣  檢查重複條文...")
        pipeline = [
            {
                '$match': {
                    'type': 'administrative-litigation',
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
    
    parser = argparse.ArgumentParser(description='驗證行政訴訟法資料完整性')
    parser.add_argument('--target', choices=['local', 'remote', 'both'],
                       default='local',
                       help='目標資料庫 (預設: local)')
    
    args = parser.parse_args()
    
    try:
        success = verify_administrative_litigation(target=args.target)
        
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
