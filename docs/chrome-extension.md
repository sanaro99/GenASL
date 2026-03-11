# Chrome Extension

> **Directory:** `chrome-extension/`  
> **Manifest:** Manifest V3  
> **Target:** YouTube (`https://www.youtube.com/*`)

## Overview

The GenASL Chrome Extension is the user-facing delivery mechanism. It injects a Picture-in-Picture ASL overlay onto YouTube video pages, fetches the full transcript and translation from the local FastAPI server, and plays timed ASL clips synchronized with the YouTube video playback — including pause, play, seek, and speed synchronization.

---

## Extension Architecture

```mermaid
flowchart TD
    subgraph Extension ["Chrome Extension"]
        CS["content.js<br/>Injected on YouTube"]
        BG["background.js<br/>Service worker"]
        POP["popup.html + popup.js<br/>Extension popup UI"]
        CSS["overlay.css<br/>Overlay styling"]
    end
    
    subgraph YouTube ["YouTube Page"]
        VID["<video> element"]
        DOM["YouTube DOM"]
    end
    
    subgraph Server ["FastAPI :8794"]
        API["REST API"]
        CLIPS["Clip files"]
    end
    
    subgraph Storage ["chrome.storage.local"]
        PREFS["aslEnabled<br/>aslSizeIndex<br/>aslShowGloss"]
    end
    
    POP -->|"Toggle/resize/gloss"| PREFS
    PREFS -->|"storage.onChanged"| CS
    CS -->|"Read currentTime"| VID
    CS -->|"POST /asl/transcript"| API
    CS -->|"GET /clips/*.mp4"| CLIPS
    POP -->|"GET /health"| API
    CS -->|"Inject overlay"| DOM
    
    style Extension fill:#1a1a2e,stroke:#2196f3,color:#eee
    style YouTube fill:#282828,stroke:#ff0000,color:#eee
    style Server fill:#0d2137,stroke:#4caf50,color:#eee
    style Storage fill:#2d1b38,stroke:#9c27b0,color:#eee
```

---

## Content Script Lifecycle

```mermaid
flowchart TD
    A["Page load on youtube.com"] --> B["content.js injected<br/>(document_idle)"]
    B --> C["Load preferences<br/>from chrome.storage"]
    C --> D["Start polling timer<br/>(every 250ms)"]
    
    D --> E{"On /watch page?"}
    E -->|"No"| D
    E -->|"Yes"| F["Extract video ID<br/>from URL ?v=..."]
    
    F --> G{"Already loaded<br/>this video?"}
    G -->|"Yes"| H["Tick: check timestamp"]
    G -->|"No"| I["POST /asl/transcript<br/>{video_id}"]
    
    I -->|"200 OK"| J["Build aslPlaylist<br/>(sorted by start_ms)"]
    I -->|"Error"| K["Show 'transcript<br/>unavailable'"]
    
    J --> H
    
    H --> L{"currentTime in<br/>playlist entry?"}
    L -->|"Yes, new"| M["Enqueue clip<br/>+ set adaptive speed"]
    L -->|"Already playing"| D
    L -->|"No match"| D
    
    M --> N["Play overlay clip"]
    N -->|"Clip ends"| O["Play next in queue<br/>or hide overlay"]
    
    style A fill:#ff5722,color:#fff
    style J fill:#4caf50,color:#fff
    style K fill:#f44336,color:#fff
```

---

## SPA Navigation Handling

YouTube is a Single-Page Application (SPA). Navigating between videos doesn't trigger a full page reload. The extension listens for YouTube's custom navigation event:

```mermaid
flowchart LR
    A["User clicks<br/>new video"] --> B["yt-navigate-finish<br/>event fires"]
    B --> C["Reset all state:<br/>playlist, clips, videoId"]
    C --> D["Wait 1.5s for<br/>new page to load"]
    D --> E["Resume polling<br/>(new video detected)"]
    
    style A fill:#ff5722,color:#fff
    style E fill:#4caf50,color:#fff
```

On `yt-navigate-finish`:
- `aslPlaylist = []`
- `transcriptLoaded = false`
- `currentVideoId = null`
- `ytVideoListenersAttached = false`
- Clip queue cleared, overlay hidden

---

## Overlay DOM Structure

The extension injects a DOM structure into the YouTube player container:

```
#movie_player (YouTube's player)
└── #asl-overlay-root (overlay container)
    ├── #asl-overlay-video-wrap
    │   └── #asl-overlay-video (<video> element)
    ├── #asl-overlay-label ("ASL" badge)
    └── #asl-gloss-label (gloss text bar)
```

