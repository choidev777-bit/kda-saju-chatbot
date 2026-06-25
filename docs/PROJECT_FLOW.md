# 프로젝트 작동 흐름

이 문서는 KDA Chatbot이 실제 파일과 코드 기준으로 어떻게 동작하는지 설명한다. 핵심 흐름은 Streamlit UI가 사용자 입력을 받고, `Orchestrator`가 의도를 라우팅한 뒤, deterministic tool JSON만 계산 근거로 삼아 LLM 또는 fallback 답변을 만드는 구조다.

## 전체 구조

```mermaid
flowchart TD
    User["사용자"]
    App["app.py<br/>Streamlit UI"]
    UIState["src/ui/state.py<br/>session_state 관리"]
    UICopy["src/ui/copy.py<br/>라벨/문구/quick actions"]
    ViewModels["src/ui/view_models.py<br/>표시용 요약"]

    Orchestrator["src/orchestrator.py<br/>Orchestrator"]
    Conversation["src/conversation.py<br/>ConversationState/slot/history"]
    Intent["src/chat_intent.py<br/>route_intent"]
    Config["src/config.py<br/>tool 이름/계약/안전 정책"]

    SajuTool["src/tools/saju_chart.py<br/>calculate_saju_chart"]
    NodeHelper["scripts/calculate_saju.mjs<br/>manseryeok-js 호출"]
    FiveTool["src/tools/five_elements.py<br/>analyze_five_elements"]
    MyeongriTool["src/tools/myeongri.py<br/>analyze_myeongri/calculate_iljin"]
    TodayTool["src/tools/today_luck.py<br/>calculate_today_luck"]
    LuckyTool["src/tools/lucky_factors.py<br/>recommend_lucky_factors"]

    Prompts["src/prompts.py<br/>LLM package/fallback 답변"]
    Provider["OpenAI/Gemini<br/>환경변수 있을 때만"]
    Fallback["deterministic fallback<br/>API key 없거나 LLM 실패"]

    User --> App
    App --> UIState
    App --> UICopy
    App --> ViewModels
    App --> Orchestrator

    Orchestrator --> Config
    Orchestrator --> Conversation
    Orchestrator --> Intent
    Orchestrator --> SajuTool
    SajuTool --> NodeHelper
    Orchestrator --> FiveTool
    Orchestrator --> MyeongriTool
    Orchestrator --> TodayTool
    Orchestrator --> LuckyTool
    Orchestrator --> Prompts

    Prompts --> Provider
    Prompts --> Fallback
    Provider --> App
    Fallback --> App
    App --> User
```

## 최초 프로필 저장 흐름

사용자가 sidebar에서 이름, 성별, 생년월일, 출생시간, 양력/음력 정보를 저장하면 `app.py`의 `save_profile()`이 실행된다.

```mermaid
sequenceDiagram
    actor U as 사용자
    participant A as app.py
    participant O as src/orchestrator.py
    participant S as src/tools/saju_chart.py
    participant N as scripts/calculate_saju.mjs
    participant F as src/tools/five_elements.py
    participant M as src/tools/myeongri.py
    participant SS as src/ui/state.py

    U->>A: sidebar 프로필 입력 후 저장
    A->>A: _profile_payload_from_widgets()
    A->>O: build_profile(user_info_json)
    O->>S: calculate_saju_chart_impl(json)
    S->>S: validate_and_normalize()
    S->>N: subprocess로 Node helper 실행
    N-->>S: 사주 팔자 JSON
    S-->>O: {"ok": true, "data": saju_chart}
    O->>F: analyze_five_elements(saju_chart)
    F-->>O: 오행 counts/strong/weak/recommended
    O->>M: analyze_myeongri_impl(profile)
    M-->>O: 십신/지장간/신강신약/용신/신살/대운
    O-->>A: profile result
    A->>SS: sync_profile()
    SS-->>A: session_state.profile/conversation_state 저장
```

프로필 생성에서 반드시 성공해야 하는 도구는 `calculate_saju_chart`다. 오행 또는 명리 해석 도구가 실패하면 앱은 가능한 범위에서 graceful하게 `pending_tools`에 기록한다.

## 일반 채팅 답변 흐름

채팅 입력 또는 quick action은 `process_chat_message()`로 들어간다. 현재 코드에서는 `Orchestrator.handle_message()`가 있으면 그 경로를 우선 사용한다.

