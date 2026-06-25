# Harness Plan

## Current Phase

Review

## Harness Status

- Lightweight harness files are present in `.harness/`.
- `.harness/config.json` exists, but no full CLI state file is present.
- Active implementation is tracked manually in this file because the local harness config has no verify/check commands registered.

## Required Workflow

1. office-hours
2. superpowers:brainstorming
3. superpowers:writing-plans
4. implementation
5. verify/check/record

The previous chatbot conversation redesign plan is complete:

- Active Implementation Plan: `docs/plans/PLAN_chatbot-conversation-redesign.md`

The current requested work is a follow-up conversation routing fix.

## Active Spec

`docs/superpowers/specs/contextual-followups-design.md`

Supporting product requirements:

- `PRD.md`
- `docs/plans/PLAN_chatbot-conversation-redesign.md`

## Active Implementation Plan

`docs/superpowers/plans/contextual-followups-plan.md`

## Current Goal

Make post-answer chat messages continue from prior conversation context by default and answer follow-up questions without repeating the fixed menu templates, while preserving explicit menu routing, deterministic tool grounding, safety redirects, and regression tests.

## Non-Goals

- Do not introduce React or FastAPI in this phase.
- Do not add new dependencies without explicit approval.
- Do not change the JSON input/output contract of `src/tools/*.py`.
- Do not make the LLM calculate saju directly.
- Do not expose `.env` or secrets.
- Do not weaken or delete tests to make verification pass.
- Do not replace the deterministic router with an LLM router.

## Completion Criteria

- Contextual Korean follow-up questions after a saju answer route as `follow_up`.
- Follow-ups reuse `last_intent` and `last_tool_results` without rerunning tools.
- Follow-up prompts preserve the saju counselor persona but do not include the fixed menu output template.
- Follow-up fallback answers respond in free form and do not repeat the saju table, lucky-color blocks, menu sections, or generic full-reading structure.
- Explicit new menu requests still switch intent.
- Safety-blocked topics still win before follow-up fallback.
- No-context ambiguous messages still ask for clarification or profile data.
- Required final validation commands pass or any gap is documented.

## Verification Plan

Required commands:

```powershell
pytest --collect-only -q
pytest -q
streamlit run app.py
```

Additional checks:

- `pytest tests/test_chat_intent.py tests/test_chat_flow.py tests/test_orchestrator.py -q`
- `pytest tests/test_prompts.py tests/test_app_chat_ui.py -q`
- Manual Streamlit smoke scenarios:
  - save a profile
  - ask "내 사주를 풀이해줘."
  - ask "토가 강하고 금의 기운이 적다는 것은 어떤 성격의 사람이라는 의미야?"
  - verify the answer continues from the prior saju result
  - verify "오늘 운세 알려줘" switches to today's fortune
  - blocked topics are redirected safely
  - fallback answer works without an API key

## Current Evidence

- Code review found the failing path in `src/chat_intent.py`: narrow follow-up keyword detection returns `clarify`.
- Reproduction: the example Korean follow-up returns `RoutedIntent(kind='clarify')` even with `last_intent='saju_reading'` and existing `last_tool_results`.
- Reproduction: `Orchestrator.handle_message()` returns `reply_kind='clarify'` and no `llm_package` for the same state.
- Implemented contextual follow-up fallback in `src/chat_intent.py`.
- Added routing and conversation-flow regression tests for Korean contextual follow-ups.
- Follow-up generation gap found: `src/prompts.py` still injected the menu output format into follow-up prompts, which could make the model repeat the full fixed answer structure.
- Updated `src/prompts.py` so follow-up prompts use persona-only free-form instructions while initial/new menu requests still receive the fixed menu format.
- Updated fallback follow-up answers to avoid menu-section output and answer the user's follow-up directly from prior tool JSON.
- Added prompt/fallback regression tests covering the fixed-template suppression on follow-up turns.
- `pytest tests/test_prompts.py tests/test_chat_intent.py tests/test_chat_flow.py tests/test_orchestrator.py -q`: 53 passed.
- `pytest --collect-only -q`: 137 tests collected.
- `pytest -q`: 137 passed.
- `streamlit run app.py --server.headless true --server.fileWatcherType none --server.port 8503`: HTTP 200 smoke passed at `http://127.0.0.1:8503` (PID 27776).
