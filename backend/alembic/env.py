from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

from backend.app.models.point import Point
from backend.app.models.risk_snapshot import RiskSnapshot
from backend.app.models.municipality import Municipality
from backend.app.models.risk_surface import RiskSurface
from backend.app.database import Base
from backend.app.settings import settings

# Alembic Config
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# -----------------------------------------
# USAR A MESMA DATABASE_URL DO BACKEND
# -----------------------------------------
config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE.DATABASE_URL
)

# Metadata dos models
target_metadata = Base.metadata


# -----------------------------------------
# OFFLINE
# -----------------------------------------
def run_migrations_offline() -> None:
    url = settings.DATABASE.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# -----------------------------------------
# ONLINE
# -----------------------------------------
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