```mermaid
flowchart TD
    Input["사용자 채팅 입력<br/>st.chat_input 또는 quick action"]
    Process["app.py<br/>process_chat_message()"]
    DisplayAppend["messages에 user 표시 메시지 추가"]
    Handle["Orchestrator.handle_message(message, state)"]
    ConvLoad["ConversationState.from_dict()"]
    SlotExtract["extract_slots_from_message()<br/>프로필 slot 보강"]
    Route["route_intent()"]

    Blocked{"blocked topic?"}
    HasProfile{"profile 있음?"}
    Missing{"필수 slot 누락?"}
    BuildProfile["build_profile()"]
    Clarify{"clarify?"}
    FollowUp{"follow_up + last_tool_results 있음?"}
    Answer["answer(intent, profile)"]
    RunTools["_run_intent_tools()<br/>필요 tool만 실행"]
    Package["prompts.build_llm_package()"]
    Generate["prompts.generate_answer()"]
    LLM{"API key + LLM 정상?"}
    Fallback["fallback_answer()"]
    Sync["app.py<br/>conversation_state/profile/last results 동기화"]
    Render["assistant 메시지 렌더링"]

    Input --> Process --> DisplayAppend --> Handle --> ConvLoad --> SlotExtract --> Route
    Route --> Blocked
    Blocked -- yes --> Sync --> Render
    Blocked -- no --> HasProfile
    HasProfile -- no --> Missing
    Missing -- yes --> Sync --> Render
    Missing -- no --> BuildProfile --> Clarify
    HasProfile -- yes --> Clarify
    Clarify -- yes --> Sync --> Render
    Clarify -- no --> FollowUp
    FollowUp -- yes --> Package
    FollowUp -- no --> Answer --> RunTools --> Package
    Package --> Generate --> LLM
    LLM -- yes --> Render
    LLM -- no --> Fallback --> Render
    Render --> Sync
```

## 의도 라우팅과 후속 질문

`src/chat_intent.py`는 키워드 기반으로 의도를 정한다. 지원 의도는 `saju_reading`, `today_fortune`, `luck_score`, `lucky_color`, `lucky_item`, `love`, `wealth`, `life_flow`다.

```mermaid
flowchart LR
    Message["message"]
    Route["route_intent(message, state)"]
    Safety["blocked topic 검사<br/>건강/투자/합격/복권 등"]
    Match["intent keyword match"]
    Follow["follow-up/context question 검사"]
    Context["state.last_intent<br/>state.last_tool_results"]

    Message --> Route --> Safety
    Safety -- 감지됨 --> Blocked["RoutedIntent(kind='blocked')"]
    Safety -- 통과 --> Match
    Match -- 새 의도 --> Intent["RoutedIntent(kind='intent', intent=...)"]
    Match -- 없음/동일 --> Follow
    Follow --> Context
    Context -- 있음 --> FollowUp["RoutedIntent(kind='follow_up')"]
    Context -- 없음 --> Clarify["RoutedIntent(kind='clarify')"]
```

후속 질문은 이전 답변의 `last_intent`와 `last_tool_results`를 재사용한다. 그래서 "왜?", "더 자세히", "그 이유는?" 같은 질문에서는 프로필 계산을 다시 하지 않고 기존 tool JSON을 근거로 답변한다.

## 의도별 실행 도구

의도별 필요 도구는 `src/config.py`의 `MENU_REQUIRED_TOOLS`가 정한다. `Orchestrator._run_intent_tools()`는 이 목록을 보고 필요한 도구만 실행하거나 이미 프로필에 있는 결과를 재사용한다.

```mermaid
flowchart TD
    Intent["intent"]
    Required["config.MENU_REQUIRED_TOOLS[intent]"]
    ProfileData["profile.data"]

    FE{"five_elements 필요?"}
    MY{"myeongri 필요?"}
    IL{"iljin 필요?"}
    TODAY{"today_luck 필요?"}
    LUCKY{"lucky_factors 필요?"}

    Results["tool_results"]
    Pending["pending_tools"]

    Intent --> Required
    Required --> FE
    Required --> MY
    Required --> IL
    Required --> TODAY
    Required --> LUCKY

    ProfileData --> FE
    FE -- 있음 --> Results
    FE -- 없음/실패 --> Pending

    ProfileData --> MY
    MY -- 있음 --> Results
    MY -- 없음/실패 --> Pending

    IL -- calculate_iljin_impl(profile) 성공 --> Results
    IL -- 실패 --> Pending

    TODAY -- calculate_today_luck(profile) 성공 --> Results
    TODAY -- 실패/오행 없음 --> Pending

    LUCKY -- recommend_lucky_factors(five_elements) 성공 --> Results
    LUCKY -- 실패/오행 없음 --> Pending
```

## 답변 생성 흐름

`src/prompts.py`는 계산을 하지 않는다. `profile.saju_chart`, `profile.five_elements`, `tool_result`만 계산 근거로 패키징하고, 환경변수에 따라 LLM 또는 fallback을 선택한다.

