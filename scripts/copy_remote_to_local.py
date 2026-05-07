#!/usr/bin/env python3
"""
Copy production database to local database for testing.

This script:
1. Backs up local database (optional)
2. Connects to remote (production) database
3. Copies all collections to local database
4. Preserves all data and indexes

Usage: 
  python scripts/copy_remote_to_local.py [--backup]
  python scripts/copy_remote_to_local.py --backup  # Create local backup first
"""

import sys
import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

# Database URIs
LOCAL_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/patent_act')
REMOTE_URI = os.environ.get('REMOTE_MONGO_URI')

# Collections to copy
COLLECTIONS = [
    'laws',
    'questions',
    'user_progress',
    'i18n_mapping'
]


def backup_local_database(local_client, local_db_name):
    """Create a backup of local database before copying."""
    print("\n=== Backing up local database ===")
    
    backup_db_name = f"{local_db_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_db = local_client[backup_db_name]
    local_db = local_client[local_db_name]
    
    # Get all collection names
    collections = local_db.list_collection_names()
    
    if not collections:
        print("ℹ️  Local database is empty, no backup needed")
        return None
    
    print(f"Creating backup database: {backup_db_name}")
    
    for collection_name in collections:
        source_collection = local_db[collection_name]
        backup_collection = backup_db[collection_name]
        
        # Copy all documents
        documents = list(source_collection.find())
        if documents:
            backup_collection.insert_many(documents)
            print(f"  ✅ Backed up {len(documents)} documents from '{collection_name}'")
    
    print(f"✅ Backup created: {backup_db_name}")
    return backup_db_name


def copy_collection(remote_db, local_db, collection_name):
    """Copy a single collection from remote to local."""
    remote_collection = remote_db[collection_name]
    local_collection = local_db[collection_name]
    
    # Get all documents from remote
    documents = list(remote_collection.find())
    
    if not documents:
        print(f"  ⚠️  '{collection_name}' is empty on remote")
        return 0
    
    # Clear local collection
    local_collection.delete_many({})
    
    # Insert documents
    local_collection.insert_many(documents)
    
    print(f"  ✅ Copied {len(documents)} documents to '{collection_name}'")
    return len(documents)


def main():
    """Main copy process."""
    # Check if remote URI is configured
    if not REMOTE_URI or '<username>' in REMOTE_URI or '<password>' in REMOTE_URI:
        print("❌ Error: REMOTE_MONGO_URI not configured in .env")
        print("\nPlease set REMOTE_MONGO_URI in your .env file:")
        print("REMOTE_MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/dbname")
        sys.exit(1)
    
    # Check if backup flag is set
    create_backup = '--backup' in sys.argv
    
    print("=" * 80)
    print("📦 Copy Remote Database to Local")
    print("=" * 80)
    print(f"\nSource (Remote): {REMOTE_URI.split('@')[1] if '@' in REMOTE_URI else 'configured'}")
    print(f"Target (Local):  {LOCAL_URI}")
    print(f"Backup local:    {'Yes' if create_backup else 'No'}")
    print("\nCollections to copy:", ', '.join(COLLECTIONS))
    
    # Confirm
    print("\n⚠️  WARNING: This will REPLACE all data in your local database!")
    if create_backup:
        print("✅ A backup will be created before copying.")
    
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled")
        sys.exit(0)
    
    try:
        # Connect to databases
        print("\n=== Connecting to databases ===")
        remote_client = MongoClient(REMOTE_URI)
        local_client = MongoClient(LOCAL_URI)
        
        # Get database names
        remote_db_name = remote_client.get_database().name
        local_db_name = local_client.get_database().name if local_client.get_database().name else 'patent_act'
        
        remote_db = remote_client[remote_db_name]
        local_db = local_client[local_db_name]
        
        print(f"✅ Connected to remote: {remote_db_name}")
        print(f"✅ Connected to local: {local_db_name}")
        
        # Backup local database if requested
        backup_name = None
        if create_backup:
            backup_name = backup_local_database(local_client, local_db_name)
        
        # Copy collections
        print("\n=== Copying collections ===")
        total_documents = 0
        
        for collection_name in COLLECTIONS:
            count = copy_collection(remote_db, local_db, collection_name)
            total_documents += count
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ Copy complete!")
        print(f"\nTotal documents copied: {total_documents}")
        if backup_name:
            print(f"Local backup saved as: {backup_name}")
        print("\nYou can now run migration scripts on your local database:")
        print("  python scripts/migrate_to_multiuser.py --dry-run")
        print("  python scripts/migrate_to_multiuser.py")
        print("=" * 80)
        
        # Close connections
        remote_client.close()
        local_client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
