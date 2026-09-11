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
- sessões persistidas para login por e-mail e senha.

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

## E-mails de não conformidade

O TestCheck usa o [Resend](https://resend.com) para avisar sobre uma NC criada,
uma evidência enviada e uma evidência revisada. No painel da Vercel, configure
as variáveis de produção abaixo:

- `RESEND_API_KEY`: chave iniciada por `re_`, criada no painel do Resend;
- `EMAIL_FROM`: remetente aprovado. Para testes, use `TestCheck <onboarding@resend.dev>`;
- `APP_URL`: `https://testcheck-luispazinsandri-7901s-projects.vercel.app`.

Sem `RESEND_API_KEY`, a aplicação continua registrando as notificações no banco,
mas não envia mensagens externas. O domínio próprio precisa ser verificado no
Resend antes de ser usado como remetente.

## SLA e escalonamento de não conformidades

O TestCheck usa prazos em **dias úteis** (segunda a sexta-feira; feriados ainda
não são considerados no MVP). A prioridade é escolhida pelo revisor ao confirmar
a não conformidade, e cada etapa recebe um prazo próprio:

| Prioridade | Responsável: corrigir ou contestar | Revisor: aprovar ou reprovar correção | Supervisor: decisão final |
| --- | --- | --- | --- |
| Alta | 2 dias úteis | 1 dia útil | 1 dia útil |
| Média | 5 dias úteis | 2 dias úteis | 2 dias úteis |
| Baixa | 10 dias úteis | 3 dias úteis | 3 dias úteis |

Se o responsável ou o revisor não cumprir a etapa ativa, a NC é escalada ao
supervisor. Uma contestação também é encaminhada diretamente para a decisão
final do supervisor. Todo evento fica registrado no histórico da NC.

O `vercel.json` chama diariamente a rota de escalonamento. Configure
`CRON_SECRET` como variável de ambiente **Production** na Vercel. Esse valor é
uma senha técnica entre a Vercel e a rota agendada: a Vercel a envia no cabeçalho
`Authorization`, e a API só executa o escalonamento se o valor conferir. Assim,
uma pessoa externa não consegue disparar o processo pelo navegador.
