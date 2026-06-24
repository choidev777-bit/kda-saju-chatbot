# 사주 챗봇 전체 구현 계획서

Last Updated: 2026-06-24

**CRITICAL INSTRUCTIONS**: 각 단계 완료 후 아래를 확인한다.
1. 완료한 작업 체크박스를 갱신한다.
2. 해당 단계의 검증 명령 또는 수동 검증을 실행한다.
3. 품질 게이트 항목이 모두 통과했는지 확인한다.
4. "Last Updated" 날짜를 갱신한다.
5. 새로 배운 점이나 이슈는 "Notes & Learnings"에 기록한다.
6. 실패한 검증이 있으면 다음 단계로 넘어가지 않는다.

## 1. 프로젝트 개요

이 프로젝트는 사용자의 이름, 성별, 생년월일, 출생시간, 양력/음력 여부를 입력받아 사주 기반 자기성찰 답변을 제공하는 챗봇이다. 챗봇은 LangChain의 `@tool` 데코레이터로 정의한 계산/분석 tool을 사용하고, LLM은 tool 결과를 바탕으로 자연어 해석만 담당한다.

주요 기능은 다음과 같다.

- 사주풀이
- 오늘의 행운 점수
- 오늘의 운세
- 행운 색깔
- 행운 아이템
- 연애운
- 재물운
- 인생흐름

건강운은 의료적 오해를 줄이기 위해 제외한다.

## 2. 구현 목표

### 필수 목표

- [ ] Streamlit 또는 Gradio 기반 챗봇 UI 구현
- [ ] LangChain `@tool` 기반 tool 4개 이상 구현
- [ ] 팀원 4명이 각각 최소 1개의 tool 담당
- [ ] 사주 계산 결과를 LLM에 구조화된 JSON으로 전달
- [ ] LLM이 계산을 직접 하지 않고 tool 결과만 해석하도록 제한
- [ ] PRD 파일 작성
- [ ] GitHub 저장소 제출
- [ ] 기술 스택 목록 제출

### 발표 목표

- [ ] 사용자 입력부터 최종 답변까지 전체 흐름 시연
- [ ] 각 팀원이 맡은 tool의 역할 설명
- [ ] `@tool` 코드 예시 설명
- [ ] LLM 환각 방지 구조 설명
- [ ] 건강운 제외 이유 설명

## 3. 기술 스택

| 구분 | 선택안 |
|---|---|
| UI 프레임워크 | Streamlit 권장, Gradio도 가능 |
| 언어 | Python |
| LLM 연결 | LangChain |
| Tool 구현 | LangChain `@tool` |
| LLM API | OpenAI API 또는 Gemini API |
| 만세력 계산 | MVP: 간단 계산/어댑터, 확장: `manseryeok-js` 또는 공공데이터 API |
| 저장 | MVP: session state, 확장: SQLite 또는 JSON |
| 환경 변수 | `python-dotenv` |
| 테스트 | pytest |
| 배포 | Streamlit Community Cloud 또는 Hugging Face Spaces |
| 개발 도구 | VS Code, GitHub, ChatGPT/Codex |

## 4. 팀원 역할 분담

| 팀원 | 담당 영역 | 필수 산출물 |
|---|---|---|
| 최연준 | Tool 1. 만세력 계산 tool, 전체 통합 리드 | `calculate_saju_chart` 구현, tool 결과 JSON 정의 |
| 이윤서 | Tool 2. 오행 분석 tool | `analyze_five_elements` 구현, 오행 매핑 테이블 작성 |
| 최호택 | Tool 3. 오늘 운세 점수 tool | `calculate_today_luck` 구현, 점수 계산 규칙 작성 |
| 전원정 | Tool 4. 행운 색깔/아이템 추천 tool | `recommend_lucky_factors` 구현, 색깔/아이템 추천 규칙 작성 |

공동 작업:

- UI 연결
- LLM 프롬프트 작성
- PRD 작성
- README 정리
- 발표 자료 준비
- 최종 QA

## 5. 필수 Tool 정의

### Tool 1. 만세력 계산 tool

담당: 최연준

```python
from langchain.tools import tool

@tool
def calculate_saju_chart(user_info_json: str) -> str:
    """사용자의 생년월일, 출생시간, 양력/음력 정보를 바탕으로 사주팔자를 계산한다."""
    ...
```

