#!/usr/bin/env python3
"""
Remote Question Generation Script
遠端題目生成腳本 - 支持本地和遠端資料庫

使用方法：
1. 本地資料庫生成（測試）：
   python scripts/generate_questions_remote.py --test

2. 遠端資料庫生成（Heroku）：
   export HEROKU_MONGO_URI="mongodb+srv://..."
   python scripts/generate_questions_remote.py --remote --test

3. 遠端完整生成：
   python scripts/generate_questions_remote.py --remote

生成規則：
- 專利法（patent-act）：100題雙語配對（中文 + 英文）
- 訴願法（administrative-appeal）：200題中文
- 行政訴訟法（administrative-litigation）：200題中文
- 審查基準（examination-guidelines）：200題中文（如果有資料）
"""
import os
import sys
import logging
import argparse
from datetime import datetime
from pymongo import MongoClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.question_gen import QuestionGenerator
from bson import ObjectId

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_connection(remote=False):
    """
    獲取資料庫連接
    
    Args:
        remote: 是否連接遠端資料庫
        
    Returns:
        tuple: (db, laws_collection, questions_collection)
    """
    if remote:
        # 連接遠端資料庫（Heroku）
        mongo_uri = os.environ.get('HEROKU_MONGO_URI') or os.environ.get('MONGO_URI')
        if not mongo_uri:
            logger.error("❌ 錯誤: HEROKU_MONGO_URI 或 MONGO_URI 未設定")
            logger.info("\n請設定環境變數:")
            logger.info("  export HEROKU_MONGO_URI='你的MongoDB URI'")
            logger.info("\n或從 Heroku 取得:")
            logger.info("  heroku config:get MONGO_URI")
            sys.exit(1)
        
        logger.info(f"🌐 連接遠端資料庫...")
        client = MongoClient(mongo_uri)
        db = client.get_default_database()
        logger.info(f"✓ 已連接到遠端資料庫: {db.name}")
    else:
        # 連接本地資料庫
        from db.models import db, laws_collection, questions_collection
        logger.info(f"💻 使用本地資料庫: {db.db.name}")
        return db.db, db.db['laws'], db.db['questions']
    
    return db, db['laws'], db['questions']


def extract_article_number(article_str):
    """提取法條編號中的數字"""
    import re
    match = re.search(r'\d+', str(article_str))
    return match.group(0) if match else None


def get_laws_by_type(laws_collection, law_type: str, lang: str = None):
    """獲取指定類型的法條列表"""
    filter_query = {"type": law_type}
    if lang:
        filter_query["lang"] = lang
    
    laws = list(laws_collection.find(filter_query, {
        "_id": 1,
        "content": 1,
        "article_number": 1,
        "lang": 1
    }))
    return laws


