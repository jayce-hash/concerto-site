-- Concerto AI questions, logged anonymously. Run once in the Supabase SQL Editor.
-- What fans ask is the clearest signal of what they want from Concerto.
-- No account, IP, or device id is stored: only the question, what it was about, and how it was answered.
-- Written only by netlify/functions/ask.js with the service key; nobody can read it through the public API.

create table if not exists public.ai_questions (
  id          bigint generated always as identity primary key,
  created_at  timestamptz not null default now(),
  question    text not null,
  venue_slug  text,
  tour_slug   text,
  mode        text,          -- guide (answered from the guide), ai (AI answer), none (couldn't tell what it was about)
  limited     text,          -- set when the AI step was skipped for a daily cap
  surface     text           -- app or web
);
create index if not exists ai_questions_created_idx on public.ai_questions (created_at desc);
alter table public.ai_questions enable row level security;
revoke all on public.ai_questions from anon, authenticated;

-- ============================================================
-- READING IT
-- ============================================================
-- Latest questions:
--   select created_at, surface, mode, venue_slug, tour_slug, question from ai_questions order by created_at desc limit 100;
-- What fans ask about most (by venue):
--   select venue_slug, count(*) from ai_questions where venue_slug is not null group by 1 order by 2 desc limit 25;
-- Questions Concerto couldn't place (gaps to fill):
--   select question, count(*) from ai_questions where mode = 'none' group by 1 order by 2 desc limit 50;
