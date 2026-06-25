// 만세력 계산 Node helper.
//
// Python @tool(calculate_saju_chart) 가 subprocess 로 호출한다.
// 입력 JSON 은 두 경로 모두 지원한다(견고성):
//   1) 명령행 인자:   node scripts/calculate_saju.mjs '<user_info_json>'
//   2) 표준 입력(권장): echo '<user_info_json>' | node scripts/calculate_saju.mjs
// Windows 에서 인자에 든 따옴표가 깨질 수 있어 Python 쪽은 stdin 을 사용한다.
//
// 입력(JSON 문자열):
//   { "birth_date": "YYYY-MM-DD", "birth_time": "HH:MM"|null,
//     "calendar_type": "solar"|"lunar", "birth_time_unknown": bool,
//     "is_leap_month": bool(선택, 음력일 때만 의미) }
//
// 출력(stdout, JSON 문자열):
//   성공 { "ok": true,  "data": { ... } }
//   실패 { "ok": false, "error": { "code": "...", "message": "..." } }
//
// 어떤 경우에도 stdout 에는 JSON 한 덩어리만 출력하고 정상 종료(exit 0)한다.
// 라이브러리 자체가 import 단계에서 깨지는 등 치명적 상황에서만 비정상 종료된다.

import { readFileSync } from "node:fs";
import { calculateSaju, lunarToSolar } from "@fullstackfamily/manseryeok";

const SOURCE = "manseryeok-js (@fullstackfamily/manseryeok)";

// argv 가 없으면 stdin(fd 0) 에서 입력을 읽는다.
function readInput() {
  const fromArg = process.argv[2];
  if (fromArg != null && fromArg !== "") return fromArg;
  try {
    return readFileSync(0, "utf8").trim();
  } catch (_) {
    return "";
  }
}

const ok = (data) => ({ ok: true, data });
const err = (code, message) => ({ ok: false, error: { code, message } });

function mapLibError(e) {
  const name = e && e.name;
  const message = (e && e.message) || "만세력 계산 중 오류가 발생했습니다.";
  if (name === "OutOfRangeError") return err("NODE_OUT_OF_RANGE", message);
  if (name === "InvalidDateError") return err("NODE_INVALID_DATE", message);
  return err("NODE_CALC_ERROR", message);
}

function compute() {
  const raw = readInput();
  if (!raw) return err("NODE_NO_INPUT", "입력 JSON 이 없습니다.");

  let input;
  try {
    input = JSON.parse(raw);
  } catch (_) {
    return err("NODE_INVALID_JSON", "입력 JSON 파싱에 실패했습니다.");
  }

  const calendarType = input.calendar_type;
  const birthDate = String(input.birth_date || "");
  const birthTime = input.birth_time;
  const isLeapMonth = input.is_leap_month === true;
  // birth_time 이 없거나 미상 플래그가 있으면 시간 미상으로 처리한다.
  const timeUnknown = input.birth_time_unknown === true || !birthTime;

  const dateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(birthDate);
  if (!dateMatch) {
    return err("NODE_INVALID_DATE", "birth_date 는 YYYY-MM-DD 형식이어야 합니다.");
  }
  let year = parseInt(dateMatch[1], 10);
  let month = parseInt(dateMatch[2], 10);
  let day = parseInt(dateMatch[3], 10);

  // 음력 입력은 양력으로 변환한 뒤 계산한다.
  let lunarInput = null;
  if (calendarType === "lunar") {
    try {
      const conv = lunarToSolar(year, month, day, isLeapMonth);
      lunarInput = { year, month, day, is_leap_month: isLeapMonth };
      year = conv.solar.year;
      month = conv.solar.month;
      day = conv.solar.day;
    } catch (e) {
      return mapLibError(e);
    }
  }

  // 시간 파싱 (미상이면 생략 -> 라이브러리가 hourPillar 를 null 로 반환).
  let hour = null;
  let minute = 0;
  if (!timeUnknown) {
    const timeMatch = /^(\d{1,2}):(\d{2})$/.exec(String(birthTime));
    if (!timeMatch) {
      return err("NODE_INVALID_TIME", "birth_time 은 HH:MM 형식이어야 합니다.");
    }
    hour = parseInt(timeMatch[1], 10);
    minute = parseInt(timeMatch[2], 10);
  }

  let saju;
  try {
    saju = timeUnknown
      ? calculateSaju(year, month, day)
      : calculateSaju(year, month, day, hour, minute);
  } catch (e) {
    return mapLibError(e);
  }

  return ok({
    year_pillar: saju.yearPillar,
    month_pillar: saju.monthPillar,
    day_pillar: saju.dayPillar,
    hour_pillar: saju.hourPillar == null ? null : saju.hourPillar,
    year_pillar_hanja: saju.yearPillarHanja,
    month_pillar_hanja: saju.monthPillarHanja,
    day_pillar_hanja: saju.dayPillarHanja,
    hour_pillar_hanja: saju.hourPillarHanja == null ? null : saju.hourPillarHanja,
    time_precision: timeUnknown ? "unknown" : "known",
    calendar_type: calendarType,
    solar_date: { year, month, day },
    lunar_input: lunarInput,
    is_time_corrected: saju.isTimeCorrected === true,
    corrected_time: saju.correctedTime || null,
    source: SOURCE,
  });
}

try {
  process.stdout.write(JSON.stringify(compute()));
} catch (e) {
  process.stdout.write(
    JSON.stringify(err("NODE_UNEXPECTED", (e && e.message) || "알 수 없는 오류"))
  );
}
