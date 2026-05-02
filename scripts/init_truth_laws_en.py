#!/usr/bin/env python3
"""
Insert English law articles from knowledge/truth_law_en.json to local and remote databases.

Usage:
    python scripts/init_truth_laws_en.py --local    # Insert to local database
    python scripts/init_truth_laws_en.py --remote   # Insert to remote database
    python scripts/init_truth_laws_en.py --both     # Insert to both databases
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

# MongoDB URIs
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

# Path to English law data
TRUTH_LAWS_EN_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'truth_law_en.json'
)


def extract_article_number_int(article_number: str) -> int:
    """
    Extract integer from article number string for sorting.
    Example: 'Article 1' -> 1, 'Article 10' -> 10, 'Article 101' -> 101
    """
    match = re.search(r'\d+', article_number)
    if match:
        return int(match.group())
    return 0


def load_truth_laws_en():
    """Load English law data from truth_law_en.json"""
    logger.info(f"Loading English law data: {TRUTH_LAWS_EN_PATH}")
    
    if not os.path.exists(TRUTH_LAWS_EN_PATH):
        raise FileNotFoundError(f"Truth laws EN file not found: {TRUTH_LAWS_EN_PATH}")
    
    with open(TRUTH_LAWS_EN_PATH, 'r', encoding='utf-8') as f:
        laws_data = json.load(f)
    
    logger.info(f"Loaded {len(laws_data)} English law articles")
    return laws_data


def init_laws_en_to_db(mongo_uri, db_name=None):
    """
    Insert English law articles to the specified database.
    
    Args:
        mongo_uri: MongoDB connection string
        db_name: Database name (for logging)
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
        
        # Get database and collection
        db = client.get_database()
        laws_collection = db['laws']
        
        # Load English law data
        laws_data = load_truth_laws_en()
        
        # Initialize counters
        inserted = 0
        updated = 0
        errors = []
        
        logger.info(f"Processing English law articles and inserting to {db_name}...")
        
        for idx, law_data in enumerate(laws_data, 1):
            try:
                # Extract article number integer for sorting
                article_number_int = extract_article_number_int(law_data['article_number'])
                law_data['article_number_int'] = article_number_int
                
                # Validate via dataclass
                law_model = LawModel(**law_data)
                law_dict = {
                    'article_number': law_model.article_number,
                    'content': law_model.content,
                    'chapter': law_model.chapter,
                    'article_number_int': law_model.article_number_int,
                    'lang': law_model.lang,  # EN: English language tag
                    'is_starred': law_model.is_starred,
                    'total_score': law_model.total_score,
                    'attempt_count': law_model.attempt_count,
                    'avg_score': law_model.avg_score
                }
                
                # Upsert: Update if exists, insert if not
                # Use composite index (article_number, lang) to distinguish from zh-TW version
                result = laws_collection.update_one(
                    {'article_number': law_model.article_number, 'lang': 'en'},
                    {'$set': law_dict},
                    upsert=True
                )
                
                if result.upserted_id:
                    inserted += 1
                    logger.debug(f"[{idx}/{len(laws_data)}] Inserted: {law_model.article_number} (en)")
                else:
                    updated += 1
                    logger.debug(f"[{idx}/{len(laws_data)}] Updated: {law_model.article_number} (en)")
                
            except Exception as e:
                error_msg = f"Error processing {law_data.get('article_number', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Output statistics
        logger.info("=" * 60)
        logger.info(f"📊 {db_name.upper()} English Law Insertion Statistics:")
        logger.info(f"   ✅ Newly inserted: {inserted} articles")
        logger.info(f"   🔄 Updated: {updated} articles")
        logger.info(f"   ❌ Errors: {len(errors)} articles")
        logger.info(f"   📝 Total: {len(laws_data)} articles")
        logger.info("=" * 60)
        
        if errors:
            logger.warning("Error details:")
            for error in errors:
                logger.warning(f"   {error}")
        
        # Verify law count in database
        total_count = laws_collection.count_documents({'lang': 'en'})
        logger.info(f"✅ {db_name} database now has {total_count} English law articles")
        
        client.close()
        return True
        
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
        description='Insert truth_law_en.json to database'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='Insert to local database'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='Insert to remote database'
    )
    parser.add_argument(
        '--both',
        action='store_true',
        help='Insert to both local and remote databases'
    )
    
    args = parser.parse_args()
    
    # Ensure at least one option is specified
    if not (args.local or args.remote or args.both):
        parser.print_help()
        logger.error("\n❌ Error: Please specify --local, --remote, or --both")
        sys.exit(1)
    
    success = True
    
    # Insert to local database
    if args.local or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("Inserting English laws to local database...")
        logger.info("=" * 60)
        local_success = init_laws_en_to_db(LOCAL_MONGO_URI, "local")
        success = success and local_success
    
    # Insert to remote database
    if args.remote or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("Inserting English laws to remote database...")
        logger.info("=" * 60)
        remote_success = init_laws_en_to_db(REMOTE_MONGO_URI, "remote")
        success = success and remote_success
    
    if success:
        logger.info("\n✅ All operations completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some operations failed, please check error messages")
        sys.exit(1)


if __name__ == '__main__':
    main()
