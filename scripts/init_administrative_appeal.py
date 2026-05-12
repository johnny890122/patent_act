#!/usr/bin/env python3
"""
訴願法初始化腳本
Initialize Administrative Appeal Act into database.

從 knowledge/administrative_appeal_zh.md 讀取並解析訴願法內容，
插入到資料庫作為 type='administrative-appeal' 的法條。

Usage:
    python scripts/init_administrative_appeal.py --target local
    python scripts/init_administrative_appeal.py --target remote --dry-run
    python scripts/init_administrative_appeal.py --target both --verbose
"""

import sys
import os
from dataclasses import asdict

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import Database, LawModel
from scripts.parse_administrative_appeal import parse_administrative_appeal_md


def init_administrative_appeal(target='local', dry_run=False, verbose=False):
    """
    初始化訴願法到資料庫
    
    Args:
        target: 'local' | 'remote' | 'both' - 目標資料庫
        dry_run: 如果為 True，只顯示將插入的資料，不實際寫入
        verbose: 如果為 True，顯示詳細日誌
    
    Returns:
        tuple: (inserted_count, updated_count, error_count)
    """
    md_file = 'knowledge/administrative_appeal_zh.md'
    
    print(f"📖 解析訴願法文件: {md_file}")
    
    try:
        articles = parse_administrative_appeal_md(md_file)
    except Exception as e:
        print(f"❌ 解析失敗: {e}")
        return (0, 0, 1)
    
    print(f"✅ 成功解析 {len(articles)} 條訴願法條文\n")
    
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
    
    if target == 'local':
        db = Database()
        laws_collections = [db.laws_collection]
    elif target == 'remote':
        db = Database()
        db.connect_remote()
        laws_collections = [db.laws_collection]
    elif target == 'both':
        db_local = Database()
        db_remote = Database()
        db_remote.connect_remote()
        laws_collections = [db_local.laws_collection, db_remote.laws_collection]
    else:
        print(f"❌ 無效的 target 參數: {target}")
        return (0, 0, 1)
    
    total_inserted = 0
    total_updated = 0
    total_errors = 0
    
    for db_idx, laws_collection in enumerate(laws_collections, 1):
        if len(laws_collections) > 1:
            db_name = "本地" if db_idx == 1 else "遠端"
            print(f"\n📊 處理 {db_name} 資料庫...")
        
        inserted = 0
        updated = 0
        errors = []
        
        for article in articles:
            try:
                # 設定法律類型和語言
                article_data = article.copy()
                article_data['type'] = 'administrative-appeal'
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
            'type': 'administrative-appeal',
            'lang': 'zh-TW'
        })
        print(f"\n✅ 資料庫中訴願法條文總數: {final_count}")
        
        if final_count != 101:
            print(f"⚠️  警告: 預期 101 條，實際 {final_count} 條")
        
        total_inserted += inserted
        total_updated += updated
        total_errors += len(errors)
    
    print(f"\n{'='*50}")
    print(f"🎉 訴願法初始化完成！")
    
    return (total_inserted, total_updated, total_errors)


def main():
    """主函數，處理命令列參數"""
    import argparse
    
    parser = argparse.ArgumentParser(description='初始化訴願法到資料庫')
    parser.add_argument('--target', choices=['local', 'remote', 'both'],
                       default='local',
                       help='目標資料庫 (預設: local)')
    parser.add_argument('--dry-run', action='store_true',
                       help='測試模式，不實際寫入資料庫')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='顯示詳細日誌')
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("📚 訴願法初始化腳本")
    print("=" * 50)
    
    if args.dry_run:
        print("⚠️  DRY RUN 模式：不會實際寫入資料庫\n")
    
    try:
        inserted, updated, errors = init_administrative_appeal(
            target=args.target,
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        if errors > 0:
            print(f"\n⚠️  完成，但有 {errors} 個錯誤")
            sys.exit(1)
        else:
            print(f"\n✅ 全部成功完成！")
            sys.exit(0)
            
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
