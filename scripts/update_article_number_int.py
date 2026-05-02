#!/usr/bin/env python3
"""
為所有現有的法條記錄新增 article_number_int 欄位
"""
import os
import sys
import re
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def extract_article_number_int(article_number: str) -> int:
    """提取條號中的數字"""
    match = re.search(r'\d+', article_number)
    if match:
        return int(match.group())
    return 0

def main():
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/localdb')
    client = MongoClient(mongo_uri)
    db = client.get_database()
    laws_collection = db['laws']
    
    print("開始更新所有法條記錄...")
    
    # 找出所有記錄
    all_laws = list(laws_collection.find({}))
    print(f'找到 {len(all_laws)} 筆記錄')
    
    # 更新所有記錄
    updated = 0
    for law in all_laws:
        article_number = law.get('article_number', '')
        article_number_int = extract_article_number_int(article_number)
        
        result = laws_collection.update_one(
            {'_id': law['_id']},
            {'$set': {'article_number_int': article_number_int}}
        )
        
        if result.modified_count > 0:
            updated += 1
    
    print(f'\n✅ 成功更新 {updated} 筆記錄')
    
    # 驗證
    with_int = laws_collection.count_documents({'article_number_int': {'$exists': True}})
    print(f'現在有 article_number_int 欄位的記錄: {with_int}')
    
    # 顯示前幾筆排序結果
    print('\n前 15 筆記錄（按 article_number_int 排序）:')
    for law in laws_collection.find({}).sort('article_number_int', 1).limit(15):
        print(f"  {law.get('article_number_int', 0):3d} - {law.get('article_number', 'N/A')}")
    
    client.close()

if __name__ == '__main__':
    main()
