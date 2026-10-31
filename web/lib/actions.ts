"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import {
  authCookieName,
  createSessionToken,
  requireAuth,
  SESSION_MAX_AGE_SECONDS,
  verifyPassword,
} from "@/lib/auth";
import { db } from "@/lib/supabase";

export async function login(
  _previousState: string | null,
  formData: FormData,
): Promise<string | null> {
  const token = createSessionToken();
  if (!token || !process.env.DM_PASSWORD) {
    return "DM_PASSWORD and a 32-character DM_AUTH_SECRET must be configured.";
  }

  const password = formData.get("password");
  if (typeof password !== "string" || !verifyPassword(password)) {
    return "Incorrect password.";
  }

  (await cookies()).set(authCookieName, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: SESSION_MAX_AGE_SECONDS,
  });
  redirect("/");
}

export async function logout(): Promise<never> {
  (await cookies()).delete(authCookieName);
  redirect("/login");
}

export async function adjustHp(
  campaignId: string,
  characterId: string,
  amount: number,
): Promise<void> {
  await requireAuth();
  if (!Number.isInteger(amount) || ![-5, -1, 1, 5].includes(amount)) {
    throw new Error("Invalid HP adjustment.");
  }

  const client = db();
  const { data: character, error: readError } = await client
    .from("dm_characters")
    .select("hp_current, hp_max")
    .eq("id", characterId)
    .eq("campaign_id", campaignId)
    .maybeSingle();

  if (readError) throw new Error(readError.message);
  if (!character) throw new Error("Character not found.");

  const hp = Math.min(character.hp_max, Math.max(0, character.hp_current + amount));
  const { error: updateError } = await client
    .from("dm_characters")
    .update({ hp_current: hp })
    .eq("id", characterId)
    .eq("campaign_id", campaignId);

  if (updateError) throw new Error(updateError.message);
  revalidatePath(`/c/${campaignId}/party`);
}
