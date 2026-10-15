# Inventario de Stored Procedures

Fuente revisada: `vehiculo_iot_carretilla_completa.sql`, dump local compartido el 14 de octubre de 2026. Se inspeccionaron las definiciones SQL; este inventario no se obtuvo conectándose a RDS y no se ejecutó el dump.

Los parámetros se listan en el orden declarado en el SQL. Todos son `IN`; los procedimientos que crean registros devuelven el identificador mediante un `SELECT` con una columna `id_*`.

| Stored Procedure | Parámetros | Función observada |
|---|---|---|
| `sp_actualizar_comando` | `p_id_comando INT`, `p_nombre VARCHAR(60)`, `p_codigo INT`, `p_descripcion VARCHAR(255)`, `p_activo BOOLEAN` | Actualiza campos del comando. |
| `sp_actualizar_demo` | `p_id_demo INT`, `p_nombre VARCHAR(80)`, `p_descripcion VARCHAR(255)`, `p_activo BOOLEAN` | Actualiza campos de la demo. |
| `sp_actualizar_estado` | `p_id_vehiculo INT`, `p_id_comando INT`, `p_conectado BOOLEAN` | Inserta o actualiza el estado del vehículo y su fecha de actualización. |
| `sp_actualizar_movimiento_demo` | `p_id_demo_movimiento INT`, `p_id_comando INT`, `p_orden INT`, `p_duracion_ms INT`, `p_pausa_ms INT` | Actualiza un movimiento de demo. |
| `sp_actualizar_vehiculo` | `p_id_vehiculo INT`, `p_nombre VARCHAR(80)`, `p_modelo VARCHAR(80)`, `p_descripcion VARCHAR(255)`, `p_microcontrolador VARCHAR(50)`, `p_activo BOOLEAN` | Actualiza campos del vehículo. |
| `sp_agregar_movimiento_demo` | `p_id_demo INT`, `p_id_comando INT`, `p_orden INT`, `p_duracion_ms INT`, `p_pausa_ms INT` | Agrega un movimiento a una demo. |
| `sp_crear_comando` | `p_id_vehiculo INT`, `p_nombre VARCHAR(60)`, `p_codigo INT`, `p_descripcion VARCHAR(255)` | Crea un comando y devuelve `id_comando`. |
| `sp_crear_demo` | `p_id_vehiculo INT`, `p_nombre VARCHAR(80)`, `p_descripcion VARCHAR(255)` | Crea una demo y devuelve `id_demo`. |
| `sp_crear_vehiculo` | `p_nombre VARCHAR(80)`, `p_modelo VARCHAR(80)`, `p_descripcion VARCHAR(255)`, `p_microcontrolador VARCHAR(50)` | Crea un vehículo y devuelve `id_vehiculo`. |
| `sp_eliminar_comando` | `p_id_comando INT` | Elimina un comando por ID. |
| `sp_eliminar_demo` | `p_id_demo INT` | Elimina una demo por ID. |
| `sp_eliminar_movimiento_demo` | `p_id_demo_movimiento INT` | Elimina un movimiento de demo por ID. |
| `sp_eliminar_vehiculo` | `p_id_vehiculo INT` | Elimina un vehículo por ID. |
| `sp_obtener_comandos_vehiculo` | `p_id_vehiculo INT` | Lista comandos del vehículo ordenados por `codigo`. |
| `sp_obtener_demos` | `p_id_vehiculo INT` | Lista demos del vehículo ordenadas por `id_demo`. |
| `sp_obtener_estado` | `p_id_vehiculo INT` | Devuelve vehículo, comando, código, conexión y fecha de actualización del estado. |
| `sp_obtener_historial` | `p_id_vehiculo INT` | Lista historial descendente por `fecha_hora` e `id_historial`. |
| `sp_obtener_movimientos_demo` | `p_id_demo INT` | Lista movimientos con comando, duración y pausa, ordenados por `orden`. |
| `sp_obtener_vehiculo` | `p_id_vehiculo INT` | Obtiene un vehículo por ID. |
| `sp_obtener_vehiculos` | *(sin parámetros)* | Lista vehículos ordenados por `id_vehiculo`. |
| `sp_registrar_historial` | `p_id_vehiculo INT`, `p_id_comando INT`, `p_origen VARCHAR(30)` | Inserta una fila de historial. |

## Observaciones para el diseño de la API

- El dump contiene exactamente 21 definiciones `CREATE PROCEDURE`.
- Para validar un vehículo se puede consultar `sp_obtener_vehiculo`; para validar que un comando pertenece a ese vehículo, `sp_obtener_comandos_vehiculo` permite comparar su ID.
- `sp_obtener_historial` ya devuelve el historial más reciente primero; el límite de diez requerido por la API se deberá aplicar en el servicio o endpoint.
- La ejecución de DEMO puede obtener su lista ordenada con `sp_obtener_movimientos_demo`; cada fila incluye `duracion_ms` y `pausa_ms`.
- No hay un procedimiento en este dump para obtener una demo individual por ID. Para comprobar su pertenencia a un vehículo, se puede consultar `sp_obtener_demos` para ese vehículo y verificar el ID solicitado.
- Los procedimientos de actualización, estado e historial son sentencias separadas. La transacción de un movimiento individual debe coordinar las llamadas a estado e historial en la capa de servicio y confirmar antes de emitir la notificación WebSocket.
- El dump también incluye DDL de tablas y sentencias `DROP PROCEDURE IF EXISTS`; no deben ejecutarse como parte de esta práctica.

## Aspectos pendientes de confirmar

Este inventario documenta el SQL compartido, no el estado actual de RDS. Antes de conectar la API, verificar que los procedimientos desplegados coincidan con el dump y confirmar el motor/driver y permisos de ejecución. No se necesitan credenciales para diseñar las interfaces del repositorio.
