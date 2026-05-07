#!/usr/bin/env python3
"""
Script to initialize laws data to remote MongoDB (Heroku MongoDB Atlas).

This script connects to the remote MongoDB using Heroku's MONGO_URI
and loads law data from knowledge/mock_laws.json.

Usage:
    python scripts/init_remote_laws.py
"""

import os
import sys
import json
import logging
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Add parent directory to path to import from project modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.models import LawModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Remote MongoDB URI (Heroku MongoDB Atlas)
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')

# Path to mock laws data
MOCK_LAWS_PATH = os.path.join(
    os.path.dirname(__file__), 
    '..', 
    'knowledge', 
    'mock_laws.json'
)


def load_mock_laws():
    """Load laws from mock_laws.json file."""
    logger.info(f"Loading laws from: {MOCK_LAWS_PATH}")
    
    if not os.path.exists(MOCK_LAWS_PATH):
        raise FileNotFoundError(f"Mock laws file not found: {MOCK_LAWS_PATH}")
    
    with open(MOCK_LAWS_PATH, 'r', encoding='utf-8') as f:
        laws_data = json.load(f)
    
    logger.info(f"Loaded {len(laws_data)} laws from file")
    return laws_data


def init_remote_laws():
    """Initialize laws to remote MongoDB."""
    try:
        # Connect to remote MongoDB
        logger.info("Connecting to remote MongoDB Atlas...")
        client = MongoClient(REMOTE_MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Test connection
        client.admin.command('ping')
        logger.info("✅ Successfully connected to remote MongoDB")
        
        # Get database and collection
        db = client.get_database()
        laws_collection = db['laws']
        
        # Load laws data
        laws_data = load_mock_laws()
        
        # Initialize counters
        inserted = 0
        updated = 0
        errors = []
        
        logger.info("Starting to process laws...")
        
        for idx, law_data in enumerate(laws_data, 1):
            try:
                # Validate through dataclass
                law_model = LawModel(**law_data)
                law_dict = {
                    'article_number': law_model.article_number,
                    'content': law_model.content,
                    'chapter': law_model.chapter,
                }
                
                # Upsert: update if exists, insert if not
                result = laws_collection.update_one(
                    {'article_number': law_model.article_number},
                    {'$set': law_dict},
                    upsert=True
                )
                
                if result.upserted_id:
                    inserted += 1
                    logger.info(f"  [{idx}/{len(laws_data)}] Inserted: {law_model.article_number}")
                elif result.modified_count > 0:
                    updated += 1
                    logger.info(f"  [{idx}/{len(laws_data)}] Updated: {law_model.article_number}")
                else:
                    logger.info(f"  [{idx}/{len(laws_data)}] No change: {law_model.article_number}")
                    
            except Exception as e:
                error_msg = f"Failed to process law #{idx}: {str(e)}"
                logger.error(f"  ❌ {error_msg}")
                errors.append(error_msg)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("INITIALIZATION COMPLETE")
        logger.info("="*60)
        logger.info(f"✅ Inserted: {inserted}")
        logger.info(f"🔄 Updated: {updated}")
        logger.info(f"❌ Errors: {len(errors)}")
        logger.info(f"📊 Total processed: {len(laws_data)}")
        
        if errors:
            logger.warning("\nErrors encountered:")
            for error in errors:
                logger.warning(f"  - {error}")
        
        # Close connection
        client.close()
        logger.info("\n✅ Connection closed. Initialization successful!")
        
        return {
            'inserted': inserted,
            'updated': updated,
            'errors': errors,
            'total': len(laws_data)
        }
        
    except PyMongoError as e:
        logger.error(f"❌ MongoDB error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        raise


if __name__ == "__main__":
    try:
        logger.info("Starting remote law initialization script...")
        logger.info("Target: Heroku MongoDB Atlas")
        logger.info("-" * 60)
        
        result = init_remote_laws()
        
        # Exit with success
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Script failed: {str(e)}")
        sys.exit(1)
