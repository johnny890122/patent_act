#!/usr/bin/env python3
"""
診斷遠端資料庫的專利審查基準相關問題
檢查 law_types、laws、questions 的完整狀態
"""

import os
import sys
from pymongo import MongoClient
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def diagnose_remote():
    remote_uri = os.getenv('REMOTE_MONGO_URI')
    
    if not remote_uri:
        print("❌ 錯誤: 找不到 REMOTE_MONGO_URI 環境變數")
        print("   請在 .env 檔案中設定 REMOTE_MONGO_URI")
        return
    
    print(f"連線到遠端資料庫: {remote_uri[:50]}...")
    
    try:
        client = MongoClient(remote_uri, serverSelectionTimeoutMS=10000)
        # 測試連線
        client.admin.command('ping')
        print("✅ 成功連接到遠端資料庫\n")
    except Exception as e:
        print(f"❌ 無法連接到遠端資料庫: {e}")
        return
    
    db = client.get_database()
    
    print("=" * 80)
    print("遠端資料庫 - 專利審查基準診斷報告")
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
            print(f"  - {lt.get('name_zh', 'N/A')} (slug: {lt.get('slug', 'N/A')}, ID: {lt['_id']})")
        
        # 檢查是否有 examination
        exam_type = db.law_types.find_one({'slug': 'examination'})
        if exam_type:
            print(f"\n✅ 找到專利審查基準法規類型:")
            print(f"   名稱: {exam_type['name_zh']}")
            print(f"   ID: {exam_type['_id']}")
        else:
            print("\n❌ 問題：沒有找到 slug='examination' 的法規類型！")
    
    # 2. 檢查 laws (檢查多種可能的 type)
    print("\n【2】檢查 laws 集合")
    print("-" * 80)
    laws_count = db.laws.count_documents({})
    print(f"總法條數: {laws_count}")
    
    if laws_count > 0:
        # 按 type 分組統計
        print("\n法條按 type 分布:")
        pipeline = [
            {'$group': {'_id': '$type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        for result in db.laws.aggregate(pipeline):
            print(f"  - {result['_id']}: {result['count']} 條")
    
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
        print("   需要運行: python scripts/init_examination_guidelines.py --remote")
    
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
        
        for result in db.questions.aggregate(pipeline):
            law_type_id = result['_id']
            count = result['count']
            
            if law_type_id is None:
                print(f"  - NULL (無法規類型): {count} 題 ❌")
            else:
                law_type = db.law_types.find_one({'_id': law_type_id})
                if law_type:
                    print(f"  - {law_type['name_zh']} (ID: {law_type_id}): {count} 題 ✅")
                else:
                    print(f"  - 未知法規類型 (ID: {law_type_id}): {count} 題 ❌")
        
        # 如果有 examination law_type，檢查其題目
        exam_type = db.law_types.find_one({'slug': 'examination'})
        if exam_type:
            exam_questions = db.questions.count_documents({'law_type': exam_type['_id']})
            print(f"\n專利審查基準題目數: {exam_questions}")
            
            if exam_questions > 0:
                print("  前3題範例:")
                for q in db.questions.find({'law_type': exam_type['_id']}).limit(3):
                    print(f"    - {q.get('law_name', 'N/A')}: {q.get('content', '')[:60]}...")
            else:
                print("  ❌ 沒有專利審查基準的題目")
        
    else:
        print("❌ 資料庫中沒有任何題目")
    
    # 4. 總結
    print("\n" + "=" * 80)
    print("診斷總結")
    print("=" * 80)
    
    issues = []
    fixes = []
    
    if law_types_count == 0:
        issues.append("資料庫中沒有法規類型")
        fixes.append("需要初始化 law_types（可能需要運行完整的資料庫初始化腳本）")
    elif not db.law_types.find_one({'slug': 'examination'}):
        issues.append("缺少 slug='examination' 的法規類型")
        fixes.append("需要在 law_types 中新增專利審查基準類型")
    
    if not exam_laws_found:
        issues.append("資料庫中沒有專利審查基準法條")
        fixes.append("運行: python scripts/init_examination_guidelines.py --remote")
    
    # 檢查 examination 題目
    exam_type = db.law_types.find_one({'slug': 'examination'})
    if exam_type:
        exam_questions = db.questions.count_documents({'law_type': exam_type['_id']})
        if exam_questions == 0:
            issues.append("資料庫中沒有專利審查基準的題目")
            fixes.append("題目需要在用戶答題時自動生成，或使用題目生成腳本")
    
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
    
    client.close()

if __name__ == '__main__':
    diagnose_remote()
