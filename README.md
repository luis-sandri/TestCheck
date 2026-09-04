# TestCheck

Aplicação web acadêmica para auditoria automatizada de casos de teste. O sistema
calcula a aderência do artefato, gera não conformidades e acompanha correções
com evidências e comunicação por e-mail.

## Estrutura

- `frontend`: React, TypeScript e Vite.
- `backend`: FastAPI, SQLAlchemy e PostgreSQL.
- `docker-compose.yml`: banco PostgreSQL para desenvolvimento local.

## Requisitos

- Node.js 20 ou superior.
- Python 3.12 ou superior.
- Docker Desktop, ou uma instalação local do PostgreSQL.

## Primeira execução

1. Copie `.env.example` para `.env`.
2. Inicie o PostgreSQL com `docker compose up -d`.
3. No diretório `backend`, crie um ambiente virtual e instale
   `requirements.txt`.
4. Inicie a API com `uvicorn app.main:app --reload`.
5. No diretório `frontend`, execute `npm install` e `npm run dev`.

Frontend: http://localhost:5173  
Documentação da API: http://localhost:8000/docs


