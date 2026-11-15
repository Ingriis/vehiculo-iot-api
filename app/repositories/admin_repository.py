"""Repositorio con consultas SQL parametrizadas para la gestión administrativa de la práctica 4.3."""

from datetime import datetime, timezone
import time
from typing import Any, Sequence
from sqlalchemy import Engine


class AdminRepository:
    """Gestiona consultas transaccionales parametrizadas sin usar concatenación de strings."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _execute_query(self, sql: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        raw_conn = self._engine.raw_connection()
        try:
            dbapi_conn = getattr(raw_conn, 'driver_connection', raw_conn)
            cursor = dbapi_conn.cursor()
            try:
                cursor.execute(sql, tuple(params))
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    return [dict(zip(columns, row)) for row in cursor.fetchall()]
                return []
            finally:
                cursor.close()
        finally:
            raw_conn.close()

    def _execute_commit(self, sql: str, params: Sequence[Any] = ()) -> int:
        raw_conn = self._engine.raw_connection()
        try:
            dbapi_conn = getattr(raw_conn, 'driver_connection', raw_conn)
            cursor = dbapi_conn.cursor()
            try:
                if hasattr(dbapi_conn, 'begin'):
                    dbapi_conn.begin()
                cursor.execute(sql, tuple(params))
                last_id = cursor.lastrowid
                if hasattr(dbapi_conn, 'commit'):
                    dbapi_conn.commit()
                return last_id
            except Exception:
                if hasattr(dbapi_conn, 'rollback'):
                    dbapi_conn.rollback()
                raise
            finally:
                cursor.close()
        finally:
            raw_conn.close()

    # -------------------------------------------------------------------------
    # Salud de Amazon RDS
    # -------------------------------------------------------------------------
    def check_rds_health(self) -> dict[str, Any]:
        start = time.perf_counter()
        try:
            self._execute_query("SELECT 1 AS alive")
            latency = round((time.perf_counter() - start) * 1000, 2)
            return {"status": "available", "database": "Amazon RDS MySQL", "latency_ms": latency}
        except Exception as exc:
            return {"status": "unavailable", "database": "Amazon RDS MySQL", "error": str(exc)}

    # -------------------------------------------------------------------------
    # Gestión de Usuarios y Clientes
    # -------------------------------------------------------------------------
    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        sql = "SELECT id_usuario, username, email, password_hash, nombre_completo, rol, activo FROM usuarios WHERE username = %s LIMIT 1"
        rows = self._execute_query(sql, (username,))
        return rows[0] if rows else None

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        sql = "SELECT id_usuario, username, email, nombre_completo, rol, activo FROM usuarios WHERE id_usuario = %s LIMIT 1"
        rows = self._execute_query(sql, (user_id,))
        return rows[0] if rows else None

    def list_clients(self) -> list[dict[str, Any]]:
        sql = """
        SELECT u.id_usuario, u.username, u.email, u.nombre_completo, u.rol, u.activo, u.creado_en,
               COUNT(v.id_vehiculo) AS total_unidades
        FROM usuarios u
        LEFT JOIN vehiculos v ON v.propietario_id = u.id_usuario
        WHERE u.rol = 'USUARIO'
        GROUP BY u.id_usuario, u.username, u.email, u.nombre_completo, u.rol, u.activo, u.creado_en
        ORDER BY u.nombre_completo ASC
        """
        return self._execute_query(sql)

    def create_user(self, username: str, email: str, password_hash: str, nombre_completo: str, rol: str = "USUARIO") -> int:
        sql = """
        INSERT INTO usuarios (username, email, password_hash, nombre_completo, rol, activo)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        """
        return self._execute_commit(sql, (username, email, password_hash, nombre_completo, rol))

    # -------------------------------------------------------------------------
    # Catálogo de Modelos y Capacidades
    # -------------------------------------------------------------------------
    def list_models(self) -> list[dict[str, Any]]:
        sql = """
        SELECT m.id_modelo, m.nombre, m.codigo_modelo, m.descripcion, m.categoria, m.imagen_url, m.activo,
               COUNT(v.id_vehiculo) AS total_unidades
        FROM modelos_vehiculo m
        LEFT JOIN vehiculos v ON v.id_modelo = m.id_modelo
        GROUP BY m.id_modelo, m.nombre, m.codigo_modelo, m.descripcion, m.categoria, m.imagen_url, m.activo
        ORDER BY m.id_modelo ASC
        """
        return self._execute_query(sql)

    def get_model(self, model_id: int) -> dict[str, Any] | None:
        sql = "SELECT * FROM modelos_vehiculo WHERE id_modelo = %s LIMIT 1"
        rows = self._execute_query(sql, (model_id,))
        return rows[0] if rows else None

    def create_model(self, nombre: str, codigo_modelo: str, descripcion: str, categoria: str, imagen_url: str | None = None) -> int:
        sql = """
        INSERT INTO modelos_vehiculo (nombre, codigo_modelo, descripcion, categoria, imagen_url, activo)
        VALUES (%s, %s, %s, %s, %s, TRUE)
        """
        return self._execute_commit(sql, (nombre, codigo_modelo, descripcion, categoria, imagen_url))

    def update_model(self, model_id: int, nombre: str, descripcion: str, categoria: str, activo: bool) -> None:
        sql = """
        UPDATE modelos_vehiculo 
        SET nombre = %s, descripcion = %s, categoria = %s, activo = %s 
        WHERE id_modelo = %s
        """
        self._execute_commit(sql, (nombre, descripcion, categoria, activo, model_id))

    def list_model_capabilities(self, model_id: int) -> list[dict[str, Any]]:
        sql = "SELECT id_modelo_comando, nombre_comando, codigo_comando, descripcion, es_critico FROM modelos_comandos WHERE id_modelo = %s ORDER BY codigo_comando ASC"
        return self._execute_query(sql, (model_id,))

    # -------------------------------------------------------------------------
    # Unidades Físicas e Inventario
    # -------------------------------------------------------------------------
    def list_units(self) -> list[dict[str, Any]]:
        sql = """
        SELECT v.id_vehiculo, v.nombre, v.modelo, v.descripcion, v.microcontrolador, v.activo,
               v.id_modelo, m.nombre AS nombre_modelo, m.codigo_modelo,
               v.propietario_id, u.nombre_completo AS nombre_propietario, u.username AS username_propietario,
               COALESCE(v.estado_comercial, 'disponible') AS estado_comercial,
               v.numero_serie, COALESCE(v.soporte_autorizado, FALSE) AS soporte_autorizado,
               e.conectado AS conectado_microcontrolador,
               e.fecha_actualizacion AS ultimo_contacto
        FROM vehiculos v
        LEFT JOIN modelos_vehiculo m ON m.id_modelo = v.id_modelo
        LEFT JOIN usuarios u ON u.id_usuario = v.propietario_id
        LEFT JOIN estados e ON e.id_vehiculo = v.id_vehiculo
        ORDER BY v.id_vehiculo ASC
        """
        return self._execute_query(sql)

    def get_unit_details(self, vehicle_id: int) -> dict[str, Any] | None:
        sql = """
        SELECT v.id_vehiculo, v.nombre, v.modelo, v.descripcion, v.microcontrolador, v.activo,
               v.id_modelo, m.nombre AS nombre_modelo,
               v.propietario_id, u.nombre_completo AS nombre_propietario,
               COALESCE(v.estado_comercial, 'disponible') AS estado_comercial,
               v.numero_serie, COALESCE(v.soporte_autorizado, FALSE) AS soporte_autorizado
        FROM vehiculos v
        LEFT JOIN modelos_vehiculo m ON m.id_modelo = v.id_modelo
        LEFT JOIN usuarios u ON u.id_usuario = v.propietario_id
        WHERE v.id_vehiculo = %s
        LIMIT 1
        """
        rows = self._execute_query(sql, (vehicle_id,))
        return rows[0] if rows else None

    def create_unit(self, nombre: str, id_modelo: int, numero_serie: str, descripcion: str, microcontrolador: str, estado_comercial: str = "disponible") -> int:
        # Reutilizamos el registro en tabla vehiculos manteniendo compatibilidad con SPs
        sql = """
        INSERT INTO vehiculos (nombre, modelo, descripcion, microcontrolador, activo, id_modelo, estado_comercial, numero_serie)
        VALUES (%s, (SELECT nombre FROM modelos_vehiculo WHERE id_modelo = %s LIMIT 1), %s, %s, TRUE, %s, %s, %s)
        """
        return self._execute_commit(sql, (nombre, id_modelo, descripcion, microcontrolador, id_modelo, estado_comercial, numero_serie))

    def update_unit_assignment(self, vehicle_id: int, propietario_id: int | None, estado_comercial: str) -> None:
        sql = """
        UPDATE vehiculos 
        SET propietario_id = %s, estado_comercial = %s 
        WHERE id_vehiculo = %s
        """
        self._execute_commit(sql, (propietario_id, estado_comercial, vehicle_id))

    def update_unit_support(self, vehicle_id: int, soporte_autorizado: bool) -> None:
        sql = "UPDATE vehiculos SET soporte_autorizado = %s WHERE id_vehiculo = %s"
        self._execute_commit(sql, (soporte_autorizado, vehicle_id))

    def get_user_units(self, user_id: int) -> list[dict[str, Any]]:
        sql = """
        SELECT v.id_vehiculo, v.nombre, v.descripcion, v.microcontrolador, v.id_modelo,
               m.nombre AS nombre_modelo, m.imagen_url, v.numero_serie,
               e.conectado, e.fecha_actualizacion
        FROM vehiculos v
        LEFT JOIN modelos_vehiculo m ON m.id_modelo = v.id_modelo
        LEFT JOIN estados e ON e.id_vehiculo = v.id_vehiculo
        WHERE v.propietario_id = %s AND v.activo = TRUE
        ORDER BY v.id_vehiculo ASC
        """
        return self._execute_query(sql, (user_id,))

    # -------------------------------------------------------------------------
    # Demos Privadas y Compatibilidad
    # -------------------------------------------------------------------------
    def list_demos_for_unit(self, vehicle_id: int, user_id: int | None = None) -> list[dict[str, Any]]:
        sql = """
        SELECT d.id_demo, d.id_vehiculo, d.nombre, d.descripcion, d.activo,
               COALESCE(d.tipo, 'FABRICA') AS tipo, d.id_usuario,
               COUNT(dm.id_demo_movimiento) AS total_pasos
        FROM demos d
        LEFT JOIN demo_movimientos dm ON dm.id_demo = d.id_demo
        WHERE d.id_vehiculo = %s AND d.activo = TRUE
          AND (d.tipo = 'FABRICA' OR d.tipo IS NULL OR d.id_usuario = %s)
        GROUP BY d.id_demo
        ORDER BY d.id_demo ASC
        """
        return self._execute_query(sql, (vehicle_id, user_id))

    def create_custom_demo(self, vehicle_id: int, user_id: int, nombre: str, descripcion: str, pasos: list[dict[str, Any]]) -> int:
        # Registrar encabezado
        sql_demo = """
        INSERT INTO demos (id_vehiculo, nombre, descripcion, activo, tipo, id_usuario)
        VALUES (%s, %s, %s, TRUE, 'PRIVADA', %s)
        """
        demo_id = self._execute_commit(sql_demo, (vehicle_id, nombre, descripcion, user_id))

        # Registrar pasos ordenados
        sql_paso = """
        INSERT INTO demo_movimientos (id_demo, id_comando, orden, duracion_ms, pausa_ms)
        VALUES (%s, %s, %s, %s, %s)
        """
        for i, paso in enumerate(pasos, start=1):
            self._execute_commit(
                sql_paso,
                (demo_id, paso["id_comando"], i, paso.get("duracion_ms", 1000), paso.get("pausa_ms", 300))
            )
        return demo_id

    # -------------------------------------------------------------------------
    # Sesiones Temporales de Invitados y Unidades de Exhibición
    # -------------------------------------------------------------------------
    def list_exhibition_units(self) -> list[dict[str, Any]]:
        sql = """
        SELECT v.id_vehiculo, v.nombre, v.descripcion, v.microcontrolador,
               m.id_modelo, m.nombre AS nombre_modelo, m.imagen_url,
               CASE WHEN s.id_sesion IS NOT NULL AND s.activa = TRUE AND s.expira_en > NOW()
                    THEN 'OCUPADO' ELSE 'DISPONIBLE' END AS estado_reserva
        FROM vehiculos v
        JOIN modelos_vehiculo m ON m.id_modelo = v.id_modelo
        LEFT JOIN sesiones_invitado s ON s.id_vehiculo = v.id_vehiculo AND s.activa = TRUE AND s.expira_en > NOW()
        WHERE v.estado_comercial = 'exhibicion' AND v.activo = TRUE
        """
        return self._execute_query(sql)

    def get_active_session(self, vehicle_id: int) -> dict[str, Any] | None:
        sql = """
        SELECT id_sesion, id_vehiculo, alias_invitado, token_sesion, iniciada_en, expira_en, duracion_segundos, activa,
               TIMESTAMPDIFF(SECOND, NOW(), expira_en) AS segundos_restantes
        FROM sesiones_invitado
        WHERE id_vehiculo = %s AND activa = TRUE AND expira_en > NOW()
        LIMIT 1
        """
        rows = self._execute_query(sql, (vehicle_id,))
        return rows[0] if rows else None

    def get_session_by_token(self, token: str) -> dict[str, Any] | None:
        sql = """
        SELECT id_sesion, id_vehiculo, alias_invitado, token_sesion, iniciada_en, expira_en, duracion_segundos, activa,
               TIMESTAMPDIFF(SECOND, NOW(), expira_en) AS segundos_restantes
        FROM sesiones_invitado
        WHERE token_sesion = %s AND activa = TRUE AND expira_en > NOW()
        LIMIT 1
        """
        rows = self._execute_query(sql, (token,))
        return rows[0] if rows else None

    def create_guest_session(self, vehicle_id: int, alias_invitado: str, token_sesion: str, duracion_segundos: int = 180) -> int:
        sql = """
        INSERT INTO sesiones_invitado (id_vehiculo, alias_invitado, token_sesion, iniciada_en, expira_en, duracion_segundos, activa)
        VALUES (%s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL %s SECOND), %s, TRUE)
        """
        return self._execute_commit(sql, (vehicle_id, alias_invitado, token_sesion, duracion_segundos, duracion_segundos))

    def release_guest_session(self, session_id: int, razon: str = "USUARIO") -> None:
        sql = "UPDATE sesiones_invitado SET activa = FALSE, finalizada_por = %s WHERE id_sesion = %s"
        self._execute_commit(sql, (razon, session_id))

    # -------------------------------------------------------------------------
    # Auditoría
    # -------------------------------------------------------------------------
    def log_audit(self, actor_id: int | None, username: str, rol: str, accion: str, recurso: str, detalle: str | None = None, resultado: str = "EXITO", ip: str | None = None) -> None:
        try:
            sql = """
            INSERT INTO auditoria (id_usuario, username_actor, rol_actor, accion, recurso, detalle, resultado, ip_origen)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            self._execute_commit(sql, (actor_id, username, rol, accion, recurso, detalle, resultado, ip))
        except Exception:
            pass  # No romper la transacción principal si la auditoría falla

    def list_audit_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        sql = """
        SELECT id_auditoria, username_actor, rol_actor, accion, recurso, detalle, resultado, ip_origen, fecha_hora
        FROM auditoria
        ORDER BY fecha_hora DESC
        LIMIT %s
        """
        return self._execute_query(sql, (limit,))
