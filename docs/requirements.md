# Requirements: 法律 AI 刷題助手

## Project Overview
**法律 AI 刷題助手** — A multi-user mobile-first web app for Taiwan legal exam preparation, supporting multiple law types.
Core loop: AI dynamically generates exam questions bound to specific law articles, grades short-answer responses, and tracks mastery per article for each user. The system now supports multiple law types (e.g., Patent Law, Trademark Law, Copyright Law) with complete data isolation.

## User Persona
- Multiple users preparing for the Taiwan Patent Law exam within a small team or organization
- Each user needs independent progress tracking and personalized study experience
- Users are pre-configured by administrators (no self-registration)

## User Stories & Scenarios

### 1. Dashboard & Navigation
- **Story:** As a user, I want to see my overall progress from the homepage so I know how I'm doing.
- **Scenario:** Viewing the home dashboard shows current streak, count of starred law articles, and buttons to start a quiz or browse laws.

### 2. Quiz Configuration
- **Story:** As a user, I want to configure my practice session so I can focus on new or reviewed questions.
- **Scenario:** Opening quiz config allows selecting question type (MCQ, Short Answer, Mixed), session mode (New, Review, Mixed), and question count (1-50).

### 2.1 Quiz Configuration - Insufficient Questions Warning
- **Story:** As a user, I want to be notified when there are not enough questions available for my selected configuration, so I can adjust my settings accordingly.
- **Scenario:**
  - User selects "複習" mode and requests 10 questions, but only 2 review questions are available.
  - System shows a warning dialog: "目前只有 2 題需要複習，是否要調整題數或改為混合模式？"
  - User can choose: (1) Adjust question count to 2, (2) Switch to "混合" mode, or (3) Cancel and reconfigure.
  - The warning prevents generating irrelevant questions that don't match the user's learning intent.

### 3. Quiz Session & Async Generation
- **Story:** As a user, I want to always have questions available, even if AI takes time to generate them.
- **Scenario:** If there are enough questions in the DB, the quiz starts immediately. If not, the UI shows a loading state ("AI 正在為您量身打造題目...") while generating.

### 4. Answering & Immediate Feedback
- **Story:** As a user, I want to answer a question and get immediate grading and feedback.
- **Scenario:** 
  - MCQ: User taps an option, gets instantly told if correct. 
  - Short Answer: User submits a text response, UI shows a loader, then LLM returns a score (0, 0.5, 1) and explanation.

### 5. Scoring & Mastery Tracking
- **Story:** As a user, I want the system to track my mastery per question.
- **Scenario:** 
  - Getting a score of 1 increments the correct streak (3 streaks = mastered). 
  - Getting < 1 resets the streak and marks the question for review.
  - User can appeal a score to undo the penalty, or permanently delete a bad question.

### 6. Law Article Reference
- **Story:** As a user, I want to browse law articles directly when needed.
- **Scenario:** User can browse a paginated list of all Patent Law articles, view single article details, view history of questions on that article, and star (★) the article for reference.

### 6.1 Law Article Search
- **Story:** As a user, I want to search for law articles by content or article number, so I can quickly find relevant legal provisions.
- **Scenario:**
  - User enters search term in the search bar on laws page
  - System searches by article_number (exact/partial match) or content (text contains)
  - Results are displayed in real-time with pagination maintained
  - Search works across current language (zh-TW or EN)
  - Search can be combined with chapter filter
  - Clear button allows user to reset search and return to full list
  - Empty state is shown when no results are found with helpful message

### 7. Multilingual Support (i18n)
- **Story:** As a user, I want to view patent law articles and practice questions in both Traditional Chinese (zh-TW) and English, so I can prepare for the exam in both languages.
- **Scenario:**
  - Law articles are available in both zh-TW and EN (same article_number, different lang field)
  - When viewing a law article detail, both language versions are available
  - Questions can be generated/viewed in both zh-TW and EN
  - UI language remains in Traditional Chinese (buttons, labels, navigation)
  - Content-only i18n: Only laws and question content are multilingual; UI stays in Chinese

