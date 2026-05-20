#!/usr/bin/env python3
"""
專利審查基準題目批次生成腳本
Generate questions for Patent Examination Guidelines

使用方法：
1. 測試模式（生成 5 題）：
   python scripts/generate_examination_questions.py --test

2. 完整生成（生成 200 題）：
   python scripts/generate_examination_questions.py

3. 自訂數量：
   python scripts/generate_examination_questions.py --count 50
"""

import os
import sys
import logging
import argparse
from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.question_gen import QuestionGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


def get_examination_law_type_id(db):
    """獲取專利審查基準的 law_type ID"""
    law_type = db.law_types.find_one({'slug': 'examination'})
    if not law_type:
        logger.error("❌ 找不到 slug='examination' 的法規類型")
        logger.error("   請先執行: python scripts/init_law_types_remote.py")
        sys.exit(1)
    return law_type['_id']


def get_examination_laws(db, limit=None):
    """
    獲取專利審查基準的法條列表
    
    Args:
        db: MongoDB database instance
        limit: 限制法條數量（用於測試）
    
    Returns:
        list: 法條列表
    """
    query = {'type': 'patent-examination', 'lang': 'zh-TW'}
    
    if limit:
        laws = list(db.laws.find(query).limit(limit))
    else:
        laws = list(db.laws.find(query))
    
    logger.info(f"找到 {len(laws)} 條專利審查基準法條")
    return laws


def generate_questions_for_examination(
    generator: QuestionGenerator,
    db,
    law_type_id,
    count: int = 200,
    questions_per_law: int = 2
):
    """
    為專利審查基準生成題目
    
    Args:
        generator: QuestionGenerator 實例
        db: MongoDB database instance
        law_type_id: 專利審查基準的 law_type ObjectId
        count: 總共要生成的題目數量
        questions_per_law: 每條法條生成的題目數量
    
    Returns:
        int: 成功生成的題目數量
    """
    logger.info("=" * 80)
    logger.info(f"開始為專利審查基準生成題目（目標: {count} 題）")
    logger.info("=" * 80)
    
    # 獲取法條列表
    laws = get_examination_laws(db)
    
    if not laws:
        logger.error("❌ 找不到任何專利審查基準法條")
        logger.error("   請先執行: python scripts/init_examination_guidelines.py --remote")
        return 0
    
    generated_count = 0
    error_count = 0
    
    logger.info(f"\n開始生成題目...")
    logger.info(f"法條總數: {len(laws)}")
    logger.info(f"每條法條生成: {questions_per_law} 題")
    logger.info(f"預計總題數: {min(len(laws) * questions_per_law, count)}\n")
    
    for idx, law in enumerate(laws, 1):
        # 檢查是否已達到目標數量
        if generated_count >= count:
            logger.info(f"✅ 已達到目標數量 {count} 題，停止生成")
            break
        
        law_id = str(law['_id'])
        article_number = law.get('article_number', 'N/A')
        content = law.get('content', '')
        
        # 計算這條法條要生成幾題
        to_generate = min(questions_per_law, count - generated_count)
        
        logger.info("-" * 80)
        logger.info(f"[{idx}/{len(laws)}] 處理: {article_number}")
        logger.info(f"         內容: {content[:80]}...")
        
        # 檢查這條法條已有的題目數量
        existing_count = db.questions.count_documents({
            'law_id': law_id,
            'is_deleted': False
        })
        
        if existing_count >= questions_per_law:
            logger.info(f"         ⏭️  已有 {existing_count} 題，跳過")
            continue
        
        # 獲取最近的題目以避免重複
        recent_questions = list(db.questions.find(
            {'law_id': law_id, 'is_deleted': False},
            {'content': 1}
        ).limit(10))
        
        # 交替生成 MCQ 和 ShortAnswer
        for q_idx in range(to_generate):
            question_type = "MCQ" if (generated_count + q_idx) % 2 == 0 else "ShortAnswer"
            
            try:
                logger.info(f"         生成第 {existing_count + q_idx + 1} 題 ({question_type})...")
                
                # 生成題目
                questions = generator.generate_questions(
                    law_content=content,
                    law_article_number=article_number,
                    question_type=question_type,
                    recent_questions=recent_questions,
                    count=1,
                    law_type='patent-examination',
                    law_name='專利審查基準'
                )
                
                if not questions:
                    logger.warning(f"         ⚠️  生成失敗（無返回結果）")
                    error_count += 1
                    continue
                
                # 插入題目到資料庫
                for question in questions:
                    question_doc = {
                        'law_id': law_id,
                        'law_type': law_type_id,  # 設定正確的 law_type
                        'type': question['type'],
                        'content': question['content'],
                        'options': question.get('options'),
                        'correct_answer': question['correct_answer'],
                        'ai_explanation': question['ai_explanation'],
                        'lang': 'zh-TW',
                        'is_deleted': False,
                        'created_at': datetime.utcnow()
                    }
                    
                    result = db.questions.insert_one(question_doc)
                    logger.info(f"         ✅ 題目已插入 (ID: {result.inserted_id})")
                    generated_count += 1
                    
                    # 更新 recent_questions
                    recent_questions.append({'content': question['content']})
                    if len(recent_questions) > 10:
                        recent_questions.pop(0)
                
            except Exception as e:
                logger.error(f"         ❌ 生成題目時發生錯誤: {e}")
                error_count += 1
                continue
        
        # 每 10 條法條顯示一次進度
        if idx % 10 == 0:
            logger.info(f"\n📊 進度報告: 已處理 {idx}/{len(laws)} 條法條，生成 {generated_count} 題\n")
    
    # 最終統計
    logger.info("=" * 80)
    logger.info("生成完成！")
    logger.info("=" * 80)
    logger.info(f"✅ 成功生成: {generated_count} 題")
    logger.info(f"❌ 錯誤: {error_count} 次")
    logger.info(f"📝 處理法條: {idx}/{len(laws)} 條")
    logger.info("=" * 80)
    
    return generated_count


