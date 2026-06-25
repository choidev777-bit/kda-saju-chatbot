# 최연준 AI 코딩 지시서

## 1. 담당 작업 요약

담당자: 최연준

담당 tool:

```python
@tool
def calculate_saju_chart(user_info_json: str) -> str:
    """사용자의 생년월일, 출생시간, 양력/음력 정보를 바탕으로 사주팔자를 계산한다."""
```

주요 책임:

- 만세력 계산 tool 구현
- 사용자 입력 JSON을 사주팔자 JSON으로 변환
- 출생시간 미상 처리
- tool 결과 JSON 계약 정의
- 다른 팀원의 tool과 연결될 수 있도록 결과 schema를 안정화
- 전체 통합 시 기준이 되는 샘플 입력/출력 제공

## 2. AI에게 전달할 메타 프롬프트

아래 프롬프트를 AI 코딩 에이전트에게 그대로 전달한다.

```text
너는 Python, LangChain, 테스트 주도 개발에 능숙한 시니어 개발자다.

우리는 사주 기반 자기성찰 챗봇을 만들고 있다. 반드시 먼저 `ARCHITECTURE.md`, `docs/plans/PLAN_saju-chatbot.md`, `docs/agent-handoffs/README.md`, `docs/agent-handoffs/choi-yeonjun.md`를 읽고 현재 프로젝트 구조를 파악해라.

내 담당 작업은 LangChain `@tool` 기반 `calculate_saju_chart(user_info_json: str) -> str` 구현이다. 이 tool은 사용자 입력 JSON을 받아 사주팔자 계산 결과 JSON을 반환해야 한다.

중요한 원칙:
- LLM이 사주 계산을 직접 하지 않도록 계산 결과를 구조화해서 반환한다.
- 함수는 JSON 문자열을 입력받고 JSON 문자열을 반환한다.
- 잘못된 입력은 앱을 죽이지 말고 `{ "ok": false, "error": ... }` 형식의 JSON으로 반환한다.
- 입력 검증은 필요한 최소 범위에서 구현하되, 별도 LangChain tool로 만들지 않는다.
- 건강운, 질병, 수명, 사고, 투자 수익 같은 기능은 구현하지 않는다.
- 다른 팀원의 tool 파일은 건드리지 말고, 필요한 공통 상수만 최소 범위로 추가한다.
- 테스트를 먼저 작성하고, 그 테스트를 통과하는 방식으로 구현한다.

완료 후에는 수정한 파일, 실행한 테스트, 남은 이슈, 다른 팀원이 알아야 할 통합 포인트를 보고해라.
```

## 3. 입력 계약

입력은 JSON 문자열이다.

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

필수 필드:

| 필드 | 타입 | 설명 |
|---|---|---|
| `name` | string | 사용자 이름 |
| `gender` | string (선택) | `female`, `male`, `other`, `unknown` 중 하나 권장. 생략 시 `unknown` 으로 처리되며 만세력 계산에는 사용되지 않는다 |
| `birth_date` | string | `YYYY-MM-DD` |
| `birth_time` | string 또는 null | `HH:MM`, 출생시간 미상일 경우 null 가능 |
| `calendar_type` | string | `solar` 또는 `lunar` |
| `birth_time_unknown` | boolean | 출생시간 미상 여부 |

## 4. 출력 계약

성공 시:

```json
{
  "ok": true,
  "data": {
    "year_pillar": "무인",
    "month_pillar": "을묘",
    "day_pillar": "예시",
    "hour_pillar": "예시",
    "time_precision": "known",
    "calendar_type": "solar",
    "source": "mvp_calculator"
  }
}
```

출생시간 미상 시:

```json
{
  "ok": true,
  "data": {
    "year_pillar": "무인",
    "month_pillar": "을묘",
    "day_pillar": "예시",
    "hour_pillar": null,
    "time_precision": "unknown",
    "calendar_type": "solar",
    "source": "mvp_calculator"
  }
}
```

