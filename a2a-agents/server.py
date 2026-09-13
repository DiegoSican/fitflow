import json
import os
import urllib.request
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from mcp.client import Client


AGENT_ROLE = os.getenv("AGENT_ROLE", "orchestrator")
AGENT_PORT = int(os.getenv("AGENT_PORT", "9000"))
AGENT_URL = os.getenv(
    "AGENT_URL",
    f"http://localhost:{AGENT_PORT}",
)

MCP_URL = os.getenv(
    "MCP_URL",
    "http://fitflow-mcp:8000/mcp",
)

BOOKING_CARD_URL = os.getenv(
    "BOOKING_CARD_URL",
    "http://booking-agent:9001/.well-known/agent.json",
)

NOTIFICATION_CARD_URL = os.getenv(
    "NOTIFICATION_CARD_URL",
    "http://notification-agent:9002/.well-known/agent.json",
)


app = FastAPI(
    title=f"FitFlow A2A {AGENT_ROLE}",
    version="1.0.0",
)


# =========================================================
# Logging
# =========================================================

def log_event(event: str, **extra):
    payload = {
        "service": f"{AGENT_ROLE}-agent",
        "protocol": "A2A",
        "event": event,
    }

    payload.update(extra)

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
        ),
        flush=True,
    )


# =========================================================
# Agent Cards
# =========================================================

def build_agent_card() -> dict:
    if AGENT_ROLE == "booking":
        return {
            "protocolVersion": "0.3.0",
            "name": "FitFlow Booking Agent",
            "description": (
                "Gestiona reservas de clases fitness "
                "utilizando FitFlow MCP."
            ),
            "url": AGENT_URL,
            "preferredTransport": "JSONRPC",
            "version": "1.0.0",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
            },
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": [
                "text/plain",
                "application/json",
            ],
            "skills": [
                {
                    "id": "create_booking",
                    "name": "Crear reserva",
                    "description": (
                        "Busca una clase y crea una reserva."
                    ),
                    "tags": [
                        "booking",
                        "fitness",
                        "reservation",
                    ],
                    "examples": [
                        "Reserva Yoga",
                        "Reserva una clase de Pilates",
                    ],
                },
                {
                    "id": "cancel_booking",
                    "name": "Cancelar reserva",
                    "description": (
                        "Cancela una reserva existente."
                    ),
                    "tags": [
                        "booking",
                        "cancel",
                    ],
                },
            ],
        }

    if AGENT_ROLE == "notification":
        return {
            "protocolVersion": "0.3.0",
            "name": "FitFlow Notification Agent",
            "description": (
                "Gestiona notificaciones de FitFlow "
                "utilizando MCP."
            ),
            "url": AGENT_URL,
            "preferredTransport": "JSONRPC",
            "version": "1.0.0",
            "capabilities": {
                "streaming": False,
                "pushNotifications": False,
            },
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": [
                "text/plain",
                "application/json",
            ],
            "skills": [
                {
                    "id": "send_notification",
                    "name": "Enviar notificación",
                    "description": (
                        "Envía una notificación al usuario."
                    ),
                    "tags": [
                        "notification",
                        "message",
                    ],
                    "examples": [
                        "Avísame que mi reserva fue creada"
                    ],
                }
            ],
        }

    return {
        "protocolVersion": "0.3.0",
        "name": "FitFlow Orchestrator Agent",
        "description": (
            "Coordina agentes especializados de FitFlow."
        ),
        "url": AGENT_URL,
        "preferredTransport": "JSONRPC",
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
        },
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": [
            "text/plain",
            "application/json",
        ],
        "skills": [
            {
                "id": "orchestrate_booking",
                "name": "Coordinar reserva",
                "description": (
                    "Descubre y coordina Booking Agent "
                    "y Notification Agent."
                ),
                "tags": [
                    "orchestration",
                    "booking",
                    "notification",
                    "a2a",
                ],
                "examples": [
                    (
                        "Reserva Yoga y avísame "
                        "por notificación"
                    )
                ],
            }
        ],
    }


@app.get("/healthz")
def healthz():
    return {
        "status": "ok",
        "agent": AGENT_ROLE,
    }


# La ruta solicitada por el proyecto.
@app.get("/.well-known/agent.json")
def agent_card():
    return build_agent_card()


# Alias compatible con versiones recientes de A2A.
@app.get("/.well-known/agent-card.json")
def agent_card_standard():
    return build_agent_card()


# =========================================================
# Helpers A2A
# =========================================================

def discover_agent(card_url: str) -> dict:
    with urllib.request.urlopen(
        card_url,
        timeout=5,
    ) as response:
        card = json.loads(
            response.read().decode("utf-8")
        )

    log_event(
        "agent_discovered",
        agent=card["name"],
        url=card["url"],
    )

    return card


def extract_text(message: dict) -> str:
    texts = []

    for part in message.get("parts", []):
        if part.get("kind") == "text":
            texts.append(part.get("text", ""))

    return " ".join(texts).strip()


def make_message(
    text: str,
    data: dict | None = None,
) -> dict:
    parts = [
        {
            "kind": "text",
            "text": text,
        }
    ]

    if data is not None:
        parts.append(
            {
                "kind": "data",
                "data": data,
            }
        )

    return {
        "role": "agent",
        "parts": parts,
        "messageId": str(uuid.uuid4()),
        "contextId": str(uuid.uuid4()),
        "kind": "message",
        "metadata": {},
    }


