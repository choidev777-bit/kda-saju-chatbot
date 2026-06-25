# 사주 기반 자기성찰 챗봇

사용자의 생년월일·출생시간·양력/음력 정보를 받아 **만세력과 오행을 계산**하고,
계산된 JSON 결과를 **LLM이 자연어로 해석**해 사주풀이·오늘의 운세·행운 점수·
행운 색깔/아이템·연애운·재물운·인생흐름을 제공하는 챗봇입니다.

핵심 원칙: **사주 계산은 LLM이 직접 하지 않습니다.** 계산은 LangChain `@tool`로
등록된 결정적(deterministic) 도구가 담당하고, LLM은 그 결과만 해석합니다. (환각 방지)
건강운은 의료적 오해를 줄이기 위해 제외합니다.

> 본 서비스는 전통 명리학 요소를 활용한 엔터테인먼트 및 자기성찰용 챗봇입니다.
> 의학, 법률, 금융 등 중요한 의사결정의 근거로 사용하지 마세요.

---

## 기술 스택

| 구분 | 내용 |
|---|---|
| 언어 | Python 3.10+ |
| UI | Streamlit |
| LLM 오케스트레이션 | LangChain (`@tool`) |
| LLM API | OpenAI 또는 Gemini (선택, 키 없으면 기본 답변으로 동작) |
| 만세력 계산 | [`@fullstackfamily/manseryeok`](https://github.com/urstory/manseryeok-js) (npm, DB 불필요, 1900~2050) |
| 연동 구조 | Python `@tool` → Node helper(`scripts/calculate_saju.mjs`) → manseryeok |
| 환경 변수 | `python-dotenv` |
| 테스트 | pytest |

---

## 사전 준비물

- **Node.js 16+** (만세력 계산 라이브러리가 JavaScript이므로 필요)
- **Python 3.10+**

설치 여부 확인:

```bash
node --version
python --version
```

---

## 설치 및 실행

### 1) 만세력 라이브러리 설치 (Node)

```bash
npm install
```

> 이 명령은 `package.json`에 적힌 `@fullstackfamily/manseryeok`를 설치합니다.
> GitHub ZIP을 직접 내려받지 않습니다.

### 2) Python 가상환경 + 의존성 설치

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3) (선택) LLM API 키 설정

```bash
cp .env.example .env     # Windows: copy .env.example .env
```

`.env`를 열어 `OPENAI_API_KEY` 또는 `GOOGLE_API_KEY` 중 하나를 채웁니다.
**키가 없어도 앱은 동작합니다** — 이 경우 tool 계산 결과 기반의 기본 답변이 표시됩니다.

### 4) 앱 실행

```bash
streamlit run app.py
```

브라우저에서 기본 정보를 입력하고 메뉴를 선택하면 해석이 표시됩니다.

---

## 테스트

```bash
pytest
```

- `tests/test_input_utils.py` — 입력 검증
- `tests/test_saju_chart.py` — 만세력 계산 tool (실제 Node helper 호출)
- `tests/test_orchestrator.py` — 통합 흐름 (팀원 도구는 계약 기반 테스트 더블로 대역)

> 테스트는 Node.js와 `npm install`이 완료되어 있어야 통과합니다.

만세력 Node helper만 단독 확인:

```bash
echo '{"birth_date":"1998-03-12","birth_time":"09:00","calendar_type":"solar"}' | node scripts/calculate_saju.mjs
```

---

## 프로젝트 구조

```text
kda-chatbot/
├─ app.py                      # Streamlit UI (통합)
├─ package.json                # manseryeok 의존성
├─ requirements.txt            # Python 의존성
├─ .env.example                # 환경 변수 예시
├─ scripts/
│  └─ calculate_saju.mjs       # Node helper (manseryeok 호출)
├─ src/
│  ├─ config.py                # 공통 상수, 응답 형식, 데이터 계약
│  ├─ input_utils.py           # 입력 검증 공통 유틸
│  ├─ prompts.py               # LLM 시스템 프롬프트 + 답변 생성(+fallback)
│  ├─ orchestrator.py          # 프로필 생성 + 메뉴별 tool 라우팅
│  └─ tools/
│     └─ saju_chart.py         # ① calculate_saju_chart (@tool)
└─ tests/
```

---

## 4개의 LangChain `@tool` 과 팀원 분담

| 도구 | 담당 | 상태 | 파일 |
|---|---|---|---|
| `calculate_saju_chart` (만세력) | 최연준 | ✅ 구현 + 통합 리드 | `src/tools/saju_chart.py` |
| `analyze_five_elements` (오행) | 이윤서 | ⏳ 예정 | `src/tools/five_elements.py` |
| `calculate_today_luck` (오늘 운세) | 최호택 | ⏳ 예정 | `src/tools/today_luck.py` |
| `recommend_lucky_factors` (행운) | 전원정 | ⏳ 예정 | `src/tools/lucky_factors.py` |

**통합 설계(최연준):** `orchestrator`는 팀원 도구가 아직 없어도 깨지지 않습니다.
각 도구 파일이 추가되면 **자동으로 인식**되어 활성화되고, 없으면 해당 기능을
"팀원 도구 연결 후 활성화" 상태(pending)로 안전하게 표시합니다.

팀원 도구가 따르면 좋은 연동 규약:
- 모듈에 `<함수명>_impl(json_str) -> json_str` 순수 함수를 함께 제공하면 가장 매끄럽게 연동됩니다.
- 모든 도구는 JSON 문자열을 입출력하고, 성공은 `{"ok": true, "data": ...}`,
  실패는 `{"ok": false, "error": {"code", "message"}}` 형식을 따릅니다.
- 오행 결과는 `counts` 중첩 형태(`{"counts": {"wood": ...}, "strong_element": ...}`)로 통일합니다.

---

## 데이터 계약 (만세력 tool)

입력(JSON 문자열):

```json
{
  "name": "민지",
  "gender": "female",
  "birth_date": "1998-03-12",
  "birth_time": "09:00",
  "calendar_type": "solar",
  "birth_time_unknown": false,
  "is_leap_month": false
}
```

성공 출력:

```json
{
  "ok": true,
  "data": {
    "year_pillar": "무인",
    "month_pillar": "을묘",
    "day_pillar": "무오",
    "hour_pillar": "병진",
    "time_precision": "known",
    "calendar_type": "solar",
    "source": "manseryeok-js (@fullstackfamily/manseryeok)"
  }
}
```

- 출생시간 미상이면 `hour_pillar`는 `null`, `time_precision`은 `"unknown"`.
- 실패 시 `{"ok": false, "error": {"code": "...", "message": "..."}}`.

---

## 안전 설계

- 건강·질병·수명·사고·투자수익·합격·당첨 등은 단정하지 않습니다.
- LLM 프롬프트에 "tool 결과 JSON만 근거로 해석" 규칙을 명시합니다.
- API 키는 `.env`에만 두고 GitHub에 올리지 않습니다(`.gitignore` 처리).
