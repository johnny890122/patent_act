#!/usr/bin/env python3
"""
Migrate existing questions to multilingual support by translating zh-TW questions to English.

This script:
1. Finds all zh-TW questions in the database
2. Translates each to English using LLM
3. Links both versions with base_question_id
4. Inserts English versions back into the database

Usage:
    python scripts/migrate_questions_to_en.py --local --dry-run    # Test run
    python scripts/migrate_questions_to_en.py --local              # Execute on local
    python scripts/migrate_questions_to_en.py --remote             # Execute on remote
    python scripts/migrate_questions_to_en.py --both               # Execute on both
"""

import os
import sys
import logging
import argparse
import uuid
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add parent directory to path to import from project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.translator import Translator
from db.models import QuestionModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB URIs
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def migrate_questions_to_en(mongo_uri, db_name=None, dry_run=False):
    """
    Migrate existing zh-TW questions by translating to English.
    
    Args:
        mongo_uri: MongoDB connection string
        db_name: Database name (for logging)
        dry_run: If True, only log what would be done, don't modify database
        
    Returns:
        bool: True if successful
    """
    if db_name is None:
        db_name = "local" if "localhost" in mongo_uri else "remote"
    
    try:
        # Connect to database
        logger.info(f"Connecting to {db_name} MongoDB...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        logger.info(f"✅ Connected to {db_name} MongoDB")
        
        # Get database and collections
        db = client.get_database()
        questions_collection = db['questions']
        
        # Initialize translator
        translator = Translator()
        
        # Find all zh-TW questions that don't have an en version yet
        # A zh-TW question without base_question_id hasn't been migrated yet
        zh_tw_questions = list(questions_collection.find(
            {'lang': {'$exists': False}}  # Old questions don't have lang field
        ))
        
        logger.info(f"Found {len(zh_tw_questions)} zh-TW questions to migrate")
        
        if not zh_tw_questions and not dry_run:
            logger.info("No questions to migrate")
            return True
        
        translated = 0
        skipped = 0
        errors = []
        
        for idx, q in enumerate(zh_tw_questions, 1):
            try:
                question_id = str(q.get('_id', ''))
                question_content = q.get('content', '')
                
                logger.info(f"[{idx}/{len(zh_tw_questions)}] Processing: {question_content[:50]}...")
                
                if dry_run:
                    translated += 1
                    logger.debug(f"[DRY RUN] Would translate question {question_id}")
                    continue
                
                # Generate base_question_id for linking
                base_question_id = str(uuid.uuid4())
                
                # Update zh-TW question with lang field and base_question_id
                update_result = questions_collection.update_one(
                    {'_id': q['_id']},
                    {
                        '$set': {
                            'lang': 'zh-TW',
                            'base_question_id': base_question_id
                        }
                    }
                )
                
                if update_result.matched_count == 0:
                    logger.warning(f"Could not update zh-TW question {question_id}")
                    skipped += 1
                    continue
                
                # Translate to English
                try:
                    translated_question = translator.translate_question_to_en(q)
                    translated_question['base_question_id'] = base_question_id
                    translated_question['lang'] = 'en'
                    translated_question['law_id'] = q.get('law_id', '')
                    translated_question['is_deleted'] = q.get('is_deleted', False)
                    translated_question['is_starred'] = q.get('is_starred', False)
                    
                    # Remove _id to let MongoDB generate a new one
                    if '_id' in translated_question:
                        del translated_question['_id']
                    
                    # Insert translated question
                    insert_result = questions_collection.insert_one(translated_question)
                    
                    translated += 1
                    logger.info(f"✅ Translated question {question_id} to English (inserted as {insert_result.inserted_id})")
                    
                except Exception as e:
                    error_msg = f"Error translating question {question_id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    # Rollback the zh-TW update
                    questions_collection.update_one(
                        {'_id': q['_id']},
                        {
                            '$unset': {
                                'lang': 1,
                                'base_question_id': 1
                            }
                        }
                    )
                    continue
                
            except Exception as e:
                error_msg = f"Error processing question at index {idx}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
                continue
        
        # Output statistics
        logger.info("=" * 60)
        logger.info(f"📊 {db_name.upper()} Migration Statistics:")
        if dry_run:
            logger.info(f"   [DRY RUN] Would translate: {translated} questions")
        else:
            logger.info(f"   ✅ Translated: {translated} questions")
            logger.info(f"   ⏭️  Skipped: {skipped} questions")
            logger.info(f"   ❌ Errors: {len(errors)} questions")
        logger.info("=" * 60)
        
        if errors:
            logger.warning("Error details:")
            for error in errors[:10]:  # Show first 10 errors
                logger.warning(f"   {error}")
            if len(errors) > 10:
                logger.warning(f"   ... and {len(errors) - 10} more errors")
        
        if not dry_run:
            # Verify migration count
            zh_tw_count = questions_collection.count_documents({'lang': 'zh-TW'})
            en_count = questions_collection.count_documents({'lang': 'en'})
            
            logger.info(f"Final counts:")
            logger.info(f"   zh-TW questions: {zh_tw_count}")
            logger.info(f"   EN questions: {en_count}")
        
        client.close()
        return len(errors) == 0
        
    except PyMongoError as e:
        logger.error(f"❌ MongoDB error ({db_name}): {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Error ({db_name}): {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main program"""
    parser = argparse.ArgumentParser(
        description='Migrate questions to multilingual support'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='Migrate local database'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='Migrate remote database'
    )
    parser.add_argument(
        '--both',
        action='store_true',
        help='Migrate both local and remote databases'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test run without modifying database'
    )
    
    args = parser.parse_args()
    
    # Ensure at least one option is specified
    if not (args.local or args.remote or args.both):
        parser.print_help()
        logger.error("\n❌ Error: Please specify --local, --remote, or --both")
        sys.exit(1)
    
    success = True
    
    # Migrate local database
    if args.local or args.both:
        logger.info("\n" + "=" * 60)
        if args.dry_run:
            logger.info("DRY RUN: Testing migration on local database...")
        else:
            logger.info("Migrating local database to multilingual...")
        logger.info("=" * 60)
        local_success = migrate_questions_to_en(LOCAL_MONGO_URI, "local", dry_run=args.dry_run)
        success = success and local_success
    
    # Migrate remote database
    if args.remote or args.both:
        logger.info("\n" + "=" * 60)
        if args.dry_run:
            logger.info("DRY RUN: Testing migration on remote database...")
        else:
            logger.info("Migrating remote database to multilingual...")
        logger.info("=" * 60)
        remote_success = migrate_questions_to_en(REMOTE_MONGO_URI, "remote", dry_run=args.dry_run)
        success = success and remote_success
    
    if success:
        if args.dry_run:
            logger.info("\n✅ Dry run completed successfully!")
        else:
            logger.info("\n✅ All migration operations completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some operations failed, please check error messages")
        sys.exit(1)


if __name__ == '__main__':
    main()
