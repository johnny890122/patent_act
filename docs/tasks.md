# Tasks Document: 專利法 AI 刷題助手

## Phase 1: Setup & Initialization
- [x] 1.1 Project scaffolding (Create directories: `routes/`, `services/`, `db/`).
- [x] 1.2 Initialize Flask app setup in `app.py`.
- [x] 1.3 Setup MongoDB connection logic in `db/models.py`.
- [x] 1.4 Write admin script/endpoint (`routes/admin.py`) to parse `knowledge/ch1.md` and seed `laws` collection. (Using mock up for now)

## Phase 2: Services Implementation (LLM & Business Logic)
- [x] 2.1 Implement `services/question_gen.py` to talk to OpenRouter and parse JSON for MCQ and Short Answer. (Enhanced with Pydantic validation)
- [x] 2.2 Implement `services/grader.py` to evaluate short answers returning 0, 0.5, or 1. (Implemented with Pydantic validation and comprehensive tests)
- [x] 2.3 Implement `services/inventory.py` to handle the `n`, `4n` inventory logic and async generation trigger. (Implemented with comprehensive tests)

## Phase 3: Core API Endpoints
- [x] 3.1 Implement `POST /quiz/session` in `routes/quiz.py` (handles new, review, mixed modes).
- [x] 3.2 Implement `POST /quiz/session/:id/answer` for MCQ and Short Answer submissions and score updating.
- [x] 3.3 Implement `POST /quiz/session/:id/answer/:aid/appeal` for reversing scores logic.
- [x] 3.4 Implement `DELETE /questions/:qid` for soft deleting questions.
- [x] 3.5 Implement `GET` routes and `PUT /laws/:id/star` in `routes/laws.py` for laws browser.

## Phase 4: Frontend & Integration (Mobile Web)
- [x] 4.1 Build basic HTML/CSS/JS templates for Dashboard (S-01) and Law Article Browser (S-07).
- [x] 4.2 Build Quiz Config (S-02) UI and wire to `POST /quiz/session`.
- [x] 4.3 Build Quiz Loop UI (S-04, S-05) handling both MCQ and Short Answer inputs.
- [x] 4.4 Build Session Summary (S-06) and bind appeal/delete interactions.
- [x] 4.5 Test end-to-end question generation, answering, and grading loop.
- [x] 4.6 Build Law Article Detail (S-08) with pagination and sorting (latest first).
- [ ] 4.6 http://127.0.0.1:5001/laws/69f4e2eb9e35bb6f6b0bad67, 法條詳情頁面開發中

## Phase 5: Design System ✅
- [x] Import the https://www.muicss.com/ into this app
- [x] Integrate knowledge/react-design-system-primitives.json and knowledge/react-design-system-tokens.json design system to the repo, unify the styling and layout

