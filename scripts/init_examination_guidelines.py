#!/usr/bin/env python3
"""
將 knowledge/examination/ 目錄中的專利審查基準插入到資料庫。

Usage:
    python scripts/init_examination_guidelines.py --local    # 插入到本地資料庫
    python scripts/init_examination_guidelines.py --remote   # 插入到遠端資料庫
    python scripts/init_examination_guidelines.py --both     # 插入到本地和遠端資料庫
    python scripts/init_examination_guidelines.py --dry-run  # 測試模式，不實際寫入
"""

import os
import sys
import json
import glob
import logging
import argparse
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add parent directory to path to import from project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.models import LawModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB URIs (從 .env 讀取或使用預設值)
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/patent_act')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

# Path to examination guidelines data
EXAMINATION_DIR = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'examination'
)


def load_examination_guidelines():
    """從 knowledge/examination/ 載入所有審查基準 JSON 檔案"""
    pattern = os.path.join(EXAMINATION_DIR, '*', '*.json')
    json_files = sorted(glob.glob(pattern))
    
    logger.info(f"掃描審查基準檔案: {pattern}")
    logger.info(f"找到 {len(json_files)} 個 JSON 檔案")
    
    all_articles = []
    file_count = 0
    
    for json_file in json_files:
        # 跳過 test.ipynb 相關檔案
        if 'test' in os.path.basename(json_file).lower():
            logger.debug(f"跳過測試檔案: {json_file}")
            continue
            
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
            
            if not isinstance(articles, list):
                logger.warning(f"⚠️  檔案格式不正確（非陣列）: {json_file}")
                continue
            
            logger.debug(f"載入 {len(articles)} 條來自 {os.path.basename(json_file)}")
            all_articles.extend(articles)
            file_count += 1
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON 解析錯誤: {json_file} - {str(e)}")
        except Exception as e:
            logger.error(f"❌ 讀取檔案錯誤: {json_file} - {str(e)}")
    
    logger.info(f"成功載入 {file_count} 個檔案，共 {len(all_articles)} 條審查基準")
    return all_articles


