-- Supabase Postgres schema read by the /web DM screen.
create extension if not exists pgcrypto;

create table if not exists campaigns (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists characters (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references campaigns(id) on delete cascade,
  name text not null,
  character_class text not null,
  level int not null default 1 check (level between 1 and 20),
  hp_current int not null default 0,
  hp_max int not null check (hp_max >= 0),
  armor_class int not null default 10,
  passive_perception int not null default 10,
  conditions text[] not null default '{}',
  created_at timestamptz not null default now()
);
create index if not exists characters_campaign_idx on characters(campaign_id);

create table if not exists npcs (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references campaigns(id) on delete cascade,
  name text not null,
  description text, -- public, safe to show players
  bio text,         -- DM-only backstory and secrets
  created_at timestamptz not null default now()
);
create index if not exists npcs_campaign_idx on npcs(campaign_id);

-- Only the server-side service role key is used by /web; block anon access.
alter table campaigns enable row level security;
alter table characters enable row level security;
alter table npcs enable row level security;
