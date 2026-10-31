"""
D&D MCP Server
A comprehensive D&D campaign management server built with modern FastMCP framework.
"""

import hmac
import logging
import random
import re
import os
from pathlib import Path
from typing import Annotated, Literal
from dotenv import load_dotenv
from fastmcp import FastMCP
from pydantic import Field
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .storage import create_storage
from .models import (
    Character, NPC, Location, Quest, SessionNote, AdventureEvent, EventType,
    AbilityScore, CharacterClass, Race, Item
)

logger = logging.getLogger("gamemaster-mcp")

logging.basicConfig(
    level=logging.DEBUG,
    )

if not load_dotenv():
    logger.warning("❌ .env file invalid or not found! Please see README.md for instructions. Using project root instead.")

data_path = Path(os.getenv("GAMEMASTER_STORAGE_DIR", "")).resolve()
logger.debug(f"📂 Data path: {data_path}")


# Initialize storage and FastMCP server
storage = create_storage(data_dir=data_path)
logger.debug("✅ Storage layer initialized")

mcp = FastMCP(
    name="gamemaster-mcp"
)
logger.debug("✅ Server initialized, registering tools")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """Liveness probe for hosting platforms (HTTP transport only)."""
    return JSONResponse({"status": "ok", "service": "gamemaster-mcp"})



# ----------------------------------------------------------------------
# Tools
# ----------------------------------------------------------------------

# Campaign management tools
@mcp.tool
def create_campaign(
    name: Annotated[str, Field(description="Campaign name")],
    description: Annotated[str, Field(description="Brief decription of the campaign, or a tagline")],
    dm_name: Annotated[str | None, Field(description="Dungeon Master name")] = None,
    setting: Annotated[str | Path | None, Field(description="""
        Campaign setting - a full description of the setting of the campaign in markdown format, or the path to a `.txt` or `.md` file containing the same.
        """)] = None,
) -> str:
    """Create and activate a campaign, returning its name; an existing campaign with the same name is overwritten. No campaign needs to be active first."""
    campaign = storage.create_campaign(
        name=name,
        description=description,
        dm_name=dm_name,
        setting=setting
    )
    return f"🌟 Created campaign: '{campaign.name} and set as active 🌟'"

@mcp.tool
def get_campaign_info() -> str:
    """Return metadata, setting, record counts, and current game-state highlights for the active campaign; unlike list_campaigns, this gives details for one campaign. Does not write data and requires an active campaign."""
    campaign = storage.get_current_campaign()
    if not campaign:
        return "No active campaign."

    info = {
        "name": campaign.name,
        "description": campaign.description,
        "dm_name": campaign.dm_name,
        "setting": campaign.get_setting(),
        "character_count": len(campaign.characters),
        "npc_count": len(campaign.npcs),
        "location_count": len(campaign.locations),
        "quest_count": len(campaign.quests),
        "session_count": len(campaign.sessions),
        "current_session": campaign.game_state.current_session,
        "current_location": campaign.game_state.current_location,
        "party_level": campaign.game_state.party_level,
        "in_combat": campaign.game_state.in_combat
    }

    return f"**Campaign: {campaign.name}**\n\n" + \
           "\n".join([f"**{k.replace('_', ' ').title()}:** {v}" for k, v in info.items()])

@mcp.tool
def list_campaigns() -> str:
    """Return saved campaign names and mark the active one, without changing campaign state. Use get_campaign_info for details; no active campaign is required."""
    campaigns = storage.list_campaigns()
    if not campaigns:
        return f"❌ No campaigns found in {storage.data_dir}!"

    current = storage.get_current_campaign()
    current_name = current.name if current else None

    campaign_list = []
    for campaign in campaigns:
        marker = " (current)" if campaign == current_name else ""
        campaign_list.append(f"• {campaign}{marker}")

    return "**Available Campaigns:**\n" + "\n".join(campaign_list)

@mcp.tool
def load_campaign(
    name: Annotated[str, Field(description="Campaign name to load")]
) -> str:
    """Make a saved campaign active and return its name; unlike list_campaigns, this switches the campaign used by subsequent tools. Does not modify the saved campaign and requires an existing campaign with the given name."""
    campaign = storage.load_campaign(name)
    return f"📖 Loaded campaign: '{campaign.name}'. Campaign is now active!"

