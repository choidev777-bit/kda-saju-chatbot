# 이윤서 AI 코딩 지시서

## 1. 담당 작업 요약

담당자: 이윤서

담당 tool:

```python
@tool
def analyze_five_elements(saju_chart_json: str) -> str:
    """사주팔자 데이터를 바탕으로 목, 화, 토, 금, 수 오행의 강약을 분석한다."""
```

주요 책임:

- 사주팔자에서 천간/지지를 읽어 오행 개수 계산
- 강한 오행, 약한 오행, 보완 오행 판단
- 오늘 운세 점수 tool과 행운 추천 tool이 사용할 오행 분석 JSON 반환
- 오행 매핑 테이블 구현
- 동률 처리 규칙 정의

## 2. AI에게 전달할 메타 프롬프트

아래 프롬프트를 AI 코딩 에이전트에게 그대로 전달한다.

```text
너는 Python, LangChain, 테스트 주도 개발에 능숙한 시니어 개발자다.

우리는 사주 기반 자기성찰 챗봇을 만들고 있다. 반드시 먼저 `ARCHITECTURE.md`, `docs/plans/PLAN_saju-chatbot.md`, `docs/agent-handoffs/README.md`, `docs/agent-handoffs/lee-yunseo.md`를 읽고 현재 프로젝트 구조를 파악해라.

내 담당 작업은 LangChain `@tool` 기반 `analyze_five_elements(saju_chart_json: str) -> str` 구현이다. 이 tool은 만세력 계산 tool의 결과 JSON을 받아 목, 화, 토, 금, 수 오행 개수와 강약을 분석해야 한다.

중요한 원칙:
- 함수는 JSON 문자열을 입력받고 JSON 문자열을 반환한다.
- 잘못된 입력은 앱을 죽이지 말고 `{ "ok": false, "error": ... }` 형식의 JSON으로 반환한다.
- 천간/지지 오행 매핑은 코드 안에서 명확하게 확인 가능해야 한다.
- 동률 상황에서도 결과가 항상 안정적으로 나오게 한다.
- 다른 팀원의 tool 파일은 건드리지 말고, 필요한 공통 상수만 최소 범위로 추가한다.
- 건강운, 질병, 수명, 사고, 투자 수익 같은 기능은 구현하지 않는다.
- 테스트를 먼저 작성하고, 그 테스트를 통과하는 방식으로 구현한다.

완료 후에는 수정한 파일, 실행한 테스트, 남은 이슈, 다른 팀원이 알아야 할 통합 포인트를 보고해라.
```

## 3. 입력 계약

입력은 `calculate_saju_chart`의 성공 결과 JSON 문자열이다.

```json
{
  "ok": true,
  "data": {
    "year_pillar": "무인",
    "month_pillar": "을묘",
    "day_pillar": "병진",
    "hour_pillar": "정사",
    "time_precision": "known",
    "calendar_type": "solar",
    "source": "mvp_calculator"
  }
}
```

`hour_pillar`는 출생시간 미상일 때 null일 수 있다.

## 4. 출력 계약

성공 시:

```json
{
  "ok": true,
  "data": {
    "counts": {
      "wood": 3,
      "fire": 2,
      "earth": 2,
      "metal": 0,
      "water": 1
    },
    "strong_element": "wood",
    "weak_element": "metal",
    "recommended_element": "metal",
    "missing_elements": ["metal"],
    "summary": "목 기운이 강하고 금 기운이 부족한 구조입니다."
  }
}
```

