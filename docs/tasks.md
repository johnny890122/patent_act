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
    - [x] 加入顯示「收藏題目」功能

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

## Phase 9: Internationalization (i18n) - Content & Questions

### 9.1 Database Schema Updates
- [ ] TASK-9.1.1: Update `LawModel` in [`db/models.py`](../db/models.py) to add `lang: str = "zh-TW"` field [REQ-7]
- [ ] TASK-9.1.2: Update `QuestionModel` in [`db/models.py`](../db/models.py) to add `lang` and `base_question_id` fields [REQ-7]
- [ ] TASK-9.1.3: Create `I18nMappingModel` in [`db/models.py`](../db/models.py) for bidirectional law article linking [REQ-7]
- [ ] TASK-9.1.4: Create MongoDB index on `(law_id, lang)` and `(base_question_id, lang)` for efficient i18n queries

### 9.2 Law Article i18n Initialization
- [ ] TASK-9.2.1: Parse [`knowledge/patent_law_en.md`](../knowledge/patent_law_en.md) and generate [`knowledge/truth_law_en.json`](../knowledge/truth_law_en.json) using [`scripts/parse_patent_law_en.py`](../scripts/parse_patent_law_en.py) [REQ-7]
- [ ] TASK-9.2.2: Modify [`scripts/init_truth_laws.py`](../scripts/init_truth_laws.py) to add `lang` field to zh-TW laws during insertion (backfill existing data) [REQ-7]
- [ ] TASK-9.2.3: Create new script [`scripts/init_truth_laws_en.py`](../scripts/init_truth_laws_en.py) to insert English laws with `lang: en` [REQ-7]
- [ ] TASK-9.2.4: Create [`scripts/create_i18n_mapping.py`](../scripts/create_i18n_mapping.py) to populate `i18n_mapping` collection for zh-TW ↔ en law pairs [REQ-7]
- [ ] TASK-9.2.5: Execute backfill + insertion scripts for both local and remote databases [REQ-7]

### 9.3 Translation Service & Question Generation
- [ ] TASK-9.3.1: Create [`services/translator.py`](../services/translator.py) with methods:
  - `translate_question_to_en(question_dict) → dict` — translates a single zh-TW question to EN
  - `generate_bilingual_question(law_content, question_type) → tuple[dict, dict]` — generates both zh-TW and EN versions simultaneously [REQ-7.1]
- [ ] TASK-9.3.2: Update [`services/question_gen.py`](../services/question_gen.py) to use translator for bilingual generation [REQ-7.1]
  - Modify prompt to request both zh-TW and EN in a single LLM call
  - Ensure semantic consistency between languages
  - Link both versions via shared `base_question_id`
- [ ] TASK-9.3.3: Test bilingual question generation end-to-end with sample law articles [REQ-7.1]

### 9.4 Data Migration: Translate Existing Questions
- [ ] TASK-9.4.1: Create [`scripts/migrate_questions_to_en.py`](../scripts/migrate_questions_to_en.py) script to:
  - Iterate over all zh-TW questions in `questions` collection
  - Call `translator.translate_question_to_en()` for each
  - Insert EN version with shared `base_question_id`
  - Log translation results and any failures [REQ-7.1]
- [ ] TASK-9.4.2: Test migration on local database with 10% of questions (dry-run with logging)
- [ ] TASK-9.4.3: Execute migration on local database and verify question counts [REQ-7.1]
- [ ] TASK-9.4.4: Execute migration on remote (production) database [REQ-7.1]

### 9.5 Frontend: Display Bilingual Question Content
- [ ] TASK-9.5.1: Modify [`routes/quiz.py`](../routes/quiz.py) `POST /quiz/session` to accept optional `lang` parameter (default: zh-TW)
- [ ] TASK-9.5.2: Update [`routes/laws.py`](../routes/laws.py) `GET /laws` endpoint to support language filtering (`?lang=zh-TW` or `?lang=en`)
- [ ] TASK-9.5.3: Modify law article detail template to display law content in the selected language
- [ ] TASK-9.5.4: Update quiz session template to show question content in selected language

