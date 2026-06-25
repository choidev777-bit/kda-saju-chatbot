# Design Readiness

## Product Context

KDA Chatbot is a Streamlit-first saju self-reflection chat. The product should feel quiet, practical, and conversational: users save structured birth data once, then ask natural questions about a deterministic tool result. The app is not a medical, legal, financial, admissions, lottery, gambling, accident, or lifespan prediction tool.

## Design Goals

- Keep the first screen focused on the chat task, not a marketing page.
- Make profile setup reliable and easy to correct from the sidebar.
- Treat calculation tools as the only source of saju facts.
- Make refusal and redirect copy calm, brief, and consistent.
- Keep the UI layer thin enough that a later visual redesign can reuse state, copy, and view-model contracts.

## Chat UX Principles

- Lead with conversation. The main surface is chat history, quick actions, and chat input.
- Keep onboarding structured. Birth data is collected in form controls so the app does not depend on brittle text parsing.
- Preserve context without overclaiming. Follow-up answers can reference recent turns, but calculations still come from tool output.
- Stay rerun-safe. User and assistant turns append only inside explicit callbacks or submitted chat input handling.
- Keep debug details optional. JSON state is useful for demos and QA, but it should remain behind a deliberate debug toggle.

## Tone And Safety

The voice is warm, plain, and grounded. It may frame results as patterns, reflections, tendencies, or prompts for thought. It should not present certainty, diagnosis, investment direction, admissions outcomes, lottery/gambling odds, accident warnings, lifespan claims, or other high-stakes predictions.

Safety redirects should:

- State the boundary in one sentence.
- Offer a safer self-reflection framing.
- Avoid partially answering the blocked request.
- Avoid adding new warnings that imply a hidden calculation.

Stable copy belongs in `src/ui/copy.py` so wording can be reviewed without touching Streamlit composition.

## Component Inventory

- App header: product title, concise description, safety disclaimer.
- Sidebar profile form: name, gender, calendar, birth date, birth time, unknown-time toggle, leap-month toggle, save action.
- Profile summary: ready state, display name, saju pillars, element counts, pending tool notice.
- Quick actions: saju reading, today, luck score, lucky color, lucky item, relationships, money habits, life flow.
- Chat history: assistant/user turns rendered through Streamlit chat primitives.
- Chat input: one primary free-form prompt entry.
- Empty/profile-needed state: friendly assistant guidance that points to the sidebar.
- Debug panel: profile, conversation state, last intent, last tool results.

## Token Strategy

Design tokens live in `design/tokens.json`. The token file keeps three levels:

- `color`, `spacing`, `radius`, and `typography` preserve the current simple keys for existing code.
- `semantic` names describe UI intent such as page background, text, action, warning, and danger.
- `component` names describe expected Streamlit surfaces such as page, sidebar, chat, quick action, profile summary, and debug panel.

The palette should avoid feeling mystical or decorative. Use a soft neutral page background, white surfaces, teal for primary actions, rust for warmth, blue for informational states, and restrained status colors for success/warning/danger.

## UI Helper Contracts

`src/ui/copy.py` owns labels, button text, helper text, warnings, quick-action prompts, and safety redirects.

`src/ui/state.py` owns Streamlit session-state key names and safe mutations:

- initialize messages and conversation state
- append chat turns with a bounded serialized history
- sync a saved profile into the conversation state
- sync last intent and last tool results after an answer
- reset only UI conversation keys

`src/ui/view_models.py` owns display shaping:

- profile readiness and compact summary rows
- element count text
- pending tool labels
- lightweight tool-result status summaries
- debug payload shaping

Domain constants and tool contracts stay in `src/config.py`. Streamlit composition stays in `app.py` until a later UI extraction is explicitly approved.

## Future Split Guidance

A later interface or service split should keep the current contracts stable before moving screens:

- `messages`
- `profile`
- `conversation_state`
- `last_intent`
- `last_tool_results`
- quick action triplets: intent, label, prompt
- profile summary view model

Any future UI should preserve the same interaction model: structured profile setup, chat-first questions, quick actions, optional debug visibility, and deterministic tool results as the only calculation source.
