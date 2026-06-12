"""
LifeNova Backend API
FastAPI application with PostgreSQL integration
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database.session import get_db, engine
from app.database.base import Base
from app.core.config import settings
from app.api import auth, users, tasks, cycle, coach

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="LifeNova API",
    description="Backend API for LifeNova - Your intelligent life companion",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "LifeNova API",
        "version": "1.0.0",
        "description": "Your intelligent life companion",
        "docs": "/docs",
    }


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(cycle.router, prefix="/api/cycle", tags=["Cycle"])
app.include_router(coach.router, prefix="/api/coach", tags=["Coach"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)