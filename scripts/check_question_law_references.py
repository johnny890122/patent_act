#!/usr/bin/env python3
"""
Check if questions incorrectly reference law types in their content
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bson import ObjectId
from db.models import questions_collection, laws_collection, LAW_TYPES

def check_law_references():
    """Check if question content matches the law type"""
    print('=' * 60)
    print('檢查題目中的法條引用是否正確')
    print('=' * 60)
    
    # Get all questions
    questions = list(questions_collection.find({'is_deleted': False}))
    print(f'\n總題目數: {len(questions)}\n')
    
    issues = []
    
    for q in questions:
        # Get the law this question belongs to
        law = laws_collection.find_one({'_id': ObjectId(q['law_id'])})
        if not law:
            continue
        
        law_type = law.get('type', '')
        content = q.get('content', '')
        
        # Check if content mentions incorrect law type
        if law_type == 'administrative-litigation':
            # Should mention 行政訴訟法, not 專利法
            if '專利法' in content and '行政訴訟法' not in content:
                issues.append({
                    'question_id': str(q['_id']),
                    'law_type': law_type,
                    'article': law.get('article_number', 'N/A'),
                    'content': content[:100] + '...',
                    'issue': '題目提到「專利法」但實際是「行政訴訟法」'
                })
        elif law_type == 'administrative-appeal':
            # Should mention 訴願法, not 專利法
            if '專利法' in content and '訴願法' not in content:
                issues.append({
                    'question_id': str(q['_id']),
                    'law_type': law_type,
                    'article': law.get('article_number', 'N/A'),
                    'content': content[:100] + '...',
                    'issue': '題目提到「專利法」但實際是「訴願法」'
                })
    
    if issues:
        print(f'⚠️  發現 {len(issues)} 個法條引用錯誤的題目:\n')
        for idx, issue in enumerate(issues[:20], 1):  # Show first 20
            print(f"{idx}. 題目 ID: {issue['question_id']}")
            print(f"   法律類型: {issue['law_type']} ({LAW_TYPES[issue['law_type']]['name_zh']})")
            print(f"   法條: {issue['article']}")
            print(f"   問題: {issue['issue']}")
            print(f"   內容: {issue['content']}")
            print()
        
        if len(issues) > 20:
            print(f"... 還有 {len(issues) - 20} 個問題未顯示\n")
        
        print('=' * 60)
        print('原因分析:')
        print('  題目生成時，提示詞可能沒有明確指定法律名稱')
        print('  或 LLM 默認使用了「專利法」這個常見法律名稱')
        print()
        print('解決方案:')
        print('  1. 修改 question_gen.py 的提示詞，明確指定法律類型')
        print('  2. 重新生成這些題目')
        print('=' * 60)
    else:
        print('✅ 所有題目的法條引用都正確!')
        print('=' * 60)

if __name__ == '__main__':
    check_law_references()
