# SwimLoad — IMU-Based Shoulder Load Monitoring for Labral Tear Recovery

A full-stack platform for tracking swimmer shoulder load using IMU (gyroscope + accelerometer) sensors. Built for clinical research comparing injured vs. healthy arm mechanics, with AI-powered recovery recommendations.

---

## Repository Structure

```
swimload/
├── firmware/          # Sensor-side code (Arduino/ESP32 + haptic feedback)
├── backend/           # FastAPI Python server (data ingestion, load calc, AI)
├── frontend/          # React app (athlete dashboard + researcher portal)
├── ml/                # RAG pipeline, vector embeddings, protocol training
├── scripts/           # Data import / migration utilities
└── docs/              # Architecture diagrams, data dictionary
```

---

## Features

| Module | Capability |
|---|---|
| **Firmware** | On-device load accumulation, haptic alert at daily max threshold |
| **Load Calculation** | Total session load from gyroscope magnitude integration |
| **Range of Motion** | ROM estimation from IMU orientation (Madgwick filter) |
| **Session Management** | Start/stop sessions, tag left/right arm, subject + session ID |
| **Pain Scale Input** | Post-session VAS score linked to session record |
| **Safe Loading Zone** | GenAI model (Claude API) calculates recovery envelope |
| **Cumulative Load Graphs** | Per-subject, per-arm, per-session time-series visualization |
| **Research Portal** | Table view organized by subject × session |
| **RAG Protocol Engine** | Vector embeddings of clinical rehab protocols (IRIS / pgvector) |

---

## Quick Start

### 1. Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your ANTHROPIC_API_KEY
uvicorn main:app --reload
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3. Firmware
Open `firmware/swimload_sensor/swimload_sensor.ino` in Arduino IDE.
Requires: `Adafruit_MPU6050`, `Adafruit_Sensor`, `ArduinoJson`, `Adafruit_DRV2605` (haptics).

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://user:pass@localhost/swimload
SECRET_KEY=your-secret-key
```

---

## Data Model Overview

- **Subject** → many Sessions
- **Session** → has arm side (left/right), subject_id, session_number, pain_score
- **IMUSample** → belongs to Session, has epoch_ms, x/y/z accel + gyro
- **LoadSummary** → computed per session: total_load, peak_load, ROM_degrees
- **AIRecommendation** → generated per session pair (injured vs healthy arm)

---

## License
MIT