입력:

```json
{
  "name": "민지",
  "gender": "female",
  "birth_date": "1998-03-12",
  "birth_time": "09:00",
  "calendar_type": "solar",
  "birth_time_unknown": false
}
```

출력:

```json
{
  "year_pillar": "무인",
  "month_pillar": "을묘",
  "day_pillar": "예시",
  "hour_pillar": "예시",
  "time_precision": "known"
}
```

완료 기준:

- [ ] 입력 JSON을 받아 사주팔자 JSON을 반환한다.
- [ ] 출생시간 미상일 때 `time_precision: "unknown"`을 반환한다.
- [ ] 계산 실패 시 에러 메시지를 구조화해서 반환한다.

### Tool 2. 오행 분석 tool

담당: 이윤서

```python
@tool
def analyze_five_elements(saju_chart_json: str) -> str:
    """사주팔자 데이터를 바탕으로 목, 화, 토, 금, 수 오행의 강약을 분석한다."""
    ...
```

출력:

```json
{
  "wood": 3,
  "fire": 1,
  "earth": 2,
  "metal": 1,
  "water": 1,
  "strong_element": "wood",
  "weak_element": "water",
  "recommended_element": "water"
}
```

완료 기준:

- [ ] 천간/지지와 오행 매핑 테이블을 만든다.
- [ ] 사주팔자에서 오행 개수를 계산한다.
- [ ] 강한 오행, 약한 오행, 보완 오행을 반환한다.

### Tool 3. 오늘 운세 점수 tool

담당: 최호택

```python
@tool
def calculate_today_luck(profile_json: str) -> str:
    """사용자 사주 프로필과 오늘 날짜의 기운을 비교해 오늘의 행운 점수를 계산한다."""
    ...
```

출력:

```json
{
  "date": "2026-06-24",
  "score": 82,
  "score_range": "0-100",
  "today_element": "water",
  "signals": [
    "오늘의 기운이 부족한 수 기운을 보완합니다."
  ],
  "cautions": [
    "중요한 결정을 서두르기보다 한 번 더 확인하는 편이 좋습니다."
  ]
}
```

완료 기준:

- [ ] 점수는 항상 0~100 사이로 제한한다.
- [ ] 기본 점수와 가산/감산 규칙을 문서화한다.
- [ ] 점수 근거를 `signals`와 `cautions`로 반환한다.

### Tool 4. 행운 색깔/아이템 추천 tool

담당: 전원정

```python
@tool
def recommend_lucky_factors(element_analysis_json: str) -> str:
    """보완 오행을 기준으로 행운 색깔과 행운 아이템을 추천한다."""
    ...
```

출력:

```json
{
  "recommended_element": "water",
  "lucky_colors": ["파란색", "남색", "검정"],
  "lucky_items": ["물병", "향수", "이어폰"],
  "reason": "수 기운은 차분함과 정리를 상징하므로 오늘의 보완 요소로 추천합니다."
}
```

완료 기준:

- [ ] 오행별 색깔 매핑을 구현한다.
- [ ] 오행별 아이템 매핑을 구현한다.
- [ ] 추천 이유를 함께 반환한다.

## 6. 시스템 구조

```text
사용자 입력
↓
입력 검증 유틸
↓
Tool 1. 만세력 계산
↓
Tool 2. 오행 분석
↓
사용자 사주 프로필 저장
↓
사용자 메뉴 선택
↓
필요한 tool만 추가 실행
↓
LLM 해석
↓
챗봇 답변 출력
```

핵심 설계:

- 입력 검증은 별도 tool이 아니라 공통 유틸 함수로 구현한다.
- 최초 1회 사주 프로필을 만들고 세션에 저장한다.
- 사용자의 질문에 따라 필요한 tool만 실행한다.
- LLM에는 생년월일 원본만 던지지 않고, tool 결과 JSON을 전달한다.

## 7. 프로젝트 파일 구조 제안

