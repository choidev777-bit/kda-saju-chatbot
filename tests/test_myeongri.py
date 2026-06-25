import json
from datetime import date

from src.tools.myeongri import (
    HEAVENLY_STEMS,
    HIDDEN_STEMS,
    SIXTY_PILLARS,
    analyze_myeongri_payload,
    analyze_myeongri,
    calculate_iljin_payload,
    pillar_index,
    sipsin_name,
)


def run_tool(payload):
    if not isinstance(payload, str):
        payload = json.dumps(payload, ensure_ascii=False)
    if hasattr(analyze_myeongri, "invoke"):
        result = analyze_myeongri.invoke(payload)
    else:
        result = analyze_myeongri(payload)
    return json.loads(result)


def _chart(year, month, day, hour, precision="known"):
    return {
        "ok": True,
        "data": {
            "year_pillar": year,
            "month_pillar": month,
            "day_pillar": day,
            "hour_pillar": hour,
            "time_precision": precision,
        },
    }


# --- 십신 단위 규칙 ------------------------------------------------------
def test_sipsin_name_rules_for_byeong_day_master():
    # 일간 병(火,양)
    assert sipsin_name("병", "무") == "식신"  # 화생토 + 같은 양
    assert sipsin_name("병", "기") == "상관"  # 화생토 + 다른 음양
    assert sipsin_name("병", "신") == "정재"  # 화극금 + 다른 음양
    assert sipsin_name("병", "경") == "편재"  # 화극금 + 같은 양
    assert sipsin_name("병", "임") == "편관"  # 수극화 + 같은 양 (칠살)
    assert sipsin_name("병", "계") == "정관"  # 수극화 + 다른 음양
    assert sipsin_name("병", "갑") == "편인"  # 목생화 + 같은 양
    assert sipsin_name("병", "을") == "정인"  # 목생화 + 다른 음양
    assert sipsin_name("병", "병") == "비견"  # 동일 + 같은 양
    assert sipsin_name("병", "정") == "겁재"  # 동일 + 다른 음양


def test_hidden_stems_main_qi_is_last_entry():
    assert HIDDEN_STEMS["자"][-1] == "계"
    assert HIDDEN_STEMS["인"][-1] == "갑"
    assert HIDDEN_STEMS["오"][-1] == "정"
    assert HIDDEN_STEMS["술"][-1] == "무"
    # 천간 테이블 정합성
    assert HEAVENLY_STEMS["갑"] == ("wood", "양")
    assert HEAVENLY_STEMS["계"] == ("water", "음")


# --- 전체 사주 해석 ------------------------------------------------------
def test_full_chart_sipsin_jijanggan_and_body_strength():
    result = run_tool(_chart("무인", "을묘", "병진", "정사"))
    assert result["ok"] is True
    data = result["data"]

    assert data["il_gan"] == "병"
    assert data["il_gan_element"] == "fire"

    # 십신 (천간/지지, 지지는 지장간 정기 기준)
    assert data["sipsin"]["year"] == {"stem": "식신", "branch": "편인"}
    assert data["sipsin"]["month"] == {"stem": "정인", "branch": "정인"}
    assert data["sipsin"]["day"] == {"stem": "일간", "branch": "식신"}
    assert data["sipsin"]["hour"] == {"stem": "겁재", "branch": "비견"}

    # 지장간
    assert data["jijanggan"]["year"] == ["무", "병", "갑"]
    assert data["jijanggan"]["hour"] == ["무", "경", "병"]

    # 인성(목)·비겁(화)이 강해 신강
    assert data["body_strength"]["label"] == "신강"
    assert data["body_strength"]["score"] > 0


def test_yongsin_follows_body_strength_direction():
    # 신강 → 설기/극제(토금수)가 길, 본기(목화)는 불리
    result = run_tool(_chart("무인", "을묘", "병진", "정사"))
    yongsin = result["data"]["yongsin"]
    assert yongsin["body_strength"] == "신강"
    assert set(yongsin["favorable_elements"]) == {"earth", "metal", "water"}
    assert set(yongsin["unfavorable_elements"]) == {"wood", "fire"}


def test_metal_overload_is_weak_body():
    # 일간 갑(木)이 금(편관) 과다 → 신약, 생조(목수)가 길
    result = run_tool(_chart("경신", "경신", "갑신", "경오"))
    data = result["data"]
    assert data["body_strength"]["label"] == "신약"
    assert set(data["yongsin"]["favorable_elements"]) == {"wood", "water"}
    assert data["sipsin"]["year"]["stem"] == "편관"


def test_sinsal_dohwa_yeokma_hwagae_detected():
    result = run_tool(_chart("무인", "을묘", "병진", "정사"))
    sinsal = {item["name"] for item in result["data"]["sinsal"]}
    assert {"도화", "역마", "화개"} <= sinsal


