# Deploy to Dokploy

## Prerequisites

- A Dokploy server (self-hosted or cloud)
- A domain (e.g., `docsagent.example.com`) pointed to your server's IP
- Your repo pushed to GitHub/GitLab

## Architecture

```
                                ┌──────────────┐
                                │   MongoDB 7   │
                                │  (internal)   │
                                └──────┬───────┘
                                       │
┌────────┐   ┌─────────────────────────▼──────────┐
│ User   │──▶│  Frontend (Next.js :3000)          │
│ Browser│   │  /auth/* → http://backend:8000     │
│        │   │  /ask/*  → http://backend:8000     │
│        │   │  /chats/*→ http://backend:8000     │
└────────┘   │  /docs/* → http://backend:8000     │
             │  /sessions/*→ http://backend:8000  │
             └────────────────────┬───────────────┘
                                  │
             ┌────────────────────▼───────────────┐
             │  Backend (FastAPI :8000)            │
             │  - OpenAI/Agno agent                │
             │  - JWT auth                         │
             └────────────────────────────────────┘
```

**Single domain.** All traffic hits the frontend. Next.js rewrites proxy `/auth/*`, `/ask/*`, `/chats/*`, `/docs/*`, `/sessions/*` to the backend over Docker's internal network.

## Step-by-Step

### 1. Push to GitHub

```bash
git push origin main
```

### 2. Create a Compose Service in Dokploy

1. In the Dokploy dashboard, create a **New Project**
2. Create a **New Service** → type **Compose**
3. **Compose Type**: `Docker Compose` (not Stack — we use `build:`)
4. **Provider**: GitHub (or your Git provider)
5. **Repository**: `your-username/your-repo`
6. **Branch**: `main`
7. **Compose Path**: `./docker-compose.yml`
8. Click **Save**

### 3. Set Environment Variables

In the **Environment** tab of your compose service, add these **required** vars:

| Variable | Example | Notes |
|---|---|---|
| `OPENAI_API_KEYS` | `gsk_key1, gsk_key2` | Comma-separated Groq/OpenAI keys |
| `JWT_SECRET` | `random-64-char-string` | Generate with `openssl rand -hex 32` |

**Optional** overrides (defaults shown):

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` | Change for other providers |
| `OPENAI_MODEL` | `qwen/qwen3-32b` | Model ID |
| `MONGO_DATABASE_NAME` | `docs-agent-db` | DB name in MongoDB |
| `AGENTOPS_API_KEY` | *(empty)* | AgentOps telemetry key |
| `JWT_EXPIRE_IN_MINUTES` | `15` | Token expiry |
| `ALLOW_ORIGINS` | `*` | CORS origins |

Dokploy stores these as an encrypted `.env` file next to your compose file.

### 4. Configure the Domain

1. Go to the **Domains** tab for your compose service
2. Add your domain: `docsagent.example.com`
3. Set the **port** to `3000` → this tells Dokploy's Traefik to route traffic to the **frontend** container
4. Wait for the SSL certificate (Dokploy auto-provisions via Let's Encrypt)

Only one domain is needed — the backend is not publicly exposed.

### 5. Deploy

Click **Deploy**. Dokploy will:
1. Clone your repo
2. Build the backend and frontend images
3. Pull the `mongo:7` image
4. Create the `dokploy-network` (if not exists)
5. Start all three containers
6. Route your domain to the frontend on port 3000

## Verifying

Check the **Logs** tab for each service:
- **mongodb**: should log "Waiting for connections"
- **backend**: should log "Uvicorn running on http://0.0.0.0:8000"
- **frontend**: should log "Listening on port 3000"

Visit `https://docsagent.example.com` — you should see the landing page.

## Persistence

- **MongoDB data**: Docker named volume `mongodb_data`
- **Uploaded docs**: Docker named volume `user_docs` mounted at `/app/uploads` in the backend container

Both survive container restarts and redeploys.

## Troubleshooting

**Frontend can't connect to backend**
- The rewrites use `http://backend:8000` — this is Docker internal DNS. Both services must be on the same `dokploy-network`.
- Check: `docker compose -p <project> exec frontend wget -qO- http://backend:8000/health` (or just check the backend logs)

**MongoDB connection refused**
- The backend container starts before MongoDB is ready. Wait ~10s after deploy. The backend will retry.
- Check env: `MONGO_DB_URL` should be `mongodb://mongodb:27017/docs-agent-db`

**Changes not reflected after push**
- Ensure the branch and compose path are correct in the service settings.
- Hit **Deploy** (not Save). Dokploy only rebuilds on explicit deploy.
