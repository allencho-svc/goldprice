#!/usr/bin/env python3
"""
한국금거래소 API 금시세를 Supabase `gold_quotes` 테이블에 upsert합니다.

필요 환경 변수 (.env 권장):
  SUPABASE_URL                 예: https://xxxx.supabase.co
  SUPABASE_SERVICE_ROLE_KEY    Project Settings > API > service_role (secret)

주의: 계정의 sbp_ 로 시작하는 토큰(Personal Access Token)은 Management/CLI용이며
      PostgREST(DB) 접속에는 사용할 수 없습니다. service_role JWT(eyJ...)를 사용하세요.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    """프로젝트 루트 .env(.env.local) 로드. 나중에 로드한 값이 우선."""
    for name in (".env", ".env.local"):
        p = ROOT / name
        if p.is_file():
            load_dotenv(p, override=True)


def _get_supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "").strip().strip('"').strip("'")


def _get_service_role_key() -> str:
    """service_role JWT. 대체 이름도 허용."""
    for env_name in (
        "SUPABASE_SERVICE_ROLE_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_SECRET_KEY",
    ):
        v = os.environ.get(env_name, "").strip().strip('"').strip("'")
        if v:
            return v
    return ""


_load_env()

KST = ZoneInfo("Asia/Seoul")
API_URL = "https://www.koreagoldx.co.kr/api/price/chart/list"


def fetch_rows(data_date_start: str, data_date_end: str) -> list[dict]:
    payload = {
        "srchDt": "SEARCH",
        "type": "Au",
        "dataDateStart": data_date_start,
        "dataDateEnd": data_date_end,
    }
    r = requests.post(
        API_URL,
        json=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or "list" not in data:
        return []
    return data["list"]


def parse_announced_at(date_str: str) -> str:
    s = (date_str or "").strip().replace("T", " ")[:19]
    if len(s) < 19:
        raise ValueError(f"invalid date: {date_str!r}")
    dt = datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST)
    return dt.isoformat()


def rows_to_records(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        ds = row.get("date")
        if not ds:
            continue
        try:
            announced = parse_announced_at(str(ds))
        except ValueError:
            continue
        out.append(
            {
                "announced_at": announced,
                "s_pure": row.get("s_pure"),
                "p_pure": row.get("p_pure"),
                "p_18k": row.get("p_18k"),
                "p_14k": row.get("p_14k"),
                "raw": row,
            }
        )
    return out


def dedupe_records(records: list[dict]) -> list[dict]:
    """동일 announced_at 이 여러 번 오면 마지막 값을 남긴다."""
    deduped: dict[str, dict] = {}
    for record in records:
        announced_at = record.get("announced_at")
        if not announced_at:
            continue
        deduped[announced_at] = record
    return list(deduped.values())


def chunked(xs: list[dict], n: int):
    for i in range(0, len(xs), n):
        yield xs[i : i + n]


def main() -> None:
    parser = argparse.ArgumentParser(description="금시세 → Supabase 동기화")
    parser.add_argument("--days", type=int, default=365, help="최근 N일 구간")
    parser.add_argument("--batch", type=int, default=200, help="upsert 배치 크기")
    args = parser.parse_args()

    url = _get_supabase_url()
    key = _get_service_role_key()
    if not url or not key:
        env_file = ROOT / ".env"
        print(
            "SUPABASE_URL 또는 SUPABASE_SERVICE_ROLE_KEY 가 비어 있습니다.\n",
            file=sys.stderr,
        )
        print(
            "  1) 대시보드에서 복사: Project Settings → API → Project URL, service_role (secret)\n"
            "     (service_role 는 eyJ 로 시작하는 JWT 입니다. sbp_ 토큰은 사용할 수 없습니다.)\n",
            file=sys.stderr,
        )
        if not env_file.is_file():
            print(
                f"  2) 프로젝트 루트에 .env 가 없습니다. 다음으로 자동 생성할 수 있습니다:\n"
                f"       python scripts/setup_supabase_env.py\n",
                file=sys.stderr,
            )
        else:
            print(
                f"  2) {env_file} 에 SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY 를 채웠는지 확인하세요.\n",
                file=sys.stderr,
            )
        sys.exit(1)
    if key.startswith("sbp_"):
        print(
            "오류: sbp_ 토큰은 DB API 용이 아닙니다. Dashboard → API 의 service_role (eyJ…) 를 사용하세요.",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from supabase import create_client
    except ImportError:
        print("pip install supabase", file=sys.stderr)
        sys.exit(1)

    end = datetime.now(KST)
    start = end - timedelta(days=args.days)
    start_s = start.strftime("%Y.%m.%d")
    end_s = end.strftime("%Y.%m.%d")

    print(f"구간: {start_s} ~ {end_s} …")
    rows = fetch_rows(start_s, end_s)
    records = rows_to_records(rows)
    deduped_records = dedupe_records(records)
    duplicate_count = len(records) - len(deduped_records)
    print(
        f"API {len(rows)}건 → 유효 레코드 {len(records)}건"
        + (f" → 중복 시각 제거 {duplicate_count}건" if duplicate_count else "")
    )

    if not deduped_records:
        print("저장할 데이터가 없습니다.")
        return

    client = create_client(url, key)
    total = 0
    for batch in chunked(deduped_records, args.batch):
        res = (
            client.table("gold_quotes")
            .upsert(batch, on_conflict="announced_at")
            .execute()
        )
        n = len(res.data or batch)
        total += n
        print(f"  upsert {n}건 (누적 {total})")

    print(f"완료: gold_quotes 에 반영 {total}건 (중복 고시 시각은 갱신)")


if __name__ == "__main__":
    main()