def generate_bilingual_questions_for_patent_act(
    generator: QuestionGenerator,
    laws_collection,
    questions_collection,
    count: int = 100
):
    """
    為專利法生成雙語配對題目
    
    Args:
        generator: QuestionGenerator 實例
        laws_collection: 法條集合
        questions_collection: 題目集合
        count: 要生成的題目對數
    
    Returns:
        生成的題目對數
    """
    logger.info(f"開始生成專利法雙語題目：{count} 對")
    
    # 獲取中文和英文法條
    laws_zh = get_laws_by_type(laws_collection, "patent-act", "zh-TW")
    laws_en = get_laws_by_type(laws_collection, "patent-act", "en")
    
    if not laws_zh or not laws_en:
        logger.error("找不到專利法的中英文法條")
        return 0
    
    # 建立法條對應關係（通過提取數字來匹配）
    laws_zh_map = {}
    for law in laws_zh:
        num = extract_article_number(law["article_number"])
        if num:
            laws_zh_map[num] = law
    
    laws_en_map = {}
    for law in laws_en:
        num = extract_article_number(law["article_number"])
        if num:
            laws_en_map[num] = law
    
    # 找出同時有中英文的法條
    common_articles = set(laws_zh_map.keys()) & set(laws_en_map.keys())
    
    if not common_articles:
        logger.error("找不到同時有中英文的法條")
        return 0
    
    logger.info(f"找到 {len(common_articles)} 條有中英文對照的法條")
    
    # 計算每條法條要生成多少題
    questions_per_law = max(1, count // len(common_articles))
    generated_pairs = 0
    
    # 按數字排序
    for article_num in sorted(common_articles, key=lambda x: int(x)):
        if generated_pairs >= count:
            break
        
        law_zh = laws_zh_map[article_num]
        law_en = laws_en_map[article_num]
        
        to_generate = min(questions_per_law, count - generated_pairs)
        
        # 獲取最近的題目以避免重複
        recent_zh = list(questions_collection.find(
            {"law_id": str(law_zh["_id"]), "lang": "zh-TW"},
            {"content": 1}
        ).limit(3))
        
        recent_en = list(questions_collection.find(
            {"law_id": str(law_en["_id"]), "lang": "en"},
            {"content": 1}
        ).limit(3))
        
        # 交替生成 MCQ 和 ShortAnswer
        question_type = "MCQ" if generated_pairs % 2 == 0 else "ShortAnswer"
        
        try:
            logger.info(f"生成第 {law_zh['article_number']} 條的 {question_type} 題目 ({to_generate} 對)")
            
            # 生成雙語題目對
            question_pairs = generator.generate_bilingual_questions(
                law_content_zh=law_zh["content"],
                law_content_en=law_en["content"],
                law_article_number=law_zh["article_number"],
                question_type=question_type,
                recent_questions_zh=recent_zh,
                recent_questions_en=recent_en,
                count=to_generate
            )
            
            # 儲存到資料庫
            for zh_q, en_q in question_pairs:
                # 儲存中文題目
                zh_q["law_id"] = str(law_zh["_id"])
                zh_q["is_deleted"] = False
                zh_q["lang"] = "zh-TW"
                result_zh = questions_collection.insert_one(zh_q)
                
                # 儲存英文題目
                en_q["law_id"] = str(law_en["_id"])
                en_q["is_deleted"] = False
                en_q["lang"] = "en"
                en_q["paired_question_id"] = str(result_zh.inserted_id)
                result_en = questions_collection.insert_one(en_q)
                
                # 更新中文題目的配對 ID
                questions_collection.update_one(
                    {"_id": result_zh.inserted_id},
                    {"$set": {"paired_question_id": str(result_en.inserted_id)}}
                )
                
                generated_pairs += 1
                logger.info(f"✓ 已生成第 {generated_pairs}/{count} 對題目")
                
        except Exception as e:
            logger.error(f"生成第 {law_zh['article_number']} 條的題目時發生錯誤: {e}")
            continue
    
    logger.info(f"專利法雙語題目生成完成：共 {generated_pairs} 對（{generated_pairs * 2} 題）")
    return generated_pairs


def generate_monolingual_questions(
    generator: QuestionGenerator,
    laws_collection,
    questions_collection,
    law_type: str,
    law_type_name: str,
    count: int = 200
):
    """
    為單語法律生成題目（僅中文）
    
    Args:
        generator: QuestionGenerator 實例
        laws_collection: 法條集合
        questions_collection: 題目集合
        law_type: 法律類型代碼
        law_type_name: 法律類型名稱
        count: 要生成的題目數量
    
    Returns:
        生成的題目數量
    """
    logger.info(f"開始生成{law_type_name}中文題目：{count} 題")
    
    # 獲取中文法條
    laws = get_laws_by_type(laws_collection, law_type, "zh-TW")
    
    if not laws:
        logger.error(f"找不到{law_type_name}的中文法條")
        return 0
    
    logger.info(f"找到 {len(laws)} 條{law_type_name}法條")
    
    # 計算每條法條要生成多少題
    questions_per_law = max(1, count // len(laws))
    generated_count = 0
    
    for law in laws:
        if generated_count >= count:
            break
        
        to_generate = min(questions_per_law, count - generated_count)
        
        # 獲取最近的題目以避免重複
        recent = list(questions_collection.find(
            {"law_id": str(law["_id"])},
            {"content": 1}
        ).limit(3))
        
        # 交替生成 MCQ 和 ShortAnswer
        question_type = "MCQ" if generated_count % 2 == 0 else "ShortAnswer"
        
        try:
            logger.info(f"生成第 {law['article_number']} 條的 {question_type} 題目 ({to_generate} 題)")
            
            # 生成題目
            questions = generator.generate_questions(
                law_content=law["content"],
                law_article_number=law["article_number"],
                question_type=question_type,
                recent_questions=recent,
                count=to_generate
            )
            
            # 儲存到資料庫
            for q in questions:
                q["law_id"] = str(law["_id"])
                q["is_deleted"] = False
                q["lang"] = "zh-TW"
                questions_collection.insert_one(q)
                generated_count += 1
                logger.info(f"✓ 已生成第 {generated_count}/{count} 題")
                
        except Exception as e:
            logger.error(f"生成第 {law['article_number']} 條的題目時發生錯誤: {e}")
            continue
    
    logger.info(f"{law_type_name}題目生成完成：共 {generated_count} 題")
    return generated_count


def main():
    """主函數"""
    # 解析命令列參數
    parser = argparse.ArgumentParser(description='批量生成題目（支持本地和遠端資料庫）')
    parser.add_argument('--remote', action='store_true', help='連接遠端資料庫（Heroku）')
    parser.add_argument('--test', action='store_true', help='測試模式（每種法律生成5題）')
    args = parser.parse_args()
    
    start_time = datetime.now()
    logger.info("=" * 60)
    mode_text = "遠端" if args.remote else "本地"
    count_text = "測試模式（每種法律 5 題）" if args.test else "完整模式"
    logger.info(f"開始批量生成題目 - {mode_text}資料庫 - {count_text}")
    logger.info("=" * 60)
    
    # 檢查 API Key
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        logger.error("未設定 OPENROUTER_API_KEY 環境變數")
        sys.exit(1)
    
    # 連接資料庫
    db, laws_collection, questions_collection = get_database_connection(remote=args.remote)
    
    # 初始化生成器
    generator = QuestionGenerator(api_key=api_key)
    
    # 設定生成數量
    if args.test:
        patent_count = 5
        other_count = 5
    else:
        patent_count = 100
        other_count = 200
    
    # 統計結果
    results = {
        "patent-act": {"zh-TW": 0, "en": 0},
        "administrative-appeal": {"zh-TW": 0},
        "administrative-litigation": {"zh-TW": 0},
        "examination-guidelines": {"zh-TW": 0}
    }
    
    # 1. 生成專利法雙語題目
    logger.info("\n" + "=" * 60)
    logger.info(f"任務 1/4：專利法雙語題目（{patent_count} 對）")
    logger.info("=" * 60)
    pairs = generate_bilingual_questions_for_patent_act(
        generator,
        laws_collection,
        questions_collection,
        count=patent_count
    )
    results["patent-act"]["zh-TW"] = pairs
    results["patent-act"]["en"] = pairs
    
    # 2. 生成訴願法題目
    logger.info("\n" + "=" * 60)
    logger.info(f"任務 2/4：訴願法中文題目（{other_count} 題）")
    logger.info("=" * 60)
    count = generate_monolingual_questions(
        generator,
        laws_collection,
        questions_collection,
        law_type="administrative-appeal",
        law_type_name="訴願法",
        count=other_count
    )
    results["administrative-appeal"]["zh-TW"] = count
    
    # 3. 生成行政訴訟法題目
    logger.info("\n" + "=" * 60)
    logger.info(f"任務 3/4：行政訴訟法中文題目（{other_count} 題）")
    logger.info("=" * 60)
    count = generate_monolingual_questions(
        generator,
        laws_collection,
        questions_collection,
        law_type="administrative-litigation",
        law_type_name="行政訴訟法",
        count=other_count
    )
    results["administrative-litigation"]["zh-TW"] = count
    
    # 4. 生成審查基準題目（檢查是否有資料）
    logger.info("\n" + "=" * 60)
    logger.info(f"任務 4/4：審查基準中文題目（{other_count} 題）")
    logger.info("=" * 60)
    
    exam_count = laws_collection.count_documents({"type": "examination-guidelines"})
    if exam_count == 0:
        logger.warning("⚠️  審查基準資料庫中尚無法條資料，跳過生成")
        results["examination-guidelines"]["zh-TW"] = 0
    else:
        count = generate_monolingual_questions(
            generator,
            laws_collection,
            questions_collection,
            law_type="examination-guidelines",
            law_type_name="審查基準",
            count=other_count
        )
        results["examination-guidelines"]["zh-TW"] = count
    
    # 顯示結果摘要
    end_time = datetime.now()
    duration = end_time - start_time
    
    logger.info("\n" + "=" * 60)
    logger.info(f"批量生成完成！（{mode_text}資料庫 - {count_text}）")
    logger.info("=" * 60)
    logger.info(f"專利法：中文 {results['patent-act']['zh-TW']} 題 + 英文 {results['patent-act']['en']} 題 = {results['patent-act']['zh-TW'] + results['patent-act']['en']} 題")
    logger.info(f"訴願法：中文 {results['administrative-appeal']['zh-TW']} 題")
    logger.info(f"行政訴訟法：中文 {results['administrative-litigation']['zh-TW']} 題")
    logger.info(f"審查基準：中文 {results['examination-guidelines']['zh-TW']} 題")
    total = sum([results[k].get('zh-TW', 0) + results[k].get('en', 0) for k in results])
    logger.info(f"總計：{total} 題")
    logger.info(f"耗時：{duration}")
    logger.info("=" * 60)
    
    if args.test and not args.remote:
        logger.info("\n✓ 本地測試成功！執行完整生成：")
        logger.info("  python scripts/generate_questions_remote.py")
        logger.info("\n或執行遠端生成：")
        logger.info("  export HEROKU_MONGO_URI='你的MongoDB URI'")
        logger.info("  python scripts/generate_questions_remote.py --remote --test")


if __name__ == "__main__":
    main()
