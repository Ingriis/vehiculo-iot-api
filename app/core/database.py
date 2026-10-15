"""Construcción diferida del engine MySQL; no conecta al importar el módulo."""

from sqlalchemy import URL, Engine, create_engine

from app.core.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    """Crea un engine SQLAlchemy usando PyMySQL y la configuración recibida."""
    url = URL.create(
        drivername="mysql+pymysql",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
        query={"charset": "utf8mb4"},
    )
    return create_engine(url, pool_pre_ping=True)
