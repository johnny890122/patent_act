#!/usr/bin/env python3
"""測試 i18n API 端點"""
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://127.0.0.1:5001"

print('=== i18n API 端點測試 ===\n')

# Test 1: GET /api/laws with lang parameter
print('1. Test GET /api/laws with lang filter:')
try:
    # zh-TW laws
    response = requests.get(f'{BASE_URL}/api/laws', params={'lang': 'zh-TW', 'per_page': 5})
    if response.status_code == 200:
        data = response.json()
        print(f'   ✅ zh-TW laws: {data.get("total")} total, showing {len(data.get("laws", []))}')
        if data.get('laws'):
            first_law = data['laws'][0]
            print(f'      First law: {first_law.get("article_number")} - {first_law.get("lang")}')
    else:
        print(f'   ❌ zh-TW request failed: {response.status_code}')
    
    # EN laws
    response = requests.get(f'{BASE_URL}/api/laws', params={'lang': 'en', 'per_page': 5})
    if response.status_code == 200:
        data = response.json()
        print(f'   ✅ EN laws: {data.get("total")} total, showing {len(data.get("laws", []))}')
        if data.get('laws'):
            first_law = data['laws'][0]
            print(f'      First law: {first_law.get("article_number")} - {first_law.get("lang")}')
    else:
        print(f'   ❌ EN request failed: {response.status_code}')
        
except Exception as e:
    print(f'   ❌ Error: {e}')

# Test 2: Check if quiz session accepts lang parameter
print('\n2. Test POST /api/quiz/session with lang parameter:')
try:
    payload = {
        'type': 'MCQ',
        'mode': 'new',
        'count': 1,
        'lang': 'en'
    }
    response = requests.post(f'{BASE_URL}/api/quiz/session', json=payload)
    if response.status_code in [200, 201]:
        data = response.json()
        session_id = data.get('session_id')
        print(f'   ✅ EN quiz session created: {session_id}')
        
        # Check first question language
        if data.get('questions') and len(data['questions']) > 0:
            first_q = data['questions'][0]
            print(f'      First question lang: {first_q.get("lang", "not set")}')
            print(f'      Question content: {first_q.get("content", "")[:50]}...')
    else:
        print(f'   ⚠️  Status: {response.status_code} - {response.text[:100]}')
except Exception as e:
    print(f'   ❌ Error: {e}')

# Test 3: Check bilingual question linking
print('\n3. Test bilingual question linking:')
try:
    from pymongo import MongoClient
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
    client = MongoClient(mongo_uri)
    db = client.get_database()
    
    # Find a question with base_question_id
    en_q = db['questions'].find_one({'lang': 'en', 'base_question_id': {'$exists': True}})
    if en_q:
        base_id = en_q['base_question_id']
        zh_q = db['questions'].find_one({'lang': 'zh-TW', 'base_question_id': base_id})
        
        if zh_q:
            print(f'   ✅ Found linked question pair:')
            print(f'      Base ID: {base_id}')
            print(f'      EN content: {en_q.get("content", "")[:50]}...')
            print(f'      ZH content: {zh_q.get("content", "")[:50]}...')
        else:
            print(f'   ⚠️  EN question found but no matching zh-TW version')
    else:
        print(f'   ⚠️  No EN questions with base_question_id found')
    
    client.close()
except Exception as e:
    print(f'   ❌ Error: {e}')

print('\n✅ i18n API 測試完成')
