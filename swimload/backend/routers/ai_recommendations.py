"""
routers/ai_recommendations.py

Uses Anthropic Claude API to:
1. Calculate safe loading zones based on session data + pain score
2. Query RAG pipeline for relevant clinical protocols
3. Return structured recovery recommendations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional
import anthropic, json, os

from database.connection import get_db
from database.models import Session, LoadSummary, AIRecommendation, Subject
from ml.rag_pipeline import query_protocols

router  = APIRouter()
client  = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def build_prompt(session: Session, summary: LoadSummary,
                 subject: Subject, protocol_context: str) -> str:
    """
    Build the prompt for Claude to generate safe loading recommendations.
    """
    injured = session.arm_side == subject.injured_arm
    arm_label = "INJURED arm" if injured else "healthy arm"

    # Get previous session loads for ACWR calculation
    prev_loads = []

    return f"""You are a sports medicine AI assistant specializing in shoulder rehabilitation for swimmers with labral tears.

PATIENT DATA:
- Subject: {subject.code}, Age: {subject.age}
- Injured arm: {subject.injured_arm}
- This session: {arm_label}
- Session #{session.session_number}
- Post-session pain score (VAS 0-10): {session.pain_score or 'not recorded'}

SESSION LOAD METRICS:
- Total load (gyro integral): {summary.total_load:.2f} rad
- Peak load rate: {summary.peak_load_rate:.2f} rad/s
- Average load rate: {summary.avg_load_rate:.2f} rad/s
- Duration: {summary.duration_s:.0f} seconds
- Stroke count: {summary.stroke_count}
- ROM Flexion: {summary.rom_flexion_deg:.1f}°
- ROM Abduction: {summary.rom_abduction_deg:.1f}°
- ROM Rotation: {summary.rom_rotation_deg:.1f}°

RELEVANT CLINICAL PROTOCOLS:
{protocol_context}

Based on this data, provide:
1. A safe loading zone for the NEXT session (min and max total_load in rad)
2. Key recovery recommendations (2-3 bullet points)
3. Any red flags or contraindications to watch for
4. Confidence level in your recommendation (low/medium/high) and why

Respond ONLY with valid JSON in this exact format:
{{
  "safe_load_min": <float>,
  "safe_load_max": <float>,
  "recovery_notes": "<string with bullet points separated by \\n>",
  "red_flags": "<string or null>",
  "confidence": "low|medium|high",
  "rationale": "<1-2 sentences>"
}}"""


@router.post("/{session_id}/generate")
def generate_recommendation(session_id: int, db: DBSession = Depends(get_db)):
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")

    summary = session.load_summary
    if not summary:
        raise HTTPException(400, "Session has no computed load summary. End the session first.")

    subject = session.subject

    # Query RAG for relevant protocols
    try:
        protocol_context = query_protocols(
            query=f"labral tear swimming shoulder load {session.arm_side} rehabilitation protocol",
            n_results=3
        )
    except Exception:
        protocol_context = "No protocol database available — basing on session data alone."

    prompt = build_prompt(session, summary, subject, protocol_context)

    response = client.messages.create(
        model      = "claude-opus-4-5",
        max_tokens = 512,
        messages   = [{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    # Strip any accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data = json.loads(raw)

    rec = AIRecommendation(
        session_id         = session_id,
        safe_load_min      = data["safe_load_min"],
        safe_load_max      = data["safe_load_max"],
        recovery_notes     = data["recovery_notes"],
        protocol_citations = protocol_context[:2000],
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return {**data, "recommendation_id": rec.id}


@router.get("/{session_id}/latest")
def get_latest(session_id: int, db: DBSession = Depends(get_db)):
    rec = (db.query(AIRecommendation)
             .filter(AIRecommendation.session_id == session_id)
             .order_by(AIRecommendation.created_at.desc())
             .first())
    if not rec:
        raise HTTPException(404, "No recommendation found")
    return rec
