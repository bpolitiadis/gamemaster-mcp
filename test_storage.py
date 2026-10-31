"""
Tests for the storage backends. FileStorage always runs; PostgresStorage runs when
TEST_DATABASE_URL is set (CI provides a Postgres service container).
"""

import os

import pytest

from gamemaster_mcp.models import (
    NPC,
    AbilityScore,
    AdventureEvent,
    Character,
    CharacterClass,
    EventType,
    Location,
    Quest,
    Race,
    SessionNote,
)
from gamemaster_mcp.storage import FileStorage, StorageBackend, create_storage

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
ALL_TABLES = ["events", "game_state", "sessions", "encounters", "quests", "locations", "npcs", "characters", "campaigns"]


def _clean_postgres():
    import psycopg

    with psycopg.connect(TEST_DATABASE_URL) as conn:
        for table in ALL_TABLES:
            conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")


@pytest.fixture(params=["file", "postgres"])
def make_storage(request, tmp_path):
    """Factory returning a fresh storage instance over the same underlying data."""
    if request.param == "file":
        return lambda: FileStorage(tmp_path)
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    from gamemaster_mcp.postgres_storage import PostgresStorage

    _clean_postgres()
    return lambda: PostgresStorage(TEST_DATABASE_URL)


def _character(name="Thorin") -> Character:
    return Character(
        name=name,
        character_class=CharacterClass(name="Fighter", level=1),
        race=Race(name="Dwarf"),
        abilities={"strength": AbilityScore(score=16)},
    )


def test_is_storage_backend(make_storage):
    assert isinstance(make_storage(), StorageBackend)


def test_campaign_roundtrip(make_storage):
    storage = make_storage()
    storage.create_campaign("Test Campaign", "A test", dm_name="DM")
    storage.add_character(_character())
    storage.add_npc(NPC(name="Bob", description="A barkeep"))
    storage.add_location(Location(name="Tavern", description="Cozy", location_type="tavern"))
    storage.add_quest(Quest(title="Find the ring", description="Ring"))
    storage.add_session_note(SessionNote(session_number=1, summary="Began"))
    storage.update_game_state(current_location="Tavern")
    storage.add_event(AdventureEvent(event_type=EventType.ROLEPLAY, title="Hello", description="Met Bob"))

    assert storage.list_campaigns() == ["Test Campaign"]

    reloaded = make_storage()
    campaign = reloaded.get_current_campaign()
    assert campaign is not None
    assert campaign.name == "Test Campaign"
    assert campaign.dm_name == "DM"
    assert reloaded.list_characters() == ["Thorin"]
    assert reloaded.get_character("Thorin").abilities["strength"].score == 16
    assert reloaded.list_npcs() == ["Bob"]
    assert reloaded.list_locations() == ["Tavern"]
    assert reloaded.list_quests() == ["Find the ring"]
    assert len(reloaded.get_sessions()) == 1
    assert reloaded.get_game_state().current_location == "Tavern"
    assert [e.title for e in reloaded.get_events()] == ["Hello"]
    assert reloaded.search_events("bob")


def test_remove_and_update_persist(make_storage):
    storage = make_storage()
    storage.create_campaign("Camp", "desc")
    storage.add_character(_character("A"))
    storage.add_character(_character("B"))
    storage.remove_character("A")
    storage.update_character("B", name="C")
    storage.update_campaign(description="new")

    reloaded = make_storage()
    assert reloaded.list_characters() == ["C"]
    assert reloaded.get_current_campaign().description == "new"


def test_load_campaign(make_storage):
    storage = make_storage()
    storage.create_campaign("One", "first")
    storage.create_campaign("Two", "second")
    assert sorted(storage.list_campaigns()) == ["One", "Two"]
    assert storage.load_campaign("One").description == "first"
    with pytest.raises(FileNotFoundError):
        storage.load_campaign("Missing")


def test_create_storage_selects_backend(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert isinstance(create_storage(tmp_path), FileStorage)
    if TEST_DATABASE_URL:
        from gamemaster_mcp.postgres_storage import PostgresStorage

        assert isinstance(create_storage(tmp_path, database_url=TEST_DATABASE_URL), PostgresStorage)


@pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")
def test_postgres_row_shape():
    import psycopg

    from gamemaster_mcp.postgres_storage import PostgresStorage

    _clean_postgres()
    storage = PostgresStorage(TEST_DATABASE_URL)
    storage.create_campaign("Shape", "desc")
    storage.add_character(_character())
    with psycopg.connect(TEST_DATABASE_URL) as conn:
        row = conn.execute("SELECT id, campaign_id, name, created_at, updated_at, data FROM characters").fetchone()
    assert row[2] == "Thorin"
    assert row[1] == storage.get_current_campaign().id
    assert row[5]["race"]["name"] == "Dwarf"
