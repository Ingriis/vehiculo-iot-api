# API IoT de vehículos — práctica 2.5

API local para administrar vehículos, comandos y demos, registrar movimientos y recibir actualizaciones por WebSocket.

## Preparar y ejecutar

En PowerShell, desde esta carpeta:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Completa `.env` con los datos de Amazon RDS y configura `API_KEY` con una clave aleatoria larga; no compartas sus valores. Puedes generar una desde PowerShell con `[Convert]::ToBase64String([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))`. `.env` está excluido de Git. Inicia localmente:

```powershell
python -m app.main
```

La API escucha en `127.0.0.1:8000`; Swagger UI está en <http://127.0.0.1:8000/docs>. En Swagger pulsa **Authorize** y pega la clave; la API la envía como `X-API-Key`.

Las solicitudes `POST`, `PUT` y `DELETE` que modifican vehículos, comandos, demos, pasos de demos o ejecutan movimientos requieren `X-API-Key`. Los `GET` de consulta no la requieren. Para cancelar una demo por WebSocket, el cliente debe iniciar la conexión con el mismo encabezado; no incluyas la clave en capturas ni la pegues en Git.

## Organización de Swagger

1. **Vehículos**: `GET/POST /vehicles` y `GET/PUT/DELETE /vehicles/{vehicle_id}`.
2. **Comandos**: listar, crear, actualizar y eliminar comandos por vehículo.
3. **Estado**: `GET /vehicles/{vehicle_id}/state`.
4. **Historial**: `GET /vehicles/{vehicle_id}/history` devuelve hasta diez registros recientes, ordenados por fecha e ID, con origen.
5. **Movimientos**: `POST /vehicles/{vehicle_id}/movements` registra un movimiento manual, actualiza el estado y el historial en una transacción y notifica después del commit.
6. **Demos**: crear, listar, actualizar, eliminar y ejecutar en `.../demos`.
7. **Movimientos de demo**: listar, agregar, actualizar y eliminar los pasos en `.../demos/{demo_id}/movements`.

WebSocket: `ws://127.0.0.1:8000/ws/vehicles/{vehicle_id}`. Envía estado inicial y eventos de movimientos; una DEMO valida vehículo/demo/comandos activos, actualiza el estado por paso, respeta duraciones y pausas y no agrega historial. Emite `demo_started`, `demo_finished`, `demo_cancelled` o `demo_error`. Para cancelar, envía `{"action":"cancel_demo"}` desde un cliente WebSocket conectado a ese vehículo. Solo se permite una DEMO simultánea por vehículo.

## Módulos

- `app/main.py`: aplicación FastAPI, orden de etiquetas OpenAPI y arranque en loopback.
- `app/core/`: configuración de entorno y engine SQLAlchemy con PyMySQL.
- `app/models/`: esquemas de solicitudes.
- `app/repositories/`: llamadas a Stored Procedures y transacciones.
- `app/services/`: validación y reglas de negocio.
- `app/api/`: routers HTTP, WebSocket y conexiones.
- `docs/stored-procedures.md`: inventario del SQL compartido.

No ejecutes el dump SQL: contiene DDL y sentencias de borrado. No se crean tablas ni se cambian Stored Procedures.
