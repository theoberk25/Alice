# Where everything runs — deployment topology (2026-09-06)

Maps the hosts behind [STATUS.md](STATUS.md): which agents / MCP servers / ALICE
runtime live where, and how they talk. These are **physical hosts** (two Macs, a
Pi) + one USB device + optional Google Cloud — not VMs.

```mermaid
flowchart TB
    subgraph MAC["🖥️ Theo's Mac — dev / demo host"]
        GOOSE["Goose local agent"]
        CHAT["Goose chat UI<br/>:8791"]
        OLLAMA["Ollama :11434<br/>qwen2.5-tools"]
        ADK["ADK cloud agent<br/>adk web :8000"]
        LMCP["Light-Control MCP<br/>:8795 (mock default /<br/>governed client)"]
        DASH["Technician dashboard<br/>Vite :5173 · Tauri<br/>(not running)"]
        FEED["runtime_feed bridge<br/>:8788 (read-only)"]
        BMCP["Decision-Brief MCP<br/>:8793 (not running)"]
    end

    subgraph PI["🍓 Raspberry Pi — alice-pi-01 · 192.168.50.20"]
        RT["ALICE runtime :8080<br/>/request · /events · /sync-status"]
        ENF["Enforcement gateway<br/>SerialLightController"]
        LEDGER["USB ledger<br/>/mnt/alice-usb (ext4)"]
        WWK["Wazuh worker / uploader"]
    end

    ESP["💡 XIAO ESP32-S3<br/>USB-serial · 8 LEDs<br/>(ESP-LIGHT-01..08)"]

    subgraph JARED["🖥️ Jared's Mac — 192.168.50.50"]
        WAZ["Wazuh indexer :9200"]
        ENT["Enterprise permissions / SIEM"]
    end

    subgraph GCP["☁️ Google Cloud (optional)"]
        GEM["Gemini API<br/>(free AI Studio key)"]
        AE["Vertex AI Agent Engine<br/>(planned, gated)"]
    end

    %% agent -> tools
    CHAT -->|spawns| GOOSE
    GOOSE -->|MCP :8795| LMCP
    GOOSE -->|local model| OLLAMA
    ADK -->|MCP :8795| LMCP
    ADK -->|LLM| GEM
    ADK -.->|deploy| AE

    %% MCP -> ALICE (governed, recommended)
    LMCP ==>|signed set_light_state<br/>POST /request · via SSH tunnel :18080| RT
    RT --> ENF
    ENF ==>|serial| ESP
    RT --> LEDGER
    RT --> WWK
    WWK -->|TLS :9200| WAZ

    %% dashboard + brief
    FEED -->|read-only :18080→:8080| RT
    DASH --> FEED
    BMCP -.->|holds + briefs| RT
    BMCP -.-> DASH

    classDef live fill:#0f5132,stroke:#22c55e,color:#e6ffef;
    classDef planned fill:#3a2f00,stroke:#d1a000,color:#fff7e0,stroke-dasharray:4 3;
    class GOOSE,CHAT,OLLAMA,LMCP,RT,ENF,LEDGER,WWK,ESP,WAZ,ENT live;
    class ADK,DASH,FEED,BMCP,GEM,AE planned;
```

## Host / process map

| Host | Runs today | Planned / optional |
| --- | --- | --- |
| **Theo's Mac** (dev/demo) | Goose agent, chat UI `:8791`, Light MCP `:8795` (mock), Ollama `:11434` | ADK cloud agent (`adk web :8000`), dashboard (Vite `:5173`), `runtime_feed :8788`, Brief MCP `:8793` |
| **Raspberry Pi** `alice-pi-01` (`192.168.50.20`) | ALICE runtime `:8080`, enforcement + `SerialLightController`, USB ledger, Wazuh worker | Light MCP in `esp` mode could run **here** instead (direct serial, bypasses gate) |
| **XIAO ESP32-S3** | 8 LEDs over **USB-serial to the Pi** (no IP, no network) | real power-grid schema |
| **Jared's Mac** (`192.168.50.50`) | Wazuh indexer `:9200`, enterprise permissions/SIEM | — |
| **Google Cloud** | Gemini API (free AI Studio key) — called by the ADK agent | Vertex AI Agent Engine deploy (gated behind human checkpoint) |

## The one that moves: the Light MCP
- **`mock`** (now) — on the Mac, no hardware, no Pi.
- **`alice`** (recommended) — MCP stays on the **Mac**, signs requests, and lets **ALICE on the Pi** decide/enforce/audit → light. Only needs to *reach* the Pi (SSH tunnel `:18080`→Pi `:8080`).
- **`esp`** (bench) — MCP runs **on the Pi** and drives the XIAO over serial directly; bypasses the ALICE gate.

_Green = running/verified · dashed amber = planned or not yet started._
