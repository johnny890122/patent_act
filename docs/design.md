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
- `GET /api/quiz/available`: Check available question count. Parameters: type, mode, **law_type** (NEW). Returns `{ available: int }`. **Requires login.**
- `POST /quiz/session`: Start a new session. Parameters: type, mode, count, **law_type** (NEW). Returns `session_id` + `questions[]`. **Requires login.**
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
    - `search`: str (search by article_number or content, case-insensitive)
    - `lang`: str (language filter)
    - `law_type`: str (NEW - filter by law type: patent-act, trademark-act, etc.)
  - Search Implementation:
    - Uses MongoDB `$regex` with case-insensitive flag
    - Searches in both `article_number` and `content` fields using `$or`
    - Can be combined with chapter filter and other filters
    - **NEW**: All queries automatically filtered by selected law_type from session
    - Example: `/api/laws?search=發明&chapter=第二章&law_type=patent-act&page=1`

### 2.4 Law Type Management Endpoints (NEW)
- `GET /api/law-types`: Get list of available law types. Returns `[{ type, name_zh, name_en, article_count }]`. **Requires login.**
- `POST /api/law-types/select`: Set current law type in session. Parameters: `law_type`. **Requires login.**
- `GET /api/law-types/current`: Get current selected law type from session. **Requires login.**

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
    type: str = "patent-act"  # NEW: Law type identifier (patent-act, trademark-act, etc.)
    article_number_int: int = 0  # For sorting
    lang: str = "zh-TW"  # Language tag (zh-TW or en)
    # REMOVED: is_starred, total_score, attempt_count, avg_score (now per-user)
```

**Supported Law Types:**
- `"patent-act"` - 專利法 (Taiwan Patent Law)
- `"trademark-act"` - 商標法 (Taiwan Trademark Law) [Future]
- `"copyright-act"` - 著作權法 (Taiwan Copyright Law) [Future]
- Additional law types can be added as needed

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
    type: str              # NEW: Law type (patent-act, trademark-act, etc.)
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

# laws collection - Multi-law support (NEW)
laws.create_index("type")  # For filtering by law type
laws.create_index([("type", 1), ("lang", 1)])  # Combined filter
laws.create_index([("type", 1), ("article_number_int", 1)])  # For sorted queries

# i18n_mapping collection - Multi-law support (NEW)
i18n_mapping.create_index([("type", 1), ("article_number", 1)])  # For law type specific lookups
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

## 9. Multi-Law Support Architecture (NEW)

### 9.1 Design Overview

**Goal**: Support multiple law types (Patent Law, Trademark Law, Copyright Law, etc.) within the same system while maintaining data integrity and user experience.

**Key Principles**:
1. **Backward Compatibility**: Existing Patent Law data remains functional with default `type = "patent-act"`
2. **Data Isolation**: Each law type is completely independent with separate articles, questions, and statistics
3. **Session-Based Selection**: User's current law type is stored in Flask session for seamless navigation
4. **Minimal Code Changes**: Leverage existing architecture with targeted filter additions

### 9.2 Law Type Definition

**Supported Law Types**:
```python
LAW_TYPES = {
    "patent-act": {
        "name_zh": "專利法",
        "name_en": "Patent Law",
        "code": "patent-act"
    },
    "trademark-act": {
        "name_zh": "商標法",
        "name_en": "Trademark Law",
        "code": "trademark-act"
    },
    "copyright-act": {
        "name_zh": "著作權法",
        "name_en": "Copyright Law",
        "code": "copyright-act"
    },
    "patent-examination": {
        "name_zh": "專利審查基準",
        "name_en": "Patent Examination Guidelines",
        "code": "patent-examination"
    }
}
```

**Default Law Type**: `"patent-act"` (for backward compatibility)

**Patent Examination Guidelines**:
- Type code: `"patent-examination"`
- Uses the same `LawModel` schema as patent law
- Stored in `knowledge/examination/` directory, organized by chapters (01-06)
- Data format: JSON files containing arrays of guideline articles
- Each article follows the same structure as patent law articles with appropriate `type` field

### 9.3 Data Migration Strategy

**Phase 1: Schema Update**
1. Add `type` field to [`LawModel`](db/models.py:18-24) with default value `"patent-act"`
2. Add `type` field to [`I18nMappingModel`](db/models.py:77-82)
3. Update database indexes to include `type` field
4. Create migration script to update existing data

**Phase 2: Database Migration**
```python
# Migration Script: scripts/migrate_add_law_type.py

