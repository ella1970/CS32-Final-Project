# SwimLoad Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENSOR LAYER                              │
│  ESP32 + MPU6050 (IMU)  +  DRV2605 (haptics)                   │
│  • ~166 Hz sampling                                             │
│  • On-device load accumulation                                  │
│  • Haptic alert when daily max load threshold is reached        │
│  • BLE stream to mobile app                                     │
└─────────────────┬───────────────────────────────────────────────┘
                  │ BLE (JSON frames) or USB Serial
┌─────────────────▼───────────────────────────────────────────────┐
│                      MOBILE / WEB APP                            │
│  React (Vite)  —  runs in browser or React Native               │
│  • Session start/stop                                           │
│  • Live load graph (BLE stream)                                 │
│  • CSV upload (bulk ingest)                                     │
│  • Pain scale input (VAS 0-10)                                  │
│  • Cumulative load charts, ROM charts                           │
│  • AI recommendation display                                    │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP / REST
┌─────────────────▼───────────────────────────────────────────────┐
│                       BACKEND API                                │
│  FastAPI (Python)                                               │
│                                                                 │
│  /subjects   → manage research participants                     │
│  /sessions   → start, stop, list, table                        │
│  /imu        → bulk ingest, CSV upload                         │
│  /analysis   → cumulative load, arm comparison, intra-session  │
│  /recommendations → AI safe loading zone generation            │
└────────┬────────────────────────────┬───────────────────────────┘
         │                            │
┌────────▼────────┐        ┌──────────▼──────────────────────────┐
│   DATABASE      │        │         AI LAYER                    │
│  PostgreSQL or  │        │  Anthropic Claude API               │
│  SQLite (dev)   │        │  • Session analysis                 │
│                 │        │  • Safe load zone calculation       │
│  Tables:        │        │  • Protocol-grounded recommendations│
│  subjects       │        │                                     │
│  sessions       │        │  RAG Pipeline (ChromaDB / pgvector) │
│  imu_samples    │        │  • Clinical rehab protocol ingestion│
│  load_summaries │        │  • Semantic search at inference time│
│  ai_recs        │        │  • sentence-transformers embeddings │
└─────────────────┘        └─────────────────────────────────────┘
```

## Load Calculation

Total session load = ∫ |ω(t)| dt

Where ω(t) is the 3D gyroscope vector at time t, and the integral is computed
via the trapezoidal rule over all samples.

This gives a scalar "angular impulse" in radians that captures how much rotational
work the shoulder performed during the session.

## Range of Motion

Two approaches implemented:
1. **Gravity-tilt (fast)** — estimates pitch/roll from accelerometer gravity direction
2. **Madgwick AHRS filter (accurate)** — full 3D orientation via sensor fusion

The Madgwick filter gives much better ROM estimates and is recommended for the
final analysis pipeline. The simple tilt method is useful for real-time on-device estimates.

## RAG Protocol Pipeline

1. Clinical protocols (PDFs, text files) are chunked into ~500-word windows
2. Each chunk is embedded using `sentence-transformers/all-MiniLM-L6-v2`
3. Embeddings stored in ChromaDB (dev) or pgvector (production)
4. At inference time, the session metadata is used as a query to retrieve
   the top-3 most relevant protocol passages
5. These passages are injected into the Claude prompt as grounding context

## Firmware BLE Protocol

Commands (app → sensor):
- `{"cmd":"start"}` — begin session
- `{"cmd":"stop"}` — end session, reply with summary
- `{"cmd":"set_threshold","val":123.4}` — update haptic threshold

Notifications (sensor → app), every 5th sample:
```json
{"t":1234,"ax":0.077,"ay":-0.296,"az":-1.031,"gx":0.1,"gy":-0.05,"gz":0.02,"sl":12.34}
```
Where `sl` = cumulative session load in rad.
