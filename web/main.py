"""금시세 조회 웹: Supabase 기반 API + 정적 페이지."""

from __future__ import annotations

from functools import lru_cache
from datetime import datetime, timedelta
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
KST = ZoneInfo("Asia/Seoul")
TABLE_NAME = "gold_quotes"

app = FastAPI(title="금시세 대시보드")

app.mount("/assets", StaticFiles(directory=BASE / "static"), name="assets")


def _load_env() -> None:
    for name in (".env", ".env.local"):
        env_path = ROOT / name
        if env_path.is_file():
            load_dotenv(env_path, override=True)


def _get_supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "").strip().strip('"').strip("'")


def _get_service_role_key() -> str:
    for env_name in (
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_SECRET_KEY",
    ):
        value = os.environ.get(env_name, "").strip().strip('"').strip("'")
        if value:
            return value
    return ""


@lru_cache(maxsize=1)
def _get_supabase_client():
    _load_env()
    url = _get_supabase_url()
    key = _get_service_role_key()
    if not url or not key:
        raise RuntimeError("SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 가 비어 있습니다.")
    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError("supabase 패키지가 설치되어 있지 않습니다.") from exc
    return create_client(url, key)


def _fetch_rows(start: datetime, end: datetime) -> list[dict]:
    client = _get_supabase_client()
    start_iso = start.isoformat()
    end_iso = end.isoformat()
    page_size = 1000
    offset = 0
    rows: list[dict] = []

    while True:
        response = (
            client.table(TABLE_NAME)
            .select("announced_at,s_pure,p_pure,p_18k,p_14k")
            .gte("announced_at", start_iso)
            .lte("announced_at", end_iso)
            .order("announced_at", desc=False)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = response.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    return rows


def _normalize_row(row: dict) -> dict:
    announced_at = str(row.get("announced_at") or "")
    return {
        "date": announced_at,
        "s_pure": row.get("s_pure"),
        "p_pure": row.get("p_pure"),
        "p_18k": row.get("p_18k"),
        "p_14k": row.get("p_14k"),
    }


def _daily_latest(rows: list[dict]) -> list[dict]:
    """캘린더 일자별로, 해당 일의 마지막 고시 시각 행만 사용."""
    by_day: dict[str, dict] = {}
    for row in rows:
        dt = row.get("date") or ""
        if len(dt) < 10:
            continue
        day = dt[:10]
        cur = by_day.get(day)
        if cur is None or dt > (cur.get("date") or ""):
            by_day[day] = row
    out = []
    for day in sorted(by_day.keys()):
        r = by_day[day]
        out.append(
            {
                "date": day,
                "s_pure": r.get("s_pure"),
                "p_pure": r.get("p_pure"),
                "p_18k": r.get("p_18k"),
                "p_14k": r.get("p_14k"),
            }
        )
    return out


@app.get("/api/prices")
def api_prices(
    days: int = Query(365, ge=7, le=3650, description="조회 기간(일)"),
    table_limit: int = Query(300, ge=10, le=5000, description="표에 보여줄 최신 고시 건수"),
):
    """Supabase 저장본 기준 금시세 원본 + 일자별 집계."""
    end = datetime.now(KST)
    start = end - timedelta(days=days)
    start_s = start.strftime("%Y.%m.%d")
    end_s = end.strftime("%Y.%m.%d")

    try:
        rows = [_normalize_row(row) for row in _fetch_rows(start, end)]
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Supabase 조회 실패: {exc}") from exc

    daily = _daily_latest(rows)
    table_rows = list(reversed(rows))[:table_limit]

    return {
        "meta": {
            "dataDateStart": start_s,
            "dataDateEnd": end_s,
            "days": days,
            "source": "supabase.gold_quotes",
        },
        "daily": daily,
        "table": table_rows,
    }


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")
