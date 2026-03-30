# 금시세 일일 업데이트 프로젝트

한국금거래소 공개 금시세 API를 수집해 Supabase에 저장하고, 저장된 데이터를 기반으로 그래프·표 형태의 금시세 대시보드를 제공하는 FastAPI 프로젝트입니다.

## 운영 현황

- 운영 URL: `https://goldprice-phi.vercel.app`
- 배포 방식: Vercel Python Functions + FastAPI
- 데이터 저장소: Supabase `public.gold_quotes`
- 수집 소스: 한국금거래소 공개 금시세 API

## 현재 구현된 기능

- 금(Au) 3.75g 기준 시세 수집
  - `내가 살 때 순금`
  - `내가 팔 때 순금`
  - `내가 팔 때 18K`
  - `내가 팔 때 14K`
- Supabase upsert 저장
  - `announced_at` 기준 중복 제거 및 갱신
- 엑셀(`.xlsx`) 저장 스크립트
- 날짜별 시세 추이 라인 차트
- 최신 고시 내역 표
- 표 내 최고가 빨간색, 최저가 파란색 강조
- Vercel 배포 지원

## 아키텍처

1. 외부 금시세 API에서 원본 데이터를 조회합니다.
2. `scripts/sync_to_supabase.py`가 데이터를 정규화하고 Supabase `gold_quotes`에 upsert 합니다.
3. `web/main.py`가 Supabase에서 기간별 데이터를 읽어 `/api/prices`로 제공합니다.
4. 프론트엔드(`web/static/*`)가 `/api/prices` 응답으로 그래프와 표를 렌더링합니다.

## 새로고침 동작

웹 화면의 `새로고침` 버튼은 **외부 API를 다시 수집하지 않습니다.**

- 현재 동작: Supabase에 저장된 데이터를 다시 읽어 화면 갱신
- 외부 데이터 동기화: `scripts/sync_to_supabase.py`를 별도로 실행해야 함

## 주요 파일

| 파일 | 설명 |
|------|------|
| [PRD.md](./PRD.md) | 현재 구현 상태를 반영한 제품 요구사항 문서 |
| [requirements.txt](./requirements.txt) | Python 의존성 |
| [scripts/fetch_gold_to_excel.py](./scripts/fetch_gold_to_excel.py) | 외부 API 호출 후 엑셀 저장 |
| [scripts/setup_supabase_env.py](./scripts/setup_supabase_env.py) | `.env` 대화형 생성 |
| [scripts/sync_to_supabase.py](./scripts/sync_to_supabase.py) | 외부 API → Supabase upsert |
| [supabase/migrations/20260330000000_gold_quotes.sql](./supabase/migrations/20260330000000_gold_quotes.sql) | `gold_quotes` 테이블 생성 SQL |
| [web/main.py](./web/main.py) | Supabase 조회 API + 정적 페이지 서빙 |
| [web/static/index.html](./web/static/index.html) | 대시보드 HTML |
| [web/static/app.js](./web/static/app.js) | 차트·표 렌더링 로직 |
| [web/static/styles.css](./web/static/styles.css) | UI 스타일 |
| [api/index.py](./api/index.py) | Vercel 엔트리포인트 |
| [vercel.json](./vercel.json) | Vercel 라우팅/함수 설정 |

## 설치

```bash
cd "/Users/youngoncho/바이브코딩/gold"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Supabase 설정

1. Supabase SQL Editor에서 `supabase/migrations/20260330000000_gold_quotes.sql` 실행
2. 환경 변수 설정

대화형 설정:

```bash
python scripts/setup_supabase_env.py
```

수동 설정:

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
```

주의:

- `SUPABASE_SERVICE_ROLE_KEY`에는 `service_role` 키를 사용해야 합니다.
- `sbp_...` 토큰은 계정용 Personal Access Token이므로 사용할 수 없습니다.

## 데이터 동기화

최근 1년 데이터를 Supabase에 적재:

```bash
python scripts/sync_to_supabase.py --days 365
```

옵션:

- `--days`: 최근 N일 범위
- `--batch`: upsert 배치 크기

## 로컬 실행

```bash
uvicorn web.main:app --host 127.0.0.1 --port 8765
```

접속:

- `http://127.0.0.1:8765`

## API

### `GET /api/prices`

쿼리:

- `days`: 조회 기간(기본 `365`)
- `table_limit`: 표에 노출할 최신 건수(기본 `300`, 최소 `10`)

응답:

```json
{
  "meta": {
    "dataDateStart": "2026.02.28",
    "dataDateEnd": "2026.03.30",
    "days": 30,
    "source": "supabase.gold_quotes"
  },
  "daily": [],
  "table": []
}
```

## 엑셀 저장

기본 100건 저장:

```bash
python scripts/fetch_gold_to_excel.py
```

경로와 건수 지정:

```bash
python scripts/fetch_gold_to_excel.py --limit 100 --output ./output/my_gold.xlsx
```

## Vercel 배포

이 프로젝트는 Next.js가 아니라 **FastAPI(Python)** 앱입니다.

Vercel 프로젝트 설정:

1. `Framework Preset`: `Other`
2. `Root Directory`: 저장소 루트
3. Environment Variables
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

배포 핵심:

- `api/index.py`가 Vercel Python 엔트리포인트입니다.
- `vercel.json`이 모든 요청을 FastAPI 앱으로 라우팅합니다.
- Python 버전은 Vercel 기본 Python 런타임 자동 감지를 사용합니다.

## 데이터 소스

- 엔드포인트: `POST https://www.koreagoldx.co.kr/api/price/chart/list`
- 주요 필드: `date`, `s_pure`, `p_pure`, `p_18k`, `p_14k`

예시 요청:

```json
{
  "srchDt": "ALL",
  "type": "Au",
  "dataDateStart": "2008.03.11",
  "dataDateEnd": "2026.03.30"
}
```

> 이용 전 해당 사이트의 이용약관·robots 정책을 확인하세요. 본 저장소는 학습·내부 운영용 기준으로 작성되었습니다.
