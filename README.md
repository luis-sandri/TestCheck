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
3. No diretório `backend`, crie um ambiente virtual e instale `requirements.txt`.
4. Ainda em `backend`, aplique a estrutura do banco com `alembic upgrade head`.
5. Inicie a API com `uvicorn app.main:app --reload`.
6. No diretório `frontend`, execute `npm install` e `npm run dev`.

Frontend: http://localhost:5173  
Documentação da API: http://localhost:8000/docs

## Banco de dados

O schema inicial possui as entidades necessárias para o fluxo do MVP:

- usuários e seus papéis;
- casos de teste;
- auditorias e itens de checklist;
- não conformidades;
- evidências enviadas pelo responsável.
- notificações internas e entregas de e-mail.

As alterações de estrutura são controladas pelo Alembic. Para criar uma nova
migração após alterar os modelos, execute em `backend`:

```bash
alembic revision --autogenerate -m "descricao da alteracao"
alembic upgrade head
```

A rota `GET /database/health` cria o schema inicial quando necessário e
confirma se a API consegue acessar o banco. A operação é segura para repetir:
ela não exclui nem substitui dados existentes.

## Publicação na Vercel

O arquivo `vercel.json` declara dois serviços no mesmo domínio:

- `/`: frontend React e Vite;
- `/api`: backend FastAPI.

Na Vercel, o projeto deve usar o preset **Services**. A rota pública de
verificação da API será `/api/health`.

Para persistir dados em produção, configure a variável `DATABASE_URL` no
projeto da Vercel com a URL de um PostgreSQL gerenciado e execute a migração
contra esse banco antes de usar o sistema.
