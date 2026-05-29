# 🛡️ Arquitetura Multi-Tenant SaaS e RLS

## 1. Modelo de Dados Multi-Tenant
Toda tabela do sistema contém uma coluna `tenant_id` (UUID) que identifica o escritório proprietário. O PostgreSQL aplica políticas de segurança (RLS) que impedem um escritório de acessar dados de outro.

```text
tenants (id, razao_social, cnpj, logo_url, cor_primaria, plano, criado_em)
   ├── usuarios (id, tenant_id → FK, email, nome, papel, ativo)
   ├── clientes (id, tenant_id → FK, razao_social, emails[], telefones[])
   ├── obrigacoes (id, tenant_id → FK, nome, departamento, periodicidade)
   ├── protocolos (id, tenant_id → FK, cliente_id → FK, obrigacao_id → FK, ...)
   └── historico (id, tenant_id → FK, protocolo_id → FK, acao, timestamp, ...)
```

## 2. Isolamento Automático via RLS (Row-Level Security)
Habilitado com `FORCE ROW LEVEL SECURITY` em todas as tabelas tenant-bound.

**Exemplo SQL:**
```sql
ALTER TABLE protocolos ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON protocolos
  USING (tenant_id = current_setting('app.current_tenant')::uuid);
```
O bypass de RLS (`app.bypass_rls = 'on'`) ou autenticação (`/login`) usa `SET LOCAL` (escopo da transação, não da sessão inteira).

## 3. Fluxo de Autenticação e Injeção de RLS no FastAPI
1. Login via Google OAuth.
2. Backend identifica o e-mail, busca na tabela `usuarios` e obtém `tenant_id`.
3. Middleware do FastAPI intercepta requisições, extrai `tenant_id` do JWT.
4. Injeta `SET app.current_tenant = '{tenant_id}'` na sessão do SQLAlchemy.
5. Todas as queries são automaticamente filtradas.

## 4. Controle de Acesso Baseado em Perfis (RBAC)
Baseado em `usuarios.papel`:
*   **ADMIN:** Acesso total (CRUD de Clientes, Regras, Perfis, Workflows, Usuários).
*   **USER (Operacional):** Acesso restrito a protocolos, atendimento e tarefas designadas. Bloqueado via `Depends(require_admin)` no FastAPI e ocultado no Jinja2.