### 7.1 Question Translation & Consistency
- **Story:** As a user, I want translated questions to be accurate and consistent between languages.
- **Scenario:**
  - For existing questions (data migration): Questions are translated into EN using an LLM agent (one-time)
  - For new questions: Questions are generated in both zh-TW and EN simultaneously with identical meaning
  - Both language versions of a question share the same `question_id`, tracked via `lang` field
  - Grading is language-agnostic: scoring a zh-TW question also updates user_progress for both language versions

### 8. Multi-User Support (NEW)
- **Story:** As a team member, I want to have my own independent account so my progress is separate from other users.
- **Scenario:**
 - Each user has a unique `username` and `display_name`
 - Users are pre-created by administrators directly in the database
 - No self-registration UI is needed
 
### 8.1 User Login
- **Story:** As a user, I want to log in with just my username so I can access my personal study data.
- **Scenario:**
 - User visits the app and sees a login page
 - User enters their `username` (e.g., "alice" or "bob")
 - System validates the username exists in the database
 - If valid, user is logged in and redirected to their dashboard
 - If invalid, system shows error: "用戶名稱不存在"
 - Session is maintained in Flask session for subsequent requests

### 8.2 Personal Progress Isolation
- **Story:** As a user, I want my progress data to be completely separate from other users.
- **Scenario:**
 - User A's starred laws are independent from User B's starred laws
 - User A's question progress (correct_streak, needs_review) is separate from User B's
 - User A's quiz sessions and scores don't affect User B's statistics
 - Each user sees only their own data on the dashboard

### 8.3 Shared Question Pool
- **Story:** As a user, I want to benefit from questions generated by the system for all users.
- **Scenario:**
 - Questions are shared across all users (not user-specific)
 - When any user completes a quiz, questions are available for all users
 - This reduces duplicate AI generation and improves system efficiency
 - However, each user's progress on each question is tracked independently

### 8.4 User Management (Admin)
- **Story:** As an administrator, I want to manage users directly in the database.
- **Scenario:**
 - Admin uses MongoDB client or script to add new users
 - Required fields: `username` (unique), `display_name`
 - Optional fields: `created_at`, `last_login`
 - Example: `db.users.insertOne({username: "alice", display_name: "Alice Chen"})`

## 9. Multi-Law Support (NEW)

### 9.1 Law Type System
- **Story:** As a user, I want to study different types of laws (Patent Law, Trademark Law, etc.) within the same system.
- **Scenario:**
  - System supports multiple law types identified by `type` field (e.g., "patent-act", "trademark-act", "copyright-act")
  - All law articles, questions, and user progress are tagged with their law type
  - Users can switch between different law types seamlessly
  - Each law type maintains independent content, questions, and statistics

### 9.2 Law Type Selection
- **Story:** As a user, I want to select which law I'm studying so I can focus on relevant content.
- **Scenario:**
  - User can see a list of available law types on the dashboard or navigation menu
  - When selecting a law type, the system filters all content (laws, questions, statistics) by that type
  - User's current law selection is saved in session for convenience
  - Dashboard shows progress statistics specific to the selected law type

### 9.3 Law Type Isolation
- **Story:** As a user, I want my study data for different laws to be completely separated.
- **Scenario:**
  - Questions generated for Patent Law don't appear when studying Trademark Law
  - User's mastery progress in Patent Law is independent from Trademark Law
  - Statistics (total score, attempt count) are calculated separately per law type
  - Starred articles are filtered by law type

### 9.4 Default Law Type (Patent Law)
- **Story:** As an existing user, I want the system to continue working with Patent Law by default after the migration.
- **Scenario:**
  - All existing law articles are migrated with `type = "patent-act"`
  - All existing questions are linked to Patent Law articles
  - New law types can be added without affecting existing data
  - System defaults to Patent Law if no law type is explicitly selected

### 9.5 Data Migration Requirements
- **Story:** As a system administrator, I want to safely migrate existing data to support multiple law types.
- **Scenario:**
  - Migration script adds `type = "patent-act"` to all existing law articles
  - All existing questions remain linked to their Patent Law articles via `law_id`
  - User progress records are automatically associated with Patent Law through question relationships
  - Migration is idempotent (can be run multiple times safely)
  - Rollback procedure is documented in case of issues

