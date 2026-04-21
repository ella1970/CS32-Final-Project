"""
routers/imu.py — ingest raw IMU samples (bulk CSV upload or single BLE stream)
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import List
import csv, io

from database.connection import get_db
from database.models import IMUSample, Session

router = APIRouter()


class IMUSampleIn(BaseModel):
    epoch_ms:  float
    elapsed_s: float
    accel_x:   float
    accel_y:   float
    accel_z:   float
    gyro_x:    float
    gyro_y:    float
    gyro_z:    float


@router.post("/{session_id}/batch")
def ingest_batch(session_id: int,
                 samples: List[IMUSampleIn],
                 db: DBSession = Depends(get_db)):
    """
    Bulk insert IMU samples for a session (used by mobile app BLE buffering).
    """
    sess = db.query(Session).filter(Session.id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")

    db.bulk_insert_mappings(IMUSample, [
        {"session_id": session_id, **s.dict()} for s in samples
    ])
    db.commit()
    return {"inserted": len(samples)}


@router.post("/{session_id}/upload_csv")
async def upload_csv(session_id: int,
                     file: UploadFile = File(...),
                     db: DBSession = Depends(get_db)):
    """
    Upload the raw CSV exported from your sensor hub.
    Expected columns (case-insensitive):
      epoc (ms), timestamp (-0800), elapsed (s),
      x-axis (g), y-axis (g), z-axis (g)
    plus optional gyro columns if present.

    If only accelerometer columns are present, gyro values default to 0.
    """
    sess = db.query(Session).filter(Session.id == session_id).first()
    if not sess:
        raise HTTPException(404, "Session not found")

    content = await file.read()
    reader  = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
    headers = [h.strip().lower() for h in reader.fieldnames or []]

    def col(row, *candidates):
        for c in candidates:
            for h in headers:
                if c.lower() in h:
                    try:
                        return float(row[reader.fieldnames[headers.index(h)]])
                    except Exception:
                        pass
        return 0.0

    records = []
    for row in reader:
        records.append({
            "session_id": session_id,
            "epoch_ms":   col(row, "epoc", "epoch"),
            "elapsed_s":  col(row, "elapsed"),
            "accel_x":    col(row, "x-axis", "accel_x", "ax"),
            "accel_y":    col(row, "y-axis", "accel_y", "ay"),
            "accel_z":    col(row, "z-axis", "accel_z", "az"),
            "gyro_x":     col(row, "gyro_x", "gx", "x gyro"),
            "gyro_y":     col(row, "gyro_y", "gy", "y gyro"),
            "gyro_z":     col(row, "gyro_z", "gz", "z gyro"),
        })

    db.bulk_insert_mappings(IMUSample, records)
    db.commit()
    return {"inserted": len(records), "session_id": session_id}


@router.get("/{session_id}/samples")
def get_samples(session_id: int,
                limit: int = 5000,
                db: DBSession = Depends(get_db)):
    samples = (db.query(IMUSample)
                 .filter(IMUSample.session_id == session_id)
                 .order_by(IMUSample.elapsed_s)
                 .limit(limit)
                 .all())
    return [
        {"elapsed_s": s.elapsed_s,
         "accel_x": s.accel_x, "accel_y": s.accel_y, "accel_z": s.accel_z,
         "gyro_x":  s.gyro_x,  "gyro_y":  s.gyro_y,  "gyro_z":  s.gyro_z}
        for s in samples
    ]
