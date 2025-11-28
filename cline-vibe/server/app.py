"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine, Base
from routes import auth_router

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Vibe Rocket Flight API",
    description="API for managing rocket flight jobs",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router.router)
# app.include_router(jobs.router)
# app.include_router(jobs.rocket_router)
# app.include_router(jobs.flight_router)
# app.include_router(websockets.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Vibe Rocket Flight API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
