"""
routers/subjects.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional, List

from database.connection import get_db
from database.models import Subject, ArmSide

router = APIRouter()


class SubjectCreate(BaseModel):
    code:        str
    age:         Optional[int] = None
    injured_arm: ArmSide


class SubjectOut(BaseModel):
    id:          int
    code:        str
    age:         Optional[int]
    injured_arm: str
    class Config:
        from_attributes = True


@router.post("/", response_model=SubjectOut)
def create_subject(payload: SubjectCreate, db: DBSession = Depends(get_db)):
    existing = db.query(Subject).filter(Subject.code == payload.code).first()
    if existing:
        raise HTTPException(400, f"Subject {payload.code} already exists")
    subj = Subject(**payload.dict())
    db.add(subj)
    db.commit()
    db.refresh(subj)
    return subj


@router.get("/", response_model=List[SubjectOut])
def list_subjects(db: DBSession = Depends(get_db)):
    return db.query(Subject).all()


@router.get("/{subject_id}", response_model=SubjectOut)
def get_subject(subject_id: int, db: DBSession = Depends(get_db)):
    subj = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subj:
        raise HTTPException(404, "Subject not found")
    return subj