def migrate_laws_add_type():
    """Add type='patent-act' to all existing law articles"""
    result = laws_collection.update_many(
        {"type": {"$exists": False}},  # Only update documents without type field
        {"$set": {"type": "patent-act"}}
    )
    print(f"Updated {result.modified_count} law articles")

def migrate_i18n_mapping_add_type():
    """Add type='patent-act' to all existing i18n mappings"""
    result = i18n_mapping_collection.update_many(
        {"type": {"$exists": False}},
        {"$set": {"type": "patent-act"}}
    )
    print(f"Updated {result.modified_count} i18n mappings")

def create_indexes():
    """Create new indexes for law type filtering"""
    laws_collection.create_index("type")
    laws_collection.create_index([("type", 1), ("lang", 1)])
    laws_collection.create_index([("type", 1), ("article_number_int", 1)])
    i18n_mapping_collection.create_index([("type", 1), ("article_number", 1)])
    print("Indexes created successfully")
```

**Migration Validation**:
- Verify all laws have `type` field: `laws_collection.count_documents({"type": {"$exists": False}})`
- Verify all i18n mappings have `type` field: `i18n_mapping_collection.count_documents({"type": {"$exists": False}})`
- Test queries with type filter work correctly
- Verify no orphaned questions (all questions have valid `law_id` with correct type)

**Rollback Plan**:
```python
# If migration fails, remove type field
laws_collection.update_many({}, {"$unset": {"type": ""}})
i18n_mapping_collection.update_many({}, {"$unset": {"type": ""}})
```

### 9.4 Session Management for Law Type

**Session Storage**:
```python
# Store in Flask session
session['current_law_type'] = 'patent-act'  # Default value

# Helper functions in services/auth.py
def get_current_law_type() -> str:
    """Get current law type from session, default to patent-act"""
    return session.get('current_law_type', 'patent-act')

def set_current_law_type(law_type: str):
    """Set current law type in session"""
    if law_type in LAW_TYPES:
        session['current_law_type'] = law_type
        return True
    return False
```

**API Endpoints**:
- `GET /api/law-types`: List all available law types with article counts
- `POST /api/law-types/select`: Change current law type in session
- `GET /api/law-types/current`: Get current selected law type

### 9.5 Query Modification Pattern

**All queries must include law type filter**. Here are the key patterns:

**Laws Query** (routes/laws.py):
```python
# Before:
query_filter = {}
if chapter:
    query_filter['chapter'] = chapter

# After:
law_type = get_current_law_type()  # Get from session
query_filter = {'type': law_type}  # REQUIRED filter
if chapter:
    query_filter['chapter'] = chapter
```

**Questions Query via Laws** (services/inventory.py):
```python
# Before:
laws = list(laws_collection.find({}, {"_id": 1}))

# After:
law_type = get_current_law_type()
laws = list(laws_collection.find({"type": law_type}, {"_id": 1}))
```

**Question Generation** (services/question_gen.py):
```python
# When generating questions, ensure law_id belongs to current law type
law = laws_collection.find_one({"_id": ObjectId(law_id)})
if law and law.get('type') != get_current_law_type():
    raise ValueError(f"Law {law_id} does not belong to current law type")
