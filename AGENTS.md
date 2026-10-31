# Gamemaster MCP

## Project overview

Gamemaster MCP is a Python server that exposes Dungeons & Dragons campaign-management tools to MCP clients. It uses FastMCP to register tools, Pydantic v2 models to validate campaign data, and either JSON files or Postgres for persistence.

The project requires Python 3.12 or newer and uses `uv` for environment and package management. Runtime dependencies are FastMCP, Pydantic, python-dotenv, shortuuid, and typing-extensions. Development dependencies include pytest, Ruff, mypy, and pre-commit.

## Install, run, and test

From the repository root:

```bash
uv venv
uv pip install -e '.[dev]'
```

Run the MCP server:

```bash
uv run gamemaster-mcp
```

Run the test suite:

```bash
uv run pytest
```

The `gamemaster-mcp` command is also available after activating the virtual environment. For MCP clients that launch the server with `uv`, set the client's working directory to the repository root. Set `GAMEMASTER_STORAGE_DIR` in the environment or `.env` file to choose the data root; see [Campaign persistence](#campaign-persistence).

## Repository structure

- `src/gamemaster_mcp/main.py` creates the FastMCP server, initializes storage, registers campaign tools, and defines the server entry point.
- `src/gamemaster_mcp/models.py` defines Pydantic campaign, character, world, session, event, and statistics models.
- `src/gamemaster_mcp/storage.py` defines the `StorageBackend` interface (in-memory active campaign/event access plus persistence hooks), `FileStorage` (JSON files; `DnDStorage` is an alias), and `create_storage()`, which picks the backend.
- `src/gamemaster_mcp/postgres_storage.py` implements `PostgresStorage` (JSONB rows, psycopg).
- `db/migrations/001_init.sql` is the idempotent Postgres schema, shared with any separate web app.
- `test_storage.py` runs the same tests against both backends.
- `src/gamemaster_mcp/logutils.py` initializes the shared `gamemaster-mcp` logger.
- `src/gamemaster_mcp/__init__.py` exposes the package API; `src/gamemaster_mcp/__main__.py` supports running the package as a module.
- `src/main.py` is a top-level CLI wrapper around the package server.
- `test_basic.py` contains the current pytest tests for server initialization, storage initialization, and model behavior.
- `docs/` contains development, storage, roadmap, and FastMCP reference documentation.
- `example/dnd/` contains example campaign documentation.

## Campaign persistence

The running MCP application loads `.env` and reads `GAMEMASTER_STORAGE_DIR` in `src/gamemaster_mcp/main.py`. Its value is resolved to an absolute path and passed to `DnDStorage`. If the variable is unset or empty, the resolved path is the process working directory (typically the MCP client's configured `cwd`). By contrast, directly constructing `DnDStorage()` without a `data_dir` argument uses the relative default `dnd_data` in the current working directory.

`DnDStorage` creates the data root and these subdirectories:

```text
<data-root>/
├── campaigns/
│   └── <sanitized-campaign-name>.json
└── events/
    └── adventure_log.json
```

Campaign filenames are formed from the campaign name by retaining only alphanumeric characters, spaces, hyphens, and underscores, trimming trailing whitespace, and adding `.json`. Each campaign file contains the full `Campaign` model, including its nested campaign data. The global adventure log is a JSON array of `AdventureEvent` models; it is shared across campaigns, not stored inside an individual campaign.

On startup, storage creates the directories, loads the campaign JSON file with the newest modification time (if any), and loads the global event log (if present). Explicitly loading a campaign reads the matching campaign file and makes that campaign active. Creating or updating campaign data serializes the model with Pydantic's JSON-mode dump and writes the campaign file; adding an event rewrites the global event file. Storage mutation methods generally save immediately. Changes made directly to an in-memory model must be followed by a save through storage to persist them.

The `.env.example` file shows the `GAMEMASTER_STORAGE_DIR` setting. The older `docs/STORAGE_STRUCTURE.md` describes `dnd_data/` as the default layout; that is the default for a direct `DnDStorage()` construction, not for the MCP application's current initialization when the setting is empty.

## Storage backends and environment variables

- `GAMEMASTER_STORAGE_DIR`: data root for `FileStorage` (see above).
- `DATABASE_URL`: when set and non-empty, the server uses `PostgresStorage` (target: Supabase Postgres, a libpq URL or `key=value` connection string) and ignores `GAMEMASTER_STORAGE_DIR`. On startup it applies the SQL files in `db/migrations/` (idempotent).
- `TEST_DATABASE_URL`: tests only; enables the Postgres tests in `test_storage.py` (they drop and recreate the tables, so use a throwaway database). CI provides a Postgres service container.

Postgres has one table per entity (`campaigns`, `characters`, `npcs`, `locations`, `quests`, `encounters`, `sessions`, `events`) plus `game_state`. Each row has `id`, `campaign_id`, `name`, `created_at`, `updated_at`, and a JSONB `data` column with the full Pydantic model (`campaigns.data` omits the child entities, which live in their own tables). Events remain global; their `campaign_id` is the campaign active when added.

## Data models and relationships

`Campaign` is the main container. It holds metadata and dictionaries of `Character`, `NPC`, `Location`, `Quest`, and `CombatEncounter` objects, a list of `SessionNote` objects, one `GameState`, and world notes. These dictionaries are keyed by character/NPC/location names or quest titles in the storage layer.

- A `Character` combines a `CharacterClass`, `Race`, ability scores (`AbilityScore` values), inventory and equipment (`Item` values), and known spells (`Spell` values), along with combat, proficiency, and descriptive fields.
- `AbilityScore` validates a score from 1 through 30 and calculates its modifier. `CharacterClass` holds class, level, hit dice, and subclass; `Race` holds race, subrace, and traits.
- `NPC` describes a non-player character and stores relationships as strings. `Location` stores its NPC names and connected-location names as strings. `Quest.giver` and `CombatEncounter.location` are also string references rather than nested model objects.
- `GameState` tracks the campaign's current session, location, date, active quest titles, party details, and combat state. Its location and quest references are strings.
- `SessionNote` records a session summary, events, attendees, experience, and treasure.
- `AdventureEvent` records a categorized event and references characters and location by strings. It is persisted globally in `adventure_log.json`, not as a `Campaign` field. `EventType` provides its event categories.
- `GameStats` tracks server/campaign counters and has a `GameStatHandler` for logging integration. Its save/load methods are currently placeholders, so these statistics are not persisted by those methods.

Pydantic models define the validated data shapes; storage groups and persists campaign-owned models, while adventure events use their separate global file.

## Adding an MCP tool

Tools are defined in `src/gamemaster_mcp/main.py` and registered with the existing `mcp` instance using `@mcp.tool`. Follow the neighboring tools:

1. Define a clearly named function in the appropriate tool category.
2. Annotate parameters with their types and `Annotated[..., Field(description=...)]`; specify defaults and validation constraints such as `ge`, `le`, or `Literal` choices where appropriate.
3. Add a concise function docstring, which FastMCP uses as the tool description.
4. Use or extend a Pydantic model for structured data, and use the `storage` API for campaign/event reads and writes so changes follow the existing persistence flow.
5. Return a clear string response and add or update pytest coverage for the behavior.

## Roadmap

- Replace or augment JSON file storage with PostgreSQL storage.
- Support remote deployment over HTTP.
- Improve MCP tool descriptions.
- Add a Next.js web UI in `/web`.
