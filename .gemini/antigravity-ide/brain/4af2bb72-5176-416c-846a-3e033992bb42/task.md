# AutoBot Refactor — Query Agent + Fuzzy Logic + Pydantic Intent

- [x] Read & understand existing codebase
- [x] Update `models/schemas.py` — Add IntentResult, QueryPlan, FuzzyCarFilter models
- [x] Create `db/fuzzy_queries.py` — Fuzzy query executor
- [x] Create `agents/query_agent.py` — Query Agent that generates QueryPlan from user prompt
- [x] Update `agents/car_agent.py` — Wire Pydantic intent + Query Agent
- [x] Update `requirements.txt` — Add rapidfuzz
- [x] Verify imports and consistency
- [x] Smoke tests: fuzzy executor, normalizers, keyword plan — all PASSED