## Phase 5: UI refinement ✅
- [x] homepage (route: http://127.0.0.1:5001)
    - [x] Remove '🔥 連續答對天數' and '⭐ 收藏的法條' cards

- [x] http://127.0.0.1:5001/laws
    - [x] 請考慮在手機版面的顯示畫面，讓法條內容可以完整顯示
    - [x] 重新設計佈局：條號和星號在上方，條文佔據完整寬度
    - [x] 優化統計資訊間距，減少 margin
    - [x] 法條應該要按照條目照順序顯示，目前 1 > 10 > 101，且所屬章節也不對
- [x] http://127.0.0.1:5001/laws

    - [x] 添加依照章節的索引，例如 menu 或其他方式，可以快速定位
        - [x] 添加左側章節索引側邊欄
        - [x] 實現章節過濾功能
        - [x] 添加側邊欄收合功能
        - [x] 響應式設計（手機版自動調整）

- [x] templates/law_detail.html
    - [x] 移除 <div class="summary-stat">
                    <div class="stat-value" id="question-count">0</div>
                    <div class="stat-label">相關題目</div>
                </div>
    - [x] 下方題目只顯示已作答過的題目（修改 API 和前端邏輯）
        - [x] 修改 [`routes/laws.py`](../routes/laws.py) 的 `get_law_questions` 函數，僅回傳有 user_progress 記錄的題目
        - [x] 移除 JavaScript 中對已刪除元素的引用
    
    - [x] http://127.0.0.1:5001/laws/69f594e89e35bb6f6b0c6c5c
        - [x] 相關題目的選項放成同一行（已改為垂直排列，每個選項獨立一行）
        - [x] 加入答錯、收藏題目的選項
            - [x] 在 [`routes/laws.py`](../routes/laws.py:318) 添加 questions_bp blueprint
            - [x] 實作 `/api/questions/<id>/star` API 端點切換題目收藏狀態
            - [x] 更新 [`app.py`](../app.py:6) 註冊 questions_bp
            - [x] 在 [`templates/law_detail.html`](../templates/law_detail.html:68) 添加「已收藏」和「答錯題」篩選標籤
            - [x] 在 [`static/css/style.css`](../static/css/style.css:1748) 添加 .btn-icon-small 按鈕樣式
            - [x] **答錯標記改為自動判斷** (方案 B)：
                - [x] 移除 `is_marked_wrong` 欄位（不再存儲在 questions collection）
                - [x] 修改 [`routes/laws.py`](../routes/laws.py:263) 的 `get_law_questions` API，根據 `user_progress.last_score < 0.7` 自動判斷答錯狀態
                - [x] 移除手動標記 API (`/api/questions/<id>/mark-wrong`)
                - [x] 更新前端顯示：自動顯示答錯標記和分數，無需手動按鈕
                - [x] 題目卡片顯示最後答題分數和答錯/答對狀態

## Phase 6: Law Insertion ✅
 - [x] use the law in knowledge/patent_law.md, generate a truth_law.json, and insert to the local db and remote db
   - [x] 創建 [`scripts/parse_patent_law.py`](../scripts/parse_patent_law.py) 解析 [`knowledge/patent_law.md`](../knowledge/patent_law.md)
   - [x] 生成 [`knowledge/truth_law.json`](../knowledge/truth_law.json) (共 168 條法條)
   - [x] 創建 [`scripts/init_truth_laws.py`](../scripts/init_truth_laws.py) 插入資料庫
   - [x] 成功插入 168 條法條到本地資料庫 (mongodb://localhost:27017/patent-act)
   - [x] 成功插入 168 條法條到遠端資料庫 (MongoDB Atlas)
   - [v] 1 本法主管機關為經濟部。 2 專利業務，由經濟部指定專責機關辦理。

        在 http://127.0.0.1:5001/laws/69f594e89e35bb6f6b0c6c60  和 http://127.0.0.1:5001/laws/

        有些條文會有細項，我希望用分行符號顯示

        在 init 時就要插入

## Phase 7: Config:
    - [x] http://127.0.0.1:5001/quiz/config
        - [x] 請 參考 law 的頁面，讓這裡變得更加緊湊，在手機上好閱讀

## Phase 8: quiz
    - [x] http://127.0.0.1:5001/quiz/session/69f59e8864ece7c6eb17c931
        - [x] 在看答案時，刷新會回到題目（已修復：使用 localStorage 保存答案狀態）
        - [x] 讓答案正確、您的答案、正確答案的顯示更緊湊
            - [x] 答錯時，解析是重點（已實現：答對時緊湊顯示單行，答錯時突出顯示 AI 解析）
        - [x] 選擇題評分錯誤：前端送完整選項，後端只儲存字母（已修復：提取選項字母進行比對）
        - [x] 正確答案只顯示字母 "B"，應該顯示完整選項（已修復：從 options 找到完整選項文字）
        - [x] 答錯時顯示題目和所有選項，並標注正確答案和用戶選擇（已實現：新增選項審閱顯示）
        - [x] 在完全正確的頁面下，加入題目跟選項，但預設收合（已實現：新增可收合區塊，點擊展開/收合）

## Phase 9: Insufficient Questions Warning ⏳
    - [ ] 9.1 Backend: 實作 `GET /api/quiz/available` API 端點
        - [ ] 在 [`routes/quiz.py`](../routes/quiz.py) 添加新端點
        - [ ] 接受 `type` 和 `mode` 參數
        - [ ] 呼叫 [`services/inventory.py`](../services/inventory.py) 的 `count_available_questions()`
        - [ ] 返回 JSON: `{ "available": int }`
    
    - [ ] 9.2 Frontend: 在配置頁面添加即時檢查
        - [ ] 修改 [`templates/quiz_config.html`](../templates/quiz_config.html)
        - [ ] 當用戶更改 type/mode/count 時，即時呼叫 `/api/quiz/available`
        - [ ] 顯示可用題數提示 (例如: "可用題數: 2 題")
        - [ ] 若 `count > available`，顯示警告標記
    
    - [ ] 9.3 Frontend: 實作題目不足警告彈窗
        - [ ] 在提交前檢查 `count > available`
        - [ ] 顯示模態對話框: "目前只有 X 題需要複習，是否要調整題數或改為混合模式？"
        - [ ] 提供三個選項按鈕:
            - [ ] "使用現有的 X 題" (自動調整 count)
            - [ ] "改為混合模式" (切換 mode 為 mixed)
            - [ ] "取消" (關閉對話框)
    
    - [ ] 9.4 Backend: 修改 inventory 邏輯（可選）
        - [ ] 考慮在 [`services/inventory.py`](../services/inventory.py) 的 `get_session_questions()` 中
        - [ ] 當 `available < count` 時返回錯誤而非自動生成
        - [ ] 或保持現有邏輯作為後備方案
    
    - [ ] 9.5 Testing: 測試題目不足情境
        - [ ] 測試只有 2 題複習題，請求 10 題的情況
        - [ ] 驗證警告彈窗正確顯示
        - [ ] 測試三個選項的功能
        - [ ] 確保調整後能正常開始測驗
