from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db


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


@app.get("/health", tags=["Sistema"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


@app.get("/database/health", tags=["Sistema"])
def database_health_check(db: Session = Depends(get_db)) -> dict[str, str]:
    """Verifica se a API consegue se comunicar com o PostgreSQL configurado."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


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
