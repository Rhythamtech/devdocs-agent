# DevDocs Agent — Production Database Design

> **Stack: MongoDB**
> Written from a production engineering lens. This covers every collection you need, the exact document shapes, all indexes, TTL policies, and the migration path from the current ad-hoc state.

---

## Overview — What Needs to Be Stored

| Domain | Current State | What's Missing |
|---|---|---|
| Users | ✅ `users` collection exists | No `role`, no `is_active`, raw password field not dropped |
| Sessions | ⚠️ Managed internally by Agno's `MongoDb` | No user→session ownership link |
| Chat History | ⚠️ Managed by Agno, opaque shape | No per-user isolation, no message-level metadata |
| Usage / Audit | ❌ Not tracked | Token counts, latency, tool calls per request |
| Rate Limit State | ❌ In-memory via SlowAPI | Resets on restart, not shared across instances |

---

## Database: `devdocs`

---

## Collection 1: `users`

### Purpose
Stores registered users, their credentials, role, and account lifecycle metadata.

### Document Shape

```json
{
  "_id": ObjectId("..."),
  "username": "rhytham",
  "email": "rhytham@example.com",
  "hash_password": "$argon2id$v=19$...",
  "role": "user",
  "is_active": true,
  "created_at": ISODate("2026-06-09T18:00:00Z"),
  "updated_at": ISODate("2026-06-09T18:00:00Z"),
  "last_login_at": ISODate("2026-06-09T22:00:00Z"),
  "login_count": 14
}
```

### Field Reference

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Auto-generated primary key |
| `username` | string | Lowercased, trimmed. Unique. |
| `email` | string | Lowercased, trimmed. Unique. |
| `hash_password` | string | Argon2id hash. Never return this in API responses. |
| `role` | string | `"user"` or `"admin"`. Default: `"user"`. |
| `is_active` | bool | Soft-delete flag. Inactive users can't login. |
| `created_at` | date | Set once at signup. |
| `updated_at` | date | Updated on every profile change. |
| `last_login_at` | date | Updated on every successful login. |
| `login_count` | int | Increment on each login. Useful for analytics. |

### Indexes

```js
// Unique lookup indexes (already partially created)
db.users.createIndex({ "username": 1 }, { unique: true })
db.users.createIndex({ "email": 1 }, { unique: true })

// For admin listing / filtering by role
db.users.createIndex({ "role": 1, "created_at": -1 })

// For soft-delete filtering
db.users.createIndex({ "is_active": 1 })
```

### What to Fix From Current Code

- `data["password"]` is being stored in the raw document — **the plain password is currently being persisted to MongoDB**. In `router.py` line 68, you call `data.update({"hash_password": ...})` but never remove `data["password"]`. Add `data.pop("password")` before the insert.
- Add `role` and `is_active` defaults at insert time.
- Add `updated_at` and `last_login_at` fields.

---

## Collection 2: `sessions`

### Purpose
Tracks the relationship between a user and a chat session. Agno manages the internal message log; this collection provides the ownership record and metadata needed by your API.

> **Why separate from Agno's internal table?** Agno's `MongoDb` backend manages its own session/message storage internally. You don't control its schema. This collection is the "envelope" — it tells your app *who owns* which session and when it was last used.

### Document Shape

```json
{
  "_id": ObjectId("..."),
  "session_id": "ses_01j5f3g8h9...",
  "user_id": ObjectId("..."),
  "title": "How does ACID work in Postgres?",
  "message_count": 7,
  "is_archived": false,
  "created_at": ISODate("2026-06-09T18:00:00Z"),
  "last_active_at": ISODate("2026-06-09T22:00:00Z")
}
```

### Field Reference

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Auto-generated |
| `session_id` | string | UUID or nanoid. This is what you pass to Agno. |
| `user_id` | ObjectId | FK reference to `users._id` |
| `title` | string | Derived from the first message (first 80 chars). Shows in sidebar. |
| `message_count` | int | Increment on each turn. Avoids a full count query. |
| `is_archived` | bool | User can archive/hide a session without deleting it. |
| `created_at` | date | When the session started. |
| `last_active_at` | date | Updated on every new message. Used for "recent chats" sorting. |

### Indexes

```js
// Primary access pattern: "list all sessions for user X, newest first"
db.sessions.createIndex({ "user_id": 1, "last_active_at": -1 })

// Lookup by session_id (used in /ask and /chats to validate ownership)
db.sessions.createIndex({ "session_id": 1 }, { unique: true })

// Filter archived sessions
db.sessions.createIndex({ "user_id": 1, "is_archived": 1 })

// Auto-expire sessions with no activity in 90 days
db.sessions.createIndex(
  { "last_active_at": 1 },
  { expireAfterSeconds: 7776000 }   // 90 days
)
```

---

## Collection 3: `audit_logs`

### Purpose
Immutable append-only log of every agent request. Invaluable for debugging bad answers, monitoring costs, and detecting abuse.

