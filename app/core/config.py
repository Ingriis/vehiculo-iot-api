"""Carga y valida la configuración local de la API."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Configuración de ejecución; los secretos solo se leen del entorno."""

    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    api_key: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        """Carga `.env` si existe y valida los campos requeridos."""
        load_dotenv()
        required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
        missing = [name for name in required if not os.getenv(name)]
        if missing:
            raise ValueError(
                "Faltan variables de entorno requeridas: " + ", ".join(missing)
            )

        try:
            db_port = int(os.getenv("DB_PORT", "3306"))
        except ValueError as exc:
            raise ValueError("DB_PORT debe ser un número entero") from exc

        return cls(
            db_host=os.environ["DB_HOST"],
            db_port=db_port,
            db_name=os.environ["DB_NAME"],
            db_user=os.environ["DB_USER"],
            db_password=os.environ["DB_PASSWORD"],
            api_key=os.getenv("API_KEY"),
        )
