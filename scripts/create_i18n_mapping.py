#!/usr/bin/env python3
"""
Create bidirectional mappings between zh-TW and en law articles.

This script creates i18n_mapping collection entries for each law article,
enabling easy lookup of the corresponding language version.

Usage:
    python scripts/create_i18n_mapping.py --local    # Create mapping in local database
    python scripts/create_i18n_mapping.py --remote   # Create mapping in remote database
    python scripts/create_i18n_mapping.py --both     # Create mapping in both databases
"""

import os
import sys
import logging
import argparse
import re
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB URIs
LOCAL_MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')


def create_i18n_mapping(mongo_uri, db_name=None):
    """
    Create bidirectional mappings between zh-TW and en law articles.
    
    Args:
        mongo_uri: MongoDB connection string
        db_name: Database name (for logging)
    """
    if db_name is None:
        db_name = "local" if "localhost" in mongo_uri else "remote"
    
    def extract_article_number(article_str):
        """Extract numeric part from article string.
        Example: '第 1 條' -> 1, 'Article 1' -> 1
        """
        match = re.search(r'\d+', article_str)
        return int(match.group()) if match else None
    
    try:
        # Connect to database
        logger.info(f"Connecting to {db_name} MongoDB...")
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        logger.info(f"✅ Connected to {db_name} MongoDB")
        
        # Get database and collections
        db = client.get_database()
        laws_collection = db['laws']
        mapping_collection = db['i18n_mapping']
        
        # Clear existing mappings (idempotent)
        logger.info(f"Clearing existing mappings in {db_name}...")
        mapping_collection.delete_many({})
        
        # Get all unique article numbers
        # Note: zh-TW format is "第 X 條", en format is "Article X"
        logger.info(f"Fetching all law articles from {db_name}...")
        
        # Get zh-TW laws
        zh_tw_laws = list(laws_collection.find({'lang': 'zh-TW'}, {'_id': 1, 'article_number': 1}))
        logger.info(f"Found {len(zh_tw_laws)} zh-TW law articles")
        
        # Get en laws
        en_laws = list(laws_collection.find({'lang': 'en'}, {'_id': 1, 'article_number': 1}))
        logger.info(f"Found {len(en_laws)} en law articles")
        
        # Build lookup dict by article number
        en_laws_by_num = {}
        for law in en_laws:
            num = extract_article_number(law['article_number'])
            if num:
                en_laws_by_num[num] = law
        
        # Create mapping by article_number
        created = 0
        skipped = 0
        errors = []
        
        logger.info(f"Creating i18n mappings in {db_name}...")
        
        for zh_tw_law in zh_tw_laws:
            zh_tw_article_num = extract_article_number(zh_tw_law['article_number'])
            
            if zh_tw_article_num and zh_tw_article_num in en_laws_by_num:
                try:
                    en_law = en_laws_by_num[zh_tw_article_num]
                    
                    mapping_doc = {
                        'zh_tw_law_id': str(zh_tw_law['_id']),
                        'en_law_id': str(en_law['_id']),
                        'article_number': str(zh_tw_article_num)
                    }
                    
                    # Upsert: Update if exists, insert if not
                    result = mapping_collection.update_one(
                        {'article_number': str(zh_tw_article_num)},
                        {'$set': mapping_doc},
                        upsert=True
                    )
                    
                    created += 1
                    logger.debug(f"Created mapping for Article {zh_tw_article_num}")
                    
                except Exception as e:
                    error_msg = f"Error creating mapping for Article {zh_tw_article_num}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            else:
                skipped += 1
                logger.debug(f"No matching en law for Article {zh_tw_article_num}")
        
        # Output statistics
        logger.info("=" * 60)
        logger.info(f"📊 {db_name.upper()} i18n Mapping Statistics:")
        logger.info(f"   ✅ Created/Updated: {created} mappings")
        logger.info(f"   ⏭️  Skipped (no match): {skipped} articles")
        logger.info(f"   ❌ Errors: {len(errors)} articles")
        logger.info("=" * 60)
        
        if errors:
            logger.warning("Error details:")
            for error in errors:
                logger.warning(f"   {error}")
        
        # Verify mapping count
        total_mappings = mapping_collection.count_documents({})
        logger.info(f"✅ {db_name} database now has {total_mappings} i18n mappings")
        
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
        description='Create i18n mappings between zh-TW and en law articles'
    )
    parser.add_argument(
        '--local',
        action='store_true',
        help='Create mapping in local database'
    )
    parser.add_argument(
        '--remote',
        action='store_true',
        help='Create mapping in remote database'
    )
    parser.add_argument(
        '--both',
        action='store_true',
        help='Create mapping in both local and remote databases'
    )
    
    args = parser.parse_args()
    
    # Ensure at least one option is specified
    if not (args.local or args.remote or args.both):
        parser.print_help()
        logger.error("\n❌ Error: Please specify --local, --remote, or --both")
        sys.exit(1)
    
    success = True
    
    # Create mapping in local database
    if args.local or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("Creating i18n mappings in local database...")
        logger.info("=" * 60)
        local_success = create_i18n_mapping(LOCAL_MONGO_URI, "local")
        success = success and local_success
    
    # Create mapping in remote database
    if args.remote or args.both:
        logger.info("\n" + "=" * 60)
        logger.info("Creating i18n mappings in remote database...")
        logger.info("=" * 60)
        remote_success = create_i18n_mapping(REMOTE_MONGO_URI, "remote")
        success = success and remote_success
    
    if success:
        logger.info("\n✅ All operations completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Some operations failed, please check error messages")
        sys.exit(1)


if __name__ == '__main__':
    main()
