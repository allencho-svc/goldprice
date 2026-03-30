#!/usr/bin/env python3
"""한국금거래소 공개 금시세 API에서 데이터를 가져와 엑셀(xlsx)로 저장합니다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import requests

API_URL = "https://www.koreagoldx.co.kr/api/price/chart/list"
DEFAULT_START = "2008.03.11"


def fetch_list(
    data_date_end: str,
    data_date_start: str = DEFAULT_START,
    srch_dt: str = "ALL",
    metal_type: str = "Au",
) -> list[dict]:
    payload = {
        "srchDt": srch_dt,
        "type": metal_type,
        "dataDateStart": data_date_start,
        "dataDateEnd": data_date_end,
    }
    r = requests.post(
        API_URL,
        json=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, dict) or "list" not in data:
        raise ValueError(f"예상하지 못한 응답 형식: {json.dumps(data)[:500]}")
    return data["list"]


def rows_to_dataframe(rows: list[dict], limit: int) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(
            columns=[
                "고시날짜",
                "내가_살때_순금_3.75g",
                "내가_팔때_순금_3.75g",
                "내가_팔때_18K_3.75g",
                "내가_팔때_14K_3.75g",
            ]
        )
    df = pd.DataFrame(rows)
    # API는 최신순으로 여러 건이 올 수 있음 — 상위 limit만 사용
    df = df.head(limit)
    out = pd.DataFrame(
        {
            "고시날짜": df["date"],
            "내가_살때_순금_3.75g": df["s_pure"],
            "내가_팔때_순금_3.75g": df["p_pure"],
            "내가_팔때_18K_3.75g": df["p_18k"],
            "내가_팔때_14K_3.75g": df["p_14k"],
        }
    )
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="금시세 API → 엑셀 저장")
    parser.add_argument("--limit", type=int, default=100, help="저장할 행 수 (기본 100)")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "output" / "gold_prices_100.xlsx",
        help="출력 xlsx 경로",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="dataDateEnd (YYYY.MM.DD). 생략 시 오늘 날짜(로컬)",
    )
    args = parser.parse_args()

    from datetime import datetime

    end = args.end_date or datetime.now().strftime("%Y.%m.%d")

    rows = fetch_list(data_date_end=end)
    df = rows_to_dataframe(rows, args.limit)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(args.output, index=False, engine="openpyxl")
    print(f"저장 완료: {args.output} ({len(df)}행)")


if __name__ == "__main__":
    main()
