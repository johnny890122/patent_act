#!/usr/bin/env python3
"""
Data migration script: Single-user to Multi-user system.

This script:
1. Creates a default admin user
2. Migrates existing user_progress records to include user_id
3. Migrates law stars from laws.is_starred to user_law_stars collection
4. Migrates law stats from laws to user_law_stats collection
5. Migrates question stars from questions.is_starred to user_question_stars collection

Usage: python scripts/migrate_to_multiuser.py [--dry-run]
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import db.models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import (
    users_collection,
    user_progress_collection,
    user_law_stars_collection,
    user_law_stats_collection,
    user_question_stars_collection,
    laws_collection,
    questions_collection,
    UserModel
)
from dataclasses import asdict


def create_default_admin_user():
    """Create default admin user if not exists."""
    print("\n=== Step 1: Creating default admin user ===")
    
    # Check if admin user already exists
    admin_user = users_collection.find_one({'username': 'admin'})
    
    if admin_user:
        print(f"✅ Admin user already exists (ID: {admin_user['_id']})")
        return str(admin_user['_id']), admin_user['username']
    
    # Create new admin user
    user = UserModel(
        username='admin',
        display_name='Administrator',
        created_at=datetime.utcnow(),
        last_login=None
    )
    
    user_dict = asdict(user)
    result = users_collection.insert_one(user_dict)
    
    print(f"✅ Created default admin user (ID: {result.inserted_id})")
    return str(result.inserted_id), 'admin'


def migrate_user_progress(user_id: str, dry_run: bool = False):
    """Migrate user_progress records to include user_id."""
    print("\n=== Step 2: Migrating user_progress records ===")
    
    # Count records without user_id
    count_without_user_id = user_progress_collection.count_documents({
        '$or': [
            {'user_id': {'$exists': False}},
            {'user_id': None}
        ]
    })
    
    print(f"Found {count_without_user_id} progress records without user_id")
    
    if count_without_user_id == 0:
        print("✅ All progress records already have user_id")
        return
    
    if dry_run:
        print("🔍 DRY RUN: Would update these records with admin user_id")
        return
    
    # Update all records without user_id
    result = user_progress_collection.update_many(
        {
            '$or': [
                {'user_id': {'$exists': False}},
                {'user_id': None}
            ]
        },
        {
            '$set': {'user_id': user_id}
        }
    )
    
    print(f"✅ Updated {result.modified_count} progress records with user_id")


def migrate_law_stars(user_id: str, dry_run: bool = False):
    """Migrate law stars from laws.is_starred to user_law_stars collection."""
    print("\n=== Step 3: Migrating law stars ===")
    
    # Find all starred laws
    starred_laws = list(laws_collection.find({'is_starred': True}))
    
    print(f"Found {len(starred_laws)} starred laws")
    
    if len(starred_laws) == 0:
        print("✅ No starred laws to migrate")
        return
    
    if dry_run:
        print(f"🔍 DRY RUN: Would create {len(starred_laws)} user_law_stars records")
        return
    
    # Create user_law_stars records
    inserted_count = 0
    for law in starred_laws:
        # Check if already exists
        existing = user_law_stars_collection.find_one({
            'user_id': user_id,
            'law_id': str(law['_id'])
        })
        
        if not existing:
            user_law_stars_collection.insert_one({
                'user_id': user_id,
                'law_id': str(law['_id']),
                'created_at': datetime.utcnow()
            })
            inserted_count += 1
    
    print(f"✅ Created {inserted_count} user_law_stars records")
    
    # Remove is_starred field from laws (cleanup)
    laws_collection.update_many(
        {'is_starred': {'$exists': True}},
        {'$unset': {'is_starred': ''}}
    )
    print("✅ Removed is_starred field from laws collection")


def migrate_law_stats(user_id: str, dry_run: bool = False):
    """Migrate law stats from laws to user_law_stats collection."""
    print("\n=== Step 4: Migrating law stats ===")
    
    # Find all laws with stats
    laws_with_stats = list(laws_collection.find({
        '$or': [
            {'total_score': {'$gt': 0}},
            {'attempt_count': {'$gt': 0}}
        ]
    }))
    
    print(f"Found {len(laws_with_stats)} laws with statistics")
    
    if len(laws_with_stats) == 0:
        print("✅ No law statistics to migrate")
        return
    
    if dry_run:
        print(f"🔍 DRY RUN: Would create {len(laws_with_stats)} user_law_stats records")
        return
    
    # Create user_law_stats records
    inserted_count = 0
    for law in laws_with_stats:
        # Check if already exists
        existing = user_law_stats_collection.find_one({
            'user_id': user_id,
            'law_id': str(law['_id'])
        })
        
        if not existing:
            user_law_stats_collection.insert_one({
                'user_id': user_id,
                'law_id': str(law['_id']),
                'total_score': law.get('total_score', 0.0),
                'attempt_count': law.get('attempt_count', 0),
                'avg_score': law.get('avg_score', 0.0)
            })
            inserted_count += 1
    
    print(f"✅ Created {inserted_count} user_law_stats records")
    
    # Remove stats fields from laws (cleanup)
    laws_collection.update_many(
        {},
        {'$unset': {
            'total_score': '',
            'attempt_count': '',
            'avg_score': ''
        }}
    )
    print("✅ Removed stats fields from laws collection")


def migrate_question_stars(user_id: str, dry_run: bool = False):
    """Migrate question stars from questions.is_starred to user_question_stars collection."""
    print("\n=== Step 5: Migrating question stars ===")
    
    # Find all starred questions
    starred_questions = list(questions_collection.find({'is_starred': True}))
    
    print(f"Found {len(starred_questions)} starred questions")
    
    if len(starred_questions) == 0:
        print("✅ No starred questions to migrate")
        return
    
    if dry_run:
        print(f"🔍 DRY RUN: Would create {len(starred_questions)} user_question_stars records")
        return
    
    # Create user_question_stars records
    inserted_count = 0
    for question in starred_questions:
        # Check if already exists
        existing = user_question_stars_collection.find_one({
            'user_id': user_id,
            'question_id': str(question['_id'])
        })
        
        if not existing:
            user_question_stars_collection.insert_one({
                'user_id': user_id,
                'question_id': str(question['_id']),
                'created_at': datetime.utcnow()
            })
            inserted_count += 1
    
    print(f"✅ Created {inserted_count} user_question_stars records")
    
    # Remove is_starred field from questions (cleanup)
    questions_collection.update_many(
        {'is_starred': {'$exists': True}},
        {'$unset': {'is_starred': ''}}
    )
    print("✅ Removed is_starred field from questions collection")


def main():
    """Main migration process."""
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No data will be modified")
    
    print("=" * 80)
    print("Starting multi-user migration")
    print("=" * 80)
    
    # Step 1: Create admin user
    user_id, username = create_default_admin_user()
    print(f"\nMigrating data to user: {username} (ID: {user_id})")
    
    # Step 2-5: Migrate data
    migrate_user_progress(user_id, dry_run)
    migrate_law_stars(user_id, dry_run)
    migrate_law_stats(user_id, dry_run)
    migrate_question_stars(user_id, dry_run)
    
    print("\n" + "=" * 80)
    if dry_run:
        print("🔍 DRY RUN COMPLETE - Run without --dry-run to apply changes")
    else:
        print("✅ Migration complete!")
        print(f"\nDefault admin user credentials:")
        print(f"  Username: {username}")
        print(f"  Display Name: Administrator")
        print(f"\nYou can now add additional users with:")
        print('  python scripts/add_user.py <username> "<display_name>"')
    print("=" * 80)


if __name__ == '__main__':
    main()
