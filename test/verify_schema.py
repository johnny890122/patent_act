#!/usr/bin/env python3
"""驗證資料庫 Schema 更新"""
import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
client = MongoClient(mongo_uri)
db = client.get_database()

print('=== 資料庫 Schema 驗證 ===\n')

# 檢查 laws collection
print('1. Laws Collection:')
zh_tw_laws = db['laws'].count_documents({'lang': 'zh-TW'})
en_laws = db['laws'].count_documents({'lang': 'en'})
print(f'   zh-TW laws: {zh_tw_laws}')
print(f'   en laws: {en_laws}')

sample_law = db['laws'].find_one({'lang': 'zh-TW'})
if sample_law:
    print(f'   Sample zh-TW law fields: {list(sample_law.keys())}')

# 檢查 questions collection
print('\n2. Questions Collection:')
zh_tw_questions = db['questions'].count_documents({'lang': 'zh-TW'})
en_questions = db['questions'].count_documents({'lang': 'en'})
old_questions = db['questions'].count_documents({'lang': {'$exists': False}})
print(f'   zh-TW questions: {zh_tw_questions}')
print(f'   en questions: {en_questions}')
print(f'   old questions (no lang): {old_questions}')

sample_q = db['questions'].find_one({'lang': 'en'})
if sample_q:
    print(f'   Sample en question has base_question_id: {"base_question_id" in sample_q}')
    if 'base_question_id' in sample_q:
        # 找到對應的 zh-TW 版本
        base_id = sample_q['base_question_id']
        zh_version = db['questions'].find_one({'base_question_id': base_id, 'lang': 'zh-TW'})
        print(f'   Found matching zh-TW version: {zh_version is not None}')

# 檢查 i18n_mapping collection
print('\n3. I18n Mapping Collection:')
mappings = db['i18n_mapping'].count_documents({})
print(f'   Total mappings: {mappings}')

sample_mapping = db['i18n_mapping'].find_one()
if sample_mapping:
    print(f'   Sample mapping: {sample_mapping}')

# 檢查索引
print('\n4. Database Indexes:')
laws_indexes = [idx['name'] for idx in db['laws'].list_indexes()]
questions_indexes = [idx['name'] for idx in db['questions'].list_indexes()]
print(f'   Laws indexes: {laws_indexes}')
print(f'   Questions indexes: {questions_indexes}')

client.close()
print('\n✅ Schema 驗證完成')
