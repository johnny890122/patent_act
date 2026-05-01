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
- [ ] 4.1 Build basic HTML/CSS/JS templates for Dashboard (S-01) and Law Article Browser (S-07).
- [ ] 4.2 Build Quiz Config (S-02) UI and wire to `POST /quiz/session`.
- [ ] 4.3 Build Quiz Loop UI (S-04, S-05) handling both MCQ and Short Answer inputs.
- [ ] 4.4 Build Session Summary (S-06) and bind appeal/delete interactions.
- [ ] 4.5 Test end-to-end question generation, answering, and grading loop.