```mermaid
flowchart TB
    subgraph Overlay ["#asl-overlay-root"]
        direction TB
        subgraph VWrap ["#asl-overlay-video-wrap"]
            V["#asl-overlay-video<br/>(plays ASL clips)"]
        end
        L["#asl-overlay-label<br/>'ASL' badge<br/>(top-left, blue)"]
        G["#asl-gloss-label<br/>'YOUR  NAME  WHAT'<br/>(bottom bar, toggleable)"]
    end
    
    style Overlay fill:#1a1a2e,stroke:#2196f3,color:#eee
    style V fill:#000,stroke:#555,color:#eee
    style L fill:#2196f3,color:#fff
    style G fill:#000,stroke:#555,color:#eee
```

### Position & Sizing

| Property | Value |
|----------|-------|
| **Position** | Bottom-right of YouTube player, 60px above controls |
| **Z-index** | 2147483647 (maximum) — beats all YouTube layers |
| **Background** | `rgba(0, 0, 0, 0.65)` — semi-transparent |
| **Border radius** | 10px |
| **Transition** | 0.3s opacity fade in/out |
| **Fullscreen** | Adjusts to bottom: 80px, right: 20px |

### Size Presets

| Size | Width | Height | Label |
|------|-------|--------|-------|
| S | 160px | 130px | Small |
| M | 220px | 180px | Medium (default) |
| L | 320px | 260px | Large |
| XL | 420px | 340px | Extra Large |

Sizes use `setProperty("width", ..., "important")` to override YouTube's styles.

---

## Playback Synchronization

The extension maintains tight synchronization between the YouTube video and the ASL overlay:

```mermaid
flowchart TD
    subgraph Events ["YouTube Video Events"]
        P["pause"] --> PA["Pause overlay"]
        PL["play"] --> RE["Resume overlay"]
        S["seeked"] --> RS["Reset playlist position<br/>Clear clip queue<br/>Hide overlay"]
    end
    
    subgraph Timer ["250ms Poll Timer"]
        T["Read currentTime"] --> M["Find matching<br/>playlist entry"]
        M --> E{"New entry?"}
        E -->|"Yes"| Q["Enqueue clip"]
        E -->|"No"| T
    end
    
    style Events fill:#282828,stroke:#ff0000,color:#eee
    style Timer fill:#0d2137,stroke:#4caf50,color:#eee
```

| Event | Action |
|-------|--------|
| **YouTube pauses** | Overlay video pauses |
| **YouTube resumes** | Overlay video resumes |
| **YouTube seeks** | Reset `lastTriggeredIdx`, clear clip queue, hide overlay |
| **New video (SPA)** | Full state reset, re-fetch transcript |

---

## Extension Popup

The popup provides user controls:

```
┌────────────────────────────┐
│ 🫶 ASL Overlay             │
│                            │
│ Enable overlay     [═══●]  │
│ Show gloss text    [●═══]  │
│ Overlay size    [−] M [+]  │
│                            │
│ ● Server running           │
└────────────────────────────┘
```

### Controls

| Control | Storage Key | Default | Effect |
|---------|-------------|---------|--------|
| Enable overlay | `aslEnabled` | `true` | Show/hide entire overlay |
| Show gloss text | `aslShowGloss` | `false` | Display gloss words below video |
| Overlay size | `aslSizeIndex` | `1` (M) | Resize overlay (S/M/L/XL) |

### Server Health Check

The popup pings `GET /health` on open. Displays:
- 🟢 "Server running" — server reachable
- 🔴 "Server offline — run: python -m src.api.server" — server unreachable

---

## File Structure

```
chrome-extension/
├── manifest.json      Manifest V3 metadata
├── background.js      Service worker (minimal)
├── content.js         Main content script (~340 lines)
├── overlay.css        Overlay styling
├── popup.html         Popup UI layout
├── popup.js           Popup event handlers
└── icons/
    ├── icon48.png     Toolbar icon
    └── icon128.png    Extension page icon
```

### Manifest Permissions

```json
{
  "permissions": ["storage", "activeTab"],
  "host_permissions": [
    "https://www.youtube.com/*",
    "http://127.0.0.1:8794/*"
  ]
}
```

- `storage` — Persist user preferences
- `activeTab` — Send messages to content script
- `youtube.com` — Inject content script
- `127.0.0.1:8794` — Fetch from local API server

---

## Installation

1. Open `chrome://extensions/` in Chrome
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension/` folder
5. Navigate to any YouTube video — the overlay appears automatically

### Requirements

- The FastAPI server must be running: `python -m src.api.server`
- The server popup indicator shows green when connected
