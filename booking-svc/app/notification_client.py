import json
import random
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from app.consul import discover_service


# =========================================================
# Configuración de resiliencia
# =========================================================

MAX_RETRIES = 3
TIMEOUT_SECONDS = 2

FAILURE_THRESHOLD = 3
CIRCUIT_OPEN_SECONDS = 30


# =========================================================
# Estado del Circuit Breaker
# =========================================================

_lock = threading.Lock()

_failure_count = 0
_circuit_state = "CLOSED"
_opened_at: datetime | None = None


def get_circuit_breaker_state() -> dict:
    """
    Devuelve el estado actual del Circuit Breaker.
    """

    global _circuit_state
    global _opened_at

    with _lock:
        if (
            _circuit_state == "OPEN"
            and _opened_at is not None
        ):
            elapsed = (
                datetime.now(timezone.utc) - _opened_at
            ).total_seconds()

            if elapsed >= CIRCUIT_OPEN_SECONDS:
                _circuit_state = "HALF_OPEN"

        return {
            "state": _circuit_state,
            "failure_count": _failure_count,
            "failure_threshold": FAILURE_THRESHOLD,
            "open_seconds": CIRCUIT_OPEN_SECONDS,
            "opened_at": (
                _opened_at.isoformat()
                if _opened_at
                else None
            ),
        }


def _register_success() -> None:
    global _failure_count
    global _circuit_state
    global _opened_at

    with _lock:
        _failure_count = 0
        _circuit_state = "CLOSED"
        _opened_at = None

    print(
        "[CIRCUIT BREAKER] CLOSED - notification successful"
    )


def _register_failure() -> None:
    global _failure_count
    global _circuit_state
    global _opened_at

    with _lock:
        _failure_count += 1

        print(
            f"[CIRCUIT BREAKER] Failure "
            f"{_failure_count}/{FAILURE_THRESHOLD}"
        )

        if _failure_count >= FAILURE_THRESHOLD:
            _circuit_state = "OPEN"
            _opened_at = datetime.now(timezone.utc)

            print(
                "[CIRCUIT BREAKER] OPEN - "
                "notif-svc temporarily blocked"
            )


def send_notification(
    user_id: int,
    message: str,
    correlation_id: str | None = None,
) -> bool:
    """
    Intenta enviar una notificación utilizando:
    - Service Discovery mediante Consul
    - Timeout de 2 segundos
    - Hasta 3 intentos
    - Backoff exponencial + jitter
    - Circuit Breaker
    """

    state = get_circuit_breaker_state()

    if state["state"] == "OPEN":
        print(
            "[CIRCUIT BREAKER] OPEN - "
            "notification call skipped"
        )
        return False

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            notif_url = discover_service("notif-svc")

            if not notif_url:
                raise RuntimeError(
                    "No healthy notif-svc instance found"
                )

            payload = {
                "user_id": user_id,
                "message": message,
            }

            headers = {
                "Content-Type": "application/json",
            }

            if correlation_id:
                headers["x-correlation-id"] = correlation_id

            request = urllib.request.Request(
                f"{notif_url}/notifications",
                data=json.dumps(payload).encode("utf-8"),
                method="POST",
                headers=headers,
            )

            with urllib.request.urlopen(
                request,
                timeout=TIMEOUT_SECONDS,
            ) as response:
                if 200 <= response.status < 300:
                    _register_success()
                    return True

                raise RuntimeError(
                    f"notif-svc returned {response.status}"
                )

        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ConnectionError,
            RuntimeError,
        ) as error:
            print(
                f"[NOTIFICATION] Attempt "
                f"{attempt}/{MAX_RETRIES} failed: {error}"
            )

            if attempt < MAX_RETRIES:
                base_delay = 0.5 * (2 ** (attempt - 1))
                jitter = random.uniform(0, 0.25)
                time.sleep(base_delay + jitter)

    # Un fallo lógico equivale a una reserva cuya
    # notificación no pudo enviarse después de los retries.
    _register_failure()

    return False