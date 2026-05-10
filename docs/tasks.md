# Tasks: 多法律支持功能實作

## Overview
本任務清單實作多法律類型支持功能，使系統能夠處理專利法、商標法、著作權法等多種法律。所有現有專利法數據將遷移為 `type="patent-act"`，並確保系統邏輯正確過濾法律類型。

---

## Phase 1: 數據模型與遷移 (Data Model & Migration)

### Task 1.1: 更新數據模型定義
**File**: [`db/models.py`](../db/models.py)

- [ ] 在 `LawModel` 中添加 `type: str = "patent-act"` 欄位
- [ ] 在 `I18nMappingModel` 中添加 `type: str` 欄位
- [ ] 添加 `LAW_TYPES` 常量定義支持的法律類型
- [ ] 更新 `init_db()` 方法，添加新的索引：
  - [ ] `laws.create_index("type")`
  - [ ] `laws.create_index([("type", 1), ("lang", 1)])`
  - [ ] `laws.create_index([("type", 1), ("article_number_int", 1)])`
  - [ ] `i18n_mapping.create_index([("type", 1), ("article_number", 1)])`

**Validation**:
- 執行 `python -c "from db.models import LawModel; import dataclasses; print(dataclasses.fields(LawModel))"` 確認新欄位存在
- 確認 `type` 欄位有預設值 `"patent-act"`

---

### Task 1.2: 建立數據遷移腳本
**File**: `scripts/migrate_add_law_type.py` (新建)

- [ ] 建立遷移腳本檔案
- [ ] 實作 `migrate_laws_add_type()` 函數：
  - [ ] 查找所有沒有 `type` 欄位的 law 文檔
  - [ ] 批量更新為 `type="patent-act"`
  - [ ] 記錄更新數量並輸出
- [ ] 實作 `migrate_i18n_mapping_add_type()` 函數：
  - [ ] 查找所有沒有 `type` 欄位的 i18n_mapping 文檔
  - [ ] 批量更新為 `type="patent-act"`
  - [ ] 記錄更新數量並輸出
- [ ] 實作 `create_new_indexes()` 函數：
  - [ ] 建立上述所有新索引
  - [ ] 處理索引已存在的情況
- [ ] 實作 `validate_migration()` 函數：
  - [ ] 驗證所有 laws 都有 `type` 欄位
  - [ ] 驗證所有 i18n_mappings 都有 `type` 欄位
  - [ ] 統計各 type 的文檔數量
- [ ] 實作 `rollback_migration()` 函數（備用）：
  - [ ] 移除所有 `type` 欄位
  - [ ] 清除相關索引
- [ ] 添加主函數和 CLI 參數處理
- [ ] 添加詳細的日誌輸出

**Validation**:
- 在本地測試數據庫執行遷移
- 驗證遷移是冪等的（可以多次執行）
- 確認 rollback 功能正常運作
- 執行後確認 `db.laws.find({"type": {"$exists": false}}).count() == 0`

---

### Task 1.3: 執行數據遷移
**執行步驟**:

- [ ] 在本地環境先測試遷移：
  ```bash
  python scripts/migrate_add_law_type.py --dry-run
  ```
- [ ] 確認 dry-run 結果正確後執行實際遷移：
  ```bash
  python scripts/migrate_add_law_type.py --execute
  ```
- [ ] 驗證遷移結果：
  ```bash
  python scripts/migrate_add_law_type.py --validate
  ```
- [ ] 記錄遷移結果（更新的文檔數量）
- [ ] 備份當前數據庫狀態（在生產環境執行前）

**Production Migration**:
- [ ] 在 staging 環境測試完整流程
- [ ] 建立生產數據庫備份
- [ ] 在維護時段執行生產遷移
- [ ] 驗證生產環境遷移結果
- [ ] 監控遷移後系統運行狀態

---

## Phase 2: 核心服務層更新 (Core Services)

### Task 2.1: 更新認證服務添加法律類型管理
**File**: [`services/auth.py`](../services/auth.py)

- [ ] 添加 `LAW_TYPES` 常量導入
- [ ] 實作 `get_current_law_type() -> str` 函數：
  - [ ] 從 Flask session 獲取 `current_law_type`
  - [ ] 如果不存在，返回預設值 `"patent-act"`
- [ ] 實作 `set_current_law_type(law_type: str) -> bool` 函數：
  - [ ] 驗證 law_type 在 LAW_TYPES 中
  - [ ] 如果有效，儲存到 session
  - [ ] 返回操作結果
