#!/usr/bin/env python3
"""
行政訴訟法初始化腳本
Initialize Administrative Litigation Act into database.

從 knowledge/administrative_litigation_zh.md 讀取並解析行政訴訟法內容，
插入到資料庫作為 type='administrative-litigation' 的法條。

Usage:
    python scripts/init_administrative_litigation.py --target local
    python scripts/init_administrative_litigation.py --target remote --dry-run
    python scripts/init_administrative_litigation.py --target both --verbose
"""

import sys
import os
from dataclasses import asdict
from pymongo import MongoClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import LawModel
from scripts.parse_administrative_litigation import parse_administrative_litigation_md

# MongoDB URIs
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/patent_act')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def init_administrative_litigation(target='local', dry_run=False, verbose=False):
    """
    初始化行政訴訟法到資料庫
    
    Args:
        target: 'local' | 'remote' | 'both' - 目標資料庫
        dry_run: 如果為 True，只顯示將插入的資料，不實際寫入
        verbose: 如果為 True，顯示詳細日誌
    
    Returns:
        tuple: (inserted_count, updated_count, error_count)
    """
    md_file = 'knowledge/administrative_litigation_zh.md'
    
    print(f"📖 解析行政訴訟法文件: {md_file}")
    
    try:
        articles = parse_administrative_litigation_md(md_file)
    except Exception as e:
        print(f"❌ 解析失敗: {e}")
        return (0, 0, 1)
    
    print(f"✅ 成功解析 {len(articles)} 條行政訴訟法條文\n")
    
    if dry_run:
        print("🔍 [DRY RUN] 以下資料將被插入:\n")
        for i, article in enumerate(articles[:5], 1):
            print(f"   [{i}] {article['article_number']}")
            print(f"       章節: {article['chapter']}")
            print(f"       內容長度: {len(article['content'])} 字元")
        
        if len(articles) > 5:
            print(f"   ... 還有 {len(articles) - 5} 條")
        
        print(f"\n💡 使用 --verbose 查看更多詳情")
        print(f"💡 移除 --dry-run 參數以實際寫入資料庫")
        return (0, 0, 0)
    
    # 連接資料庫
    print(f"🔌 連接資料庫: {target}")
    
    laws_collections = []
    db_names = []
    
    if target == 'local' or target == 'both':
        client_local = MongoClient(LOCAL_MONGO_URI)
        db_local = client_local.get_database()
        laws_collections.append(db_local['laws'])
        db_names.append('本地')
    
    if target == 'remote' or target == 'both':
        if not REMOTE_MONGO_URI:
            print(f"❌ 遠端資料庫 URI 未設定（REMOTE_MONGO_URI）")
            return (0, 0, 1)
        client_remote = MongoClient(REMOTE_MONGO_URI)
        db_remote = client_remote.get_database()
        laws_collections.append(db_remote['laws'])
        db_names.append('遠端')
    
    if not laws_collections:
        print(f"❌ 無效的 target 參數: {target}")
        return (0, 0, 1)
    
    total_inserted = 0
    total_updated = 0
    total_errors = 0
    
    for db_idx, (db_name, laws_collection) in enumerate(zip(db_names, laws_collections), 1):
        if len(laws_collections) > 1:
            print(f"\n📊 處理 {db_name} 資料庫...")
        
        inserted = 0
        updated = 0
        errors = []
        
        for article in articles:
            try:
                # 設定法律類型和語言
                article_data = article.copy()
                article_data['type'] = 'administrative-litigation'
                article_data['lang'] = 'zh-TW'
                
                # 使用 LawModel 驗證資料結構
                try:
                    law_model = LawModel(**article_data)
                except Exception as e:
                    errors.append(f"{article.get('article_number', 'unknown')}: 資料驗證失敗 - {str(e)}")
                    continue
                
                # Upsert (複合鍵: article_number + lang + type)
                result = laws_collection.update_one(
                    {
                        'article_number': law_model.article_number,
                        'lang': law_model.lang,
                        'type': law_model.type
                    },
                    {
                        '$set': {
                            'content': law_model.content,
                            'chapter': law_model.chapter,
                            'article_number_int': law_model.article_number_int,
                        }
                    },
                    upsert=True
                )
                
                if result.upserted_id:
                    inserted += 1
                    if verbose:
                        print(f"   ✅ 插入: {law_model.article_number}")
                elif result.modified_count > 0:
                    updated += 1
                    if verbose:
                        print(f"   🔄 更新: {law_model.article_number}")
                else:
                    if verbose:
                        print(f"   ⏭️  跳過: {law_model.article_number} (無變更)")
                    
            except Exception as e:
                error_msg = f"{article.get('article_number', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                if verbose:
                    print(f"   ❌ 錯誤: {error_msg}")
        
        # 輸出統計
        print(f"\n{'='*50}")
        if len(laws_collections) > 1:
            print(f"📊 {db_name}資料庫統計:")
        else:
            print(f"📊 統計結果:")
        print(f"   插入: {inserted} 條")
        print(f"   更新: {updated} 條")
        print(f"   錯誤: {len(errors)} 條")
        
        if errors:
            print(f"\n⚠️  發生 {len(errors)} 個錯誤:")
            for error in errors[:5]:
                print(f"   - {error}")
            if len(errors) > 5:
                print(f"   ... 還有 {len(errors) - 5} 個錯誤")
        
        # 驗證最終結果
        final_count = laws_collection.count_documents({
            'type': 'administrative-litigation',
            'lang': 'zh-TW'
        })
        print(f"\n✅ 資料庫中行政訴訟法條文總數: {final_count}")
        
        if final_count != 390:
            print(f"⚠️  警告: 預期約 390 條，實際 {final_count} 條")
        
        total_inserted += inserted
        total_updated += updated
        total_errors += len(errors)
    
    print(f"\n{'='*50}")
    print(f"🎉 行政訴訟法初始化完成！")
    
    return (total_inserted, total_updated, total_errors)


def main():
    """主函數，處理命令列參數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='初始化行政訴訟法到資料庫')
    parser.add_argument('--target', choices=['local', 'remote', 'both'],
                       default='local',
                       help='目標資料庫 (預設: local)')
    parser.add_argument('--dry-run', action='store_true',
                       help='測試模式，不實際寫入資料庫')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='顯示詳細日誌')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("📚 行政訴訟法初始化腳本")
    print("=" * 50)
    print(f"目標: {args.target}")
    print(f"模式: {'DRY RUN (測試)' if args.dry_run else '實際寫入'}")
    print(f"詳細: {'是' if args.verbose else '否'}")
    print("=" * 50)
    print()
    
    inserted, updated, errors = init_administrative_litigation(
        target=args.target,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
    
    # 退出碼
    if errors > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