# Character Management Tools
@mcp.tool
def create_character(
    name: Annotated[str, Field(description="Character name")],
    character_class: Annotated[str, Field(description="Character class")],
    class_level: Annotated[int, Field(description="Class level", ge=1, le=20)],
    race: Annotated[str, Field(description="Character race")],
    player_name: Annotated[str | None, Field(description="The name of the player in control of this character")] = None,
    description: Annotated[str | None, Field(description="A brief description of the character's appearance and demeanor.")] = None,
    bio: Annotated[str | None, Field(description="The character's backstory, personality, and motivations.")] = None,
    background: Annotated[str | None, Field(description="Character background")] = None,
    alignment: Annotated[str | None, Field(description="Character alignment")] = None,
    strength: Annotated[int, Field(description="Strength score", ge=1, le=30)] = 10,
    dexterity: Annotated[int, Field(description="Dexterity score", ge=1, le=30)] = 10,
    constitution: Annotated[int, Field(description="Constitution score", ge=1, le=30)] = 10,
    intelligence: Annotated[int, Field(description="Intelligence score", ge=1, le=30)] = 10,
    wisdom: Annotated[int, Field(description="Wisdom score", ge=1, le=30)] = 10,
    charisma: Annotated[int, Field(description="Charisma score", ge=1, le=30)] = 10,
) -> str:
    """Create a character and return a confirmation; unlike update_character, this adds a new record, replacing any same-name character. Saves immediately in the active campaign, which must be loaded."""
    # Build ability scores
    abilities = {
        "strength": AbilityScore(score=strength),
        "dexterity": AbilityScore(score=dexterity),
        "constitution": AbilityScore(score=constitution),
        "intelligence": AbilityScore(score=intelligence),
        "wisdom": AbilityScore(score=wisdom),
        "charisma": AbilityScore(score=charisma),
    }

    character = Character(
        name=name,
        player_name=player_name,
        character_class=CharacterClass(name=character_class, level=class_level),
        race=Race(name=race),
        background=background,
        alignment=alignment,
        abilities=abilities,
        description=description,
        bio=bio,
    )

    storage.add_character(character)
    return f"Created character '{character.name}' (Level {character.character_class.level} {character.race.name} {character.character_class.name})"

@mcp.tool
def get_character(
    name_or_id: Annotated[str, Field(description="Character name or ID")]
) -> str:
    """Return a character's identity, abilities, combat stats, and inventory count; use list_characters for only a roster summary. Does not write data and requires an active campaign."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    char_info = f"""**{character.name}** (`{character.id}`)
Level {character.character_class.level} {character.race.name} {character.character_class.name}
**Player:** {character.player_name or 'N/A'}
**Background:** {character.background or 'N/A'}
**Alignment:** {character.alignment or 'N/A'}

**Description:** {character.description or 'No description provided.'}
**Bio:** {character.bio or 'No bio provided.'}

**Ability Scores:**
• STR: {character.abilities['strength'].score} ({character.abilities['strength'].mod:+d})
• DEX: {character.abilities['dexterity'].score} ({character.abilities['dexterity'].mod:+d})
• CON: {character.abilities['constitution'].score} ({character.abilities['constitution'].mod:+d})
• INT: {character.abilities['intelligence'].score} ({character.abilities['intelligence'].mod:+d})
• WIS: {character.abilities['wisdom'].score} ({character.abilities['wisdom'].mod:+d})
• CHA: {character.abilities['charisma'].score} ({character.abilities['charisma'].mod:+d})

**Combat Stats:**
• AC: {character.armor_class}
• HP: {character.hit_points_current}/{character.hit_points_max}
• Temp HP: {character.temporary_hit_points}

