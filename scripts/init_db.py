#!/usr/bin/env python3
"""
整合的資料庫初始化腳本
1. 初始化法條資料 (從 truth_law.json)
2. 預先生成選擇題和簡答題各40題

Usage:
    python scripts/init_db.py --local    # 初始化本地資料庫
    python scripts/init_db.py --remote   # 初始化遠端資料庫
    python scripts/init_db.py --both     # 初始化本地和遠端資料庫
    
Options:
    --skip-laws        跳過法條初始化，只生成題目
    --skip-questions   跳過題目生成，只初始化法條
"""

import os
import sys
import json
import logging
import argparse
import re
import random
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add parent directory to path to import from project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.models import LawModel
from services.question_gen import QuestionGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB URIs
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

# Paths
TRUTH_LAWS_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'truth_law.json'
)


def extract_article_number_int(article_number: str) -> int:
    """從條號字串中提取整數，用於排序"""
    match = re.search(r'\d+', article_number)
    if match:
        return int(match.group())
    return 0


def load_truth_laws():
    """從 truth_law.json 載入法條資料"""
    logger.info(f"載入法條資料: {TRUTH_LAWS_PATH}")
    
    if not os.path.exists(TRUTH_LAWS_PATH):
        raise FileNotFoundError(f"Truth laws file not found: {TRUTH_LAWS_PATH}")
    
    with open(TRUTH_LAWS_PATH, 'r', encoding='utf-8') as f:
        laws_data = json.load(f)
    
    logger.info(f"載入 {len(laws_data)} 條法條")
    return laws_data


