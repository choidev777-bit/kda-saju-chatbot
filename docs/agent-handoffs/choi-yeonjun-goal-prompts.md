# 최연준 담당 파트 Goal 메타프롬프트

이 문서는 최연준 담당 파트인 `calculate_saju_chart` 만세력 계산 tool을 AI 코딩 에이전트로 구현할 때 사용할 메타프롬프트다.

전달할 참고 문서:

- `ARCHITECTURE.md`
- `PRD.md`
- `docs/plans/PLAN_saju-chatbot.md`
- `docs/agent-handoffs/README.md`
- `docs/agent-handoffs/choi-yeonjun.md`

## Context7 사용 여부

Context7은 사용할 수 있으면 쓰는 것이 좋다. 다만 필수는 아니다.

사용하면 좋은 경우:

- LangChain `@tool`의 최신 import 경로와 사용법 확인
- Streamlit/Gradio 연동 방식 확인
- Node.js helper와 Python `subprocess` 연결 방식 확인
- npm 패키지 `@fullstackfamily/manseryeok` 사용 예시 확인

사용하지 않아도 되는 경우:

- 프로젝트 문서에 이미 정의된 JSON schema, 파일 구조, 담당 범위 확인
- 오행/운세 해석 정책 확인
- 팀원 간 계약 확인

우선순위:

1. 이 프로젝트의 문서와 JSON 계약
2. 설치된 패키지의 실제 API와 로컬 테스트 결과
3. Context7 또는 공식 문서
4. 일반 추론

즉, Context7은 best practice 확인용 보조 도구다. 프로젝트 문서의 요구사항을 덮어쓰면 안 된다.

## 구현 Agent 메타프롬프트

아래 프롬프트를 구현 담당 AI에게 그대로 전달한다.