**Inventory:** {len(character.inventory)} items
"""

    return char_info

@mcp.tool
def update_character(
    name_or_id: Annotated[str, Field(description="The name or ID of the character to update.")],
    name: Annotated[str | None, Field(description="New character name. If you change this, you must use the character's ID to identify them.")] = None,
    player_name: Annotated[str | None, Field(description="The name of the player in control of this character")] = None,
    description: Annotated[str | None, Field(description="A brief description of the character's appearance and demeanor.")] = None,
    bio: Annotated[str | None, Field(description="The character's backstory, personality, and motivations.")] = None,
    background: Annotated[str | None, Field(description="Character background")] = None,
    alignment: Annotated[str | None, Field(description="Character alignment")] = None,
    hit_points_current: Annotated[int | None, Field(description="Current hit points", ge=0)] = None,
    hit_points_max: Annotated[int | None, Field(description="Maximum hit points", ge=1)] = None,
    temporary_hit_points: Annotated[int | None, Field(description="Temporary hit points", ge=0)] = None,
    armor_class: Annotated[int | None, Field(description="Armor class")] = None,
    inspiration: Annotated[bool | None, Field(description="Inspiration status")] = None,
    notes: Annotated[str | None, Field(description="Additional notes about the character")] = None,
    strength: Annotated[int | None, Field(description="Strength score", ge=1, le=30)] = None,
    dexterity: Annotated[int | None, Field(description="Dexterity score", ge=1, le=30)] = None,
    constitution: Annotated[int | None, Field(description="Constitution score", ge=1, le=30)] = None,
    intelligence: Annotated[int | None, Field(description="Intelligence score", ge=1, le=30)] = None,
    wisdom: Annotated[int | None, Field(description="Wisdom score", ge=1, le=30)] = None,
    charisma: Annotated[int | None, Field(description="Charisma score", ge=1, le=30)] = None,
) -> str:
    """Set supplied fields on one character and return the changed values; use bulk_update_characters for numeric changes across multiple characters. Saves immediately in the active campaign; identify a character by name or ID, and use its ID when renaming."""
    character = storage.get_character(name_or_id)
    if not character:
        return f"❌ Character '{name_or_id}' not found."

    updates = {k: v for k, v in locals().items() if v is not None and k not in ["name_or_id", "character"]}
    updated_fields = [f"{key.replace('_', ' ')}: {value}" for key, value in updates.items()]

    if not updates:
        return f"No updates provided for {character.name}."

    storage.update_character(str(character.id), **updates)

    return f"Updated {character.name}'s properties: {'; '.join(updated_fields)}."

@mcp.tool
def bulk_update_characters(
    names_or_ids: Annotated[list[str], Field(description="List of character names or IDs to update.")],
    hp_change: Annotated[int | None, Field(description="Amount to change current HP by (positive or negative).")] = None,
    temp_hp_change: Annotated[int | None, Field(description="Amount to change temporary HP by (positive or negative).")] = None,
    strength_change: Annotated[int | None, Field(description="Amount to change strength by.")] = None,
    dexterity_change: Annotated[int | None, Field(description="Amount to change dexterity by.")] = None,
    constitution_change: Annotated[int | None, Field(description="Amount to change constitution by.")] = None,
    intelligence_change: Annotated[int | None, Field(description="Amount to change intelligence by.")] = None,
    wisdom_change: Annotated[int | None, Field(description="Amount to change wisdom by.")] = None,
    charisma_change: Annotated[int | None, Field(description="Amount to change charisma by.")] = None,
) -> str:
    """Apply numeric HP or ability-score changes to multiple characters and report updated or missing names; use update_character to set one character's fields directly. Saves each found character in the active campaign, clamping HP and ability scores to valid bounds."""
    updates_log = []
    not_found_log = []

    changes = {
        "hp_change": hp_change,
        "temp_hp_change": temp_hp_change,
        "strength_change": strength_change,
        "dexterity_change": dexterity_change,
        "constitution_change": constitution_change,
        "intelligence_change": intelligence_change,
        "wisdom_change": wisdom_change,
        "charisma_change": charisma_change,
    }

    # Filter out None changes
    active_changes = {k: v for k, v in changes.items() if v is not None}
    if not active_changes:
        return "No changes specified."

    for name_or_id in names_or_ids:
        character = storage.get_character(name_or_id)
        if not character:
            not_found_log.append(name_or_id)
            continue

        char_updates = {}
        char_log = [f"{character.name}:"]

        if hp_change is not None:
            new_hp = character.hit_points_current + hp_change
            # Clamp HP between 0 and max HP
            new_hp = max(0, min(new_hp, character.hit_points_max))
            char_updates['hit_points_current'] = new_hp
            char_log.append(f"HP -> {new_hp}")

        if temp_hp_change is not None:
            new_temp_hp = character.temporary_hit_points + temp_hp_change
            # Temp HP cannot be negative
            new_temp_hp = max(0, new_temp_hp)
            char_updates['temporary_hit_points'] = new_temp_hp
            char_log.append(f"Temp HP -> {new_temp_hp}")

        abilities_updated = False
        ability_changes = {
            "strength": strength_change, "dexterity": dexterity_change,
            "constitution": constitution_change, "intelligence": intelligence_change,
            "wisdom": wisdom_change, "charisma": charisma_change
        }
        for ability, change in ability_changes.items():
            if change is not None:
                new_score = character.abilities[ability].score + change
                new_score = max(1, min(new_score, 30)) # Clamp score
                character.abilities[ability].score = new_score
                abilities_updated = True
                char_log.append(f"{ability.capitalize()} -> {new_score}")

        if abilities_updated:
            char_updates['abilities'] = character.abilities

        if char_updates:
            storage.update_character(str(character.id), **char_updates)
            updates_log.append(" ".join(char_log))

    response_parts = []
    if updates_log:
        response_parts.append("Characters updated:\n" + "\n".join(updates_log))
    if not_found_log:
        response_parts.append(f"Characters not found: {', '.join(not_found_log)}")

    return "\n".join(response_parts) if response_parts else "No characters found to update."

