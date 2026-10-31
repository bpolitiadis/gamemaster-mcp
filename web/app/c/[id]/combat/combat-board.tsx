"use client";

import { useOptimistic, useState, useTransition } from "react";
import * as combat from "@/lib/combat";
import { CONDITIONS, type CombatState } from "@/lib/combat";
import {
  addCombatantAction,
  adjustHpAction,
  endCombatAction,
  nextTurnAction,
  removeCombatantAction,
  toggleConditionAction,
} from "@/lib/combat-actions";

type Op =
  | { t: "next" }
  | { t: "add"; name: string; initiative: number; hp: number; ac: number }
  | { t: "hp"; name: string; delta: number }
  | { t: "cond"; name: string; condition: string }
  | { t: "remove"; name: string }
  | { t: "end" };

function reduce(s: CombatState, op: Op): CombatState {
  switch (op.t) {
    case "next": return combat.nextTurn(s);
    case "add": return combat.addCombatant(s, op);
    case "hp": return combat.adjustHp(s, op.name, op.delta);
    case "cond": return combat.toggleCondition(s, op.name, op.condition);
    case "remove": return combat.removeCombatant(s, op.name);
    case "end": return combat.endCombat();
  }
}

export function CombatBoard({ campaignId, initial }: { campaignId: string; initial: CombatState }) {
  const [saved, setSaved] = useState(initial);
  const [state, apply] = useOptimistic(saved, reduce);
  const [, start] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const run = (op: Op, action: () => Promise<CombatState>) =>
    start(async () => {
      apply(op);
      try {
        setSaved(await action());
        setError(null);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Save failed");
      }
    });

  const btn = "h-14 rounded-xl bg-zinc-800 active:bg-zinc-700 text-xl font-bold";
  const input = "h-14 rounded-xl bg-zinc-900 border border-zinc-800 px-3 text-lg w-full";

  return (
    <>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Round {state.combat_round}</h1>
        {state.in_combat && (
          <button
            className="h-12 px-4 rounded-xl border border-zinc-800 text-zinc-400"
            onClick={() => confirm("End combat?") && run({ t: "end" }, () => endCombatAction(campaignId))}
          >
            End combat
          </button>
        )}
      </div>
      {error && <p className="text-red-400">{error}</p>}
      {!state.in_combat && <p className="text-zinc-400">No active combat. Add a combatant to start one.</p>}

      <ul className="flex flex-col gap-2">
        {state.initiative_order.map((c) => {
          const current = c.name === state.current_turn;
          const open = selected === c.name;
          const conditions = c.conditions ?? [];
          const down = c.hp !== undefined && c.hp <= 0;
          return (
            <li
              key={c.name}
              className={`rounded-xl border p-3 flex flex-col gap-3 ${current ? "border-indigo-500 bg-indigo-950/60" : "border-zinc-800 bg-zinc-900"}`}
            >
              <button
                className="flex items-center gap-3 text-left min-h-14"
                aria-expanded={open}
                onClick={() => setSelected(open ? null : c.name)}
              >
                <span className="w-10 text-center text-2xl font-bold text-zinc-400">{c.initiative}</span>
                <span className="flex-1">
                  <span className={`block text-lg font-semibold ${down ? "line-through text-zinc-500" : ""}`}>{c.name}</span>
                  {conditions.length > 0 && (
                    <span className="flex flex-wrap gap-1 mt-1">
                      {conditions.map((x) => (
                        <span key={x} className="rounded-full bg-amber-900/60 text-amber-200 px-2 py-0.5 text-xs">{x}</span>
                      ))}
                    </span>
                  )}
                </span>
                <span className="text-right">
                  {c.hp !== undefined && (
                    <span className={`block text-xl font-bold ${c.max_hp && c.hp / c.max_hp <= 0.25 ? "text-red-400" : ""}`}>
                      {c.hp}{c.max_hp !== undefined && <span className="text-sm text-zinc-400">/{c.max_hp}</span>}
                    </span>
                  )}
                  {c.ac !== undefined && <span className="block text-sm text-zinc-400">AC {c.ac}</span>}
                </span>
              </button>
              {open && (
                <div className="flex flex-col gap-3">
                  <div className="grid grid-cols-4 gap-2">
                    {[-5, -1, 1, 5].map((d) => (
                      <button
                        key={d}
                        className={btn}
                        aria-label={`${d < 0 ? "Damage" : "Heal"} ${Math.abs(d)}`}
                        onClick={() => run({ t: "hp", name: c.name, delta: d }, () => adjustHpAction(campaignId, c.name, d))}
                      >
                        {d > 0 ? `+${d}` : `−${-d}`}
                      </button>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {CONDITIONS.map((cond) => {
                      const on = conditions.includes(cond);
                      return (
                        <button
                          key={cond}
                          aria-pressed={on}
                          className={`h-11 px-3 rounded-full text-sm ${on ? "bg-amber-700 text-white" : "bg-zinc-800 text-zinc-300"}`}
                          onClick={() => run({ t: "cond", name: c.name, condition: cond }, () => toggleConditionAction(campaignId, c.name, cond))}
                        >
                          {cond}
                        </button>
                      );
                    })}
                  </div>
                  <button
                    className="h-11 rounded-xl text-red-400 border border-zinc-800"
                    onClick={() => {
                      setSelected(null);
                      run({ t: "remove", name: c.name }, () => removeCombatantAction(campaignId, c.name));
                    }}
                  >
                    Remove {c.name}
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      {adding && (
        <form
          className="rounded-xl bg-zinc-900 border border-zinc-800 p-3 grid grid-cols-3 gap-2"
          action={(fd) => {
            const op = {
              name: String(fd.get("name") ?? ""),
              initiative: Number(fd.get("initiative")) || 0,
              hp: Number(fd.get("hp")) || 0,
              ac: Number(fd.get("ac")) || 10,
            };
            setAdding(false);
            run({ t: "add", ...op }, () => addCombatantAction(campaignId, op));
          }}
        >
          <input name="name" required placeholder="Monster name" className={`${input} col-span-3`} autoComplete="off" />
          <input name="initiative" type="number" inputMode="numeric" required placeholder="Init" className={input} />
          <input name="hp" type="number" inputMode="numeric" min={0} required placeholder="HP" className={input} />
          <input name="ac" type="number" inputMode="numeric" min={0} required placeholder="AC" className={input} />
          <button className="h-14 rounded-xl bg-indigo-600 text-lg font-semibold col-span-2">Add</button>
          <button type="button" className="h-14 rounded-xl bg-zinc-800" onClick={() => setAdding(false)}>Cancel</button>
        </form>
      )}

      <div className="fixed inset-x-0 bottom-0 bg-zinc-950/95 border-t border-zinc-800 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <div className="max-w-2xl mx-auto flex gap-2">
          <button
            className="h-16 w-20 rounded-xl bg-zinc-800 active:bg-zinc-700 text-lg font-semibold"
            onClick={() => setAdding((a) => !a)}
            aria-label="Quick add monster"
          >
            + Add
          </button>
          <button
            className="h-16 flex-1 rounded-xl bg-indigo-600 active:bg-indigo-500 text-xl font-bold disabled:opacity-50"
            disabled={!state.in_combat || state.initiative_order.length === 0}
            onClick={() => run({ t: "next" }, () => nextTurnAction(campaignId))}
          >
            Next Turn
          </button>
        </div>
      </div>
    </>
  );
}
