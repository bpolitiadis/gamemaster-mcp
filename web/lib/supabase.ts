import "server-only";

import { createClient } from "@supabase/supabase-js";

export type Campaign = {
  id: string;
  name: string;
  description: string | null;
};

export type Character = {
  id: string;
  name: string;
  character_class: string;
  level: number;
  hp_current: number;
  hp_max: number;
  armor_class: number;
  passive_perception: number;
  conditions: string[];
};

export type Npc = {
  id: string;
  name: string;
  description: string | null;
  bio: string | null;
};

export function db() {
  const url = process.env.SUPABASE_URL;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !serviceRoleKey) {
    throw new Error("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured.");
  }

  return createClient(url, serviceRoleKey, {
    auth: {
      autoRefreshToken: false,
      persistSession: false,
    },
  });
}
