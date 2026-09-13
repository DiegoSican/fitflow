# FitFlow

FitFlow es una plataforma de reservas de clases fitness desarrollada utilizando una arquitectura de microservicios.

El sistema está compuesto por servicios independientes para usuarios, reservas y notificaciones. Cada microservicio posee su propia base de datos PostgreSQL, siguiendo el patrón **Database per Service**.

Además, FitFlow incorpora descubrimiento dinámico de servicios con **Consul**, integración con agentes de inteligencia artificial mediante **Model Context Protocol (MCP)**, mecanismos de resiliencia y observabilidad, autenticación mediante **JWT** y comunicación entre agentes utilizando **Agent-to-Agent (A2A)**.

## Video de explicación del proyecto

En el siguiente video se presenta una demostración del funcionamiento de FitFlow, incluyendo la arquitectura de microservicios, Service Discovery con Consul, autenticación JWT, resiliencia, observabilidad, integración con Claude mediante MCP y comunicación Agent-to-Agent (A2A).

🎥 **[FitFlow](https://drive.google.com/drive/folders/1zsR94LIaLUoZ3Ch7CDrB7pg5a_UkCoUM?usp=sharing)**

---

## Arquitectura

```text
                              FITFLOW

                         Usuario / Cliente
                                |
              +-----------------+------------------+
              |                                    |
              |                              Claude Desktop
              |                                    |
              |                                    v
              |                            FitFlow MCP :8000
              |                                    |
              |                               Consul :8500
              |
              v
      Orchestrator Agent :9000
              |
        A2A / Agent Cards
              |
       +------+------+
       |             |
       v             v
 Booking Agent    Notification Agent
    :9001              :9002
       |                  |
       +-------- MCP -----+
                |
                v
          FitFlow MCP :8000
                |
           Consul :8500
                |
       +--------+--------+
       |        |        |
       v        v        v
 users-svc  booking-svc notif-svc
   :8003      :8001      :8002
     |          |          |
     v          v          v
 users-db   booking-db   notif-db
PostgreSQL PostgreSQL PostgreSQL
```

La arquitectura combina microservicios, descubrimiento dinámico de servicios, MCP y comunicación Agent-to-Agent.

Los tres microservicios principales se registran automáticamente en Consul. Cuando un componente necesita localizar otro servicio, consulta el Service Registry en lugar de depender de direcciones IP fijas.

FitFlow MCP expone operaciones del sistema como herramientas para agentes de inteligencia artificial. Claude Desktop puede consultar las clases disponibles y crear o cancelar reservas utilizando estas herramientas.

La capa A2A incorpora agentes especializados que publican sus capacidades mediante Agent Cards y pueden delegarse tareas entre sí.

---

## Tecnologías utilizadas

- Python 3.12
- FastAPI
- Uvicorn
- PostgreSQL 16
- SQLAlchemy 2
- Psycopg
- Pydantic
- Argon2
- PyJWT
- Docker
- Docker Compose
- Consul
- Model Context Protocol (MCP)
- Agent-to-Agent (A2A)
- JSON-RPC

---

## Componentes y puertos

| Componente         | Puerto | Función                                        |
| ------------------ | -----: | ---------------------------------------------- |
| FitFlow MCP        | `8000` | Expone herramientas de FitFlow a agentes de IA |
| booking-svc        | `8001` | Gestión de clases y reservas                   |
| notif-svc          | `8002` | Gestión de notificaciones                      |
| users-svc          | `8003` | Registro y autenticación                       |
| Consul             | `8500` | Service Registry                               |
| Orchestrator Agent | `9000` | Coordina agentes A2A                           |
| Booking Agent      | `9001` | Agente especializado en reservas               |
| Notification Agent | `9002` | Agente especializado en notificaciones         |

Las bases PostgreSQL se exponen localmente mediante puertos independientes para desarrollo.

---

# Microservicios

## users-svc

Puerto:

```text
8003
```

Responsable del registro y autenticación de usuarios.

Endpoints principales:

```text
POST /users/register
POST /users/login
GET  /users/{user_id}

GET /healthz
GET /readyz
```

El servicio almacena las contraseñas utilizando Argon2 y genera tokens JWT durante el login.

---

## booking-svc

Puerto:

```text
8001
```

Responsable de las clases fitness y las reservas.

Endpoints principales:

```text
GET    /classes
POST   /bookings
GET    /bookings/{booking_id}
DELETE /bookings/{booking_id}

GET /healthz
GET /readyz
```

También expone endpoints para comprobar el estado del Circuit Breaker y administrar notificaciones pendientes.

Las operaciones protegidas utilizan autenticación mediante JWT.

---

## notif-svc

Puerto:

```text
8002
```

Responsable del almacenamiento y envío de notificaciones.

Endpoints principales:

```text
POST /notifications
GET  /notifications/user/{user_id}

GET /healthz
GET /readyz
```

Las notificaciones se almacenan en PostgreSQL para mantener un historial por usuario.

---

# Database per Service

FitFlow utiliza tres bases PostgreSQL independientes:

```text
users-svc   --> users-db
booking-svc --> booking-db
notif-svc   --> notif-db
```

Cada microservicio es propietario exclusivo de sus datos y posee sus propias credenciales de base de datos.

Un microservicio no consulta directamente las tablas pertenecientes a otro servicio.

Esto mantiene el desacoplamiento y la independencia entre los componentes.

---

# Service Discovery con Consul

FitFlow utiliza **Consul** como Service Registry.

La interfaz web está disponible en:

```text
http://localhost:8500
```

Al iniciar, los siguientes servicios se registran automáticamente:

```text
users-svc
booking-svc
notif-svc
```

Cada registro incluye:

- Nombre del servicio.
- Dirección.
- Puerto.
- URL del health check.

Consul consulta periódicamente `/healthz` para verificar la disponibilidad de cada servicio.

Cuando `booking-svc` necesita comunicarse con `notif-svc`, consulta Consul para descubrir dinámicamente su dirección actual.

Esto evita depender de direcciones IP fijas.

---

# Model Context Protocol (MCP)

FitFlow incluye un servidor MCP llamado:

```text
fitflow-mcp
```

Puerto:

```text
8000
```

MCP permite que agentes de inteligencia artificial descubran y utilicen herramientas de FitFlow.

## Herramientas MCP

El servidor expone las siguientes herramientas:

```text
get_available_classes
create_booking
cancel_booking
send_notification
```

### get_available_classes

Consulta las clases disponibles en `booking-svc`.

### create_booking

Crea una reserva mediante `booking-svc`.

La operación requiere un JWT válido.

### cancel_booking

Cancela una reserva existente utilizando `booking-svc`.

### send_notification

Envía una notificación utilizando `notif-svc`.

## Flujo MCP

```text
Agente IA
   |
   v
FitFlow MCP
   |
   v
Consul
   |
   v
Microservicio correspondiente
   |
   v
PostgreSQL
```

El MCP Server consulta Consul para localizar dinámicamente los servicios antes de realizar las llamadas HTTP.

---

# Claude Desktop

FitFlow MCP puede conectarse a **Claude Desktop** como servidor MCP local.

Esto permite interactuar con la plataforma utilizando lenguaje natural.

Por ejemplo:

```text
¿Qué clases hay disponibles en FitFlow?
```

Claude utiliza:

```text
get_available_classes
```

y devuelve las clases reales almacenadas por `booking-svc`.

También es posible solicitar:

```text
Reserva la clase de Spinning en FitFlow.
```

Claude utiliza:

```text
create_booking
```

y la reserva queda almacenada en `booking-db`.

## Configuración MCP de Claude Desktop

Ejemplo de configuración:

```json
{
  "mcpServers": {
    "fitflow": {
      "command": "C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe",
      "args": [
        "exec",
        "-i",
        "-e",
        "MCP_TRANSPORT=stdio",
        "fitflow-mcp",
        "python",
        "server.py"
      ]
    }
  }
}
```

La ruta de `docker.exe` puede variar dependiendo de la instalación de Docker Desktop.

En algunas instalaciones empaquetadas de Claude Desktop para Windows, el archivo de configuración puede encontrarse dentro del directorio de datos de la aplicación en:

```text
AppData\Local\Packages\Claude_...\LocalCache\Roaming\Claude\
```

El servidor puede comprobarse desde:

```text
Claude Desktop
→ Configuración
→ Aplicación de escritorio
→ Desarrollador
→ Servidores MCP locales
```

El servidor `fitflow` debe aparecer en ejecución.

---

# Resiliencia

`booking-svc` implementa mecanismos de resiliencia para evitar que una falla de `notif-svc` impida crear reservas.

Se implementaron:

- Timeout máximo de 2 segundos.
- Hasta 3 reintentos.
- Backoff exponencial.
- Jitter.
- Circuit Breaker.
- Outbox para notificaciones pendientes.

## Circuit Breaker

Cuando `notif-svc` falla tres veces consecutivas, el Circuit Breaker cambia al estado:

```text
OPEN
```

Durante los siguientes 30 segundos se evitan nuevas llamadas al servicio que está fallando.

Después del período de espera se permite una nueva prueba.

Si `notif-svc` responde correctamente, el Circuit Breaker vuelve a:

```text
CLOSED
```

## Outbox

Si la notificación no puede enviarse, la reserva no falla.

El flujo es:

```text
Crear reserva
     |
     v
Reserva almacenada
     |
     v
Intentar notificación
     |
     +---- éxito ----> notificación enviada
     |
     +---- fallo ----> guardar notificación pendiente
```

Esto permite que `booking-svc` siga respondiendo correctamente aunque `notif-svc` esté temporalmente fuera de servicio.

---

# Observabilidad

FitFlow utiliza `x-correlation-id` para rastrear una solicitud entre servicios.

Cuando una solicitud no incluye un correlation ID, se genera automáticamente un UUID.

Cuando `booking-svc` llama a `notif-svc`, propaga el mismo `x-correlation-id`.

Ejemplo del flujo:

```text
Cliente
   |
   | correlation_id = ABC-123
   v
booking-svc
   |
   | correlation_id = ABC-123
   v
notif-svc
```

Los logs son estructurados en formato JSON e incluyen información como:

```text
timestamp
level
service
event
correlation_id
user_id
```

Esto permite seguir el recorrido completo de una operación entre diferentes microservicios.

---

# Seguridad

FitFlow implementa diferentes mecanismos de seguridad.

## Contraseñas

Las contraseñas de los usuarios no se almacenan en texto plano.

Se utiliza:

```text
Argon2
```

para generar hashes seguros.

## JWT

`users-svc` genera un JWT al realizar un login válido.

El token contiene la identificación del usuario y debe utilizarse en los endpoints protegidos de `booking-svc`.

Los tokens inválidos o expirados son rechazados con:

```text
HTTP 401 Unauthorized
```

Los logs de operaciones autenticadas incluyen el `user_id` junto con el `correlation_id`.

---

# Variables de entorno y secretos

Las credenciales y secretos no se almacenan directamente en el código.

Para configurar el proyecto se utiliza:

```text
.env
```

Este archivo está excluido del repositorio mediante `.gitignore`.

El archivo:

```text
.env.example
```

documenta las variables necesarias sin incluir credenciales reales.

## Crear archivo .env

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Posteriormente deben completarse los valores correspondientes.

Ejemplo:

```env
USERS_DB_NAME=users_db
USERS_DB_USER=users_user
USERS_DB_PASSWORD=valor_seguro

BOOKING_DB_NAME=booking_db
BOOKING_DB_USER=booking_user
BOOKING_DB_PASSWORD=valor_seguro

NOTIF_DB_NAME=notif_db
NOTIF_DB_USER=notif_user
NOTIF_DB_PASSWORD=valor_seguro

JWT_SECRET=valor_seguro
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

Nunca deben colocarse credenciales reales en `.env.example`.

---

# Rotación de credenciales sin downtime

La rotación debe realizarse gradualmente para evitar interrumpir el servicio.

## Rotación de credenciales de base de datos

Una estrategia de rotación es:

1. Crear una nueva credencial o usuario de base de datos.
2. Conceder únicamente los permisos necesarios.
3. Mantener temporalmente activa la credencial anterior.
4. Actualizar las variables de entorno del servicio correspondiente.
5. Recrear o desplegar de forma controlada las instancias del servicio utilizando la nueva credencial.
6. Verificar `/healthz` y `/readyz`.
7. Confirmar que las operaciones normales funcionan correctamente.
8. Revocar la credencial anterior.

De esta manera existe un período de transición donde la nueva credencial puede verificarse antes de eliminar la anterior.

## Rotación de JWT_SECRET

Para realizar una rotación de JWT sin invalidar inmediatamente todos los tokens activos, la estrategia recomendada es:

1. Generar un nuevo secreto.
2. Utilizar el nuevo secreto para emitir tokens nuevos.
3. Durante el período de transición, mantener temporalmente la capacidad de validar tokens emitidos con el secreto anterior.
4. Esperar a que los tokens anteriores expiren.
5. Retirar definitivamente el secreto anterior.

Si una credencial o secreto se expone accidentalmente, debe considerarse comprometido y rotarse inmediatamente.

---

# Agent-to-Agent (A2A)

FitFlow incorpora una capa **Agent-to-Agent** formada por tres agentes especializados.

## Orchestrator Agent

Puerto:

```text
9000
```

Recibe una instrucción del usuario, descubre los agentes disponibles mediante sus Agent Cards y coordina las tareas necesarias.

## Booking Agent

Puerto:

```text
9001
```

Agente especializado en operaciones de reserva.

Utiliza internamente FitFlow MCP para consultar clases y crear reservas.

## Notification Agent

Puerto:

```text
9002
```

Agente especializado en notificaciones.

Utiliza internamente FitFlow MCP para enviar notificaciones.

---

# Agent Cards

Cada agente publica información sobre sus capacidades mediante:

```text
/.well-known/agent.json
```

Ejemplos locales:

```text
http://localhost:9000/.well-known/agent.json
http://localhost:9001/.well-known/agent.json
http://localhost:9002/.well-known/agent.json
```

El Orchestrator utiliza estas Agent Cards para descubrir las capacidades de Booking Agent y Notification Agent.

---

# MCP vs A2A

**MCP** permite que un agente utilice herramientas o sistemas externos.

En FitFlow:

```text
Agente
  |
  v
MCP
  |
  v
Microservicios
```

**A2A** permite que diferentes agentes especializados se descubran, deleguen trabajo y colaboren entre sí.

En FitFlow:

```text
Usuario
   |
   v
Orchestrator Agent
   |
   | A2A
   +--------------------+
   |                    |
   v                    v
Booking Agent    Notification Agent
   |                    |
   +-------- MCP -------+
             |
             v
           FitFlow
```

En resumen:

```text
MCP = Agente --> Herramientas / Sistemas

A2A = Agente --> Agente
```

---

# Flujo A2A

Ejemplo de instrucción:

```text
Reserva Yoga y avísame por notificación
```

Flujo:

```text
Usuario
   |
   v
Orchestrator Agent
   |
   | descubre Agent Cards
   v
Booking Agent
   |
   | MCP: get_available_classes
   | MCP: create_booking
   v
booking-svc
   |
   v
Reserva creada
   |
   v
Orchestrator Agent
   |
   v
Notification Agent
   |
   | MCP: send_notification
   v
notif-svc
   |
   v
Notificación enviada
```

La comunicación A2A utiliza mensajes JSON-RPC.

---

# Ejecutar el proyecto

## 1. Clonar repositorio

```bash
git clone https://github.com/DiegoSican/fitflow.git
cd fitflow
```

## 2. Crear archivo .env

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Completar los valores de las variables de entorno.

## 3. Construir y ejecutar

```bash
docker compose up --build
```

Para ejecutar en segundo plano:

```bash
docker compose up -d --build
```

Docker Compose levanta la arquitectura completa:

```text
users-svc
booking-svc
notif-svc

users-db
booking-db
notif-db

consul
fitflow-mcp

orchestrator-agent
booking-agent
notification-agent
```

---

# Verificar contenedores

```bash
docker compose ps
```

Los componentes deben aparecer ejecutándose y los servicios configurados con health checks deben mostrarse saludables.

---

# Health Checks

Microservicios:

```bash
curl http://localhost:8003/healthz
curl http://localhost:8001/healthz
curl http://localhost:8002/healthz
```

Respuesta esperada:

```json
{
  "status": "ok"
}
```

Readiness:

```bash
curl http://localhost:8003/readyz
curl http://localhost:8001/readyz
curl http://localhost:8002/readyz
```

Los endpoints `/readyz` verifican adicionalmente la conexión con la base de datos correspondiente.

---

# Swagger

FastAPI genera documentación interactiva automáticamente.

Users:

```text
http://localhost:8003/docs
```

Bookings:

```text
http://localhost:8001/docs
```

Notifications:

```text
http://localhost:8002/docs
```

---

# Verificar Consul

Abrir:

```text
http://localhost:8500
```

Los tres microservicios principales deben aparecer registrados y saludables:

```text
users-svc
booking-svc
notif-svc
```

---

# Verificar Agent Cards

Orchestrator Agent:

```text
http://localhost:9000/.well-known/agent.json
```

Booking Agent:

```text
http://localhost:9001/.well-known/agent.json
```

Notification Agent:

```text
http://localhost:9002/.well-known/agent.json
```

---

# Estructura del repositorio

```text
fitflow/
|
+-- users-svc/
|   +-- app/
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- booking-svc/
|   +-- app/
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- notif-svc/
|   +-- app/
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- fitflow-mcp/
|   +-- server.py
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- a2a-agents/
|   +-- server.py
|   +-- Dockerfile
|   +-- requirements.txt
|
+-- .env.example
+-- .gitignore
+-- docker-compose.yml
+-- README.md
```

---

# Flujo general de FitFlow

```text
1. Registrar usuario
        |
        v
2. Login
        |
        v
3. Obtener JWT
        |
        v
4. Consultar clases
        |
        v
5. Crear reserva
        |
        v
6. booking-svc intenta notificar
        |
        +--> notif-svc disponible --> notificación enviada
        |
        +--> notif-svc caído --> Circuit Breaker / Outbox

También:

Claude Desktop
        |
        v
FitFlow MCP
        |
        v
Consul
        |
        v
Microservicios

Y:

Usuario
        |
        v
Orchestrator Agent
        |
        v
Booking Agent + Notification Agent
        |
        v
MCP
        |
        v
Microservicios
```

---

# Estado del proyecto

FitFlow integra:

```text
Microservicios
Database per Service
Docker Compose
PostgreSQL
Consul
Service Discovery
Model Context Protocol (MCP)
Claude Desktop
JWT
Gestión de secretos
Timeouts
Retries
Backoff exponencial
Jitter
Circuit Breaker
Outbox
Logs JSON
x-correlation-id
Agent-to-Agent (A2A)
Agent Cards
JSON-RPC
```

---

FitFlow — Postgrado en Diseño y Desarrollo de Software — Universidad Galileo
