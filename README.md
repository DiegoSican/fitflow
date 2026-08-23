# FitFlow

FitFlow es una plataforma de reservas de clases fitness desarrollada utilizando una arquitectura de microservicios.

El sistema se encuentra dividido en servicios independientes responsables de usuarios, reservas y notificaciones. Cada servicio posee su propia base de datos PostgreSQL, siguiendo el patrón **Database per Service**.

## Arquitectura

```text
                         FITFLOW

                    ┌─────────────┐
                    │   Cliente   │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │  users-svc  │ │ booking-svc │ │  notif-svc  │
     │    :8003    │ │    :8001    │ │    :8002    │
     └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
            │               │               │
            ▼               ▼               ▼
     ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
     │  users-db   │ │ booking-db  │ │  notif-db   │
     │ PostgreSQL  │ │ PostgreSQL  │ │ PostgreSQL  │
     └─────────────┘ └─────────────┘ └─────────────┘
```

Cada microservicio es propietario exclusivo de sus datos. Ningún servicio consulta directamente la base de datos de otro servicio.

## Tecnologías

- Python 3.12
- FastAPI
- Uvicorn
- PostgreSQL 16
- SQLAlchemy 2
- Psycopg
- Pydantic
- Argon2
- JWT
- Docker
- Docker Compose

## Microservicios

### users-svc

Puerto: `8003`

Responsable del registro y autenticación de usuarios.

Endpoints principales:

```text
POST /users/register
POST /users/login
GET  /users/{user_id}

GET /healthz
GET /readyz
```

El servicio almacena las contraseñas utilizando hash Argon2 y genera tokens JWT durante el login.

### booking-svc

Puerto: `8001`

Responsable de las clases fitness y reservas.

Endpoints:

```text
GET    /classes
POST   /bookings
GET    /bookings/{booking_id}
DELETE /bookings/{booking_id}

GET /healthz
GET /readyz
```

La creación, consulta y cancelación de reservas utiliza autenticación mediante JWT.

### notif-svc

Puerto: `8002`

Responsable de las notificaciones.

Endpoints:

```text
POST /notifications
GET  /notifications/user/{user_id}

GET /healthz
GET /readyz
```

Durante Task 1, se simuló el envío de una notificación por medio de logs y la información se almacena en PostgreSQL para conservar el historial.

## Database per Service

FitFlow utiliza tres instancias PostgreSQL independientes:

```text
users-svc   → users-db
booking-svc → booking-db
notif-svc   → notif-db
```

Cada servicio cuenta con sus propias credenciales de base de datos.

Los microservicios no tienen acceso directo a las tablas pertenecientes a otros servicios.

## Variables de entorno

Crear el archivo `.env` utilizando `.env.example` como plantilla.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Luego completar los valores correspondientes.

Ejemplo:

```env
USERS_DB_NAME=users_db
USERS_DB_USER=users_user
USERS_DB_PASSWORD=valores_aquí

BOOKING_DB_NAME=booking_db
BOOKING_DB_USER=booking_user
BOOKING_DB_PASSWORD=valores_aquí

NOTIF_DB_NAME=notif_db
NOTIF_DB_USER=notif_user
NOTIF_DB_PASSWORD=valores_aquí

JWT_SECRET=valores_aquí
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=60
```

El archivo `.env` no debe agregarse al repositorio.

## Ejecutar el proyecto

Clonar el repositorio:

```bash
git clone https://github.com/DiegoSican/fitflow.git
cd fitflow
```

Crear y configurar `.env`.

Luego ejecutar:

```bash
docker compose up --build
```

Docker Compose construirá y levantará:

```text
users-svc
booking-svc
notif-svc

users-db
booking-db
notif-db
```

## Verificar contenedores

```bash
docker compose ps
```

Los servicios y bases de datos deben aparecer activos y saludables.

## Health Checks

Verificar los tres microservicios:

```bash
curl http://localhost:8003/healthz
curl http://localhost:8001/healthz
curl http://localhost:8002/healthz
```

Respuesta esperada:

```json
{ "status": "ok" }
```

Los readiness checks verifican adicionalmente la conexión con la base de datos correspondiente:

```bash
curl http://localhost:8003/readyz
curl http://localhost:8001/readyz
curl http://localhost:8002/readyz
```

## Documentación Swagger

FastAPI genera documentación interactiva automáticamente:

```text
Users:
http://localhost:8003/docs

Bookings:
http://localhost:8001/docs

Notifications:
http://localhost:8002/docs
```

## Flujo básico

El flujo principal del sistema es:

```text
1. Registrar usuario
        ↓
2. Login
        ↓
3. Obtener JWT
        ↓
4. Consultar clases disponibles
        ↓
5. Crear reserva utilizando JWT
        ↓
6. Consultar reserva
        ↓
7. Generar notificación
        ↓
8. Cancelar reserva
        ↓
9. Consultar historial de notificaciones
```

## Seguridad

Las contraseñas no se almacenan en texto plano.

FitFlow utiliza:

- Argon2 para hash de contraseñas.
- JWT para autenticación.
- Variables de entorno para credenciales.
- `.gitignore` para excluir `.env`.
- Usuarios PostgreSQL independientes por servicio.

## Estructura del repositorio

```text
fitflow/
│
├── users-svc/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
│
├── booking-svc/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
│
├── notif-svc/
│   ├── app/
│   ├── Dockerfile
│   └── requirements.txt
│
├── fitflow-mcp/
│
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

## Estado del proyecto

### Task 1 — Microservicios + Docker — COMPLETADO

---

FitFlow — Postgrado en Diseño y Desarrollo de Software — Universidad Galileo
