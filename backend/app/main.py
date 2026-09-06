from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import get_settings
from .database import Base, engine
from . import models  # noqa: F401 - registra as tabelas do schema inicial
from .auth import router as auth_router
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


@app.get("/dashboard", tags=["Dashboard"])
def dashboard_summary() -> dict[str, object]:
    """Dados demonstrativos até a persistência das auditorias ser implementada."""
    return {
        "metrics": {
            "test_cases": 12,
            "pending_audits": 4,
            "open_nonconformities": 3,
            "average_adherence": 86,
        },
        "recent_cases": [
            {
                "code": "TC-014",
                "title": "Login com senha incorreta",
                "author": "André Murilo",
                "adherence": 67,
                "status": "Não conforme",
            },
            {
                "code": "TC-013",
                "title": "Recuperação de acesso",
                "author": "Marcelo Bellon",
                "adherence": 100,
                "status": "Conforme",
            },
            {
                "code": "TC-012",
                "title": "Cadastro com e-mail existente",
                "author": "Matheus Pamplona",
                "adherence": 83,
                "status": "Em correção",
            },
        ],
    }
