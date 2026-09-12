from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.ratelimit import RateLimitMiddleware
from app.api.routers import (
    ai,
    anomalies,
    audit,
    auth,
    buildings,
    carbon,
    cost,
    energy,
    forecasts,
    notifications,
    recommendations,
    scenarios,
    search,
    structure,
    system,
    waste,
)

settings = get_settings()

app = FastAPI(
    title="GridMind API",
    description="Energy Intelligence + Digital Twin + Optimization platform (synthetic demo data).",
    version="0.1.0",
)

register_error_handlers(app)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "gridmind-api"}


app.include_router(auth.router)
app.include_router(buildings.router)
app.include_router(structure.router)
app.include_router(energy.router)
app.include_router(anomalies.router)
app.include_router(waste.router)
app.include_router(forecasts.router)
app.include_router(scenarios.router)
app.include_router(recommendations.router)
app.include_router(carbon.router)
app.include_router(cost.router)
app.include_router(ai.router)
app.include_router(audit.router)
app.include_router(system.router)
app.include_router(notifications.router)
app.include_router(search.router)
