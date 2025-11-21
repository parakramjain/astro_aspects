from __future__ import annotations
import time
import uuid
from typing import Callable
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, header_name: str = "X-Request-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable):
        req_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        # store on state
        request.state.request_id = req_id
        response = await call_next(request)
        response.headers[self.header_name] = req_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, mode: str = "basic"):
        super().__init__(app)
        self.mode = mode

    async def dispatch(self, request: Request, call_next: Callable):
        if self.mode == "off":
            return await call_next(request)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            dur_ms = (time.perf_counter() - start) * 1000.0
            req_id = getattr(request.state, "request_id", "-")
            path = request.url.path
            method = request.method
            try:
                status = response.status_code  # type: ignore[attr-defined]
            except Exception:
                status = 500
            if self.mode == "basic":
                print(f"{method} {path} => {status} [{dur_ms:.1f}ms] rid={req_id}")
            elif self.mode == "full":
                print(f"{method} {path} qs={request.url.query} ua={request.headers.get('user-agent','-')} => {status} [{dur_ms:.1f}ms] rid={req_id}")
