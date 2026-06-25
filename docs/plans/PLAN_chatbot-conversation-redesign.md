# Implementation Plan: Chatbot Conversation Redesign

**Status**: Implemented and verified  
**Started**: 2026-06-25  
**Last Updated**: 2026-06-25  

## Goal

Convert the app from a form/menu saju report generator into a chat-window based chatbot while preserving deterministic tool contracts, fallback answers without API keys, prompt safety, tests, and documentation.

## Implementation Summary

The redesign is implemented in the current worktree:

- `app.py` is now chat-first with `st.chat_message`, `st.chat_input`, quick actions, sidebar profile onboarding, debug visibility, and rerun-safe message handling.
- `src/conversation.py` adds `ConversationState`, state serialization, history capping, and profile slot helpers.
- `src/chat_intent.py` adds deterministic intent routing, follow-up detection, clarification, and blocked-topic routing.
- `src/orchestrator.py` preserves `answer(intent, profile, follow_up=None)` and adds `handle_message(message, state=None)`.
- `src/prompts.py` now supports follow-up/history-aware packages, stronger safety policy, and deterministic menu-specific fallback answers.
- `src/ui/copy.py`, `src/ui/state.py`, and `src/ui/view_models.py` split UI copy, state helpers, and display shaping.
- `DESIGN.md`, `design/tokens.json`, and `.streamlit/config.toml` provide design-readiness without React/FastAPI.
- README and ARCHITECTURE are updated for the chat-first implementation.

## Phase Status

| Phase | Status | Evidence |
|---|---|---|
| Phase 0: Baseline and plan acceptance | Complete | Existing tests preserved; current suite collects 109 tests. |
| Phase 1: Conversation domain foundation | Complete | `src/conversation.py`, `src/chat_intent.py`, `tests/test_chat_intent.py`, `tests/test_chat_flow.py`. |
| Phase 2: Orchestrator conversation entry point | Complete | `Orchestrator.handle_message()` tests pass and `answer()` compatibility remains covered. |
| Phase 3: Prompt and answer format | Complete | `tests/test_prompts.py` covers follow-up, history, fallback, and safety. |
| Phase 4: Streamlit chat UI | Complete | `tests/test_app_chat_ui.py` covers chat shell, state init, sidebar save, rerun behavior, and chat submit. |
| Phase 5: Design-ready UI structure | Complete | `DESIGN.md`, `design/tokens.json`, `src/ui/*`, `.streamlit/config.toml`. |
| Phase 6: Docs and final regression | Complete | README and ARCHITECTURE updated; final commands pass; Review Agent P2 fixed. |

## Requirements Mapping

- Existing tool JSON contracts remain unchanged.
- LLM calculation is not allowed; prompts ground answers in tool JSON only.
- Profile is built once and then reused in conversation state.
- Follow-ups reuse `last_intent` and `last_tool_results`.
- Streamlit message append happens only in explicit action paths.
- API-key-free fallback is covered by tests.
- Blocked topics include health, disease, lifespan, accidents, investment returns, admissions, lottery/gambling, and other high-stakes claims.
- Unknown birth time is supported through `birth_time_unknown` and limited interpretation.

## Verification Commands

Required final validation:

```powershell
pytest --collect-only -q
pytest -q
echo '{"birth_date":"1998-03-12","birth_time":"09:00","calendar_type":"solar"}' | node scripts/calculate_saju.mjs
streamlit run app.py
```

Current evidence:

- `pytest --collect-only -q`: 109 tests collected.
- `pytest -q`: 109 passed.
- `echo '{"birth_date":"1998-03-12","birth_time":"09:00","calendar_type":"solar"}' | node scripts/calculate_saju.mjs`: passed with `ok: true`.
- `streamlit run app.py --server.headless true --server.port 8502`: passed, HTTP 200.
- Review Agent completed. One P2 high-stakes routing gap was fixed and covered by `tests/test_chat_intent.py`.

## Manual QA Checklist

- [x] First visit shows chat-first empty state. Covered by `tests/test_app_chat_ui.py`.
- [x] Sidebar profile creation works. Covered by `tests/test_app_chat_ui.py`.
- [x] "How is today's fortune?" works after profile creation. Covered by chat/orchestrator tests.
- [x] "Then lucky color?" reuses the same profile. Covered by profile reuse tests.
- [x] "Why?" uses the previous tool result. Covered by follow-up tests.
- [x] Blocked health/high-stakes questions are redirected safely. Covered by intent/prompt tests.
- [x] API-key-free fallback answer appears when no provider is configured. Covered by prompt tests.
- [x] Unknown birth time is handled as limited interpretation. Covered by saju chart tests.

## Remaining Work

No required work remains in this plan. Residual risk: enabled LLM providers rely on prompt policy rather than a separate post-generation safety classifier.
