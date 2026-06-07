## Summary
### Fastapi is a high-performance, easy-to-use, and extensible web framework for building APIs with Python
### It is built on top of starlette, which is a high-performance, low-overhead web server for Python
### For type checking, Fastapi uses pydantic
### The architecture of Fastapi is build using ASGI (Asynchronous Server Gateway Interface)
### ASGI is a specification for asynchronous web servers
### Fastapi can handle both sync and async tasks.
### The Async operations are executed in a main thread 
### Async operations are excuted in the Event loop
### Sync tasks are executed in the Thread pool.
### Non blocking I/O operations - Async
### Blocking operations Sync with Thread pool

### Uvicorn - ASGI server it communicates with HTTP, manages connections, and runs app's event loop. It's blazing fast but single-process, so it uses only one CPU core.

### Gunicorn - Process Manager (Multiple Workers). It spawns multiple worker processes and keeps them healthy (restarts crashed workers, graceful reloads). 

### Uvicorn + Gunicorn - gunicorn main:app  -k uvicorn.workers.UvicornWorker -w 4
### To handle more number of concurrent requests
### Gunicorn manages the n Uvicorn workers. Gunicorn can handle multiple spawned processes of Uvicorn.
### workers = (2 × CPU cores) + 1

### Each worker has its own event loop.
### Event loop is a coroutine-based concurrency model.
### Coroutine is a function that can be paused and resumed.
### Multiple coroutines can run concurrently in the same event loop.
### Multiple workers provide parallelism.

### For Background Tasks - Use Celery

---

# FastAPI — Complete Reference Guide

---

## What is FastAPI?

FastAPI is a **high-performance, easy-to-use, and extensible web framework** for building APIs with Python. It is designed around modern Python features — type hints, async/await — and auto-generates interactive API documentation without any extra setup.

**Core dependencies:**

| Library | Role |
|---|---|
| **Starlette** | The underlying ASGI framework — routing, middleware, WebSockets |
| **Pydantic** | Data validation, type checking, serialization |
| **Uvicorn** | ASGI server — runs the event loop and handles HTTP |
| **Gunicorn** | Process manager — spawns and manages multiple Uvicorn workers |

---

## Architecture: ASGI

FastAPI is built on the **ASGI (Asynchronous Server Gateway Interface)** specification — the modern successor to WSGI. ASGI is what enables FastAPI to handle async operations, WebSockets, Server-Sent Events, and HTTP/2.

```
Client → Uvicorn (ASGI server) → FastAPI (ASGI app) → Your route handlers
```

Unlike WSGI (Flask, classic Django), which blocks a thread per request, ASGI allows a single thread to handle thousands of concurrent connections by yielding control during I/O waits.

---

## Sync vs Async

FastAPI can handle **both sync and async** tasks — and treats them differently internally.

### Async operations — `async def`

```python
@app.get("/users/{id}")
async def get_user(id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, id)   # non-blocking — yields to event loop
    return user
```

- Runs directly on the **main thread inside the event loop**
- `await` suspends the coroutine — the event loop runs other coroutines while waiting
- Zero thread overhead — thousands of concurrent async routes can run on a single thread
- **Non-blocking I/O operations** — database queries, HTTP calls, file reads, Redis

**Use async libraries:** `asyncpg`, `httpx`, `aiofiles`, `aioredis`

> **Never** call blocking code inside `async def` — it freezes the entire event loop.

```python
# WRONG — blocks the event loop for every request
async def get_data():
    time.sleep(2)           # freezes everything
    requests.get(url)       # sync HTTP in async context

# CORRECT
async def get_data():
    await asyncio.sleep(2)
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
```

---

### Sync operations — `def`

```python
@app.get("/report")
def generate_report():
    data = psycopg2.connect(...)   # legacy sync driver — fine here
    return process(data)
```

- FastAPI automatically offloads plain `def` routes to a **thread pool executor**
- The event loop is **not blocked** — it submits the work to a thread and continues
- **Blocking operations** that can't be made async: legacy sync libraries, CPU-heavy work, PIL, NumPy

> FastAPI uses `anyio.to_thread.run_sync()` internally to push sync routes into threads.

---

### Worst pattern to avoid

```python
# WORST — async def + blocking call inside = blocks the event loop
async def bad_route():
    result = some_sync_library.query()   # blocks all other requests
    return result
```

If you must use a blocking library inside an async context, wrap it explicitly:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

async def safe_route():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, blocking_function, arg)
    return result