def send_a2a(
    agent_url: str,
    text: str,
    metadata: dict,
) -> dict:
    request_id = str(uuid.uuid4())

    body = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": text,
                    }
                ],
                "messageId": str(uuid.uuid4()),
                "kind": "message",
            },
            "metadata": metadata,
        },
    }

    log_event(
        "a2a_request_sent",
        destination=agent_url,
        request_id=request_id,
    )

    request = urllib.request.Request(
        agent_url,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    log_event(
        "a2a_response_received",
        destination=agent_url,
        request_id=request_id,
    )

    return result


def extract_data_from_result(
    response: dict,
) -> dict:
    result = response.get("result", {})

    for part in result.get("parts", []):
        if part.get("kind") == "data":
            return part.get("data", {})

    return {}


# =========================================================
# MCP helper
# =========================================================

async def call_mcp(
    tool_name: str,
    arguments: dict,
):
    log_event(
        "mcp_tool_call",
        tool=tool_name,
    )

    client = Client(MCP_URL)

    async with client:
        result = await client.call_tool(
            tool_name,
            arguments,
        )

    parsed = []

    for item in result.content:
        text = getattr(item, "text", None)

        if not text:
            continue

        try:
            parsed.append(json.loads(text))
        except json.JSONDecodeError:
            parsed.append(text)

    if len(parsed) == 1:
        return parsed[0]

    return parsed


# =========================================================
# Booking Agent
# =========================================================

async def booking_agent(
    instruction: str,
    metadata: dict,
) -> dict:
    token = metadata.get("token")

    if not token:
        return {
            "error": True,
            "detail": "JWT token is required.",
        }

    classes = await call_mcp(
        "get_available_classes",
        {},
    )

    if not isinstance(classes, list):
        classes = [classes]

    instruction_lower = instruction.lower()

    selected_class = None

    for item in classes:
        if not isinstance(item, dict):
            continue

        class_name = str(
            item.get("name", "")
        ).lower()

        if class_name and class_name in instruction_lower:
            selected_class = item
            break

    if selected_class is None:
        return {
            "error": True,
            "detail": (
                "No pude identificar la clase solicitada."
            ),
            "available_classes": classes,
        }

    booking = await call_mcp(
        "create_booking",
        {
            "class_id": selected_class["id"],
            "token": token,
        },
    )

    log_event(
        "booking_delegation_completed",
        class_name=selected_class["name"],
    )

    return {
        "selected_class": selected_class,
        "booking": booking,
    }


# =========================================================
# Notification Agent
# =========================================================

async def notification_agent(
    instruction: str,
    metadata: dict,
) -> dict:
    user_id = int(
        metadata.get("user_id", 1)
    )

    booking_id = metadata.get("booking_id")
    class_name = metadata.get(
        "class_name",
        "clase fitness",
    )

    message = (
        f"Reserva {booking_id} confirmada "
        f"para {class_name} mediante A2A."
    )

    result = await call_mcp(
        "send_notification",
        {
            "user_id": user_id,
            "message": message,
        },
    )

    log_event(
        "notification_delegation_completed",
        user_id=user_id,
        booking_id=booking_id,
    )

    return result


# =========================================================
# Orchestrator Agent
# =========================================================

async def orchestrator_agent(
    instruction: str,
    metadata: dict,
) -> dict:
    booking_card = discover_agent(
        BOOKING_CARD_URL
    )

    notification_card = discover_agent(
        NOTIFICATION_CARD_URL
    )

    booking_response = send_a2a(
        booking_card["url"],
        instruction,
        metadata,
    )

    booking_data = extract_data_from_result(
        booking_response
    )

    booking_result = booking_data.get(
        "booking",
        {}
    )

    if (
        not booking_result
        or booking_result.get("error")
    ):
        return {
            "status": "booking_failed",
            "booking_agent": booking_data,
        }

    notification_response = send_a2a(
        notification_card["url"],
        "Notifica al usuario sobre la reserva creada.",
        {
            "user_id": booking_result.get(
                "user_id",
                1,
            ),
            "booking_id": booking_result.get(
                "id"
            ),
            "class_name": booking_data.get(
                "selected_class",
                {},
            ).get(
                "name",
                "clase fitness",
            ),
        },
    )

    notification_data = extract_data_from_result(
        notification_response
    )

    log_event(
        "orchestration_completed",
        booking_id=booking_result.get("id"),
    )

    return {
        "status": "completed",
        "booking_agent": booking_data,
        "notification_agent": notification_data,
    }


# =========================================================
# A2A JSON-RPC endpoint
# =========================================================

@app.post("/")
async def a2a_endpoint(request: Request):
    body = await request.json()

    request_id = body.get("id")

    if (
        body.get("jsonrpc") != "2.0"
        or body.get("method") != "message/send"
    ):
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": (
                        "Only A2A message/send is supported."
                    ),
                },
            },
        )

    params = body.get("params", {})
    message = params.get("message", {})
    metadata = params.get("metadata", {})

    instruction = extract_text(message)

    log_event(
        "a2a_message_received",
        instruction=instruction,
    )

    try:
        if AGENT_ROLE == "booking":
            data = await booking_agent(
                instruction,
                metadata,
            )

        elif AGENT_ROLE == "notification":
            data = await notification_agent(
                instruction,
                metadata,
            )

        else:
            data = await orchestrator_agent(
                instruction,
                metadata,
            )

        response_message = make_message(
            text=(
                f"FitFlow {AGENT_ROLE} agent "
                "completed the request."
            ),
            data=data,
        )

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": response_message,
        }

    except Exception as error:
        log_event(
            "a2a_error",
            error=str(error),
        )

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": str(error),
            },
        }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=AGENT_PORT,
    )