#!/usr/bin/env python3
"""
Fix law names in question content - replace incorrect references
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bson import ObjectId
from db.models import questions_collection, laws_collection, LAW_TYPES

def fix_law_names():
    """Fix incorrect law names in question content"""
    print('=' * 60)
    print('修正題目中的法律名稱')
    print('=' * 60)
    
    # Get all questions
    questions = list(questions_collection.find({'is_deleted': False}))
    print(f'\n檢查 {len(questions)} 個題目...\n')
    
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
        
        # Check if content mentions incorrect law type and needs fixing
        new_content = content
        fixed = False
        
        if law_type == 'administrative-litigation':
            # Should mention 行政訴訟法, not 專利法
            if '專利法' in content and '行政訴訟法' not in content:
                new_content = content.replace('專利法', '行政訴訟法')
                fixed = True
                
        elif law_type == 'administrative-appeal':
            # Should mention 訴願法, not 專利法
            if '專利法' in content and '訴願法' not in content:
                new_content = content.replace('專利法', '訴願法')
                fixed = True
        
        if fixed:
            fixes.append({
                'id': q['_id'],
                'law_type': law_type,
                'law_name': correct_law_name,
                'article': law.get('article_number', 'N/A'),
                'old_content': content[:100] + '...',
                'new_content': new_content[:100] + '...'
            })
    
    if not fixes:
        print('✅ 所有題目的法律名稱都正確，無需修正')
        return
    
    print(f'發現 {len(fixes)} 個需要修正的題目:\n')
    for idx, item in enumerate(fixes, 1):
        print(f"{idx}. ID: {item['id']}")
        print(f"   法律: {item['law_name']} ({item['article']})")
        print(f"   修正前: {item['old_content']}")
        print(f"   修正後: {item['new_content']}")
        print()
    
    # Apply fixes
    print('正在應用修正...\n')
    fixed_count = 0
    
    for item in fixes:
        # Get the full question again
        question = questions_collection.find_one({'_id': item['id']})
        if not question:
            continue
        
        # Fix content
        old_content = question['content']
        law = laws_collection.find_one({'_id': ObjectId(question['law_id'])})
        law_type = law.get('type', '')
        correct_law_name = LAW_TYPES.get(law_type, {}).get('name_zh', '')
        
        if law_type == 'administrative-litigation':
            new_content = old_content.replace('專利法', '行政訴訟法')
        elif law_type == 'administrative-appeal':
            new_content = old_content.replace('專利法', '訴願法')
        else:
            continue
        
        # Update in database
        result = questions_collection.update_one(
            {'_id': item['id']},
            {'$set': {'content': new_content}}
        )
        
        if result.modified_count > 0:
            fixed_count += 1
            print(f'✓ 已修正: {item["id"]}')
    
    print(f'\n✅ 成功修正 {fixed_count} 個題目')
    print('=' * 60)

if __name__ == '__main__':
    fix_law_names()
