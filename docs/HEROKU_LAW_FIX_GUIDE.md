# Heroku 法條顯示問題修復指南

## 🔍 問題診斷

### 問題描述
插入新的訴願法和行政訴訟法後，Heroku 上的法條無法正確顯示。

### 根本原因
**環境變數配置混淆 - 兩個資料庫不同步**

系統中存在兩個不同的 MongoDB 環境變數：

1. **`MONGO_URI`** - Heroku/本地應用程式實際使用的資料庫（完整資料）
2. **`REMOTE_MONGO_URI`** - 開發時用於測試的遠端資料庫（資料不完整）

**實際狀況：**
- **MONGO_URI (localdb)**: 包含完整資料（專利法、審查基準、訴願法、行政訴訟法）
- **REMOTE_MONGO_URI (patent-act)**: 僅有部分資料（只有行政訴訟法）

**問題發生原因：**
- 使用 `init_administrative_appeal.py --target remote` 時，資料被插入到 `REMOTE_MONGO_URI` 指向的資料庫
- 但如果 Heroku 指向的是不同的資料庫，或者您需要兩個資料庫保持同步，就需要手動同步資料

### 系統架構說明

```
本地開發環境
├── MONGO_URI: mongodb://localhost:27017/patent_act (本地資料庫)
└── REMOTE_MONGO_URI: mongodb+srv://...@cluster.mongodb.net/... (測試用遠端)

Heroku 生產環境
└── MONGO_URI: mongodb+srv://...@heroku-cluster.mongodb.net/... (生產資料庫)
```

## 🩺 診斷步驟

### 步驟 1: 執行診斷工具

```bash
# 設定環境變數 (從 .env 或 Heroku)
export MONGO_URI="你的Heroku MongoDB URI"
export REMOTE_MONGO_URI="你的開發用遠端 MongoDB URI"

# 執行診斷
python scripts/diagnose_heroku_laws.py
```

診斷工具會檢查：
- ✅ 兩個資料庫的連接狀態
- ✅ 各法律類型的條文數量
- ✅ 資料庫索引狀態
- ✅ 範例資料
- ✅ 兩個 URI 是否指向同一資料庫

### 步驟 2: 從 Heroku 取得正確的資料庫 URI

```bash
# 取得 Heroku 實際使用的 MONGO_URI
heroku config:get MONGO_URI -a your-app-name

# 或查看所有配置
heroku config -a your-app-name
```

## 🔧 修復方案

### 方案 A: 同步資料到 Heroku 生產資料庫（推薦）

這是最直接的解決方案，將新法條直接同步到 Heroku 使用的資料庫。

#### 步驟 1: 設定 Heroku 資料庫 URI

```bash
# 方法 1: 從 Heroku 取得並設定為環境變數
export HEROKU_MONGO_URI=$(heroku config:get MONGO_URI -a your-app-name)

# 方法 2: 直接設定 (從 Heroku dashboard 複製)
export HEROKU_MONGO_URI="mongodb+srv://user:pass@cluster.mongodb.net/dbname"
```

#### 步驟 2: 執行同步腳本

```bash
# 同步訴願法
python scripts/sync_to_heroku.py --law-type administrative-appeal

# 同步行政訴訟法
python scripts/sync_to_heroku.py --law-type administrative-litigation

# 或一次同步所有
python scripts/sync_to_heroku.py --law-type all

# 顯示詳細日誌
python scripts/sync_to_heroku.py --law-type all --verbose
```

#### 步驟 3: 驗證結果

```bash
# 重新執行診斷
python scripts/diagnose_heroku_laws.py

# 或使用驗證腳本
python scripts/verify_administrative_appeal.py --target remote
python scripts/verify_administrative_litigation.py --target remote
```

#### 步驟 4: 重啟 Heroku 應用

```bash
heroku restart -a your-app-name
```

### 方案 B: 統一環境變數配置

如果您希望開發環境和生產環境使用相同的資料庫。

#### 在 Heroku 設定 REMOTE_MONGO_URI

```bash
# 設定 Heroku 的 REMOTE_MONGO_URI 為相同的值
heroku config:set REMOTE_MONGO_URI=$(heroku config:get MONGO_URI) -a your-app-name
```

#### 或在本地 .env 統一設定

```env
# .env
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
REMOTE_MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/dbname
```

### 方案 C: 同步資料庫資料（資料庫間同步）

如果您需要將完整資料從一個資料庫同步到另一個資料庫。

#### 使用同步工具

```bash
# 預覽同步計劃（不實際執行）
python scripts/sync_local_to_remote.py --dry-run

# 同步所有法律類型
python scripts/sync_local_to_remote.py --law-type all

# 同步特定法律類型
python scripts/sync_local_to_remote.py --law-type administrative-appeal
python scripts/sync_local_to_remote.py --law-type patent-act

# 顯示詳細日誌
python scripts/sync_local_to_remote.py --law-type all --verbose
```

這個工具會：
1. 從 `MONGO_URI` 讀取完整資料
2. 同步到 `REMOTE_MONGO_URI`
3. 自動建立必要索引
4. 驗證同步結果

### 方案 D: 修改初始化腳本使用 MONGO_URI

修改 `init_administrative_appeal.py` 和 `init_administrative_litigation.py` 的 `--target remote` 參數，使其直接使用 `MONGO_URI` 而非 `REMOTE_MONGO_URI`。

## 📋 快速修復清單

如果您遇到法條顯示問題，請按照以下步驟操作：

