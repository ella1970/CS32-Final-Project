"""
routers/analysis.py — cumulative load, cross-session, arm comparison
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from database.connection import get_db
from database.models import Subject, Session, LoadSummary, IMUSample, ArmSide
from core.load_calculator import calculate_session_load, IMUFrame

router = APIRouter()


@router.get("/subject/{subject_id}/cumulative_load")
def cumulative_load(subject_id: int, db: DBSession = Depends(get_db)):
    """
    Returns per-session total load for both arms, ordered by session number.
    Used to generate the cumulative load graph on the dashboard.
    """
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    sessions = (db.query(Session)
                  .filter(Session.subject_id == subject_id,
                          Session.is_active == False)
                  .order_by(Session.session_number)
                  .all())

    result = {"subject_code": subj.code, "injured_arm": subj.injured_arm, "sessions": []}
    running = {"left": 0.0, "right": 0.0}

    for sess in sessions:
        sl = sess.load_summary
        if not sl:
            continue
        running[sess.arm_side] += sl.total_load
        result["sessions"].append({
            "session_number":     sess.session_number,
            "arm_side":           sess.arm_side,
            "is_injured":         sess.arm_side == subj.injured_arm,
            "session_load":       sl.total_load,
            "cumulative_load":    running[sess.arm_side],
            "pain_score":         sess.pain_score,
            "rom_flexion":        sl.rom_flexion_deg,
            "rom_abduction":      sl.rom_abduction_deg,
            "rom_rotation":       sl.rom_rotation_deg,
            "stroke_count":       sl.stroke_count,
            "duration_s":         sl.duration_s,
        })

    return result


@router.get("/subject/{subject_id}/arm_comparison")
def arm_comparison(subject_id: int, db: DBSession = Depends(get_db)):
    """
    Side-by-side comparison of injured vs healthy arm across matched sessions.
    """
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")

    sessions = (db.query(Session)
                  .filter(Session.subject_id == subject_id,
                          Session.is_active == False)
                  .all())

    by_num = {}
    for sess in sessions:
        n = sess.session_number
        if n not in by_num:
            by_num[n] = {}
        by_num[n][sess.arm_side] = sess

    comparison = []
    for num in sorted(by_num.keys()):
        entry = {"session_number": num}
        for side in ("left", "right"):
            s = by_num[num].get(side)
            if s and s.load_summary:
                entry[side] = {
                    "total_load":  s.load_summary.total_load,
                    "rom_flexion": s.load_summary.rom_flexion_deg,
                    "pain_score":  s.pain_score,
                }
            else:
                entry[side] = None
        if entry.get("left") or entry.get("right"):
            comparison.append(entry)

    return {"subject_code": subj.code, "injured_arm": subj.injured_arm,
            "comparison": comparison}


@router.get("/session/{session_id}/intra_session")
def intra_session(session_id: int, db: DBSession = Depends(get_db)):
    """
    Returns the time-series cumulative load curve for a single session.
    Used for the in-session live graph on the athlete app.
    """
    samples = (db.query(IMUSample)
                 .filter(IMUSample.session_id == session_id)
                 .order_by(IMUSample.elapsed_s)
                 .all())

    if not samples:
        return {"elapsed": [], "cumulative_load": [], "gyro_mag": []}

    frames = [
        IMUFrame(s.elapsed_s, s.accel_x, s.accel_y, s.accel_z,
                 s.gyro_x, s.gyro_y, s.gyro_z)
        for s in samples
    ]
    result = calculate_session_load(frames)

    # Downsample to 500 points max for frontend performance
    n = len(result.elapsed_series)
    step = max(1, n // 500)
    return {
        "elapsed":          result.elapsed_series[::step],
        "cumulative_load":  result.cumulative_load_series[::step],
        "gyro_mag":         result.gyro_mag_series[::step],
    }
