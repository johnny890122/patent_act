#!/usr/bin/env python3
"""
同步法條資料到 Heroku 生產資料庫
Sync law articles to Heroku production database

使用方法:
1. 設定 HEROKU_MONGO_URI 環境變數為 Heroku 的 MONGO_URI
   export HEROKU_MONGO_URI="mongodb+srv://..."
   
2. 運行腳本:
   python scripts/sync_to_heroku.py --law-type administrative-appeal
   python scripts/sync_to_heroku.py --law-type administrative-litigation
   python scripts/sync_to_heroku.py --law-type all
"""

import sys
import os
from pymongo import MongoClient
import argparse

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import LawModel, LAW_TYPES
from scripts.parse_administrative_appeal import parse_administrative_appeal_md
from scripts.parse_administrative_litigation import parse_administrative_litigation_md

# Heroku 生產環境的 MongoDB URI
# 從環境變數讀取，或者使用 MONGO_URI 作為備選
HEROKU_MONGO_URI = os.environ.get('HEROKU_MONGO_URI') or os.environ.get('MONGO_URI')


def sync_law_type(mongo_uri, law_type, verbose=False):
    """
    同步指定類型的法條到資料庫
    
    Args:
        mongo_uri: MongoDB 連接 URI
        law_type: 法律類型 (administrative-appeal, administrative-litigation, all)
        verbose: 顯示詳細日誌
        
    Returns:
        bool: 是否成功
    """
    if not mongo_uri:
        print("❌ 錯誤: HEROKU_MONGO_URI 或 MONGO_URI 未設定")
        print("\n請設定環境變數:")
        print("  export HEROKU_MONGO_URI='你的MongoDB URI'")
        print("\n或從 Heroku 取得:")
        print("  heroku config:get MONGO_URI")
        return False
    
    try:
        # 連接資料庫
        print(f"🔌 連接 Heroku 資料庫...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print(f"✅ 連接成功")
        
        db = client.get_database()
        laws_collection = db['laws']
        
        print(f"📊 資料庫: {db.name}")
        
        # 根據法律類型處理
        law_types_to_sync = []
        
        if law_type == 'all':
            law_types_to_sync = [
                ('administrative-appeal', 'knowledge/administrative_appeal_zh.md', parse_administrative_appeal_md, 101),
                ('administrative-litigation', 'knowledge/administrative_litigation_zh.md', parse_administrative_litigation_md, 390)
            ]
        elif law_type == 'administrative-appeal':
            law_types_to_sync = [
                ('administrative-appeal', 'knowledge/administrative_appeal_zh.md', parse_administrative_appeal_md, 101)
            ]
        elif law_type == 'administrative-litigation':
            law_types_to_sync = [
                ('administrative-litigation', 'knowledge/administrative_litigation_zh.md', parse_administrative_litigation_md, 390)
            ]
        else:
            print(f"❌ 不支援的法律類型: {law_type}")
            return False
        
        # 處理每種法律類型
        for type_code, md_file, parser_func, expected_count in law_types_to_sync:
            print(f"\n{'='*60}")
            print(f"📚 同步 {LAW_TYPES[type_code]['name_zh']}")
            print(f"{'='*60}")
            
            # 解析法條
            print(f"📖 解析文件: {md_file}")
            try:
                articles = parser_func(md_file)
            except Exception as e:
                print(f"❌ 解析失敗: {e}")
                continue
            
            print(f"✅ 解析成功: {len(articles)} 條")
            
            # 插入/更新法條
            inserted = 0
            updated = 0
            errors = []
            
            for article in articles:
                try:
                    # 設定法律類型和語言
                    article_data = article.copy()
                    article_data['type'] = type_code
                    article_data['lang'] = 'zh-TW'
                    
                    # 驗證資料
                    law_model = LawModel(**article_data)
                    
                    # Upsert
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
            
            # 統計結果
            print(f"\n{'='*50}")
            print(f"📊 同步結果:")
            print(f"   插入: {inserted} 條")
            print(f"   更新: {updated} 條")
            print(f"   錯誤: {len(errors)} 條")
            
            if errors:
                print(f"\n⚠️  錯誤詳情:")
                for error in errors[:5]:
                    print(f"   - {error}")
                if len(errors) > 5:
                    print(f"   ... 還有 {len(errors) - 5} 個錯誤")
            
            # 驗證結果
            final_count = laws_collection.count_documents({
                'type': type_code,
                'lang': 'zh-TW'
            })
            print(f"\n✅ 資料庫中總數: {final_count} 條")
            
            if final_count != expected_count:
                print(f"⚠️  警告: 預期 {expected_count} 條，實際 {final_count} 條")
        
        # 確保索引建立
        print(f"\n{'='*60}")
        print(f"🔧 確保資料庫索引...")
        print(f"{'='*60}")
        
        from db.models import Database
        # 創建臨時資料庫實例來建立索引
        temp_db = Database()
        temp_db.client = client
        temp_db.db = db
        temp_db.laws_collection = laws_collection
        temp_db.init_db()
        
        print(f"✅ 索引建立完成")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ 同步失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='同步法條資料到 Heroku 生產資料庫')
    parser.add_argument('--law-type', 
                       choices=['administrative-appeal', 'administrative-litigation', 'all'],
                       default='all',
                       help='要同步的法律類型')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='顯示詳細日誌')
    
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 Heroku 資料庫同步工具")
    print("="*60)
    
    if not HEROKU_MONGO_URI:
        print("\n❌ 錯誤: 找不到資料庫連接資訊")
        print("\n請使用以下方式設定:")
        print("  方法 1: export HEROKU_MONGO_URI='...'")
        print("  方法 2: 確保 .env 中已設定 MONGO_URI")
        print("  方法 3: 從 Heroku 取得: heroku config:get MONGO_URI")
        return 1
    
    print(f"\n⚠️  將同步資料到: {HEROKU_MONGO_URI[:50]}...")
    print(f"法律類型: {args.law_type}")
    
    # 確認操作
    response = input("\n是否繼續? (y/N): ")
    if response.lower() != 'y':
        print("❌ 操作已取消")
        return 0
    
    success = sync_law_type(HEROKU_MONGO_URI, args.law_type, verbose=args.verbose)
    
    print(f"\n{'='*60}")
    if success:
        print("✅ 同步完成！")
        print("\n💡 建議執行診斷工具確認:")
        print("   python scripts/diagnose_heroku_laws.py")
    else:
        print("❌ 同步失敗")
    print(f"{'='*60}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
