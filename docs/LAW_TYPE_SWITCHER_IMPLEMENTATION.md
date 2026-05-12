# 法律類型切換器實作說明

## 概述

已成功實作前端法律類型切換器，允許用戶在專利法和審查基準之間切換。

## 實作內容

### 1. 前端 UI 組件

#### [`templates/base.html`](../templates/base.html)
在導航欄添加法律類型下拉選擇器：

```html
<div class="law-type-selector">
    <select id="law-type-select" class="law-type-select" title="選擇法律類型">
        <option value="patent-act">專利法</option>
        <option value="patent-examination">審查基準</option>
    </select>
</div>
```

**位置**: 放置在語言切換按鈕和用戶菜單之間

### 2. JavaScript 邏輯

#### [`static/js/main.js`](../static/js/main.js)
添加法律類型管理功能：

**新增函數**:
- `getCurrentLawType()`: 從 API 獲取當前法律類型
- `setLawType(lawType)`: 設定新的法律類型並重新載入頁面
- `updateLawTypeSelector(currentLawType)`: 更新 UI 選擇器狀態

**初始化邏輯**:
```javascript
document.addEventListener('DOMContentLoaded', async function() {
    // 獲取並顯示當前法律類型
    const currentLawType = await getCurrentLawType();
    updateLawTypeSelector(currentLawType);
    
    // 監聽選擇器變更事件
    const lawTypeSelect = document.getElementById('law-type-select');
    if (lawTypeSelect) {
        lawTypeSelect.addEventListener('change', function() {
            const newLawType = this.value;
            if (newLawType !== currentLawType) {
                setLawType(newLawType);
            }
        });
    }
});
```

### 3. CSS 樣式

#### [`static/css/style.css`](../static/css/style.css)
添加法律類型選擇器樣式：

```css
/* Law Type Selector */
.law-type-selector {
  display: flex;
  align-items: center;
}

.law-type-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  background-color: var(--card-bg);
  color: var(--text-primary);
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;
  min-width: 120px;
}

.law-type-select:hover {
  border-color: var(--primary-color);
  background-color: var(--bg-color);
}

.law-type-select:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}
```

**設計特點**:
- 與現有設計系統一致
- 支援 hover 和 focus 狀態
- 響應式設計
- 使用設計 token 變數

### 4. API 端點

#### [`routes/law_types.py`](../routes/law_types.py)
已存在完整的 API 端點：

- `GET /api/law-types`: 獲取所有可用法律類型
- `GET /api/law-types/current`: 獲取當前選中的法律類型
- `POST /api/law-types/select`: 設定新的法律類型
- `GET /api/law-types/info/<law_type>`: 獲取特定法律類型詳情

### 5. 後端服務層

#### [`services/auth.py`](../services/auth.py)
已實作法律類型管理函數：

- `get_current_law_type()`: 從 session 獲取當前法律類型
- `set_current_law_type(law_type)`: 設定法律類型到 session
- `get_available_law_types()`: 獲取所有可用法律類型及統計

## 使用流程

### 1. 頁面載入
```
User → 頁面載入 → JavaScript 初始化
          ↓
    getCurrentLawType() API 調用
          ↓
    GET /api/law-types/current
          ↓
    更新 UI 選擇器狀態
```

### 2. 切換法律類型
```
User 選擇新類型 → change 事件觸發
          ↓
    setLawType(lawType) 調用
          ↓
    POST /api/law-types/select
          ↓
    Session 更新
          ↓
    顯示成功提示
          ↓
    頁面重新載入 (500ms 延遲)
```

### 3. 資料隔離
```
頁面重新載入後
    ↓
所有 API 請求使用 get_current_law_type()
    ↓
查詢自動過濾: {type: "patent-act"} 或 {type: "patent-examination"}
    ↓
用戶只看到所選法律類型的內容
```

## 測試驗證

### 手動測試步驟

1. **啟動應用**:
   ```bash
   python app.py
   ```

