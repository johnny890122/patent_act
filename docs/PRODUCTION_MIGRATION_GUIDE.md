# 生產環境多用戶遷移指南

## 📋 概述
本指南詳細說明如何將生產環境的「專利法 AI 刷題助手」從單用戶系統遷移至多用戶系統。

**預估停機時間**：5-10 分鐘  
**資料風險**：低（有完整備份機制）  
**可回滾**：是

---

## ✅ 本地測試結果

### 測試環境資料規模
- **Laws**: 336 條法規
- **Questions**: 720 題
- **User Progress**: 69 筆記錄
- **I18n Mapping**: 168 筆對應

### 遷移成果
```
✅ Created default admin user
✅ Updated 69 progress records with user_id
✅ Created 61 user_law_stats records
✅ Created 21 user_question_stars records
✅ Removed deprecated fields from collections
```

### 測試時間
- 本地資料備份：< 1 秒
- 資料複製（遠端→本地）：~5 秒
- 遷移執行：< 2 秒
- **總計**：~10 秒

---

## 🎯 生產環境遷移步驟

### 階段 1: 準備階段（遷移前 1 天）

#### 1.1 確認程式碼已部署
```bash
# 確保所有多用戶程式碼已推送到 Git
git status
git push origin main

# 確認 Heroku 已部署最新版本
git push heroku main
```

#### 1.2 設定環境變數
在 Heroku 設定 `SECRET_KEY`：
```bash
# 生成安全的 SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# 設定到 Heroku
heroku config:set SECRET_KEY=<生成的金鑰>
```

#### 1.3 通知用戶
通知所有用戶系統將進行維護升級：
- 維護時間：[具體時間]
- 預估停機：5-10 分鐘
- 影響：需重新登入

---

### 階段 2: 遷移執行（維護時段）

#### 2.1 建立資料庫備份
```bash
# 方法 1: MongoDB Atlas 控制台手動備份
1. 登入 MongoDB Atlas
2. 進入 Clusters → Backups
3. 建立手動快照（Snapshot）
4. 記錄快照名稱和時間

# 方法 2: 使用 mongodump（本地備份）
mongodump --uri="<REMOTE_MONGO_URI>" --out=./backup_$(date +%Y%m%d_%H%M%S)
```

#### 2.2 啟動維護模式（可選）
```bash
# Heroku 維護模式
heroku maintenance:on

# 或於應用中顯示維護頁面
# 修改 app.py 暫時返回 503 維護頁面
```

#### 2.3 執行遷移腳本
```bash
# 連線到 Heroku dyno 執行遷移
heroku run bash

# 在 Heroku dyno 內執行
python scripts/migrate_to_multiuser.py --dry-run  # 先 dry-run 檢查
python scripts/migrate_to_multiuser.py             # 實際執行

# 驗證結果
python scripts/add_user.py --list
```

**預期輸出**：
```
✅ Admin user already exists (ID: ...)
✅ Updated X progress records with user_id
✅ Created X user_law_stats records
✅ Created X user_question_stars records
```

#### 2.4 驗證遷移結果
```bash
# 檢查用戶數量
python scripts/add_user.py --list

# 預期：顯示 1 位 admin 用戶

# 測試登入功能（瀏覽器）
# 1. 訪問 https://your-app.herokuapp.com/auth/login
# 2. 輸入 username: admin
# 3. 確認能成功登入並看到 dashboard
```

#### 2.5 新增額外用戶（如需要）
```bash
# 在 Heroku dyno 內執行
python scripts/add_user.py alice "Alice Chen"
python scripts/add_user.py bob "Bob Wu"

# 列出所有用戶
python scripts/add_user.py --list
```

#### 2.6 關閉維護模式
```bash
# Heroku 維護模式
heroku maintenance:off
```

---

### 階段 3: 驗證與監控（遷移後 1 小時）

#### 3.1 功能測試
- [ ] 登入功能正常
- [ ] 用戶 A 和用戶 B 資料隔離
- [ ] 進度追蹤正常運作
- [ ] 收藏功能正常
- [ ] 測驗功能正常

