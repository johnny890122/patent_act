#!/usr/bin/env python3
"""
Fix law names in questions on remote (Heroku) database
Connects to MONGODB_URI_REMOTE from .env
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

# Law type mappings
LAW_TYPES = {
    "patent-act": {"name_zh": "專利法"},
    "administrative-appeal": {"name_zh": "訴願法"},
    "administrative-litigation": {"name_zh": "行政訴訟法"}
}

def fix_remote_law_names():
    """Fix incorrect law names in remote database questions"""
    
    # Connect to remote MongoDB
    # Try MONGODB_URI_REMOTE first, then fall back to MONGODB_URI
    remote_uri = os.environ.get('REMOTE_MONGO_URI') or os.environ.get('MONGODB_URI')
    if not remote_uri:
        print('❌ 錯誤: 找不到 MONGODB_URI_REMOTE 或 MONGODB_URI 環境變數')
        print('請在 .env 文件中設置遠端數據庫連接')
        return
    
    # Confirm with user which database we're connecting to
    if 'mongodb://127.0.0.1' in remote_uri or 'localhost' in remote_uri:
        print('⚠️  警告: 即將連接到本地數據庫')
        response = input('確定要修正本地數據庫嗎? (yes/no): ')
        if response.lower() != 'yes':
            print('取消操作')
            return
    else:
        print(f'⚠️  即將連接到遠端數據庫')
        print(f'   URI: {remote_uri[:50]}...')
        response = input('確定要修正遠端數據庫嗎? (yes/no): ')
        if response.lower() != 'yes':
            print('取消操作')
            return
    
    print('=' * 60)
    print('修正遠端數據庫中的法律名稱')
    print('=' * 60)
    
    try:
        client = MongoClient(remote_uri)
        db = client.get_database()  # Use default database from URI
        questions_collection = db['questions']
        laws_collection = db['laws']
        
        print(f'\n✓ 已連接到遠端數據庫')
        
        # Get all non-deleted questions
        questions = list(questions_collection.find({'is_deleted': False}))
        print(f'✓ 找到 {len(questions)} 個題目\n')
        
        fixes = []
        
        for q in questions:
            # Get the law this question belongs to
            law = laws_collection.find_one({'_id': ObjectId(q['law_id'])})
            if not law:
                continue
            
            law_type = law.get('type', '')
            content = q.get('content', '')
            correct_law_name = LAW_TYPES.get(law_type, {}).get('name_zh', '')
            
            if not correct_law_name:
                continue
            
            # Check if content mentions incorrect law type
            needs_fix = False
            new_content = content
            
            if law_type == 'administrative-litigation':
                # Should mention 行政訴訟法, not 專利法
                if '專利法' in content and '行政訴訟法' not in content:
                    new_content = content.replace('專利法', '行政訴訟法')
                    needs_fix = True
                    
            elif law_type == 'administrative-appeal':
                # Should mention 訴願法, not 專利法
                if '專利法' in content and '訴願法' not in content:
                    new_content = content.replace('專利法', '訴願法')
                    needs_fix = True
            
            if needs_fix:
                fixes.append({
                    'id': q['_id'],
                    'law_type': law_type,
                    'law_name': correct_law_name,
                    'article': law.get('article_number', 'N/A'),
                    'old_content': content,
                    'new_content': new_content
                })
        
        if not fixes:
            print('✅ 所有題目的法律名稱都正確，無需修正')
            client.close()
            return
        
        print(f'發現 {len(fixes)} 個需要修正的題目:\n')
        for idx, item in enumerate(fixes, 1):
            print(f"{idx}. ID: {item['id']}")
            print(f"   法律: {item['law_name']} ({item['article']})")
            print(f"   修正: 「專利法」→「{item['law_name']}」")
            print(f"   內容預覽: {item['old_content'][:80]}...")
            print()
        
        # Apply fixes
        print('正在應用修正...\n')
        fixed_count = 0
        
        for item in fixes:
            result = questions_collection.update_one(
                {'_id': item['id']},
                {'$set': {'content': item['new_content']}}
            )
            
            if result.modified_count > 0:
                fixed_count += 1
                print(f'✓ 已修正: {item["id"]} ({item["article"]})')
        
        print(f'\n✅ 成功修正 {fixed_count} 個遠端題目')
        print('=' * 60)
        
        client.close()
        
    except Exception as e:
        print(f'\n❌ 錯誤: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    fix_remote_law_names()