@mcp.tool
def add_item_to_character(
    character_name_or_id: Annotated[str, Field(description="Name or ID of the character to receive the item.")],
    item_name: Annotated[str, Field(description="Item name")],
    description: Annotated[str | None, Field(description="Item description")] = None,
    quantity: Annotated[int, Field(description="Quantity", ge=1)] = 1,
    item_type: Annotated[Literal["weapon", "armor", "consumable", "misc"], Field(description="Item type")] = "misc",
    weight: Annotated[float | None, Field(description="Item weight", ge=0)] = None,
    value: Annotated[str | None, Field(description="Item value (e.g., '50 gp')")] = None,
) -> str:
    """Append an item to a character's inventory and return a confirmation; use update_character for other character fields. Saves immediately in the active campaign; the character must already exist."""
    character = storage.get_character(character_name_or_id)
    if not character:
        return f"❌ Character '{character_name_or_id}' not found!"

    item = Item(
        name=item_name,
        description=description,
        quantity=quantity,
        item_type=item_type,
        weight=weight,
        value=value
    )

    character.inventory.append(item)
    storage.update_character(str(character.id), inventory=character.inventory)

    return f"Added {item.quantity}x {item.name} to {character.name}'s inventory"

@mcp.tool
def list_characters() -> str:
    """Return character names with level, race, and class; use get_character for one character's full details. Does not write data and requires an active campaign."""
    characters = storage.list_characters()
    if not characters:
        return "No characters in the current campaign."

    char_list = []
    for char_name in characters:
        char = storage.get_character(char_name)
        if char:
            char_list.append(f"• {char.name} (Level {char.character_class.level} {char.race.name} {char.character_class.name})")

    return "**Characters:**\n" + "\n".join(char_list)

