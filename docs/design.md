# Design Document: 專利法 AI 刷題助手

## 1. Architecture

**Stack:** Python Flask · MongoDB · Heroku (gunicorn) · OpenRouter (LLM API)

`app.py` is the main entry point (Flask app factory + route registration). As the app grows, modules are split into:

```text
app.py              ← Flask app factory + route registration
routes/
  auth.py           ← NEW: /auth/* endpoints (login, logout, session check)
  quiz.py           ← /quiz/* endpoints
  laws.py           ← /laws/* endpoints
  admin.py          ← /admin/init, /admin/generate
services/
  question_gen.py   ← LLM question generation logic
  grader.py         ← LLM grading logic
  inventory.py      ← question pool inventory & trigger logic
  auth.py           ← NEW: User authentication & session management
db/
  models.py         ← MongoDB Singleton manager & PyMongo collection helpers & Dataclass schemas
knowledge/          ← Markdown files of 專利法 articles & mock JSON data
```

## 2. API Endpoints (Planned)

### 2.1 Authentication Endpoints (NEW)
- `GET /auth/login`: Show login page
- `POST /auth/login`: Validate username and create session. Returns redirect to dashboard.
- `POST /auth/logout`: Clear session and redirect to login.
- `GET /auth/current`: Check current logged-in user. Returns `{ user_id, username, display_name }`.

### 2.2 Quiz Endpoints
- `GET /api/quiz/available`: Check available question count. Parameters: type, mode. Returns `{ available: int }`. **Requires login.**
- `POST /quiz/session`: Start a new session. Parameters: type, mode, count. Returns `session_id` + `questions[]`. **Requires login.**
- `POST /quiz/session/:id/answer`: Submit answer (sync grade for MCQ, async style LLM for Short Answer). **Requires login.**
- `POST /quiz/session/:id/answer/:aid/appeal`: Appeal score. **Requires login.**
- `DELETE /questions/:qid`: Soft delete question. **Requires login.**

### 2.3 Laws Endpoints
- `PUT /laws/:id/star`: Toggle star status for current user. **Requires login.**
- `GET /laws`: Retrieve paginated laws with optional search. **Requires login.**
  - Query Parameters:
    - `page`: int (pagination)
    - `per_page`: int (items per page)
    - `chapter`: str (filter by chapter)
    - `starred`: bool (filter by starred status)
    - `sort`: str (sort field)
    - `order`: str (asc/desc)
    - `search`: str (NEW - search by article_number or content, case-insensitive)
    - `lang`: str (language filter)
  - Search Implementation:
    - Uses MongoDB `$regex` with case-insensitive flag
    - Searches in both `article_number` and `content` fields using `$or`
    - Can be combined with chapter filter and other filters
    - Example: `/api/laws?search=發明&chapter=第二章&page=1`

## 3. Database Schema (MongoDB)

All schemas are enforced at the application level using Python `dataclasses`. The MongoDB connection is managed via a Singleton `Database` class.

### 3.1 Multi-User Architecture Changes

**Key Design Decisions:**
1. **Shared Content**: Laws and questions are shared across all users (efficient, reduces duplication)
2. **Personal Data**: Progress, stars, and statistics are per-user (isolated, independent tracking)
3. **Composite Keys**: Many collections use `(user_id, resource_id)` as composite unique keys

**users (NEW)**
```python
@dataclass
class UserModel:
    username: str          # Unique login identifier (e.g., "alice")
    display_name: str      # Display name (e.g., "Alice Chen")
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
```

**laws**
```python
@dataclass
class LawModel:
    article_number: str
    content: str
    chapter: str
    article_number_int: int = 0  # For sorting
    lang: str = "zh-TW"  # Language tag (zh-TW or en)
    # REMOVED: is_starred, total_score, attempt_count, avg_score (now per-user)
```

**questions**
```python
@dataclass
class QuestionModel:
    law_id: str
    type: Literal["MCQ", "ShortAnswer"]
    content: str
    correct_answer: str
    ai_explanation: str
    lang: str = "zh-TW"  # Language tag (zh-TW or en)
    options: Optional[List[str]] = None
    is_deleted: bool = False
    base_question_id: Optional[str] = None  # Links zh-TW ↔ en translations
    # REMOVED: is_starred (now per-user)
```

**user_progress (UPDATED)**
```python
@dataclass
class UserProgressModel:
    user_id: str           # NEW: Links to users collection
    question_id: str
    correct_streak: int = 0
    needs_review: bool = True
    last_score: float = 0.0
    is_appealed: bool = False
    # Composite unique index: (user_id, question_id)
```