### Document Shape

```json
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "session_id": "ses_01j5f3g8h9...",
  "request_id": "req_01j5abc...",
  "prompt": "What is the CAP theorem?",
  "prompt_length": 27,
  "response_preview": "The CAP theorem states that a distributed system...",
  "tools_called": ["grep", "read_doc"],
  "tool_call_count": 2,
  "model": "gpt-4o",
  "input_tokens": 312,
  "output_tokens": 189,
  "latency_ms": 1843,
  "status": "success",
  "error": null,
  "endpoint": "/ask/stream",
  "created_at": ISODate("2026-06-09T22:00:00Z")
}
```

### Field Reference

| Field | Type | Notes |
|---|---|---|
| `_id` | ObjectId | Auto-generated |
| `user_id` | ObjectId | Who made the request |
| `session_id` | string | Which session it belongs to |
| `request_id` | string | Unique per HTTP request (use `uuid4`). Tie logs together. |
| `prompt` | string | Full prompt text (for debugging — consider encrypting or truncating for PII) |
| `prompt_length` | int | Character count |
| `response_preview` | string | First 200 chars of agent reply |
| `tools_called` | string[] | List of tool names invoked |
| `tool_call_count` | int | Total tool calls made in this turn |
| `model` | string | Model name used |
| `input_tokens` | int | From OpenAI response metadata |
| `output_tokens` | int | From OpenAI response metadata |
| `latency_ms` | int | End-to-end time from request received to response sent |
| `status` | string | `"success"`, `"error"`, `"timeout"` |
| `error` | string? | Error message if status != success |
| `endpoint` | string | `/ask` or `/ask/stream` |
| `created_at` | date | Request timestamp |

### Indexes

```js
// Most common query: "show me recent requests for user X"
db.audit_logs.createIndex({ "user_id": 1, "created_at": -1 })

// Admin query: show all errors in the last hour
db.audit_logs.createIndex({ "status": 1, "created_at": -1 })

// Tie a request_id to a log for debugging
db.audit_logs.createIndex({ "request_id": 1 }, { unique: true })

// Auto-delete logs older than 1 year (compliance / storage management)
db.audit_logs.createIndex(
  { "created_at": 1 },
  { expireAfterSeconds: 31536000 }  // 365 days
)
```

---

## Collection 4: `refresh_tokens`

### Purpose
Currently your JWT access tokens have no revocation mechanism — once issued, they're valid until expiry. This collection enables proper token revocation (logout, force-expire on password change, etc.).

### Document Shape

```json
{
  "_id": ObjectId("..."),
  "token_hash": "sha256:a3f9c2...",
  "user_id": ObjectId("..."),
  "issued_at": ISODate("2026-06-09T22:00:00Z"),
  "expires_at": ISODate("2026-06-23T22:00:00Z"),
  "is_revoked": false,
  "revoked_at": null,
  "user_agent": "Mozilla/5.0...",
  "ip_address": "203.0.113.42"
}
```

### Field Reference

| Field | Type | Notes |
|---|---|---|
| `token_hash` | string | SHA-256 of the raw refresh token. Never store raw tokens. |
| `user_id` | ObjectId | Owner |
| `issued_at` | date | Creation time |
| `expires_at` | date | Hard expiry |
| `is_revoked` | bool | Set to `true` on logout or password change |
| `revoked_at` | date? | When it was revoked |
| `user_agent` | string | For "active sessions" UX (show device info) |
| `ip_address` | string | For anomaly detection |

### Indexes

```js
// Token lookup on every refresh
db.refresh_tokens.createIndex({ "token_hash": 1 }, { unique: true })

// List all active sessions for a user
db.refresh_tokens.createIndex({ "user_id": 1, "is_revoked": 1 })

// Auto-delete expired tokens (MongoDB TTL handles cleanup)
db.refresh_tokens.createIndex(
  { "expires_at": 1 },
  { expireAfterSeconds: 0 }
)
```

---

## Collection 5: `rate_limit_counters` *(optional — only if you go multi-instance)*

### Purpose
SlowAPI's current in-memory rate limiting resets every time the server restarts and doesn't work across multiple instances. If you ever run 2+ workers, move rate limit state to MongoDB.

### Document Shape

```json
{
  "_id": "rl:user_id:203.0.113.42:/ask",
  "count": 7,
  "window_start": ISODate("2026-06-09T22:00:00Z"),
  "expires_at": ISODate("2026-06-09T22:01:00Z")
}
```

### Indexes

```js
// TTL: auto-delete after window expires
db.rate_limit_counters.createIndex(
  { "expires_at": 1 },
  { expireAfterSeconds: 0 }
)
```

> **Note:** For high-frequency rate limiting, Redis is a much better fit than MongoDB (atomic `INCR` + `EXPIRE`). Use this collection only if you want to avoid adding Redis as a dependency.

---

## Agno's Internal Collections (Managed, Don't Touch)

