#!/usr/bin/env python3
"""
Debug script to analyze question distribution and selection logic
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import Counter, defaultdict
from bson import ObjectId
from db.models import questions_collection, laws_collection, user_progress_collection

def analyze_distribution():
    """Analyze the distribution of questions across articles"""
    print('=' * 60)
    print('題目分佈分析報告')
    print('=' * 60)
    
    # Get all non-deleted questions
    questions = list(questions_collection.find({'is_deleted': False}))
    print(f'\n總題目數: {len(questions)}')
    
    # Analyze by article number
    article_stats = defaultdict(lambda: {
        'count': 0, 
        'article_num': '', 
        'type': '',
        'lang': '',
        'mcq': 0,
        'short': 0
    })
    
    for q in questions:
        law = laws_collection.find_one({'_id': ObjectId(q['law_id'])})
        if law and law.get('type') == 'patent-act':
            art_int = law.get('article_number_int', 0)
            article_stats[art_int]['count'] += 1
            article_stats[art_int]['article_num'] = law.get('article_number', 'N/A')
            article_stats[art_int]['type'] = law.get('type', 'N/A')
            article_stats[art_int]['lang'] = law.get('lang', 'zh-TW')
            
            if q.get('type') == 'MCQ':
                article_stats[art_int]['mcq'] += 1
            else:
                article_stats[art_int]['short'] += 1
    
    # Print first 20 articles
    print('\n前 20 條法條的題目分佈:')
    print(f"{'法條編號':<12} | {'MCQ':>5} | {'簡答':>5} | {'總計':>5}")
    print('-' * 40)
    
    total_1_5 = 0
    total_1_20 = 0
    
    for i in range(1, 21):
        if i in article_stats:
            info = article_stats[i]
            print(f"第 {i:2d} 條       | {info['mcq']:5d} | {info['short']:5d} | {info['count']:5d}")
            if i <= 5:
                total_1_5 += info['count']
            total_1_20 += info['count']
        else:
            print(f"第 {i:2d} 條       |     0 |     0 |     0")
    
    total_patent_acts = sum(info['count'] for info in article_stats.values())
    
    print('\n' + '=' * 60)
    print('統計摘要:')
    print(f"  專利法題目總數:          {total_patent_acts}")
    print(f"  前 1-5 條題目數:          {total_1_5}")
    print(f"  前 1-20 條題目數:         {total_1_20}")
    print(f"  前 1-5 條占比:            {total_1_5/total_patent_acts*100:.1f}%")
    print(f"  前 1-20 條占比:           {total_1_20/total_patent_acts*100:.1f}%")
    print('=' * 60)
    
    # Analyze the fetch logic simulation
    print('\n模擬題目選取邏輯:')
    print('-' * 60)
    
    # Get patent-act law IDs
    patent_law_ids = [
        str(law["_id"])
        for law in laws_collection.find({"type": "patent-act", "lang": "zh-TW"}, {"_id": 1})
    ]
    
    print(f"專利法(繁中)法條數: {len(patent_law_ids)}")
    
    # Get all questions for patent-act
    all_patent_questions = list(questions_collection.find({
        "type": "MCQ",
        "is_deleted": False,
        "law_id": {"$in": patent_law_ids}
    }))
    
    print(f"專利法 MCQ 題目數: {len(all_patent_questions)}")
    
    # Check distribution of these questions by article
    question_articles = []
    for q in all_patent_questions[:50]:  # Check first 50 questions in DB order
        law = laws_collection.find_one({'_id': ObjectId(q['law_id'])})
        if law:
            question_articles.append(law.get('article_number_int', 0))
    
    print(f"\n資料庫中前 50 題的法條分佈:")
    article_counter = Counter(question_articles)
    for art_num, count in sorted(article_counter.items())[:10]:
        print(f"  第 {art_num} 條: {count} 題")
    
    # Check if there's an issue with ordering
    print(f"\n⚠️  問題分析:")
    if question_articles[:10].count(1) > 3 or question_articles[:10].count(2) > 3:
        print("  ❌ 發現問題: 資料庫中前幾條記錄過度集中在第 1-5 條!")
        print("  原因: fetch_questions 沒有做隨機化，直接按 _id 順序取出")
        print("  解決方案: 在 inventory.py 的 _fetch_by_mode 中加入隨機化邏輯")
    else:
        print("  ✅ 資料庫記錄分佈看起來正常")

if __name__ == '__main__':
    analyze_distribution()