**user_law_stars (NEW)**
```python
@dataclass
class UserLawStarModel:
    user_id: str           # Links to users collection
    law_id: str            # Links to laws collection
    created_at: datetime = field(default_factory=datetime.utcnow)
    # Composite unique index: (user_id, law_id)
```

**user_law_stats (NEW)**
```python
@dataclass
class UserLawStatsModel:
    user_id: str           # Links to users collection
    law_id: str            # Links to laws collection
    total_score: float = 0.0
    attempt_count: int = 0
    avg_score: float = 0.0
    # Composite unique index: (user_id, law_id)
```

**user_question_stars (NEW)**
```python
@dataclass
class UserQuestionStarModel:
    user_id: str           # Links to users collection
    question_id: str       # Links to questions collection
    created_at: datetime = field(default_factory=datetime.utcnow)
    # Composite unique index: (user_id, question_id)
```

**i18n_mapping**
```python
@dataclass
class I18nMappingModel:
    zh_tw_law_id: str      # ObjectId of zh-TW law
    en_law_id: str         # ObjectId of en law
    article_number: str    # Common article number (e.g., "Article 1")
```

### 3.2 Index Strategy (NEW)
```python
# users collection
users.create_index("username", unique=True)

# user_progress collection
user_progress.create_index([("user_id", 1), ("question_id", 1)], unique=True)
user_progress.create_index([("user_id", 1), ("needs_review", 1)])

# user_law_stars collection
user_law_stars.create_index([("user_id", 1), ("law_id", 1)], unique=True)
user_law_stars.create_index("user_id")

# user_law_stats collection
user_law_stats.create_index([("user_id", 1), ("law_id", 1)], unique=True)

# user_question_stars collection
user_question_stars.create_index([("user_id", 1), ("question_id", 1)], unique=True)
user_question_stars.create_index("user_id")
```

## 4. LLM Integration (OpenRouter)
- **Question Generation**: Uses a thinking model (quality over speed). Always passes the 3 most-recent questions for that `law_id` for diversity.  
  Output schema: `{ content, options, correct_answer, ai_explanation }`
- **Short Answer Grading**: Uses a fast model. Scores must be `0`, `0.5`, or `1`.  
  Output schema: `{ score, feedback }`
- **Law Parsing**: Converts raw Markdown article text into structured `laws` documents.  
  Output schema: `{ chapter, article_number, content }`
- **Translation Service (NEW)**: LLM agent that translates questions from zh-TW ↔ en while preserving meaning and structure.
  - Used for data migration: translates existing zh-TW questions to EN
  - Used for new questions: generates both zh-TW and EN versions simultaneously
  - Output schema: `{ content_en, options_en, correct_answer_en, ai_explanation_en }`

## 5. Question Inventory Logic & Rules

### 5.1 Pre-flight Check (NEW)
Before starting a quiz session, the frontend should check available questions:
1. Call `GET /api/quiz/available?type={type}&mode={mode}` on config change
2. Compare `available` with user's requested `count`
3. If `available < count`, show warning modal with options:
   - **Option 1**: Adjust count to `available` (e.g., "使用現有的 2 題")
   - **Option 2**: Switch to "mixed" mode (if applicable)
   - **Option 3**: Cancel and reconfigure
4. Only proceed to `POST /quiz/session` after user confirms

### 5.2 Session Creation Rules
When a quiz session is started for `n` questions:
| Available in pool | Action |
|---|---|
| `>= 4n` | Pull `n` directly from DB |
| `n <= available < 4n` | Return `n` to user; trigger async generation of 40 more in background |
| `< n` | ~~Block and generate synchronously~~ **Prevented by pre-flight check** |

Session Types:
- `new`: `needs_review == False` AND never attempted.
- `review`: `needs_review == True`.
- `mixed`: 50% new + 50% review.

**Important Change**: The `< n` synchronous generation scenario should be **prevented** by the pre-flight check. This ensures users don't get unexpected questions that don't match their selected mode (e.g., getting new questions when they selected "review" mode).

### 5.3 Multi-User Query Modifications (NEW)
All inventory and session queries must be filtered by `user_id`:
- **Available questions**: Filter by `user_progress.user_id == current_user_id`
- **New questions**: `user_progress.find({ user_id: current_user_id, needs_review: false })`
- **Review questions**: `user_progress.find({ user_id: current_user_id, needs_review: true })`

## 6. Authentication & Session Management (NEW)

### 6.1 Flask Session Strategy
- Use Flask's built-in session management (server-side session storage)
- Session data stored in cookies (signed with `SECRET_KEY`)
- Session contains: `user_id`, `username`, `display_name`
- Session timeout: configurable (default 7 days for study apps)