### 9.6 Adding New Law Types
- **Story:** As an administrator, I want to add new law types to expand the system's coverage.
- **Scenario:**
  - Admin can run initialization scripts to add new law types (e.g., Trademark Law)
  - Each new law type requires:
    - Law articles with `type` field set (e.g., "trademark-act")
    - Properly formatted law content (markdown or JSON)
    - Language support (zh-TW and EN versions)
  - System automatically creates necessary indexes for new law types
  - Questions can be generated for new law types using the same AI pipeline

### 9.7 Law Type Filtering in UI
- **Story:** As a user, I want to see only content relevant to my selected law type.
- **Scenario:**
  - Law browser page shows only articles from the selected law type
  - Quiz configuration automatically filters questions by law type
  - Search functionality respects law type filter
  - Law detail page shows related questions from the same law type only
  - Dashboard statistics aggregate data for the selected law type

### 9.8 Patent Examination Guidelines Support (NEW)
- **Story:** As a user preparing for patent examiner certification, I want to study Patent Examination Guidelines alongside Patent Law.
- **Scenario:**
  - System supports Patent Examination Guidelines as a separate law type: `"patent-examination"`
  - Examination guidelines are structured similarly to patent law articles with chapter hierarchy
  - Users can switch between Patent Law and Examination Guidelines
  - Each guideline article can have associated practice questions
  - Progress tracking is independent between Patent Law and Examination Guidelines
  - Search and filtering work across examination guidelines content

### 9.9 Examination Guidelines Data Structure
- **Story:** As an administrator, I want examination guidelines data to be properly structured for easy management.
- **Scenario:**
  - Examination guideline articles stored in `knowledge/examination/` directory
  - Organized by chapters (01-06) in JSON format
  - Each article contains:
    - `article_number`: Section identifier (e.g., "1.1 文件")
    - `article_number_int`: Integer for sorting (e.g., 1102)
    - `chapter`: Full chapter hierarchy (e.g., "第一篇程序審查及專利權管理 第一章...")
    - `content`: Full text content
    - `lang`: Language tag (zh-TW)
    - `type`: Set to "patent-examination"
  - Initialization script imports all examination guideline articles into database
  - Same database schema as patent law articles (uses `LawModel`)

## 10. Mobile Header Responsive Layout (REQ-010)

### REQ-010-001: Mobile Header Two-Row Layout

- **Story:** As a user on a mobile device, I want the header to be organized and easy to use so I don't have to scroll horizontally or struggle with cramped controls.

- **Acceptance Criteria:**
  - On screens 640px wide or narrower, the header reorganizes into two rows
  - Row 1 contains: logo on the left, logout icon button on the right
  - Row 2 contains: nav links (首頁, 法條瀏覽) on the left, law-type-select dropdown on the right
  - The header never causes horizontal overflow on any device 320px wide or wider
  - All tap targets in the mobile header are at minimum 44x44px (WCAG 2.5.5 guideline)

### REQ-010-002: Mobile Header Hidden Elements

- **Story:** As a user on mobile, I want the header to surface only the most essential controls so the interface stays clean.

- **Acceptance Criteria:**
  - On screens 640px wide or narrower:
    - The username text (`.user-name` span) is hidden
    - The language toggle (`.lang-toggle`) is hidden
  - The law-type-select dropdown remains visible and full-width in row 2
  - The logout icon button remains visible in row 1

### REQ-010-003: Desktop Header Unchanged

- **Story:** As a user on desktop, I want the header to continue working exactly as it does today.

- **Acceptance Criteria:**
  - On screens wider than 640px, all existing header elements remain visible and laid out in a single row
  - No visual regression on desktop layouts at 641px and wider
  - Username text, lang-toggle, law-type-select, nav links, and logout button all appear in their current positions on desktop

### REQ-010-004: Smooth Breakpoint Transition

- **Story:** As a user who resizes the browser window, I want the header to switch cleanly between its mobile and desktop layouts without any flash or broken intermediate state.

- **Acceptance Criteria:**
  - The layout switches at exactly 640px using a CSS media query
  - No layout jump or content overflow occurs at the breakpoint boundary
  - The header height adjusts naturally to accommodate two rows on mobile
