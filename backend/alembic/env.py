"""
Alembic env - usa DATABASE_URL do app.config e Base.metadata dos modelos.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Raiz do backend = diretório do alembic.ini
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database import Base
import app.models  # noqa: F401 - registra todas as tabelas no Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# URL: do settings e normaliza postgres -> postgresql
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = "postgresql://" + database_url[9:]
config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
