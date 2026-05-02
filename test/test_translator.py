#!/usr/bin/env python3
"""
Test script for Translator Service - validates translation and bilingual generation.

Usage:
    python test/test_translator.py --local     # Test with local MongoDB
    python test/test_translator.py --remote    # Test with remote MongoDB
"""

import os
import sys
import argparse
import logging
import json
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.translator import Translator
from db.models import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB configuration
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def test_translator_service(mongo_uri, db_name="local"):
    """Test translator service with real data."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing Translator Service on {db_name.upper()} Database")
    logger.info(f"{'='*60}")
    
    try:
        # Connect to database
        client = MongoClient(mongo_uri)
        db = client.get_database()
        
        # Initialize translator
        translator = Translator()
        
        # Test 1: Get a sample question to translate
        logger.info("\n[Test 1] Fetching sample zh-TW question from database...")
        sample_question = db['questions'].find_one({
            '$or': [
                {'lang': 'zh-TW'},
                {'lang': {'$exists': False}}  # Old questions default to zh-TW
            ]
        })
        
        if not sample_question:
            logger.warning("⚠️  No zh-TW questions found in database. Skipping translation test.")
        else:
            logger.info(f"✅ Found sample question:")
            logger.info(f"   Content: {sample_question.get('content', '')[:60]}...")
            logger.info(f"   Type: {sample_question.get('type', 'unknown')}")
            
            # Test 2: Translate the sample question
            logger.info("\n[Test 2] Translating sample question to English...")
            try:
                translated = translator.translate_question_to_en(sample_question)
                logger.info("✅ Translation successful!")
                logger.info(f"   Original (zh-TW): {sample_question.get('content', '')[:50]}...")
                logger.info(f"   Translated (en): {translated.get('content', '')[:50]}...")
                logger.info(f"   Translation lang: {translated.get('lang')}")
                logger.info(f"   Translation type: {translated.get('type')}")
            except Exception as e:
                logger.error(f"❌ Translation failed: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # Test 3: Get bilingual law articles and test bilingual generation
        logger.info("\n[Test 3] Testing bilingual question generation...")
        
        # Find a law article that exists in both languages
        zh_tw_law = db['laws'].find_one({'lang': 'zh-TW'})
        if not zh_tw_law:
            logger.warning("⚠️  No zh-TW law found. Trying to find any law...")
            zh_tw_law = db['laws'].find_one({'lang': {'$exists': False}})
        
        if zh_tw_law:
            logger.info(f"   Found zh-TW law: {zh_tw_law.get('article_number')} (ID: {str(zh_tw_law.get('_id'))})")
            
            # Try to find the English version via i18n mapping
            zh_tw_id_str = str(zh_tw_law.get('_id'))
            mapping = db['i18n_mapping'].find_one({
                'zh_tw_law_id': zh_tw_id_str
            })
            
            logger.info(f"   Searching for mapping with zh_tw_law_id: {zh_tw_id_str}")
            
            if mapping:
                logger.info(f"   ✅ Found mapping: {mapping}")
                en_law = db['laws'].find_one({
                    '_id': ObjectId(mapping.get('en_law_id')),
                    'lang': 'en'
                })
                
                if en_law:
                    logger.info(f"✅ Found bilingual law pair")
                    logger.info(f"   Article (zh-TW): {zh_tw_law.get('article_number')}")
                    logger.info(f"   Article (en): {en_law.get('article_number')}")
                    
                    try:
                        logger.info("\n   Generating bilingual MCQ question pair...")
                        pairs = translator.generate_bilingual_question(
                            law_content_zh=zh_tw_law.get('content', ''),
                            law_content_en=en_law.get('content', ''),
                            law_article_number=zh_tw_law.get('article_number', ''),
                            question_type="MCQ",
                            count=1
                        )
                        
                        logger.info(f"✅ Generated {len(pairs)} bilingual question pair(s)!")
                        
                        for idx, (zh_tw_q, en_q) in enumerate(pairs, 1):
                            logger.info(f"\n   Pair {idx}:")
                            logger.info(f"      zh-TW Question: {zh_tw_q.get('content', '')[:50]}...")
                            logger.info(f"      EN Question: {en_q.get('content', '')[:50]}...")
                            logger.info(f"      Shared base_question_id: {zh_tw_q.get('base_question_id')}")
                            logger.info(f"      zh-TW lang: {zh_tw_q.get('lang')}")
                            logger.info(f"      EN lang: {en_q.get('lang')}")
                            logger.info(f"      Same base_id? {zh_tw_q.get('base_question_id') == en_q.get('base_question_id')}")
                    
                    except Exception as e:
                        logger.error(f"❌ Bilingual generation failed: {str(e)}")
                        import traceback
                        traceback.print_exc()
                else:
                    logger.warning(f"⚠️  English version of law not found (ObjectId: {mapping.get('en_law_id')})")
            else:
                logger.warning(f"⚠️  No i18n mapping found for zh-TW law {zh_tw_id_str}")
        else:
            logger.warning("⚠️  No laws found in database")
        
        client.close()
        logger.info(f"\n{'='*60}")
        logger.info("✅ Translator service tests completed!")
        logger.info(f"{'='*60}\n")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main program"""
    parser = argparse.ArgumentParser(
        description='Test Translator Service'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='Test with local database'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='Test with remote database'
    )
    
    args = parser.parse_args()
    
    # Default to local if no option specified
    if not args.local and not args.remote:
        args.local = True
    
    success = True
    
    if args.local:
        test_translator_service(LOCAL_MONGO_URI, "local")
    
    if args.remote:
        if not REMOTE_MONGO_URI:
            logger.error("❌ REMOTE_MONGO_URI not configured")
            sys.exit(1)
        test_translator_service(REMOTE_MONGO_URI, "remote")


if __name__ == '__main__':
    main()