```text
kda-chatbot/
├─ app.py
├─ requirements.txt
├─ .env.example
├─ README.md
├─ PRD.md
├─ ARCHITECTURE.md
├─ docs/
│  └─ plans/
│     └─ PLAN_saju-chatbot.md
├─ src/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ input_utils.py
│  ├─ prompts.py
│  ├─ orchestrator.py
│  ├─ tools/
│  │  ├─ __init__.py
│  │  ├─ saju_chart.py
│  │  ├─ five_elements.py
│  │  ├─ today_luck.py
│  │  └─ lucky_factors.py
│  └─ storage.py
└─ tests/
   ├─ test_input_utils.py
   ├─ test_saju_chart.py
   ├─ test_five_elements.py
   ├─ test_today_luck.py
   └─ test_lucky_factors.py
```

## 8. 단계별 구현 계획

### Phase 1. 프로젝트 기본 구조 세팅

예상 소요: 1~2시간

목표: 실행 가능한 Streamlit/Gradio 기본 앱과 개발 환경을 만든다.

RED Tasks:

- [ ] `tests/test_input_utils.py`에 입력 검증 테스트 케이스를 작성한다.
- [ ] 잘못된 날짜, 출생시간 미상, 양력/음력 누락 테스트를 작성한다.

GREEN Tasks:

- [ ] `requirements.txt`를 작성한다.
- [ ] `app.py` 기본 화면을 만든다.
- [ ] `src/input_utils.py`를 만든다.
- [ ] `.env.example`을 만든다.

REFACTOR Tasks:

- [ ] 입력 필드 이름과 JSON schema를 `ARCHITECTURE.md`와 맞춘다.
- [ ] 공통 상수와 설정값을 `src/config.py`로 분리한다.

Quality Gate:

- [ ] 앱이 로컬에서 실행된다.
- [ ] 입력 검증 테스트가 통과한다.
- [ ] 잘못된 입력에서 사용자에게 재입력 안내가 나온다.

검증 명령:

```bash
pytest tests/test_input_utils.py
streamlit run app.py
```

Rollback:

- `app.py`, `src/input_utils.py`, `src/config.py`, `requirements.txt` 변경분을 되돌린다.

### Phase 2. Tool 1 만세력 계산 구현

예상 소요: 2~4시간

담당: 최연준

목표: 사용자 입력을 받아 사주팔자 JSON을 반환하는 `@tool`을 만든다.

RED Tasks:

- [ ] `tests/test_saju_chart.py`에 정상 입력 테스트를 작성한다.
- [ ] 출생시간 미상 테스트를 작성한다.
- [ ] 지원 범위 밖 날짜 테스트를 작성한다.

GREEN Tasks:

- [ ] `src/tools/saju_chart.py`를 만든다.
- [ ] `calculate_saju_chart`에 `@tool`을 붙인다.
- [ ] MVP 계산 로직 또는 만세력 어댑터를 연결한다.
- [ ] 결과 JSON에 `year_pillar`, `month_pillar`, `day_pillar`, `hour_pillar`를 포함한다.

REFACTOR Tasks:

- [ ] 계산 소스를 나중에 교체할 수 있도록 어댑터 함수로 감싼다.
- [ ] 에러 응답 형식을 통일한다.

Quality Gate:

- [ ] tool 함수가 LangChain tool로 등록된다.
- [ ] 같은 입력에 대해 같은 결과를 반환한다.
- [ ] 출생시간 미상 처리가 깨지지 않는다.

검증 명령:

```bash
pytest tests/test_saju_chart.py
```

Rollback:

- `src/tools/saju_chart.py`와 관련 테스트만 되돌린다.

### Phase 3. Tool 2 오행 분석 구현

예상 소요: 2~3시간

담당: 이윤서

목표: 사주팔자를 받아 오행 비율과 보완 오행을 계산한다.

RED Tasks:

- [ ] `tests/test_five_elements.py`에 천간/지지 매핑 테스트를 작성한다.
- [ ] 오행 개수 합산 테스트를 작성한다.
- [ ] 강한 오행과 약한 오행 판단 테스트를 작성한다.

GREEN Tasks:

- [ ] `src/tools/five_elements.py`를 만든다.
- [ ] `analyze_five_elements`에 `@tool`을 붙인다.
- [ ] 천간/지지 오행 매핑 테이블을 구현한다.
- [ ] `strong_element`, `weak_element`, `recommended_element`를 반환한다.

