import json
import os
import time
import urllib.error
import urllib.request


CONSUL_HOST = os.getenv("CONSUL_HOST", "consul")
CONSUL_PORT = os.getenv("CONSUL_PORT", "8500")


def register_service(
    service_name: str,
    service_port: int,
) -> bool:
    """
    Registra el microservicio actual en Consul.
    """

    consul_url = (
        f"http://{CONSUL_HOST}:{CONSUL_PORT}"
        "/v1/agent/service/register"
    )

    registration = {
        "ID": service_name,
        "Name": service_name,
        "Address": service_name,
        "Port": service_port,
        "Check": {
            "HTTP": f"http://{service_name}:{service_port}/healthz",
            "Interval": "10s",
            "Timeout": "3s",
            "DeregisterCriticalServiceAfter": "30s",
        },
    }

    data = json.dumps(registration).encode("utf-8")

    request = urllib.request.Request(
        consul_url,
        data=data,
        method="PUT",
        headers={
            "Content-Type": "application/json",
        },
    )

    # Reintentamos porque Consul puede tardar unos segundos
    # en quedar disponible durante docker compose up.
    for attempt in range(1, 6):
        try:
            with urllib.request.urlopen(
                request,
                timeout=3,
            ) as response:
                if response.status == 200:
                    print(
                        f"[CONSUL] {service_name} "
                        f"registered successfully"
                    )
                    return True

        except (
            urllib.error.URLError,
            TimeoutError,
            ConnectionError,
        ) as error:
            print(
                f"[CONSUL] Registration attempt "
                f"{attempt}/5 failed for "
                f"{service_name}: {error}"
            )

            time.sleep(2)

    print(
        f"[CONSUL] Could not register {service_name}"
    )

    return False


def discover_service(service_name: str) -> str | None:
    """
    Consulta Consul y devuelve la URL de una instancia
    saludable del servicio solicitado.
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

        if not services:
            print(
                f"[CONSUL] No healthy instances "
                f"found for {service_name}"
            )
            return None

        service = services[0]["Service"]

        address = service["Address"]
        port = service["Port"]

        service_url = f"http://{address}:{port}"

        print(
            f"[CONSUL] Discovered {service_name} "
            f"at {service_url}"
        )

        return service_url

    except (
        urllib.error.URLError,
        TimeoutError,
        ConnectionError,
    ) as error:
        print(
            f"[CONSUL] Could not discover "
            f"{service_name}: {error}"
        )

        return None