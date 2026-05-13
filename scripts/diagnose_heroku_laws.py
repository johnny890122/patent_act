#!/usr/bin/env python3
"""
診斷 Heroku 資料庫法條問題
Diagnose Heroku database law articles issue

檢查遠端資料庫的法條數量和索引狀態
"""

import sys
import os
from pymongo import MongoClient

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import LAW_TYPES

# 重要: Heroku 生產環境使用 MONGO_URI，不是 REMOTE_MONGO_URI
# 這是問題的關鍵所在！
HEROKU_MONGO_URI = os.environ.get('MONGO_URI')  # Heroku 生產環境
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI')  # 開發用的遠端資料庫


def diagnose_database(uri_name, mongo_uri):
    """診斷資料庫狀態"""
    if not mongo_uri:
        print(f"❌ {uri_name} 未設定")
        return False
    
    print(f"\n{'='*60}")
    print(f"診斷資料庫: {uri_name}")
    print(f"{'='*60}")
    
    try:
        # 連接資料庫
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print(f"✅ 成功連接")
        
        db = client.get_database()
        laws_collection = db['laws']
        
        print(f"\n資料庫名稱: {db.name}")
        
        # 檢查每種法律類型的數量
        print(f"\n📊 法條統計:")
        print(f"{'法律類型':<30} {'中文條數':<12} {'英文條數':<12}")
        print("-" * 60)
        
        total_zh = 0
        total_en = 0
        
        for law_code, law_info in LAW_TYPES.items():
            count_zh = laws_collection.count_documents({
                'type': law_code,
                'lang': 'zh-TW'
            })
            count_en = laws_collection.count_documents({
                'type': law_code,
                'lang': 'en'
            })
            
            status = "✅" if count_zh > 0 else "❌"
            print(f"{status} {law_info['name_zh']:<28} {count_zh:<12} {count_en:<12}")
            
            total_zh += count_zh
            total_en += count_en
        
        print("-" * 60)
        print(f"   {'總計':<28} {total_zh:<12} {total_en:<12}")
        
        # 檢查索引
        print(f"\n🔍 索引狀態:")
        indexes = laws_collection.index_information()
        
        required_indexes = [
            'article_number_int_1',
            'chapter_1',
            'lang_1',
            'type_1',
            'type_1_lang_1',
            'type_1_article_number_int_1',
            'article_number_lang_type_unique'
        ]
        
        for idx_name in required_indexes:
            exists = idx_name in indexes
            status = "✅" if exists else "❌"
            print(f"   {status} {idx_name}")
        
        # 檢查範例資料
        print(f"\n📝 範例法條 (訴願法):")
        sample_appeal = laws_collection.find_one({
            'type': 'administrative-appeal',
            'lang': 'zh-TW'
        })
        if sample_appeal:
            print(f"   ✅ 找到: {sample_appeal.get('article_number', 'N/A')}")
            print(f"      內容長度: {len(sample_appeal.get('content', ''))} 字元")
        else:
            print(f"   ❌ 未找到訴願法資料")
        
        print(f"\n📝 範例法條 (行政訴訟法):")
        sample_litigation = laws_collection.find_one({
            'type': 'administrative-litigation',
            'lang': 'zh-TW'
        })
        if sample_litigation:
            print(f"   ✅ 找到: {sample_litigation.get('article_number', 'N/A')}")
            print(f"      內容長度: {len(sample_litigation.get('content', ''))} 字元")
        else:
            print(f"   ❌ 未找到行政訴訟法資料")
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ 診斷失敗: {e}")
        return False


def main():
    print("="*60)
    print("🩺 Heroku 資料庫診斷工具")
    print("="*60)
    
    print("\n⚠️  重要提示:")
    print("   Heroku 生產環境使用 MONGO_URI")
    print("   開發用遠端資料庫使用 REMOTE_MONGO_URI")
    print("   這兩個環境變數可能指向不同的資料庫！")
    
    # 診斷兩個資料庫
    success = True
    
    if HEROKU_MONGO_URI:
        success = diagnose_database("MONGO_URI (Heroku 生產環境)", HEROKU_MONGO_URI) and success
    else:
        print("\n⚠️  MONGO_URI 未設定")
    
    if REMOTE_MONGO_URI:
        success = diagnose_database("REMOTE_MONGO_URI (開發用遠端)", REMOTE_MONGO_URI) and success
    else:
        print("\n⚠️  REMOTE_MONGO_URI 未設定")
    
    # 比較兩個資料庫
    if HEROKU_MONGO_URI and REMOTE_MONGO_URI:
        print(f"\n{'='*60}")
        print("📋 診斷結論:")
        print(f"{'='*60}")
        
        if HEROKU_MONGO_URI == REMOTE_MONGO_URI:
            print("✅ MONGO_URI 和 REMOTE_MONGO_URI 指向同一個資料庫")
        else:
            print("⚠️  MONGO_URI 和 REMOTE_MONGO_URI 指向不同的資料庫！")
            print("\n💡 這可能是問題的根源：")
            print("   1. 您使用 init script --target remote 插入資料到 REMOTE_MONGO_URI")
            print("   2. 但 Heroku 應用程式連接的是 MONGO_URI")
            print("   3. 因此 Heroku 上看不到新插入的法條")
            print("\n🔧 解決方案：")
            print("   選項 1: 在 Heroku Config Vars 中設定 MONGO_URI 為您的 MongoDB Atlas URI")
            print("   選項 2: 使用以下命令將資料同步到 Heroku 資料庫")
            print("           heroku config:get MONGO_URI")
            print("           然後用該 URI 重新運行 init scripts")
    
    print(f"\n{'='*60}")
    if success:
        print("✅ 診斷完成")
    else:
        print("❌ 診斷過程中發生錯誤")
    print(f"{'='*60}\n")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
