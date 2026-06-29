# 10 — State Management & Realtime

---

## Client State Architecture

### Server State — TanStack Query
All API data fetched via `@hermes/sdk` client.

```typescript
// Example hooks
useToday()           // GET /api/v1/today, staleTime: 60_000
useDispatchActive()  // GET /api/v1/dispatch/active, refetchInterval: false (SSE)
useWorkflows()       // GET /api/v1/workflows
useServicesHealth()  // GET /api/v1/services, staleTime: 30_000
```

Query keys:
```
['today']
['dispatch', 'active']
['dispatch', id]
['workflows']
['workflows', id]
['services']
['cron']
['nightly', 'latest']
```

### UI State — Zustand
```typescript
interface UIStore {
  sidebarCollapsed: boolean;
  activeSpace: SpaceId;
  drawer: { open: boolean; type: string; id: string | null };
  commandPaletteOpen: boolean;
  aiChatOpen: boolean;
  profileMode: 'auto' | 'manual';
  manualProfile: string | null;
}
```

### Optimistic Updates
- Task lane move: optimistic `tasks` cache update, rollback on error
- Dispatch enqueue: prepend to `dispatch/active` cache
- Workflow create: append to `workflows` list

---

## Realtime — SSE Primary

### Why SSE over WebSocket
- Unidirectional updates (server → client) cover 95% of cases
- Simpler infra, works through proxies
- WebSocket reserved for bidirectional AI chat streaming (Phase 4)

### Event Stream
`GET /api/v1/stream/events`

Headers: `Accept: text/event-stream`

### Event Types

| Event | Payload | Trigger |
|-------|---------|---------|
| `dispatch.updated` | `{ id, status, ... }` | dispatch_engine finalize |
| `dispatch.output` | `{ id, stdout_tail }` | stdout reader thread |
| `workflow.updated` | `{ id, status }` | subtask sync |
| `nightly.job` | `{ run_id, job_key, status }` | scheduler |
| `alert` | `{ severity, title, ... }` | failure detection |
| `heartbeat` | `{ ts }` | every 30s |

### Server Implementation
```python
# FastAPI SSE
async def event_generator():
    pubsub = redis.pubsub()
    await pubsub.subscribe("hermes:events")
    async for message in pubsub.listen():
        yield f"event: {message['type']}\ndata: {json.dumps(message['data'])}\n\n"
```

dispatch_engine publishes to Redis on state changes.

### Client Implementation
```typescript
useEffect(() => {
  const es = new EventSource('/api/v1/stream/events');
  es.addEventListener('dispatch.updated', (e) => {
    queryClient.invalidateQueries(['dispatch', 'active']);
  });
  return () => es.close();
}, []);
```

---

## Polling Fallback
If SSE disconnects, fall back to 30s polling for active dispatches only.

---

## Offline / PWA (Phase 6)
- Cache Today briefing in IndexedDB
- Service worker serves stale briefing when offline
- Show "offline" banner; disable actions

---

## BFF Pattern (Optional)
Next.js `app/api/` routes can proxy to FastAPI for:
- Cookie auth bridging
- SSE proxy (avoid CORS)
- Response shaping for RSC

Default: web calls FastAPI directly via `NEXT_PUBLIC_API_URL`.

---

*Next: [11-automation-and-nightly.md](./11-automation-and-nightly.md)*
