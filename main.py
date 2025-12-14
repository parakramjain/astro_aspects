from __future__ import annotations
import datetime as dt
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from contextlib import asynccontextmanager
import yaml

from api_router import router
from schemas import ErrorResponse, ErrorEnvelope, ErrorDetail
from settings import APP_NAME, APP_VERSION, CORS_ALLOW_ORIGINS, TRUSTED_HOSTS, GZIP_MIN_SIZE, REQUEST_LOGGING
from middleware import RequestIDMiddleware, LoggingMiddleware

OPENAPI_SPEC_PATH = Path(__file__).with_name("API_defination.yaml")


@lru_cache()
def _load_openapi_schema() -> Any:
    with OPENAPI_SPEC_PATH.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


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


def _custom_openapi() -> Any:
    try:
        schema = _load_openapi_schema()
    except (FileNotFoundError, yaml.YAMLError) as exc:
        print(f"[openapi] Falling back to generated schema: {exc}")
        schema = get_openapi(
            title=APP_NAME,
            version=APP_VERSION,
            description="Natal, Reports, and Compatibility endpoints with best-practice metadata.",
            routes=app.routes,
        )
    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi  # type: ignore[assignment]

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


@app.exception_handler(StarletteHTTPException)
async def on_http_exception(request: Request, exc: StarletteHTTPException):
    status_code = int(getattr(exc, "status_code", 500))
    detail = getattr(exc, "detail", None)
    message = detail if isinstance(detail, str) and detail else str(exc)

    if status_code == status.HTTP_400_BAD_REQUEST:
        code = "BAD_REQUEST"
    elif status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
    elif status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
    elif status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
    elif status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        code = "METHOD_NOT_ALLOWED"
    else:
        code = f"HTTP_{status_code}"

    err = ErrorEnvelope(code=code, message=message)
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=err).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError):
    err = ErrorEnvelope(
        code="UNPROCESSABLE_ENTITY",
        message="Validation error",
        details=[ErrorDetail(issue=str(exc))],
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(error=err).model_dump(),
    )


@app.exception_handler(Exception)
async def on_any_error(request: Request, exc: Exception):
    err = ErrorEnvelope(code="SERVER_ERROR", message=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(error=err).model_dump(),
    )

@app.get("/")
async def landing():
    return {"Welcome to Astro Vision": True, "ts": dt.datetime.utcnow().isoformat() + "Z"}

# --- Liveness/Readiness ---
@app.get("/healthz")
async def healthz():
    return {"Astro Vision is OK": True, "ts": dt.datetime.utcnow().isoformat() + "Z"}


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