def init_laws_to_db(client, db_name=None):
    """
    初始化法條到資料庫
    
    Args:
        client: MongoDB client
        db_name: 資料庫名稱 (用於 log)
    
    Returns:
        bool: 是否成功
    """
    try:
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
                
                # 透過 dataclass 驗證
                law_model = LawModel(**law_data)
                law_dict = {
                    'article_number': law_model.article_number,
                    'content': law_model.content,
                    'chapter': law_model.chapter,
                    'article_number_int': law_model.article_number_int,
                    'is_starred': law_model.is_starred,
                    'total_score': law_model.total_score,
                    'attempt_count': law_model.attempt_count,
                    'avg_score': law_model.avg_score
                }
                
                # Upsert: 若存在則更新，不存在則插入
                result = laws_collection.update_one(
                    {'article_number': law_model.article_number},
                    {'$set': law_dict},
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
        logger.info(f"📊 {db_name.upper()} 資料庫法條插入統計:")
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
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 初始化法條時發生錯誤 ({db_name}): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def init_questions_to_db(client, db_name=None):
    """
    預先生成題目到資料庫
    生成選擇題 40 題 + 簡答題 40 題
    
    Args:
        client: MongoDB client
        db_name: 資料庫名稱 (用於 log)
    
    Returns:
        bool: 是否成功
    """
    try:
        db = client.get_database()
        laws_collection = db['laws']
        questions_collection = db['questions']
        
        # 取得所有法條
        all_laws = list(laws_collection.find({}, {"_id": 1, "content": 1, "article_number": 1}))
        
        if not all_laws:
            logger.error(f"❌ {db_name} 資料庫中沒有法條，請先執行法條初始化")
            return False
        
        logger.info(f"找到 {len(all_laws)} 條法條，準備隨機選擇生成題目")
        
        # 獲取 API key
        api_key = os.environ.get('OPENROUTER_API_KEY')
        if not api_key:
            logger.error("❌ 缺少 OPENROUTER_API_KEY 環境變數，無法生成題目")
            return False
        
        # 初始化題目生成器
        question_gen = QuestionGenerator(api_key=api_key)
        
        # 生成選擇題 40 題
        logger.info("\n" + "=" * 60)
        logger.info("開始生成選擇題 (MCQ) 40 題...")
        logger.info("=" * 60)
        
        mcq_success = generate_questions_for_type(
            question_gen,
            all_laws,
            questions_collection,
            question_type="MCQ",
            count=40,
            db_name=db_name
        )
        
        # 生成簡答題 40 題
        logger.info("\n" + "=" * 60)
        logger.info("開始生成簡答題 (ShortAnswer) 40 題...")
        logger.info("=" * 60)
        
        sa_success = generate_questions_for_type(
            question_gen,
            all_laws,
            questions_collection,
            question_type="ShortAnswer",
            count=40,
            db_name=db_name
        )
        
        return mcq_success and sa_success
        
    except Exception as e:
        logger.error(f"❌ 生成題目時發生錯誤 ({db_name}): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def generate_questions_for_type(question_gen, all_laws, questions_collection, question_type, count, db_name):
    """
    為特定題型生成題目
    
    Args:
        question_gen: QuestionGenerator 實例
        all_laws: 所有法條列表
        questions_collection: 題目集合
        question_type: 題型 ("MCQ" 或 "ShortAnswer")
        count: 要生成的題目數量
        db_name: 資料庫名稱 (用於 log)
    
    Returns:
        bool: 是否成功
    """
    generated = 0
    errors = []
    
    # 隨機打亂法條順序
    shuffled_laws = random.sample(all_laws, len(all_laws))
    
    for law in shuffled_laws:
        if generated >= count:
            break
        
        law_id = str(law["_id"])
        
        try:
            # 取得此法條最近的題目（避免重複）
            recent = list(questions_collection.find(
                {"law_id": law_id, "type": question_type},
                {"content": 1}
            ).sort("_id", -1).limit(3))
            
            # 生成 1 題
            logger.info(f"[{generated + 1}/{count}] 正在為法條 {law['article_number']} 生成 {question_type} 題目...")
            
            new_questions = question_gen.generate_questions(
                law_content=law["content"],
                law_article_number=law["article_number"],
                question_type=question_type,
                recent_questions=recent,
                count=1
            )
            
            # 儲存到資料庫
            for q in new_questions:
                q["law_id"] = law_id
                q["is_deleted"] = False
                q["is_starred"] = False
                result = questions_collection.insert_one(q)
                logger.info(f"   ✅ 成功生成並儲存題目 (ID: {result.inserted_id})")
                generated += 1
                
                if generated >= count:
                    break
            
        except Exception as e:
            error_msg = f"為法條 {law.get('article_number', 'unknown')} 生成題目時發生錯誤: {str(e)}"
            logger.error(f"   ❌ {error_msg}")
            errors.append(error_msg)
            continue
    
    # 輸出統計結果
    logger.info("=" * 60)
    logger.info(f"📊 {db_name.upper()} 資料庫 {question_type} 題目生成統計:")
    logger.info(f"   ✅ 成功生成: {generated} 題")
    logger.info(f"   ❌ 錯誤: {len(errors)} 次")
    logger.info("=" * 60)
    
    if errors:
        logger.warning("錯誤詳情:")
        for error in errors[:5]:  # 只顯示前5個錯誤
            logger.warning(f"   {error}")
        if len(errors) > 5:
            logger.warning(f"   ... 還有 {len(errors) - 5} 個錯誤")
    
    # 驗證資料庫中的題目數量
    total_count = questions_collection.count_documents({"type": question_type, "is_deleted": False})
    logger.info(f"✅ {db_name} 資料庫目前共有 {total_count} 題 {question_type} 題目")
    
    return generated > 0


def init_database(mongo_uri, db_name, skip_laws=False, skip_questions=False):
    """
    初始化資料庫（法條 + 題目）
    
    Args:
        mongo_uri: MongoDB 連線字串
        db_name: 資料庫名稱
        skip_laws: 是否跳過法條初始化
        skip_questions: 是否跳過題目生成
    
    Returns:
        bool: 是否成功
    """
    try:
        # 連接資料庫
        logger.info(f"連接到 {db_name} MongoDB...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=10000)
        
        # 測試連線
        client.admin.command('ping')
        logger.info(f"✅ 成功連接到 {db_name} MongoDB")
        
        success = True
        
        # 初始化法條
        if not skip_laws:
            logger.info("\n" + "=" * 60)
            logger.info(f"步驟 1: 初始化法條到 {db_name} 資料庫")
            logger.info("=" * 60)
            laws_success = init_laws_to_db(client, db_name)
            success = success and laws_success
        else:
            logger.info(f"⏭️  跳過法條初始化 (--skip-laws)")
        
        # 生成題目
        if not skip_questions:
            logger.info("\n" + "=" * 60)
            logger.info(f"步驟 2: 生成題目到 {db_name} 資料庫")
            logger.info("=" * 60)
            questions_success = init_questions_to_db(client, db_name)
            success = success and questions_success
        else:
            logger.info(f"⏭️  跳過題目生成 (--skip-questions)")
        
        client.close()
        return success
        
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
        description='初始化資料庫（法條 + 題目）'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='初始化本地資料庫'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='初始化遠端資料庫'
    )
    parser.add_argument(
        '--both',
        action='store_true',
        help='初始化本地和遠端資料庫'
    )
    parser.add_argument(
        '--skip-laws',
        action='store_true',
        help='跳過法條初始化，只生成題目'
    )
    parser.add_argument(
        '--skip-questions',
        action='store_true',
        help='跳過題目生成，只初始化法條'
    )
    
    args = parser.parse_args()
    
    # 確保至少指定一個選項
    if not (args.local or args.remote or args.both):
        parser.print_help()
        logger.error("\n❌ 錯誤: 請指定 --local, --remote 或 --both")
        sys.exit(1)
    
    # 檢查是否同時跳過所有步驟
    if args.skip_laws and args.skip_questions:
        logger.error("❌ 錯誤: 不能同時指定 --skip-laws 和 --skip-questions")
        sys.exit(1)
    
    success = True
    
    # 初始化本地資料庫
    if args.local or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("🚀 開始初始化本地資料庫...")
        logger.info("=" * 60)
        local_success = init_database(
            LOCAL_MONGO_URI, 
            "local",
            skip_laws=args.skip_laws,
            skip_questions=args.skip_questions
        )
        success = success and local_success
    
    # 初始化遠端資料庫
    if args.remote or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("🚀 開始初始化遠端資料庫...")
        logger.info("=" * 60)
        remote_success = init_database(
            REMOTE_MONGO_URI, 
            "remote",
            skip_laws=args.skip_laws,
            skip_questions=args.skip_questions
        )
        success = success and remote_success
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ 所有操作成功完成!")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("❌ 某些操作失敗，請檢查錯誤訊息")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
