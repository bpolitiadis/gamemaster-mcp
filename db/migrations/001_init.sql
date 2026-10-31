-- Gamemaster MCP initial schema.
-- One table per entity; each row stores the full Pydantic model in the JSONB `data` column.
-- Idempotent: safe to run repeatedly. Compatible with Supabase Postgres.

CREATE TABLE IF NOT EXISTS campaigns (
    id         TEXT PRIMARY KEY,
    campaign_id TEXT GENERATED ALWAYS AS (id) STORED,
    name       TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    data       JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS characters (
    id          TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL,
    PRIMARY KEY (campaign_id, id)
);
CREATE INDEX IF NOT EXISTS characters_campaign_id_idx ON characters (campaign_id);

CREATE TABLE IF NOT EXISTS npcs (
    id          TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL,
    PRIMARY KEY (campaign_id, id)
);
CREATE INDEX IF NOT EXISTS npcs_campaign_id_idx ON npcs (campaign_id);

CREATE TABLE IF NOT EXISTS locations (
    id          TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL,
    PRIMARY KEY (campaign_id, id)
);
CREATE INDEX IF NOT EXISTS locations_campaign_id_idx ON locations (campaign_id);

CREATE TABLE IF NOT EXISTS quests (
    id          TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL,
    PRIMARY KEY (campaign_id, id)
);
CREATE INDEX IF NOT EXISTS quests_campaign_id_idx ON quests (campaign_id);

CREATE TABLE IF NOT EXISTS encounters (
    id          TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL,
    PRIMARY KEY (campaign_id, id)
);
CREATE INDEX IF NOT EXISTS encounters_campaign_id_idx ON encounters (campaign_id);

CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT NOT NULL,
    campaign_id TEXT NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL,
    PRIMARY KEY (campaign_id, id)
);
CREATE INDEX IF NOT EXISTS sessions_campaign_id_idx ON sessions (campaign_id);

-- One row per campaign; id equals the campaign id.
CREATE TABLE IF NOT EXISTS game_state (
    id          TEXT NOT NULL,
    campaign_id TEXT PRIMARY KEY REFERENCES campaigns(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL
);

-- The adventure log is global; campaign_id records the campaign that was active when the event was added.
CREATE TABLE IF NOT EXISTS events (
    id          TEXT PRIMARY KEY,
    campaign_id TEXT REFERENCES campaigns(id) ON DELETE SET NULL,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    data        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS events_campaign_id_idx ON events (campaign_id);
