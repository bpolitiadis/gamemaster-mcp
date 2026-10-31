import Link from "next/link";
import { requireAuth } from "@/lib/auth";
import { logout } from "@/lib/actions";
import { db, type Campaign } from "@/lib/supabase";

export default async function CampaignPicker() {
  await requireAuth();
  const { data, error } = await db().from("campaigns").select("id, name, description").order("name");
  const campaigns = (data ?? []) as Campaign[];
  return (
    <main className="flex flex-col gap-4 p-4 max-w-2xl mx-auto w-full">
      <h1 className="text-2xl font-bold">Choose a campaign</h1>
      {error && <p className="text-red-400">{error.message}</p>}
      {campaigns.length === 0 && !error && <p className="text-zinc-400">No campaigns yet.</p>}
      {campaigns.map((c) => (
        <Link
          key={c.id}
          href={`/c/${c.id}/party`}
          className="rounded-xl bg-zinc-900 border border-zinc-800 p-5 active:bg-zinc-800"
        >
          <div className="text-xl font-semibold">{c.name}</div>
          {c.description && <div className="text-zinc-400 mt-1">{c.description}</div>}
        </Link>
      ))}
      <form action={logout}>
        <button className="h-12 w-full rounded-xl text-zinc-400 border border-zinc-800">Log out</button>
      </form>
    </main>
  );
}
