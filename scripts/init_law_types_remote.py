#!/usr/bin/env python3
"""
初始化 law_types 集合到遠端資料庫
並修復所有題目的 law_type 欄位

這個腳本解決以下問題：
1. 在資料庫中創建 law_types 集合
2. 根據 laws.type 自動匹配並更新 questions.law_type
"""

import os
import sys
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db.models import LAW_TYPES

load_dotenv()

def init_law_types():
    """初始化法規類型到遠端資料庫"""
    
    remote_uri = os.getenv('REMOTE_MONGO_URI')
    if not remote_uri:
        print("❌ 錯誤: 找不到 REMOTE_MONGO_URI 環境變數")
        return False
    
    print("=" * 80)
    print("初始化 law_types 集合到遠端資料庫")
    print("=" * 80)
    
    try:
        print(f"\n連線到遠端資料庫...")
        client = MongoClient(remote_uri, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        print("✅ 成功連接到遠端資料庫\n")
        
        db = client.get_database()
        
        # 定義所有法規類型（依照 slug 順序）
        law_types_data = [
            {
                'slug': 'patent-act',
                'name_zh': '專利法',
                'name_en': 'Patent Act',
                'description': '中華民國專利法',
                'order': 1
            },
            {
                'slug': 'examination',
                'name_zh': '專利審查基準',
                'name_en': 'Patent Examination Guidelines',
                'description': '專利申請審查相關規範',
                'order': 2,
                'laws_type': 'patent-examination'  # laws collection 中的 type 欄位值
            },
            {
                'slug': 'administrative-appeal',
                'name_zh': '訴願法',
                'name_en': 'Administrative Appeal Act',
                'description': '行政救濟程序法規',
                'order': 3
            },
            {
                'slug': 'administrative-litigation',
                'name_zh': '行政訴訟法',
                'name_en': 'Administrative Litigation Act',
                'description': '行政訴訟程序法規',
                'order': 4
            }
        ]
        
        # 1. 初始化 law_types 集合
        print("【步驟 1】初始化 law_types 集合")
        print("-" * 80)
        
        law_type_mapping = {}  # slug -> ObjectId 的映射
        
        for lt_data in law_types_data:
            slug = lt_data['slug']
            
            # 檢查是否已存在
            existing = db.law_types.find_one({'slug': slug})
            
            if existing:
                print(f"  ⏭️  {lt_data['name_zh']} 已存在，跳過")
                law_type_mapping[slug] = existing['_id']
            else:
                # 插入新的 law_type
                result = db.law_types.insert_one(lt_data)
                print(f"  ✅ 新增 {lt_data['name_zh']} (ID: {result.inserted_id})")
                law_type_mapping[slug] = result.inserted_id
        
        print(f"\n完成！共 {len(law_type_mapping)} 個法規類型")
        
        # 2. 修復 questions 的 law_type 欄位
        print("\n【步驟 2】修復 questions.law_type 欄位")
        print("-" * 80)
        
        # 統計當前狀況
        total_questions = db.questions.count_documents({})
        null_law_type = db.questions.count_documents({'law_type': None})
        
        print(f"總題目數: {total_questions}")
        print(f"law_type 為 NULL 的題目: {null_law_type}")
        
        if null_law_type == 0:
            print("\n✅ 所有題目都已有 law_type，無需修復")
        else:
            print(f"\n開始修復 {null_law_type} 個題目...\n")
            
            updated_count = 0
            error_count = 0
            
            # 建立 laws.type -> law_types._id 的映射
            type_to_law_type_id = {}
            for slug, law_type_id in law_type_mapping.items():
                lt = db.law_types.find_one({'_id': law_type_id})
                if lt:
                    # 如果有 laws_type 欄位，使用它；否則使用 slug
                    laws_type = lt.get('laws_type', slug)
                    type_to_law_type_id[laws_type] = law_type_id
            
            print("Laws type -> Law Type ID 映射:")
            for laws_type, lt_id in type_to_law_type_id.items():
                lt = db.law_types.find_one({'_id': lt_id})
                print(f"  {laws_type} -> {lt['name_zh']} ({lt_id})")
            print()
            
            # 遍歷所有 law_type 為 NULL 的題目
            for question in db.questions.find({'law_type': None}):
                try:
                    q_id = question['_id']
                    law_id = question.get('law_id')
                    
                    if not law_id:
                        print(f"  ⚠️  題目 {q_id} 沒有 law_id，跳過")
                        error_count += 1
                        continue
                    
                    # 查找對應的 law
                    law = db.laws.find_one({'_id': ObjectId(law_id)})
                    
                    if not law:
                        print(f"  ⚠️  找不到 law_id={law_id} 的法條，跳過")
                        error_count += 1
                        continue
                    
                    law_type_str = law.get('type')
                    
                    if not law_type_str:
                        print(f"  ⚠️  法條 {law_id} 沒有 type 欄位，跳過")
                        error_count += 1
                        continue
                    
                    # 找到對應的 law_type_id
                    law_type_id = type_to_law_type_id.get(law_type_str)
                    
                    if not law_type_id:
                        print(f"  ⚠️  找不到 type={law_type_str} 對應的 law_type，跳過")
                        error_count += 1
                        continue
                    
                    # 更新題目的 law_type
                    db.questions.update_one(
                        {'_id': q_id},
                        {'$set': {'law_type': law_type_id}}
                    )
                    
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        print(f"  已更新 {updated_count} 個題目...")
                
                except Exception as e:
                    print(f"  ❌ 處理題目 {question.get('_id')} 時發生錯誤: {e}")
                    error_count += 1
            
            print(f"\n完成！")
            print(f"  ✅ 成功更新: {updated_count} 個")
            print(f"  ❌ 錯誤: {error_count} 個")
        
        # 3. 驗證結果
        print("\n【步驟 3】驗證結果")
        print("-" * 80)
        
        print("\n法規類型列表:")
        for lt in db.law_types.find().sort('order', 1):
            print(f"  - {lt['name_zh']} (slug: {lt['slug']}, ID: {lt['_id']})")
        
        print("\n題目按 law_type 分布:")
        pipeline = [
            {'$group': {'_id': '$law_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        for result in db.questions.aggregate(pipeline):
            law_type_id = result['_id']
            count = result['count']
            
            if law_type_id is None:
                print(f"  - NULL: {count} 題 ❌")
            else:
                law_type = db.law_types.find_one({'_id': law_type_id})
                if law_type:
                    print(f"  - {law_type['name_zh']}: {count} 題 ✅")
                else:
                    print(f"  - 未知 (ID: {law_type_id}): {count} 題 ❌")
        
        null_count = db.questions.count_documents({'law_type': None})
        if null_count == 0:
            print("\n✅ 所有題目都已正確關聯到法規類型！")
        else:
            print(f"\n⚠️  仍有 {null_count} 個題目的 law_type 為 NULL")
        
        print("\n" + "=" * 80)
        print("✅ 初始化完成！")
        print("=" * 80)
        
        client.close()
        return True
        
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = init_law_types()
    sys.exit(0 if success else 1)
