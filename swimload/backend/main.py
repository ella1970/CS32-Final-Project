"""
SwimLoad Backend — FastAPI
Run: uvicorn main:app --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import sessions, subjects, imu, analysis, ai_recommendations

app = FastAPI(title="SwimLoad API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(subjects.router,          prefix="/subjects",        tags=["Subjects"])
app.include_router(sessions.router,          prefix="/sessions",        tags=["Sessions"])
app.include_router(imu.router,               prefix="/imu",             tags=["IMU Data"])
app.include_router(analysis.router,          prefix="/analysis",        tags=["Analysis"])
app.include_router(ai_recommendations.router,prefix="/recommendations", tags=["AI"])

@app.get("/")
def root():
    return {"status": "ok", "service": "SwimLoad API"}
