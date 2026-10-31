import { requireAuth } from "@/lib/auth";
import { loadCombat } from "@/lib/combat-actions";
import { Nav } from "../nav";
import { CombatBoard } from "./combat-board";

export const dynamic = "force-dynamic";

export default async function CombatPage({ params }: PageProps<"/c/[id]/combat">) {
  await requireAuth();
  const { id } = await params;
  const state = await loadCombat(id);
  return (
    <main className="flex flex-col gap-4 p-4 pb-28 max-w-2xl mx-auto w-full">
      <Nav id={id} current="combat" />
      {state ? (
        <CombatBoard campaignId={id} initial={state} />
      ) : (
        <p className="text-red-400">No MCP campaign with this name was found, so there is no combat data to show.</p>
      )}
    </main>
  );
}
