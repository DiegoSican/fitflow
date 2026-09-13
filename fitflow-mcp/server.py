import json
import os
import urllib.error
import urllib.request

from mcp.server import MCPServer


# =========================================================
# Configuración
# =========================================================

CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = os.getenv("CONSUL_PORT", "8500")

MCP_TRANSPORT = os.getenv(
    "MCP_TRANSPORT",
    "streamable-http",
)


# =========================================================
# MCP Server
# =========================================================

mcp = MCPServer(
    "FitFlow MCP",
    instructions=(
        "Servidor MCP de FitFlow. "
        "Permite consultar clases disponibles, "
        "crear reservas y cancelar reservas."
    ),
)


# =========================================================
# Service Discovery
# =========================================================

def discover_service(service_name: str) -> str:
    """
    Consulta Consul para encontrar una instancia saludable
    del servicio solicitado.
    """

    consul_url = (
        f"http://{CONSUL_HOST}:{CONSUL_PORT}"
        f"/v1/health/service/{service_name}?passing=true"
    )

    try:
        with urllib.request.urlopen(
            consul_url,
            timeout=3,
        ) as response:
            services = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"No fue posible consultar Consul: {error}"
        ) from error

    if not services:
        raise RuntimeError(
            f"No hay instancias saludables de {service_name}"
        )

    service = services[0]["Service"]

    address = service["Address"]
    port = service["Port"]

    return f"http://{address}:{port}"


# =========================================================
# Helper HTTP
# =========================================================

def request_json(
    url: str,
    method: str = "GET",
    body: dict | None = None,
    token: str | None = None,
):
    headers = {
        "Content-Type": "application/json",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None

    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {
                    "status": "ok",
                }

            return json.loads(content)

    except urllib.error.HTTPError as error:
        content = error.read().decode("utf-8")

        try:
            detail = json.loads(content)
        except json.JSONDecodeError:
            detail = content

        return {
            "error": True,
            "status_code": error.code,
            "detail": detail,
        }

    except urllib.error.URLError as error:
        return {
            "error": True,
            "detail": str(error),
        }


# =========================================================
# TOOL 1
# get_available_classes
# =========================================================

@mcp.tool()
def get_available_classes() -> list[dict]:
    """
    Obtiene las clases fitness disponibles en FitFlow.
    """

    booking_url = discover_service("booking-svc")

    result = request_json(
        f"{booking_url}/classes"
    )

    return result


# =========================================================
# TOOL 2
# create_booking
# =========================================================

@mcp.tool()
def create_booking(
    class_id: int,
    token: str,
) -> dict:
    """
    Crea una reserva para una clase.

    class_id:
        ID de la clase que se desea reservar.

    token:
        JWT válido obtenido mediante users-svc.
    """

    booking_url = discover_service("booking-svc")

    result = request_json(
        f"{booking_url}/bookings",
        method="POST",
        body={
            "class_id": class_id,
        },
        token=token,
    )

    return result


# =========================================================
# TOOL 3
# cancel_booking
# =========================================================

@mcp.tool()
def cancel_booking(
    booking_id: int,
    token: str,
) -> dict:
    """
    Cancela una reserva existente.

    booking_id:
        ID de la reserva.

    token:
        JWT válido obtenido mediante users-svc.
    """

    booking_url = discover_service("booking-svc")

    result = request_json(
        f"{booking_url}/bookings/{booking_id}",
        method="DELETE",
        token=token,
    )

    return result

# =========================================================
# TOOL 4
# send_notification
# =========================================================

@mcp.tool()
def send_notification(
    user_id: int,
    message: str,
) -> dict:
    """
    Envía una notificación a un usuario de FitFlow.
    """

    notif_url = discover_service("notif-svc")

    result = request_json(
        f"{notif_url}/notifications",
        method="POST",
        body={
            "user_id": user_id,
            "message": message,
        },
    )

    return result
    
# =========================================================
# Ejecución
# =========================================================

if __name__ == "__main__":
    if MCP_TRANSPORT == "stdio":
        mcp.run()

    else:
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=8000,
            stateless_http=True,
            json_response=True,
        )