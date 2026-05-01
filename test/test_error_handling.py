#!/usr/bin/env python3
"""測試改進後的錯誤處理功能"""
import json
import os
import shutil
from datetime import datetime

print("=== 錯誤處理測試 ===\n")

# Backup original mock data
backup_path = 'knowledge/mock_laws.json.backup'
original_path = 'knowledge/mock_laws.json'

if os.path.exists(original_path):
    shutil.copy(original_path, backup_path)
    print(f"✅ 已備份原始資料至 {backup_path}\n")

# Test 1: Invalid JSON format
print("測試 1: 無效的 JSON 格式")
test_file = 'knowledge/test_invalid.json'
with open(test_file, 'w', encoding='utf-8') as f:
    f.write('{ invalid json }')
print(f"✅ 建立無效 JSON 測試檔案: {test_file}")
print("   請執行: curl -X POST http://localhost:5001/admin/init-laws")
print("   預期結果: 400 Bad Request\n")

# Test 2: Invalid data format (not a list)
print("測試 2: 無效的資料格式（非列表）")
test_file2 = 'knowledge/test_not_list.json'
with open(test_file2, 'w', encoding='utf-8') as f:
    json.dump({"error": "this is not a list"}, f)
print(f"✅ 建立非列表格式測試檔案: {test_file2}")
print("   請手動將此檔案重命名為 mock_laws.json 後測試")
print("   預期結果: 400 Bad Request\n")

# Test 3: Missing required field
print("測試 3: 缺少必要欄位")
test_file3 = 'knowledge/test_missing_field.json'
invalid_data = [
    {
        "article_number": "測試條",
        # 缺少 content 欄位
        "chapter": "測試章",
        "is_starred": False,
        "total_score": 0.0,
        "attempt_count": 0,
        "avg_score": 0.0
    }
]
with open(test_file3, 'w', encoding='utf-8') as f:
    json.dump(invalid_data, f, ensure_ascii=False, indent=2)
print(f"✅ 建立缺少欄位測試檔案: {test_file3}")
print("   請手動將此檔案重命名為 mock_laws.json 後測試")
print("   預期結果: 207 Multi-Status (部分成功)\n")

# Test 4: Mixed valid and invalid data
print("測試 4: 混合有效與無效資料")
test_file4 = 'knowledge/test_mixed.json'
mixed_data = [
    {
        "article_number": "有效條文",
        "content": "這是有效的內容",
        "chapter": "測試章",
        "is_starred": False,
        "total_score": 0.0,
        "attempt_count": 0,
        "avg_score": 0.0
    },
    {
        "article_number": "無效條文",
        # 缺少 content
        "chapter": "測試章"
    }
]
with open(test_file4, 'w', encoding='utf-8') as f:
    json.dump(mixed_data, f, ensure_ascii=False, indent=2)
print(f"✅ 建立混合資料測試檔案: {test_file4}\n")

print("=== 測試檔案準備完成 ===")
print("\n📝 手動測試步驟:")
print("1. 保留原始 mock_laws.json")
print("2. 將測試檔案重命名為 mock_laws.json")
print("3. 執行 curl -X POST http://localhost:5001/admin/init-laws")
print("4. 檢查回應和日誌輸出")
print("5. 測試完成後還原 mock_laws.json")
print(f"\n還原指令: cp {backup_path} {original_path}")

# Clean up test files
print("\n清理測試檔案...")
for f in [test_file, test_file2, test_file3, test_file4]:
    if os.path.exists(f):
        os.remove(f)
        print(f"✅ 已刪除: {f}")

print("\n✅ 測試準備完成")
