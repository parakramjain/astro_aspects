from __future__ import annotations
import datetime as dt
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from contextlib import asynccontextmanager

from api_router import router
from schemas import ErrorResponse, ErrorEnvelope, Meta
from settings import APP_NAME, APP_VERSION, CORS_ALLOW_ORIGINS, TRUSTED_HOSTS, GZIP_MIN_SIZE, REQUEST_LOGGING
from middleware import RequestIDMiddleware, LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    print(f"[startup] {APP_NAME} v{APP_VERSION} starting up…")
    yield
    # Shutdown tasks
    print("[shutdown] Bye.")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Natal, Reports, and Compatibility endpoints with best-practice metadata.",
    lifespan=lifespan,
)

# --- Middleware ---
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware, mode=REQUEST_LOGGING)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=GZIP_MIN_SIZE)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=TRUSTED_HOSTS or ["*"])


# --- Exception handlers -> uniform envelope ---

def _meta_from_request(request: Request) -> Meta:
    rid = getattr(request.state, "request_id", None)
    return Meta(
        timestamp=dt.datetime.utcnow().isoformat() + "Z",
        requestId=rid or "",
        apiVersion=APP_VERSION,
    )


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError):
    m = _meta_from_request(request)
    from schemas import ErrorDetail
    err = ErrorEnvelope(code="UNPROCESSABLE_ENTITY", message="Validation error", details=[ErrorDetail(issue=str(exc))])
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=ErrorResponse(meta=m, error=err).model_dump())


@app.exception_handler(Exception)
async def on_any_error(request: Request, exc: Exception):
    m = _meta_from_request(request)
    err = ErrorEnvelope(code="SERVER_ERROR", message=str(exc))
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=ErrorResponse(meta=m, error=err).model_dump())


# --- Liveness/Readiness ---
@app.get("/healthz")
async def healthz():
    return {"ok": True, "ts": dt.datetime.utcnow().isoformat() + "Z"}


@app.get("/readyz")
async def readyz():
    # In future, check kb/index.json, ephemeris availability, etc.
    return {"ready": True}


# --- Routes ---
app.include_router(router)


# (startup/shutdown handled via lifespan above)


# Optional: dev run
if __name__ == "__main__":
    try:
        import uvicorn  # type: ignore
    except Exception as e:
        raise SystemExit("Uvicorn is required. Install dependencies first.")
    uvicorn.run("main:app", host="127.0.0.1", port=8787, reload=True)
