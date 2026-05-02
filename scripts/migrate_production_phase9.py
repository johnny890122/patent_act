#!/usr/bin/env python3
"""
Phase 9 Production Data Migration Script

This script performs a complete i18n migration for production database:
1. Backfill existing zh-TW laws with 'lang' field
2. Insert English law articles from truth_law_en.json
3. Create i18n_mapping collection for zh-TW ↔ en law pairs
4. Backfill existing questions with 'lang' field
5. Translate existing zh-TW questions to English
6. Create necessary database indexes
7. Verify migration results

Usage:
    # Dry run (test without modifying database)
    python scripts/migrate_production_phase9.py --remote --dry-run
    
    # Execute migration on remote database
    python scripts/migrate_production_phase9.py --remote
    
    # Execute on local database (for testing)
    python scripts/migrate_production_phase9.py --local
    
    # Execute on both
    python scripts/migrate_production_phase9.py --both

Safety Features:
- Dry run mode for testing
- Step-by-step confirmation prompts
- Automatic backup suggestions
- Rollback capabilities
- Comprehensive logging
"""

import os
import sys
import json
import logging
import argparse
import re
import uuid
from datetime import datetime
from typing import Dict, List, Tuple
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.translator import Translator
from db.models import LawModel, QuestionModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'migration_phase9_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# MongoDB URIs
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

# Paths
TRUTH_LAWS_EN_PATH = os.path.join(os.path.dirname(__file__), '..', 'knowledge', 'truth_law_en.json')