#### 3.2 監控指標
```bash
# 查看應用日誌
heroku logs --tail

# 監控錯誤
heroku logs --tail | grep ERROR

# 資料庫連線狀態
# 在 MongoDB Atlas 查看 Metrics
```

#### 3.3 用戶回饋
監控用戶回報的問題並快速回應。

---

## 🔄 回滾計畫

### 如果遷移失敗，執行以下步驟：

#### 方法 1: 從 MongoDB Atlas 快照還原
```bash
1. 登入 MongoDB Atlas
2. 進入 Clusters → Backups
3. 選擇遷移前的快照
4. 點擊 "Restore" 還原資料
5. 重新部署舊版程式碼（移除多用戶功能）
```

#### 方法 2: 使用本地備份還原
```bash
# 如果有使用 mongodump 備份
mongorestore --uri="<REMOTE_MONGO_URI>" ./backup_YYYYMMDD_HHMMSS/

# 重新部署舊版程式碼
git revert <commit-hash>
git push heroku main
```

#### 方法 3: 清理多用戶資料（快速回滾）
```bash
# 連線到 Heroku dyno
heroku run python scripts/clean_local_db.py

# 注意：這會刪除所有多用戶資料，但保留原始進度
```

**回滾時間**：< 5 分鐘

---

## 📊 遷移檢查清單

### 遷移前
- [ ] 程式碼已測試完成
- [ ] 本地遷移測試成功
- [ ] SECRET_KEY 已設定
- [ ] 資料庫備份已建立
- [ ] 用戶已收到通知
- [ ] 備援計畫已準備

### 遷移中
- [ ] 維護模式已啟動（可選）
- [ ] Dry-run 檢查通過
- [ ] 遷移腳本執行成功
- [ ] Admin 用戶已建立
- [ ] 資料檢查通過

### 遷移後
- [ ] 登入功能測試通過
- [ ] 資料隔離驗證通過
- [ ] 所有使用者已通知
- [ ] 監控已設置
- [ ] 維護模式已關閉

---

## 🐛 常見問題與解決方案

### Q1: 遷移腳本執行失敗
**原因**：資料庫連線問題或權限不足  
**解決**：
```bash
# 檢查 MongoDB URI 是否正確
heroku config:get REMOTE_MONGO_URI

# 確認資料庫使用者權限
# 需要 readWrite 權限
```

### Q2: 用戶登入後看不到資料
**原因**：資料未正確遷移到 user_id  
**解決**：
```bash
# 檢查 user_progress 是否有 user_id
# 在 MongoDB Atlas 執行查詢
db.user_progress.findOne()

# 如果缺少 user_id，重新執行遷移
python scripts/migrate_to_multiuser.py
```

### Q3: 多個用戶看到相同資料
**原因**：路由未加入 @login_required 或查詢未過濾 user_id  
**解決**：這是 Phase 10 後續任務，需要更新業務邏輯層

---

## 📝 遷移後任務

遷移完成後，還需要完成 Phase 10 的剩餘工作：

1. **更新路由加入驗證保護** (`routes/quiz.py`, `routes/laws.py`)
2. **修改服務層支援 user_id** (`services/inventory.py`, `services/grader.py`)
3. **前端整合** (`templates/base.html` 顯示用戶資訊)
4. **撰寫測試** (`test/test_multiuser_isolation.py`)
5. **更新文檔** (README.md)

詳見 [`docs/tasks.md`](tasks.md) 的 Phase 10 清單。

---

## 📞 聯絡資訊

如有問題，請聯繫：
- **技術負責人**：[姓名]
- **緊急聯絡**：[電話/Email]

---

## 📚 相關文件
- [多用戶實作報告](MULTIUSER_IMPLEMENTATION_REPORT.md)
- [設計文件](design.md)
- [任務清單](tasks.md)

---

**文件版本**：1.0  
**最後更新**：2026-05-07  
**審核者**：[待審核]
