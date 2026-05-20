#!/usr/bin/env python3
"""
Directly delete the 4 incorrect questions
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bson import ObjectId
from db.models import questions_collection

def delete_questions():
    """Soft delete the 4 known incorrect questions"""
    
    incorrect_ids = [
        "6a0dbb1341b8fa22372ccdab",  # 訴願法 17條 -> 提到專利法
        "6a0dbb2141b8fa22372ccdad",  # 訴願法 19條 -> 提到專利法
        "6a0354f88798ba53de6c60e9",  # 行政訴訟法 3-1條 -> 提到專利法
        "6a03563c886de87faba02fac",  # 行政訴訟法 3-1條 -> 提到專利法
    ]
    
    print('正在刪除 4 個法條引用錯誤的題目...\n')
    
    deleted = 0
    for qid in incorrect_ids:
        try:
            result = questions_collection.update_one(
                {'_id': ObjectId(qid)},
                {'$set': {'is_deleted': True}}
            )
            if result.modified_count > 0:
                deleted += 1
                print(f'✓ 已刪除: {qid}')
        except Exception as e:
            print(f'✗ 刪除失敗 {qid}: {e}')
    
    print(f'\n完成！共刪除 {deleted} 個題目')

if __name__ == '__main__':
    delete_questions()