REFACTOR Tasks:

- [ ] 매핑 테이블을 읽기 쉽게 정리한다.
- [ ] 동률 처리 규칙을 명확히 한다.

Quality Gate:

- [ ] 오행 개수가 누락 없이 계산된다.
- [ ] 반환 JSON schema가 문서와 일치한다.
- [ ] 동률 상황에서도 결과가 안정적으로 나온다.

검증 명령:

```bash
pytest tests/test_five_elements.py
```

Rollback:

- `src/tools/five_elements.py`와 관련 테스트만 되돌린다.

### Phase 4. Tool 3 오늘 운세 점수 구현

예상 소요: 2~3시간

담당: 최호택

목표: 사용자 사주 프로필과 오늘 날짜를 비교해 0~100점 사이의 행운 점수를 계산한다.

RED Tasks:

- [ ] `tests/test_today_luck.py`에 점수 범위 테스트를 작성한다.
- [ ] 보완 오행이 오늘 오행과 맞을 때 가산되는 테스트를 작성한다.
- [ ] 결과에 `signals`와 `cautions`가 포함되는지 테스트한다.

GREEN Tasks:

- [ ] `src/tools/today_luck.py`를 만든다.
- [ ] `calculate_today_luck`에 `@tool`을 붙인다.
- [ ] 기본 점수, 가산점, 감산점 규칙을 구현한다.
- [ ] 오늘 날짜 기준 결과를 반환한다.

REFACTOR Tasks:

- [ ] 점수 계산 규칙을 상수로 분리한다.
- [ ] 과도하게 단정적인 문구를 제거한다.

Quality Gate:

- [ ] 점수가 0보다 작거나 100보다 커지지 않는다.
- [ ] 점수 근거가 함께 반환된다.
- [ ] 날짜가 바뀌어도 함수가 실패하지 않는다.

검증 명령:

```bash
pytest tests/test_today_luck.py
```

Rollback:

- `src/tools/today_luck.py`와 관련 테스트만 되돌린다.

### Phase 5. Tool 4 행운 색깔/아이템 추천 구현

예상 소요: 1~2시간

담당: 전원정

목표: 보완 오행에 따라 행운 색깔과 행운 아이템을 추천한다.

RED Tasks:

- [ ] `tests/test_lucky_factors.py`에 오행별 색깔 추천 테스트를 작성한다.
- [ ] 오행별 아이템 추천 테스트를 작성한다.
- [ ] 알 수 없는 오행이 들어왔을 때 기본값 반환 테스트를 작성한다.

GREEN Tasks:

- [ ] `src/tools/lucky_factors.py`를 만든다.
- [ ] `recommend_lucky_factors`에 `@tool`을 붙인다.
- [ ] 오행별 색깔 매핑을 구현한다.
- [ ] 오행별 아이템 매핑을 구현한다.

REFACTOR Tasks:

- [ ] 추천 문구를 발표용으로 읽기 쉽게 다듬는다.
- [ ] 색깔/아이템 리스트가 너무 길지 않게 정리한다.

Quality Gate:

- [ ] 모든 오행에 대해 추천값이 반환된다.
- [ ] 추천 이유가 포함된다.
- [ ] 반환 JSON schema가 문서와 일치한다.

검증 명령:

```bash
pytest tests/test_lucky_factors.py
```

Rollback:

- `src/tools/lucky_factors.py`와 관련 테스트만 되돌린다.

### Phase 6. LLM 해석 및 Orchestrator 연결

예상 소요: 2~4시간

목표: 사용자의 메뉴 선택에 따라 필요한 tool만 실행하고, LLM이 결과를 자연어로 해석하게 만든다.

담당: 공동, 최연준 통합

RED Tasks:

- [ ] `tests/test_orchestrator.py`에 메뉴별 tool 호출 테스트를 작성한다.
- [ ] 사주풀이 요청 시 오늘 운세 tool이 호출되지 않는지 테스트한다.
- [ ] 오늘 운세 요청 시 점수와 행운 추천이 포함되는지 테스트한다.

GREEN Tasks:

- [ ] `src/orchestrator.py`를 만든다.
- [ ] 메뉴별 tool 호출 흐름을 구현한다.
- [ ] `src/prompts.py`에 LLM 시스템 프롬프트를 작성한다.
- [ ] Streamlit/Gradio UI와 연결한다.

