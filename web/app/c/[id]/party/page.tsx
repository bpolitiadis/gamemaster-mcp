import { requireAuth } from "@/lib/auth";
import { db, type Character } from "@/lib/supabase";
import { Nav } from "../nav";
import { HpButtons } from "./hp-buttons";

export default async function PartyPage({ params }: PageProps<"/c/[id]/party">) {
  await requireAuth();
  const { id } = await params;
  const { data, error } = await db()
    .from("dm_characters")
    .select("id, name, character_class, level, hp_current, hp_max, armor_class, passive_perception, conditions")
    .eq("campaign_id", id)
    .order("name");
  const party = (data ?? []) as Character[];
  return (
    <main className="flex flex-col gap-4 p-4 max-w-2xl mx-auto w-full">
      <Nav id={id} current="party" />
      {error && <p className="text-red-400">{error.message}</p>}
      {party.length === 0 && !error && <p className="text-zinc-400">No characters yet.</p>}
      {party.map((pc) => {
        const low = pc.hp_max > 0 && pc.hp_current / pc.hp_max <= 0.25;
        return (
          <section key={pc.id} className="rounded-xl bg-zinc-900 border border-zinc-800 p-4 flex flex-col gap-3">
            <div>
              <h2 className="text-xl font-bold">{pc.name}</h2>
              <p className="text-zinc-400">{pc.character_class} {pc.level}</p>
            </div>
            <div className="flex items-end justify-between">
              <div className={`text-4xl font-bold ${low ? "text-red-400" : ""}`}>
                {pc.hp_current}<span className="text-xl text-zinc-400"> / {pc.hp_max} HP</span>
              </div>
              <div className="text-right text-zinc-300">
                <div>AC <b>{pc.armor_class}</b></div>
                <div>PP <b>{pc.passive_perception}</b></div>
              </div>
            </div>
            <HpButtons campaignId={id} characterId={pc.id} />
            {pc.conditions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {pc.conditions.map((c) => (
                  <span key={c} className="rounded-full bg-amber-900/60 text-amber-200 px-3 py-1 text-sm">{c}</span>
                ))}
              </div>
            )}
          </section>
        );
      })}
    </main>
  );
}