### 9.6 Testing & Validation
- [ ] TASK-9.6.1: Create [`test/test_i18n_migration.py`](../test/test_i18n_migration.py) — test question translation and data migration logic
- [ ] TASK-9.6.2: Create [`test/test_i18n_schema.py`](../test/test_i18n_schema.py) — verify database schema changes and indexes
- [ ] TASK-9.6.3: Create [`test/test_bilingual_questions.py`](../test/test_bilingual_questions.py) — end-to-end test for generating bilingual questions
- [ ] TASK-9.6.4: Run all tests and ensure no regression in existing functionality

## Phase 10: Multi-User Support (NEW)

### 10.1 Database Schema Updates
- [ ] TASK-10.1.1: Create `UserModel` in [`db/models.py`](../db/models.py) with fields: `username`, `display_name`, `created_at`, `last_login` [REQ-8]
- [ ] TASK-10.1.2: Create `UserLawStarModel` in [`db/models.py`](../db/models.py) for per-user law stars [REQ-8.2]
- [ ] TASK-10.1.3: Create `UserLawStatsModel` in [`db/models.py`](../db/models.py) for per-user law statistics [REQ-8.2]
- [ ] TASK-10.1.4: Create `UserQuestionStarModel` in [`db/models.py`](../db/models.py) for per-user question stars [REQ-8.2]
- [ ] TASK-10.1.5: Update `UserProgressModel` to add `user_id` field [REQ-8.2]
- [ ] TASK-10.1.6: Remove `is_starred`, `total_score`, `attempt_count`, `avg_score` from `LawModel` (移至 per-user collections) [REQ-8.2]
- [ ] TASK-10.1.7: Remove `is_starred` from `QuestionModel` (移至 per-user collections) [REQ-8.2]
- [ ] TASK-10.1.8: Update MongoDB indexes in [`db/models.py`](../db/models.py):
  - Add `username` unique index on `users` collection
  - Add composite index `(user_id, question_id)` on `user_progress`
  - Add composite index `(user_id, law_id)` on `user_law_stars` and `user_law_stats`
  - Add composite index `(user_id, question_id)` on `user_question_stars`

### 10.2 Authentication Service & Routes
- [ ] TASK-10.2.1: Create [`services/auth.py`](../services/auth.py) with helper functions:
  - `get_current_user() → Optional[str]` — Get user_id from session
  - `get_current_user_info() → Optional[dict]` — Get full user info from session
  - `login_required` decorator — Redirect to login if not authenticated [REQ-8.1]
- [ ] TASK-10.2.2: Create [`routes/auth.py`](../routes/auth.py) with endpoints:
  - `GET /auth/login` — Show login page
  - `POST /auth/login` — Validate username and create session [REQ-8.1]
  - `POST /auth/logout` — Clear session and redirect to login
  - `GET /auth/current` — Return current user info (for frontend)
- [ ] TASK-10.2.3: Register auth blueprint in [`app.py`](../app.py)
- [ ] TASK-10.2.4: Configure `SECRET_KEY` in Flask app for session signing

### 10.3 Frontend: Login Page
- [ ] TASK-10.3.1: Create [`templates/login.html`](../templates/login.html) with username input form [REQ-8.1]
- [ ] TASK-10.3.2: Add login form styles to [`static/css/style.css`](../static/css/style.css)
- [ ] TASK-10.3.3: Add client-side validation for username field

### 10.4 Update Existing Routes for Multi-User
- [ ] TASK-10.4.1: Update [`routes/quiz.py`](../routes/quiz.py) — Add `@login_required` decorator and filter by `user_id`:
  - `GET /api/quiz/available` — Filter by current user's progress
  - `POST /quiz/session` — Create session for current user
  - `POST /quiz/session/:id/answer` — Update current user's progress
  - `POST /quiz/session/:id/answer/:aid/appeal` — Appeal for current user [REQ-8.2]
