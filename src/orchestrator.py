"""오케스트레이터 — 담당: 최연준 (통합 리드).

역할:
- tool 레지스트리를 만든다. 내 도구(calculate_saju_chart)는 항상 포함하고,
  팀원 도구(analyze_five_elements/calculate_today_luck/recommend_lucky_factors)는
  파일이 존재하면 자동 등록, 없으면 graceful 하게 'pending' 으로 둔다.
- 최초 1회 사주 프로필을 만든다. (사주팔자 + 오행)
- 메뉴별로 '필요한 tool 만' 실행하고 LLM 입력 패키지를 조립한다.
- calculate_today_luck 가 쓰는 profile({user, saju_chart, five_elements})을 조립한다.

팀원 도구 연동 규약:
- 각 팀원 모듈은 `<함수명>_impl(json_str)->json_str` 순수 함수를 제공하면 가장 좋다.
  없으면 LangChain @tool 객체를 통해 호출을 시도한다.
"""
from __future__ import annotations

import importlib
import json

from . import config, prompts
from .tools.saju_chart import calculate_saju_chart_impl

# 팀원 도구의 (모듈 경로, 함수 이름) 명세
_TEAMMATE_SPECS = {
    config.TOOL_FIVE_ELEMENTS: ("src.tools.five_elements", "analyze_five_elements"),
    config.TOOL_TODAY_LUCK: ("src.tools.today_luck", "calculate_today_luck"),
    config.TOOL_LUCKY_FACTORS: ("src.tools.lucky_factors", "recommend_lucky_factors"),
}


def _load_teammate(module_name: str, func_name: str):
    """팀원 도구를 'json 문자열 -> json 문자열' 호출 가능 객체로 로드한다.

    아직 구현되지 않았으면 None 을 돌려준다(graceful).
    """
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return None

    # 1) 순수 impl 함수 우선 (<func_name>_impl)
    impl = getattr(module, func_name + "_impl", None)
    if callable(impl):
        return impl

    # 2) LangChain @tool 객체로 폴백
    obj = getattr(module, func_name, None)
    if obj is None:
        return None
    if hasattr(obj, "invoke") and hasattr(obj, "args"):
        arg_names = list(getattr(obj, "args", {}) or {})
        param = arg_names[0] if arg_names else None

        def _call(json_str: str, _obj=obj, _param=param):
            return _obj.invoke({_param: json_str} if _param else json_str)

        return _call
    if callable(obj):
        return obj
    return None


def default_registry() -> dict:
    """기본 tool 레지스트리. 내 도구 + 사용 가능한 팀원 도구."""
    registry = {config.TOOL_SAJU_CHART: calculate_saju_chart_impl}
    for name, (module_name, func_name) in _TEAMMATE_SPECS.items():
        loaded = _load_teammate(module_name, func_name)
        if loaded is not None:
            registry[name] = loaded
    return registry


def _safe_call(func, json_str: str) -> dict:
    """tool 호출을 감싸 어떤 예외도 에러 dict 로 변환한다."""
    try:
        raw = func(json_str)
    except Exception as exc:  # noqa: BLE001 - 통합 안정성 우선
        return config.failure(config.ErrorCode.MANSERYEOK_ERROR, f"tool 실행 실패: {exc}")
    if isinstance(raw, dict):
        return raw
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return config.failure(
            config.ErrorCode.MANSERYEOK_ERROR, "tool 결과를 해석할 수 없습니다."
        )