- [ ] 實作 `get_available_law_types() -> List[Dict]` 函數：
  - [ ] 查詢每個法律類型的法條數量
  - [ ] 返回格式：`[{type, name_zh, name_en, count_zh_tw, count_en}]`
- [ ] 添加單元測試

**Validation**:
- 測試 session 中有/無 law_type 的情況
- 測試無效 law_type 的處理
- 驗證預設值返回正確

---

### Task 2.2: 更新題目庫存服務
**File**: [`services/inventory.py`](../services/inventory.py)

- [ ] 在 `count_available_questions()` 方法添加 `law_type` 參數：
  - [ ] 參數預設值為 `None`（從 session 獲取）
  - [ ] 如果為 `None`，調用 `get_current_law_type()`
- [ ] 更新查詢邏輯，添加法律類型過濾：
  - [ ] 在獲取 laws 時添加 `{"type": law_type}` 過濾
  - [ ] 確保只計算該法律類型的題目
- [ ] 在 `get_questions_for_session()` 方法添加相同的過濾邏輯
- [ ] 在 `trigger_generation()` 方法中傳遞 law_type 到題目生成器
- [ ] 更新所有相關的輔助方法

**Validation**:
- 測試只返回指定 law_type 的題目
- 測試不同 law_type 之間的題目完全隔離
- 驗證題目計數正確

---

### Task 2.3: 更新題目生成服務
**File**: [`services/question_gen.py`](../services/question_gen.py)

- [ ] 在生成題目前驗證 law_id 的法律類型：
  - [ ] 查詢 law 文檔
  - [ ] 確認其 `type` 欄位與當前 law_type 匹配
  - [ ] 如果不匹配，拋出 `ValueError`
- [ ] 在獲取最近題目時添加 law_type 過濾（通過 law_id 關聯）
- [ ] 確保生成的題目只參考同一法律類型的法條

**Validation**:
- 測試不能為錯誤的 law_type 生成題目
- 驗證題目去重邏輯在法律類型內正常運作

---

## Phase 3: API 路由更新 (API Routes)

### Task 3.1: 添加法律類型管理 API
**File**: `routes/law_types.py` (新建)

- [ ] 建立新的 Blueprint: `law_types_bp`
- [ ] 實作 `GET /api/law-types` 端點：
  - [ ] 調用 `get_available_law_types()`
  - [ ] 返回所有可用的法律類型及統計
  - [ ] 需要登入驗證 `@login_required`
- [ ] 實作 `GET /api/law-types/current` 端點：
  - [ ] 返回當前 session 中的 law_type
  - [ ] 返回格式：`{type, name_zh, name_en}`
- [ ] 實作 `POST /api/law-types/select` 端點：
  - [ ] 接收 `law_type` 參數
  - [ ] 調用 `set_current_law_type(law_type)`
  - [ ] 返回操作結果和新的 law_type
- [ ] 添加錯誤處理和輸入驗證
- [ ] 在 [`app.py`](../app.py) 中註冊新的 Blueprint

**Validation**:
- 測試獲取法律類型列表
- 測試切換法律類型
- 測試無效法律類型的錯誤處理
- 驗證需要登入才能訪問

---

### Task 3.2: 更新法條 API 路由
**File**: [`routes/laws.py`](../routes/laws.py)

- [ ] 在 `get_laws()` 函數開頭添加：
  ```python
  law_type = request.args.get('law_type') or get_current_law_type()
  query_filter['type'] = law_type
  ```
- [ ] 在 `get_law_detail()` 函數中驗證法條類型：
  - [ ] 獲取 law 文檔
  - [ ] 檢查其 `type` 是否與當前 law_type 匹配
  - [ ] 如果不匹配，返回 403 錯誤
- [ ] 在 `toggle_law_star()` 函數中添加類型驗證
- [ ] 在 `get_law_chapters()` 函數中添加 law_type 過濾
- [ ] 在 `get_law_questions()` 函數中：
  - [ ] 驗證 law 的類型
  - [ ] 確保只返回該法律類型的題目
- [ ] 更新所有相關統計查詢，添加 law_type 過濾

**Validation**:
- 測試法條列表只顯示指定類型
- 測試訪問錯誤類型的法條返回 403
- 測試統計數據按法律類型正確隔離

---

### Task 3.3: 更新測驗 API 路由
**File**: [`routes/quiz.py`](../routes/quiz.py)

