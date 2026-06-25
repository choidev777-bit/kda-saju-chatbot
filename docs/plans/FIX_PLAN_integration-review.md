# 통합 리뷰 수정 계획서 (Codex 작업 지시서)

> 이 문서는 다중 에이전트 코드 리뷰에서 확정된 결함을 수정하기 위한 **자체 완결적 작업 지시서**다.
> Codex는 이 문서만으로 작업할 수 있어야 한다. 우리 대화 맥락은 없다고 가정한다.

## 0. 프로젝트 컨텍스트

`kda-chatbot`은 사주 기반 자기성찰 챗봇이다. 계산은 LangChain `@tool`(deterministic)이 하고
LLM은 결과 JSON만 해석한다. 모든 tool은 **JSON 문자열 입력 → JSON 문자열 출력**이며
성공은 `{"ok": true, "data": {...}}`, 실패는 `{"ok": false, "error": {"code","message"}}` 형식이다.

작업 대상 브랜치: **`integration`** (여기에 4개 tool이 모두 모여 있다).
수정 대상 파일(세 팀원의 tool + 테스트):

- `src/tools/today_luck.py` (+ `tests/test_today_luck.py`) — 결함 다수
- `src/tools/lucky_factors.py` (+ `tests/test_lucky_factors.py`)
- `src/tools/five_elements.py` (+ `tests/test_five_elements.py`)
- 공통: `src/config.py` (이미 존재하는 단일 소스 상수/헬퍼)

tool 간 데이터 계약(중요):
- `analyze_five_elements`: 입력=만세력 성공 JSON `{ok,data:{year_pillar,month_pillar,day_pillar,hour_pillar,...}}`
  → 출력 `{ok,data:{counts:{wood,fire,earth,metal,water}, strong_element, weak_element, recommended_element, missing_elements, summary}}`.
  **`recommended_element`는 항상 `weak_element`와 동일하게 설정된다.** (이 불변식이 아래 FIX-1의 핵심)
- `calculate_today_luck`: 입력=조립 profile `{ok,data:{user,saju_chart,five_elements:{...}}}`
  → 출력 `{ok,data:{date,score(0~100),today_element,recommended_element,signals,cautions}}`.
- `recommend_lucky_factors`: 입력=`analyze_five_elements` 성공 JSON `{ok,data:{recommended_element,...}}`
  → 출력 `{ok,data:{recommended_element,lucky_colors,lucky_items,reason}}`.

## 1. 작업 환경 & 검증 방법

```bash
# (최초 1회) 의존성
pip install -r requirements.txt        # langchain, langchain-core, streamlit, pytest 등
npm install                            # 만세력 Node helper용 (@fullstackfamily/manseryeok)

# 검증: 모든 수정 후 반드시 전체 테스트 통과
pytest -q
```

현재 기준선: **64 tests passing**. 수정 후에도 전부 통과해야 하고, 아래 명시된 신규 테스트가 추가되어야 한다.

## 2. 수정 원칙 (가드레일)

1. **JSON 계약을 깨지 마라.** 출력 key 이름(`ok/data/error/code/message`, 각 tool의 data 필드)을 바꾸지 않는다.
2. **잘못된 입력에 크래시 금지.** 예외는 구조화된 `{ok:false,error}` JSON으로 변환한다.
3. **deterministic 유지.** 같은 입력(+같은 날짜)은 같은 출력.
4. **금지 주제 추가 금지.** 건강/질병/수명/사고/투자수익/합격/당첨 단정 문구를 넣지 않는다.
5. 기존 통과 테스트를 깨지 않는다. 동작 변경이 필요한 테스트는 "수용 기준"에 명시된 것만 수정한다.
6. 각 FIX는 가능한 한 **해당 tool 파일 내부에서** 최소 변경으로 처리한다(Phase 3 리팩터 제외).

---

## 3. 수정 항목