```mermaid
sequenceDiagram
    participant O as Orchestrator
    participant P as src/prompts.py
    participant L as LLM Provider
    participant F as fallback_answer()
    participant A as app.py

    O->>P: build_llm_package(intent, profile_data, tool_results)
    P-->>O: package
    A->>P: generate_answer(package, follow_up, history)
    P->>P: _select_provider()
    alt OPENAI_API_KEY 또는 GOOGLE_API_KEY 있고 호출 성공
        P->>L: SystemMessage + HumanMessage
        L-->>P: answer text
        P-->>A: {"mode": "llm", "text": "..."}
    else API key 없음 또는 호출 실패
        P->>F: fallback_answer(package)
        F-->>P: deterministic text
        P-->>A: {"mode": "fallback", "text": "..."}
    end
```

## 파일별 책임 요약

| 파일 | 책임 |
| --- | --- |
| `app.py` | Streamlit 진입점. sidebar 프로필 입력, quick action, chat input, session_state 동기화, 답변 렌더링을 담당한다. |
| `src/orchestrator.py` | 앱의 중심 조정자. 프로필 생성, 자연어 채팅 처리, 의도별 tool 실행, LLM package 생성을 연결한다. |
| `src/conversation.py` | UI와 독립적인 대화 상태 모델. 메시지 history, slot 추출, 누락 slot 검사, 직렬화를 담당한다. |
| `src/chat_intent.py` | 안전 차단, 의도 라우팅, 후속 질문 감지를 담당한다. |
| `src/config.py` | 공통 JSON 계약, 에러 코드, tool 이름, 의도별 필요 도구, 안전 정책 상수를 담는다. |
| `src/prompts.py` | LLM 입력 패키지, system/user prompt, provider 선택, deterministic fallback 답변을 담당한다. |
| `src/tools/saju_chart.py` | 입력 검증 후 Node helper를 subprocess로 호출해 사주 팔자를 계산한다. |
| `scripts/calculate_saju.mjs` | `@fullstackfamily/manseryeok`를 사용해 양력/음력 변환과 사주 팔자 계산을 수행한다. |
| `src/tools/five_elements.py` | 사주 팔자에서 오행 개수, 강한 오행, 약한 오행, 보완 오행을 계산한다. |
| `src/tools/myeongri.py` | 십신, 지장간, 신강/신약, 용신 근사, 신살, 대운, 일진을 계산한다. |
| `src/tools/today_luck.py` | 프로필과 오행 분석을 바탕으로 오늘의 운 점수와 신호를 계산한다. |
| `src/tools/lucky_factors.py` | 보완 오행을 기준으로 lucky color/item 추천 JSON을 만든다. |
| `src/ui/state.py` | Streamlit `session_state` key와 안전한 mutation helper를 제공한다. |
| `src/ui/copy.py` | UI 라벨, 안내문, quick action 문구를 제공한다. |
| `src/ui/view_models.py` | profile summary, pending tool 표시 등 UI 표시용 데이터를 만든다. |

## 상태 저장 모델

```mermaid
classDiagram
    class StreamlitSessionState {
        messages
        profile
        conversation_state
        last_intent
        last_tool_results
        profile_ready_message_added
    }

    class ConversationState {
        profile
        user_slots
        message_history
        last_intent
        last_tool_results
        pending_slots
        pending_tools
        history_limit
        to_dict()
        from_dict()
    }

    StreamlitSessionState --> ConversationState : stores serialized dict
```

`app.py`의 화면용 `messages`와 `ConversationState.message_history`는 목적이 다르다. `messages`는 Streamlit 렌더링용이고, `message_history`는 후속 질문 문맥용이다.

## 안전 경계

```mermaid
flowchart TD
    UserMessage["사용자 질문"]
    IntentRouter["route_intent()"]
    BlockList["blocked topic<br/>건강/질병/수명/사고/투자수익/합격/복권/법률 등"]
    ToolExecution["tool 실행"]
    SafeRedirect["안전한 자기성찰 안내"]
    LlmPackage["tool JSON 기반 LLM package"]

    UserMessage --> IntentRouter --> BlockList
    BlockList -- 해당 --> SafeRedirect
    BlockList -- 비해당 --> ToolExecution --> LlmPackage
```

금지 주제는 tool 실행 전에 차단된다. LLM도 계산 근거를 만들지 않으며, tool JSON에 없는 정보를 추측하지 않도록 prompt와 fallback 양쪽에서 제한한다.

## 검증 포인트

이 흐름을 수정했다면 최소한 아래 명령을 확인한다.

```powershell
pytest --collect-only -q
pytest -q
echo '{"birth_date":"1998-03-12","birth_time":"09:00","calendar_type":"solar"}' | node scripts/calculate_saju.mjs
```

Streamlit UI까지 확인해야 하는 변경이라면 다음 명령으로 앱을 띄운다.

```powershell
streamlit run app.py
```
