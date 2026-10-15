"""Acceso transaccional a los Stored Procedures verificados del dump."""

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

from sqlalchemy import Engine


_ALLOWED_PROCEDURES = frozenset(
    {
        "sp_actualizar_comando",
        "sp_actualizar_demo",
        "sp_actualizar_estado",
        "sp_actualizar_movimiento_demo",
        "sp_actualizar_vehiculo",
        "sp_agregar_movimiento_demo",
        "sp_crear_comando",
        "sp_crear_demo",
        "sp_crear_vehiculo",
        "sp_eliminar_comando",
        "sp_eliminar_demo",
        "sp_eliminar_movimiento_demo",
        "sp_eliminar_vehiculo",
        "sp_obtener_comandos_vehiculo",
        "sp_obtener_demos",
        "sp_obtener_estado",
        "sp_obtener_historial",
        "sp_obtener_movimientos_demo",
        "sp_obtener_vehiculo",
        "sp_obtener_vehiculos",
        "sp_registrar_historial",
    }
)


class ProcedureUnitOfWork:
    """Ejecuta consultas dentro de una conexión y transacción compartidas."""

    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def call(self, procedure: str, params: Sequence[Any] = ()) -> list[dict[str, Any]]:
        if procedure not in _ALLOWED_PROCEDURES:
            raise ValueError(f"Stored Procedure no habilitado: {procedure}")

        placeholders = ", ".join("%s" for _ in params)
        self._cursor.execute(f"CALL `{procedure}`({placeholders})", tuple(params))
        rows: list[dict[str, Any]] = []
        while True:
            if self._cursor.description:
                columns = [column[0] for column in self._cursor.description]
                rows.extend(
                    dict(zip(columns, row)) for row in self._cursor.fetchall()
                )
            if not self._cursor.nextset():
                break
        return rows

    def get_vehicle(self, vehicle_id: int) -> dict[str, Any] | None:
        rows = self.call("sp_obtener_vehiculo", (vehicle_id,))
        return rows[0] if rows else None

    def get_vehicles(self) -> list[dict[str, Any]]:
        return self.call("sp_obtener_vehiculos")

    def create_vehicle(
        self, name: str, model: str, description: str, microcontroller: str
    ) -> int:
        rows = self.call(
            "sp_crear_vehiculo", (name, model, description, microcontroller)
        )
        return int(rows[0]["id_vehiculo"])

    def update_vehicle(
        self,
        vehicle_id: int,
        name: str,
        model: str,
        description: str,
        microcontroller: str,
        active: bool,
    ) -> None:
        self.call(
            "sp_actualizar_vehiculo",
            (vehicle_id, name, model, description, microcontroller, active),
        )

    def delete_vehicle(self, vehicle_id: int) -> None:
        self.call("sp_eliminar_vehiculo", (vehicle_id,))

    def get_vehicle_commands(self, vehicle_id: int) -> list[dict[str, Any]]:
        return self.call("sp_obtener_comandos_vehiculo", (vehicle_id,))

    def create_command(
        self, vehicle_id: int, name: str, code: int, description: str | None
    ) -> int:
        rows = self.call(
            "sp_crear_comando", (vehicle_id, name, code, description)
        )
        return int(rows[0]["id_comando"])

    def update_command(
        self,
        command_id: int,
        name: str,
        code: int,
        description: str | None,
        active: bool,
    ) -> None:
        self.call(
            "sp_actualizar_comando",
            (command_id, name, code, description, active),
        )

    def delete_command(self, command_id: int) -> None:
        self.call("sp_eliminar_comando", (command_id,))

    def get_vehicle_demos(self, vehicle_id: int) -> list[dict[str, Any]]:
        return self.call("sp_obtener_demos", (vehicle_id,))

    def create_demo(
        self, vehicle_id: int, name: str, description: str | None
    ) -> int:
        rows = self.call("sp_crear_demo", (vehicle_id, name, description))
        return int(rows[0]["id_demo"])

    def update_demo(
        self, demo_id: int, name: str, description: str | None, active: bool
    ) -> None:
        self.call("sp_actualizar_demo", (demo_id, name, description, active))

    def delete_demo(self, demo_id: int) -> None:
        self.call("sp_eliminar_demo", (demo_id,))

    def get_demo_movements(self, demo_id: int) -> list[dict[str, Any]]:
        return self.call("sp_obtener_movimientos_demo", (demo_id,))

    def add_demo_movement(
        self, demo_id: int, command_id: int, order: int, duration_ms: int, pause_ms: int
    ) -> None:
        self.call(
            "sp_agregar_movimiento_demo",
            (demo_id, command_id, order, duration_ms, pause_ms),
        )

    def update_demo_movement(
        self,
        movement_id: int,
        command_id: int,
        order: int,
        duration_ms: int,
        pause_ms: int,
    ) -> None:
        self.call(
            "sp_actualizar_movimiento_demo",
            (movement_id, command_id, order, duration_ms, pause_ms),
        )

    def delete_demo_movement(self, movement_id: int) -> None:
        self.call("sp_eliminar_movimiento_demo", (movement_id,))

    def get_vehicle_state(self, vehicle_id: int) -> dict[str, Any] | None:
        rows = self.call("sp_obtener_estado", (vehicle_id,))
        return rows[0] if rows else None

    def get_history(self, vehicle_id: int) -> list[dict[str, Any]]:
        return self.call("sp_obtener_historial", (vehicle_id,))

    def update_vehicle_state(
        self, vehicle_id: int, command_id: int, connected: bool
    ) -> None:
        self.call("sp_actualizar_estado", (vehicle_id, command_id, connected))

    def register_history(
        self, vehicle_id: int, command_id: int, origin: str = "MANUAL"
    ) -> None:
        self.call("sp_registrar_historial", (vehicle_id, command_id, origin))


class VehicleRepository:
    """Abre una transacción SQL para agrupar llamadas a procedimientos."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @contextmanager
    def transaction(self) -> Iterator[ProcedureUnitOfWork]:
        pooled_connection = self._engine.raw_connection()
        dbapi_connection = pooled_connection.driver_connection
        cursor = dbapi_connection.cursor()
        try:
            dbapi_connection.begin()
            yield ProcedureUnitOfWork(cursor)
            dbapi_connection.commit()
        except Exception:
            dbapi_connection.rollback()
            raise
        finally:
            cursor.close()
            pooled_connection.close()