실패 시:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_INPUT",
    "message": "birth_date는 YYYY-MM-DD 형식이어야 합니다."
  }
}
```

## 5. 구현 순서

1. 기존 파일 확인
   - `ARCHITECTURE.md`
   - `docs/plans/PLAN_saju-chatbot.md`
   - `docs/agent-handoffs/README.md`

2. 테스트 작성
   - `tests/test_saju_chart.py` 생성
   - 정상 입력 테스트
   - 출생시간 미상 테스트
   - 잘못된 날짜 테스트
   - 잘못된 JSON 테스트

3. 구현 파일 생성
   - `src/tools/saju_chart.py`
   - 필요 시 `src/tools/__init__.py`
   - 필요 시 `src/__init__.py`

4. `@tool` 함수 구현
   - `from langchain.tools import tool` 또는 프로젝트에서 사용하는 최신 import 경로 사용
   - JSON 문자열 파싱
   - 필수 필드 확인
   - 사주팔자 계산 결과 생성
   - JSON 문자열 반환

5. MVP 계산 전략 선택
   - 시간이 부족하면 deterministic MVP 계산기를 먼저 만든다.
   - 정확한 만세력 연동은 별도 어댑터 함수로 감싸 나중에 교체 가능하게 한다.
   - `source` 필드에 현재 계산 방식이 MVP인지 외부 라이브러리인지 표시한다.
   - `manseryeok-js`를 사용할 경우 GitHub ZIP을 다운로드하지 않는다.
   - npm 패키지 `@fullstackfamily/manseryeok`를 설치해서 사용한다.
   - Python에서 직접 import하지 말고 Node.js helper 스크립트를 만들어 Python `@tool`에서 호출한다.

   ```bash
   npm install @fullstackfamily/manseryeok
   ```

   권장 연결 구조:

   ```text
   src/tools/saju_chart.py
   ↓ subprocess.run(["node", "scripts/calculate_saju.mjs", user_info_json])
   scripts/calculate_saju.mjs
   ↓ import { calculateSaju } from "@fullstackfamily/manseryeok"
   JSON 결과 반환
   ```

6. 테스트 실행
   - `pytest tests/test_saju_chart.py`

7. 통합 확인
   - 반환 JSON이 이윤서 담당 `analyze_five_elements` 입력으로 쓰일 수 있는지 확인한다.

## 6. 구현 가이드

### 권장 파일

```text
src/tools/saju_chart.py
scripts/calculate_saju.mjs
package.json
tests/test_saju_chart.py
```

### 주의할 점

- MVP에서 계산 정확도가 완전하지 않다면 문서나 `source` 필드에 명확히 표시한다.
- LLM에게 "예시" 값을 넘기는 최종 구현은 피한다.
- `hour_pillar`는 출생시간 미상일 때 null로 둔다.
- 날짜가 지원 범위를 벗어나면 에러 JSON을 반환한다.
- 함수 내부에서 print를 남발하지 않는다.

## 7. 테스트 케이스

필수 테스트:

- [ ] 정상 입력은 `ok: true`를 반환한다.
- [ ] 반환 데이터에 `year_pillar`, `month_pillar`, `day_pillar`, `hour_pillar`, `time_precision`이 있다.
- [ ] `birth_time_unknown: true`이면 `hour_pillar`는 null이고 `time_precision`은 `unknown`이다.
- [ ] 잘못된 JSON 문자열은 `ok: false`를 반환한다.
- [ ] 잘못된 날짜 형식은 `ok: false`를 반환한다.
- [ ] `calendar_type`이 `solar` 또는 `lunar`가 아니면 `ok: false`를 반환한다.

## 8. 완료 기준

- [ ] `calculate_saju_chart`에 `@tool`이 붙어 있다.
- [ ] 함수 docstring이 tool의 목적을 설명한다.
- [ ] JSON 입력/출력 계약을 지킨다.
- [ ] 테스트가 통과한다.
- [ ] 다른 팀원이 사용할 샘플 출력 JSON을 제공한다.

## 9. 최종 보고 형식

AI는 작업 완료 후 다음 형식으로 보고한다.

```text
최연준 담당 작업 완료 보고

완료한 작업:
- ...

수정/생성한 파일:
- ...

실행한 테스트:
- ...

샘플 출력 JSON:
- ...

남은 이슈:
- ...

다른 팀원에게 전달할 내용:
- ...
```
