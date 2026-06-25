# KDA Chatbot

KDA Chatbot is a Streamlit chat app for saju-based self-reflection. The user saves birth information once, then asks natural follow-up questions in a chat window.

The app keeps calculation and interpretation separate:

- Deterministic tools calculate the saju chart, five elements, today's luck score, and lucky factors.
- The LLM, when configured, only interprets structured tool JSON.
- If no API key is configured, deterministic fallback answers still work.

This is an entertainment and self-reflection tool. It must not be used for medical, legal, financial, admissions, lottery, gambling, accident, lifespan, or other high-stakes decisions.

## Current UX

1. Run the Streamlit app.
2. Save a profile in the sidebar.
3. Use the main chat area to ask questions.
4. Use quick actions for common topics:
   - saju reading
   - today fortune
   - luck score
   - lucky color
   - lucky item
   - relationships
   - money habits
   - life flow
5. Ask follow-ups such as "why?" or "what is the reason?" to reuse the previous tool result.

The app uses `st.chat_message` and `st.chat_input` for the main conversation. The sidebar owns structured profile onboarding, profile summary, reset, and optional debug details.

## Example Prompts

```text
How is today's fortune?
What is my lucky color?
Then what lucky item should I use?
Why did you say that?
Tell me about relationship luck.
What should I watch in money habits?
```

Blocked or high-stakes prompts, such as health predictions or investment returns, are redirected to safer self-reflection framing.

## Requirements

- Python 3.10+
- Node.js 16+
- npm dependencies from `package.json`
- Python dependencies from `requirements.txt`

## Setup

```powershell
npm install
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Optional LLM configuration:

```powershell
copy .env.example .env
```

Set one of:

- `OPENAI_API_KEY`
- `GOOGLE_API_KEY`

If no API key is present, the app falls back to deterministic tool-based responses.

## Run

```powershell
streamlit run app.py
```

## Deploy to Render with Docker

This repository includes `Dockerfile` and `render.yaml` for Render Web Service deployment.

1. Push the repository to GitHub.
2. In Render, create a new Blueprint or Web Service from the GitHub repository.
3. Select the `main` branch.
4. Use Docker runtime. The container starts Streamlit on Render's `$PORT`.
5. Add secrets in Render Environment Variables:
   - `OPENAI_API_KEY` for OpenAI-backed interpretation
   - or `GOOGLE_API_KEY` if Gemini support is enabled

If no API key is configured, the app still runs with deterministic fallback answers.

## Test

```powershell
pytest --collect-only -q
pytest -q
```

Node helper smoke test:

```powershell
echo '{"birth_date":"1998-03-12","birth_time":"09:00","calendar_type":"solar"}' | node scripts/calculate_saju.mjs
```

## Project Structure

```text
app.py                         Streamlit chat-first entrypoint
src/config.py                  shared constants, tool contracts, safety lists
src/conversation.py            ConversationState and slot/history helpers
src/chat_intent.py             deterministic intent router
src/orchestrator.py            profile build, menu answer, handle_message chat flow
src/prompts.py                 LLM prompts and deterministic fallback answers
src/tools/saju_chart.py        LangChain saju chart tool via Node helper
src/tools/five_elements.py     LangChain five-elements tool
src/tools/today_luck.py        LangChain today-luck tool
src/tools/lucky_factors.py     LangChain lucky-factor tool
src/ui/copy.py                 UI labels, quick actions, safety copy
src/ui/state.py                Streamlit session-state helpers
src/ui/view_models.py          display shaping helpers
design/tokens.json             design token seed
DESIGN.md                      design-readiness guide
tests/                         regression, chat flow, prompt, and UI tests
```

## Safety Notes

- Tools are the only source of calculation truth.
- The LLM must not invent missing saju data.
- Conversation history is context only, not a calculation source.
- `.env` is ignored and must not be committed.
- Debug JSON is optional and local to the Streamlit session.

