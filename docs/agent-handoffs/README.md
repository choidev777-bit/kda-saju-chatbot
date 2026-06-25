# AI 코딩 에이전트 전달 문서 모음

이 폴더는 팀원들이 각자 사용하는 AI 코딩 에이전트에게 전달할 작업 지시서다. 각 팀원은 자기 이름에 해당하는 문서를 AI에게 먼저 읽히고, 그 문서의 "AI에게 전달할 메타 프롬프트"를 작업 시작 프롬프트로 사용한다.

## 공통 프로젝트 목표

사주 기반 자기성찰 챗봇을 구현한다. 사용자는 이름, 성별, 생년월일, 출생시간, 양력/음력 여부를 입력한다. 앱은 LangChain `@tool`로 정의된 계산/분석 tool을 호출하고, LLM은 tool 결과 JSON만 바탕으로 자연어 해석을 생성한다.

건강운은 구현하지 않는다. 질병, 수명, 사고, 투자 수익, 합격, 당첨 같은 단정적 예측도 제공하지 않는다.

## 필수 참고 문서

AI는 작업 전에 아래 문서를 먼저 읽어야 한다.

1. `ARCHITECTURE.md`
2. `docs/plans/PLAN_saju-chatbot.md`
3. 자기 담당 문서

## 팀원별 담당

| 팀원 | 문서 | 담당 tool |
|---|---|---|
| 최연준 | `choi-yeonjun.md` | `calculate_saju_chart` |
| 이윤서 | `lee-yunseo.md` | `analyze_five_elements` |
| 최호택 | `choi-hotaek.md` | `calculate_today_luck` |
| 전원정 | `jeon-wonjeong.md` | `recommend_lucky_factors` |

## 공통 구현 규칙

- Python으로 구현한다.
- LangChain의 `@tool` 데코레이터를 사용한다.
- tool 함수는 JSON 문자열을 입력받고 JSON 문자열을 반환한다.
- JSON 파싱 실패, 필수 필드 누락, 지원하지 않는 값은 예외로 앱을 죽이지 말고 구조화된 에러 JSON을 반환한다.
- 입력 검증은 별도 tool이 아니라 공통 유틸 함수로 구현한다.
- LLM이 사주 계산을 직접 하게 만들지 않는다.
- 각자 담당 tool과 테스트를 우선 구현한다.
- 다른 팀원의 tool 파일은 필요한 경우가 아니면 수정하지 않는다.
- 공통 타입이나 상수가 필요하면 `src/config.py` 또는 별도 공통 모듈에 최소 변경으로 추가한다.
- `manseryeok-js`를 사용할 경우 GitHub ZIP을 다운로드하지 않고 npm 패키지 `@fullstackfamily/manseryeok`를 설치한다.
- Python에서 `@fullstackfamily/manseryeok`를 직접 import할 수 없으므로, 필요한 경우 Python tool에서 Node.js helper 스크립트를 호출한다.

## 권장 파일 구조

```text
kda-chatbot/
├─ app.py
├─ requirements.txt
├─ package.json
├─ ARCHITECTURE.md
├─ scripts/
│  └─ calculate_saju.mjs
├─ docs/
│  ├─ plans/
│  │  └─ PLAN_saju-chatbot.md
│  └─ agent-handoffs/
│     ├─ README.md
│     ├─ choi-yeonjun.md
│     ├─ lee-yunseo.md
│     ├─ choi-hotaek.md
│     └─ jeon-wonjeong.md
├─ src/
│  ├─ __init__.py
│  ├─ config.py
│  ├─ input_utils.py
│  ├─ tools/
│  │  ├─ __init__.py
│  │  ├─ saju_chart.py
│  │  ├─ five_elements.py
│  │  ├─ today_luck.py
│  │  └─ lucky_factors.py
│  └─ orchestrator.py
└─ tests/
   ├─ test_saju_chart.py
   ├─ test_five_elements.py
   ├─ test_today_luck.py
   └─ test_lucky_factors.py
```

## 공통 에러 JSON 형식

tool이 실패할 때는 다음 형식으로 반환한다.

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "birth_date는 YYYY-MM-DD 형식이어야 합니다."
  }
}
```

성공할 때는 다음 형식을 권장한다.

```json
{
  "ok": true,
  "data": {
    "...": "..."
  }
}
```

## AI 작업 완료 보고 형식

각 팀원의 AI는 작업 완료 후 아래 형식으로 보고해야 한다.

```text
완료한 작업:
- ...

수정/생성한 파일:
- ...

실행한 테스트:
- ...

남은 이슈:
- ...

통합 시 주의할 점:
- ...
```
