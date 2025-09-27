from datetime import datetime
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from schemas.responses import HealthCheckResponse
from lib.database import db_manager
import structlog

app = FastAPI()
logger = structlog.get_logger()


@app.get("/api/health")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint"""
    try:
        # Test database connection
        pool = await db_manager.get_master_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        database_healthy = True
    except Exception as e:
        await logger.aerror("health_check_db_failed", error=str(e))
        database_healthy = False
    
    return HealthCheckResponse(
        status="healthy" if database_healthy else "degraded",
        version="1.0.0",
        database=database_healthy,
        timestamp=datetime.utcnow()
    )


# Vercel serverless function handler
async def handler(request):
    return await health_check()