REFACTOR Tasks:

- [ ] LLM에 전달되는 JSON schema를 한 곳에서 관리한다.
- [ ] 프롬프트에서 금지 표현과 안전 문구를 정리한다.

Quality Gate:

- [ ] LLM이 사주 계산을 직접 하지 않도록 프롬프트가 제한한다.
- [ ] 없는 정보를 지어내지 않도록 지시한다.
- [ ] 건강, 질병, 수명, 투자 수익 관련 단정 문구가 나오지 않는다.

검증 명령:

```bash
pytest tests/test_orchestrator.py
streamlit run app.py
```

Rollback:

- `src/orchestrator.py`, `src/prompts.py`, `app.py`의 통합 변경분을 되돌린다.

### Phase 7. 산출물, 발표, 배포 준비

예상 소요: 2~4시간

목표: 과제 제출에 필요한 문서, GitHub, 기술 스택, 발표 시나리오를 완성한다.

Tasks:

- [ ] `PRD.md`를 작성한다.
- [ ] `README.md`를 작성한다.
- [ ] `requirements.txt`를 최종 정리한다.
- [ ] `.env.example`에 필요한 환경 변수 이름을 정리한다.
- [ ] GitHub 저장소를 만든다.
- [ ] 배포 환경을 선택한다.
- [ ] 발표 데모용 입력값을 정한다.
- [ ] 각 팀원 코드 설명 분량을 정한다.
- [ ] 최종 실행 영상을 찍거나 발표 리허설을 한다.

Quality Gate:

- [ ] 새 PC 또는 새 가상환경에서 설치 후 실행 가능하다.
- [ ] GitHub URL 접속이 가능하다.
- [ ] PRD, README, ARCHITECTURE, PLAN 문서가 모두 존재한다.
- [ ] 발표자가 각 tool의 역할을 설명할 수 있다.

검증 명령:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Rollback:

- 문서 변경은 이전 버전으로 되돌릴 수 있게 Git commit 단위로 관리한다.

## 9. LLM 프롬프트 원칙

LLM에는 다음 원칙을 적용한다.

```text
너는 사주 계산을 직접 하지 않는다.
아래 JSON에 있는 tool 결과만 근거로 해석한다.
JSON에 없는 정보는 추측하지 않는다.
계산 결과가 비어 있거나 불확실하면 제한적으로 해석한다고 말한다.
건강, 질병, 수명, 사고, 투자 수익, 합격, 당첨 등은 단정하지 않는다.
답변은 엔터테인먼트와 자기성찰용 조언으로 작성한다.
```

## 10. 메뉴별 실행 흐름

| 사용자 요청 | 실행되는 tool | LLM 역할 |
|---|---|---|
| 사주풀이 | Tool 1, Tool 2 | 성향, 강점, 주의점 설명 |
| 오늘의 운세 | Tool 1, Tool 2, Tool 3 | 오늘 흐름과 조언 설명 |
| 행운 색깔 | Tool 1, Tool 2, Tool 4 | 색깔과 이유 설명 |
| 행운 아이템 | Tool 1, Tool 2, Tool 4 | 아이템과 이유 설명 |
| 연애운 | Tool 1, Tool 2 | 관계/소통 중심으로 해석 |
| 재물운 | Tool 1, Tool 2 | 소비/기회/주의점 중심으로 해석 |
| 인생흐름 | Tool 1, Tool 2 | 초년/청년/중년/후반 흐름 설명 |

최적화:

- Tool 1과 Tool 2 결과는 최초 1회 생성 후 세션에 저장한다.
- 이후 메뉴 선택 시 필요한 tool만 추가 실행한다.

## 11. 테스트 체크리스트

### 기능 테스트

- [ ] 정상 입력으로 사주 프로필이 생성된다.
- [ ] 출생시간 미상이어도 앱이 중단되지 않는다.
- [ ] 오늘의 행운 점수가 표시된다.
- [ ] 행운 색깔과 아이템이 표시된다.
- [ ] 연애운, 재물운, 인생흐름 답변이 표시된다.
- [ ] 건강운 관련 요청에는 제외 안내를 반환한다.

