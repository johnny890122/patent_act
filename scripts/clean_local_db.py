#!/usr/bin/env python3
"""
Clean local database by removing multi-user collections.

This script removes:
- users collection
- user_law_stars collection
- user_law_stats collection
- user_question_stars collection
- Removes user_id field from user_progress
- Restores is_starred fields to laws and questions

Usage: python scripts/clean_local_db.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import (
    users_collection,
    user_progress_collection,
    user_law_stars_collection,
    user_law_stats_collection,
    user_question_stars_collection,
    laws_collection,
    questions_collection
)


def clean_database():
    """Clean multi-user collections and restore single-user state."""
    print("=" * 80)
    print("🧹 Cleaning Local Database")
    print("=" * 80)
    
    # Confirm
    print("\n⚠️  WARNING: This will remove all multi-user data!")
    print("This includes:")
    print("  - All users")
    print("  - User-specific stars and stats")
    print("  - user_id from user_progress")
    
    response = input("\nDo you want to continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Operation cancelled")
        sys.exit(0)
    
    print("\n=== Cleaning collections ===")
    
    # Drop multi-user collections
    collections_to_drop = [
        ('users', users_collection),
        ('user_law_stars', user_law_stars_collection),
        ('user_law_stats', user_law_stats_collection),
        ('user_question_stars', user_question_stars_collection)
    ]
    
    for name, collection in collections_to_drop:
        count = collection.count_documents({})
        if count > 0:
            collection.drop()
            print(f"  ✅ Dropped '{name}' collection ({count} documents)")
        else:
            print(f"  ℹ️  '{name}' collection is already empty")
    
    # Remove user_id from user_progress
    result = user_progress_collection.update_many(
        {'user_id': {'$exists': True}},
        {'$unset': {'user_id': ''}}
    )
    if result.modified_count > 0:
        print(f"  ✅ Removed user_id from {result.modified_count} user_progress records")
    else:
        print(f"  ℹ️  No user_id fields found in user_progress")
    
    print("\n" + "=" * 80)
    print("✅ Cleanup complete!")
    print("\nLocal database is now in single-user state.")
    print("You can now copy remote data:")
    print("  python scripts/copy_remote_to_local.py --backup")
    print("=" * 80)


if __name__ == '__main__':
    clean_database()
