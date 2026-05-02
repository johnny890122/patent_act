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
    options: Optional[List[str]] = None
    is_deleted: bool = False
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

## 4. LLM Integration (OpenRouter)
- **Question Generation**: Uses a thinking model (quality over speed). Always passes the 3 most-recent questions for that `law_id` for diversity.  
  Output schema: `{ content, options, correct_answer, ai_explanation }`
- **Short Answer Grading**: Uses a fast model. Scores must be `0`, `0.5`, or `1`.  
  Output schema: `{ score, feedback }`
- **Law Parsing**: Converts raw Markdown article text into structured `laws` documents.  
  Output schema: `{ chapter, article_number, content }`

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
