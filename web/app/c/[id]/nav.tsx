import Link from "next/link";

export function Nav({ id, current }: { id: string; current: "party" | "npcs" }) {
  const base = "flex-1 h-14 flex items-center justify-center rounded-xl text-lg font-semibold";
  const on = "bg-indigo-600";
  const off = "bg-zinc-900 border border-zinc-800";
  return (
    <nav className="flex gap-2 items-center">
      <Link href="/" className="h-14 w-14 flex items-center justify-center rounded-xl bg-zinc-900 border border-zinc-800" aria-label="Campaigns">
        ←
      </Link>
      <Link href={`/c/${id}/party`} className={`${base} ${current === "party" ? on : off}`}>Party</Link>
      <Link href={`/c/${id}/npcs`} className={`${base} ${current === "npcs" ? on : off}`}>NPCs</Link>
    </nav>
  );
}
