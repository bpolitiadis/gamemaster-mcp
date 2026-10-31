# Deploying Gamemaster MCP remotely

## Configuration (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `MCP_TRANSPORT` | `stdio` | `stdio` for local use; `http` for Streamable HTTP |
| `HOST` / `PORT` | `0.0.0.0` / `8000` | Bind address (Railway sets `PORT`) |
| `MCP_PATH` | `/mcp` | URL path of the MCP endpoint. **Make it a long random secret** (see below) |
| `MCP_AUTH_TOKEN` | unset | Optional `Authorization: Bearer` token |
| `GAMEMASTER_STORAGE_DIR` | `/data` in Docker | Campaign JSON storage; mount a persistent volume here |
| `DATABASE_URL` | unset | Reserved for the planned PostgreSQL storage; not used yet |

`GET /health` returns `{"status":"ok"}` without authentication.

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

