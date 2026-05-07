"""
Fix user_progress records by adding user_id field.
This script assigns all existing progress to the meng user.
"""
from pymongo import MongoClient
import os

# Get MongoDB URI from environment or use default
uri = os.environ.get('MONGODB_URI', 'mongodb+srv://admin:03ra64XqDM8sOBdV@cluster0.lsu6m2w.mongodb.net/patent-act?retryWrites=true&w=majority')

client = MongoClient(uri)
db = client['patent-act']

# Find meng user
meng_user = db.users.find_one({'username': 'meng'})
if not meng_user:
    print('Error: meng user not found')
    users = list(db.users.find({}))
    print(f'Available users: {[u.get("username") for u in users]}')
    client.close()
    exit(1)

meng_id = str(meng_user['_id'])
print(f'Found meng user with ID: {meng_id}')
print(f'Display name: {meng_user.get("display_name")}')

# Update all progress records without user_id
print('\nUpdating user_progress records...')
result = db.user_progress.update_many(
    {'user_id': {'$exists': False}},
    {'$set': {'user_id': meng_id}}
)

print(f'✅ Updated {result.modified_count} user_progress records')

# Verification
progress_with_user_id = db.user_progress.count_documents({'user_id': {'$exists': True}})
progress_without_user_id = db.user_progress.count_documents({'user_id': {'$exists': False}})
progress_for_meng = db.user_progress.count_documents({'user_id': meng_id})

print(f'\nVerification:')
print(f'  Total with user_id: {progress_with_user_id}')
print(f'  Without user_id: {progress_without_user_id}')
print(f'  Belonging to meng: {progress_for_meng}')

client.close()
print('\n✅ Migration complete!')
