"""
database.py

Camada de infraestrutura responsável por:

- Configuração da conexão com o banco de dados
- Criação da engine SQLAlchemy
- Gerenciamento de sessões
- Criação automática de tabelas
- Integração com ciclo de vida da aplicação
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.engine import Engine

from backend.app.settings import settings

# =====================================================
# ENGINE
# =====================================================

_engine: Engine | None = None
SessionLocal: sessionmaker  # <-- não é mais Optional

def _build_engine_and_session(url: str) -> tuple[Engine, sessionmaker]:
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
        connect_args=connect_args,
    )

    SessionMaker = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )

    return engine, SessionMaker

_engine, SessionLocal = _build_engine_and_session(settings.DATABASE.DATABASE_URL)

Base = declarative_base()


# =====================================================
# INICIALIZAÇÃO
# =====================================================

def init_database(
    database_url: str | None = None,
    force_recreate: bool = False,
) -> None:
    """
    Inicializa conexão com banco e cria tabelas automaticamente.

    - database_url: permite override (ex: sqlite memory para testes)
    - force_recreate: força recriação (útil para testes)
    """
    global _engine, SessionLocal

    url = database_url or settings.DATABASE.DATABASE_URL

    if _engine is not None and not force_recreate:
        return

    if _engine is not None:
        _engine.dispose()

    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    _engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        future=True,
        connect_args=connect_args,
    )

    SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )

    import backend.app.models 

    Base.metadata.create_all(bind=_engine)


# =====================================================
# ENCERRAMENTO
# =====================================================

def close_database() -> None:
    global _engine, SessionLocal

    if _engine:
        _engine.dispose()

    _engine = None
    SessionLocal = None


# =====================================================
# DEPENDÊNCIA FASTAPI
# =====================================================

def get_db():
    """
    Dependency para injeção de sessão nas rotas.
    """

    if SessionLocal is None:
        init_database()

    if SessionLocal is None:
        raise RuntimeError("SessionLocal não inicializou. Verifique init_database().")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

init_database()
