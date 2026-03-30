# 금시세 일일 업데이트 프로젝트

한국금거래소(koreagoldx.co.kr) 금시세 페이지와 동일한 구조의 **공개 API**를 호출해 금(Au) 3.75g 기준 시세를 수집하고, 이를 Supabase에 저장한 뒤 웹사이트에서 그래프·표로 보여주는 예제와 [PRD](./PRD.md)를 포함합니다.

## 구성

| 파일 | 설명 |
|------|------|
| [PRD.md](./PRD.md) | 제품 요구사항(기능·데이터·아키텍처 초안) |
| [requirements.txt](./requirements.txt) | Python 의존성 |
| [scripts/fetch_gold_to_excel.py](./scripts/fetch_gold_to_excel.py) | API 호출 → 상위 N건 → xlsx 저장 |
| [supabase/migrations/](./supabase/migrations/) | `gold_quotes` 테이블 DDL |
| [scripts/sync_to_supabase.py](./scripts/sync_to_supabase.py) | API → Supabase upsert |
| [web/main.py](./web/main.py) | Supabase `gold_quotes` 조회 API + 정적 페이지 |

## Supabase에 데이터 적재

1. **테이블 생성**: Supabase 대시보드 → SQL → `supabase/migrations/20260330000000_gold_quotes.sql` 내용 실행.
2. **환경 변수** (택 1)
   - **대화형 설정** (권장): 프로젝트 루트에서 `python scripts/setup_supabase_env.py` 실행 후 URL·service_role 키 입력 → `.env` 자동 생성.
   - **수동**: `.env`에 `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` 입력. 키는 **Project Settings → API**의 **service_role (secret)** — `eyJ…` JWT. `sbp_` 토큰은 DB용이 아닙니다.
3. **동기화 실행**:

```bash
python scripts/sync_to_supabase.py --days 365
```

4. **웹 실행**:

```bash
uvicorn web.main:app --host 127.0.0.1 --port 8765
```

이제 웹 화면의 그래프·표는 외부 금시세 사이트가 아니라 **Supabase `gold_quotes` 테이블**을 기준으로 표시됩니다.

## 데이터 소스

- **엔드포인트**: `POST https://www.koreagoldx.co.kr/api/price/chart/list`
- **요청 본문(JSON)** 예:

```json
{
  "srchDt": "ALL",
  "type": "Au",
  "dataDateStart": "2008.03.11",
  "dataDateEnd": "2026.03.30"
}
```

- **응답**: `{ "list": [ { "date", "s_pure", "p_pure", "p_18k", "p_14k", ... }, ... ] }`

> 이용 전 해당 사이트의 이용약관·robots 정책을 확인하세요. 본 저장소 스크립트는 개인 학습·내부 참고용 POC 수준입니다.

## 설치

```bash
cd "/Users/youngoncho/바이브코딩/gold"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 엑셀 저장 (100건)

```bash
python scripts/fetch_gold_to_excel.py
```

기본 출력: `output/gold_prices_100.xlsx`  
건수·경로는 인자로 바꿀 수 있습니다.

```bash
python scripts/fetch_gold_to_excel.py --limit 100 --output ./output/my_gold.xlsx
```

## 다음 단계 (PRD 기준)

- 일 스케줄러로 DB 적재
- 웹 UI(Tabulator) + 기간 필터
- 실패 알림·출처·면책 문구 고정 노출
