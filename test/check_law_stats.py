#!/usr/bin/env python3
"""檢查法條統計數據"""
import os
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
client = MongoClient(mongo_uri)
db = client.get_database()

print('=== 檢查法條統計數據 ===\n')

# 檢查有統計數據的中文法條
zh_law_with_stats = db['laws'].find_one({
    'lang': 'zh-TW',
    'attempt_count': {'$gt': 0}
})

if zh_law_with_stats:
    print('✅ 中文法條有統計數據:')
    print(f'  ID: {zh_law_with_stats["_id"]}')
    print(f'  條號: {zh_law_with_stats.get("article_number")}')
    print(f'  嘗試次數: {zh_law_with_stats.get("attempt_count")}')
    print(f'  平均分數: {zh_law_with_stats.get("avg_score")}')
    
    # 查找對應的英文版
    zh_id = str(zh_law_with_stats['_id'])
    mapping = db['i18n_mapping'].find_one({'zh_tw_law_id': zh_id})
    
    if mapping:
        en_law_id = mapping['en_law_id']
        en_law = db['laws'].find_one({'_id': ObjectId(en_law_id)})
        
        if en_law:
            print(f'\n對應的英文法條:')
            print(f'  ID: {en_law["_id"]}')
            print(f'  條號: {en_law.get("article_number")}')
            print(f'  嘗試次數: {en_law.get("attempt_count", "無")}')
            print(f'  平均分數: {en_law.get("avg_score", "無")}')
            
            if not en_law.get('attempt_count'):
                print('\n⚠️  英文法條沒有統計數據！')
        else:
            print(f'\n❌ 找不到英文法條: {en_law_id}')
    else:
        print(f'\n⚠️  找不到映射: {zh_id}')
else:
    print('⚠️  沒有找到有統計數據的中文法條')

# 檢查統計數據分佈
print('\n=== 統計數據分佈 ===')
zh_with_stats = db['laws'].count_documents({'lang': 'zh-TW', 'attempt_count': {'$gt': 0}})
en_with_stats = db['laws'].count_documents({'lang': 'en', 'attempt_count': {'$gt': 0}})
print(f'有統計數據的中文法條: {zh_with_stats}')
print(f'有統計數據的英文法條: {en_with_stats}')

client.close()
