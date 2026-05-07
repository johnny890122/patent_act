#!/usr/bin/env python3
"""
將 knowledge/truth_law.json 中的專利法條文插入到本地和遠端資料庫。

Usage:
    python scripts/init_truth_laws.py --local    # 插入到本地資料庫
    python scripts/init_truth_laws.py --remote   # 插入到遠端資料庫
    python scripts/init_truth_laws.py --both     # 插入到本地和遠端資料庫
"""

import os
import sys
import json
import logging
import argparse
import re
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
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

# Path to truth laws data
TRUTH_LAWS_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'truth_law.json'
)


def extract_article_number_int(article_number: str) -> int:
    """
    從條號字串中提取整數，用於排序。
    例如：'第 1 條' -> 1, '第 10 條' -> 10, '第 101 條' -> 101
    """
    match = re.search(r'\d+', article_number)
    if match:
        return int(match.group())
    return 0  # 如果無法提取，返回 0


def load_truth_laws():
    """從 truth_law.json 載入法條資料"""
    logger.info(f"載入法條資料: {TRUTH_LAWS_PATH}")
    
    if not os.path.exists(TRUTH_LAWS_PATH):
        raise FileNotFoundError(f"Truth laws file not found: {TRUTH_LAWS_PATH}")
    
    with open(TRUTH_LAWS_PATH, 'r', encoding='utf-8') as f:
        laws_data = json.load(f)
    
    logger.info(f"載入 {len(laws_data)} 條法條")
    return laws_data


def backfill_lang_field(mongo_uri, db_name=None):
    """
    Backfill existing laws with lang='zh-TW' field.
    
    Args:
        mongo_uri: MongoDB connection string
        db_name: Database name (for logging)
    """
    if db_name is None:
        db_name = "local" if "localhost" in mongo_uri else "remote"
    
    try:
        logger.info(f"Connecting to {db_name} MongoDB for lang field backfill...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        db = client.get_database()
        laws_collection = db['laws']
        
        # Find laws without lang field
        laws_without_lang = laws_collection.count_documents({'lang': {'$exists': False}})
        
        if laws_without_lang > 0:
            logger.info(f"Found {laws_without_lang} laws without lang field, backfilling with 'zh-TW'...")
            result = laws_collection.update_many(
                {'lang': {'$exists': False}},
                {'$set': {'lang': 'zh-TW'}}
            )
            logger.info(f"✅ Updated {result.modified_count} documents with lang='zh-TW'")
        else:
            logger.info("All laws already have lang field")
        
        client.close()
        return True
        
    except Exception as e:
        logger.error(f"Error backfilling lang field: {str(e)}")
        return False


def init_laws_to_db(mongo_uri, db_name=None):
    """
    將法條插入到指定的資料庫。
    
    Args:
        mongo_uri: MongoDB 連線字串
        db_name: 資料庫名稱 (用於 log)
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
        
        # 載入法條資料
        laws_data = load_truth_laws()
        
        # 初始化計數器
        inserted = 0
        updated = 0
        errors = []
        
        logger.info(f"開始處理法條並插入到 {db_name} 資料庫...")
        
        for idx, law_data in enumerate(laws_data, 1):
            try:
                # 提取條號整數用於排序
                article_number_int = extract_article_number_int(law_data['article_number'])
                law_data['article_number_int'] = article_number_int
                
                # 確保 lang field 設定為 zh-TW (預設值)
                if 'lang' not in law_data:
                    law_data['lang'] = 'zh-TW'
                
                # 透過 dataclass 驗證
                law_model = LawModel(**law_data)
                
                # 分離需要更新的欄位和只在插入時設置的欄位
                content_fields = {
                    'article_number': law_model.article_number,
                    'content': law_model.content,
                    'chapter': law_model.chapter,
                    'article_number_int': law_model.article_number_int,
                    'lang': law_model.lang,
                }
                
                # Upsert: 使用複合鍵 (article_number, lang) 以同時處理 zh-TW 和 en
                result = laws_collection.update_one(
                    {'article_number': law_model.article_number, 'lang': law_model.lang},
                    {'$set': content_fields},
                    upsert=True
                )
                
                if result.upserted_id:
                    inserted += 1
                    logger.debug(f"[{idx}/{len(laws_data)}] 插入: {law_model.article_number}")
                else:
                    updated += 1
                    logger.debug(f"[{idx}/{len(laws_data)}] 更新: {law_model.article_number}")
                
            except Exception as e:
                error_msg = f"處理 {law_data.get('article_number', 'unknown')} 時發生錯誤: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # 輸出統計結果
        logger.info("=" * 60)
        logger.info(f"📊 {db_name.upper()} 資料庫插入統計:")
        logger.info(f"   ✅ 新插入: {inserted} 條")
        logger.info(f"   🔄 已更新: {updated} 條")
        logger.info(f"   ❌ 錯誤: {len(errors)} 條")
        logger.info(f"   📝 總計: {len(laws_data)} 條")
        logger.info("=" * 60)
        
        if errors:
            logger.warning("錯誤詳情:")
            for error in errors:
                logger.warning(f"   {error}")
        
        # 驗證資料庫中的法條數量
        total_count = laws_collection.count_documents({})
        logger.info(f"✅ {db_name} 資料庫目前共有 {total_count} 條法條")
        
        client.close()
        return True
        
    except PyMongoError as e:
        logger.error(f"❌ MongoDB 錯誤 ({db_name}): {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ 發生錯誤 ({db_name}): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主程式"""
    parser = argparse.ArgumentParser(
        description='將 truth_law.json 插入到資料庫'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='插入到本地資料庫'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='插入到遠端資料庫'
    )
    parser.add_argument(
        '--both',
        action='store_true',
        help='插入到本地和遠端資料庫'
    )
    
    args = parser.parse_args()
    
    # 確保至少指定一個選項
    if not (args.local or args.remote or args.both):
        parser.print_help()
        logger.error("\n❌ 錯誤: 請指定 --local, --remote 或 --both")
        sys.exit(1)
    
    success = True
    
    # Backfill lang field for existing zh-TW laws
    if args.local or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("Backfilling lang field for local database...")
        logger.info("=" * 60)
        backfill_success = backfill_lang_field(LOCAL_MONGO_URI, "local")
        success = success and backfill_success
    
    if args.remote or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("Backfilling lang field for remote database...")
        logger.info("=" * 60)
        backfill_success = backfill_lang_field(REMOTE_MONGO_URI, "remote")
        success = success and backfill_success
    
    # 插入到本地資料庫
    if args.local or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("開始插入到本地資料庫...")
        logger.info("=" * 60)
        local_success = init_laws_to_db(LOCAL_MONGO_URI, "local")
        success = success and local_success
    
    # 插入到遠端資料庫
    if args.remote or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("開始插入到遠端資料庫...")
        logger.info("=" * 60)
        remote_success = init_laws_to_db(REMOTE_MONGO_URI, "remote")
        success = success and remote_success
    
    if success:
        logger.info("\n✅ 所有操作成功完成!")
        sys.exit(0)
    else:
        logger.error("\n❌ 某些操作失敗，請檢查錯誤訊息")
        sys.exit(1)


if __name__ == '__main__':
    main()