def test_cheoneul_gwiin_detected_for_matching_branch():
    # 일간 갑 → 천을귀인 축/미. 연지 축 보유.
    result = run_tool(_chart("을축", "무인", "갑자", None, precision="unknown"))
    data = result["data"]
    names = {item["name"] for item in data["sinsal"]}
    assert "천을귀인" in names
    cheoneul = next(item for item in data["sinsal"] if item["name"] == "천을귀인")
    assert "year" in cheoneul["positions"]


# --- 시주 미상 / 에러 처리 ----------------------------------------------
def test_missing_hour_pillar_is_handled_with_note():
    result = run_tool(_chart("무인", "을묘", "병진", None, precision="unknown"))
    assert result["ok"] is True
    data = result["data"]
    assert data["sipsin"]["hour"] == {"stem": None, "branch": None}
    assert data["jijanggan"]["hour"] is None
    assert any("출생시간" in note for note in data["notes"])


def test_invalid_json_returns_error():
    result = run_tool("{not json")
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_JSON"


def test_missing_day_pillar_returns_error():
    result = run_tool(
        {"ok": True, "data": {"year_pillar": "무인", "month_pillar": "을묘", "hour_pillar": "정사"}}
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_SAJU_CHART"


def test_unknown_ganji_returns_error():
    result = run_tool(_chart("X인", "을묘", "병진", "정사"))
    assert result["ok"] is False
    assert result["error"]["code"] == "INVALID_SAJU_CHART"


def test_upstream_error_is_preserved():
    result = run_tool(
        {"ok": False, "error": {"code": "INVALID_INPUT", "message": "birth_date가 누락되었습니다."}}
    )
    assert result["ok"] is False
    assert result["error"]["code"] == "UPSTREAM_TOOL_ERROR"


def test_raw_chart_dict_without_ok_is_supported():
    result = run_tool(
        {"year_pillar": "무인", "month_pillar": "을묘", "day_pillar": "병진", "hour_pillar": "정사"}
    )
    assert result["ok"] is True
    assert result["data"]["il_gan"] == "병"


# --- 대운 / 일진 ---------------------------------------------------------
def _profile(gender="male"):
    return {
        "ok": True,
        "data": {
            "user": {"name": "테스트", "gender": gender},
            "saju_chart": {
                "year_pillar": "무인",
                "month_pillar": "을묘",
                "day_pillar": "병진",
                "hour_pillar": "정사",
                "time_precision": "known",
                "solar_date": {"year": 1998, "month": 3, "day": 12},
            },
        },
    }


def test_sixty_pillars_table_is_well_formed():
    assert len(SIXTY_PILLARS) == 60
    assert SIXTY_PILLARS[0] == "갑자"
    assert SIXTY_PILLARS[-1] == "계해"
    assert pillar_index("을묘") == 51


def test_daewoon_forward_for_yang_year_male():
    data = analyze_myeongri_payload(json.dumps(_profile("male"), ensure_ascii=False))["data"]
    daewoon = data["daewoon"]
    assert daewoon["available"] is True
    assert daewoon["direction"] == "순행"  # 무(양)년 + 남성 = 양남 순행
    assert daewoon["start_age"] >= 1
    assert len(daewoon["periods"]) == 8
    # 순행이면 월주(을묘=51) 다음 간지(병진=52)부터 시작
    assert daewoon["periods"][0]["ganji"] == "병진"
    assert daewoon["periods"][0]["stem_sipsin"] == "비견"


def test_daewoon_direction_flips_for_female():
    data = analyze_myeongri_payload(json.dumps(_profile("female"), ensure_ascii=False))["data"]
    assert data["daewoon"]["direction"] == "역행"  # 양년 + 여성 = 양녀 역행


def test_daewoon_requires_gender():
    data = analyze_myeongri_payload(json.dumps(_profile("unknown"), ensure_ascii=False))["data"]
    assert data["daewoon"]["available"] is False
    assert any("성별" in note for note in data["notes"])


def test_iljin_is_deterministic_from_birth_anchor():
    profile_json = json.dumps(_profile("male"), ensure_ascii=False)
    # 출생일 당일은 출생 일주(병진) 그대로
    same_day = calculate_iljin_payload(profile_json, target_date=date(1998, 3, 12))
    assert same_day["ok"] is True
    assert same_day["data"]["ganji"] == "병진"
    # 다음 날은 60갑자 다음(정사)
    next_day = calculate_iljin_payload(profile_json, target_date=date(1998, 3, 13))
    assert next_day["data"]["ganji"] == "정사"
    # 일간(병) 기준 십신이 채워진다
    assert "stem_sipsin" in next_day["data"]


def test_iljin_needs_day_pillar():
    result = calculate_iljin_payload(
        json.dumps({"ok": True, "data": {"year_pillar": "무인", "month_pillar": "을묘"}}, ensure_ascii=False)
    )
    assert result["ok"] is False