def main():
    parser = argparse.ArgumentParser(
        description='為專利審查基準批次生成題目'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='測試模式：只生成 5 題'
    )
    parser.add_argument(
        '--count',
        type=int,
        default=200,
        help='要生成的題目數量（預設: 200）'
    )
    
    args = parser.parse_args()
    
    # 測試模式
    if args.test:
        count = 5
        logger.info("🧪 測試模式：只生成 5 題")
    else:
        count = args.count
    
    # 連接遠端資料庫
    remote_uri = os.getenv('REMOTE_MONGO_URI')
    if not remote_uri:
        logger.error("❌ 錯誤: 找不到 REMOTE_MONGO_URI 環境變數")
        logger.error("   請在 .env 檔案中設定 REMOTE_MONGO_URI")
        sys.exit(1)
    
    logger.info("🌐 連接遠端資料庫...")
    try:
        client = MongoClient(remote_uri, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        logger.info("✅ 成功連接到遠端資料庫\n")
    except Exception as e:
        logger.error(f"❌ 無法連接到遠端資料庫: {e}")
        sys.exit(1)
    
    db = client.get_database()
    
    # 獲取 OpenRouter API Key
    api_key = os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        logger.error("❌ 錯誤: 找不到 OPENROUTER_API_KEY 環境變數")
        logger.error("   請在 .env 檔案中設定 OPENROUTER_API_KEY")
        sys.exit(1)
    
    # 初始化題目生成器
    logger.info("🤖 初始化 AI 題目生成器...")
    generator = QuestionGenerator(api_key=api_key)
    
    # 獲取專利審查基準的 law_type ID
    law_type_id = get_examination_law_type_id(db)
    logger.info(f"✅ 專利審查基準 law_type ID: {law_type_id}\n")
    
    # 生成題目
    try:
        generated = generate_questions_for_examination(
            generator=generator,
            db=db,
            law_type_id=law_type_id,
            count=count,
            questions_per_law=2  # 每條法條生成 2 題
        )
        
        if generated > 0:
            logger.info(f"\n✅ 成功完成！共生成 {generated} 題")
            
            if args.test:
                logger.info("\n💡 測試成功！執行完整生成:")
                logger.info("   python scripts/generate_examination_questions.py")
        else:
            logger.warning("\n⚠️  沒有生成任何題目")
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  用戶中斷執行")
    except Exception as e:
        logger.error(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        client.close()


if __name__ == '__main__':
    main()