Agno's `MongoDb` backend creates and manages its own collections for session persistence and message history. You will see collections like:

| Collection | Managed By | Purpose |
|---|---|---|
| `agno_sessions` (or similar) | Agno | Stores session metadata, summary state |
| `agno_messages` (or similar) | Agno | Stores the full message log per session |

**Do not manually write to these.** Your `sessions` collection (above) is the ownership layer on top. When you need to validate that user X owns session Y, check `sessions`. When you need the actual chat messages, call `agent.get_chat_history(session_id)` which reads from Agno's tables.

---

## Initialization Script

Run this once at startup (or in a migration) to set up all indexes cleanly:

```python
# backend/core/db_init.py
from pymongo import AsyncMongoClient, ASCENDING, DESCENDING
from core.config import settings

async def initialize_indexes(client: AsyncMongoClient) -> None:
    db = client[settings.MONGO_DATABASE_NAME]

    # --- users ---
    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)
    await db.users.create_index([("role", ASCENDING), ("created_at", DESCENDING)])
    await db.users.create_index("is_active")

    # --- sessions ---
    await db.sessions.create_index("session_id", unique=True)
    await db.sessions.create_index([("user_id", ASCENDING), ("last_active_at", DESCENDING)])
    await db.sessions.create_index([("user_id", ASCENDING), ("is_archived", ASCENDING)])
    await db.sessions.create_index("last_active_at", expireAfterSeconds=7_776_000)  # 90 days

    # --- audit_logs ---
    await db.audit_logs.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await db.audit_logs.create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    await db.audit_logs.create_index("request_id", unique=True)
    await db.audit_logs.create_index("created_at", expireAfterSeconds=31_536_000)  # 365 days

    # --- refresh_tokens ---
    await db.refresh_tokens.create_index("token_hash", unique=True)
    await db.refresh_tokens.create_index([("user_id", ASCENDING), ("is_revoked", ASCENDING)])
    await db.refresh_tokens.create_index("expires_at", expireAfterSeconds=0)
```

Call `await initialize_indexes(state.mongo_client)` inside the `lifespan` startup block in `main.py`, replacing the current ad-hoc index creation.

---

## Critical Fix: Plain Password Being Stored

In `router.py`, the current signup handler stores `password` (plain text) inside the MongoDB document because `data.pop("password")` is never called.

```python
# router.py — CURRENT (BROKEN)
data.update({"hash_password": hash_password(data["password"])})
# data["password"] still exists here and gets inserted!
result = await state.db.users.insert_one(data)

# FIXED
data["hash_password"] = hash_password(data.pop("password"))   # pop removes it
data["role"] = "user"
data["is_active"] = True
data["updated_at"] = datetime.datetime.now(datetime.UTC)
data["last_login_at"] = None
data["login_count"] = 0
result = await state.db.users.insert_one(data)
```

---

## Access Pattern Summary

| Query | Collection | Index Used |
|---|---|---|
| Login by username | `users` | `username_1` |
| Get user profile | `users` | `username_1` or `email_1` |
| List user's sessions (sidebar) | `sessions` | `user_id_1_last_active_at_-1` |
| Validate session ownership | `sessions` | `session_id_1` |
| Validate refresh token | `refresh_tokens` | `token_hash_1` |
| Revoke all user tokens (logout all) | `refresh_tokens` | `user_id_1_is_revoked_1` |
| Write audit log per request | `audit_logs` | insert only |
| Admin: view recent errors | `audit_logs` | `status_1_created_at_-1` |
| User: view their request history | `audit_logs` | `user_id_1_created_at_-1` |

---

## Data Flow Per Request

```
POST /ask/stream
     │
     ├─► Validate JWT → read users (username lookup)
     │
     ├─► Check session ownership → read sessions (session_id lookup)
     │   └─► If new session_id → insert into sessions
     │
     ├─► agent.stream() → Agno reads/writes its internal collections
     │
     └─► Write audit_log → insert into audit_logs
         (user_id, session_id, prompt, tools_called, latency_ms, tokens, status)
```

---

## Production Checklist

- [ ] Fix plain-password storage bug in signup
- [ ] Run `initialize_indexes()` on startup (replace the 2-line index creation in `main.py`)
- [ ] Add `role` and `is_active` to the `users` document on insert
- [ ] Create `sessions` collection with user ownership on every new session
- [ ] Wire up `audit_logs` write after every `/ask` and `/ask/stream` call
- [ ] Implement refresh token rotation (issue `refresh_token` on login, store hash in `refresh_tokens`)
- [ ] Add session ownership validation in `/chats` — verify `sessions.user_id == current_user._id` before returning history
- [ ] Enable MongoDB authentication (username + password) — never use `mongodb://localhost:27017` in production without auth
- [ ] Enable TLS on the MongoDB connection string (`mongodb+srv://...` or `?tls=true`)
- [ ] Set up MongoDB Atlas or a managed replica set — never use a single-node MongoDB in production (no redundancy, no oplog)
