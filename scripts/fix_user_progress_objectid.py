"""
Fix user_progress records - use ObjectId instead of string.
"""
from pymongo import MongoClient
from bson import ObjectId
import os

uri = os.environ.get('MONGODB_URI', 'mongodb+srv://admin:03ra64XqDM8sOBdV@cluster0.lsu6m2w.mongodb.net/patent-act?retryWrites=true&w=majority')

client = MongoClient(uri)
db = client['patent-act']

# Find meng user
meng_user = db.users.find_one({'username': 'meng'})
if not meng_user:
    print('Error: meng user not found')
    client.close()
    exit(1)

meng_id = meng_user['_id']  # Keep as ObjectId, NOT string!
print(f'Found meng user with ID: {meng_id} (ObjectId)')
print(f'Display name: {meng_user.get("display_name")}')

# Check current state
sample = db.user_progress.find_one({'user_id': {'$exists': True}})
if sample:
    print(f'\nCurrent user_id type: {type(sample.get("user_id"))}')
    print(f'Sample value: {sample.get("user_id")}')

# Update all progress records - use ObjectId!
print('\nUpdating user_progress records with ObjectId...')
result = db.user_progress.update_many(
    {},  # Update ALL records
    {'$set': {'user_id': meng_id}}  # Use ObjectId directly
)

print(f'✅ Updated {result.modified_count} user_progress records')

# Verification
progress_count = db.user_progress.count_documents({})
progress_for_meng_objectid = db.user_progress.count_documents({'user_id': meng_id})

print(f'\nVerification:')
print(f'  Total progress records: {progress_count}')
print(f'  With meng ObjectId: {progress_for_meng_objectid}')

# Check one record
sample_after = db.user_progress.find_one({'user_id': meng_id})
if sample_after:
    print(f'\n✅ Confirmed: user_id is now ObjectId')
    print(f'   Type: {type(sample_after["user_id"])}')
    print(f'   Value: {sample_after["user_id"]}')

client.close()
print('\n✅ Migration complete!')
