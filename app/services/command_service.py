"""Reglas de negocio para el catálogo de comandos."""

from typing import Any

from app.repositories.vehicle_repository import VehicleRepository
from app.services.movement_service import CommandNotFoundError, VehicleNotFoundError


class CommandService:
    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository

    def list_commands(self, vehicle_id: int) -> list[dict[str, Any]]:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            return unit.get_vehicle_commands(vehicle_id)

    def create_command(
        self, vehicle_id: int, name: str, code: int, description: str | None
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            command_id = unit.create_command(vehicle_id, name, code, description)
            return next(
                (
                    command
                    for command in unit.get_vehicle_commands(vehicle_id)
                    if int(command["id_comando"]) == command_id
                ),
                {"id_comando": command_id, "id_vehiculo": vehicle_id},
            )

    def update_command(
        self,
        vehicle_id: int,
        command_id: int,
        name: str,
        code: int,
        description: str | None,
        active: bool,
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            commands = unit.get_vehicle_commands(vehicle_id)
            if not any(int(command["id_comando"]) == command_id for command in commands):
                raise CommandNotFoundError(command_id)
            unit.update_command(command_id, name, code, description, active)
            return next(
                (
                    command
                    for command in unit.get_vehicle_commands(vehicle_id)
                    if int(command["id_comando"]) == command_id
                ),
                {"id_comando": command_id, "id_vehiculo": vehicle_id},
            )

    def delete_command(self, vehicle_id: int, command_id: int) -> None:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            commands = unit.get_vehicle_commands(vehicle_id)
            if not any(int(command["id_comando"]) == command_id for command in commands):
                raise CommandNotFoundError(command_id)
            unit.delete_command(command_id)
