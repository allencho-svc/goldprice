#!/usr/bin/env python3
"""
프로젝트 루트에 .env 를 만들고 Supabase 연결 값을 입력받습니다.

대시보드: Project Settings → API
  - Project URL → SUPABASE_URL
  - service_role (secret) → SUPABASE_SERVICE_ROLE_KEY  (eyJ 로 시작하는 JWT)
"""

from __future__ import annotations

import re
import sys
from getpass import getpass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"


def main() -> None:
    print("Supabase 연결 정보를 입력하세요.")
    print("복사 위치: https://supabase.com/dashboard → 프로젝트 선택 → Project Settings → API\n")

    url = input("SUPABASE_URL (예: https://xxxxx.supabase.co): ").strip().strip('"').strip("'")
    if not url:
        print("URL이 비어 있습니다.", file=sys.stderr)
        sys.exit(1)
    if not re.match(r"^https://[a-z0-9-]+\.supabase\.co/?$", url.rstrip("/")):
        print("경고: URL 형식이 일반적인 Supabase URL과 다릅니다. 그대로 진행합니다.", file=sys.stderr)

    print("SUPABASE_SERVICE_ROLE_KEY: (입력 내용은 화면에 표시되지 않습니다)")
    key = getpass("> ").strip()
    if not key:
        print("키가 비어 있습니다.", file=sys.stderr)
        sys.exit(1)
    if key.startswith("sbp_"):
        print(
            "\n오류: sbp_ 로 시작하는 값은 계정 Personal Access Token 입니다.\n"
            "같은 화면에서 'service_role' (secret) — 보통 eyJ 로 시작하는 긴 JWT 를 복사하세요.",
            file=sys.stderr,
        )
        sys.exit(1)
    if not key.startswith("eyJ"):
        print("경고: service_role 키는 보통 eyJ 로 시작합니다. 오타인지 확인하세요.", file=sys.stderr)

    text = f"""# Supabase — setup_supabase_env.py 로 생성됨
# Git 에 커밋하지 마세요 (.gitignore 에 포함)

SUPABASE_URL={url}
SUPABASE_SERVICE_ROLE_KEY={key}
"""
    ENV_PATH.write_text(text, encoding="utf-8")
    print(f"\n저장했습니다: {ENV_PATH}")
    print("이제 실행: python scripts/sync_to_supabase.py")


if __name__ == "__main__":
    main()
