from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import get_settings
from .database import Base, engine
from . import models  # noqa: F401 - registra as tabelas do schema inicial
from .auth import router as auth_router
from .audits import router as audit_router
from .nonconformities import router as nonconformity_router
from .scenarios import router as scenario_router
from .test_cases import router as test_case_router


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="API para auditoria automatizada de casos de teste.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(test_case_router)
app.include_router(audit_router)
app.include_router(nonconformity_router)
app.include_router(scenario_router)


def ensure_database_ready() -> None:
    """Cria o schema inicial e confirma a comunicação com o PostgreSQL.

    A criação é idempotente: tabelas e dados existentes não são removidos.
    """
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        # A primeira versão já pode estar no Neon; por isso evoluímos esta
        # coluna de forma segura até as migrations passarem a ser executadas no deploy.
        if engine.dialect.name == "postgresql":
            connection.execute(
                text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS responsible_email VARCHAR(255)")
            )
            connection.execute(text("ALTER TABLE test_cases ADD COLUMN IF NOT EXISTS scenario_id VARCHAR(36)"))
            connection.execute(text("ALTER TABLE audit_items ADD COLUMN IF NOT EXISTS suggested_result VARCHAR(32)"))
            connection.execute(text("ALTER TABLE audit_items ADD COLUMN IF NOT EXISTS final_result VARCHAR(32)"))
            connection.execute(text("ALTER TABLE nonconformities ADD COLUMN IF NOT EXISTS resolution_due_at TIMESTAMP WITH TIME ZONE"))
            connection.execute(text("ALTER TABLE nonconformities ADD COLUMN IF NOT EXISTS review_due_at TIMESTAMP WITH TIME ZONE"))
            connection.execute(text("ALTER TABLE nonconformities ADD COLUMN IF NOT EXISTS escalation_due_at TIMESTAMP WITH TIME ZONE"))
            connection.execute(text("ALTER TABLE nonconformities ADD COLUMN IF NOT EXISTS escalated_at TIMESTAMP WITH TIME ZONE"))
            connection.execute(text("ALTER TABLE nonconformities ADD COLUMN IF NOT EXISTS supervisor_email VARCHAR(255)"))
            connection.execute(text("ALTER TABLE nonconformities ADD COLUMN IF NOT EXISTS final_decision TEXT"))
        connection.execute(text("SELECT 1"))


@app.get("/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    ensure_database_ready()
    return {"status": "ok", "service": settings.app_name, "database": "connected"}


@app.get("/database/health", tags=["Sistema"])
def database_health_check() -> dict[str, str]:
    """Inicializa o schema e verifica a comunicação com o PostgreSQL.

    A inicialização é idempotente: não recria nem apaga tabelas já existentes.
    As migrations do Alembic continuam sendo a referência para evoluções futuras.
    """
    ensure_database_ready()
    return {"status": "ok", "database": "connected", "schema": "ready"}
