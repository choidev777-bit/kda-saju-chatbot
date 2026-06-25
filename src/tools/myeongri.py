"""명리 해석 도구 — 십신·지장간·신강신약·용신·신살 (담당: 최연준 / 통합 리드).

설계 원칙(ARCHITECTURE 8 연장):
- LLM 은 명리 계산을 직접 하지 않는다. 이 도구가 사주팔자(간지)만으로
  결정적(deterministic)으로 십신/지장간/신강신약/용신/신살을 계산해 JSON 으로 준다.
- 만세력 라이브러리(@fullstackfamily/manseryeok)는 '간지·절기' 재료만 제공하고
  십신/대운/신살 같은 '해석 데이터'는 제공하지 않으므로, 그 해석 레이어를
  여기서 표준 명리 규칙(룩업 테이블)으로 구현한다.
- 대운/일진은 절기·임의 날짜 간지가 필요하므로 별도(Node helper) 단계에서 채운다.
  이 모듈은 출생 사주만으로 결정되는 '정적' 부분을 담당한다.

입력(JSON 문자열): calculate_saju_chart 의 성공 JSON({"ok":true,"data":{...}})
  또는 사주 chart dict 자체. 최소 year/month/day_pillar 가 필요하고 hour_pillar 는
  없으면(None) 시주를 제외하고 계산한다.
출력(JSON 문자열): {"ok":true,"data":{il_gan, sipsin, jijanggan, body_strength,
  yongsin, sinsal, notes}} 또는 표준 실패 JSON.

주의: 신강/신약과 용신은 유파에 따라 기준이 다른 '근사' 값이며, 그 사실을 결과에
명시한다. 십신·지장간·신살은 표준 룩업으로 비교적 명확하다.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

try:  # 프로젝트 표준: langchain.tools 우선, 신버전 폴백, 미설치 시 더미 데코레이터
    from langchain.tools import tool
except Exception:  # pragma: no cover - 환경별 import 차이
    try:
        from langchain_core.tools import tool
    except Exception:  # pragma: no cover

        def tool(func):  # type: ignore[no-redef]
            func.invoke = lambda tool_input: func(tool_input)
            return func


# --- 기본 간지 테이블 ----------------------------------------------------
# 천간 -> (오행 영문키, 음양)
HEAVENLY_STEMS: dict[str, tuple[str, str]] = {
    "갑": ("wood", "양"),
    "을": ("wood", "음"),
    "병": ("fire", "양"),
    "정": ("fire", "음"),
    "무": ("earth", "양"),
    "기": ("earth", "음"),
    "경": ("metal", "양"),
    "신": ("metal", "음"),
    "임": ("water", "양"),
    "계": ("water", "음"),
}

# 지지 -> 오행 영문키 (라이브러리 v1.0.6 의 정정된 12지지 오행과 동일)
EARTHLY_BRANCHES: dict[str, str] = {
    "자": "water",
    "축": "earth",
    "인": "wood",
    "묘": "wood",
    "진": "earth",
    "사": "fire",
    "오": "fire",
    "미": "earth",
    "신": "metal",
    "유": "metal",
    "술": "earth",
    "해": "water",
}

# 지지 -> 지장간(여기, 중기, 정기 순). 정기(본기)는 리스트의 마지막 원소.
HIDDEN_STEMS: dict[str, list[str]] = {
    "자": ["임", "계"],
    "축": ["계", "신", "기"],
    "인": ["무", "병", "갑"],
    "묘": ["갑", "을"],
    "진": ["을", "계", "무"],
    "사": ["무", "경", "병"],
    "오": ["병", "기", "정"],
    "미": ["정", "을", "기"],
    "신": ["무", "임", "경"],
    "유": ["경", "신"],
    "술": ["신", "정", "무"],
    "해": ["무", "갑", "임"],
}

ELEMENT_ORDER = ("wood", "fire", "earth", "metal", "water")
ELEMENT_KO = {"wood": "목", "fire": "화", "earth": "토", "metal": "금", "water": "수"}

# 오행 상생/상극 순환
GENERATES = {"wood": "fire", "fire": "earth", "earth": "metal", "metal": "water", "water": "wood"}
CONTROLS = {"wood": "earth", "earth": "water", "water": "fire", "fire": "metal", "metal": "wood"}
GENERATED_BY = {v: k for k, v in GENERATES.items()}  # key 를 생하는 오행
CONTROLLED_BY = {v: k for k, v in CONTROLS.items()}  # key 를 극하는 오행

# 십신 그룹 -> (같은 음양 이름, 다른 음양 이름)
_SIPSIN_NAMES = {
    "비겁": ("비견", "겁재"),
    "식상": ("식신", "상관"),
    "재성": ("편재", "정재"),
    "관성": ("편관", "정관"),
    "인성": ("편인", "정인"),
}

PILLAR_KEYS = ("year", "month", "day", "hour")
PILLAR_KO = {"year": "연주", "month": "월주", "day": "일주", "hour": "시주"}


# --- 응답 유틸 -----------------------------------------------------------
def _ok(data: dict[str, Any]) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _error(code: str, message: str) -> str:
    return json.dumps({"ok": False, "error": {"code": code, "message": message}}, ensure_ascii=False)


def _load_chart(raw_json: str) -> tuple[dict[str, Any] | None, str | None]:
    """calculate_saju_chart 성공 JSON 또는 chart dict 를 받아 chart data 를 돌려준다."""
    try:
        payload = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError):
        return None, _error("INVALID_JSON", "입력값은 JSON 문자열이어야 합니다.")
    if not isinstance(payload, dict):
        return None, _error("INVALID_INPUT", "입력 JSON은 객체 형식이어야 합니다.")
    if payload.get("ok") is False:
        upstream = payload.get("error")
        message = (upstream or {}).get("message") if isinstance(upstream, dict) else None
        return None, _error("UPSTREAM_TOOL_ERROR", message or "이전 tool 결과가 실패 상태입니다.")
    if payload.get("ok") is True:
        data = payload.get("data")
        if not isinstance(data, dict):
            return None, _error("INVALID_SAJU_CHART", "data 객체가 누락되었습니다.")
        return data, None
    if "ok" not in payload:
        return payload, None
    return None, _error("INVALID_SAJU_CHART", "ok 값은 true 또는 false 여야 합니다.")


def _split_pillar(value: Any, key: str, *, required: bool) -> tuple[tuple[str, str] | None, str | None]:
    """간지 2글자를 (천간, 지지)로 분리·검증한다."""
    if value in (None, "") and not required:
        return None, None
    if value in (None, "") and required:
        return None, _error("INVALID_SAJU_CHART", f"{key}가 누락되었습니다.")
    if not isinstance(value, str):
        return None, _error("INVALID_SAJU_CHART", f"{key}는 문자열이어야 합니다.")
    pillar = value.strip()
    if len(pillar) != 2:
        return None, _error("INVALID_SAJU_CHART", f"{key}는 두 글자 간지여야 합니다: {pillar}")
    stem, branch = pillar[0], pillar[1]
    if stem not in HEAVENLY_STEMS:
        return None, _error("INVALID_SAJU_CHART", f"알 수 없는 천간입니다: {stem}")
    if branch not in EARTHLY_BRANCHES:
        return None, _error("INVALID_SAJU_CHART", f"알 수 없는 지지입니다: {branch}")
    return (stem, branch), None


# --- 십신 계산 -----------------------------------------------------------
def sipsin_group(day_element: str, target_element: str) -> str:
    """일간 오행 대비 대상 오행의 십신 그룹(비겁/식상/재성/관성/인성)."""
    if target_element == day_element:
        return "비겁"
    if GENERATES[day_element] == target_element:
        return "식상"
    if CONTROLS[day_element] == target_element:
        return "재성"
    if CONTROLS[target_element] == day_element:
        return "관성"
    return "인성"  # GENERATES[target] == day_element


def sipsin_name(day_stem: str, target_stem: str) -> str:
    """일간(천간) 대비 대상 천간의 십신 이름(예: 정관, 편재)."""
    day_el, day_yy = HEAVENLY_STEMS[day_stem]
    tgt_el, tgt_yy = HEAVENLY_STEMS[target_stem]
    group = sipsin_group(day_el, tgt_el)
    same = tgt_yy == day_yy
    return _SIPSIN_NAMES[group][0 if same else 1]


def _group_element(day_element: str, group: str) -> str:
    """십신 그룹이 가리키는 오행(일간 기준)."""
    return {
        "비겁": day_element,
        "식상": GENERATES[day_element],
        "재성": CONTROLS[day_element],
        "관성": CONTROLLED_BY[day_element],
        "인성": GENERATED_BY[day_element],
    }[group]


# --- 신살 테이블 ---------------------------------------------------------
# 천을귀인(일간 -> 길지): 연해자평 표준표
CHEONEUL_GWIIN = {
    "갑": ["축", "미"], "무": ["축", "미"], "경": ["축", "미"],
    "을": ["자", "신"], "기": ["자", "신"],
    "병": ["해", "유"], "정": ["해", "유"],
    "임": ["묘", "사"], "계": ["묘", "사"],
    "신": ["인", "오"],
}
# 양인(양간 -> 지지)
YANGIN = {"갑": "묘", "병": "오", "무": "오", "경": "유", "임": "자"}
# 문창귀인(일간 -> 지지)
MUNCHANG = {
    "갑": "사", "을": "오", "병": "신", "정": "유", "무": "신",
    "기": "유", "경": "해", "신": "자", "임": "인", "계": "묘",
}
# 삼합 그룹(지지 -> 그룹 오행키). 도화/역마/화개는 이 그룹으로 결정된다.
_SAMHAP_GROUP = {
    "신": "water", "자": "water", "진": "water",
    "인": "fire", "오": "fire", "술": "fire",
    "사": "metal", "유": "metal", "축": "metal",
    "해": "wood", "묘": "wood", "미": "wood",
}
DOHWA = {"water": "유", "fire": "묘", "metal": "오", "wood": "자"}
YEOKMA = {"water": "인", "fire": "신", "metal": "해", "wood": "사"}
HWAGAE = {"water": "진", "fire": "술", "metal": "축", "wood": "미"}
# 괴강/백호(간지 자체)
GWAEGANG = {"경진", "경술", "임진", "무술"}
BAEKHO = {"갑진", "을미", "병술", "정축", "무진", "임술", "계축"}


def _compute_sinsal(pillars: dict[str, tuple[str, str]], day_stem: str) -> list[dict[str, Any]]:
    """사주의 신살/귀인을 표준 룩업으로 찾는다."""
    # 위치별 지지/간지
    branches = {key: gz[1] for key, gz in pillars.items()}
    ganji = {key: gz[0] + gz[1] for key, gz in pillars.items()}
    found: list[dict[str, Any]] = []

    def add(name: str, target_branch: str) -> None:
        positions = [key for key, br in branches.items() if br == target_branch]
        if positions:
            found.append({"name": name, "branch": target_branch, "positions": positions})

    # 천을귀인
    for target in CHEONEUL_GWIIN.get(day_stem, []):
        add("천을귀인", target)
    # 양인
    if day_stem in YANGIN:
        add("양인", YANGIN[day_stem])
    # 문창귀인
    if day_stem in MUNCHANG:
        add("문창귀인", MUNCHANG[day_stem])

    # 도화/역마/화개: 연지·일지를 기준으로 삼합 그룹을 잡고 대상 지지를 찾는다.
    anchors = [branches.get("year"), branches.get("day")]
    seen: set[tuple[str, str]] = set()
    for anchor in anchors:
        if not anchor:
            continue
        group = _SAMHAP_GROUP.get(anchor)
        if not group:
            continue
        for name, table in (("도화", DOHWA), ("역마", YEOKMA), ("화개", HWAGAE)):
            target = table[group]
            key = (name, target)
            if key in seen:
                continue
            positions = [k for k, br in branches.items() if br == target]
            if positions:
                found.append({"name": name, "branch": target, "positions": positions})
                seen.add(key)

    # 괴강/백호: 간지 자체로 판정
    for key, gz in ganji.items():
        if gz in GWAEGANG:
            found.append({"name": "괴강", "ganji": gz, "positions": [key]})
        if gz in BAEKHO:
            found.append({"name": "백호", "ganji": gz, "positions": [key]})

    return found


# --- 신강/신약 + 용신(억부 근사) ----------------------------------------
_SUPPORT_GROUPS = {"비겁", "인성"}
_DRAIN_GROUPS = {"식상", "재성", "관성"}
# 위치별 가중치. 월지(월령)를 가장 무겁게 본다. 일간(천간)은 '나' 자신이라 제외.
_WEIGHTS = {
    ("year", "stem"): 1, ("year", "branch"): 2,
    ("month", "stem"): 1, ("month", "branch"): 3,
    ("day", "branch"): 2,
    ("hour", "stem"): 1, ("hour", "branch"): 2,
}


def _body_strength(pillars: dict[str, tuple[str, str]], day_element: str) -> dict[str, Any]:
    """신강/신약을 가중 점수로 근사한다(유파별 차이가 있는 근사값)."""
    score = 0
    support = 0
    drain = 0
    for key, gz in pillars.items():
        stem, branch = gz
        # 천간 (일간 자신은 제외)
        if key != "day":
            weight = _WEIGHTS.get((key, "stem"), 0)
            group = sipsin_group(day_element, HEAVENLY_STEMS[stem][0])
            if group in _SUPPORT_GROUPS:
                score += weight
                support += weight
            elif group in _DRAIN_GROUPS:
                score -= weight
                drain += weight
        # 지지(정기 기준)
        weight = _WEIGHTS.get((key, "branch"), 0)
        jeonggi = HIDDEN_STEMS[branch][-1]
        group = sipsin_group(day_element, HEAVENLY_STEMS[jeonggi][0])
        if group in _SUPPORT_GROUPS:
            score += weight
            support += weight
        elif group in _DRAIN_GROUPS:
            score -= weight
            drain += weight

    if score >= 2:
        label = "신강"
    elif score <= -2:
        label = "신약"
    else:
        label = "중화"
    return {
        "label": label,
        "score": score,
        "support_weight": support,
        "drain_weight": drain,
        "method": "weighted_approx",
        "note": "월령·통근을 가중한 근사값이며 유파에 따라 다를 수 있습니다.",
    }


def _yongsin(day_element: str, body_label: str) -> dict[str, Any]:
    """억부 기준 용신(근사): 강하면 설기/극제 오행, 약하면 생조 오행을 길하게 본다."""
    support = sorted({day_element, GENERATED_BY[day_element]}, key=ELEMENT_ORDER.index)
    drain = sorted(
        {GENERATES[day_element], CONTROLS[day_element], CONTROLLED_BY[day_element]},
        key=ELEMENT_ORDER.index,
    )
    if body_label == "신강":
        favorable, unfavorable = drain, support
    elif body_label == "신약":
        favorable, unfavorable = support, drain
    else:  # 중화
        favorable, unfavorable = [], []
    return {
        "method": "eokbu_approx",
        "body_strength": body_label,
        "favorable_elements": favorable,
        "favorable_elements_ko": [ELEMENT_KO[e] for e in favorable],
        "unfavorable_elements": unfavorable,
        "note": "억부 기준 근사 용신이며, 조후·격국 등 유파에 따라 달라질 수 있습니다.",
    }


# --- 60갑자 / 대운 / 일진 (순수 파이썬) ---------------------------------
# 만세력 라이브러리의 절기 데이터는 2020~2030년만 지원하므로, 대운/일진은
# 라이브러리에 의존하지 않고 60갑자 순환과 평균 절기일로 직접 계산한다.
HEAVENLY_STEM_ORDER = "갑을병정무기경신임계"
EARTHLY_BRANCH_ORDER = "자축인묘진사오미신유술해"
SIXTY_PILLARS = [
    HEAVENLY_STEM_ORDER[i % 10] + EARTHLY_BRANCH_ORDER[i % 12] for i in range(60)
]
_PILLAR_INDEX = {ganji: i for i, ganji in enumerate(SIXTY_PILLARS)}

# 12 절(節) 평균 양력일(월, 일). 각 사주월의 시작 절기. 연도별 ±1일 오차 범위라
# 대운수(일수/3) 산정에는 충분한 근사값이다.
_JEOL_APPROX = [
    (2, 4),   # 입춘 (인월)
    (3, 6),   # 경칩 (묘월)
    (4, 5),   # 청명 (진월)
    (5, 6),   # 입하 (사월)
    (6, 6),   # 망종 (오월)
    (7, 7),   # 소서 (미월)
    (8, 8),   # 입추 (신월)
    (9, 8),   # 백로 (유월)
    (10, 8),  # 한로 (술월)
    (11, 7),  # 입동 (해월)
    (12, 7),  # 대설 (자월)
    (1, 6),   # 소한 (축월)
]


def pillar_index(ganji: str | None) -> int | None:
    """60갑자에서 간지의 인덱스(0~59). 없으면 None."""
    if not ganji:
        return None
    return _PILLAR_INDEX.get(ganji.strip())


def _parse_solar_date(value: Any) -> date | None:
    """saju_chart.solar_date({year,month,day}) 또는 'YYYY-MM-DD' 를 date 로."""
    if isinstance(value, dict):
        try:
            return date(int(value["year"]), int(value["month"]), int(value["day"]))
        except (KeyError, ValueError, TypeError):
            return None
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _jeol_candidates(birth: date) -> list[date]:
    """출생 연도 전후의 12절 평균일을 정렬해 돌려준다(경계 탐색용)."""
    candidates: list[date] = []
    for year in (birth.year - 1, birth.year, birth.year + 1):
        for month, day in _JEOL_APPROX:
            try:
                candidates.append(date(year, month, day))
            except ValueError:  # 윤일 등 비정상 조합 방어
                continue
    return sorted(candidates)


def _daewoon_start_age(birth: date, forward: bool) -> tuple[int, int]:
    """대운수(시작 나이)와 경계까지의 일수를 근사 계산한다.

    순행이면 다음 절(節)까지, 역행이면 직전 절까지의 일수를 3으로 나눈다.
    """
    candidates = _jeol_candidates(birth)
    if forward:
        nxt = next((d for d in candidates if d > birth), None)
        days = (nxt - birth).days if nxt else 0
    else:
        prev = next((d for d in reversed(candidates) if d <= birth), None)
        days = (birth - prev).days if prev else 0
    start_age = max(1, round(days / 3))
    return start_age, days


def calculate_daewoon(
    year_stem: str,
    month_pillar: str,
    gender: str | None,
    birth_solar_date: Any,
    count: int = 8,
) -> dict[str, Any]:
    """대운(방향·대운수·간지 목록)을 계산한다. 불가하면 ok=False dict."""
    birth = _parse_solar_date(birth_solar_date)
    if birth is None:
        return {"available": False, "reason": "출생 양력일 정보가 없어 대운을 계산할 수 없습니다."}

    normalized_gender = (gender or "").strip().lower()
    if normalized_gender not in ("male", "female"):
        return {"available": False, "reason": "성별 정보가 있어야 대운 방향을 정할 수 있습니다."}

    month_index = pillar_index(month_pillar)
    if month_index is None or year_stem not in HEAVENLY_STEMS:
        return {"available": False, "reason": "월주/연간 간지가 올바르지 않습니다."}

    year_yy = HEAVENLY_STEMS[year_stem][1]
    # 양남음녀 순행, 음남양녀 역행
    forward = (year_yy == "양") == (normalized_gender == "male")
    start_age, days = _daewoon_start_age(birth, forward)

    day_stem = None  # 대운 간지의 십신은 일간 기준으로 계산
    periods: list[dict[str, Any]] = []
    for step in range(1, count + 1):
        idx = (month_index + step) % 60 if forward else (month_index - step) % 60
        ganji = SIXTY_PILLARS[idx]
        age_from = start_age + (step - 1) * 10
        periods.append(
            {
                "sequence": step,
                "age_from": age_from,
                "age_to": age_from + 9,
                "ganji": ganji,
                "stem": ganji[0],
                "branch": ganji[1],
            }
        )

    return {
        "available": True,
        "direction": "순행" if forward else "역행",
        "start_age": start_age,
        "start_age_basis_days": days,
        "periods": periods,
        "method": "approx_jeolgi",
        "note": "대운수는 평균 절기일 기준 근사이며, 정밀 절기 시각과 1년 내외 차이가 날 수 있습니다.",
    }


def _attach_daewoon_sipsin(daewoon: dict[str, Any], day_stem: str) -> None:
    """대운 간지에 일간 기준 십신을 채워 넣는다."""
    if not daewoon.get("available"):
        return
    for period in daewoon.get("periods", []):
        branch_jeonggi = HIDDEN_STEMS[period["branch"]][-1]
        period["stem_sipsin"] = sipsin_name(day_stem, period["stem"])
        period["branch_sipsin"] = sipsin_name(day_stem, branch_jeonggi)


def iljin_for_date(
    birth_day_pillar: str, birth_solar_date: Any, target: date, day_stem: str | None = None
) -> dict[str, Any] | None:
    """출생 일주를 기준점으로 임의 날짜의 일진(간지)을 60갑자 순환으로 계산한다."""
    birth = _parse_solar_date(birth_solar_date)
    base_index = pillar_index(birth_day_pillar)
    if birth is None or base_index is None:
        return None
    offset = (target - birth).days
    ganji = SIXTY_PILLARS[(base_index + offset) % 60]
    stem, branch = ganji[0], ganji[1]
    result: dict[str, Any] = {
        "date": target.isoformat(),
        "ganji": ganji,
        "stem": stem,
        "branch": branch,
        "stem_element": HEAVENLY_STEMS[stem][0],
        "stem_element_ko": ELEMENT_KO[HEAVENLY_STEMS[stem][0]],
        "branch_element": EARTHLY_BRANCHES[branch],
        "branch_element_ko": ELEMENT_KO[EARTHLY_BRANCHES[branch]],
    }
    if day_stem:
        result["stem_sipsin"] = sipsin_name(day_stem, stem)
        result["branch_sipsin"] = sipsin_name(day_stem, HIDDEN_STEMS[branch][-1])
    return result


# --- 메인 계산 -----------------------------------------------------------
def analyze_myeongri_payload(saju_chart_json: str) -> dict[str, Any]:
    """순수 계산 본체. dict({"ok":...}) 를 돌려준다(테스트/오케스트레이터용)."""
    container, error = _load_chart(saju_chart_json)
    if error:
        return json.loads(error)
    assert container is not None
    # 입력이 전체 프로필({user, saju_chart, ...})이면 chart 를 꺼내고 성별을 읽는다.
    if isinstance(container.get("saju_chart"), dict):
        chart = container["saju_chart"]
        user = container.get("user") or {}
    else:
        chart = container
        user = {}

    pillars: dict[str, tuple[str, str]] = {}
    for key, required in (("year", True), ("month", True), ("day", True), ("hour", False)):
        gz, err = _split_pillar(chart.get(f"{key}_pillar"), f"{key}_pillar", required=required)
        if err:
            return json.loads(err)
        if gz is not None:
            pillars[key] = gz

    day_stem, _day_branch = pillars["day"]
    day_element, day_yy = HEAVENLY_STEMS[day_stem]

    notes: list[str] = []
    if "hour" not in pillars:
        notes.append("출생시간 정보가 없어 시주를 제외하고 해석했습니다.")

    # 십신 (천간/지지). 일간 천간은 '일간'(아신)으로 표기.
    sipsin: dict[str, dict[str, str | None]] = {}
    jijanggan: dict[str, list[str] | None] = {}
    for key in PILLAR_KEYS:
        gz = pillars.get(key)
        if gz is None:
            sipsin[key] = {"stem": None, "branch": None}
            jijanggan[key] = None
            continue
        stem, branch = gz
        stem_sipsin = "일간" if key == "day" else sipsin_name(day_stem, stem)
        branch_jeonggi = HIDDEN_STEMS[branch][-1]
        sipsin[key] = {
            "stem": stem_sipsin,
            "branch": sipsin_name(day_stem, branch_jeonggi),
        }
        jijanggan[key] = list(HIDDEN_STEMS[branch])

    body = _body_strength(pillars, day_element)
    yongsin = _yongsin(day_element, body["label"])
    sinsal = _compute_sinsal(pillars, day_stem)

    daewoon = calculate_daewoon(
        year_stem=pillars["year"][0],
        month_pillar=pillars["month"][0] + pillars["month"][1],
        gender=user.get("gender"),
        birth_solar_date=chart.get("solar_date"),
    )
    _attach_daewoon_sipsin(daewoon, day_stem)
    if not daewoon.get("available") and daewoon.get("reason"):
        notes.append(daewoon["reason"])

    return {
        "ok": True,
        "data": {
            "il_gan": day_stem,
            "il_gan_element": day_element,
            "il_gan_element_ko": ELEMENT_KO[day_element],
            "il_gan_yinyang": day_yy,
            "sipsin": sipsin,
            "jijanggan": jijanggan,
            "body_strength": body,
            "yongsin": yongsin,
            "sinsal": sinsal,
            "daewoon": daewoon,
            "notes": notes,
        },
    }


def analyze_myeongri_impl(saju_chart_json: str) -> str:
    """`analyze_myeongri` 의 순수 함수 본체 (JSON 문자열 입출력)."""
    result = analyze_myeongri_payload(saju_chart_json)
    return json.dumps(result, ensure_ascii=False)


@tool
def analyze_myeongri(saju_chart_json: str) -> str:
    """사주팔자(간지)로부터 십신·지장간·신강신약·용신·신살을 결정적으로 계산한다.

    입력(JSON 문자열): calculate_saju_chart 성공 JSON 또는 사주 chart dict.
    출력(JSON 문자열): {"ok":true,"data":{il_gan, sipsin, jijanggan,
        body_strength, yongsin, sinsal, notes}} 또는 표준 실패 JSON.
    대운은 입력에 성별·출생 양력일이 포함되면 함께 계산한다. 일진(오늘)은
    날짜 의존이므로 calculate_iljin 으로 분리한다.
    """
    return analyze_myeongri_impl(saju_chart_json)


# --- 일진 (오늘의 간지) --------------------------------------------------
def calculate_iljin_payload(profile_json: str, target_date: date | None = None) -> dict[str, Any]:
    """프로필(또는 chart)과 대상 날짜로 일진을 계산한다. dict 반환."""
    container, error = _load_chart(profile_json)
    if error:
        return json.loads(error)
    assert container is not None
    if isinstance(container.get("saju_chart"), dict):
        chart = container["saju_chart"]
    else:
        chart = container

    day_pillar = chart.get("day_pillar")
    if not isinstance(day_pillar, str) or pillar_index(day_pillar) is None:
        return {
            "ok": False,
            "error": {"code": "INVALID_SAJU_CHART", "message": "일주(day_pillar) 정보가 필요합니다."},
        }

    target = target_date or date.today()
    iljin = iljin_for_date(day_pillar, chart.get("solar_date"), target, day_stem=day_pillar[0])
    if iljin is None:
        return {
            "ok": False,
            "error": {"code": "INVALID_SAJU_CHART", "message": "출생 양력일 정보가 없어 일진을 계산할 수 없습니다."},
        }
    return {"ok": True, "data": iljin}


def calculate_iljin_impl(profile_json: str) -> str:
    """`calculate_iljin` 의 순수 함수 본체 (JSON 문자열 입출력)."""
    return json.dumps(calculate_iljin_payload(profile_json), ensure_ascii=False)


@tool
def calculate_iljin(profile_json: str) -> str:
    """사용자 출생 일주를 기준점으로 오늘(또는 대상 날짜)의 일진 간지를 계산한다.

    입력(JSON 문자열): 프로필 성공 JSON 또는 day_pillar/solar_date 를 가진 chart.
    출력(JSON 문자열): {"ok":true,"data":{date, ganji, stem, branch, *_element,
        stem_sipsin, branch_sipsin}} 또는 표준 실패 JSON.
    """
    return calculate_iljin_impl(profile_json)


__all__ = [
    "HEAVENLY_STEMS",
    "EARTHLY_BRANCHES",
    "HIDDEN_STEMS",
    "SIXTY_PILLARS",
    "analyze_myeongri",
    "analyze_myeongri_impl",
    "analyze_myeongri_payload",
    "calculate_daewoon",
    "calculate_iljin",
    "calculate_iljin_impl",
    "calculate_iljin_payload",
    "iljin_for_date",
    "pillar_index",
    "sipsin_name",
    "sipsin_group",
]
