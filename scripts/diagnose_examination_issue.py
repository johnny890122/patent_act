#!/usr/bin/env python3
"""
診斷專利審查基準相關問題
檢查 law_types、laws、questions 的完整狀態
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def diagnose():
    mongo_uri = os.getenv('MONGO_URI')
    client = MongoClient(mongo_uri)
    db = client['act_quiz_db']
    
    print("=" * 80)
    print("專利審查基準診斷報告")
    print("=" * 80)
    
    # 1. 檢查 law_types
    print("\n【1】檢查 law_types 集合")
    print("-" * 80)
    law_types_count = db.law_types.count_documents({})
    print(f"總法規類型數: {law_types_count}")
    
    if law_types_count == 0:
        print("❌ 問題：資料庫中沒有任何法規類型！")
        print("   解決方法：需要初始化 law_types")
    else:
        print("\n現有法規類型:")
        for lt in db.law_types.find():
            print(f"  - {lt.get('name_zh', 'N/A')} (slug: {lt.get('slug', 'N/A')})")
        
        # 檢查是否有 examination
        exam_type = db.law_types.find_one({'slug': 'examination'})
        if exam_type:
            print(f"\n✅ 找到專利審查基準法規類型: {exam_type['name_zh']}")
        else:
            print("\n❌ 問題：沒有找到 slug='examination' 的法規類型！")
    
    # 2. 檢查 laws (檢查多種可能的 type)
    print("\n【2】檢查 laws 集合")
    print("-" * 80)
    laws_count = db.laws.count_documents({})
    print(f"總法條數: {laws_count}")
    
    # 檢查各種可能的 examination 相關 type
    exam_types = [
        'examination',
        'patent-examination',
        'examination-guideline',
        'examination-guidelines'
    ]
    
    exam_laws_found = False
    for exam_type in exam_types:
        count = db.laws.count_documents({'type': exam_type})
        if count > 0:
            print(f"\n✅ 找到 type='{exam_type}' 的法條: {count} 條")
            exam_laws_found = True
            # 顯示幾個範例
            print("  範例:")
            for law in db.laws.find({'type': exam_type}).limit(3):
                print(f"    - {law.get('article_number', 'N/A')}: {law.get('content', '')[:60]}...")
    
    if not exam_laws_found:
        print("\n❌ 問題：沒有找到任何專利審查基準的法條！")
        print("   需要運行: python scripts/init_examination_guidelines.py --local")
    
    # 3. 檢查 questions
    print("\n【3】檢查 questions 集合")
    print("-" * 80)
    total_questions = db.questions.count_documents({})
    print(f"總題目數: {total_questions}")
    
    if total_questions > 0:
        # 分析題目的 law_type 分布
        print("\n題目按 law_type 分布:")
        pipeline = [
            {'$group': {'_id': '$law_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        
        has_valid_law_type = False
        for result in db.questions.aggregate(pipeline):
            law_type_id = result['_id']
            count = result['count']
            
            if law_type_id is None:
                print(f"  - NULL (無法規類型): {count} 題 ❌")
            else:
                law_type = db.law_types.find_one({'_id': law_type_id})
                if law_type:
                    print(f"  - {law_type['name_zh']}: {count} 題 ✅")
                    has_valid_law_type = True
                else:
                    print(f"  - 未知法規類型 (ID: {law_type_id}): {count} 題 ❌")
        
        # 檢查審查基準題目
        print("\n檢查審查基準相關題目:")
        # 透過 law_name 模式匹配（審查基準通常以章節編號開頭）
        patterns = [
            {'law_name': {'$regex': '^第.+章', '$options': 'i'}},
            {'law_name': {'$regex': '^[0-9].*', '$options': 'i'}},
        ]
        
        for pattern in patterns:
            count = db.questions.count_documents(pattern)
            if count > 0:
                print(f"  匹配模式 {pattern}: {count} 題")
                # 顯示範例
                sample = db.questions.find_one(pattern)
                if sample:
                    print(f"    範例 law_name: {sample.get('law_name', 'N/A')}")
                    print(f"    law_type: {sample.get('law_type', 'N/A')}")
    else:
        print("❌ 資料庫中沒有任何題目")
    
    # 4. 檢查 knowledge/examination 目錄
    print("\n【4】檢查 knowledge/examination 檔案")
    print("-" * 80)
    exam_dir = os.path.join(os.path.dirname(__file__), '..', 'knowledge', 'examination')
    if os.path.exists(exam_dir):
        import glob
        json_files = glob.glob(os.path.join(exam_dir, '*', '*.json'))
        json_files = [f for f in json_files if 'test' not in os.path.basename(f).lower()]
        print(f"找到 {len(json_files)} 個審查基準 JSON 檔案")
        if json_files:
            print("  檔案列表:")
            for f in sorted(json_files)[:10]:
                rel_path = os.path.relpath(f, os.path.dirname(__file__) + '/..')
                print(f"    - {rel_path}")
            if len(json_files) > 10:
                print(f"    ... 還有 {len(json_files) - 10} 個檔案")
    else:
        print("❌ 找不到 knowledge/examination 目錄")
    
    # 5. 總結
    print("\n" + "=" * 80)
    print("診斷總結")
    print("=" * 80)
    
    issues = []
    fixes = []
    
    if law_types_count == 0:
        issues.append("資料庫中沒有法規類型")
        fixes.append("運行初始化腳本來建立法規類型")
    
    if not exam_laws_found:
        issues.append("資料庫中沒有專利審查基準法條")
        fixes.append("運行: python scripts/init_examination_guidelines.py --local")
    
    if law_types_count > 0 and not db.law_types.find_one({'slug': 'examination'}):
        issues.append("缺少 slug='examination' 的法規類型")
        fixes.append("需要在 law_types 中新增專利審查基準類型")
    
    if issues:
        print("\n❌ 發現以下問題:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n🔧 建議修復步驟:")
        for i, fix in enumerate(fixes, 1):
            print(f"  {i}. {fix}")
    else:
        print("\n✅ 所有檢查通過！")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    diagnose()
