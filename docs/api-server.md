# API Server

> **Module:** `src.api.server`  
> **Framework:** FastAPI 0.115+  
> **Port:** `8794` (localhost only)  
> **Run:** `python -m src.api.server`

## Overview

The API server is the bridge between the Chrome extension and the Python pipeline. It receives transcript requests from the extension, orchestrates the full translate → lookup → chain pipeline, and serves the resulting video clips over HTTP.

---

## Server Startup

```mermaid
flowchart TD
    A["python -m src.api.server"] --> B["Uvicorn starts on :8794"]
    B --> C["Lifespan: _lifespan()"]
    C --> D["Init GlossTranslator"]
    D --> E["Init WordLookup"]
    E --> F["Warmup: translate('hello')"]
    F -->|"Success"| G["Model is hot ✓"]
    F -->|"Failure"| H["Log warning<br/>(non-fatal, retry on first request)"]
    G --> I["Server accepting requests"]
    H --> I
    
    style A fill:#ff5722,color:#fff
    style I fill:#4caf50,color:#fff
```

Warmup is performed in a thread pool executor so the async event loop isn't blocked. If the LLM provider is unreachable at startup, the server still starts — the first real request will trigger lazy initialization.

---

## Endpoint Map

```mermaid
flowchart LR
    subgraph Endpoints ["API Endpoints"]
        direction TB
        E1["POST /asl/transcript<br/>(primary)"]
        E2["POST /asl<br/>(legacy single)"]
        E3["GET /clips/{name}.mp4"]
        E4["GET /health"]
        E5["GET /glosses"]
    end
    
    EXT["Chrome Extension"] -->|"Batch transcript"| E1
    EXT -->|"Health check"| E4
    EXT -->|"Play clip"| E3
    CLI["Standalone client"] -->|"Single caption"| E2
    CLI -->|"Available signs"| E5
    
    style EXT fill:#2196f3,color:#fff
    style CLI fill:#9c27b0,color:#fff
```

---

## Endpoints

### `POST /asl/transcript` — Batch Transcript Translation

The primary endpoint used by the Chrome extension. Fetches the full transcript for a YouTube video, batch-translates all lines to ASL gloss, looks up clips, and chains them.

**Request:**
```json
{
  "video_id": "dQw4w9WgXcQ"
}
```

**Response (200):**
```json
{
  "entries": [
    {
      "start_ms": 1200,
      "end_ms": 4800,
      "text": "what is your name",
      "glosses": ["YOUR", "NAME", "WHAT"],
      "found": ["YOUR", "NAME", "WHAT"],
      "missing": [],
      "clip_url": "http://127.0.0.1:8794/clips/ext_abc123.mp4",
      "clip_duration_ms": 2850
    }
  ],
  "cached": false
}
```

**Error Responses:**
| Status | Condition | Body |
|--------|-----------|------|
| 400 | Invalid `video_id` format (must be 11 chars, `[A-Za-z0-9_-]`) | `{"error": "invalid video_id"}` |
| 404 | Transcript fetch or processing failed | `{"error": "transcript unavailable: ..."}` |

**Processing flow:**

```mermaid
sequenceDiagram
    participant Ext as Chrome Extension
    participant API as FastAPI Server
    participant Cache as _transcript_cache
    participant Fetch as fetch_transcript()
    participant LLM as GlossTranslator
    participant Look as WordLookup
    participant Chain as chain_clips()
    
    Ext->>API: POST /asl/transcript {video_id}
    API->>API: Validate video_id regex
    API->>Cache: Check video_id in cache?
    
    alt Cache hit
        Cache-->>API: Cached entries
        API-->>Ext: TranscriptResponse (cached=true)
    else Cache miss
        API->>Fetch: fetch_transcript(video_id)
        Fetch-->>API: [{start_ms, end_ms, text}, ...]
        API->>LLM: translate_batch(texts)
        LLM-->>API: [["GLOSS", ...], ...]
        
        loop For each segment
            API->>Look: lookup_sequence(glosses)
            Look-->>API: [{gloss, path, found}, ...]
            API->>Chain: chain_clips(entries, clip_name)
            Chain-->>API: {path, duration_ms}
        end
        
        API->>Cache: Store entries
        API-->>Ext: TranscriptResponse (cached=false)
    end
```

