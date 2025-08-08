# ------------------ Fast API ------------------------------
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

# ----------------- Third Parties -------------------------
import time

# ---------------- Internals ------------------------------

start_time = time.time()

router = APIRouter()


def format_uptime(seconds: float) -> str:
    if seconds < 5:
        return "just now"
    elif seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        return f"{int(seconds // 60)} minutes"
    else:
        return f"{int(seconds // 3600)} hours"


@router.get("/health")
async def health_check(request: Request):
    uptime_seconds = time.time() - start_time
    formatted_uptime = format_uptime(uptime_seconds)

    health_data = {
        "status": 200,
        "uptime": formatted_uptime,
        "date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": "🟢 NewsFeed Bot is running.",
    }

    return JSONResponse(status_code=200, content=health_data)
