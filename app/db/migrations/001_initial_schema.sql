-- Enable required extensions
create extension if not exists "pgcrypto";
create extension if not exists "uuid-ossp";

-- profiles: extends auth.users
create table if not exists profiles (
  id uuid primary key references auth.users on delete cascade,
  name text,
  email text,
  plan text not null default 'free' check (plan in ('free', 'pro', 'premium')),
  created_at timestamptz not null default now()
);

-- charts: one row per birth chart
create table if not exists charts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles(id) on delete cascade,
  name text not null,
  dob date not null,
  tob time not null,
  pob_name text not null,
  pob_lat float8 not null,
  pob_lon float8 not null,
  timezone float8 not null,
  birth_details jsonb,
  astro_details jsonb,
  planets jsonb,
  divisional_charts jsonb,
  kp_planets jsonb,
  kp_cusps jsonb,
  kp_house_significators jsonb,
  kp_planet_significators jsonb,
  parashari_significators jsonb,
  dashas jsonb,
  current_dasha jsonb,
  ashtakavarga jsonb,
  doshas jsonb,
  panchang jsonb,
  created_at timestamptz not null default now()
);

-- analyses: cached AI-generated analyses
create table if not exists analyses (
  id uuid primary key default gen_random_uuid(),
  chart_id uuid not null references charts(id) on delete cascade,
  section text not null,
  content text not null,
  input_hash text not null,
  model text not null,
  created_at timestamptz not null default now(),
  unique (chart_id, section, input_hash)
);

-- chat_messages: conversation history
create table if not exists chat_messages (
  id uuid primary key default gen_random_uuid(),
  chart_id uuid not null references charts(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz not null default now()
);

-- comparisons: compatibility matching
create table if not exists comparisons (
  id uuid primary key default gen_random_uuid(),
  chart_id_1 uuid not null references charts(id) on delete cascade,
  chart_id_2 uuid not null references charts(id) on delete cascade,
  ashtakoot_data jsonb,
  dashakoot_data jsonb,
  analysis text,
  created_at timestamptz not null default now()
);

-- Enable Row Level Security
alter table profiles enable row level security;
alter table charts enable row level security;
alter table analyses enable row level security;
alter table chat_messages enable row level security;
alter table comparisons enable row level security;

-- RLS Policies
create policy "Users own profile" on profiles
  for all using (id = auth.uid());

create policy "Users own charts" on charts
  for all using (user_id = auth.uid());

create policy "Users own analyses" on analyses
  for all using (
    chart_id in (select id from charts where user_id = auth.uid())
  );

create policy "Users own chat messages" on chat_messages
  for all using (
    chart_id in (select id from charts where user_id = auth.uid())
  );

create policy "Users own comparisons" on comparisons
  for all using (
    chart_id_1 in (select id from charts where user_id = auth.uid())
    or chart_id_2 in (select id from charts where user_id = auth.uid())
  );

-- Indexes for common queries
create index if not exists idx_charts_user_id on charts(user_id);
create index if not exists idx_analyses_chart_section on analyses(chart_id, section);
create index if not exists idx_chat_messages_chart on chat_messages(chart_id, created_at);