2. **登入系統**:
   - 訪問 `http://127.0.0.1:5001/`
   - 使用有效用戶名登入

3. **測試切換器**:
   - 觀察導航欄的法律類型選擇器
   - 當前應顯示「專利法」（預設）
   - 切換到「審查基準」
   - 確認頁面重新載入
   - 確認顯示的法條內容改變

4. **測試持久性**:
   - 切換到「審查基準」
   - 導航到不同頁面（如法條瀏覽）
   - 確認選擇器仍顯示「審查基準」
   - 確認顯示的內容仍為審查基準

5. **測試隔離性**:
   - 在「專利法」模式下瀏覽法條
   - 切換到「審查基準」
   - 確認法條列表完全不同
   - 確認題目和進度也分別追蹤

### API 測試

可使用 curl 或 Postman 測試：

```bash
# 獲取當前法律類型
curl http://127.0.0.1:5001/api/law-types/current \
  -H "Cookie: session=YOUR_SESSION"

# 切換到審查基準
curl -X POST http://127.0.0.1:5001/api/law-types/select \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION" \
  -d '{"law_type": "patent-examination"}'

# 獲取所有法律類型
curl http://127.0.0.1:5001/api/law-types \
  -H "Cookie: session=YOUR_SESSION"
```

## 功能特性

### ✅ 已實作
- [x] 導航欄中的下拉選擇器
- [x] 即時切換法律類型
- [x] Session 持久化選擇
- [x] 頁面重新載入以更新內容
- [x] 成功/錯誤提示訊息
- [x] 與現有設計系統整合
- [x] 響應式設計
- [x] API 端點完整實作
- [x] 後端服務層支援
- [x] 資料完全隔離

### 📋 支援的法律類型
1. **專利法** (`patent-act`)
   - 中文: 168 條
   - 英文: 168 條

2. **審查基準** (`patent-examination`)
   - 中文: 1,073 條
   - 英文: 0 條（未來可擴展）

## UI 位置

```
導航欄結構:
[Logo] [首頁] [法條瀏覽] ... [法律類型▼] [中|EN] [用戶名 🚪]
                                  ↑
                          新增的選擇器
```

## 技術細節

### Session 管理
- 法律類型儲存在 Flask session 中
- Key: `current_law_type`
- 預設值: `"patent-act"`
- 跨頁面持久化

### 資料過濾
所有資料查詢自動加上法律類型過濾：

```python
# 在 services/inventory.py, routes/laws.py 等處
law_type = get_current_law_type()
query_filter = {'type': law_type}
laws = laws_collection.find(query_filter)
```

### 錯誤處理
- 無效法律類型 → 自動回退到 `patent-act`
- API 錯誤 → 顯示錯誤訊息給用戶
- 網路錯誤 → Console 日誌記錄

## 未來擴展

### 可能的改進
1. **動態載入**: 無需重新載入整個頁面
2. **歷史記錄**: 記錄用戶最近使用的法律類型
3. **快捷鍵**: 支援鍵盤快捷鍵切換
4. **統計資訊**: 在選擇器中顯示條文數量
5. **搜尋整合**: 跨法律類型搜尋功能
6. **書籤**: 支援收藏不同法律類型的法條

### 新增法律類型
要添加新的法律類型：

1. 更新 [`db/models.py`](../db/models.py) 中的 `LAW_TYPES`
2. 準備該法律類型的資料（JSON 或 Markdown）
3. 建立對應的初始化腳本
4. 執行資料導入
5. 在 [`templates/base.html`](../templates/base.html) 選擇器中添加選項

## 相關文檔

- [需求文檔 §9.7](requirements.md#97-law-type-filtering-in-ui)
- [設計文檔 §9.6](design.md#96-uiux-changes)
- [任務清單 Phase 4](tasks.md#phase-4-前端界面更新-frontend-ui)
- [審查基準設定指南](EXAMINATION_GUIDELINES_SETUP.md)

---

**實作完成日期**: 2026-05-11  
**狀態**: ✅ 完成並可用
