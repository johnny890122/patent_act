# 🚨 安全事件應對指南

## 概述

此文件詳細說明當 MongoDB 憑證意外暴露到 GitHub 時需要採取的緊急措施。

---

## ✅ 已完成的緊急修復

### 1. 移除硬編碼的憑證
已從以下檔案中移除硬編碼的 MongoDB URI：
- [`scripts/init_db.py`](scripts/init_db.py:46)
- [`scripts/init_truth_laws.py`](scripts/init_truth_laws.py:38)
- [`scripts/init_remote_laws.py`](scripts/init_remote_laws.py:32)

所有憑證現已改用環境變數：
```python
REMOTE_MONGO_URI = os.environ.get('REMOTE_MONGO_URI', '')
```

### 2. 更新環境變數範例
已更新 [`.env.example`](.env.example) 文件，加入正確的環境變數配置範例。

---

## 🔥 立即需要執行的關鍵步驟

### 步驟 1: 立即更改 MongoDB Atlas 密碼

**最高優先級！**

1. 登入 [MongoDB Atlas](https://cloud.mongodb.com/)
2. 進入您的專案
3. 點擊左側選單 **"Database Access"**
4. 找到使用者 `admin`
5. 點擊 **"Edit"** → **"Edit Password"**
6. 生成新的強密碼（建議使用密碼管理器）
7. 點擊 **"Update User"**

> ⚠️ **重要**: 更改密碼後，暴露的舊憑證將立即失效！

### 步驟 2: 檢查 MongoDB Atlas 存取日誌

1. 在 MongoDB Atlas 中，前往 **"Metrics"** 或 **"Real-time Performance Panel"**
2. 檢查是否有可疑的連線活動
3. 查看 **"Network Access"** 設定，確認 IP 白名單
4. 如果發現異常活動，考慮：
   - 備份數據
   - 檢查數據完整性
   - 聯繫 MongoDB 支援團隊

### 步驟 3: 更新本地環境變數

創建或更新您的本地 `.env` 文件：

```bash
# 複製範例文件
cp .env.example .env

# 編輯 .env 文件並填入新的憑證
nano .env
```

在 `.env` 中設定新的 MongoDB URI：
```ini
REMOTE_MONGO_URI=mongodb+srv://admin:<NEW_PASSWORD>@cluster0.lsu6m2w.mongodb.net/patent-act?retryWrites=true&w=majority
```

### 步驟 4: 更新生產環境配置

如果您使用 Heroku 或其他雲端平台：

**Heroku:**
```bash
heroku config:set REMOTE_MONGO_URI="mongodb+srv://admin:<NEW_PASSWORD>@cluster0.lsu6m2w.mongodb.net/patent-act?retryWrites=true&w=majority"
```

**其他平台:** 請參考該平台的環境變數設定文件。

---

## 🧹 清理 Git 歷史記錄

由於憑證已經被提交到 GitHub，您需要從 Git 歷史中完全移除這些敏感資訊。

### 選項 A: 使用 git-filter-repo (推薦)

1. **安裝 git-filter-repo:**
```bash
# macOS
brew install git-filter-repo

# 或使用 pip
pip3 install git-filter-repo
```

2. **備份您的倉庫:**
```bash
cd /Users/zhangxiangxian/patent_act
git clone --mirror . ../patent_act_backup
```

3. **創建包含敏感資訊的文本文件:**
```bash
cat > /tmp/passwords.txt << 'EOF'
03ra64XqDM8sOBdV
cluster0.lsu6m2w.mongodb.net
mongodb+srv://admin:03ra64XqDM8sOBdV
EOF
```

4. **執行過濾:**
```bash
git filter-repo --replace-text /tmp/passwords.txt
```

5. **強制推送到 GitHub:**
```bash
git remote add origin <YOUR_GITHUB_REPO_URL>
git push origin --force --all
git push origin --force --tags
```

### 選項 B: 使用 BFG Repo-Cleaner

1. **下載 BFG:**
```bash
brew install bfg
# 或從 https://rtyley.github.io/bfg-repo-cleaner/ 下載
```

2. **創建密碼文件:**
```bash
echo "03ra64XqDM8sOBdV" > /tmp/passwords.txt
```

3. **執行清理:**
```bash
cd /Users/zhangxiangxian/patent_act
git clone --mirror <YOUR_GITHUB_REPO_URL> patent_act-mirror.git
cd patent_act-mirror.git
bfg --replace-text /tmp/passwords.txt
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

4. **重新克隆乾淨的倉庫:**
```bash
cd ..
rm -rf patent_act
git clone <YOUR_GITHUB_REPO_URL> patent_act
```

### 警告事項

⚠️ **重要警告:**
- 重寫 Git 歷史會改變所有 commit SHA
- 所有協作者需要重新克隆倉庫
- Pull requests 和 forks 仍可能包含舊憑證
- 考慮將倉庫設為私有或創建新倉庫

---

## 🔒 MongoDB Atlas 安全最佳實踐

### 1. 網路存取限制

在 MongoDB Atlas 中設定 IP 白名單：

1. 進入 **"Network Access"**
2. 點擊 **"Add IP Address"**
3. **不要使用** `0.0.0.0/0`（允許所有 IP）
4. 只添加您需要的特定 IP：
   - 您的開發機器 IP
   - 生產伺服器 IP
   - CI/CD 服務 IP

### 2. 使用專用數據庫用戶

不要使用管理員帳號連接應用程式：

1. 在 **"Database Access"** 中創建新用戶
2. 使用 **"Built-in Role"** → **"Read and write to any database"**
3. 或自定義僅授予必要權限的角色

### 3. 啟用 MongoDB Atlas 審計日誌

1. 升級到 M10+ 叢集（如有需要）
2. 在專案設定中啟用 **"Database Auditing"**
3. 設定日誌轉發到您的監控系統

### 4. 定期輪換憑證

設定定期更換密碼的提醒：
- 建議每 90 天輪換一次
- 使用密碼管理器生成強密碼
- 記錄輪換日期

### 5. 啟用雙因素驗證 (2FA)

為您的 MongoDB Atlas 帳戶啟用 2FA：
1. 點擊右上角的頭像
2. 選擇 **"Account Settings"**
3. 在 **"Security"** 標籤下啟用 2FA

---

## 📋 安全檢查清單

在完成上述步驟後，確認以下項目：

- [ ] MongoDB Atlas 密碼已更改
- [ ] 檢查過 MongoDB Atlas 存取日誌，無異常活動
- [ ] 本地 `.env` 文件已更新為新密碼
- [ ] 生產環境環境變數已更新
- [ ] `.env` 已在 `.gitignore` 中（已確認存在）
- [ ] Git 歷史已清理完成
- [ ] 強制推送已完成
- [ ] MongoDB Atlas IP 白名單已設定
- [ ] 已創建專用數據庫用戶（如適用）
- [ ] 已啟用 2FA
- [ ] 已通知所有團隊成員重新克隆倉庫
- [ ] 已設定密碼輪換提醒

---

## 🔐 未來預防措施

### 1. 使用 Git Hooks

安裝 pre-commit hook 來防止提交敏感資訊：

```bash
# 安裝 pre-commit
pip3 install pre-commit

# 創建 .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: detect-private-key
      - id: check-added-large-files
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
EOF

# 安裝 hooks
pre-commit install
```

### 2. 使用 GitHub Secret Scanning

確保在 GitHub 倉庫設定中啟用：
- Settings → Security → Code security and analysis
- 啟用 "Secret scanning"

### 3. 團隊培訓

- 教育團隊成員關於敏感資訊的處理
- 定期審查代碼中的硬編碼憑證
- 建立清晰的環境變數管理流程

---

## 📞 需要協助？

如果發現數據洩露或未授權存取的跡象：

1. **立即聯繫 MongoDB 支援**: https://support.mongodb.com/
2. **檢查您的數據完整性**
3. **考慮諮詢安全專家**
4. **準備事件報告**

---

## 參考資源

- [MongoDB Atlas Security Checklist](https://www.mongodb.com/docs/atlas/security-checklist/)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning)
- [git-filter-repo Documentation](https://github.com/newren/git-filter-repo)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

**最後更新:** 2026-05-02
