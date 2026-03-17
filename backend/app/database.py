"""
Conexão e sessão do banco de dados (PostgreSQL)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# SQLAlchemy exige postgresql:// (não postgres://)
database_url = settings.DATABASE_URL
if database_url.startswith("postgres://"):
    database_url = "postgresql://" + database_url[9:]

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Importa modelos para que Base.metadata contenha todas as tabelas (create_all / Alembic)
import app.models  # noqa: F401


def get_db():
    """Dependency: sessão do banco por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Cria tabelas se não existirem (Alembic assumirá nas migrações)."""
    Base.metadata.create_all(bind=engine)
