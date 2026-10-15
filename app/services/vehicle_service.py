"""Reglas de negocio y transacciones para el recurso vehículo."""

from typing import Any

from app.repositories.vehicle_repository import VehicleRepository
from app.services.movement_service import VehicleNotFoundError


class VehicleService:
    def __init__(self, repository: VehicleRepository) -> None:
        self._repository = repository

    def list_vehicles(self) -> list[dict[str, Any]]:
        with self._repository.transaction() as unit:
            return unit.get_vehicles()

    def get_vehicle(self, vehicle_id: int) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            vehicle = unit.get_vehicle(vehicle_id)
            if vehicle is None:
                raise VehicleNotFoundError(vehicle_id)
            return vehicle

    def create_vehicle(
        self, name: str, model: str, description: str, microcontroller: str
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            vehicle_id = unit.create_vehicle(name, model, description, microcontroller)
            vehicle = unit.get_vehicle(vehicle_id)
            if vehicle is None:
                return {"id_vehiculo": vehicle_id}
            return vehicle

    def update_vehicle(
        self,
        vehicle_id: int,
        name: str,
        model: str,
        description: str,
        microcontroller: str,
        active: bool,
    ) -> dict[str, Any]:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            unit.update_vehicle(
                vehicle_id, name, model, description, microcontroller, active
            )
            return unit.get_vehicle(vehicle_id) or {"id_vehiculo": vehicle_id}

    def delete_vehicle(self, vehicle_id: int) -> None:
        with self._repository.transaction() as unit:
            if unit.get_vehicle(vehicle_id) is None:
                raise VehicleNotFoundError(vehicle_id)
            unit.delete_vehicle(vehicle_id)