- [ ] 在 `check_available_questions()` 端點添加：
  - [ ] 從參數或 session 獲取 `law_type`
  - [ ] 傳遞給 `count_available_questions()`
- [ ] 在 `create_quiz_session()` 端點添加：
  - [ ] 從參數或 session 獲取 `law_type`
  - [ ] 傳遞給 `get_questions_for_session()`
  - [ ] 在 session 記錄中儲存 `law_type`
- [ ] 在題目生成觸發邏輯中傳遞 `law_type`
- [ ] 確保所有題目查詢都經過 law 的類型過濾

**Validation**:
- 測試測驗只包含指定法律類型的題目
- 測試背景生成只為當前法律類型生成題目
- 驗證不同法律類型的進度完全獨立

---

### Task 3.4: 更新前端路由
**File**: [`routes/frontend.py`](../routes/frontend.py)

- [ ] 在 `dashboard()` 函數中：
  - [ ] 獲取當前 law_type
  - [ ] 篩選該類型的法條 IDs
  - [ ] 統計數據只計算該法律類型
  - [ ] 傳遞 law_type 到模板
- [ ] 在 `laws_page()` 函數中傳遞當前 law_type
- [ ] 在 `law_detail_page()` 函數中驗證法條類型

**Validation**:
- 測試儀表板統計按法律類型正確顯示
- 測試切換法律類型後數據更新

---

## Phase 4: 前端界面更新 (Frontend UI)

### Task 4.1: 添加法律類型選擇器組件
**Files**: 
- [`templates/base.html`](../templates/base.html)
- [`static/js/main.js`](../static/js/main.js)

- [ ] 在導航欄添加法律類型下拉選單：
  - [ ] 顯示當前選中的法律類型
  - [ ] 列出所有可用的法律類型
  - [ ] 每個選項顯示中文名稱和法條數量
- [ ] 實作 JavaScript 切換邏輯：
  - [ ] 調用 `POST /api/law-types/select`
  - [ ] 成功後重新加載頁面或更新數據
  - [ ] 顯示切換成功的提示訊息
- [ ] 添加 CSS 樣式使其美觀並響應式

**Validation**:
- 測試在各個頁面都能看到選擇器
- 測試選擇器切換後頁面數據更新
- 測試移動端顯示正常

---

### Task 4.2: 更新法條瀏覽頁面
**File**: [`templates/laws.html`](../templates/laws.html)

- [ ] 顯示當前選中的法律類型名稱
- [ ] 添加法律類型篩選提示文字
- [ ] 確保搜尋功能在當前法律類型內進行
- [ ] 更新空狀態提示（如果該法律類型沒有法條）

**Validation**:
- 測試只顯示當前法律類型的法條
- 測試搜尋在正確的範圍內

---

### Task 4.3: 更新儀表板頁面
**File**: [`templates/dashboard.html`](../templates/dashboard.html)

- [ ] 顯示當前學習的法律類型
- [ ] 添加明顯的法律類型標識
- [ ] 統計數據標註為當前法律類型的進度
- [ ] 提示用戶可以在導航欄切換法律類型

**Validation**:
- 測試儀表板顯示正確的法律類型
- 測試統計數據正確

---

### Task 4.4: 更新測驗配置頁面
**File**: [`templates/quiz_config.html`](../templates/quiz_config.html)

- [ ] 顯示將為哪個法律類型生成題目
- [ ] 添加法律類型標籤或提示
- [ ] 確保可用題目數量查詢包含 law_type

**Validation**:
- 測試配置頁面顯示正確的法律類型
- 測試可用題目數量計算正確

---

### Task 4.5: 更新樣式設計
**File**: [`static/css/style.css`](../static/css/style.css)

- [ ] 添加法律類型選擇器的樣式
- [ ] 為不同法律類型設計不同的主題色（可選）
- [ ] 添加法律類型標籤 badge 樣式
- [ ] 確保所有新組件響應式設計

**Validation**:
- 測試在不同螢幕尺寸下顯示正常
- 測試深色/淺色模式兼容（如果有）

---

## Phase 5: 初始化與管理腳本 (Initialization Scripts)

### Task 5.1: 更新現有初始化腳本
**Files**: 
- [`scripts/init_db.py`](../scripts/init_db.py)
- [`scripts/init_remote_laws.py`](../scripts/init_remote_laws.py)

