#!/usr/bin/env python3
"""
測試初始化腳本的基本功能
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("=" * 60)
print("測試初始化腳本環境")
print("=" * 60)

# 檢查必要的環境變數
print("\n1. 檢查環境變數:")
mongo_uri = os.environ.get('MONGO_URI')
api_key = os.environ.get('OPENROUTER_API_KEY')

print(f"   MONGO_URI: {'✅ 已設置' if mongo_uri else '❌ 未設置'}")
print(f"   OPENROUTER_API_KEY: {'✅ 已設置' if api_key else '❌ 未設置'}")

# 檢查必要的文件
print("\n2. 檢查必要文件:")
truth_laws_path = os.path.join(os.path.dirname(__file__), '..', 'knowledge', 'truth_law.json')
exists = os.path.exists(truth_laws_path)
print(f"   truth_law.json: {'✅ 存在' if exists else '❌ 不存在'}")

if exists:
    import json
    with open(truth_laws_path, 'r', encoding='utf-8') as f:
        laws = json.load(f)
    print(f"   法條數量: {len(laws)} 條")

# 嘗試連接資料庫
print("\n3. 測試資料庫連線:")
if mongo_uri:
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("   ✅ 成功連接到 MongoDB")
        
        db = client.get_database()
        laws_count = db['laws'].count_documents({})
        questions_count = db['questions'].count_documents({})
        
        print(f"   當前法條數量: {laws_count}")
        print(f"   當前題目數量: {questions_count}")
        
        client.close()
    except Exception as e:
        print(f"   ❌ 連接失敗: {e}")
else:
    print("   ⏭️  跳過（MONGO_URI 未設置）")

# 測試題目生成器
print("\n4. 測試題目生成器模組:")
try:
    from services.question_gen import QuestionGenerator
    print("   ✅ QuestionGenerator 模組載入成功")
    
    if api_key:
        gen = QuestionGenerator(api_key=api_key)
        print("   ✅ QuestionGenerator 初始化成功")
    else:
        print("   ⚠️  無 API Key，跳過初始化測試")
except Exception as e:
    print(f"   ❌ 載入失敗: {e}")

print("\n" + "=" * 60)
print("環境檢查完成")
print("=" * 60)
print("\n使用方式:")
print("  python scripts/init_db.py --local              # 初始化本地資料庫")
print("  python scripts/init_db.py --local --skip-laws  # 只生成題目")
print("  python scripts/init_db.py --help               # 查看所有選項")
