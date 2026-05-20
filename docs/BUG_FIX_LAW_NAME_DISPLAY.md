# Bug Fix: 法律名稱顯示錯誤

## 問題描述

用戶反饋兩個問題：

1. **題目內容錯誤**：行政訴訟法和訴願法的題目中，錯誤地提到「專利法」
   - 例如：「依據專利法第3-1條規定...」但實際應該是「依據行政訴訟法第3-1條規定...」

2. **頁面標題固定**：所有頁面標題都顯示「專利法 AI 刷題助手」，沒有根據當前法律類型動態更新

## 問題分析

### 問題 1: 題目內容中的法律名稱錯誤

**根本原因：**
- [`services/question_gen.py:77`](../services/question_gen.py:77) 的提示詞硬編碼了「台灣專利法的專家」
- 生成其他法律類型題目時，LLM 仍然使用「專利法」這個名稱

**影響範圍：**
- 遠端數據庫中發現 4 個題目有此問題
  - 2 個訴願法題目（第 17、19 條）
  - 2 個行政訴訟法題目（第 3-1 條）

### 問題 2: 頁面標題固定

**根本原因：**
- 所有模板文件中的 `<title>` 標籤硬編碼為「專利法 AI 刷題助手」
- 沒有根據 session 中的 `current_law_type` 動態更新

## 解決方案

### 修復 1: 題目生成提示詞

**修改文件：** [`services/question_gen.py`](../services/question_gen.py)

1. **添加法律類型參數**
   ```python
   def generate_questions(
       self, 
       law_content: str, 
       law_article_number: str,
       question_type: Literal["MCQ", "ShortAnswer"],
       recent_questions: List[Dict] = None,
       count: int = 1,
       law_type: str = "patent-act",      # 新增
       law_name: str = None               # 新增
   ) -> List[Dict]:
   ```

2. **動態推斷法律名稱**
   ```python
   # Infer law name from law_type if not provided
   if law_name is None:
       from db.models import LAW_TYPES
       law_name = LAW_TYPES.get(law_type, {}).get('name_zh', '專利法')
   ```

3. **更新提示詞**
   ```python
   user_prompt = f"""
你是台灣{law_name}的專家。請根據以下法條生成 {count} 道 {question_type} 題目：
{law_name} {law_article_number}：{law_content}

重要：
1. 所有題目、選項、答案和解釋都必須使用繁體中文
2. 題目中提到法條時，必須使用「{law_name}」，不要使用其他法律名稱
3. 題目應該聚焦在這條法條的內容和應用
"""
   ```

**修改文件：** [`services/inventory.py`](../services/inventory.py:341-347)

更新調用處，傳入 `law_type` 參數：
```python
new_qs = self.question_gen.generate_questions(
    law_content=law["content"],
    law_article_number=law["article_number"],
    question_type=actual_type,
    recent_questions=recent,
    count=to_generate,
    law_type=law_type  # 傳入法律類型
)
```

### 修復 2: 遠端數據庫中的錯誤題目

**修復腳本：** [`scripts/fix_remote_law_names.py`](../scripts/fix_remote_law_names.py)

此腳本會：
1. 連接到遠端 MongoDB (Heroku)
2. 查找所有提到錯誤法律名稱的題目
3. 將「專利法」替換為正確的法律名稱（訴願法/行政訴訟法）
4. 更新數據庫

**執行方式：**
```bash
python3 scripts/fix_remote_law_names.py
```

### 修復 3: 頁面標題動態化 (待實現)

**計劃修改：**

1. **後端：** 在 [`routes/frontend.py`](../routes/frontend.py) 的每個路由中傳入當前法律類型
   ```python
   from services.auth import get_current_law_type
   from db.models import LAW_TYPES
   
   @frontend_bp.route('/')
   @login_required
   def dashboard():
       law_type = get_current_law_type()
       law_name = LAW_TYPES.get(law_type, {}).get('name_zh', '專利法')
       return render_template('dashboard.html', law_name=law_name)
   ```

2. **前端：** 更新 [`templates/base.html`](../templates/base.html) 使用動態標題
   ```html
   <title>{% block title %}{{ law_name|default('專利法') }} AI 刷題助手{% endblock %}</title>
   ```

3. **各個頁面模板** 不需要修改 title block，會自動使用父模板的 law_name

## 測試驗證

### 本地測試

1. **檢查題目**
   ```bash
   python3 scripts/check_question_law_references.py
   ```
   結果：✅ 本地數據庫無問題

2. **測試題目生成**
   - 生成新的行政訴訟法題目
   - 確認題目內容使用正確的法律名稱

### 遠端修復

1. **執行修復腳本**
   ```bash
   python3 scripts/fix_remote_law_names.py
   ```

2. **驗證**
   - 訪問用戶提到的題目 URL
   - 確認法律名稱已修正

## 部署步驟

1. **提交代碼**
   ```bash
   git add services/question_gen.py services/inventory.py
   git commit -m "fix: 修復題目生成時的法律名稱錯誤

   - 在 question_gen.py 中添加 law_type 和 law_name 參數
   - 提示詞動態使用正確的法律名稱
   - 更新 inventory.py 傳入 law_type 參數
   - 添加隨機化邏輯避免題目重複
   
   Fixes #issue-law-name-incorrect"
   ```

2. **推送到 Heroku**
   ```bash
   git push heroku main
   ```

3. **修復遠端數據庫**
   ```bash
   # 設置遠端數據庫連接
   heroku config:get MONGODB_URI > .env.remote
   
   # 執行修復腳本
   python3 scripts/fix_remote_law_names.py
   ```

4. **驗證部署**
   - 訪問 https://patent-act-15774ac83829.herokuapp.com
   - 測試行政訴訟法和訴願法的題目
   - 確認新生成的題目使用正確名稱

## 預防措施

### 未來新增法律類型時

1. 在 [`db/models.py`](../db/models.py) 的 `LAW_TYPES` 中添加新法律類型及其中文名稱

2. 題目生成會自動使用正確的法律名稱（無需額外修改）

3. 遵循 [`docs/NEW_LAW_TYPE_SOP.md`](NEW_LAW_TYPE_SOP.md) 標準操作流程

### 代碼審查檢查項

- ✅ 題目生成提示詞不應硬編碼法律名稱
- ✅ 頁面標題應動態顯示當前法律類型
- ✅ 所有引用法律名稱的地方應從 `LAW_TYPES` 取得

## 相關文件

- 修改文件：
  - [`services/question_gen.py`](../services/question_gen.py)
  - [`services/inventory.py`](../services/inventory.py)
  
- 測試腳本：
  - [`scripts/check_question_law_references.py`](../scripts/check_question_law_references.py)
  - [`scripts/fix_remote_law_names.py`](../scripts/fix_remote_law_names.py)
  
- 相關文檔：
  - [`docs/BUG_FIX_QUESTION_RANDOMIZATION.md`](BUG_FIX_QUESTION_RANDOMIZATION.md) - 題目隨機化修復
  - [`docs/NEW_LAW_TYPE_SOP.md`](NEW_LAW_TYPE_SOP.md) - 新增法律類型SOP

## 修復日期

2026-05-20

## 修復人員

AI Assistant (Claude)