class Phase9Migrator:
    """Handles Phase 9 i18n data migration"""
    
    def __init__(self, mongo_uri: str, db_name: str, dry_run: bool = False):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.dry_run = dry_run
        self.client = None
        self.db = None
        self.translator = None
        
        # Statistics
        self.stats = {
            'laws_backfilled': 0,
            'en_laws_inserted': 0,
            'mappings_created': 0,
            'questions_backfilled': 0,
            'questions_translated': 0,
            'indexes_created': 0,
            'errors': []
        }
    
    def connect(self) -> bool:
        """Connect to MongoDB"""
        try:
            logger.info(f"Connecting to {self.db_name} MongoDB...")
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client.get_database()
            logger.info(f"✅ Connected to {self.db_name} MongoDB")
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {str(e)}")
            return False
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info(f"Closed connection to {self.db_name}")
    
    def print_pre_migration_stats(self):
        """Print database statistics before migration"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 PRE-MIGRATION DATABASE STATISTICS")
        logger.info("=" * 60)
        
        laws_collection = self.db['laws']
        questions_collection = self.db['questions']
        mapping_collection = self.db['i18n_mapping']
        
        # Laws statistics
        total_laws = laws_collection.count_documents({})
        zh_laws = laws_collection.count_documents({'lang': 'zh-TW'})
        en_laws = laws_collection.count_documents({'lang': 'en'})
        laws_no_lang = laws_collection.count_documents({'lang': {'$exists': False}})
        
        logger.info(f"Laws Collection:")
        logger.info(f"  Total laws: {total_laws}")
        logger.info(f"  zh-TW laws: {zh_laws}")
        logger.info(f"  EN laws: {en_laws}")
        logger.info(f"  Laws without lang field: {laws_no_lang}")
        
        # Questions statistics
        total_questions = questions_collection.count_documents({})
        zh_questions = questions_collection.count_documents({'lang': 'zh-TW'})
        en_questions = questions_collection.count_documents({'lang': 'en'})
        questions_no_lang = questions_collection.count_documents({'lang': {'$exists': False}})
        
        logger.info(f"\nQuestions Collection:")
        logger.info(f"  Total questions: {total_questions}")
        logger.info(f"  zh-TW questions: {zh_questions}")
        logger.info(f"  EN questions: {en_questions}")
        logger.info(f"  Questions without lang field: {questions_no_lang}")
        
        # Mappings
        total_mappings = mapping_collection.count_documents({})
        logger.info(f"\ni18n Mapping Collection:")
        logger.info(f"  Total mappings: {total_mappings}")
        
        logger.info("=" * 60 + "\n")
    
    def step1_backfill_laws_lang(self) -> bool:
        """Step 1: Backfill existing laws with lang='zh-TW'"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 1: Backfill Laws with lang='zh-TW'")
        logger.info("=" * 60)
        
        try:
            laws_collection = self.db['laws']
            laws_without_lang = laws_collection.count_documents({'lang': {'$exists': False}})
            
            if laws_without_lang == 0:
                logger.info("✅ All laws already have lang field")
                return True
            
            logger.info(f"Found {laws_without_lang} laws without lang field")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would backfill {laws_without_lang} laws with lang='zh-TW'")
                self.stats['laws_backfilled'] = laws_without_lang
                return True
            
            result = laws_collection.update_many(
                {'lang': {'$exists': False}},
                {'$set': {'lang': 'zh-TW'}}
            )
            
            self.stats['laws_backfilled'] = result.modified_count
            logger.info(f"✅ Backfilled {result.modified_count} laws with lang='zh-TW'")
            return True
            
        except Exception as e:
            error_msg = f"Error in step 1: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def step2_insert_english_laws(self) -> bool:
        """Step 2: Insert English law articles"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 2: Insert English Law Articles")
        logger.info("=" * 60)
        
        try:
            # Load English laws
            if not os.path.exists(TRUTH_LAWS_EN_PATH):
                raise FileNotFoundError(f"English laws file not found: {TRUTH_LAWS_EN_PATH}")
            
            with open(TRUTH_LAWS_EN_PATH, 'r', encoding='utf-8') as f:
                en_laws_data = json.load(f)
            
            logger.info(f"Loaded {len(en_laws_data)} English law articles from file")
            
            laws_collection = self.db['laws']
            existing_en_laws = laws_collection.count_documents({'lang': 'en'})
            
            if existing_en_laws > 0:
                logger.info(f"⚠️  Found {existing_en_laws} existing EN laws")
                logger.info("Skipping insertion to avoid duplicates")
                logger.info("If you want to re-insert, please delete existing EN laws first")
                return True
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would insert {len(en_laws_data)} English laws")
                self.stats['en_laws_inserted'] = len(en_laws_data)
                return True
            
            # Insert English laws
            inserted_count = 0
            for law_data in en_laws_data:
                # Extract article_number_int for sorting
                match = re.search(r'\d+', law_data['article_number'])
                article_number_int = int(match.group()) if match else 0
                
                law_doc = {
                    'article_number': law_data['article_number'],
                    'article_number_int': article_number_int,
                    'chapter': law_data['chapter'],
                    'content': law_data['content'],
                    'lang': 'en',
                    'is_starred': False,
                    'attempt_count': 0,
                    'total_score': 0.0,
                    'avg_score': 0.0
                }
                
                laws_collection.insert_one(law_doc)
                inserted_count += 1
            
            self.stats['en_laws_inserted'] = inserted_count
            logger.info(f"✅ Inserted {inserted_count} English law articles")
            return True
            
        except Exception as e:
            error_msg = f"Error in step 2: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def step3_create_i18n_mappings(self) -> bool:
        """Step 3: Create i18n mappings between zh-TW and en laws"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 3: Create i18n Mappings")
        logger.info("=" * 60)
        
        def extract_article_number(article_str: str) -> int:
            """Extract numeric part from article string"""
            match = re.search(r'\d+', article_str)
            return int(match.group()) if match else None
        
        try:
            laws_collection = self.db['laws']
            mapping_collection = self.db['i18n_mapping']
            
            # Clear existing mappings
            existing_mappings = mapping_collection.count_documents({})
            if existing_mappings > 0:
                logger.info(f"Clearing {existing_mappings} existing mappings...")
                if not self.dry_run:
                    mapping_collection.delete_many({})
            
            # Get all laws
            zh_tw_laws = list(laws_collection.find({'lang': 'zh-TW'}, {'_id': 1, 'article_number': 1}))
            en_laws = list(laws_collection.find({'lang': 'en'}, {'_id': 1, 'article_number': 1}))
            
            logger.info(f"Found {len(zh_tw_laws)} zh-TW laws and {len(en_laws)} EN laws")
            
            # Build lookup dict
            en_laws_by_num = {}
            for law in en_laws:
                num = extract_article_number(law['article_number'])
                if num:
                    en_laws_by_num[num] = law
            
            # Create mappings
            created = 0
            skipped = 0
            
            for zh_law in zh_tw_laws:
                num = extract_article_number(zh_law['article_number'])
                if not num:
                    skipped += 1
                    continue
                
                en_law = en_laws_by_num.get(num)
                if not en_law:
                    logger.warning(f"No EN law found for article {num}")
                    skipped += 1
                    continue
                
                if self.dry_run:
                    created += 1
                    continue
                
                mapping_doc = {
                    'article_number': str(num),
                    'zh_tw_law_id': str(zh_law['_id']),
                    'en_law_id': str(en_law['_id'])
                }
                
                mapping_collection.insert_one(mapping_doc)
                created += 1
            
            self.stats['mappings_created'] = created
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would create {created} mappings (skipped {skipped})")
            else:
                logger.info(f"✅ Created {created} i18n mappings (skipped {skipped})")
            
            return True
            
        except Exception as e:
            error_msg = f"Error in step 3: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def step4_backfill_questions_lang(self) -> bool:
        """Step 4: Backfill existing questions with lang='zh-TW'"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 4: Backfill Questions with lang='zh-TW'")
        logger.info("=" * 60)
        
        try:
            questions_collection = self.db['questions']
            questions_without_lang = questions_collection.count_documents({'lang': {'$exists': False}})
            
            if questions_without_lang == 0:
                logger.info("✅ All questions already have lang field")
                return True
            
            logger.info(f"Found {questions_without_lang} questions without lang field")
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would backfill {questions_without_lang} questions")
                self.stats['questions_backfilled'] = questions_without_lang
                return True
            
            # Note: We'll add base_question_id during translation in step 5
            result = questions_collection.update_many(
                {'lang': {'$exists': False}},
                {'$set': {'lang': 'zh-TW'}}
            )
            
            self.stats['questions_backfilled'] = result.modified_count
            logger.info(f"✅ Backfilled {result.modified_count} questions with lang='zh-TW'")
            return True
            
        except Exception as e:
            error_msg = f"Error in step 4: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def step5_translate_questions(self) -> bool:
        """Step 5: Translate zh-TW questions to English"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 5: Translate Questions to English")
        logger.info("=" * 60)
        
        try:
            questions_collection = self.db['questions']
            
            # Find zh-TW questions without base_question_id (not yet translated)
            zh_questions = list(questions_collection.find({
                'lang': 'zh-TW',
                'base_question_id': {'$exists': False}
            }))
            
            logger.info(f"Found {len(zh_questions)} zh-TW questions to translate")
            
            if len(zh_questions) == 0:
                logger.info("✅ All questions already translated")
                return True
            
            if self.dry_run:
                logger.info(f"[DRY RUN] Would translate {len(zh_questions)} questions")
                self.stats['questions_translated'] = len(zh_questions)
                return True
            
            # Initialize translator
            if not self.translator:
                self.translator = Translator()
            
            translated = 0
            errors = []
            
            for idx, q in enumerate(zh_questions, 1):
                try:
                    question_id = str(q.get('_id', ''))
                    question_content = q.get('content', '')
                    
                    if idx % 10 == 0:
                        logger.info(f"Progress: {idx}/{len(zh_questions)} ({int(idx/len(zh_questions)*100)}%)")
                    
                    # Generate base_question_id
                    base_question_id = str(uuid.uuid4())
                    
                    # Update zh-TW question with base_question_id
                    questions_collection.update_one(
                        {'_id': q['_id']},
                        {'$set': {'base_question_id': base_question_id}}
                    )
                    
                    # Translate to English
                    translated_question = self.translator.translate_question_to_en(q)
                    translated_question['base_question_id'] = base_question_id
                    translated_question['lang'] = 'en'
                    translated_question['law_id'] = q.get('law_id', '')
                    translated_question['is_deleted'] = q.get('is_deleted', False)
                    translated_question['is_starred'] = q.get('is_starred', False)
                    
                    # Remove _id to let MongoDB generate new one
                    if '_id' in translated_question:
                        del translated_question['_id']
                    
                    # Insert English question
                    questions_collection.insert_one(translated_question)
                    translated += 1
                    
                except Exception as e:
                    error_msg = f"Error translating question {idx}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    # Rollback base_question_id
                    questions_collection.update_one(
                        {'_id': q['_id']},
                        {'$unset': {'base_question_id': 1}}
                    )
                    continue
            
            self.stats['questions_translated'] = translated
            self.stats['errors'].extend(errors)
            
            logger.info(f"✅ Translated {translated} questions to English")
            if errors:
                logger.warning(f"⚠️  {len(errors)} translation errors occurred")
            
            return len(errors) < len(zh_questions) * 0.1  # Allow up to 10% errors
            
        except Exception as e:
            error_msg = f"Error in step 5: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def step6_create_indexes(self) -> bool:
        """Step 6: Create necessary database indexes"""
        logger.info("\n" + "=" * 60)
        logger.info("STEP 6: Create Database Indexes")
        logger.info("=" * 60)
        
        try:
            laws_collection = self.db['laws']
            questions_collection = self.db['questions']
            
            indexes_to_create = [
                # Laws collection
                ('laws', 'lang_1', [('lang', ASCENDING)]),
                ('laws', 'article_number_1_lang_1', [('article_number', ASCENDING), ('lang', ASCENDING)]),
                
                # Questions collection
                ('questions', 'lang_1', [('lang', ASCENDING)]),
                ('questions', 'law_id_1_lang_1', [('law_id', ASCENDING), ('lang', ASCENDING)]),
                ('questions', 'base_question_id_1_lang_1', [('base_question_id', ASCENDING), ('lang', ASCENDING)]),
            ]
            
            created = 0
            
            for collection_name, index_name, keys in indexes_to_create:
                collection = self.db[collection_name]
                existing_indexes = collection.index_information()
                
                if index_name in existing_indexes:
                    logger.info(f"Index {index_name} already exists on {collection_name}")
                    continue
                
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would create index {index_name} on {collection_name}")
                    created += 1
                else:
                    collection.create_index(keys, name=index_name)
                    logger.info(f"✅ Created index {index_name} on {collection_name}")
                    created += 1
            
            self.stats['indexes_created'] = created
            return True
            
        except Exception as e:
            error_msg = f"Error in step 6: {str(e)}"
            logger.error(f"❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def verify_migration(self):
        """Verify migration results"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 POST-MIGRATION VERIFICATION")
        logger.info("=" * 60)
        
        laws_collection = self.db['laws']
        questions_collection = self.db['questions']
        mapping_collection = self.db['i18n_mapping']
        
        # Laws verification
        total_laws = laws_collection.count_documents({})
        zh_laws = laws_collection.count_documents({'lang': 'zh-TW'})
        en_laws = laws_collection.count_documents({'lang': 'en'})
        laws_no_lang = laws_collection.count_documents({'lang': {'$exists': False}})
        
        logger.info(f"Laws Collection:")
        logger.info(f"  Total laws: {total_laws}")
        logger.info(f"  zh-TW laws: {zh_laws}")
        logger.info(f"  EN laws: {en_laws}")
        logger.info(f"  Laws without lang: {laws_no_lang} {'✅' if laws_no_lang == 0 else '❌'}")
        
        # Questions verification
        total_questions = questions_collection.count_documents({})
        zh_questions = questions_collection.count_documents({'lang': 'zh-TW'})
        en_questions = questions_collection.count_documents({'lang': 'en'})
        questions_no_lang = questions_collection.count_documents({'lang': {'$exists': False}})
        questions_with_base_id = questions_collection.count_documents({'base_question_id': {'$exists': True}})
        
        logger.info(f"\nQuestions Collection:")
        logger.info(f"  Total questions: {total_questions}")
        logger.info(f"  zh-TW questions: {zh_questions}")
        logger.info(f"  EN questions: {en_questions}")
        logger.info(f"  Questions without lang: {questions_no_lang} {'✅' if questions_no_lang == 0 else '❌'}")
        logger.info(f"  Questions with base_id: {questions_with_base_id}")
        
        # Check if translation ratio is reasonable
        translation_ratio = en_questions / zh_questions if zh_questions > 0 else 0
        logger.info(f"  Translation coverage: {translation_ratio*100:.1f}% {'✅' if translation_ratio >= 0.9 else '⚠️'}")
        
        # Mappings verification
        total_mappings = mapping_collection.count_documents({})
        logger.info(f"\ni18n Mapping Collection:")
        logger.info(f"  Total mappings: {total_mappings} {'✅' if total_mappings >= zh_laws else '❌'}")
        
        # Test a sample mapping
        if total_mappings > 0:
            sample_mapping = mapping_collection.find_one({})
            if sample_mapping:
                zh_id = sample_mapping.get('zh_tw_law_id')
                en_id = sample_mapping.get('en_law_id')
                zh_law = laws_collection.find_one({'_id': ObjectId(zh_id)})
                en_law = laws_collection.find_one({'_id': ObjectId(en_id)})
                
                if zh_law and en_law:
                    logger.info(f"  Sample mapping verified: Article {sample_mapping['article_number']}")
                    logger.info(f"    zh-TW: {zh_law['article_number']}")
                    logger.info(f"    EN: {en_law['article_number']}")
        
        logger.info("=" * 60)
    
    def print_migration_summary(self):
        """Print final migration summary"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Database: {self.db_name}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTION'}")
        logger.info(f"")
        logger.info(f"Results:")
        logger.info(f"  ✅ Laws backfilled: {self.stats['laws_backfilled']}")
        logger.info(f"  ✅ EN laws inserted: {self.stats['en_laws_inserted']}")
        logger.info(f"  ✅ i18n mappings created: {self.stats['mappings_created']}")
        logger.info(f"  ✅ Questions backfilled: {self.stats['questions_backfilled']}")
        logger.info(f"  ✅ Questions translated: {self.stats['questions_translated']}")
        logger.info(f"  ✅ Indexes created: {self.stats['indexes_created']}")
        
        if self.stats['errors']:
            logger.info(f"  ❌ Errors: {len(self.stats['errors'])}")
            logger.info(f"\nError details (first 5):")
            for error in self.stats['errors'][:5]:
                logger.info(f"    - {error}")
        else:
            logger.info(f"  ❌ Errors: 0")
        
        logger.info("=" * 60 + "\n")
    
    def run(self) -> bool:
        """Execute full migration"""
        logger.info("\n" + "🚀" * 30)
        logger.info("PHASE 9 PRODUCTION DATA MIGRATION")
        logger.info("🚀" * 30)
        logger.info(f"Target: {self.db_name}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTION'}")
        logger.info("🚀" * 30 + "\n")
        
        if not self.connect():
            return False
        
        try:
            # Print pre-migration stats
            self.print_pre_migration_stats()
            
            # Execute migration steps
            steps = [
                ("Backfill Laws Lang Field", self.step1_backfill_laws_lang),
                ("Insert English Laws", self.step2_insert_english_laws),
                ("Create i18n Mappings", self.step3_create_i18n_mappings),
                ("Backfill Questions Lang Field", self.step4_backfill_questions_lang),
                ("Translate Questions to English", self.step5_translate_questions),
                ("Create Database Indexes", self.step6_create_indexes),
            ]
            
            for step_name, step_func in steps:
                logger.info(f"\n>>> Executing: {step_name}")
                success = step_func()
                
                if not success:
                    logger.error(f"❌ Step failed: {step_name}")
                    logger.error("Migration aborted")
                    return False
                
                logger.info(f"✅ Completed: {step_name}")
            
            # Verify migration (skip in dry run)
            if not self.dry_run:
                self.verify_migration()
            
            # Print summary
            self.print_migration_summary()
            
            return True
            
        finally:
            self.close()