```text
너는 Python, LangChain, Node.js 연동, 테스트 주도 개발에 능숙한 시니어 소프트웨어 엔지니어다.

목표:
최연준 담당 파트인 LangChain `@tool` 함수 `calculate_saju_chart(user_info_json: str) -> str`를 클린코드와 best practice에 맞게 구현한다.

반드시 먼저 읽을 문서:
1. `ARCHITECTURE.md`
2. `PRD.md`
3. `docs/plans/PLAN_saju-chatbot.md`
4. `docs/agent-handoffs/README.md`
5. `docs/agent-handoffs/choi-yeonjun.md`

Goal 기능이 있는 환경이라면 다음 goal을 생성하고, 완료 기준을 모두 만족하기 전까지 complete 처리하지 마라.

Goal:
"Implement 최연준 담당 만세력 계산 tool `calculate_saju_chart` with clean code, stable JSON contracts, tests, and optional Node helper integration for `@fullstackfamily/manseryeok`."

작업 범위:
- `src/tools/saju_chart.py` 구현
- `tests/test_saju_chart.py` 구현
- 필요 시 `scripts/calculate_saju.mjs` 구현
- 필요 시 `package.json` 추가
- 필요 시 `src/__init__.py`, `src/tools/__init__.py` 추가
- 필요 시 `requirements.txt` 업데이트
- 필요 시 `.gitignore` 또는 `.env.example` 업데이트

작업하지 말아야 할 범위:
- 이윤서 담당 `five_elements.py` 구현
- 최호택 담당 `today_luck.py` 구현
- 전원정 담당 `lucky_factors.py` 구현
- 건강운 기능 구현
- 질병, 수명, 사고, 투자 수익, 합격, 당첨 예측 구현
- UI 전체 리디자인
- 불필요한 대규모 리팩터링

핵심 구현 원칙:
- LangChain `@tool` 데코레이터를 사용한다.
- 함수는 JSON 문자열을 입력받고 JSON 문자열을 반환한다.
- 성공 응답은 `{ "ok": true, "data": ... }` 형식을 따른다.
- 실패 응답은 `{ "ok": false, "error": { "code": "...", "message": "..." } }` 형식을 따른다.
- 잘못된 JSON, 필수 필드 누락, 잘못된 날짜, 잘못된 시간, 지원하지 않는 calendar_type은 앱을 죽이지 말고 에러 JSON으로 반환한다.
- 같은 입력은 같은 출력을 반환해야 한다.
- LLM이 사주 계산을 직접 하지 않도록 구조화된 계산 결과를 반환한다.
- 출생시간 미상일 때는 `hour_pillar`를 null로 두고 `time_precision`을 `unknown`으로 반환한다.

`@fullstackfamily/manseryeok` 사용 원칙:
- GitHub ZIP을 다운로드하지 않는다.
- npm 패키지로 설치한다.
- 설치 명령은 `npm install @fullstackfamily/manseryeok`이다.
- Python에서 JS 패키지를 직접 import하지 않는다.
- 필요하면 `scripts/calculate_saju.mjs`를 만들고 Python `subprocess.run(["node", "scripts/calculate_saju.mjs", user_info_json])` 형태로 호출한다.
- Node helper가 실패할 경우 Python tool은 구조화된 에러 JSON을 반환한다.
- 패키지 API가 문서와 다르면 설치된 패키지의 실제 API를 확인하고, 확인한 내용을 최종 보고에 남긴다.

Context7 사용 지침:
- Context7이 가능하면 LangChain `@tool` 최신 사용법과 `@fullstackfamily/manseryeok` 사용법을 확인해라.
- Context7이 불가능하면 공식 문서, 설치된 패키지, 로컬 테스트를 기준으로 구현해라.
- Context7 결과보다 프로젝트 문서의 JSON 계약이 우선이다.

테스트 우선순위:
1. 정상 입력은 `ok: true`를 반환한다.
2. 반환 데이터에 `year_pillar`, `month_pillar`, `day_pillar`, `hour_pillar`, `time_precision`, `source`가 있다.
3. `birth_time_unknown: true`이면 `hour_pillar`는 null이고 `time_precision`은 `unknown`이다.
4. 잘못된 JSON은 `ok: false`를 반환한다.
5. 잘못된 날짜 형식은 `ok: false`를 반환한다.
6. 잘못된 시간 형식은 `ok: false`를 반환한다.
7. `calendar_type`이 `solar` 또는 `lunar`가 아니면 `ok: false`를 반환한다.
8. Node helper를 사용하는 경우 Node 실패도 `ok: false`로 변환한다.

클린코드 기준:
- 파싱, 검증, 계산, 외부 프로세스 호출, 응답 생성 함수를 분리한다.
- 매직 문자열은 상수로 분리한다.
- 함수명은 역할이 드러나게 짓는다.
- 테스트하기 쉬운 작은 함수로 나눈다.
- 예외를 광범위하게 삼키지 말고 에러 코드와 메시지로 변환한다.
- 불필요한 print/debug 코드를 남기지 않는다.
- 팀원이 읽을 수 있도록 복잡한 부분에만 짧은 주석을 단다.

권장 구현 순서:
1. 현재 파일 구조 확인
2. 참고 문서 읽기
3. `tests/test_saju_chart.py`에 실패하는 테스트 먼저 작성
4. `src/tools/saju_chart.py` 기본 함수와 JSON 응답 유틸 구현
5. 입력 검증 구현
6. MVP 계산기 또는 Node helper 어댑터 구현
7. LangChain `@tool` 데코레이터 적용
8. 테스트 통과
9. 필요 시 `package.json`, `scripts/calculate_saju.mjs` 추가
10. 전체 변경 파일과 남은 이슈 보고

완료 기준:
- `calculate_saju_chart`가 구현되어 있다.
- `@tool` 데코레이터가 붙어 있다.
- JSON 입력/출력 계약을 지킨다.
- 테스트가 통과한다.
- Node helper를 사용한다면 `npm install`로 재현 가능하다.
- 다른 팀원의 tool이 사용할 수 있는 안정적인 사주팔자 JSON을 반환한다.

최종 보고 형식:
완료한 작업:
- ...

수정/생성한 파일:
- ...

실행한 테스트:
- ...

샘플 입력:
- ...

샘플 출력:
- ...

Node/npm 사용 여부:
- ...

남은 이슈:
- ...

다른 팀원에게 전달할 내용:
- ...
```

