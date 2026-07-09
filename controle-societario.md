# Controle Societário - Serviços

## Overview
Implementação de quatro novos serviços de gestão societária (Licença/Localização, Alvará Sanitário, AVCB e Inscrição Municipal). Cada serviço possuirá sua própria tabela no banco de dados para permitir campos customizados futuros. Além disso, haverá funcionalidade de upload e visualização de documentos armazenados no banco, e um sistema de alertas visuais (tela) e por email (30, 15, 10, 5 dias de antecedência do vencimento) para o departamento societário.

## Project Type
WEB + BACKEND (Python FastAPI, Jinja2 Templates)

## Success Criteria
- [ ] 4 tabelas novas no banco de dados criadas (Alembic migration).
- [ ] Upload, edição, visualização e exclusão de documentos funcioando para os 4 novos serviços.
- [ ] Alertas visuais (badges/cores) na interface para vencimentos próximos.
- [ ] Rotina (CRON/Script) configurada para enviar emails de alerta aos responsáveis 30, 15, 10 e 5 dias antes do vencimento.

## Tech Stack
- Backend: FastAPI (Python), SQLAlchemy.
- Database: PostgreSQL (armazenamento de arquivos no DB).
- Frontend: HTML/Jinja2, TailwindCSS.

## File Structure
```
app/
├── models/
│   ├── licenca_localizacao.py (New)
│   ├── alvara_sanitario.py (New)
│   ├── avcb.py (New)
│   └── inscricao_municipal.py (New)
├── routers/
│   ├── controle_societario.py (New) ou extensões no arquivo existente
├── templates/
│   ├── licenca_localizacao.html (New)
│   ├── alvara_sanitario.html (New)
│   ├── avcb.html (New)
│   └── inscricao_municipal.html (New)
scripts/
└── check_vencimentos_societario.py (New)
alembic/
└── versions/
    └── [migration_societario].py
```

## Task Breakdown

### Task 1: Database Models & Migrations
- **Agent:** `@backend-specialist`
- **Skill:** `database-design`
- **Input:** Criar modelos do SQLAlchemy para Licença/Localização, Alvará Sanitário, AVCB, Inscrição Municipal (Campos: id, cliente_id, vencimento, arquivo (LargeBinary), nome_arquivo, etc).
- **Output:** Modelos criados e migração gerada (`alembic revision --autogenerate`).
- **Verify:** `alembic upgrade head` roda sem erros e tabelas são criadas no banco de dados.

### Task 2: Backend Routers (CRUD & Upload)
- **Agent:** `@backend-specialist`
- **Skill:** `api-patterns`
- **Input:** Implementar rotas em `app/routers/` para Listar, Criar, Atualizar, Deletar e Fazer Upload/Download dos documentos para os 4 serviços.
- **Output:** Endpoints funcionando e retornando os dados corretos ou templates.
- **Verify:** Chamadas para os endpoints retornam status 200/302 sem exceções no terminal.

### Task 3: Frontend Views & Navigation
- **Agent:** `@frontend-specialist`
- **Skill:** `frontend-design`
- **Input:** Criar arquivos HTML para os 4 serviços, similares ao `certificados.html`, incluindo uploaders e badges de alerta visual baseados na diferença de dias da Data de Validade. Atualizar links no menu superior.
- **Output:** Telas renderizadas com sucesso, tabelas com alertas visuais por vencimento.
- **Verify:** Interface acessível e responsiva sem quebra de CSS.

### Task 4: Email Alert Script
- **Agent:** `@backend-specialist`
- **Skill:** `python-patterns`
- **Input:** Criar script `scripts/check_vencimentos_societario.py` que consulta as 5 tabelas (incluindo certificados) e dispara email para o departamento societário (30, 15, 10, 5 dias).
- **Output:** Script testável que se conecta ao banco e aciona a função de envio de email.
- **Verify:** Executar o script no terminal e verificar logs de email enviado com sucesso para vencimentos simulados.

## Phase X: Verification
- [ ] Lint: `ruff check .`
- [ ] Build/Deploy Tests: `python -m pytest` (se aplicável)
- [ ] Executar script de testes manuais/UI nas 4 novas páginas.
- [ ] Testar envio de emails.
