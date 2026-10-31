# Deploying Gamemaster MCP remotely

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` for local use; `http` for Streamable HTTP (Railway/Docker). Ignored on Vercel, which loads the ASGI `app` directly. |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Bind address (Railway sets `PORT`) |
| `MCP_PATH` | `/mcp` | URL path of the MCP endpoint. **Make it a long random secret** (see below) |
| `MCP_AUTH_TOKEN` | unset | Optional `Authorization: Bearer` token |
| `FASTMCP_STATELESS_HTTP` | unset | Set `true` for multi-instance / serverless-friendly Streamable HTTP. Auto-enabled when `VERCEL` is set. |
| `GAMEMASTER_STORAGE_DIR` | cwd; on Vercel `/tmp/gamemaster` | Campaign JSON storage; mount a persistent volume on Railway |
| `DATABASE_URL` | unset | PostgreSQL campaign storage; if unset, the server uses JSON files |

`GET /health` returns `{"status":"ok"}` without authentication.

## View the DM screen

The web UI is a separate Next.js app. To deploy it to Vercel and configure its Supabase database, follow [`web/README.md`](web/README.md).

## Deploy on Vercel

The repo’s Python project exposes a Streamable HTTP ASGI app as `app` in `src/main.py` (what Vercel’s Python runtime looks for). `vercel.json` sets a 60s function timeout and excludes the Next.js `web/` tree from the Python bundle.

1. In the Vercel project linked to this repo, keep the **root directory** at the repository root (not `web/`). Framework should be the auto-detected Python preset.
2. Deploy from Git (or `vercel --prod`). No build command is required beyond dependency install from `pyproject.toml` / `uv.lock`.
3. Set environment variables in the Vercel project:
   - `MCP_PATH=/mcp/<long-random-string>` (e.g. `openssl rand -hex 24`) — treat the URL as a password.
   - Optional: `MCP_AUTH_TOKEN` for clients that can send a bearer header (Claude web/mobile cannot).
   - Strongly recommended: `DATABASE_URL` pointing at Postgres (e.g. Supabase). Without it, JSON files go under `/tmp/gamemaster` and **do not persist** across cold starts or instances.
4. After deploy, check `https://<project>.vercel.app/health`.
5. MCP endpoint: `https://<project>.vercel.app/mcp` (or your custom `MCP_PATH`).

### Vercel limitations

- **Ephemeral filesystem**: file-based campaign storage under `/tmp` is lost when the function instance recycles. Use `DATABASE_URL` for durable data.
- **Stateless HTTP**: sessions are not sticky across invocations; Streamable HTTP runs with `stateless_http=True` on Vercel.
- **Timeouts**: Hobby plans may allow less than the configured 60s `maxDuration`; raise the plan or lower expectations for slow tool calls.
- The Next.js DM screen in `/web` is a **separate** Vercel project (root directory `web`).

Local ASGI smoke test (same entrypoint Vercel uses):

```bash
uv sync
uv run uvicorn main:app --app-dir src --host 127.0.0.1 --port 8000
# then: curl -s http://127.0.0.1:8000/health
```

## Deploy on Railway

1. Push the repo to GitHub, then in Railway choose **New Project → Deploy from GitHub repo**. `railway.json` makes it build the `Dockerfile` and use `/health` as the health check.
2. Add a **Volume** mounted at `/data` (campaigns are stored there).
3. Set variables: `MCP_PATH=/mcp/<long-random-string>` (e.g. `openssl rand -hex 24`). Optionally `MCP_AUTH_TOKEN`.
4. Under **Settings → Networking** generate a public domain.
5. Check `https://<domain>/health`.

Local Docker test:

```bash
docker build -t gamemaster-mcp .
docker run -p 8000:8000 -v gm-data:/data -e MCP_PATH=/mcp/changeme gamemaster-mcp
```

## Add the connector in Claude (web and mobile)

1. In claude.ai: **Settings → Connectors → Add custom connector** (Team/Enterprise: an owner adds it under organization connectors).
2. URL: `https://<domain>/mcp/<long-random-string>`. Leave the OAuth fields empty.
3. Enable the connector in a chat. Connectors added on the web are available in the mobile apps.

Claude custom connectors do not let you enter a static bearer header; see the auth decision in `AGENTS.md`. `MCP_AUTH_TOKEN` is for clients that can send an `Authorization` header whose value is the word Bearer, a space, then your token (Claude Code via `claude mcp add --transport http gamemaster <url> --header`, the API MCP connector, MCP Inspector).