| ID | 심각도 | 파일 | 담당 | 한 줄 요약 |
|---|---|---|---|---|
| FIX-1 | **P1** | today_luck.py | 최호택 | 점수 가산 이중 계산 제거(+10/+8 동시발동) |
| FIX-2 | **P1** | today_luck.py | 최호택 | `@tool` 폴백에 `.invoke`/`langchain_core` 추가 |
| FIX-3 | P2 | today_luck.py | 최호택 | 비-문자열 `date` 입력 크래시 방지 |
| FIX-4 | P2 | lucky_factors.py | 전원정 | 업스트림 실패 게이트 강화(`ok is not True`) |
| FIX-5 | P2 | test_today_luck.py | 최호택 | 계약-충실(recommended==weak) 점수 테스트 추가 |
| FIX-6 | P3 | today_luck.py | 최호택 | `date`를 data 레벨에서도 읽기(주입/무시 버그) |
| FIX-7 | P3 | today_luck.py | 최호택 | 정규화 불일치: `_validate_element`에 strip/lower |
| FIX-8 | P3 | five_elements.py | 이윤서 | `_load_payload` 비-bool `ok` fallthrough 차단 |
| FIX-9 | P3 | five_elements.py | 이윤서 | 기둥 카운트 루프 중복 제거 |
| FIX-10 | P3 | today_luck.py | 최호택 | `_today_element_for_date` docstring 정정 |
| FIX-11(선택) | P3 | 3개 tool | 공통 | `config.py` 단일 소스로 수렴 리팩터 |

---

### FIX-1 (P1) — 점수 이중 가산 제거

**파일**: `src/tools/today_luck.py` (점수 계산 블록, 현재 대략 194~206행)

**문제**: `+10(recommended 일치)`과 `+8(weak 일치)`이 독립 `if` 2개다. 계약상
`recommended_element == weak_element`가 항상 성립하므로, 오늘 오행이 그 값과 같으면
두 가산이 **항상 동시 발동**해 보완 매칭일 점수가 `70+10+8+3=91`로 고정된다(의도는 단일 +10 → 83).
`WEAK_MATCH_BONUS`가 production에서 죽은 분기가 되고 전체 점수 분포가 +8 상향 편향된다.

**수정**: 가산/감산을 상호배타 분기로 바꾼다.

```python
# AS-IS
if today_element == recommended_element:
    score += RECOMMENDED_MATCH_BONUS
if weak_element and today_element == weak_element:
    score += WEAK_MATCH_BONUS
if strong_element and today_element != strong_element:
    score += BALANCE_BONUS
if strong_element and today_element == strong_element:
    score -= STRONG_MATCH_PENALTY
if limited:
    score -= LIMITED_INTERPRETATION_PENALTY

# TO-BE
if today_element == recommended_element:
    score += RECOMMENDED_MATCH_BONUS
elif weak_element and today_element == weak_element:
    score += WEAK_MATCH_BONUS

if strong_element and today_element == strong_element:
    score -= STRONG_MATCH_PENALTY
elif strong_element:
    score += BALANCE_BONUS

if limited:
    score -= LIMITED_INTERPRETATION_PENALTY
```

**수용 기준**:
- `recommended=weak=metal, strong=wood, today=metal` → score == **83** (91이 아님).
- 기존 `test_recommended_element_match_adds_bonus`(>=80), `test_strong_element_match_applies_penalty`(==65)는 그대로 통과해야 한다.
- (FIX-5에서 정확값 회귀 테스트를 추가한다.)

---

### FIX-2 (P1) — `@tool` 폴백에 `.invoke`/`langchain_core` 추가

**파일**: `src/tools/today_luck.py` (import 폴백, 현재 14~18행)

