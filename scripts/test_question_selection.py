#!/usr/bin/env python3
"""
Test actual question selection logic
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import Counter
from bson import ObjectId
from db.models import questions_collection, laws_collection, user_progress_collection
from services.inventory import QuestionInventory

def test_selection():
    """Test the actual question selection logic"""
    print('=' * 60)
    print('測試實際題目選取邏輯')
    print('=' * 60)
    
    # Get a test user (or create a fake one for testing)
    test_user_id = ObjectId()  # Fake user with no progress
    
    inventory = QuestionInventory()
    
    # Test 1: Fetch 10 MCQ questions in "new" mode
    print('\n測試 1: 取 10 題 MCQ (new mode)')
    print('-' * 60)
    
    questions = inventory.fetch_questions(
        question_type="MCQ",
        session_mode="new",
        count=10,
        lang='zh-TW',
        user_id=str(test_user_id),
        law_type='patent-act'
    )
    
    print(f"取得 {len(questions)} 題")
    
    # Analyze the article distribution
    article_nums = []
    for q in questions:
        law = laws_collection.find_one({'_id': ObjectId(q['law_id'])})
        if law:
            art_num = law.get('article_number_int', 0)
            article_nums.append(art_num)
            print(f"  題目 {q['_id']}: 第 {art_num} 條 - {q['content'][:50]}...")
    
    print(f"\n法條分佈:")
    counter = Counter(article_nums)
    for art_num, count in sorted(counter.items()):
        print(f"  第 {art_num} 條: {count} 題")
    
    # Check if concentrated in 1-5
    count_1_5 = sum(1 for a in article_nums if 1 <= a <= 5)
    print(f"\n前 1-5 條: {count_1_5}/10 = {count_1_5/10*100:.1f}%")
    
    if count_1_5 > 5:
        print("⚠️  警告: 題目過度集中在前 1-5 條!")
    
    # Test 2: Run 5 times to see if it's always the same
    print('\n\n測試 2: 連續 5 次取題，檢查是否每次都一樣')
    print('-' * 60)
    
    all_first_articles = []
    for i in range(5):
        questions = inventory.fetch_questions(
            question_type="MCQ",
            session_mode="new",
            count=10,
            lang='zh-TW',
            user_id=str(test_user_id),
            law_type='patent-act'
        )
        
        first_articles = []
        for q in questions[:3]:  # Just check first 3
            law = laws_collection.find_one({'_id': ObjectId(q['law_id'])})
            if law:
                first_articles.append(law.get('article_number_int', 0))
        
        all_first_articles.append(tuple(first_articles))
        print(f"  第 {i+1} 次: 前 3 題來自第 {first_articles} 條")
    
    # Check if all runs are identical
    if len(set(all_first_articles)) == 1:
        print("\n❌ 問題確認: 每次取題結果完全相同 - 沒有隨機化!")
        print("   原因: inventory.py 的 _fetch_by_mode 直接返回 filtered_questions[:count]")
        print("   解決方案: 需要加入 random.sample() 或 random.shuffle()")
    else:
        print("\n✅ 結果: 每次取題有所不同 - 有隨機化")

if __name__ == '__main__':
    test_selection()