```

---

## The Event Loop

The event loop is the heart of async Python. It is a **coroutine-based concurrency model** running on a single OS thread.

### How it works

1. Event loop starts and runs continuously
2. A coroutine hits `await` → it is **suspended** and added to the waiting queue
3. The OS signals (via `epoll`/`kqueue`) when the awaited I/O is ready
4. The event loop **resumes** the coroutine and runs it until the next `await`
5. Meanwhile, other coroutines ran — no thread was ever blocked

```
Event Loop (single thread)
│
├── Coroutine A runs → hits await db.get() → suspended
├── Coroutine B runs → hits await redis.get() → suspended
├── Coroutine C runs → completes → response sent
├── OS: "DB result ready for A" → A resumed → completes
└── OS: "Redis ready for B" → B resumed → completes
```

### Coroutines

A **coroutine** is a function defined with `async def` that can be **paused and resumed**. It is not a thread — it cooperatively yields control at `await` points.

```python
async def fetch_user(user_id: int) -> User:
    # pauses here, gives control back to event loop
    user = await db.get(User, user_id)
    # resumes when DB responds
    return user
```

Multiple coroutines run **concurrently** in the same event loop — not in parallel. One thread, many coroutines interleaved.

---

## Thread Pool

The thread pool handles all work that cannot be made async — legacy sync libraries, CPU computation, anything that would block.

```
Event Loop Thread
│
├── async routes run here directly
└── sync routes → submitted to thread pool → result returned as future
        │
        ├── Thread 1: psycopg2 DB query
        ├── Thread 2: PIL image resize
        └── Thread 3: CSV parsing
```

FastAPI's default thread pool has **40 threads**. You can customise it:

```python
import anyio
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # set thread pool size at startup
    limiter = anyio.to_thread.current_default_thread_limiter()
    limiter.total_tokens = 100
    yield

app = FastAPI(lifespan=lifespan)
```

> For **CPU-bound** work (image processing, ML inference, heavy computation) use a `ProcessPoolExecutor` instead — Python's GIL means threads don't give real CPU parallelism.

```python
from concurrent.futures import ProcessPoolExecutor

cpu_pool = ProcessPoolExecutor()

@app.post("/resize")
async def resize(file: UploadFile):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(cpu_pool, heavy_image_work, data)
    return result
```

---

## Concurrency vs Parallelism

| | Concurrency | Parallelism |
|---|---|---|
| **Definition** | Dealing with many things at once | Doing many things at once |
| **Mechanism** | Event loop + coroutines | Multiple OS threads or processes |
| **CPU cores used** | 1 | N |
| **Best for** | I/O-bound work | CPU-bound work |
| **FastAPI mechanism** | `async def` + `await` | Gunicorn multi-worker |

FastAPI gives you **both**:
- **Concurrency** via the async event loop (thousands of concurrent I/O-bound requests on one core)
- **Parallelism** via Gunicorn workers (multiple processes, each with their own event loop, spread across CPU cores)

---

## Uvicorn

**Uvicorn** is the ASGI server. It is the bridge between raw HTTP and your FastAPI app.

**What it does:**
- Listens for incoming TCP connections
- Parses HTTP/1.1 and HTTP/2 requests into ASGI scope dictionaries
- Manages WebSocket connections
- Runs the asyncio event loop
- Passes requests to your FastAPI app and sends responses back

**What it does not do:**
- Multi-process management (that is Gunicorn's job)
- TLS termination in production (use Nginx)
- Serving static files efficiently (use Nginx)

```bash
# Development — single process, auto-reload on file change
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production (single process, not recommended for multi-core)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Uvicorn is **blazing fast** but single-process — it uses only **one CPU core**. To use all cores, you need Gunicorn.

---

## Gunicorn

**Gunicorn** is a production process manager. It does not speak ASGI — instead it spawns and manages multiple Uvicorn processes, each of which is a full ASGI server with its own event loop.

**What it does:**
- Spawns N worker processes at startup
- Monitors workers — restarts crashed workers automatically
- Handles graceful reloads (`kill -HUP <pid>`) — zero-downtime deploys
- Distributes incoming connections across workers
- Sets maximum request limits per worker (prevents memory leaks)

```bash
gunicorn main:app \
  -k uvicorn.workers.UvicornWorker \
  --workers 9 \
  --worker-connections 1000 \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  --max-requests 1000 \
  --max-requests-jitter 100
```

### Worker formula

```
workers = (2 × CPU cores) + 1
```

| CPU cores | Recommended workers |
|---|---|
| 1 | 3 |
| 2 | 5 |
| 4 | 9 |
| 8 | 17 |

### Each worker is independent

```
Gunicorn master process
│
├── Uvicorn Worker 1  →  own event loop  →  handles 100s of async requests
├── Uvicorn Worker 2  →  own event loop  →  handles 100s of async requests
├── Uvicorn Worker 3  →  own event loop  →  handles 100s of async requests
└── Uvicorn Worker N  →  own event loop  →  handles 100s of async requests
```

Each worker has its **own event loop**, its own memory space, and runs on a separate OS process. This is true CPU parallelism — each worker can run on a different core simultaneously.

> **Important:** Because workers are separate processes, they do **not share state**. For shared state (sessions, WebSocket rooms, rate limit counters), use an external store — Redis.

---

## Background Tasks

### Tier 1 — Built-in `BackgroundTasks` (same process)

For lightweight work that should happen after the response is sent — emails, audit logs, webhooks.