---

### `POST /asl` — Single Caption Translation (Legacy)

Translates a single caption line. Used before the batch architecture was implemented.

**Request:**
```json
{
  "text": "what is your name"
}
```

**Response (200):**
```json
{
  "glosses": ["YOUR", "NAME", "WHAT"],
  "found": ["YOUR", "NAME", "WHAT"],
  "missing": [],
  "clip_url": "http://127.0.0.1:8794/clips/ext_abc123.mp4",
  "clip_duration_ms": 2850,
  "cached": false
}
```

---

### `GET /clips/{filename}` — Serve Chained Clips

Serves pre-chained MP4 files from `assets/chained/`. The Chrome extension uses clip URLs from transcript responses to load these.

**Security:** Path traversal protection — rejects filenames containing `/`, `\`, or `..`.

**Headers:**
- `Access-Control-Allow-Origin: *`
- `Cache-Control: public, max-age=3600`

---

### `GET /health` — Health Check

Returns server status and timestamp. Used by the extension popup.

**Response:**
```json
{
  "status": "ok",
  "time": 1719000000.123
}
```

---

### `GET /glosses` — Available Gloss List

Returns all ASL glosses available in the WLASL dataset.

**Response:**
```json
{
  "count": 1998,
  "glosses": ["ABOUT", "ABOVE", "ACCEPT", "..."]
}
```

---

## Caching Strategy

```mermaid
flowchart TD
    subgraph Caches ["In-Memory Caches"]
        C1["_transcript_cache<br/>Key: video_id (str)<br/>Value: list[dict]<br/>Eviction: None (grows unbounded)"]
        C2["_response_cache<br/>Key: MD5 of text<br/>Value: AslResponse dict<br/>Max: 500 entries (FIFO evict 100)"]
    end
    
    E1["POST /asl/transcript"] --> C1
    E2["POST /asl"] --> C2
    
    style C1 fill:#1565c0,color:#fff
    style C2 fill:#6a1b9a,color:#fff
```

| Cache | Key | Used By | Max Size | Eviction |
|-------|-----|---------|----------|----------|
| `_transcript_cache` | `video_id` string | `/asl/transcript` | Unbounded | None |
| `_response_cache` | MD5 of normalized text | `/asl` | 500 entries | FIFO (oldest 100 removed) |

Both caches are in-memory only and reset on server restart.

---

## CORS Configuration

The server allows cross-origin requests from:

| Origin | Purpose |
|--------|---------|
| `https://www.youtube.com` | Chrome extension running on YouTube |
| `chrome-extension://*` | Extension popup and background script |
| `http://localhost:*` | Local development |
| `http://127.0.0.1:*` | Local development |

All HTTP methods and headers are allowed.

---

## Thread Pool Execution

All blocking pipeline operations (LLM calls, FFmpeg, file I/O) run in the default thread pool executor via `loop.run_in_executor(None, ...)`. This prevents the async event loop from being blocked during potentially slow operations like:

- LLM translation (100ms–10s depending on provider)
- FFmpeg clip concatenation (50–500ms per clip chain)
- Transcript fetching (500ms–3s)

---

## Data Models

```mermaid
classDiagram
    class TranscriptRequest {
        +str video_id
    }
    
    class TranscriptResponse {
        +list~TranscriptEntry~ entries
        +bool cached
    }
    
    class TranscriptEntry {
        +int start_ms
        +int end_ms
        +str text
        +list~str~ glosses
        +list~str~ found
        +list~str~ missing
        +str|None clip_url
        +int clip_duration_ms
    }
    
    class CaptionRequest {
        +str text
    }
    
    class AslResponse {
        +list~str~ glosses
        +list~str~ found
        +list~str~ missing
        +str|None clip_url
        +int clip_duration_ms
        +bool cached
    }
    
    TranscriptResponse --> TranscriptEntry
```