- [ ] 確保插入法條時包含 `type="patent-act"`
- [ ] 更新 i18n mapping 插入邏輯包含 `type`
- [ ] 驗證腳本執行後數據格式正確

**Validation**:
- 在乾淨的數據庫執行初始化
- 確認所有法條都有 type 欄位

---

### Task 5.2: 建立新法律類型初始化範本
**File**: `scripts/init_new_law_type_template.py` (新建)

- [ ] 建立範本腳本，包含：
  - [ ] 法律類型參數配置
  - [ ] 中英文法條解析與插入
  - [ ] i18n mapping 建立
  - [ ] 索引驗證
  - [ ] 數據驗證
- [ ] 添加詳細的使用說明註解
- [ ] 建立對應的 README 文檔

**Validation**:
- 使用範本建立測試法律類型
- 驗證所有數據結構正確

---

## Phase 6: 測試覆蓋 (Testing Coverage)

### Task 6.1: 單元測試
**File**: `test/test_multi_law_support.py` (新建)

- [ ] 測試數據模型：
  - [ ] LawModel 預設 type 值
  - [ ] I18nMappingModel type 欄位
- [ ] 測試 auth service：
  - [ ] `get_current_law_type()` 各種情況
  - [ ] `set_current_law_type()` 驗證邏輯
  - [ ] `get_available_law_types()` 返回格式
- [ ] 測試 inventory service：
  - [ ] 法律類型過濾邏輯
  - [ ] 題目計數按類型隔離
- [ ] 執行測試：`pytest test/test_multi_law_support.py -v`

---

### Task 6.2: 整合測試
**File**: `test/test_multi_law_integration.py` (新建)

- [ ] 測試完整流程：
  - [ ] 初始化兩種法律類型
  - [ ] 切換法律類型
  - [ ] 驗證法條列表過濾
  - [ ] 驗證題目生成隔離
  - [ ] 驗證統計數據隔離
- [ ] 測試 API 端點：
  - [ ] 法律類型管理 API
  - [ ] 法條 API 過濾
  - [ ] 測驗 API 過濾
- [ ] 執行測試：`pytest test/test_multi_law_integration.py -v`

---

### Task 6.3: 遷移測試
**File**: `test/test_migration_law_type.py` (新建)

- [ ] 測試遷移腳本：
  - [ ] 在測試數據庫執行遷移
  - [ ] 驗證所有文檔更新
  - [ ] 測試冪等性（多次執行）
  - [ ] 測試 rollback 功能
- [ ] 測試數據完整性：
  - [ ] 驗證沒有孤兒題目
  - [ ] 驗證 i18n mapping 完整
- [ ] 執行測試：`pytest test/test_migration_law_type.py -v`

---

### Task 6.4: E2E 測試
**File**: [`test/test_integration_e2e.py`](../test/test_integration_e2e.py) (更新)

- [ ] 添加多法律支持的 E2E 測試場景：
  - [ ] 用戶登入後選擇法律類型
  - [ ] 瀏覽該法律類型的法條
  - [ ] 開始該法律類型的測驗
  - [ ] 切換到另一個法律類型
  - [ ] 驗證數據完全隔離
- [ ] 執行測試：`pytest test/test_integration_e2e.py -v`

---

## Phase 7: 文檔與部署 (Documentation & Deployment)

### Task 7.1: 更新技術文檔
**Files**:
- [`README.md`](../README.md)
- `docs/MULTI_LAW_GUIDE.md` (新建)

- [ ] 更新 README：
  - [ ] 添加多法律支持說明
  - [ ] 更新功能列表
  - [ ] 更新架構圖
- [ ] 建立多法律支持指南：
  - [ ] 架構說明
  - [ ] 數據遷移步驟
  - [ ] 如何添加新法律類型
  - [ ] 故障排除指南

---

### Task 7.2: 建立遷移執行計劃
**File**: `docs/MIGRATION_PLAN_LAW_TYPE.md` (新建)

- [ ] 撰寫遷移計劃：
  - [ ] Pre-flight 檢查清單
  - [ ] 備份策略
  - [ ] 執行步驟
  - [ ] 驗證檢查點
  - [ ] Rollback 程序
  - [ ] 監控指標
- [ ] 建立遷移時間表
- [ ] 準備回報模板

---

### Task 7.3: 準備部署
**Checklist**:

- [ ] 在 staging 環境完整測試
- [ ] 驗證所有測試通過
- [ ] 準備數據庫備份腳本
- [ ] 準備監控告警
- [ ] 通知團隊成員遷移計劃
- [ ] 準備緊急回滾計劃

