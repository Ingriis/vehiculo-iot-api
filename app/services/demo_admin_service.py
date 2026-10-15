"""Reglas de negocio para administrar demos y sus movimientos."""

from typing import Any

from app.repositories.vehicle_repository import VehicleRepository
from app.services.movement_service import CommandNotFoundError, VehicleNotFoundError
from app.services.vehicle_query_service import DemoNotFoundError


class DemoMovementNotFoundError(Exception):
    """El paso no existe o no pertenece a la demo indicada."""


class DemoAdminService:
    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository

    @staticmethod
    def _find_demo(unit: Any, vehicle_id: int, demo_id: int) -> dict[str, Any]:
        if unit.get_vehicle(vehicle_id) is None:
            raise VehicleNotFoundError(vehicle_id)
        demo = next(
            (row for row in unit.get_vehicle_demos(vehicle_id)
             if int(row["id_demo"]) == demo_id),
            None,
        )
        if demo is None:
            raise DemoNotFoundError(demo_id)
        return demo

    @staticmethod
    def _validate_command(unit: Any, vehicle_id: int, command_id: int) -> None:
        if not any(
            int(command["id_comando"]) == command_id
            for command in unit.get_vehicle_commands(vehicle_id)
        ):
            raise CommandNotFoundError(command_id)

    def list_demos(self, vehicle_id: int) -> list[dict[str, Any]]:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            return unit.get_vehicle_demos(vehicle_id)

    def create_demo(
        self, vehicle_id: int, name: str, description: str | None
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            demo_id = unit.create_demo(vehicle_id, name, description)
            return next(
                (demo for demo in unit.get_vehicle_demos(vehicle_id)
                 if int(demo["id_demo"]) == demo_id),
                {"id_demo": demo_id, "id_vehiculo": vehicle_id},
            )

    def update_demo(
        self,
        vehicle_id: int,
        demo_id: int,
        name: str,
        description: str | None,
        active: bool,
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            self._find_demo(unit, vehicle_id, demo_id)
            unit.update_demo(demo_id, name, description, active)
            return next(
                (demo for demo in unit.get_vehicle_demos(vehicle_id)
                 if int(demo["id_demo"]) == demo_id),
                {"id_demo": demo_id, "id_vehiculo": vehicle_id},
            )

    def delete_demo(self, vehicle_id: int, demo_id: int) -> None:
        with self._repository.transaction() as unit:
            self._find_demo(unit, vehicle_id, demo_id)
            unit.delete_demo(demo_id)

    def list_movements(
        self, vehicle_id: int, demo_id: int
    ) -> list[dict[str, Any]]:
        with self._repository.transaction() as unit:
            self._find_demo(unit, vehicle_id, demo_id)
            return unit.get_demo_movements(demo_id)

    def add_movement(
        self,
        vehicle_id: int,
        demo_id: int,
        command_id: int,
        order: int,
        duration_ms: int,
        pause_ms: int,
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            self._find_demo(unit, vehicle_id, demo_id)
            self._validate_command(unit, vehicle_id, command_id)
            unit.add_demo_movement(
                demo_id, command_id, order, duration_ms, pause_ms
            )
            return next(
                (movement for movement in unit.get_demo_movements(demo_id)
                 if int(movement["orden"]) == order),
                {"id_demo": demo_id, "orden": order},
            )

    def update_movement(
        self,
        vehicle_id: int,
        demo_id: int,
        movement_id: int,
        command_id: int,
        order: int,
        duration_ms: int,
        pause_ms: int,
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            self._find_demo(unit, vehicle_id, demo_id)
            movements = unit.get_demo_movements(demo_id)
            if not any(
                int(movement["id_demo_movimiento"]) == movement_id
                for movement in movements
            ):
                raise DemoMovementNotFoundError(movement_id)
            self._validate_command(unit, vehicle_id, command_id)
            unit.update_demo_movement(
                movement_id, command_id, order, duration_ms, pause_ms
            )
            return next(
                (movement for movement in unit.get_demo_movements(demo_id)
                 if int(movement["id_demo_movimiento"]) == movement_id),
                {"id_demo": demo_id, "id_demo_movimiento": movement_id},
            )

    def delete_movement(
        self, vehicle_id: int, demo_id: int, movement_id: int
    ) -> None:
        with self._repository.transaction() as unit:
            self._find_demo(unit, vehicle_id, demo_id)
            movements = unit.get_demo_movements(demo_id)
            if not any(
                int(movement["id_demo_movimiento"]) == movement_id
                for movement in movements
            ):
                raise DemoMovementNotFoundError(movement_id)
            unit.delete_demo_movement(movement_id)