```python
from fastapi import BackgroundTasks

def send_welcome_email(email: str):
    # runs after response is returned to client
    smtp_client.send(to=email, subject="Welcome!")

@app.post("/register")
async def register(user: UserCreate, bg: BackgroundTasks, db=Depends(get_db)):
    new_user = await create_user(db, user)
    bg.add_task(send_welcome_email, new_user.email)
    return {"id": new_user.id}   # response sent immediately
```

**Limitations:** Same process. If the worker crashes, the task is lost. Not retryable. Not suitable for heavy work.

---

### Tier 2 — Celery (separate worker processes)

For heavy, crash-resilient, retryable background jobs — video processing, ML inference, bulk operations, scheduled tasks.

```
FastAPI app  →  enqueue task  →  Redis / RabbitMQ (broker)
                                        │
                              Celery workers (separate processes)
                                        │
                              Execute task, store result in Redis
```

```python
# tasks.py
from celery import Celery

celery = Celery("tasks", broker="redis://localhost:6379/0")

@celery.task(bind=True, max_retries=3)
def process_video(self, video_id: int):
    try:
        run_ffmpeg(video_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# main.py
@app.post("/upload")
async def upload_video(video_id: int):
    process_video.delay(video_id)   # enqueue — returns immediately
    return {"status": "queued", "video_id": video_id}
```

**Celery features:**
- `max_retries` with exponential backoff
- Task priorities and routing
- **Celery Beat** — cron-like scheduler for periodic tasks (daily reports, cache warming, cleanup)
- Result backend — store and query task results
- Monitoring via Flower dashboard

---

### Tier 3 — ARQ (async Celery alternative)

ARQ is an async-native task queue built for asyncio — simpler than Celery, Redis-backed, ideal for FastAPI.

```python
import arq

# worker.py
async def process_order(ctx, order_id: int):
    db = ctx["db"]
    await fulfill_order(db, order_id)

class WorkerSettings:
    functions = [process_order]
    redis_settings = arq.connections.RedisSettings()

# main.py
@app.post("/order")
async def create_order(order: OrderCreate, redis=Depends(get_redis)):
    await redis.enqueue_job("process_order", order.id)
    return {"status": "queued"}
```

---

## Quick decision guide

| Situation | Pattern |
|---|---|
| DB query, HTTP call, Redis | `async def` + async library |
| Legacy sync library (psycopg2, boto3) | `def` route — FastAPI uses thread pool |
| CPU-heavy work (PIL, NumPy, ML) | `def` route or `ProcessPoolExecutor` |
| Blocking inside async context | `loop.run_in_executor(executor, fn, arg)` |
| Fire-and-forget after response | `BackgroundTasks` |
| Retryable, crash-safe heavy jobs | Celery or ARQ |
| Scheduled / periodic jobs | Celery Beat |
| Real-time bidirectional comms | WebSockets (FastAPI native) |
| One-way server push | SSE via `sse-starlette` |
| Share state across workers | Redis |
| **Never do** | `async def` + `time.sleep()` / blocking call directly |

---

## Production server stack

```
Internet
   │
Cloudflare / AWS ALB   (DDoS, CDN, anycast)
   │
Nginx                  (TLS termination, static files, rate limiting, gzip)
   │
Gunicorn               (process manager, worker lifecycle)
   │
├── Uvicorn Worker 1   (event loop, ASGI)
├── Uvicorn Worker 2   (event loop, ASGI)
└── Uvicorn Worker N   (event loop, ASGI)
        │
    FastAPI App
    ├── Middleware stack   (CORS, auth, logging, request ID)
    ├── Router             (path + method matching)
    ├── Dependency injection (DB session, current user, settings)
    ├── Pydantic           (validation in, serialization out)
    └── Route handler      (your business logic)
        │
   ┌────┴─────────────────────────────┐
   │                                  │
PostgreSQL (asyncpg)            Redis (aioredis)
   │                                  │
Alembic migrations           ├── Cache (fastapi-cache2)
                             ├── Sessions
                             ├── Rate limiting
                             └── Celery / ARQ broker
```

### Recommended production command

```bash
gunicorn main:app \
  -k uvicorn.workers.UvicornWorker \
  --workers 9 \
  --worker-connections 1000 \
  --bind 0.0.0.0:8000 \
  --timeout 60 \
  --graceful-timeout 30 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --log-level info \
  --access-logfile -
```

---

## Key mental model

> **Async gives you concurrency. Gunicorn workers give you parallelism. You need both.**

One Uvicorn worker with async routes can handle thousands of I/O-bound requests concurrently on a single CPU core — because while one request waits for the database, the event loop runs another. But it only uses one CPU core. Add Gunicorn workers to spread load across all cores. The result: each core handles thousands of concurrent requests, and all cores run simultaneously.

```
1 Uvicorn worker   =  1 CPU core  ×  1000s of concurrent async requests
N Gunicorn workers =  N CPU cores ×  1000s of concurrent async requests each
                   =  massive total throughput with a lean Python process count
```