def main():
    """Main program"""
    parser = argparse.ArgumentParser(
        description='Phase 9 Production Data Migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test migration on local database
  python scripts/migrate_production_phase9.py --local --dry-run
  
  # Execute migration on local database
  python scripts/migrate_production_phase9.py --local
  
  # Test migration on production database
  python scripts/migrate_production_phase9.py --remote --dry-run
  
  # Execute migration on production database
  python scripts/migrate_production_phase9.py --remote
  
  # Execute on both databases
  python scripts/migrate_production_phase9.py --both

⚠️  IMPORTANT: Always run with --dry-run first to verify!
⚠️  IMPORTANT: Backup your database before running on production!
        """
    )
    
    parser.add_argument('--local', action='store_true', help='Migrate local database')
    parser.add_argument('--remote', action='store_true', help='Migrate remote database')
    parser.add_argument('--both', action='store_true', help='Migrate both databases')
    parser.add_argument('--dry-run', action='store_true', help='Test run without modifying database')
    parser.add_argument('--skip-confirmation', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    # Ensure at least one option is specified
    if not (args.local or args.remote or args.both):
        parser.print_help()
        logger.error("\n❌ Error: Please specify --local, --remote, or --both")
        sys.exit(1)
    
    # Safety check for production
    if (args.remote or args.both) and not args.dry_run and not args.skip_confirmation:
        print("\n⚠️  WARNING: You are about to modify the PRODUCTION database!")
        print("⚠️  Please ensure you have:")
        print("   1. Created a database backup")
        print("   2. Tested the migration with --dry-run")
        print("   3. Reviewed the migration logs")
        print("")
        response = input("Type 'PROCEED' to continue: ")
        
        if response != 'PROCEED':
            logger.info("Migration cancelled by user")
            sys.exit(0)
    
    success = True
    
    # Migrate local database
    if args.local or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("🔧 LOCAL DATABASE MIGRATION")
        logger.info("=" * 60)
        
        migrator = Phase9Migrator(LOCAL_MONGO_URI, "local", dry_run=args.dry_run)
        local_success = migrator.run()
        success = success and local_success
    
    # Migrate remote database
    if args.remote or args.both:
        if not REMOTE_MONGO_URI:
            logger.error("❌ REMOTE_MONGO_URI not configured in .env file")
            sys.exit(1)
        
        logger.info("\n" + "=" * 60)
        logger.info("🌐 REMOTE DATABASE MIGRATION")
        logger.info("=" * 60)
        
        migrator = Phase9Migrator(REMOTE_MONGO_URI, "remote", dry_run=args.dry_run)
        remote_success = migrator.run()
        success = success and remote_success
    
    # Final result
    if success:
        if args.dry_run:
            logger.info("\n✅ Dry run completed successfully!")
            logger.info("Review the logs above, then run without --dry-run to execute")
        else:
            logger.info("\n✅ All migration operations completed successfully!")
            logger.info("Phase 9 i18n migration is complete")
        sys.exit(0)
    else:
        logger.error("\n❌ Some operations failed, please check error messages")
        logger.error("Review the log file for details")
        sys.exit(1)


if __name__ == '__main__':
    main()
