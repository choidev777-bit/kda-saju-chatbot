# 최호택 AI 코딩 지시서

## 1. 담당 작업 요약

담당자: 최호택

담당 tool:

```python
@tool
def calculate_today_luck(profile_json: str) -> str:
    """사용자 사주 프로필과 오늘 날짜의 기운을 비교해 오늘의 행운 점수를 계산한다."""
```

주요 책임:

- 사용자 사주 프로필과 오늘 날짜를 바탕으로 오늘의 행운 점수 계산
- 점수 계산 규칙 구현
- 점수 근거 `signals`와 주의점 `cautions` 반환
- 점수를 항상 0~100 범위로 제한
- LLM이 오늘의 운세를 자연어로 해석할 수 있는 구조화 데이터 제공

## 2. AI에게 전달할 메타 프롬프트

아래 프롬프트를 AI 코딩 에이전트에게 그대로 전달한다.

```text
너는 Python, LangChain, 테스트 주도 개발에 능숙한 시니어 개발자다.

우리는 사주 기반 자기성찰 챗봇을 만들고 있다. 반드시 먼저 `ARCHITECTURE.md`, `docs/plans/PLAN_saju-chatbot.md`, `docs/agent-handoffs/README.md`, `docs/agent-handoffs/choi-hotaek.md`를 읽고 현재 프로젝트 구조를 파악해라.

내 담당 작업은 LangChain `@tool` 기반 `calculate_today_luck(profile_json: str) -> str` 구현이다. 이 tool은 사용자 사주 프로필과 오늘 날짜의 기운을 비교해 0~100점 사이의 오늘의 행운 점수를 반환해야 한다.

중요한 원칙:
- 함수는 JSON 문자열을 입력받고 JSON 문자열을 반환한다.
- 잘못된 입력은 앱을 죽이지 말고 `{ "ok": false, "error": ... }` 형식의 JSON으로 반환한다.
- 점수 계산은 임의 문장이 아니라 코드 규칙으로 수행한다.
- 점수는 항상 0 이상 100 이하로 제한한다.
- 오늘의 운세는 단정적 예언이 아니라 자기성찰용 조언으로 해석될 수 있게 근거를 반환한다.
- 건강운, 질병, 수명, 사고, 투자 수익 같은 기능은 구현하지 않는다.
- 다른 팀원의 tool 파일은 건드리지 말고, 필요한 공통 상수만 최소 범위로 추가한다.
- 테스트를 먼저 작성하고, 그 테스트를 통과하는 방식으로 구현한다.

완료 후에는 수정한 파일, 실행한 테스트, 남은 이슈, 다른 팀원이 알아야 할 통합 포인트를 보고해라.
```

## 3. 입력 계약

입력은 사용자 사주 프로필 JSON 문자열이다.

```json
{
  "ok": true,
  "data": {
    "user": {
      "name": "민지",
      "birth_date": "1998-03-12"
    },
    "saju_chart": {
      "year_pillar": "무인",
      "month_pillar": "을묘",
      "day_pillar": "병진",
      "hour_pillar": "정사",
      "time_precision": "known"
    },
    "five_elements": {
      "counts": {
        "wood": 3,
        "fire": 2,
        "earth": 2,
        "metal": 0,
        "water": 1
      },
      "strong_element": "wood",
      "weak_element": "metal",
      "recommended_element": "metal"
    }
  }
}
```

최소 필요 필드:

- `five_elements.recommended_element`
- `five_elements.weak_element`
- `five_elements.strong_element`

## 4. 출력 계약

성공 시:

```json
{
  "ok": true,
  "data": {
    "date": "2026-06-24",
    "score": 82,
    "score_range": "0-100",
    "today_element": "metal",
    "recommended_element": "metal",
    "signals": [
      "오늘의 기운이 보완 오행과 잘 맞아 균형감을 높이는 흐름입니다."
    ],
    "cautions": [
      "좋은 흐름이 있어도 중요한 결정은 한 번 더 확인하는 편이 좋습니다."
    ]
  }
}
```