**문제**: `from langchain.tools import tool` 실패 시 폴백이 맨 함수를 반환해 `.invoke`가 없다.
`langchain_core`만 설치된 환경(또는 deps 미설치)에서 `calculate_today_luck.invoke(...)`가
`AttributeError`로 깨진다(모듈 주석의 "deps 설치 전에도 테스트 동작" 주장과 정반대).
다른 두 tool(`five_elements`, `lucky_factors`)은 `langchain_core` 폴백이 있어 비대칭.

**수정**: `five_elements.py`(8~20행)와 동일한 3단 폴백으로 맞춘다.

```python
try:
    from langchain.tools import tool
except ImportError:  # pragma: no cover
    try:
        from langchain_core.tools import tool
    except ImportError:  # pragma: no cover
        def tool(func):
            func.invoke = lambda tool_input: func(tool_input)
            return func
```

**수용 기준**: `langchain` 미설치 환경에서도 `tests/test_today_luck.py::test_langchain_tool_returns_json_string` 통과.

---

### FIX-3 (P2) — 비-문자열 `date` 입력 크래시 방지

**파일**: `src/tools/today_luck.py` (`_parse_date`, 현재 63~69행)

**문제**: `date.fromisoformat(value)`가 `ValueError`만 처리된다. `value`가 숫자/리스트면
`TypeError`가 나서 `{ok:false}` 대신 함수가 크래시한다(가드레일 2 위반).

**수정**:

```python
def _parse_date(value):
    if not value:
        return date.today()
    if not isinstance(value, str):
        raise ValueError("date는 YYYY-MM-DD 형식의 문자열이어야 합니다.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("date는 YYYY-MM-DD 형식이어야 합니다.") from exc
```

**수용 기준**: profile의 `date`가 비-문자열(예: `20260624` 정수)일 때 `{ok:false, error.code=="INVALID_DATE"}` 반환(크래시 없음). 해당 테스트 1개 추가.

---

### FIX-4 (P2) — `lucky_factors` 업스트림 실패 게이트 강화

**파일**: `src/tools/lucky_factors.py` (현재 대략 113~115행)

**문제**: `if payload.get("ok") is False:` 만으로 실패를 차단한다. `ok` 키 부재,
문자열 `"false"`, `ok:1`(truthy non-bool) 입력이 전부 통과해, 업스트림 오행 분석이
실제로는 실패했는데 잔여 `recommended_element`로 엉터리 추천을 반환할 수 있다(no-fabrication 위반).

**수정**: 엄격히 `ok:true`만 진행한다.

```python
# AS-IS
if payload.get("ok") is False:
    return _error_response("오행 분석 결과가 성공 상태가 아닙니다.")

# TO-BE
if payload.get("ok") is not True:
    return _error_response("오행 분석 결과가 성공 상태(ok:true)가 아닙니다.")
```

**수용 기준**: `{"ok":"false",...}`, `ok` 키 없는 입력, `{"ok":1,...}` 모두 `{ok:false, error.code=="INVALID_ELEMENT_ANALYSIS"}` 반환. 테스트 3종 추가. 정상 `{ok:true,data:{recommended_element}}`는 기존대로 동작.

---

### FIX-5 (P2) — 계약-충실 점수 테스트 추가

**파일**: `tests/test_today_luck.py`

**문제**: 모든 점수 테스트가 `recommended != weak`(계약상 불가능한 shape)를 쓰고 하한만 단언해,
실제 production 경로(`recommended == weak`)의 정확 점수를 전혀 커버하지 않는다. FIX-1 회귀를 못 잡는다.

**수정**: `recommended == weak`인 fixture로 고정 `target_date`에서 **정확 점수**를 단언하는 테스트 추가.

```python
def test_recommended_equals_weak_no_double_bonus():
    # 계약: analyze_five_elements 는 recommended_element == weak_element 로 출력한다.
    profile = json.dumps({
        "ok": True,
        "data": {"five_elements": {
            "counts": {"wood": 3, "fire": 2, "earth": 2, "metal": 0, "water": 1},
            "strong_element": "wood",
            "weak_element": "metal",
            "recommended_element": "metal",
        }},
    }, ensure_ascii=False)
    # 2026-06-24 -> today_element == metal (MVP 날짜 규칙)
    result = calculate_today_luck_payload(profile, target_date=date(2026, 6, 24))
    assert result["ok"] is True
    assert result["data"]["today_element"] == "metal"
    assert result["data"]["score"] == 83   # 70 + 10(recommended) + 3(balance), 이중가산 없음
```

