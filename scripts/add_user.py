#!/usr/bin/env python3
"""
CLI tool to add new users to the system.
Usage: python scripts/add_user.py <username> <display_name>
Example: python scripts/add_user.py alice "Alice Chen"
"""

import sys
import os
from datetime import datetime

# Add parent directory to path to import db.models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.models import users_collection, UserModel
from dataclasses import asdict


def add_user(username: str, display_name: str) -> bool:
    """
    Add a new user to the database.
    
    Args:
        username: Unique username for login
        display_name: Display name for the user
        
    Returns:
        bool: True if user was added successfully, False if username already exists
    """
    # Check if username already exists
    existing_user = users_collection.find_one({'username': username})
    if existing_user:
        print(f"❌ 錯誤：用戶名稱 '{username}' 已存在")
        return False
    
    # Create new user
    user = UserModel(
        username=username,
        display_name=display_name,
        created_at=datetime.utcnow(),
        last_login=None
    )
    
    # Insert into database
    user_dict = asdict(user)
    result = users_collection.insert_one(user_dict)
    
    if result.inserted_id:
        print(f"✅ 成功新增用戶：")
        print(f"   用戶名稱：{username}")
        print(f"   顯示名稱：{display_name}")
        print(f"   用戶 ID：{result.inserted_id}")
        return True
    else:
        print(f"❌ 新增用戶失敗")
        return False


def list_users():
    """List all users in the database."""
    users = list(users_collection.find())
    
    if not users:
        print("資料庫中沒有用戶")
        return
    
    print(f"\n目前系統中共有 {len(users)} 位用戶：")
    print("-" * 80)
    print(f"{'用戶名稱':<20} {'顯示名稱':<25} {'建立時間':<20} {'最後登入':<20}")
    print("-" * 80)
    
    for user in users:
        username = user.get('username', 'N/A')
        display_name = user.get('display_name', 'N/A')
        created_at = user.get('created_at', None)
        last_login = user.get('last_login', None)
        
        created_str = created_at.strftime('%Y-%m-%d %H:%M') if created_at else 'N/A'
        login_str = last_login.strftime('%Y-%m-%d %H:%M') if last_login else '從未登入'
        
        print(f"{username:<20} {display_name:<25} {created_str:<20} {login_str:<20}")
    
    print("-" * 80)


def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("用法：")
        print("  新增用戶：python scripts/add_user.py <username> <display_name>")
        print("  列出用戶：python scripts/add_user.py --list")
        print("")
        print("範例：")
        print('  python scripts/add_user.py alice "Alice Chen"')
        print('  python scripts/add_user.py bob "Bob Wu"')
        print('  python scripts/add_user.py --list')
        sys.exit(1)
    
    # Handle list command
    if sys.argv[1] == '--list' or sys.argv[1] == '-l':
        list_users()
        sys.exit(0)
    
    # Add user command
    if len(sys.argv) < 3:
        print("❌ 錯誤：請提供用戶名稱和顯示名稱")
        print('範例：python scripts/add_user.py alice "Alice Chen"')
        sys.exit(1)
    
    username = sys.argv[1].strip()
    display_name = sys.argv[2].strip()
    
    # Validate input
    if not username:
        print("❌ 錯誤：用戶名稱不能為空")
        sys.exit(1)
    
    if not display_name:
        print("❌ 錯誤：顯示名稱不能為空")
        sys.exit(1)
    
    # Validate username format (alphanumeric and underscore only)
    if not username.replace('_', '').replace('-', '').isalnum():
        print("❌ 錯誤：用戶名稱只能包含字母、數字、底線和連字號")
        sys.exit(1)
    
    # Add user
    success = add_user(username, display_name)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
