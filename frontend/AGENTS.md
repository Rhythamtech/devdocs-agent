<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# DevDocs Frontend

## Setup
1. `npm install`
2. Copy `.env.example` to `.env.local` and configure:
   - `NEXT_PUBLIC_MOCK_MODE=true` — use mock auth/chat (no backend needed)
   - `NEXT_PUBLIC_API_URL=http://localhost:8000` — backend URL
3. `npm run dev` — starts on port 3000

## Mock Credentials
When `NEXT_PUBLIC_MOCK_MODE=true`, use:
- **Username:** `admin`
- **Password:** `admin`

## Pages
| Route | Auth | Description |
|---|---|---|
| `/` | No | Landing page with CTA |
| `/login` | No | Login (mock: admin/admin) |
| `/signup` | No | Signup form |
| `/chat` | Yes | Chat with SSE streaming + tool calls |
| `/profile` | Yes | User profile, logout |

## Architecture
- **Auth:** JWT stored in localStorage, AuthContext provider
- **Chat:** Custom SSE parser reads `POST /ask/stream` from backend
- **Tool calls:** Parsed from `data: Tool Call: name(args)` SSE events, shown as collapsible cards
- **Sidebar:** Session list loaded from `GET /sessions`
- **UI:** shadcn/ui + assistant-ui components (tooltip, collapsible, scroll-area, etc.)

## Design System (NovaFlow)
Defined in `DESIGN.md`. Key tokens:
| Token | Value | Usage |
|---|---|---|
| Primary | `#FB923C` | Accent, emphasis |
| Secondary | `#F97316` | Border, supporting accent |
| Neutral/Background | `#0A0908` | Page bg, dark foundation |
| Surface | `#FFFFFF` | Card bg, elevated surfaces |
| Text Primary | `#737373` | Body text on dark bg |
| Text Secondary | `#525252` | Text on white cards |
| Muted | `#A3A3A3` | Ghost/secondary button text |
| Border | `#F97316` | All borders, separators |
| Display | Inter 48px/500 | Hero headings |
| Body | JetBrains Mono 10px/400 | Body and description text |
| Labels | JetBrains Mono 9px/400, 1.08px tracking | Buttons, sidebar items, labels |
| Radius | 6px base | Buttons, inputs |
| Gradient shell | 24px outer, 23px inner | White gradient border on cards |

**Card variant:** `variant="gradient"` renders the white gradient border shell (`linear-gradient(rgba(255,255,255,0.14), rgba(255,255,255,0.02) 40%, rgba(255,255,255,0.01))`).**Buttons:**
- **default/primary:** bg `#0A0908`, text `#737373` — for use on white surfaces
- **outline/ghost/secondary:** text `#A3A3A3`, border `rgba(255,255,255,0.05)` — for use on dark surfaces
- **link:** text `#737373`, radius 8px

## Key Files
- `src/lib/api.ts` — API client, SSE connection, mock mode
- `src/contexts/AuthContext.tsx` — Auth state management
- `src/app/chat/page.tsx` — Main chat page
- `src/components/chat/ToolCallCard.tsx` — Tool call display component
- `src/hooks/useChatHistory.ts` — Session list management

## Missing Backend Endpoints
The frontend expects these backend endpoints:
- `GET /sessions` — list user's chat sessions
- `DELETE /sessions` — clear all sessions
- `DELETE /sessions/{session_id}` — delete single session
