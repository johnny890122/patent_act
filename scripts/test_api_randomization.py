#!/usr/bin/env python3
"""
Test API-level question randomization
Simulates what happens when a user requests a quiz session
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bson import ObjectId
from services.inventory import QuestionInventory

def test_api_level():
    """Test the get_session_questions method (used by API)"""
    print('=' * 60)
    print('測試 API 層級的題目隨機化')
    print('=' * 60)
    
    # Create a fake user for testing
    test_user_id = str(ObjectId())
    
    inventory = QuestionInventory()
    
    print(f'\n模擬用戶 {test_user_id[:8]}... 連續 3 次請求測驗\n')
    
    all_first_questions = []
    
    for session_num in range(1, 4):
        print(f'第 {session_num} 次測驗:')
        print('-' * 60)
        
        # This is what the API actually calls
        questions, is_loading = inventory.get_session_questions(
            question_type="MCQ",
            session_mode="new",
            count=10,
            lang='zh-TW',
            user_id=test_user_id,
            law_type='patent-act'
        )
        
        # Get the first 3 question IDs
        first_3_ids = [q['_id'] for q in questions[:3]]
        all_first_questions.append(tuple(first_3_ids))
        
        print(f'  取得 {len(questions)} 題')
        print(f'  前 3 題 ID: {first_3_ids}')
        print()
    
    # Check if all sessions are different
    unique_sessions = len(set(all_first_questions))
    
    print('=' * 60)
    print('結果分析:')
    print(f'  總測驗次數: 3')
    print(f'  不同的題目組合: {unique_sessions}')
    
    if unique_sessions == 3:
        print('\n✅ 成功: 每次測驗的題目都不同!')
        print('   隨機化功能正常運作')
    elif unique_sessions == 1:
        print('\n❌ 失敗: 所有測驗的題目完全相同')
        print('   隨機化功能未生效')
    else:
        print(f'\n⚠️ 部分成功: {unique_sessions}/3 個不同組合')
        print('   可能存在隨機性問題')
    
    print('=' * 60)

if __name__ == '__main__':
    test_api_level()