실패 시:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_SAJU_CHART",
    "message": "year_pillar, month_pillar, day_pillar 중 하나가 누락되었습니다."
  }
}
```

## 5. 오행 매핑 기준

천간 매핑:

| 천간 | 오행 |
|---|---|
| 갑, 을 | wood |
| 병, 정 | fire |
| 무, 기 | earth |
| 경, 신 | metal |
| 임, 계 | water |

지지 매핑:

| 지지 | 오행 |
|---|---|
| 인, 묘 | wood |
| 사, 오 | fire |
| 진, 술, 축, 미 | earth |
| 신, 유 | metal |
| 해, 자 | water |

동률 처리 권장:

1. 가장 개수가 많은 오행이 여러 개면 `strong_element`는 고정 우선순위 `wood`, `fire`, `earth`, `metal`, `water` 순으로 하나를 선택한다.
2. 가장 개수가 적은 오행이 여러 개면 `weak_element`도 같은 우선순위로 하나를 선택한다.
3. 개수가 0인 오행은 `missing_elements`에 모두 넣는다.
4. `recommended_element`는 `weak_element`와 동일하게 둔다.

## 6. 구현 순서

1. 기존 문서 읽기
   - `ARCHITECTURE.md`
   - `docs/plans/PLAN_saju-chatbot.md`
   - `docs/agent-handoffs/README.md`

2. 테스트 작성
   - `tests/test_five_elements.py` 생성
   - 천간 매핑 테스트
   - 지지 매핑 테스트
   - 오행 개수 계산 테스트
   - `hour_pillar: null` 처리 테스트
   - 잘못된 JSON 테스트

3. 구현 파일 생성
   - `src/tools/five_elements.py`
   - 필요 시 `src/tools/__init__.py`

4. `@tool` 함수 구현
   - JSON 문자열 파싱
   - `ok: false` 입력이 들어온 경우 적절한 에러 반환
   - pillar 값에서 첫 글자 천간, 두 번째 글자 지지 추출
   - 천간/지지 각각의 오행 count 증가
   - 강한 오행, 약한 오행, 보완 오행 계산

5. 테스트 실행
   - `pytest tests/test_five_elements.py`

6. 통합 확인
   - `recommended_element`가 전원정 담당 `recommend_lucky_factors`의 입력으로 사용될 수 있는지 확인한다.
   - `weak_element`가 최호택 담당 `calculate_today_luck`에서 사용할 수 있는지 확인한다.

## 7. 구현 가이드

### 권장 파일

```text
src/tools/five_elements.py
tests/test_five_elements.py
```

### 주의할 점

- 한글 간지 문자열은 보통 두 글자다. 예: `무인`, `을묘`.
- `hour_pillar`가 null이면 시주는 계산에서 제외한다.
- 알 수 없는 글자가 있으면 조용히 무시하지 말고 에러 JSON을 반환한다.
- 결과 JSON의 key 이름은 영어로 고정한다.
- LLM이 이해할 수 있도록 `summary`를 짧게 포함한다.

## 8. 테스트 케이스

필수 테스트:

- [ ] `무인`은 `earth`와 `wood`를 각각 1씩 증가시킨다.
- [ ] `을묘`는 `wood`를 2 증가시킨다.
- [ ] `hour_pillar`가 null이면 나머지 3개 기둥만 분석한다.
- [ ] 가장 많은 오행이 `strong_element`가 된다.
- [ ] 가장 적은 오행이 `weak_element`와 `recommended_element`가 된다.
- [ ] 개수가 0인 오행은 `missing_elements`에 포함된다.
- [ ] 잘못된 JSON 문자열은 `ok: false`를 반환한다.
- [ ] 알 수 없는 간지 문자는 `ok: false`를 반환한다.

## 9. 완료 기준

- [ ] `analyze_five_elements`에 `@tool`이 붙어 있다.
- [ ] 천간/지지 오행 매핑이 구현되어 있다.
- [ ] JSON 입력/출력 계약을 지킨다.
- [ ] 테스트가 통과한다.
- [ ] 최호택, 전원정 tool에서 사용할 수 있는 `recommended_element`를 반환한다.

## 10. 최종 보고 형식

AI는 작업 완료 후 다음 형식으로 보고한다.

```text
이윤서 담당 작업 완료 보고

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
