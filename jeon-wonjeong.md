# 전원정 AI 코딩 지시서

## 1. 담당 작업 요약

담당자: 전원정

담당 tool:

```python
@tool
def recommend_lucky_factors(element_analysis_json: str) -> str:
    """보완 오행을 기준으로 행운 색깔과 행운 아이템을 추천한다."""
```

주요 책임:

- 보완 오행에 따른 행운 색깔 추천
- 보완 오행에 따른 행운 아이템 추천
- 추천 이유 생성
- 모든 오행에 대해 안정적인 추천 결과 반환
- LLM이 최종 답변에 바로 사용할 수 있는 구조화 JSON 제공

## 2. AI에게 전달할 메타 프롬프트

아래 프롬프트를 AI 코딩 에이전트에게 그대로 전달한다.

```text
너는 Python, LangChain, 테스트 주도 개발에 능숙한 시니어 개발자다.

우리는 사주 기반 자기성찰 챗봇을 만들고 있다. 반드시 먼저 `ARCHITECTURE.md`, `docs/plans/PLAN_saju-chatbot.md`, `docs/agent-handoffs/README.md`, `docs/agent-handoffs/jeon-wonjeong.md`를 읽고 현재 프로젝트 구조를 파악해라.

내 담당 작업은 LangChain `@tool` 기반 `recommend_lucky_factors(element_analysis_json: str) -> str` 구현이다. 이 tool은 오행 분석 결과 JSON을 받아 보완 오행에 맞는 행운 색깔과 행운 아이템을 추천해야 한다.

중요한 원칙:
- 함수는 JSON 문자열을 입력받고 JSON 문자열을 반환한다.
- 잘못된 입력은 앱을 죽이지 말고 `{ "ok": false, "error": ... }` 형식의 JSON으로 반환한다.
- 모든 오행 wood, fire, earth, metal, water에 대해 추천 결과가 있어야 한다.
- 추천은 단정적 예언이 아니라 엔터테인먼트와 자기성찰용 표현이어야 한다.
- 건강운, 질병, 수명, 사고, 투자 수익 같은 기능은 구현하지 않는다.
- 다른 팀원의 tool 파일은 건드리지 말고, 필요한 공통 상수만 최소 범위로 추가한다.
- 테스트를 먼저 작성하고, 그 테스트를 통과하는 방식으로 구현한다.

완료 후에는 수정한 파일, 실행한 테스트, 남은 이슈, 다른 팀원이 알아야 할 통합 포인트를 보고해라.
```

## 3. 입력 계약

입력은 이윤서 담당 `analyze_five_elements`의 성공 결과 JSON 문자열이다.

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

최소 필요 필드:

- `data.recommended_element`

## 4. 출력 계약

성공 시:

```json
{
  "ok": true,
  "data": {
    "recommended_element": "metal",
    "lucky_colors": ["흰색", "금색", "은색"],
    "lucky_items": ["시계", "펜", "금속 액세서리"],
    "reason": "금 기운은 정리, 판단, 집중의 상징으로 해석되어 오늘의 보완 요소로 추천합니다."
  }
}
```

실패 시:

```json
{
  "ok": false,
  "error": {
    "code": "INVALID_ELEMENT_ANALYSIS",
    "message": "recommended_element가 필요합니다."
  }
}
```

## 5. 추천 매핑 기준

| 오행 | 색깔 | 아이템 | 추천 이유 키워드 |
|---|---|---|---|
| wood | 초록, 민트 | 식물, 노트, 나무 소재 소품 | 성장, 시작, 정리 |
| fire | 빨강, 분홍, 보라 | 조명, 향초, 따뜻한 음료 | 활력, 표현, 자신감 |
| earth | 노랑, 베이지, 갈색 | 다이어리, 머그컵, 쿠션 | 안정, 균형, 현실감 |
| metal | 흰색, 금색, 은색 | 시계, 펜, 금속 액세서리 | 집중, 판단, 정돈 |
| water | 검정, 남색, 파랑 | 물병, 향수, 이어폰 | 차분함, 유연함, 회복 |

## 6. 구현 순서

1. 기존 문서 읽기
   - `ARCHITECTURE.md`
   - `docs/plans/PLAN_saju-chatbot.md`
   - `docs/agent-handoffs/README.md`

2. 테스트 작성
   - `tests/test_lucky_factors.py` 생성
   - 오행별 색깔 추천 테스트
   - 오행별 아이템 추천 테스트
   - 추천 이유 포함 테스트
   - 잘못된 JSON 테스트
   - 알 수 없는 오행 테스트

3. 구현 파일 생성
   - `src/tools/lucky_factors.py`
   - 필요 시 `src/tools/__init__.py`

4. `@tool` 함수 구현
   - JSON 문자열 파싱
   - `recommended_element` 확인
   - 오행별 색깔/아이템/이유 매핑
   - JSON 문자열 반환

5. 테스트 실행
   - `pytest tests/test_lucky_factors.py`

6. 통합 확인
   - 이윤서 담당 `analyze_five_elements` 출력의 `recommended_element`와 key 이름이 맞는지 확인한다.
   - LLM이 최종 답변에서 색깔, 아이템, 이유를 바로 사용할 수 있는지 확인한다.

## 7. 구현 가이드

### 권장 파일

```text
src/tools/lucky_factors.py
tests/test_lucky_factors.py
```

### 주의할 점

- 추천 결과는 모든 오행에 대해 있어야 한다.
- 색깔과 아이템은 각각 최소 3개씩 제공한다.
- 추천 이유는 짧고 발표에서 읽기 좋은 문장으로 만든다.
- "이 아이템을 가지면 반드시 좋은 일이 생긴다" 같은 단정 표현은 피한다.
- 알 수 없는 오행은 기본값으로 넘기지 말고 에러 JSON을 반환한다.

## 8. 테스트 케이스

필수 테스트:

- [ ] `wood`는 초록/민트 계열 색상을 반환한다.
- [ ] `fire`는 빨강/분홍/보라 계열 색상을 반환한다.
- [ ] `earth`는 노랑/베이지/갈색 계열 색상을 반환한다.
- [ ] `metal`은 흰색/금색/은색 계열 색상을 반환한다.
- [ ] `water`는 검정/남색/파랑 계열 색상을 반환한다.
- [ ] 모든 오행은 아이템을 최소 3개 반환한다.
- [ ] 결과에 `reason`이 포함된다.
- [ ] 잘못된 JSON 문자열은 `ok: false`를 반환한다.
- [ ] `recommended_element` 누락 시 `ok: false`를 반환한다.
- [ ] 알 수 없는 오행은 `ok: false`를 반환한다.

## 9. 완료 기준

- [ ] `recommend_lucky_factors`에 `@tool`이 붙어 있다.
- [ ] 모든 오행에 대한 색깔/아이템 매핑이 구현되어 있다.
- [ ] JSON 입력/출력 계약을 지킨다.
- [ ] 테스트가 통과한다.
- [ ] LLM이 사용할 수 있는 추천 이유를 반환한다.

## 10. 최종 보고 형식

AI는 작업 완료 후 다음 형식으로 보고한다.

```text
전원정 담당 작업 완료 보고

완료한 작업:
- ...

수정/생성한 파일:
- ...

실행한 테스트:
- ...

오행별 추천 매핑:
- ...

샘플 출력 JSON:
- ...

남은 이슈:
- ...

다른 팀원에게 전달할 내용:
- ...
```
