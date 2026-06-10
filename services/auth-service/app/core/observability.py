"""Structured logging + request correlation.

Emits one JSON log line per request carrying a request id, so logs from many
replicas can be correlated and indexed by a log aggregator. Stdlib-only (no
extra dependency).
"""
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

REQUEST_ID_HEADER = "X-Request-ID"
_PROBE_PATHS = {"/health", "/health/ready"}

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id.get()


class JsonLogFormatter(logging.Formatter):
    """Minimal JSON formatter that injects the current request id."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": get_request_id(),
        }
        for key in ("method", "path", "status", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str, json_logs: bool) -> None:
    """Route all logging (including uvicorn) through one handler/format."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonLogFormatter() if json_logs else logging.Formatter("%(levelname)s [%(name)s] %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # uvicorn.access is replaced by our structured per-request line below.
    access = logging.getLogger("uvicorn.access")
    access.handlers = []
    access.propagate = False
    for name in ("uvicorn", "uvicorn.error"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns/propagates a request id and logs one structured access line per
    request (method, path, status, duration). Health probes are not logged."""

    def __init__(self, app, logger_name: str) -> None:
        super().__init__(app)
        self._logger = logging.getLogger(logger_name)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        token = _request_id.set(request_id)
        start = time.perf_counter()
        log = request.url.path not in _PROBE_PATHS
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            self._logger.exception(
                "request failed",
                extra={"method": request.method, "path": request.url.path, "duration_ms": duration_ms},
            )
            _request_id.reset(token)
            raise
        response.headers[REQUEST_ID_HEADER] = request_id
        if log:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            self._logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                },
            )
        _request_id.reset(token)
        return response
