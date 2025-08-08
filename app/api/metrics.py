# ------------------ Fast API ------------------------------
from fastapi import APIRouter, Response

# ----------------- Third Parties -------------------------
import time
from datetime import datetime, timezone
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# ---------------- Internals ------------------------------

start_time = time.time()

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