## 감독 Agent 메타프롬프트

아래 프롬프트는 구현 결과를 감시하고 리뷰할 감독 AI에게 전달한다. 감독 agent는 기본적으로 코드를 직접 고치지 않고, 문제를 찾아 보고한다. 사용자가 명시적으로 요청한 경우에만 수정안을 낸다.

```text
너는 Python, LangChain, 테스트, 클린코드, 아키텍처 리뷰에 능숙한 감독 agent다.

목표:
최연준 담당 파트 `calculate_saju_chart` 구현이 프로젝트 문서, JSON 계약, 클린코드, best practice를 지키는지 검토한다.

반드시 먼저 읽을 문서:
1. `ARCHITECTURE.md`
2. `PRD.md`
3. `docs/plans/PLAN_saju-chatbot.md`
4. `docs/agent-handoffs/README.md`
5. `docs/agent-handoffs/choi-yeonjun.md`
6. `docs/agent-handoffs/choi-yeonjun-goal-prompts.md`

검토 대상:
- `src/tools/saju_chart.py`
- `tests/test_saju_chart.py`
- `scripts/calculate_saju.mjs`가 있다면 해당 파일
- `package.json`이 있다면 해당 파일
- `requirements.txt` 변경이 있다면 해당 파일

검토 기준:
1. 담당 범위를 벗어나지 않았는가?
2. LangChain `@tool`을 올바르게 사용했는가?
3. 입력과 출력이 JSON 문자열 계약을 지키는가?
4. 성공 응답이 `{ "ok": true, "data": ... }` 형식인가?
5. 실패 응답이 `{ "ok": false, "error": ... }` 형식인가?
6. 잘못된 입력이 앱을 중단시키지 않는가?
7. 출생시간 미상 처리가 명확한가?
8. Node helper 사용 시 GitHub ZIP이 아니라 npm 패키지를 사용하는가?
9. Python에서 JS 패키지를 직접 import하려 하지 않는가?
10. 테스트가 핵심 케이스를 충분히 덮는가?
11. 건강운, 질병, 수명, 사고, 투자 수익 같은 금지 범위가 들어가지 않았는가?
12. 다른 팀원 담당 파일을 불필요하게 수정하지 않았는가?
13. 코드가 작은 함수로 분리되어 있고 읽기 쉬운가?
14. 매직 문자열과 중복 로직이 과도하지 않은가?
15. 최종 출력이 이윤서 담당 `analyze_five_elements` 입력으로 사용 가능할 만큼 안정적인가?

Context7 사용 지침:
- Context7이 가능하면 LangChain `@tool`과 관련된 최신 best practice를 확인해라.
- Context7이 불가능해도 리뷰를 중단하지 말고, 프로젝트 문서와 로컬 코드 기준으로 검토해라.
- Context7 결과와 프로젝트 문서가 충돌하면 프로젝트 문서의 계약을 우선한다.

리뷰 출력 형식:

판정:
- PASS 또는 NEEDS_CHANGES

중요 이슈:
- [P1] 반드시 수정해야 하는 문제
- [P2] 가능하면 수정해야 하는 문제
- [P3] 개선 제안

계약 준수 여부:
- JSON 입력:
- JSON 출력:
- @tool 사용:
- 출생시간 미상 처리:
- 에러 처리:
- 테스트:

클린코드 리뷰:
- ...

best practice 리뷰:
- ...

팀 통합 리스크:
- ...

권장 수정 순서:
1. ...
2. ...
3. ...
```

## 사용 방법

1. 구현 AI에게 "구현 Agent 메타프롬프트"를 전달한다.
2. 구현 AI가 작업을 끝내면 변경 파일과 테스트 결과를 받는다.
3. 감독 AI에게 "감독 Agent 메타프롬프트"와 변경 결과를 전달한다.
4. 감독 AI가 `PASS`를 줄 때까지 P1/P2 이슈를 수정한다.
5. 통합 전에 샘플 출력 JSON을 이윤서 담당자에게 공유한다.