- [ ] **步驟 1**: 取得 Heroku 的 MONGO_URI
  ```bash
  heroku config:get MONGO_URI -a your-app-name
  ```

- [ ] **步驟 2**: 設定環境變數
  ```bash
  export HEROKU_MONGO_URI="從步驟1取得的URI"
  ```

- [ ] **步驟 3**: 執行診斷
  ```bash
  python scripts/diagnose_heroku_laws.py
  ```

- [ ] **步驟 4**: 同步法條資料
  ```bash
  python scripts/sync_to_heroku.py --law-type all
  ```

- [ ] **步驟 5**: 驗證資料
  ```bash
  python scripts/diagnose_heroku_laws.py
  ```

- [ ] **步驟 6**: 重啟 Heroku
  ```bash
  heroku restart -a your-app-name
  ```

- [ ] **步驟 7**: 在瀏覽器測試
  - 開啟 Heroku 應用
  - 登入帳號
  - 切換法律類型為「訴願法」或「行政訴訟法」
  - 確認法條正確顯示

## 🚨 常見錯誤

### 錯誤 1: 連接超時
```
ServerSelectionTimeoutError: ...
```

**解決方案：**
- 檢查網路連接
- 確認 MongoDB URI 是否正確
- 確認 IP 白名單設定（MongoDB Atlas）

### 錯誤 2: 認證失敗
```
Authentication failed
```

**解決方案：**
- 檢查使用者名稱和密碼
- 檢查資料庫使用者權限
- 確認 URI 格式正確（特殊字元需要 URL 編碼）

### 錯誤 3: 找不到環境變數
```
HEROKU_MONGO_URI not configured
```

**解決方案：**
```bash
export HEROKU_MONGO_URI="你的MongoDB URI"
```

## 📚 相關腳本說明

### 診斷工具
- **[`scripts/diagnose_heroku_laws.py`](../scripts/diagnose_heroku_laws.py)** - 診斷兩個資料庫狀態和法條數量
- **[`scripts/verify_administrative_appeal.py`](../scripts/verify_administrative_appeal.py)** - 驗證訴願法資料完整性
- **[`scripts/verify_administrative_litigation.py`](../scripts/verify_administrative_litigation.py)** - 驗證行政訴訟法資料完整性

### 同步工具
- **[`scripts/sync_local_to_remote.py`](../scripts/sync_local_to_remote.py)** - 從 MONGO_URI 同步到 REMOTE_MONGO_URI（✨ 新增）
- **[`scripts/sync_to_heroku.py`](../scripts/sync_to_heroku.py)** - 同步法條到 Heroku 生產資料庫
- **[`scripts/init_administrative_appeal.py`](../scripts/init_administrative_appeal.py)** - 初始化訴願法（支援 local/remote）
- **[`scripts/init_administrative_litigation.py`](../scripts/init_administrative_litigation.py)** - 初始化行政訴訟法（支援 local/remote）

### 資料庫管理
- **[`scripts/copy_remote_to_local.py`](../scripts/copy_remote_to_local.py)** - 複製遠端資料到本地
- **[`scripts/fix_laws_index.py`](../scripts/fix_laws_index.py)** - 修復法條索引

## 🔐 安全注意事項

1. **不要在程式碼中硬編碼資料庫憑證**
2. **使用環境變數管理敏感資訊**
3. **不要將 .env 檔案提交到 Git**
4. **定期更換資料庫密碼**
5. **限制 MongoDB Atlas IP 白名單**

## 📞 需要協助？

如果問題仍未解決，請提供以下資訊：

1. 診斷工具的完整輸出
2. Heroku 日誌: `heroku logs --tail -a your-app-name`
3. 瀏覽器 Console 錯誤訊息
4. 使用的法律類型和搜尋條件

## 🎯 預防措施

為了避免將來再次發生此問題：

### 1. 明確標示環境變數用途

在 `.env.example` 中添加清楚的說明：

```env
# Heroku 生產環境資料庫 (應用程式實際使用)
MONGO_URI=mongodb+srv://...

# 開發用遠端測試資料庫 (僅供開發測試)
REMOTE_MONGO_URI=mongodb+srv://...
```

### 2. 統一初始化腳本參數

建議使用以下命名：
- `--target local` → 本地開發資料庫
- `--target production` → Heroku 生產資料庫（使用 MONGO_URI）
- `--target staging` → 測試環境資料庫（使用 REMOTE_MONGO_URI）

### 3. 建立部署檢查清單

每次新增法律類型後，執行：
```bash
# 1. 本地測試
python scripts/init_xxx.py --target local

# 2. 本地驗證
python scripts/verify_xxx.py --target local

# 3. 同步到生產環境
python scripts/sync_to_heroku.py --law-type xxx

# 4. 生產環境驗證
python scripts/diagnose_heroku_laws.py

# 5. 重啟應用
heroku restart -a your-app-name
```

## 📈 監控建議

設定定期監控腳本，檢查資料庫狀態：

```bash
# 每日檢查腳本
#!/bin/bash
export HEROKU_MONGO_URI=$(heroku config:get MONGO_URI -a your-app-name)
python scripts/diagnose_heroku_laws.py > daily_check.log 2>&1
```

---

**最後更新**: 2026-05-12
**相關文件**: 
- [`docs/NEW_LAW_TYPE_SOP.md`](NEW_LAW_TYPE_SOP.md) - 新增法律類型標準流程
- [`scripts/README.md`](../scripts/README.md) - 腳本使用說明