**수용 기준**: 이 테스트가 FIX-1 적용 후 통과(83)하고, FIX-1 미적용 시 실패(91)해야 한다.

---

### FIX-6 (P3) — `date`를 data 레벨에서도 읽기

**파일**: `src/tools/today_luck.py` (`calculate_today_luck_payload`)

**문제**: `payload.get("date")`를 unwrap 전 바깥 봉투에서만 읽는다. 오케스트레이터 profile
(`{ok,data:{...}}`)에는 바깥에 `date`가 없어 항상 `date.today()`로 폴백하고, `data` 안에 넣은
`date`는 무시된다. "오늘의 운세"라 today() 자체는 정상이나, 날짜 주입(테스트/캐싱/재현)이 불가능하다.

**수정**: unwrap 후 `data` 레벨의 `date`도 인식한다(우선순위: 바깥 date → data.date → today).
`five_elements`를 꺼내는 기존 `_extract_five_elements`처럼 unwrap된 dict에서 `date`를 읽도록 보강.

**수용 기준**: profile의 `data.date`에 날짜를 넣으면 그 날짜로 계산된다(무시되지 않음). 테스트 1개 추가.
(주: 오케스트레이터가 날짜를 주입할지는 통합 리드가 별도 결정 — 이 FIX는 tool이 주입을 "받을 수 있게"만 한다.)

---

### FIX-7 (P3) — 입력 정규화 불일치 해소

**파일**: `src/tools/today_luck.py` (`_validate_element`, 87~95행)

**문제**: `today_luck`은 오행 값을 정확 일치로만 보는데, `lucky_factors`는 `.strip().lower()`로
정규화한다. 같은 five_elements 출력을 소비하는 두 tool이 `"Metal"`/`" water "` 같은 비-canonical
입력에 성공/실패가 갈린다.

**수정**: `_validate_element`에서 비교 전 `str(value).strip().lower()`로 정규화한 뒤 `ELEMENTS` 검사.

**수용 기준**: `"Metal"`, `" water "` 같은 입력이 `lucky_factors`와 동일하게 정상 처리된다. 테스트 1개 추가.

---

### FIX-8 (P3) — `five_elements._load_payload` fallthrough 차단

**파일**: `src/tools/five_elements.py` (`_load_payload`, 끝부분 105행 부근)

**문제**: `ok`가 `True`/`False` 어느 쪽도 아닐 때(키 부재 또는 truthy non-bool) 마지막 줄에서
payload 전체를 raw chart로 반환한다. `ok` 키가 있으나 `True`가 아닌 봉투를 chart로 오인할 수 있다.

**수정**: raw chart 관용은 **`ok` 키가 아예 없을 때만** 허용한다.

```python
# AS-IS (마지막 줄)
return payload, None

# TO-BE
if "ok" not in payload:
    return payload, None   # raw chart 관용 (test_raw_chart_data 의도)
return None, _json_error("INVALID_SAJU_CHART", "ok 값이 올바르지 않습니다.")
```

**수용 기준**: 기존 `test_raw_chart_data_is_supported_for_local_integration` 통과 유지. `{"ok": 1, "data": {...}}` 같은 입력은 `INVALID_SAJU_CHART` 반환. 테스트 1개 추가.

---

### FIX-9 (P3) — 기둥 카운트 루프 중복 제거

**파일**: `src/tools/five_elements.py` (REQUIRED/OPTIONAL 루프, 169~185행)

