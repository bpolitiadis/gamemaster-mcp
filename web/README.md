# DM Screen

The mobile-first DM screen is a Next.js app backed by the `dm_*` tables in Supabase. It is separate from the MCP server's campaign storage.

## Run locally

1. Apply [`../db/migrations/002_dm_screen.sql`](../db/migrations/002_dm_screen.sql) to your Supabase project.
2. Copy `.env.example` to `.env.local` and set `DM_PASSWORD`, `DM_AUTH_SECRET`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`.
   Generate the signing secret with `openssl rand -hex 32`. Keep the service-role key and signing secret private; do not use either in a `NEXT_PUBLIC_*` variable.
3. Install and start the app:

   ```bash
   npm install
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000) and sign in with `DM_PASSWORD`.

The campaign picker and party/NPC views read from `dm_campaigns`, `dm_characters`, and `dm_npcs`. Add records through the Supabase table editor to populate the screen.

## Deploy on Vercel

1. Push the repository to GitHub and import it into [Vercel](https://vercel.com/new).
2. Set the project **Root Directory** to `web` and the Node.js version to 22 or newer.
3. Apply the migration above to Supabase.
4. Add these environment variables in the Vercel project settings for Production (and Preview if needed):
   - `DM_PASSWORD`: a strong password for the DM screen.
   - `DM_AUTH_SECRET`: a random secret of at least 32 characters, e.g. `openssl rand -hex 32`.
   - `SUPABASE_URL`: the Supabase project URL.
   - `SUPABASE_SERVICE_ROLE_KEY`: the Supabase service-role key.
5. Deploy. Open the Vercel URL, sign in, and add campaign data in Supabase to view it.

The service-role key is used only by server-side code. The app protects its pages and server actions with a signed, HTTP-only session cookie.
