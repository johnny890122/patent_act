# Design Document: 專利法 AI 刷題助手

## 1. Architecture

**Stack:** Python Flask · MongoDB · Heroku (gunicorn) · OpenRouter (LLM API)

`app.py` is the main entry point (Flask app factory + route registration). As the app grows, modules are split into:

```text
app.py              ← Flask app factory + route registration
routes/
  quiz.py           ← /quiz/* endpoints
  laws.py           ← /laws/* endpoints
  admin.py          ← /admin/init, /admin/generate
services/
  question_gen.py   ← LLM question generation logic
  grader.py         ← LLM grading logic
  inventory.py      ← question pool inventory & trigger logic
db/
  models.py         ← MongoDB Singleton manager & PyMongo collection helpers & Dataclass schemas
knowledge/          ← Markdown files of 專利法 articles & mock JSON data
```

## 2. API Endpoints (Planned)
- `GET /api/quiz/available`: Check available question count. Parameters: type, mode. Returns `{ available: int }`.
- `POST /quiz/session`: Start a new session. Parameters: type, mode, count. Returns `session_id` + `questions[]`.
- `POST /quiz/session/:id/answer`: Submit answer (sync grade for MCQ, async style LLM for Short Answer).
- `POST /quiz/session/:id/answer/:aid/appeal`: Appeal score.
- `DELETE /questions/:qid`: Soft delete question.
- `PUT /laws/:id/star`: Toggle star status.
- `GET /laws`: Retrieve paginated laws.

## 3. Database Schema (MongoDB)

All schemas are enforced at the application level using Python `dataclasses`. The MongoDB connection is managed via a Singleton `Database` class.

**laws**
```python
@dataclass
class LawModel:
    article_number: str
    content: str
    chapter: str
    lang: str = "zh-TW"  # NEW: Language tag (zh-TW or en)
    is_starred: bool = False
    total_score: float = 0.0
    attempt_count: int = 0
    avg_score: float = 0.0
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
    lang: str = "zh-TW"  # NEW: Language tag (zh-TW or en)
    options: Optional[List[str]] = None
    is_deleted: bool = False
    base_question_id: Optional[str] = None  # NEW: Links zh-TW ↔ en translations
```

**user_progress**
```python
@dataclass
class UserProgressModel:
    question_id: str
    correct_streak: int = 0
    needs_review: bool = True
    last_score: float = 0.0
    is_appealed: bool = False
```

**i18n_mapping (NEW)**
```python
@dataclass
class I18nMappingModel:
    zh_tw_law_id: str      # ObjectId of zh-TW law
    en_law_id: str         # ObjectId of en law
    article_number: str    # Common article number (e.g., "Article 1")
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

## 6. User Flow

### Screen Inventory
| ID | Screen Name | Description |
|---|---|---|
| S-01 | Home / Dashboard | Entry point; shows streak, starred laws count |
| S-02 | Quiz Config | Picker for type, mode, count |
| S-03 | Loading (sync) | Blocking spinner when inventory < n |
| S-04 | Question Display | Single question card |
| S-05 | Result / Feedback | Score badge, LLM feedback, appeal/delete buttons |
| S-06 | Session Summary | Aggregated stats for completed session |
| S-07 | Law Article Browser | Paginated list of all laws |
| S-08 | Law Article Detail | One article + its question history |

## 7. Internationalization (i18n) Architecture

### 7.1 Language Support
- **Content-only i18n**: Laws and questions are available in zh-TW and EN
- **UI remains in Chinese**: All buttons, labels, navigation, and system messages stay in Traditional Chinese (zh-TW)
- **Database structure**: 
  - Each law article is stored with a `lang` field (zh-TW or en)
  - Questions are similarly tagged with `lang` field
  - Bidirectional mapping via `article_number` for laws and `base_question_id` for questions

### 7.2 Question Translation Flow
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

### 7.3 Law Article i18n
- Existing zh-TW laws from `knowledge/truth_law.json` remain unchanged with `lang: zh-TW`
- New EN laws from `knowledge/patent_law_en.json` are inserted with `lang: en`
- Bidirectional mapping is stored in a separate `i18n_mapping` collection for easy lookups
- Law detail pages can show both versions side-by-side or allow language switching (UI enhancement for future)
