"""Consultas de movimientos y demos para los endpoints de lectura."""

from typing import Any

from app.repositories.vehicle_repository import VehicleRepository
from app.services.movement_service import VehicleNotFoundError


class DemoNotFoundError(Exception):
    """La demo no existe o no pertenece al vehículo indicado."""


class InactiveVehicleError(Exception):
    """El vehículo está desactivado."""


class InactiveDemoError(Exception):
    """La demo está desactivada."""


class InactiveCommandInDemoError(Exception):
    """La secuencia contiene un comando desactivado."""


class VehicleQueryService:
    """Aplica los límites y validaciones de lectura sobre los procedimientos."""

    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository

    def get_vehicle_state(self, vehicle_id: int) -> dict[str, Any] | None:
        with self._repository.transaction() as unit_of_work:
            if unit_of_work.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            return unit_of_work.get_vehicle_state(vehicle_id)

    def get_history(self, vehicle_id: int) -> list[dict[str, Any]]:
        with self._repository.transaction() as unit_of_work:
            if unit_of_work.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            # sp_obtener_historial ya ordena del más reciente al más antiguo.
            return unit_of_work.get_history(vehicle_id)[:10]

    def get_demo_sequence(
        self, vehicle_id: int, demo_id: int
    ) -> list[dict[str, Any]]:
        with self._repository.transaction() as unit_of_work:
            vehicle = unit_of_work.get_vehicle(vehicle_id)
            if vehicle is None:
                raise VehicleNotFoundError(vehicle_id)
            if not bool(vehicle.get("activo", True)):
                raise InactiveVehicleError(vehicle_id)

            demos = unit_of_work.get_vehicle_demos(vehicle_id)
            selected_demo = next(
                (demo for demo in demos if int(demo["id_demo"]) == demo_id), None
            )
            if selected_demo is None:
                raise DemoNotFoundError(demo_id)
            if not bool(selected_demo.get("activo", True)):
                raise InactiveDemoError(demo_id)

            # El SP devuelve nombre/código/tiempos, mientras el SP de comandos
            # incluye activo; así se valida sin alterar los procedimientos.
            sequence = unit_of_work.get_demo_movements(demo_id)
            active_by_id = {
                int(command["id_comando"]): bool(command.get("activo", True))
                for command in unit_of_work.get_vehicle_commands(vehicle_id)
            }
            if any(
                not active_by_id.get(int(step["id_comando"]), False)
                for step in sequence
            ):
                raise InactiveCommandInDemoError(demo_id)
            return sequence

    def update_demo_state(self, vehicle_id: int, command_id: int) -> None:
        """Actualiza el estado de la demo sin agregar un registro al historial."""
        with self._repository.transaction() as unit_of_work:
            if unit_of_work.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            state = unit_of_work.get_vehicle_state(vehicle_id)
            connected = bool(state["conectado"]) if state else False
            unit_of_work.update_vehicle_state(vehicle_id, command_id, connected)

