"""
database/models.py — SQLAlchemy ORM models
"""
from sqlalchemy import (Column, Integer, Float, String, Boolean,
                         DateTime, ForeignKey, Text, Enum)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import enum

Base = declarative_base()


class ArmSide(str, enum.Enum):
    left  = "left"
    right = "right"


class Subject(Base):
    __tablename__ = "subjects"

    id            = Column(Integer, primary_key=True, index=True)
    code          = Column(String(32), unique=True, nullable=False)  # e.g. "SUB_001"
    age           = Column(Integer)
    injured_arm   = Column(Enum(ArmSide))  # which arm has labral tear
    created_at    = Column(DateTime, default=datetime.utcnow)

    sessions      = relationship("Session", back_populates="subject")


class Session(Base):
    __tablename__ = "sessions"

    id             = Column(Integer, primary_key=True, index=True)
    subject_id     = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    session_number = Column(Integer, nullable=False)
    arm_side       = Column(Enum(ArmSide), nullable=False)
    started_at     = Column(DateTime, default=datetime.utcnow)
    ended_at       = Column(DateTime, nullable=True)
    pain_score     = Column(Float, nullable=True)   # 0–10 VAS
    notes          = Column(Text, nullable=True)
    is_active      = Column(Boolean, default=True)

    subject        = relationship("Subject",     back_populates="sessions")
    imu_samples    = relationship("IMUSample",   back_populates="session",
                                  cascade="all, delete-orphan")
    load_summary   = relationship("LoadSummary", back_populates="session",
                                  uselist=False,  cascade="all, delete-orphan")
    ai_recs        = relationship("AIRecommendation", back_populates="session",
                                  cascade="all, delete-orphan")


class IMUSample(Base):
    """
    One row per sensor reading (~166 Hz).
    epoch_ms matches the 'epoc (ms)' column in your CSV exports.
    """
    __tablename__ = "imu_samples"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    epoch_ms    = Column(Float, nullable=False)      # unix epoch in ms
    elapsed_s   = Column(Float, nullable=False)      # seconds since session start
    accel_x     = Column(Float)                      # g
    accel_y     = Column(Float)
    accel_z     = Column(Float)
    gyro_x      = Column(Float)                      # rad/s  (or deg/s — keep consistent)
    gyro_y      = Column(Float)
    gyro_z      = Column(Float)

    session     = relationship("Session", back_populates="imu_samples")


class LoadSummary(Base):
    """
    Computed once per session after it ends.
    """
    __tablename__ = "load_summaries"

    id               = Column(Integer, primary_key=True, index=True)
    session_id       = Column(Integer, ForeignKey("sessions.id"), unique=True)
    total_load       = Column(Float)    # integral of gyro magnitude (rad)
    peak_load_rate   = Column(Float)    # peak instantaneous gyro magnitude (rad/s)
    avg_load_rate    = Column(Float)    # mean gyro magnitude
    rom_flexion_deg  = Column(Float, nullable=True)
    rom_abduction_deg= Column(Float, nullable=True)
    rom_rotation_deg = Column(Float, nullable=True)
    stroke_count     = Column(Integer, nullable=True)
    duration_s       = Column(Float)
    computed_at      = Column(DateTime, default=datetime.utcnow)

    session          = relationship("Session", back_populates="load_summary")


class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"

    id                 = Column(Integer, primary_key=True, index=True)
    session_id         = Column(Integer, ForeignKey("sessions.id"))
    safe_load_min      = Column(Float)
    safe_load_max      = Column(Float)
    recovery_notes     = Column(Text)
    protocol_citations = Column(Text)   # JSON list of protocol snippets used
    created_at         = Column(DateTime, default=datetime.utcnow)

    session            = relationship("Session", back_populates="ai_recs")