### 안전 테스트

- [ ] LLM이 질병, 수명, 사고를 단정하지 않는다.
- [ ] LLM이 투자 수익을 단정하지 않는다.
- [ ] LLM이 계산되지 않은 사주값을 지어내지 않는다.
- [ ] 결과 하단에 엔터테인먼트/자기성찰 목적 안내가 표시된다.

### 발표 테스트

- [ ] 3분 이내 데모 시나리오가 가능하다.
- [ ] 각 팀원이 자기 tool을 30초 내로 설명할 수 있다.
- [ ] 전체 아키텍처를 한 장으로 설명할 수 있다.

## 12. 리스크 및 대응

| 리스크 | 가능성 | 영향 | 대응 |
|---|---|---|---|
| 만세력 계산이 예상보다 어렵다 | 높음 | 높음 | MVP에서는 단순 계산/샘플 어댑터로 구현하고, 시간이 남으면 고도화한다. |
| `manseryeok-js`와 Python 연동이 어렵다 | 중간 | 중간 | Node.js 호출을 포기하고 Python 기반 계산 또는 공공 API로 전환한다. |
| LLM이 결과를 지어낸다 | 중간 | 높음 | JSON 결과만 해석하도록 프롬프트를 제한하고, 없는 정보는 추측 금지한다. |
| 팀원별 tool 결과 형식이 다르다 | 중간 | 높음 | JSON schema를 먼저 합의하고 테스트로 고정한다. |
| 발표 직전 실행 오류가 난다 | 중간 | 높음 | 발표용 고정 입력값과 예비 스크린샷을 준비한다. |
| API 키가 노출된다 | 낮음 | 높음 | `.env` 사용, `.env.example`만 GitHub에 올린다. |

## 13. 산출물 체크리스트

### 제출물

- [ ] PRD 파일
- [ ] GitHub URL
- [ ] 기술 스택 목록
- [ ] 실행 가능한 챗봇 코드
- [ ] `requirements.txt` 또는 `pyproject.toml`
- [ ] 배포 URL 또는 실행 방법

### 문서

- [ ] `README.md`
- [ ] `PRD.md`
- [ ] `ARCHITECTURE.md`
- [ ] `docs/plans/PLAN_saju-chatbot.md`

### 코드

- [ ] `app.py`
- [ ] `src/tools/saju_chart.py`
- [ ] `src/tools/five_elements.py`
- [ ] `src/tools/today_luck.py`
- [ ] `src/tools/lucky_factors.py`
- [ ] `src/orchestrator.py`
- [ ] `src/prompts.py`
- [ ] `tests/` 파일

## 14. 발표 시나리오

1. 문제 소개
   - 사주 기반으로 오늘의 운세와 자기성찰 조언을 제공하는 챗봇을 만들었다고 설명한다.

2. 사용자 입력 시연
   - 이름, 성별, 생년월일, 출생시간, 양력/음력 여부를 입력한다.

3. 사주 프로필 생성 설명
   - 만세력 계산 tool과 오행 분석 tool이 먼저 실행된다고 설명한다.

4. 기능 메뉴 시연
   - 오늘의 행운 점수
   - 행운 색깔
   - 행운 아이템
   - 연애운 또는 재물운

5. 기술 구조 설명
   - `@tool`로 정의한 4개 tool을 소개한다.
   - LLM은 계산하지 않고 해석만 한다고 설명한다.

6. 안전 설계 설명
   - 건강운은 제외했다.
   - 중요한 의사결정에 영향을 줄 수 있는 단정적 예측은 제한했다.

7. 팀원별 기여 설명
   - 최연준: 만세력 계산 tool
   - 이윤서: 오행 분석 tool
   - 최호택: 오늘 운세 점수 tool
   - 전원정: 행운 색깔/아이템 추천 tool

## 15. Notes & Learnings

- 입력 검증은 별도 tool이 아니라 공통 유틸 함수로 둔다.
- 필수 tool은 4개로 고정하고 팀원별 책임을 명확히 한다.
- LLM 해석은 tool 결과 JSON만 근거로 생성한다.
- 건강운은 제외한다.
- 인생흐름은 MVP에서는 정통 대운이 아니라 원국 기반 간단 해석으로 제한한다.
