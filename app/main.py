"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Job Agent API",
    description="API for Job Agent - Company Discovery + Outreach Assistant",
    version="0.1.0",
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Job Agent API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# TODO: Add routers
# from app.api import digest, feedback, companies
# app.include_router(digest.router, prefix="/api/digest", tags=["digest"])
# app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
# app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