class Orchestrator:
    """메뉴 흐름을 조율한다. 레지스트리를 주입하면 테스트가 쉬워진다."""

    def __init__(self, registry: dict | None = None) -> None:
        self.registry = registry if registry is not None else default_registry()

    # --- 프로필 생성 (최초 1회) ----------------------------------------
    def build_profile(self, user_info_json: str) -> dict:
        """사주팔자 + 오행을 계산해 프로필을 만든다.

        반환: 성공 시 {"ok": true, "data": {user, saju_chart, five_elements,
        pending_tools}}, 실패 시 에러 dict.
        """
        saju_fn = self.registry.get(config.TOOL_SAJU_CHART)
        if saju_fn is None:
            return config.failure(
                config.ErrorCode.NOT_IMPLEMENTED, "만세력 계산 도구가 없습니다."
            )

        saju = _safe_call(saju_fn, user_info_json)
        if not saju.get("ok"):
            return saju  # 사주 계산 실패는 그대로 전달 (프로필 생성 불가)
        saju_data = saju["data"]

        # 사용자 표시 정보
        try:
            raw = json.loads(user_info_json)
        except (json.JSONDecodeError, TypeError):
            raw = {}
        user = {
            key: raw.get(key)
            for key in ("name", "gender", "birth_date", "birth_time", "calendar_type")
        }

        # 오행 분석 (팀원 도구; 없으면 pending)
        five_elements_data = None
        pending: list[str] = []
        fe_fn = self.registry.get(config.TOOL_FIVE_ELEMENTS)
        if fe_fn is not None:
            # 이윤서 계약: 입력은 calculate_saju_chart 의 전체 성공 JSON
            fe = _safe_call(fe_fn, config.to_json(saju))
            if fe.get("ok"):
                five_elements_data = fe["data"]
            else:
                pending.append(config.TOOL_FIVE_ELEMENTS)
        else:
            pending.append(config.TOOL_FIVE_ELEMENTS)

        return config.success(
            {
                "user": user,
                "saju_chart": saju_data,
                "five_elements": five_elements_data,
                "pending_tools": pending,
            }
        )

    # --- 메뉴 응답 ------------------------------------------------------
    def answer(
        self, intent: str, profile: dict, follow_up: str | None = None
    ) -> dict:
        """메뉴(intent)에 필요한 tool 만 실행하고 LLM 입력 패키지를 조립한다."""
        if intent not in config.MENU_REQUIRED_TOOLS:
            return config.failure(
                config.ErrorCode.NOT_IMPLEMENTED, f"지원하지 않는 메뉴입니다: {intent}"
            )
        if not profile.get("ok"):
            return config.failure(
                config.ErrorCode.INVALID_PROFILE, "유효한 사주 프로필이 필요합니다."
            )

        pdata = profile["data"]
        five_elements_data = pdata.get("five_elements")
        required = config.MENU_REQUIRED_TOOLS[intent]

        tool_results: dict = {}
        tools_run: list[str] = []
        pending: list[str] = []

        # 오행 분석은 프로필 생성 단계에서 이미 계산되었다.
        if config.TOOL_FIVE_ELEMENTS in required:
            if five_elements_data is not None:
                tool_results["five_elements"] = five_elements_data
            else:
                pending.append(config.TOOL_FIVE_ELEMENTS)

        # 오늘 운세 점수 (입력: 조립된 profile)
        if config.TOOL_TODAY_LUCK in required:
            fn = self.registry.get(config.TOOL_TODAY_LUCK)
            if fn is not None and five_elements_data is not None:
                res = _safe_call(fn, config.to_json(config.success(pdata)))
                tools_run.append(config.TOOL_TODAY_LUCK)
                if res.get("ok"):
                    tool_results["today_luck"] = res["data"]
                else:
                    pending.append(config.TOOL_TODAY_LUCK)
            else:
                pending.append(config.TOOL_TODAY_LUCK)

        # 행운 색깔/아이템 (입력: 오행 분석 성공 JSON)
        if config.TOOL_LUCKY_FACTORS in required:
            fn = self.registry.get(config.TOOL_LUCKY_FACTORS)
            if fn is not None and five_elements_data is not None:
                res = _safe_call(fn, config.to_json(config.success(five_elements_data)))
                tools_run.append(config.TOOL_LUCKY_FACTORS)
                if res.get("ok"):
                    tool_results["lucky_factors"] = res["data"]
                else:
                    pending.append(config.TOOL_LUCKY_FACTORS)
            else:
                pending.append(config.TOOL_LUCKY_FACTORS)

        package = prompts.build_llm_package(intent, pdata, tool_results)
        return config.success(
            {
                "intent": intent,
                "tool_results": tool_results,
                "llm_package": package,
                "tools_run": tools_run,
                "pending_tools": pending,
                "follow_up": follow_up,
            }
        )
