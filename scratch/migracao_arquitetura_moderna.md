# 🚀 Checklist de Migração — Janio Pontes SaaS

Referências de arquitetura: [RLS Multi-Tenant](./doc_arquitetura_rls_multitenant.md) · [Segurança e Deploy](./doc_seguranca_deploy_gcp.md) · [Chatwoot Infra](./doc_chatwoot_infra.md)
Todos os deploys serão realizados exclusivamente pelo usuario.
---

## ✅ Concluído
- [x] Fase 1 — Inicialização do Banco (Cloud SQL, Alembic, RLS, Super Admin)
- [x] Fase 2.1–2.3 — Script de migração GAS → PostgreSQL executado (129 clientes, 58 regras, 10 usuários, 69 workflows)
- [x] Fase 3 — Chatwoot integrado (SDK, WhatsApp Cloud API, Central de Atendimento via iframe)

## 📧 Modo Sandbox (Ativo)
E-mails redirecionados para `janiopontes@janiopontes.com.br`. Para liberar: `EMAIL_MODE=intercept` → `production` (`.env` + `deploy.ps1`).

---

## 🔜 Próximos Passos

### Fase 2.4 — Testes Finais
- [ ] Testar intensivamente a plataforma (CRUD, webhooks, fluxos de atendimento)

### Fase 4 — Cutover (A Grande Virada)
- [ ] Travar planilhas do GAS (modo leitura)
- [ ] Wipe do banco (`alembic downgrade base` + `alembic upgrade head`)
- [ ] Carga final definitiva via `scripts/migracao_gas_to_pg.py`
- [ ] Validar integridade (quantidades, status, datas)

### Fase 5 — Go-Live
- [ ] Habilitar Reverse Sync (backup para planilhas)
- [ ] Mudar `EMAIL_MODE` para `production`
- [ ] Operação exclusiva em `app.janiopontes.com.br`
- [ ] Monitorar logs (Google Cloud Logging) por 48h
- [ ] Desligar Reverse Sync após 72h
- [ ] Arquivar scripts do Google Apps Script