**문제**: 필수 기둥 루프와 선택 기둥 루프가 `required=`와 `None continue` 가드만 다른 거의 동일한 복붙이다.

**수정**: `(pillar_key, required)` 목록 하나로 합쳐 단일 루프로 카운트한다. 동작은 동일해야 한다.

```python
PILLARS = (("year_pillar", True), ("month_pillar", True), ("day_pillar", True), ("hour_pillar", False))
# ...
for key, required in PILLARS:
    pillar, error = _normalize_pillar(data, key, required=required)
    if error:
        return error
    if pillar is None:
        continue
    counts[HEAVENLY_STEM_ELEMENTS[pillar[0]]] += 1
    counts[EARTHLY_BRANCH_ELEMENTS[pillar[1]]] += 1
```

**수용 기준**: 기존 five_elements 테스트 전부 통과(동작 불변).

---

### FIX-10 (P3) — `_today_element_for_date` docstring 정정

**파일**: `src/tools/today_luck.py` (53~60행)

**문제**: `int(YYYYMMDD) % 5` 매핑은 월/연 경계에서 부드럽게 순환하지 않는데 docstring은
"stable day-by-day results"라 오해를 부른다(결정성·핸드오프 계약 자체는 만족).

**수정**: docstring을 "deterministic per-date MVP 매핑(같은 날짜=같은 결과). 인접일 균등 순환은 보장하지 않음"으로 정정. 로직은 그대로 둔다.

---

### FIX-11 (선택, P3) — `config.py` 단일 소스 수렴 리팩터

세 tool이 `ELEMENTS`/오행 한글 라벨/응답 헬퍼(`_success`/`_error`/`_json_ok`)를 각자 중복 정의한다.
`src/config.py`에 이미 `ELEMENTS`, `ELEMENT_KO`, `success`/`failure`/`success_json`/`failure_json`,
`ErrorCode`가 있다. 가능하면 세 tool이 이를 import해 사용하도록 수렴시킨다.

- **주의**: 큰 변경이므로 **모든 테스트가 계속 통과하는 선에서만** 진행한다.
- 에러 코드 문자열(`INVALID_ELEMENT_ANALYSIS`, `INVALID_PROFILE`, `INVALID_SAJU_CHART`, `INVALID_JSON`)이
  바뀌면 테스트가 깨지므로, `config.ErrorCode`에 누락된 코드를 추가하되 **기존 문자열 값을 유지**한다.
- 우선순위 낮음. P1~P3(FIX-1~10) 완료 후 시간이 남으면 진행한다.

---

## 4. 최종 검증 체크리스트

- [ ] `pytest -q` 전부 통과 (기존 64 + 신규 테스트).
- [ ] FIX-1: 계약 fixture에서 점수 == 83 (이중가산 제거 확인).
- [ ] FIX-2: `langchain` 미설치 환경에서도 today_luck `.invoke` 동작.
- [ ] FIX-3: 비-str `date` → 크래시 없이 `INVALID_DATE`.
- [ ] FIX-4: 헐거운 `ok` 입력 3종 → `INVALID_ELEMENT_ANALYSIS`.
- [ ] 출력 JSON 계약 key가 변경되지 않았다.
- [ ] (선택) 통합 스모크: `streamlit run app.py` 후 각 메뉴가 정상 응답.

## 5. 범위 밖 / 주의

- `src/tools/saju_chart.py`, `src/orchestrator.py`, `src/prompts.py`, `app.py`는 **이 작업 범위 밖**이다(통합 리드 최연준 담당). FIX-6의 "오케스트레이터 날짜 주입"은 별도 결정 사항이므로 tool 쪽만 준비한다.
- 점수 규칙의 숫자(70/10/8/3/5)와 색깔/아이템 매핑 같은 **명세 값은 바꾸지 않는다**(이중가산 구조만 수정).
- 이 파일들은 원래 각 팀원 담당이다. 통합 브랜치에서 수정하되, 결과를 각 담당자와 공유할 것.
