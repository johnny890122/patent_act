# Requirements: 專利法 AI 刷題助手

## Project Overview
**專利法 AI 刷題助手** — A multi-user mobile-first web app for Taiwan Patent Law (專利法) exam preparation.
Core loop: AI dynamically generates exam questions bound to specific law articles, grades short-answer responses, and tracks mastery per article for each user.

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
