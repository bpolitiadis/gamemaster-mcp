"use server";

import { requireAuth } from "@/lib/auth";
import { db } from "@/lib/supabase";
import * as combat from "@/lib/combat";
import type { CombatState } from "@/lib/combat";

// The web DM screen's dm_campaigns row is matched to the MCP `campaigns` row by name;
// combat lives in that campaign's game_state row, exactly where the MCP tools write it.
async function gameStateRow(dmCampaignId: string) {
  const { data: dm, error: dmErr } = await db().from("dm_campaigns").select("name").eq("id", dmCampaignId).single();
  if (dmErr || !dm) throw new Error(dmErr?.message ?? "Campaign not found");
  const { data: mcp, error: mcpErr } = await db().from("campaigns").select("id").eq("name", dm.name).maybeSingle();
  if (mcpErr) throw new Error(mcpErr.message);
  if (!mcp) throw new Error(`No MCP campaign named "${dm.name}"; create or load it from the MCP server first.`);
  const { data: gs, error: gsErr } = await db().from("game_state").select("data").eq("campaign_id", mcp.id).maybeSingle();
  if (gsErr) throw new Error(gsErr.message);
  return { mcpId: mcp.id as string, name: dm.name as string, data: (gs?.data ?? { campaign_name: dm.name }) as Record<string, unknown> };
}

export async function loadCombat(dmCampaignId: string): Promise<CombatState | null> {
  await requireAuth();
  try {
    return combat.readCombat((await gameStateRow(dmCampaignId)).data);
  } catch {
    return null;
  }
}

async function mutate(dmCampaignId: string, fn: (s: CombatState) => CombatState): Promise<CombatState> {
  await requireAuth();
  const row = await gameStateRow(dmCampaignId);
  const next = fn(combat.readCombat(row.data));
  const data = { ...row.data, ...next, updated_at: new Date().toISOString() };
  const { error } = await db()
    .from("game_state")
    .upsert({ id: row.mcpId, campaign_id: row.mcpId, name: row.name, data, updated_at: new Date().toISOString() }, { onConflict: "campaign_id" });
  if (error) throw new Error(error.message);
  return next;
}

export async function nextTurnAction(id: string) {
  return mutate(id, combat.nextTurn);
}
export async function addCombatantAction(id: string, input: { name: string; initiative: number; hp: number; ac: number }) {
  return mutate(id, (s) => combat.addCombatant(s, input));
}
export async function adjustHpAction(id: string, name: string, delta: number) {
  return mutate(id, (s) => combat.adjustHp(s, name, delta));
}
export async function toggleConditionAction(id: string, name: string, condition: string) {
  return mutate(id, (s) => combat.toggleCondition(s, name, condition));
}
export async function removeCombatantAction(id: string, name: string) {
  return mutate(id, (s) => combat.removeCombatant(s, name));
}
export async function endCombatAction(id: string) {
  return mutate(id, () => combat.endCombat());
}
