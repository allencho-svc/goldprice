-- 금시세 고시 내역 (한국금거래소 API 동기화용)
-- Supabase SQL Editor에서 실행하거나: supabase db push (CLI 사용 시)

create table if not exists public.gold_quotes (
  id uuid primary key default gen_random_uuid (),
  announced_at timestamptz not null,
  s_pure bigint,
  p_pure bigint,
  p_18k bigint,
  p_14k bigint,
  raw jsonb,
  created_at timestamptz not null default now (),
  constraint gold_quotes_announced_at_key unique (announced_at)
);

create index if not exists idx_gold_quotes_announced_at_desc on public.gold_quotes (announced_at desc);

comment on table public.gold_quotes is 'Au 3.75g 기준 고시 시세 (원본 API 필드 매핑)';

alter table public.gold_quotes enable row level security;

-- 익명/로그인 사용자: 조회만 (웹·앱에서 anon 키로 읽기 가능)
create policy "gold_quotes_select_anon"
  on public.gold_quotes
  for select
  to anon, authenticated
  using (true);

-- 삽입·갱신: service_role 키만 (서버 스크립트). service_role은 RLS를 우회합니다.
