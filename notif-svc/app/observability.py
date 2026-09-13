import json
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware


correlation_id_context: ContextVar[str] = ContextVar(
    "correlation_id",
    default="",
)


def get_correlation_id() -> str:
    return correlation_id_context.get()


def json_log(
    service: str,
    event: str,
    level: str = "INFO",
    correlation_id: str | None = None,
    user_id: int | None = None,
    **extra,
) -> None:
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "service": service,
        "event": event,
        "correlation_id": (
            correlation_id
            or get_correlation_id()
            or "unknown"
        ),
    }

    if user_id is not None:
        log_entry["user_id"] = user_id

    log_entry.update(extra)

    print(
        json.dumps(
            log_entry,
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        service_name: str,
    ):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(
        self,
        request,
        call_next,
    ):
        correlation_id = (
            request.headers.get("x-correlation-id")
            or str(uuid.uuid4())
        )
        request.state.correlation_id = correlation_id
        token = correlation_id_context.set(
            correlation_id
        )

        try:
            response = await call_next(request)

            response.headers[
                "x-correlation-id"
            ] = correlation_id

            json_log(
                service=self.service_name,
                event="request_completed",
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
            )

            return response

        except Exception as error:
            json_log(
                service=self.service_name,
                event="request_failed",
                level="ERROR",
                correlation_id=correlation_id,
                method=request.method,
                path=request.url.path,
                error=str(error),
            )

            raise

        finally:
            correlation_id_context.reset(token)