### 6.2 Login Flow
1. User visits any route
2. If not logged in, redirect to `/auth/login`
3. User enters `username` in login form
4. `POST /auth/login` validates username against `users` collection
5. If valid:
   - Create session: `session['user_id'] = user_id`
   - Update `users.last_login = datetime.utcnow()`
   - Redirect to `/` (dashboard)
6. If invalid: Show error "用戶名稱不存在，請聯繫管理員"

### 6.3 Authentication Decorator
```python
from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
```

### 6.4 User Context Helper
```python
def get_current_user():
    """Return user_id from session, or None if not logged in"""
    return session.get('user_id')
    
def get_current_user_info():
    """Return full user info dict from session"""
    if 'user_id' not in session:
        return None
    return {
        'user_id': session['user_id'],
        'username': session['username'],
        'display_name': session['display_name']
    }
```

## 7. User Flow (UPDATED)

### 7.1 Screen Inventory (UPDATED)
| ID | Screen Name | Description |
|---|---|---|
| S-00 | Login Page | NEW: Username input form |
| S-01 | Home / Dashboard | Entry point; shows user's personal streak, starred laws count |
| S-02 | Quiz Config | Picker for type, mode, count |
| S-03 | Loading (sync) | Blocking spinner when inventory < n |
| S-04 | Question Display | Single question card |
| S-05 | Result / Feedback | Score badge, LLM feedback, appeal/delete buttons |
| S-06 | Session Summary | Aggregated stats for completed session |
| S-07 | Law Article Browser | Paginated list of all laws |
| S-08 | Law Article Detail | One article + its question history |

### 7.2 Data Isolation Examples (NEW)
All queries must be scoped to the current user:

**Dashboard (S-01)**:
```python
user_id = get_current_user()
# Get user's progress
progress_records = user_progress_collection.find({ "user_id": user_id })
# Get user's starred laws count
starred_count = user_law_stars_collection.count_documents({ "user_id": user_id })
```

**Quiz Session**:
```python
user_id = get_current_user()
# Get review questions for this user
review_questions = user_progress_collection.find({
    "user_id": user_id,
    "needs_review": True
})
```

**Law Stars**:
```python
user_id = get_current_user()
law_id = request.json['law_id']
# Toggle star for current user only
existing = user_law_stars_collection.find_one({
    "user_id": user_id,
    "law_id": law_id
})
if existing:
    user_law_stars_collection.delete_one({"_id": existing["_id"]})
else:
    user_law_stars_collection.insert_one({
        "user_id": user_id,
        "law_id": law_id,
        "created_at": datetime.utcnow()
    })
```

## 8. Internationalization (i18n) Architecture

### 8.1 Language Support
- **Content-only i18n**: Laws and questions are available in zh-TW and EN
- **UI remains in Chinese**: All buttons, labels, navigation, and system messages stay in Traditional Chinese (zh-TW)
- **Database structure**: 
  - Each law article is stored with a `lang` field (zh-TW or en)
  - Questions are similarly tagged with `lang` field
  - Bidirectional mapping via `article_number` for laws and `base_question_id` for questions

### 8.2 Question Translation Flow
1. **New Question Generation**:
   - When a question is generated, `services/question_gen.py` simultaneously generates zh-TW and EN versions
   - Both versions share the same `base_question_id` for linking
   - Both are stored as separate documents with their respective `lang` field
   - LLM prompt is enhanced to ensure both languages have identical meaning (same correct answer semantically)

2. **Data Migration (Existing Questions)**:
   - Existing zh-TW questions in the database are translated to EN using `services/translator.py`
   - Translation uses an LLM agent with strict prompts to preserve question integrity
   - For each zh-TW question, an EN version is created and linked via `base_question_id`
   - Process is idempotent (can be re-run safely)

3. **User Progress Tracking**:
   - Grading is language-agnostic: when a user answers a zh-TW question and gets a score, the `user_progress` record is marked
   - When querying questions for a session, the system can optionally filter by `lang` parameter
   - Currently, UI remains zh-TW, so most queries filter for zh-TW questions

### 8.3 Law Article i18n
- Existing zh-TW laws from `knowledge/truth_law.json` remain unchanged with `lang: zh-TW`
- New EN laws from `knowledge/patent_law_en.json` are inserted with `lang: en`
- Bidirectional mapping is stored in a separate `i18n_mapping` collection for easy lookups
- Law detail pages can show both versions side-by-side or allow language switching (UI enhancement for future)
