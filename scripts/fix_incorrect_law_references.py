#!/usr/bin/env python3
"""
Fix questions with incorrect law references - soft delete them
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bson import ObjectId
from db.models import questions_collection, laws_collection, LAW_TYPES

def fix_incorrect_references():
    """Soft delete questions with incorrect law references"""
    print('=' * 60)
    print('修復法條引用錯誤的題目')
    print('=' * 60)
    
    # Get all questions
    questions = list(questions_collection.find({'is_deleted': False}))
    print(f'\n總題目數: {len(questions)}\n')
    
    to_delete = []
    
    for q in questions:
        # Get the law this question belongs to
        law = laws_collection.find_one({'_id': ObjectId(q['law_id'])})
        if not law:
            continue
        
        law_type = law.get('type', '')
        content = q.get('content', '')
        
        # Check if content mentions incorrect law type
        should_delete = False
        
        if law_type == 'administrative-litigation':
            # Should mention 行政訴訟法, not 專利法
            if '專利法' in content and '行政訴訟法' not in content:
                should_delete = True
                
        elif law_type == 'administrative-appeal':
            # Should mention 訴願法, not 專利法
            if '專利法' in content and '訴願法' not in content:
                should_delete = True
        
        if should_delete:
            to_delete.append({
                'id': q['_id'],
                'law_type': law_type,
                'law_name': LAW_TYPES[law_type]['name_zh'],
                'article': law.get('article_number', 'N/A'),
                'content': content[:80] + '...'
            })
    
    if not to_delete:
        print('✅ 沒有發現需要修復的題目')
        return
    
    print(f'發現 {len(to_delete)} 個需要刪除的題目:\n')
    for idx, item in enumerate(to_delete, 1):
        print(f"{idx}. ID: {item['id']}")
        print(f"   法律: {item['law_name']} (type={item['law_type']})")
        print(f"   法條: {item['article']}")
        print(f"   內容: {item['content']}")
        print()
    
    # Ask for confirmation
    response = input(f'\n確定要刪除這 {len(to_delete)} 個題目嗎? (yes/no): ')
    
    if response.lower() != 'yes':
        print('取消操作')
        return
    
    # Soft delete
    deleted_count = 0
    for item in to_delete:
        result = questions_collection.update_one(
            {'_id': item['id']},
            {'$set': {'is_deleted': True}}
        )
        if result.modified_count > 0:
            deleted_count += 1
    
    print(f'\n✅ 成功刪除 {deleted_count} 個題目')
    print('\n下次生成題目時，會使用正確的法律名稱')
    print('=' * 60)

if __name__ == '__main__':
    fix_incorrect_references()
