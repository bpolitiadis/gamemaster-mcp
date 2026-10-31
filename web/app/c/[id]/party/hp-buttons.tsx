"use client";

import { useTransition } from "react";
import { adjustHp } from "@/lib/actions";

export function HpButtons({ campaignId, characterId }: { campaignId: string; characterId: string }) {
  const [pending, start] = useTransition();
  const btn = "h-16 flex-1 rounded-xl text-3xl font-bold bg-zinc-800 active:bg-zinc-700 disabled:opacity-50";
  const go = (d: number) => start(() => adjustHp(campaignId, characterId, d));
  return (
    <div className="flex gap-2">
      <button className={btn} disabled={pending} onClick={() => go(-5)} aria-label="Minus 5 HP">−5</button>
      <button className={btn} disabled={pending} onClick={() => go(-1)} aria-label="Minus 1 HP">−</button>
      <button className={btn} disabled={pending} onClick={() => go(1)} aria-label="Plus 1 HP">+</button>
      <button className={btn} disabled={pending} onClick={() => go(5)} aria-label="Plus 5 HP">+5</button>
    </div>
  );
}