---

### Task 7.4: 執行生產部署
**Steps**:

- [ ] 建立生產數據庫完整備份
- [ ] 在維護時段執行遷移：
  1. [ ] 停止影響數據的服務（可選）
  2. [ ] 執行 `migrate_add_law_type.py --execute`
  3. [ ] 驗證遷移結果
  4. [ ] 部署新版本程式碼
  5. [ ] 驗證系統功能正常
  6. [ ] 監控錯誤日誌
- [ ] 執行煙霧測試（smoke test）
- [ ] 記錄部署結果

---

### Task 7.5: 監控與驗證
**Post-deployment**:

- [ ] 監控系統 24-48 小時
- [ ] 檢查錯誤日誌無異常
- [ ] 驗證用戶回饋
- [ ] 性能指標對比
- [ ] 記錄遇到的問題與解決方案

---

## Phase 8: 未來增強 (Future Enhancements)

### Task 8.1: 權限控制（可選）
- [ ] 設計用戶法律類型權限系統
- [ ] 實作權限檢查中間件
- [ ] 添加管理界面分配權限

### Task 8.2: 批量操作工具
- [ ] 建立法律類型批量管理工具
- [ ] 實作法律類型匯出/匯入功能
- [ ] 建立數據驗證工具

### Task 8.3: 性能優化
- [ ] 實作法律類型元數據緩存
- [ ] 優化跨法律類型的查詢
- [ ] 添加查詢性能監控

---

## 完成檢查清單 (Completion Checklist)

### 代碼質量
- [ ] 所有代碼通過 lint 檢查
- [ ] 所有測試通過（單元、整合、E2E）
- [ ] 代碼覆蓋率 > 80%
- [ ] 無重大技術債務

### 功能完整性
- [ ] 所有現有功能正常運作
- [ ] 法律類型切換功能完整
- [ ] 數據完全隔離無洩漏
- [ ] 用戶體驗流暢

### 數據完整性
- [ ] 所有現有數據遷移成功
- [ ] 無數據丟失
- [ ] 無孤兒記錄
- [ ] i18n mapping 完整

### 文檔完整性
- [ ] 技術文檔完整
- [ ] API 文檔更新
- [ ] 遷移文檔完整
- [ ] 故障排除指南完整

### 部署準備
- [ ] Staging 環境驗證通過
- [ ] 備份策略已測試
- [ ] Rollback 程序已驗證
- [ ] 監控告警已設置

---

## 風險與緩解策略

### 風險 1: 數據遷移失敗
**緩解**:
- 在測試環境多次演練
- 準備詳細的 rollback 腳本
- 遷移前完整備份

### 風險 2: 性能下降
**緩解**:
- 建立適當的索引
- 性能測試與基準對比
- 監控查詢執行時間

### 風險 3: 現有功能破壞
**緩解**:
- 完整的回歸測試
- 漸進式部署
- 特性開關控制

### 風險 4: 用戶體驗混亂
**緩解**:
- 清晰的 UI 指示
- 預設為專利法（現有用戶無感知）
- 提供使用指南

---

## 預估時間

- **Phase 1**: 數據模型與遷移 - 2-3 天
- **Phase 2**: 核心服務層更新 - 2-3 天
- **Phase 3**: API 路由更新 - 3-4 天
- **Phase 4**: 前端界面更新 - 2-3 天
- **Phase 5**: 初始化與管理腳本 - 1-2 天
- **Phase 6**: 測試覆蓋 - 3-4 天
- **Phase 7**: 文檔與部署 - 2-3 天
- **Phase 8**: 未來增強 - 依需求

**總計**: 約 15-22 個工作天

---

## 注意事項

1. **向後兼容**: 所有變更必須確保現有專利法功能完全正常
2. **數據安全**: 任何數據庫操作前必須備份
3. **測試優先**: 先寫測試再實作功能
4. **漸進部署**: 可以先部署後端，再部署前端
5. **監控重點**: 重點監控查詢性能和錯誤率
6. **用戶溝通**: 重大更新前通知用戶

---

## 參考資料

- [`requirements.md`](requirements.md) - 功能需求文檔
- [`design.md`](design.md) - 系統設計文檔
- [`db/models.py`](../db/models.py) - 數據模型定義
- [`services/auth.py`](../services/auth.py) - 認證服務
- [`routes/laws.py`](../routes/laws.py) - 法條路由