- [ ] TASK-10.4.2: Update [`routes/laws.py`](../routes/laws.py) — Add `@login_required` and user filtering:
  - `GET /laws` — Show laws with current user's star status
  - `PUT /laws/:id/star` — Toggle star for current user only
  - `GET /laws/:id` — Show law detail with current user's stats
  - `GET /api/laws/:id/questions` — Show questions with current user's progress [REQ-8.2]
- [ ] TASK-10.4.3: Update [`routes/frontend.py`](../routes/frontend.py) — Add `@login_required` to dashboard and other pages [REQ-8.2]

### 10.5 Update Services for Multi-User
- [ ] TASK-10.5.1: Update [`services/inventory.py`](../services/inventory.py):
  - Modify `count_available_questions()` to accept and filter by `user_id`
  - Modify `get_session_questions()` to filter by `user_id` [REQ-8.3]
- [ ] TASK-10.5.2: Update [`services/grader.py`](../services/grader.py):
  - Ensure grading saves to correct user's progress record

### 10.6 Data Migration: Single-User to Multi-User
- [ ] TASK-10.6.1: Create [`scripts/migrate_to_multiuser.py`](../scripts/migrate_to_multiuser.py) to:
  - Create a default admin user (e.g., username: "admin", display_name: "Administrator")
  - Migrate existing `user_progress` records to include default user's `user_id`
  - Migrate law stars from `laws.is_starred` to `user_law_stars` collection for default user
  - Migrate law stats from `laws` to `user_law_stats` collection for default user
  - Migrate question stars from `questions.is_starred` to `user_question_stars` for default user [REQ-8.2]
- [ ] TASK-10.6.2: Test migration script on local database
- [ ] TASK-10.6.3: Create backup of production database
- [ ] TASK-10.6.4: Execute migration on production database

### 10.7 Admin Tools: User Management
- [ ] TASK-10.7.1: Create [`scripts/add_user.py`](../scripts/add_user.py) CLI tool to add new users:
  - Accept `username` and `display_name` as arguments
  - Validate username uniqueness
  - Insert into `users` collection [REQ-8.4]
- [ ] TASK-10.7.2: Document user management process in [`README.md`](../README.md)

### 10.8 Frontend: Session & User Context
- [ ] TASK-10.8.1: Update [`templates/base.html`](../templates/base.html) to:
  - Show current user's display name in header
  - Add logout button
  - Check authentication status on page load
- [ ] TASK-10.8.2: Update [`static/js/main.js`](../static/js/main.js):
  - Add function to check current user (`GET /auth/current`)
  - Redirect to login if not authenticated on protected pages

### 10.9 Testing: Multi-User Functionality
- [ ] TASK-10.9.1: Create [`test/test_auth.py`](../test/test_auth.py) — Test login, logout, session management
- [ ] TASK-10.9.2: Create [`test/test_multiuser_isolation.py`](../test/test_multiuser_isolation.py) — Verify data isolation between users:
  - User A's stars don't appear for User B
  - User A's progress doesn't affect User B's progress
  - Quiz sessions are correctly filtered by user [REQ-8.2]
- [ ] TASK-10.9.3: Update existing tests to include authentication context
- [ ] TASK-10.9.4: Test edge cases:
  - Multiple users answering same question simultaneously
  - User logout and re-login preserves data
  - Invalid username login attempt

### 10.10 Documentation & Deployment
- [ ] TASK-10.10.1: Update [`README.md`](../README.md) with multi-user setup instructions
- [ ] TASK-10.10.2: Document how to add new users via MongoDB or script
- [ ] TASK-10.10.3: Update environment variables documentation (add `SECRET_KEY` requirement)
- [ ] TASK-10.10.4: Test complete user flow end-to-end:
  - Admin adds new user
  - New user logs in
  - New user completes quiz session
  - Verify data isolation