"use client";

import { useActionState } from "react";
import { login } from "@/lib/actions";

export default function LoginPage() {
  const [error, action, pending] = useActionState(login, null);
  return (
    <main className="flex flex-1 flex-col justify-center gap-4 p-6 max-w-md mx-auto w-full">
      <h1 className="text-3xl font-bold">DM Screen</h1>
      <form action={action} className="flex flex-col gap-4">
        <input
          name="password"
          type="password"
          placeholder="Password"
          autoFocus
          required
          className="h-14 rounded-xl bg-zinc-800 px-4 text-lg"
        />
        {error && <p className="text-red-400">{error}</p>}
        <button disabled={pending} className="h-14 rounded-xl bg-indigo-600 text-lg font-semibold active:bg-indigo-500">
          Enter
        </button>
      </form>
    </main>
  );
}
