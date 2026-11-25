"""Reglas de negocio para registrar un movimiento individual."""

from typing import Any

from app.repositories.vehicle_repository import VehicleRepository


class VehicleNotFoundError(Exception):
    """El ID solicitado no corresponde a un vehículo existente."""


class CommandNotFoundError(Exception):
    """El comando no existe o no pertenece al vehículo indicado."""


class InactiveVehicleError(Exception):
    """El vehículo está desactivado."""


class InactiveCommandError(Exception):
    """El comando está desactivado."""


class MovementService:
    """Valida y registra estado e historial en una sola transacción."""

    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository

    def validate_control_state(self, vehicle_id: int, active_names: list[str]) -> None:
        """Valida el vehículo y cada señal activa sin registrar un comando único."""
        if not active_names:
            return

        with self._repository.transaction() as unit_of_work:
            vehicle = unit_of_work.get_vehicle(vehicle_id)
            if vehicle is None:
                raise VehicleNotFoundError(vehicle_id)
            if not bool(vehicle.get("activo", True)):
                raise InactiveVehicleError(vehicle_id)

            commands = unit_of_work.get_vehicle_commands(vehicle_id)
            for name in active_names:
                command = next(
                    (item for item in commands if item.get("nombre") == name),
                    None,
                )
                if command is None:
                    raise CommandNotFoundError(name)
                if not bool(command.get("activo", True)):
                    raise InactiveCommandError(name)

    def register_movement(self, vehicle_id: int, command_id: int) -> dict[str, Any]:
        with self._repository.transaction() as unit_of_work:
            vehicle = unit_of_work.get_vehicle(vehicle_id)
            if vehicle is None:
                raise VehicleNotFoundError(vehicle_id)
            if not bool(vehicle.get("activo", True)):
                raise InactiveVehicleError(vehicle_id)

            commands = unit_of_work.get_vehicle_commands(vehicle_id)
            selected_command = next(
                (
                    command
                    for command in commands
                    if int(command["id_comando"]) == command_id
                ),
                None,
            )
            if selected_command is None:
                raise CommandNotFoundError(command_id)
            if not bool(selected_command.get("activo", True)):
                raise InactiveCommandError(command_id)

            current_state = unit_of_work.get_vehicle_state(vehicle_id)
            connected = bool(current_state["conectado"]) if current_state else False
            unit_of_work.update_vehicle_state(vehicle_id, command_id, connected)
            unit_of_work.register_history(vehicle_id, command_id, "MANUAL")

        # El servicio retorna únicamente después del commit efectuado al salir
        # del contexto de transacción; la capa API podrá notificar después.
        return {
            "id_vehiculo": vehicle_id,
            "id_comando": command_id,
            "comando": selected_command.get("nombre"),
            "codigo": selected_command.get("codigo"),
            "conectado": connected,
        }
