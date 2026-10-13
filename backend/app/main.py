from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.api.destinations import router as destinations_router
from app.api.errors import (
    http_exception_handler,
    rate_limit_exception_handler,
    unexpected_exception_handler,
    validation_exception_handler,
)
from app.api.health import router as health_router
from app.api.bookings import router as bookings_router
from app.api.itineraries import router as itineraries_router
from app.api.rate_limit import limiter
from app.api.recommendations import router as recommendations_router
from app.config import Settings, load_settings
from app.integrations.llm_client import TextOnlyGenerator


_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
logger = logging.getLogger("pahadpath.api")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming_headers = dict(scope.get("headers", []))
        supplied = incoming_headers.get(b"x-request-id", b"").decode("latin-1")
        request_id = supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("ascii")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logging.getLogger("pahadpath.api").info(
                "request_id=%s method=%s status=%s duration_ms=%s",
                request_id,
                scope["method"],
                status_code,
                elapsed_ms,
            )


def create_app(
    settings: Settings | None = None,
    text_generator: TextOnlyGenerator | None = None,
) -> FastAPI:
    app = FastAPI(title="PahadPath API", version="0.2.0")
    app.state.settings = settings or load_settings()
    app.state.text_generator = text_generator
    app.state.limiter = limiter
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app.state.settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
    app.include_router(health_router)
    app.include_router(bookings_router)
    app.include_router(destinations_router)
    app.include_router(recommendations_router)
    app.include_router(itineraries_router)
    logger.info("PahadPath API configured")
    return app


app = create_app()