def init_guidelines_to_db(mongo_uri, db_name=None, dry_run=False):
    """
    將審查基準插入到指定的資料庫。
    
    Args:
        mongo_uri: MongoDB 連線字串
        db_name: 資料庫名稱 (用於 log)
        dry_run: 是否為測試模式（不實際寫入）
    """
    # 自動設定 db_name
    if db_name is None:
        db_name = "local" if "localhost" in mongo_uri else "remote"
    
    try:
        # 連接資料庫
        logger.info(f"連接到 {db_name} MongoDB...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # 測試連線
        client.admin.command('ping')
        logger.info(f"✅ 成功連接到 {db_name} MongoDB")
        
        # 取得資料庫和集合
        db = client.get_database()
        laws_collection = db['laws']
        
        # 載入審查基準資料
        articles = load_examination_guidelines()
        
        if not articles:
            logger.warning("⚠️  沒有找到任何審查基準資料")
            return
        
        # 初始化計數器
        inserted = 0
        updated = 0
        skipped = 0
        errors = []
        
        logger.info(f"開始處理審查基準並{'模擬' if dry_run else '插入到'} {db_name} 資料庫...")
        
        for idx, article_data in enumerate(articles, 1):
            try:
                # 設定 type 為 patent-examination
                article_data['type'] = 'patent-examination'
                
                # 確保 lang field 設定為 zh-TW
                if 'lang' not in article_data:
                    article_data['lang'] = 'zh-TW'
                
                # 檢查必要欄位
                required_fields = ['article_number', 'content', 'chapter', 'article_number_int']
                missing_fields = [f for f in required_fields if f not in article_data]
                if missing_fields:
                    raise ValueError(f"缺少必要欄位: {', '.join(missing_fields)}")
                
                # 透過 dataclass 驗證
                law_model = LawModel(**article_data)
                
                # 準備要更新的欄位
                content_fields = {
                    'article_number': law_model.article_number,
                    'content': law_model.content,
                    'chapter': law_model.chapter,
                    'article_number_int': law_model.article_number_int,
                    'lang': law_model.lang,
                    'type': law_model.type,
                }
                
                if dry_run:
                    # 測試模式：只檢查不寫入
                    logger.debug(f"[DRY-RUN] [{idx}/{len(articles)}] {law_model.article_number}")
                    inserted += 1
                else:
                    # Upsert: 使用複合鍵 (article_number, lang, type)
                    result = laws_collection.update_one(
                        {
                            'article_number': law_model.article_number, 
                            'lang': law_model.lang,
                            'type': law_model.type
                        },
                        {'$set': content_fields},
                        upsert=True
                    )
                    
                    if result.upserted_id:
                        inserted += 1
                        logger.debug(f"[{idx}/{len(articles)}] 插入: {law_model.article_number}")
                    elif result.modified_count > 0:
                        updated += 1
                        logger.debug(f"[{idx}/{len(articles)}] 更新: {law_model.article_number}")
                    else:
                        skipped += 1
                        logger.debug(f"[{idx}/{len(articles)}] 跳過（無變更）: {law_model.article_number}")
                
            except Exception as e:
                error_msg = f"處理 {article_data.get('article_number', 'unknown')} 時發生錯誤: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # 輸出統計結果
        logger.info("=" * 70)
        logger.info(f"📊 {db_name.upper()} 資料庫{'模擬' if dry_run else '插入'}統計:")
        logger.info(f"   ✅ 新插入: {inserted} 條")
        logger.info(f"   🔄 已更新: {updated} 條")
        logger.info(f"   ⏭️  跳過: {skipped} 條")
        logger.info(f"   ❌ 錯誤: {len(errors)} 條")
        logger.info(f"   📝 總計: {len(articles)} 條")
        logger.info("=" * 70)
        
        if errors:
            logger.warning("錯誤詳情:")
            for error in errors[:10]:  # 只顯示前 10 個錯誤
                logger.warning(f"  - {error}")
            if len(errors) > 10:
                logger.warning(f"  ... 還有 {len(errors) - 10} 個錯誤")
        
        # 驗證插入結果（非測試模式）
        if not dry_run:
            count = laws_collection.count_documents({'type': 'patent-examination', 'lang': 'zh-TW'})
            logger.info(f"✅ 資料庫中現有 {count} 條審查基準（zh-TW）")
        
        client.close()
        return True
        
    except PyMongoError as e:
        logger.error(f"❌ MongoDB 錯誤: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ 未預期的錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='將專利審查基準插入到 MongoDB 資料庫'
    )
    
    # 互斥參數群組：只能選擇一個目標資料庫
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--local', action='store_true', help='插入到本地資料庫')
    group.add_argument('--remote', action='store_true', help='插入到遠端資料庫')
    group.add_argument('--both', action='store_true', help='插入到本地和遠端資料庫')
    group.add_argument('--dry-run', action='store_true', help='測試模式，不實際寫入')
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🚀 開始初始化專利審查基準")
    logger.info("=" * 70)
    
    success = True
    
    if args.dry_run:
        logger.info("🧪 執行測試模式...")
        success = init_guidelines_to_db(LOCAL_MONGO_URI, "dry-run", dry_run=True)
    elif args.local or args.both:
        logger.info("📥 處理本地資料庫...")
        success = init_guidelines_to_db(LOCAL_MONGO_URI, "local") and success
    
    if args.remote or args.both:
        if not REMOTE_MONGO_URI:
            logger.error("❌ 遠端資料庫 URI 未設定（REMOTE_MONGO_URI）")
            success = False
        else:
            logger.info("📤 處理遠端資料庫...")
            success = init_guidelines_to_db(REMOTE_MONGO_URI, "remote") and success
    
    if success:
        logger.info("=" * 70)
        logger.info("✅ 審查基準初始化完成！")
        logger.info("=" * 70)
        sys.exit(0)
    else:
        logger.error("=" * 70)
        logger.error("❌ 審查基準初始化失敗")
        logger.error("=" * 70)
        sys.exit(1)


if __name__ == '__main__':
    main()
