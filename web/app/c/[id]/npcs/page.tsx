import { requireAuth } from "@/lib/auth";
import { db, type Npc } from "@/lib/supabase";
import { Nav } from "../nav";

export default async function NpcsPage({ params }: PageProps<"/c/[id]/npcs">) {
  await requireAuth();
  const { id } = await params;
  const { data, error } = await db()
    .from("dm_npcs")
    .select("id, name, description, bio")
    .eq("campaign_id", id)
    .order("name");
  const npcs = (data ?? []) as Npc[];
  return (
    <main className="flex flex-col gap-4 p-4 max-w-2xl mx-auto w-full">
      <Nav id={id} current="npcs" />
      {error && <p className="text-red-400">{error.message}</p>}
      {npcs.length === 0 && !error && <p className="text-zinc-400">No NPCs yet.</p>}
      {npcs.map((npc) => (
        <section key={npc.id} className="rounded-xl bg-zinc-900 border border-zinc-800 p-4 flex flex-col gap-2">
          <h2 className="text-xl font-bold">{npc.name}</h2>
          {npc.description && <p className="text-zinc-300">{npc.description}</p>}
          {npc.bio && (
            <details className="group">
              <summary className="h-14 flex items-center justify-center rounded-xl bg-zinc-800 active:bg-zinc-700 cursor-pointer list-none font-semibold">
                <span className="group-open:hidden">Tap to reveal bio</span>
                <span className="hidden group-open:inline">Hide bio</span>
              </summary>
              <p className="mt-3 text-zinc-200 whitespace-pre-wrap">{npc.bio}</p>
            </details>
          )}
        </section>
      ))}
    </main>
  );
}