```

**Dashboard Statistics** (routes/frontend.py):
```python
# Filter statistics by current law type
law_type = get_current_law_type()
# Get laws for this type
law_ids = [str(law['_id']) for law in laws_collection.find(
    {"type": law_type},
    {"_id": 1}
)]
# Filter user stats by these law_ids
stats = user_law_stats_collection.find({
    "user_id": ObjectId(user_id),
    "law_id": {"$in": law_ids}
})
```

### 9.6 UI/UX Changes

**Law Type Selector**:
- Add law type dropdown in navigation bar or dashboard
- Display current law type prominently (e.g., "當前法律: 專利法")
- Allow users to switch law types with instant filter update

**Visual Indicators**:
- Show law type badge on law article cards
- Display law type in quiz configuration
- Include law type in session summary

**Breadcrumb Updates**:
- Dashboard → [Law Type] → Quiz Config
- Dashboard → [Law Type] → Law Browser → Law Detail

### 9.7 Adding New Law Types

**Process**:
1. Prepare law content files (markdown or JSON) with proper structure
2. Create initialization script (e.g., `scripts/init_trademark_law.py`)
3. Parse and insert law articles with `type = "trademark-act"`
4. Create i18n mappings if multi-language support needed
5. Verify data integrity and indexes
6. Update `LAW_TYPES` constant in code

**Example Init Script**:
```python
# scripts/init_trademark_law.py
from services.law_parser import LawParser
from db.models import laws_collection

def init_trademark_law():
    parser = LawParser()
    
    # Parse zh-TW version
    with open('knowledge/trademark_law_zh.md', 'r') as f:
        laws_zh = parser.parse(f.read())
        for law in laws_zh:
            law['type'] = 'trademark-act'
            law['lang'] = 'zh-TW'
            laws_collection.insert_one(law)
    
    # Parse EN version
    with open('knowledge/trademark_law_en.md', 'r') as f:
        laws_en = parser.parse(f.read())
        for law in laws_en:
            law['type'] = 'trademark-act'
            law['lang'] = 'en'
            laws_collection.insert_one(law)
    
    print("Trademark Law initialized successfully")
```

### 9.8 Patent Examination Guidelines Initialization

**Data Source**:
- Location: `knowledge/examination/` directory
- Structure: Organized by chapters in subdirectories (01/, 02/, 03/, 04/, 05/, 06/)
- Format: JSON files (e.g., `1-01.json`, `1-02.json`, etc.)
- Total files: 54 JSON files across 6 chapter directories

**Initialization Script**: `scripts/init_examination_guidelines.py`

```python
#!/usr/bin/env python3
"""
Initialize Patent Examination Guidelines into database.
Reads JSON files from knowledge/examination/ and inserts as law type 'patent-examination'.
"""

import os
import json
import glob
from pymongo import MongoClient
from db.models import LawModel, Database

