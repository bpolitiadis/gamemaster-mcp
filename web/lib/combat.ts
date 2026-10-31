// Combat state shared by the DM screen and the MCP tools (start_combat, next_turn, end_combat).
// It lives in game_state.data: in_combat, initiative_order, current_turn, combat_round.

export type Combatant = {
  name: string;
  initiative: number;
  hp?: number;
  max_hp?: number;
  ac?: number;
  conditions?: string[];
  [key: string]: unknown;
};

export type CombatState = {
  in_combat: boolean;
  initiative_order: Combatant[];
  current_turn: string | null;
  combat_round: number;
};

export const CONDITIONS = [
  "Blinded", "Charmed", "Deafened", "Frightened", "Grappled", "Incapacitated", "Invisible",
  "Paralyzed", "Petrified", "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious",
  "Concentrating",
] as const;

export function readCombat(data: Record<string, unknown> | null | undefined): CombatState {
  const d = data ?? {};
  const order = Array.isArray(d.initiative_order) ? (d.initiative_order as Combatant[]) : [];
  return {
    in_combat: d.in_combat === true,
    initiative_order: order,
    current_turn: typeof d.current_turn === "string" ? d.current_turn : null,
    combat_round: typeof d.combat_round === "number" && d.combat_round > 0 ? d.combat_round : 1,
  };
}

export function nextTurn(s: CombatState): CombatState {
  if (!s.in_combat || s.initiative_order.length === 0) return s;
  const idx = Math.max(0, s.initiative_order.findIndex((c) => c.name === s.current_turn));
  const next = (idx + 1) % s.initiative_order.length;
  return {
    ...s,
    current_turn: s.initiative_order[next].name,
    combat_round: next === 0 ? s.combat_round + 1 : s.combat_round,
  };
}

export function addCombatant(
  s: CombatState,
  input: { name: string; initiative: number; hp: number; ac: number },
): CombatState {
  const base = input.name.trim() || "Monster";
  const taken = new Set(s.initiative_order.map((c) => c.name));
  let name = base;
  for (let n = 2; taken.has(name); n++) name = `${base} ${n}`;
  const hp = Math.max(0, Math.round(input.hp));
  const added: Combatant = {
    name,
    initiative: input.initiative,
    hp,
    max_hp: hp,
    ac: input.ac,
    conditions: [],
  };
  // Insert after existing combatants of equal or higher initiative (keeps order stable).
  const order = [...s.initiative_order];
  let at = order.findIndex((c) => (c.initiative ?? 0) < added.initiative);
  if (at < 0) at = order.length;
  order.splice(at, 0, added);
  return {
    in_combat: true,
    initiative_order: order,
    current_turn: s.in_combat && s.current_turn ? s.current_turn : order[0].name,
    combat_round: s.in_combat ? s.combat_round : 1,
  };
}

function mapCombatant(s: CombatState, name: string, fn: (c: Combatant) => Combatant): CombatState {
  return { ...s, initiative_order: s.initiative_order.map((c) => (c.name === name ? fn(c) : c)) };
}

export function adjustHp(s: CombatState, name: string, delta: number): CombatState {
  return mapCombatant(s, name, (c) => {
    const max = c.max_hp ?? Math.max(c.hp ?? 0, 0);
    const hp = Math.min(Math.max((c.hp ?? 0) + delta, 0), Math.max(max, c.hp ?? 0));
    return { ...c, hp, max_hp: c.max_hp ?? max };
  });
}

export function toggleCondition(s: CombatState, name: string, condition: string): CombatState {
  return mapCombatant(s, name, (c) => {
    const has = (c.conditions ?? []).includes(condition);
    const conditions = has
      ? (c.conditions ?? []).filter((x) => x !== condition)
      : [...(c.conditions ?? []), condition];
    return { ...c, conditions };
  });
}

export function removeCombatant(s: CombatState, name: string): CombatState {
  const order = s.initiative_order.filter((c) => c.name !== name);
  if (order.length === s.initiative_order.length) return s;
  let current = s.current_turn;
  if (current === name) {
    const idx = s.initiative_order.findIndex((c) => c.name === name);
    current = order.length ? order[idx % order.length].name : null;
  }
  return { ...s, initiative_order: order, current_turn: current, in_combat: order.length > 0 && s.in_combat };
}

export function endCombat(): CombatState {
  return { in_combat: false, initiative_order: [], current_turn: null, combat_round: 1 };
}