# NPC Management Tools
@mcp.tool
def create_npc(
    name: Annotated[str, Field(description="NPC name")],
    description: Annotated[str | None, Field(description="A brief, public description of the NPC.")] = None,
    bio: Annotated[str | None, Field(description="A detailed, private bio for the NPC, including secrets.")] = None,
    race: Annotated[str | None, Field(description="NPC race")] = None,
    occupation: Annotated[str | None, Field(description="NPC occupation")] = None,
    location: Annotated[str | None, Field(description="Current location")] = None,
    attitude: Annotated[Literal["friendly", "neutral", "hostile", "unknown"] | None, Field(description="Attitude towards party")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create an NPC and return a confirmation; description is player-facing, while bio is DM-only and may contain secrets. Saves immediately in the active campaign, replacing any same-name NPC; a campaign must be loaded."""
    npc = NPC(
        name=name,
        description=description,
        bio=bio,
        race=race,
        occupation=occupation,
        location=location,
        attitude=attitude,
        notes=notes
    )

    storage.add_npc(npc)
    return f"Created NPC '{npc.name}'"

@mcp.tool
def get_npc(
    name: Annotated[str, Field(description="NPC name")]
) -> str:
    """Return an NPC's details, including player-facing description and DM-only bio that must not be shared with players; use list_npcs for a roster summary. Does not write data and requires an active campaign."""
    npc = storage.get_npc(name)
    if not npc:
        return f"NPC '{name}' not found."

    npc_info = f"""**{npc.name}** (`{npc.id}`)
**Race:** {npc.race or 'Unknown'}
**Occupation:** {npc.occupation or 'Unknown'}
**Location:** {npc.location or 'Unknown'}
**Attitude:** {npc.attitude or 'Neutral'}

**Description:** {npc.description or 'No description available.'}
**Bio:** {npc.bio or 'No bio available.'}

**Notes:** {npc.notes or 'No additional notes.'}
"""

    return npc_info

@mcp.tool
def list_npcs() -> str:
    """Return NPC names and known locations without descriptions or bios; use get_npc for details (including its DM-only bio). Does not write data and requires an active campaign."""
    npcs = storage.list_npcs()
    if not npcs:
        return "No NPCs in the current campaign."

    npc_list = []
    for npc_name in npcs:
        npc = storage.get_npc(npc_name)
        if npc:
            location = f" ({npc.location})" if npc.location else ""
            npc_list.append(f"• {npc.name}{location}")

    return "**NPCs:**\n" + "\n".join(npc_list)

# Location Management Tools
@mcp.tool
def create_location(
    name: Annotated[str, Field(description="Location name")],
    location_type: Annotated[str, Field(description="Type of location (city, town, village, dungeon, etc.)")],
    description: Annotated[str, Field(description="Location description")],
    population: Annotated[int | None, Field(description="Population (if applicable)", ge=0)] = None,
    government: Annotated[str | None, Field(description="Government type")] = None,
    notable_features: Annotated[list[str] | None, Field(description="Notable features")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a location and return its name and type; use get_location for details or list_locations for a roster. Saves immediately in the active campaign, replacing any same-name location; a campaign must be loaded."""
    location = Location(
        name=name,
        location_type=location_type,
        description=description,
        population=population,
        government=government,
        notable_features=notable_features or [],
        notes=notes
    )

    storage.add_location(location)
    return f"Created location '{location.name}' ({location.location_type})"

@mcp.tool
def get_location(
    name: Annotated[str, Field(description="Location name")]
) -> str:
    """Return one location's description, population, government, features, and notes; use list_locations for a name-and-type roster. Does not write data and requires an active campaign."""
    location = storage.get_location(name)
    if not location:
        return f"Location '{name}' not found."

    loc_info = f"""**{location.name}** ({location.location_type})

**Description:** {location.description}

**Population:** {location.population or 'Unknown'}
**Government:** {location.government or 'Unknown'}

**Notable Features:**
{chr(10).join(['• ' + feature for feature in location.notable_features]) if location.notable_features else 'None listed'}

**Notes:** {location.notes or 'No additional notes.'}
"""

    return loc_info

@mcp.tool
def list_locations() -> str:
    """Return location names and types; use get_location for a location's full details. Does not write data and requires an active campaign."""
    locations = storage.list_locations()
    if not locations:
        return "No locations in the current campaign."

    loc_list = []
    for loc_name in locations:
        loc = storage.get_location(loc_name)
        if loc:
            loc_list.append(f"• {loc.name} ({loc.location_type})")

    return "**Locations:**\n" + "\n".join(loc_list)

# Quest Management Tools
@mcp.tool
def create_quest(
    title: Annotated[str, Field(description="Quest title")],
    description: Annotated[str, Field(description="Quest description")],
    giver: Annotated[str | None, Field(description="Quest giver (NPC name)")] = None,
    objectives: Annotated[list[str] | None, Field(description="Quest objectives")] = None,
    reward: Annotated[str | None, Field(description="Quest reward")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Create a quest and return a confirmation; use update_quest to change an existing quest's status or completed objectives. Saves immediately in the active campaign, replacing any same-title quest; a campaign must be loaded."""
    quest = Quest(
        title=title,
        description=description,
        giver=giver,
        objectives=objectives or [],
        reward=reward,
        notes=notes
    )

    storage.add_quest(quest)
    return f"Created quest '{quest.title}'"

@mcp.tool
def update_quest(
    title: Annotated[str, Field(description="Quest title")],
    status: Annotated[Literal["active", "completed", "failed", "on_hold"] | None, Field(description="New quest status")] = None,
    completed_objective: Annotated[str | None, Field(description="Objective to mark as completed")] = None,
) -> str:
    """Set a quest's status and/or mark one listed objective complete, then return a confirmation; use create_quest to add a quest or list_quests to find titles. Saves changes to the active campaign; the quest must exist in a loaded campaign."""
    quest = storage.get_quest(title)
    if not quest:
        return f"Quest '{title}' not found."

    if status:
        storage.update_quest_status(title, status)

    if completed_objective:
        if completed_objective in quest.objectives and completed_objective not in quest.completed_objectives:
            quest.completed_objectives.append(completed_objective)
            storage._save_campaign()  # Direct save since we modified the object

    return f"Updated quest '{title}'"

@mcp.tool
def list_quests(
    status: Annotated[Literal["active", "completed", "failed", "on_hold"] | None, Field(description="Filter by status")] = None,
) -> str:
    """Return quest titles and statuses, optionally filtered by status; use update_quest to change one. Does not write data and requires an active campaign."""
    quests = storage.list_quests(status)

    if not quests:
        filter_text = f" with status '{status}'" if status else ""
        return f"No quests found{filter_text}."

    quest_list = []
    for quest_title in quests:
        quest = storage.get_quest(quest_title)
        if quest:
            status_text = f" [{quest.status}]"
            quest_list.append(f"• {quest.title}{status_text}")

    return "**Quests:**\n" + "\n".join(quest_list)

# Game State Management Tools
@mcp.tool
def update_game_state(
    current_location: Annotated[str | None, Field(description="Current party location")] = None,
    current_session: Annotated[int | None, Field(description="Current session number", ge=1)] = None,
    current_date_in_game: Annotated[str | None, Field(description="Current in-game date")] = None,
    party_level: Annotated[int | None, Field(description="Average party level", ge=1, le=20)] = None,
    party_funds: Annotated[str | None, Field(description="Party treasure/funds")] = None,
    in_combat: Annotated[bool | None, Field(description="Whether party is in combat")] = None,
    notes: Annotated[str | None, Field(description="Current situation notes")] = None,
) -> str:
    """Set only the supplied party or session state fields and return a confirmation; use start_combat/end_combat for combat setup and teardown. Saves immediately and requires an active campaign."""
    kwargs = {}
    if current_location is not None:
        kwargs["current_location"] = current_location
    if current_session is not None:
        kwargs["current_session"] = current_session
    if current_date_in_game is not None:
        kwargs["current_date_in_game"] = current_date_in_game
    if party_level is not None:
        kwargs["party_level"] = party_level
    if party_funds is not None:
        kwargs["party_funds"] = party_funds
    if in_combat is not None:
        kwargs["in_combat"] = in_combat
    if notes is not None:
        kwargs["notes"] = notes

    storage.update_game_state(**kwargs)
    return "Updated game state"

@mcp.tool
def get_game_state() -> str:
    """Return the active campaign's session, location, party, combat, and active-quest-count summary; use get_campaign_info for broader campaign metadata. Does not write data and requires an active campaign."""
    game_state = storage.get_game_state()
    if not game_state:
        return "No game state available."

    state_info = f"""**Game State**
**Campaign:** {game_state.campaign_name}
**Session:** {game_state.current_session}
**Location:** {game_state.current_location or 'Unknown'}
**Date (In-Game):** {game_state.current_date_in_game or 'Unknown'}
**Party Level:** {game_state.party_level}
**Party Funds:** {game_state.party_funds}
**In Combat:** {'Yes' if game_state.in_combat else 'No'}

**Active Quests:** {len(game_state.active_quests)}

**Notes:** {game_state.notes or 'No current notes.'}
"""

    return state_info

# Combat Management Tools
@mcp.tool
def start_combat(
    participants: Annotated[list[dict], Field(description="Combat participants with initiative order")]
) -> str:
    """Sort participants by initiative, set combat active and select the first turn, then return the initiative order. Replaces current combat state in the active campaign; use update_game_state for non-combat fields and load a campaign first."""
    # Sort by initiative (highest first)
    initiative_order = sorted(participants, key=lambda x: x.get("initiative", 0), reverse=True)

    storage.update_game_state(
        in_combat=True,
        initiative_order=initiative_order,
        current_turn=initiative_order[0]["name"] if initiative_order else None,
        combat_round=1
    )

    order_text = "\n".join([
        f"{i+1}. {p['name']} (Initiative: {p.get('initiative', 0)})"
        for i, p in enumerate(initiative_order)
    ])

    return f"**Combat Started!**\n\n**Initiative Order:**\n{order_text}\n\n**Current Turn:** {initiative_order[0]['name'] if initiative_order else 'None'}"

@mcp.tool
def end_combat() -> str:
    """Set combat inactive and clear initiative order and current turn, then return a confirmation; use next_turn to advance ongoing combat. Saves game state and requires an active campaign."""
    storage.update_game_state(
        in_combat=False,
        initiative_order=[],
        current_turn=None,
        combat_round=1
    )
    return "Combat ended."

@mcp.tool
def next_turn() -> str:
    """Advance cyclically to the next participant and return their name; unlike end_combat, this leaves combat active. Saves the new turn in the active campaign and requires combat with an initiative order."""
    game_state = storage.get_game_state()
    if not game_state or not game_state.in_combat:
        return "Not currently in combat."

    if not game_state.initiative_order:
        return "No initiative order set."

    # Find current turn index and advance
    current_index = 0
    if game_state.current_turn:
        for i, participant in enumerate(game_state.initiative_order):
            if participant["name"] == game_state.current_turn:
                current_index = i
                break

    next_index = (current_index + 1) % len(game_state.initiative_order)
    next_participant = game_state.initiative_order[next_index]

    new_round = game_state.combat_round + 1 if next_index == 0 else game_state.combat_round
    storage.update_game_state(current_turn=next_participant["name"], combat_round=new_round)

    return f"**Next Turn:** {next_participant['name']}"

# Session Management Tools
@mcp.tool
def add_session_note(
    session_number: Annotated[int, Field(description="Session number", ge=1)],
    summary: Annotated[str, Field(description="Session summary")],
    title: Annotated[str | None, Field(description="Session title")] = None,
    events: Annotated[list[str] | None, Field(description="Key events that occurred")] = None,
    characters_present: Annotated[list[str] | None, Field(description="Characters present in session")] = None,
    experience_gained: Annotated[int | None, Field(description="Experience points gained", ge=0)] = None,
    treasure_found: Annotated[list[str] | None, Field(description="Treasure or items found")] = None,
    notes: Annotated[str, Field(description="Additional notes")] = "",
) -> str:
    """Append a session summary and its events, attendees, XP, and treasure to the active campaign, then return a confirmation; unlike add_event, this is a campaign session record, not a global event-log entry. Does not replace notes with the same session number; a campaign must be loaded."""
    session_note = SessionNote(
        session_number=session_number,
        title=title,
        summary=summary,
        events=events or [],
        characters_present=characters_present or [],
        experience_gained=experience_gained,
        treasure_found=treasure_found or [],
        notes=notes
    )

    storage.add_session_note(session_note)
    return f"Added session note for Session {session_note.session_number}"

@mcp.tool
def get_sessions() -> str:
    """Return session numbers, dates, titles, and brief summary excerpts; use get_events for the separately stored adventure log. Does not write data and requires an active campaign."""
    sessions = storage.get_sessions()
    if not sessions:
        return "No session notes recorded."

    session_list = []
    for session in sorted(sessions, key=lambda s: s.session_number):
        title = session.title or "No title"
        date = session.date.strftime("%Y-%m-%d")
        session_list.append(f"**Session {session.session_number}** ({date}): {title}")
        session_list.append(f"  {session.summary[:100]}{'...' if len(session.summary) > 100 else ''}")
        session_list.append("")

    return "**Session Notes:**\n\n" + "\n".join(session_list)

# Adventure Log Tools
@mcp.tool
def add_event(
    event_type: Annotated[Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"], Field(description="Type of event")],
    title: Annotated[str, Field(description="Event title")],
    description: Annotated[str, Field(description="Event description")],
    session_number: Annotated[int | None, Field(description="Session number", ge=1)] = None,
    characters_involved: Annotated[list[str] | None, Field(description="Characters involved in the event")] = None,
    location: Annotated[str | None, Field(description="Location where event occurred")] = None,
    importance: Annotated[int, Field(description="Event importance (1-5)", ge=1, le=5)] = 3,
    tags: Annotated[list[str] | None, Field(description="Tags for categorizing the event")] = None,
) -> str:
    """Append an event to the persistent adventure log shared across campaigns and return a confirmation; unlike add_session_note, this does not add a campaign session record. Does not require an active campaign."""
    event = AdventureEvent(
        event_type=EventType(event_type),
        title=title,
        description=description,
        session_number=session_number,
        characters_involved=characters_involved or [],
        location=location,
        importance=importance,
        tags=tags or []
    )

    storage.add_event(event)
    return f"Added {event_type.lower} event: '{event.title}'"

@mcp.tool
def get_events(
    limit: Annotated[int | None, Field(description="Maximum number of events to return", ge=1)] = None,
    event_type: Annotated[Literal["combat", "roleplay", "exploration", "quest", "character", "world", "session"] | None, Field(description="Filter by event type")] = None,
    search: Annotated[str | None, Field(description="Search events by title/description")] = None,
) -> str:
    """Return adventure-log events; without search, limit and event type filter results, while search matches titles and descriptions. Unlike get_sessions, this reads the global log rather than campaign session notes; it does not write data or require an active campaign."""
    if search:
        events = storage.search_events(search)
    else:
        events = storage.get_events(limit=limit, event_type=event_type)

    if not events:
        return "No events found."

    event_list = []
    for event in events:
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M")
        session_text = f" (Session {event.session_number})" if event.session_number else ""
        importance_stars = "★" * event.importance

        event_list.append(f"**{event.title}** [{event.event_type}] {importance_stars}")
        event_list.append(f"  {timestamp}{session_text}")
        event_list.append(f"  {event.description[:150]}{'...' if len(event.description) > 150 else ''}")
        if event.location:
            event_list.append(f"  📍 {event.location}")
        event_list.append("")

    return "**Adventure Log:**\n\n" + "\n".join(event_list)

# Utility Tools
@mcp.tool
def roll_dice(
    dice_notation: Annotated[str, Field(description="Dice notation (e.g., '1d20', '3d6+2')")],
    advantage: Annotated[bool, Field(description="Roll with advantage")] = False,
    disadvantage: Annotated[bool, Field(description="Roll with disadvantage")] = False,
) -> str:
    """Roll the requested dice and return individual results and the total, optionally using advantage or disadvantage on a single d20. This is random and does not change campaign data; no campaign is required."""
    dice_notation = dice_notation.lower().strip()

    # Parse dice notation (e.g., "1d20", "3d6+2", "2d8-1")
    pattern = r'(\d+)d(\d+)([+-]\d+)?'
    match = re.match(pattern, dice_notation)

    if not match:
        return f"Invalid dice notation: {dice_notation}"

    num_dice = int(match.group(1))
    die_size = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    # Roll dice
    if advantage or disadvantage:
        if num_dice != 1 or die_size != 20:
            return "Advantage/disadvantage only applies to single d20 rolls"

        roll1 = random.randint(1, 20)
        roll2 = random.randint(1, 20)

        if advantage:
            result = max(roll1, roll2)
            roll_text = f"Advantage: {roll1}, {roll2} (taking {result})"
        else:
            result = min(roll1, roll2)
            roll_text = f"Disadvantage: {roll1}, {roll2} (taking {result})"

        total = result + modifier
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** {roll_text}{modifier_text} = **{total}**"
    else:
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        roll_sum = sum(rolls)
        total = roll_sum + modifier

        rolls_text = ", ".join(map(str, rolls)) if num_dice > 1 else str(rolls[0])
        modifier_text = f" {modifier:+d}" if modifier != 0 else ""

        return f"🎲 **{dice_notation}** [{rolls_text}]{modifier_text} = **{total}**"

@mcp.tool
def calculate_experience(
    party_size: Annotated[int, Field(description="Number of party members", ge=1)],
    party_level: Annotated[int, Field(description="Average party level", ge=1, le=20)],
    encounter_xp: Annotated[int, Field(description="Total encounter XP value", ge=0)],
) -> str:
    """Calculate adjusted encounter XP and the per-player share, applying the party-size multiplier; unlike recording a session, this only returns a calculation. Does not write campaign data and requires no active campaign."""
    # D&D 5e encounter multipliers based on party size
    if party_size < 3:
        multiplier = 1.5
    elif party_size > 5:
        multiplier = 0.5
    else:
        multiplier = 1.0

    adjusted_xp = int(encounter_xp * multiplier)
    xp_per_player = adjusted_xp // party_size

    return f"""**Experience Calculation:**
Base Encounter XP: {encounter_xp}
Party Size Multiplier: {multiplier}x
Adjusted XP: {adjusted_xp}
**XP per Player: {xp_per_player}**"""

logger.debug("✅ All tools successfully registered. Gamemaster-MCP server running! 🎲")

class BearerAuthMiddleware:
    """Optional ASGI middleware requiring a matching bearer token (skips /health)."""

    def __init__(self, app, token: str) -> None:  # type: ignore[no-untyped-def]
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        if scope["type"] == "http" and scope["path"] != "/health":
            supplied = dict(scope["headers"]).get(b"authorization", b"").decode()
            expected = "Bearer " + self.token
            if not hmac.compare_digest(supplied.encode(), expected.encode()):
                response = JSONResponse({"error": "unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def main() -> None:
    """Main entry point for the D&D MCP Server.

    MCP_TRANSPORT selects the transport: `stdio` (default) or `http`
    (Streamable HTTP, also accepts `streamable-http`).
    """
    transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
        return
    if transport not in ("http", "streamable-http"):
        raise SystemExit(f"Unsupported MCP_TRANSPORT '{transport}' (use 'stdio' or 'http')")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")
    middleware = []
    token = os.getenv("MCP_AUTH_TOKEN")
    if token:
        middleware.append(Middleware(BearerAuthMiddleware, token=token))
    elif path.rstrip("/") == "/mcp":
        logger.warning("⚠️ HTTP transport without MCP_AUTH_TOKEN or a secret MCP_PATH is unauthenticated!")
    mcp.run(transport="http", host=host, port=port, path=path, middleware=middleware)

if __name__ == "__main__":
    main()