def init_examination_guidelines(mongo_uri=None):
    """
    Load examination guideline JSON files and insert into database.
    
    Args:
        mongo_uri: MongoDB connection string (optional, uses env var if not provided)
    """
    db = Database()
    laws_collection = db.laws_collection
    
    # Pattern to find all JSON files in examination subdirectories
    pattern = 'knowledge/examination/*/*.json'
    json_files = sorted(glob.glob(pattern))
    
    inserted_count = 0
    updated_count = 0
    
    for json_file in json_files:
        with open(json_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        
        for article in articles:
            # Set type to patent-examination
            article['type'] = 'patent-examination'
            
            # Ensure lang field is set
            if 'lang' not in article:
                article['lang'] = 'zh-TW'
            
            # Validate with LawModel
            law_model = LawModel(**article)
            
            # Upsert using composite key (article_number, lang, type)
            result = laws_collection.update_one(
                {
                    'article_number': law_model.article_number,
                    'lang': law_model.lang,
                    'type': law_model.type
                },
                {
                    '$set': {
                        'content': law_model.content,
                        'chapter': law_model.chapter,
                        'article_number_int': law_model.article_number_int,
                    }
                },
                upsert=True
            )
            
            if result.upserted_id:
                inserted_count += 1
            else:
                updated_count += 1
    
    print(f"✅ Examination Guidelines initialized")
    print(f"   Inserted: {inserted_count}")
    print(f"   Updated: {updated_count}")
    print(f"   Total files processed: {len(json_files)}")
```

**Usage**:
```bash
python scripts/init_examination_guidelines.py
```

**Data Validation**:
- Verify all JSON files are valid and parseable
- Check all required fields exist (article_number, content, chapter, article_number_int)
- Ensure article_number_int is unique within each chapter for proper sorting
- Validate type is set to "patent-examination"
- Confirm lang field is properly set

### 9.9 Testing Strategy

**Unit Tests**:
- Test `get_current_law_type()` with/without session data
- Test `set_current_law_type()` with valid/invalid types
- Test query filters include law type

**Integration Tests**:
- Test law listing filtered by type
- Test quiz session creation with law type filter
- Test statistics aggregation per law type
- Test switching between law types maintains correct data

**Migration Tests**:
- Test migration script is idempotent (can run multiple times)
- Test all existing data gets `type = "patent-act"`
- Test no data loss during migration
- Test rollback procedure works correctly

### 9.9 Performance Considerations

**Index Strategy**:
- `laws.type` (single field index)
- `laws.(type, lang)` (compound index for filtered i18n queries)
- `laws.(type, article_number_int)` (compound index for sorted queries)
- `i18n_mapping.(type, article_number)` (compound index for lookups)

**Query Optimization**:
- Always filter by law type early in query pipeline
- Use projection to limit returned fields
- Batch queries where possible to reduce database round trips

**Caching Opportunities**:
- Cache law type metadata (names, counts) in memory
- Cache current user's law type selection
- Consider caching frequently accessed law articles

### 9.10 Error Handling

**Common Error Scenarios**:
1. **Invalid law type**: Return 400 with error message "無效的法律類型"
2. **No laws found for type**: Return empty list with message "此法律尚未初始化"
3. **Type mismatch**: When law_id doesn't match current type, return 403 "此法條不屬於當前法律類型"
4. **Migration failure**: Log error, rollback changes, notify admin

**Graceful Degradation**:
- If law type not in session, default to "patent-act"
- If invalid type provided, fallback to "patent-act"
- Log warnings for debugging but don't break user experience

### 9.11 Security Considerations

**Access Control**:
- Users can only access law types they have permission for (future enhancement)
- No direct database manipulation via API
- Validate all law type parameters against whitelist

**Data Integrity**:
- Foreign key relationships maintained via `law_id` references
- Prevent orphaned questions when law type is removed
- Cascade effects documented and tested

## 10. Mobile Header Responsive Layout Design

### 10.1 Design Goal (REQ-010)

The header currently renders all controls — logo, nav links, law-type-select, lang-toggle, username, and logout button — in a single flex row. On viewports 640px and narrower this row overflows or becomes too cramped to use. The fix reorganizes the header into two stacked rows exclusively for the mobile breakpoint, with no changes to the desktop layout.

### 10.2 Two-Row Mobile Layout Structure

```text
┌─────────────────────────────────────────────┐
│ Row 1: [📚 專利法刷題]          [logout btn] │
├─────────────────────────────────────────────┤
│ Row 2: [首頁] [法條瀏覽]   [law-type-select]│
└─────────────────────────────────────────────┘
```

**Row 1** (`header-row-1`):

- Left: `.logo` — unchanged appearance, `flex: 0 0 auto`
- Right: logout icon button (`.btn-logout` inside `.user-menu`) — `flex: 0 0 auto`
- Hidden in row 1: `.user-name` text span, `.lang-toggle`

**Row 2** (`header-row-2`):

- Left: `.nav` links (首頁, 法條瀏覽) — existing styles, `flex: 0 0 auto`
- Right: `.law-type-selector` containing `#law-type-select` — `flex: 1`, full available width

### 10.3 HTML Structure Change

No new HTML elements are required. The two-row appearance is achieved purely with CSS by changing `.header-content` from a single `flex-row` to a `flex-wrap: wrap` or `flex-direction: column` container and reorganizing child element ordering and widths via media query.

The `.header-content` element uses `flex-wrap: wrap` at mobile breakpoint. Children are assigned explicit `order` values and `width` properties:

| Element | Desktop order | Mobile order | Mobile width |
| --- | --- | --- | --- |
| `.logo` | — | 1 | `auto` |
| `.nav` | — | 3 | `auto` |
| `.header-right` | — | 2 | `auto` |

To achieve two distinct rows cleanly, `.logo` and `.header-right` share row 1 (they are the only items with `flex: 0` and together do not exceed 100% width), while `.nav` and `.law-type-selector` wrap to row 2.

Concretely:

- `.header-content`: add `flex-wrap: wrap` and `align-items: center`
- `.logo`: `order: 1`
- `.header-right`: `order: 2; margin-left: auto` — pushes logout button to far right of row 1
- `.nav`: `order: 3; width: 100%; justify-content: flex-start` — forces a new row, left-aligned
- Move `.law-type-selector` out of `.header-right` and into `.nav` row by giving `.header-right` `width: auto` and repositioning the selector

Because the `.law-type-selector` currently lives inside `.header-right`, the cleanest CSS-only approach is:

1. `.header-right` at mobile: hide `.user-name` and `.lang-toggle`; keep only logout button visible
2. `.nav` at mobile: `width: 100%` to force it to row 2; add the law-type-select after nav links via CSS `order` on `.law-type-selector` placed as a sibling element, OR duplicate the select in the nav row (preferred: move `.law-type-selector` out of `.header-right` in HTML to sit between `.nav` and `.header-right` — assigning `order: 4` and `margin-left: auto` to float it right within row 2)

**Recommended minimal HTML change**: Move `<div class="law-type-selector">` to be a direct child of `.header-content` (sibling of `.logo`, `.nav`, and `.header-right`), not nested inside `.header-right`. This gives CSS full control over its row assignment.

### 10.4 CSS Rules (mobile breakpoint, `max-width: 640px`)

```css
@media (max-width: 640px) {
  .header {
    padding: 0.5rem;
  }

  .header-content {
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
  }

  /* Row 1 left */
  .logo {
    order: 1;
    flex: 0 0 auto;
  }

  /* Row 1 right — logout only */
  .header-right {
    order: 2;
    margin-left: auto;
    flex: 0 0 auto;
    gap: 0;
  }

  .user-name {
    display: none;
  }

  .lang-toggle {
    display: none;
  }

  /* Row 2 left — nav links */
  .nav {
    order: 3;
    flex: 1 1 auto;
    justify-content: flex-start;
    gap: 0.25rem;
  }

  /* Row 2 right — law type select */
  .law-type-selector {
    order: 4;
    flex: 0 0 auto;
    margin-left: auto;
  }

  .law-type-select {
    min-width: unset;
    width: auto;
    font-size: 0.8rem;
    padding: 0.375rem 0.5rem;
  }

  /* Ensure nav and law-type-selector together occupy a full row */
  /* (logo + header-right fit row 1; nav + selector wrap to row 2) */
  .nav,
  .law-type-selector {
    /* Combined, these are > 100% of row 1 space, forcing wrap */
  }
}
```

### 10.5 Element Visibility Matrix

| Element | Desktop (>640px) | Mobile (<=640px) |
| --- | --- | --- |
| `.logo` | Visible, row 1 | Visible, row 1 |
| `.nav` (links) | Visible, row 1 | Visible, row 2 |
| `.law-type-selector` | Visible, row 1 (in header-right) | Visible, row 2 (direct child of header-content) |
| `.lang-toggle` | Visible, row 1 | **Hidden** |
| `.user-name` | Visible, row 1 | **Hidden** |
| logout `.btn-logout` | Visible, row 1 | Visible, row 1 |

### 10.6 Files Affected

| File | Change |
| --- | --- |
| `templates/base.html` | Move `.law-type-selector` div to be a direct sibling of `.nav` and `.header-right` inside `.header-content` |
| `static/css/style.css` | Replace existing `@media (max-width: 640px)` header block with new two-row rules |

No JavaScript changes are needed. No backend changes are needed.

### 9.12 Documentation Updates

**For Developers**:
- Update README with multi-law support overview
- Document query filter requirements in code comments
- Create migration guide with step-by-step instructions

**For Administrators**:
- Document how to add new law types
- Provide troubleshooting guide for common issues
- Create data validation scripts

**For Users**:
- Update UI help text to explain law type selection
- Provide FAQ about switching between law types
- Clarify progress tracking is per law type
