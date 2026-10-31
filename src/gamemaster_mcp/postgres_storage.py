"""
Postgres storage backend (targets Supabase Postgres).
Schema lives in db/migrations/*.sql; each entity row keeps the full Pydantic model in JSONB `data`.
"""

import logging
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from .models import AdventureEvent, Campaign
from .storage import StorageBackend

logger = logging.getLogger("gamemaster-mcp")

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"

# Campaign fields stored in their own tables rather than in campaigns.data
_CHILD_FIELDS = ("characters", "npcs", "locations", "quests", "encounters", "sessions", "game_state")


def _entity_name(entity: Any) -> str:
    """Display name for an entity row."""
    for attr in ("name", "title"):
        value = getattr(entity, attr, None)
        if value:
            return str(value)
    session_number = getattr(entity, "session_number", None)
    return f"Session {session_number}" if session_number is not None else str(entity.id)


class PostgresStorage(StorageBackend):
    """Stores D&D campaign data in Postgres tables with JSONB payloads."""

    def __init__(self, database_url: str, migrations_dir: str | Path | None = None):
        self.database_url = database_url
        logger.debug("🐘 Initializing PostgresStorage")
        self._apply_migrations(Path(migrations_dir) if migrations_dir else MIGRATIONS_DIR)
        self._init_state()

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url)

    def _apply_migrations(self, migrations_dir: Path) -> None:
        """Run the idempotent SQL migrations if they are available."""
        if not migrations_dir.is_dir():
            logger.warning(f"⚠️ Migrations directory not found: {migrations_dir}; assuming schema exists.")
            return
        with self._connect() as conn:
            for sql_file in sorted(migrations_dir.glob("*.sql")):
                logger.debug(f"🐘 Applying migration {sql_file.name}")
                conn.execute(sql_file.read_text(encoding="utf-8"))  # type: ignore[arg-type]

    # Campaigns
    def _save_campaign(self) -> None:
        campaign = self._current_campaign
        if not campaign:
            logger.debug("❌ No current campaign to save.")
            return

        logger.info(f"💾 Autosaving '{campaign.name}'")
        base = campaign.model_dump(mode="json", exclude=set(_CHILD_FIELDS))
        game_state = campaign.game_state
        children: dict[str, list[Any]] = {
            "characters": list(campaign.characters.values()),
            "npcs": list(campaign.npcs.values()),
            "locations": list(campaign.locations.values()),
            "quests": list(campaign.quests.values()),
            "encounters": list(campaign.encounters.values()),
            "sessions": list(campaign.sessions),
        }

        with self._connect() as conn:
            # A campaign name is unique; saving under an existing name replaces the old campaign
            conn.execute("DELETE FROM campaigns WHERE name = %s AND id <> %s", (campaign.name, campaign.id))
            conn.execute(
                """
                INSERT INTO campaigns (id, name, data) VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET name = EXCLUDED.name, data = EXCLUDED.data, updated_at = now()
                """,
                (campaign.id, campaign.name, Jsonb(base)),
            )
            conn.execute(
                """
                INSERT INTO game_state (id, campaign_id, name, data) VALUES (%s, %s, %s, %s)
                ON CONFLICT (campaign_id) DO UPDATE
                SET name = EXCLUDED.name, data = EXCLUDED.data, updated_at = now()
                """,
                (campaign.id, campaign.id, campaign.name, Jsonb(game_state.model_dump(mode="json"))),
            )
            for table, entities in children.items():
                ids = [e.id for e in entities]
                for entity in entities:
                    conn.execute(
                        f"""
                        INSERT INTO {table} (id, campaign_id, name, data) VALUES (%s, %s, %s, %s)
                        ON CONFLICT (campaign_id, id) DO UPDATE
                        SET name = EXCLUDED.name, data = EXCLUDED.data, updated_at = now()
                        """,  # noqa: S608 - table names are fixed constants
                        (entity.id, campaign.id, _entity_name(entity), Jsonb(entity.model_dump(mode="json"))),
                    )
                conn.execute(
                    f"DELETE FROM {table} WHERE campaign_id = %s AND NOT (id = ANY(%s))",  # noqa: S608
                    (campaign.id, ids),
                )
        logger.debug(f"✅ Campaign '{campaign.name}' saved successfully.")

    def _build_campaign(self, conn: psycopg.Connection, campaign_id: str, base: dict[str, Any]) -> Campaign:
        """Reassemble a Campaign from its row data and child tables."""

        def rows(table: str, order: str) -> list[dict[str, Any]]:
            cur = conn.execute(
                f"SELECT data FROM {table} WHERE campaign_id = %s ORDER BY {order}",  # noqa: S608
                (campaign_id,),
            )
            return [r[0] for r in cur.fetchall()]

        data = dict(base)
        for table in ("characters", "npcs", "locations", "quests", "encounters"):
            data[table] = {row["name" if table != "quests" else "title"]: row
                           for row in rows(table, "created_at, name")}
        data["sessions"] = rows("sessions", "data->>'session_number', id")
        state = rows("game_state", "id")
        data["game_state"] = state[0] if state else {"campaign_name": base.get("name", "")}
        return Campaign.model_validate(data)

    def _load_current_campaign(self) -> None:
        logger.debug("📂 Attempting to load the most recent campaign...")
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, data FROM campaigns ORDER BY updated_at DESC, created_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                logger.debug("❌ No campaigns found.")
                return
            try:
                self._current_campaign = self._build_campaign(conn, row[0], row[1])
                logger.info(f"✅ Successfully loaded campaign: {self._current_campaign.name}")
            except ValueError as e:
                logger.error(f"❌ Error loading campaign {row[0]}: {e}")

    def list_campaigns(self) -> list[str]:
        with self._connect() as conn:
            return [r[0] for r in conn.execute("SELECT name FROM campaigns ORDER BY name").fetchall()]

    def load_campaign(self, name: str) -> Campaign:
        logger.info(f"📂 Attempting to load campaign: '{name}'")
        with self._connect() as conn:
            row = conn.execute("SELECT id, data FROM campaigns WHERE name = %s", (name,)).fetchone()
            if not row:
                logger.error(f"❌ Campaign not found for '{name}'")
                raise FileNotFoundError(f"Campaign '{name}' not found")
            self._current_campaign = self._build_campaign(conn, row[0], row[1])
        logger.info(f"✅ Successfully loaded campaign '{name}'.")
        return self._current_campaign

    # Events
    def _save_events(self) -> None:
        campaign_id = self._current_campaign.id if self._current_campaign else None
        logger.debug(f"💾 Saving {len(self._events)} events...")
        with self._connect() as conn:
            for event in self._events:
                conn.execute(
                    """
                    INSERT INTO events (id, campaign_id, name, data) VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET name = EXCLUDED.name, data = EXCLUDED.data, updated_at = now()
                    """,
                    (event.id, campaign_id, event.title, Jsonb(event.model_dump(mode="json"))),
                )
            conn.execute(
                "DELETE FROM events WHERE NOT (id = ANY(%s))", ([e.id for e in self._events],)
            )
        logger.debug("✅ Events saved successfully.")

    def _load_events(self) -> None:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM events ORDER BY created_at, id").fetchall()
        try:
            self._events = [AdventureEvent.model_validate(r[0]) for r in rows]
            logger.info(f"✅ Successfully loaded {len(self._events)} events.")
        except ValueError as e:
            logger.error(f"❌ Error loading events: {e}")
