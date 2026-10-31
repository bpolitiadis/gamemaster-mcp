import "server-only";

import { createHmac, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

const COOKIE_NAME = "dm_auth";
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

export function verifyPassword(candidate: string): boolean {
  const password = process.env.DM_PASSWORD;
  if (!password) return false;

  const expected = Buffer.from(password);
  const supplied = Buffer.from(candidate);
  return expected.length === supplied.length && timingSafeEqual(expected, supplied);
}

export function createSessionToken(): string | null {
  const secret = process.env.DM_AUTH_SECRET;
  if (!secret || secret.length < 32) return null;

  const issuedAt = Math.floor(Date.now() / 1000).toString();
  const signature = createHmac("sha256", secret)
    .update(`gamemaster-dm-screen:${issuedAt}`)
    .digest("hex");
  return `${issuedAt}.${signature}`;
}

function isValidSessionToken(token: string | undefined): boolean {
  const secret = process.env.DM_AUTH_SECRET;
  if (!secret || secret.length < 32 || !token) return false;

  const [issuedAt, signature, extra] = token.split(".");
  if (!issuedAt || !/^\d+$/.test(issuedAt) || !signature || extra) return false;

  const issuedAtSeconds = Number(issuedAt);
  const now = Math.floor(Date.now() / 1000);
  if (
    !Number.isSafeInteger(issuedAtSeconds) ||
    issuedAtSeconds > now + 60 ||
    now - issuedAtSeconds > SESSION_MAX_AGE_SECONDS ||
    !/^[a-f0-9]{64}$/.test(signature)
  ) {
    return false;
  }

  const expected = createHmac("sha256", secret)
    .update(`gamemaster-dm-screen:${issuedAt}`)
    .digest();
  return timingSafeEqual(expected, Buffer.from(signature, "hex"));
}

export async function requireAuth(): Promise<void> {
  if (!isValidSessionToken((await cookies()).get(COOKIE_NAME)?.value)) {
    redirect("/login");
  }
}

export const authCookieName = COOKIE_NAME;