실패 시:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_PROFILE",
    "message": "five_elements.recommended_element가 필요합니다."
  }
}
```

## 5. 점수 계산 규칙

MVP에서는 아래 규칙을 사용한다.

기본 점수:

- 시작 점수: 70점

가산점:

- 오늘 오행이 `recommended_element`와 같으면 +10
- 오늘 오행이 `weak_element`와 같으면 +8
- 오늘 오행이 `strong_element`와 다르면 균형 보완 가능성으로 +3

감산점:

- 오늘 오행이 `strong_element`와 같고 이미 강한 기운을 더 키우는 경우 -5
- 필요한 필드가 일부 부족해 제한 해석이면 -5

범위 제한:

- 최종 점수는 0~100으로 clamp한다.

오늘 오행 계산 MVP:

- 외부 만세력 계산이 준비되지 않은 경우, 오늘 날짜를 기준으로 deterministic하게 오행을 선택한다.
- 예: 날짜 ordinal 또는 `YYYYMMDD` 값을 5로 나눈 나머지를 `wood`, `fire`, `earth`, `metal`, `water`에 매핑한다.
- 중요한 점은 같은 날짜에는 항상 같은 오늘 오행이 나와야 한다는 것이다.

## 6. 구현 순서

1. 기존 문서 읽기
   - `ARCHITECTURE.md`
   - `docs/plans/PLAN_saju-chatbot.md`
   - `docs/agent-handoffs/README.md`

2. 테스트 작성
   - `tests/test_today_luck.py` 생성
   - 점수 범위 테스트
   - recommended element와 today element가 같을 때 가산 테스트
   - strong element와 today element가 같을 때 감산 테스트
   - 잘못된 JSON 테스트
   - 필수 필드 누락 테스트

3. 구현 파일 생성
   - `src/tools/today_luck.py`
   - 필요 시 `src/tools/__init__.py`

4. `@tool` 함수 구현
   - JSON 문자열 파싱
   - 필수 필드 확인
   - 오늘 날짜 구하기
   - 오늘 오행 계산
   - 점수 계산
   - `signals`, `cautions` 생성
   - JSON 문자열 반환

5. 테스트 실행
   - `pytest tests/test_today_luck.py`

6. 통합 확인
   - 이윤서 담당 `analyze_five_elements` 출력의 `recommended_element`를 입력으로 사용할 수 있는지 확인한다.
   - LLM이 오늘의 운세를 쓸 수 있도록 `signals`와 `cautions`가 충분히 구체적인지 확인한다.

## 7. 구현 가이드

### 권장 파일

```text
src/tools/today_luck.py
tests/test_today_luck.py
```

### 주의할 점

- 점수는 코드 규칙으로 계산한다.
- LLM에게 점수 계산을 맡기지 않는다.
- 오늘 날짜에 따라 결과가 달라질 수 있으므로 테스트에서는 날짜를 주입할 수 있게 helper 함수를 분리하는 것이 좋다.
- `signals`와 `cautions`는 단정적 예언이 아니라 조언 근거가 되도록 작성한다.
- 건강, 질병, 수명, 사고, 투자 수익 관련 문구를 넣지 않는다.

## 8. 테스트 케이스

필수 테스트:

- [ ] 정상 입력은 `ok: true`를 반환한다.
- [ ] `score`는 0~100 범위다.
- [ ] 오늘 오행이 `recommended_element`와 같으면 점수가 기본점수보다 높다.
- [ ] 오늘 오행이 `strong_element`와 같으면 감산 규칙이 적용된다.
- [ ] 결과에 `date`, `score`, `today_element`, `signals`, `cautions`가 있다.
- [ ] 잘못된 JSON 문자열은 `ok: false`를 반환한다.
- [ ] `recommended_element` 누락 시 `ok: false`를 반환한다.

## 9. 완료 기준

- [ ] `calculate_today_luck`에 `@tool`이 붙어 있다.
- [ ] 점수 계산 규칙이 코드로 구현되어 있다.
- [ ] 점수가 0~100 범위를 벗어나지 않는다.
- [ ] JSON 입력/출력 계약을 지킨다.
- [ ] 테스트가 통과한다.
- [ ] LLM이 활용할 수 있는 `signals`, `cautions`를 반환한다.

## 10. 최종 보고 형식

AI는 작업 완료 후 다음 형식으로 보고한다.

```text
최호택 담당 작업 완료 보고

완료한 작업:
- ...

수정/생성한 파일:
- ...

실행한 테스트:
- ...

점수 계산 규칙:
- ...

샘플 출력 JSON:
- ...

남은 이슈:
- ...

다른 팀원에게 전달할 내용:
- ...
```
