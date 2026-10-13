from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi.errors import RateLimitExceeded


logger = logging.getLogger("pahadpath.api")
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def request_id_for(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return request_id
    supplied = request.headers.get("X-Request-ID", "")
    request_id = supplied if _REQUEST_ID_PATTERN.fullmatch(supplied) else str(uuid.uuid4())
    request.state.request_id = request_id
    return request_id


def error_body(
    request: Request,
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id_for(request),
    }
    if details:
        error["details"] = details
    return {"error": error}


async def http_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, StarletteHTTPException):
        raise exception
    code = {
        400: "invalid_request",
        409: "conflict",
        404: "not_found",
        422: "validation_error",
        429: "rate_limit_exceeded",
        503: "catalogue_unavailable",
    }.get(exception.status_code, "request_error")
    message = exception.detail if isinstance(exception.detail, str) else "The request could not be completed."
    return JSONResponse(
        status_code=exception.status_code,
        content=error_body(request, code, message),
        headers=exception.headers,
    )


async def validation_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, RequestValidationError):
        raise exception
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"] if part != "body"),
            "code": str(error["type"]),
            "message": str(error["msg"]),
        }
        for error in exception.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body(request, "validation_error", "Request validation failed.", details),
    )


async def rate_limit_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    if not isinstance(exception, RateLimitExceeded):
        raise exception
    return JSONResponse(
        status_code=429,
        content=error_body(request, "rate_limit_exceeded", "Request rate limit exceeded."),
        headers={"Retry-After": "60"},
    )


async def unexpected_exception_handler(
    request: Request,
    _exception: Exception,
) -> JSONResponse:
    request_id = request_id_for(request)
    logger.error(
        "Unhandled request failure request_id=%s category=%s",
        request_id,
        type(_exception).__name__,
    )
    return JSONResponse(
        status_code=500,
        content=error_body(request, "internal_error", "An unexpected server error occurred."),
    )
