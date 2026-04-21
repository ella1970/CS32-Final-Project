"""
routers/sessions.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database.connection import get_db
from database.models import Session, Subject, LoadSummary, ArmSide
from core.load_calculator import calculate_session_load, IMUFrame

router = APIRouter()


class SessionCreate(BaseModel):
    subject_id:     int
    arm_side:       ArmSide
    session_number: Optional[int] = None


class SessionEnd(BaseModel):
    pain_score: Optional[float] = None   # 0–10
    notes:      Optional[str]   = None


class SessionOut(BaseModel):
    id:             int
    subject_id:     int
    session_number: int
    arm_side:       str
    started_at:     datetime
    ended_at:       Optional[datetime]
    pain_score:     Optional[float]
    is_active:      bool

    class Config:
        from_attributes = True


@router.post("/start", response_model=SessionOut)
def start_session(payload: SessionCreate, db: DBSession = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(404, "Subject not found")

    # Auto-increment session number if not provided
    if payload.session_number is None:
        last = (db.query(Session)
                  .filter(Session.subject_id == payload.subject_id)
                  .order_by(Session.session_number.desc())
                  .first())
        payload.session_number = (last.session_number + 1) if last else 1

    session = Session(
        subject_id     = payload.subject_id,
        session_number = payload.session_number,
        arm_side       = payload.arm_side,
        started_at     = datetime.utcnow(),
        is_active      = True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/end", response_model=SessionOut)
def end_session(session_id: int, payload: SessionEnd, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    session.ended_at   = datetime.utcnow()
    session.pain_score = payload.pain_score
    session.notes      = payload.notes
    session.is_active  = False

    # Compute load summary from stored IMU samples
    frames = [
        IMUFrame(
            elapsed_s = s.elapsed_s,
            accel_x   = s.accel_x, accel_y = s.accel_y, accel_z = s.accel_z,
            gyro_x    = s.gyro_x,  gyro_y  = s.gyro_y,  gyro_z  = s.gyro_z,
        )
        for s in session.imu_samples
    ]

    if frames:
        result = calculate_session_load(frames)
        summary = LoadSummary(
            session_id        = session_id,
            total_load        = result.total_load,
            peak_load_rate    = result.peak_load_rate,
            avg_load_rate     = result.avg_load_rate,
            rom_flexion_deg   = result.rom_flexion_deg,
            rom_abduction_deg = result.rom_abduction_deg,
            rom_rotation_deg  = result.rom_rotation_deg,
            stroke_count      = result.stroke_count,
            duration_s        = result.duration_s,
        )
        db.add(summary)

    db.commit()
    db.refresh(session)
    return session


@router.get("/subject/{subject_id}", response_model=List[SessionOut])
def list_sessions(subject_id: int, db: DBSession = Depends(get_db)):
    return (db.query(Session)
              .filter(Session.subject_id == subject_id)
              .order_by(Session.session_number)
              .all())


@router.get("/table")
def session_table(db: DBSession = Depends(get_db)):
    """
    Returns all subjects × sessions in a flat table format for the researcher view.
    """
    rows = []
    subjects = db.query(Subject).all()
    for subj in subjects:
        for sess in subj.sessions:
            sl = sess.load_summary
            rows.append({
                "subject_code":    subj.code,
                "subject_id":      subj.id,
                "session_id":      sess.id,
                "session_number":  sess.session_number,
                "arm_side":        sess.arm_side,
                "injured_arm":     subj.injured_arm,
                "is_injured_arm":  sess.arm_side == subj.injured_arm,
                "started_at":      sess.started_at,
                "pain_score":      sess.pain_score,
                "total_load":      sl.total_load        if sl else None,
                "peak_load_rate":  sl.peak_load_rate    if sl else None,
                "stroke_count":    sl.stroke_count      if sl else None,
                "duration_s":      sl.duration_s        if sl else None,
                "rom_flexion":     sl.rom_flexion_deg   if sl else None,
                "rom_abduction":   sl.rom_abduction_deg if sl else None,
                "rom_rotation":    sl.rom_rotation_deg  if sl else None,
            })
    return rows
