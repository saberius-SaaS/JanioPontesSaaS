# 🚀 Checklist de Migração — Janio Pontes SaaS

Referências de arquitetura: [RLS Multi-Tenant](./doc_arquitetura_rls_multitenant.md) · [Segurança e Deploy](./doc_seguranca_deploy_gcp.md) · [Chatwoot Infra](./doc_chatwoot_infra.md)
Deploys: Todos os deploys serão realizados exclusivamente pelo usuario.
---

## 📧 Modo Sandbox (Ativo)
E-mails redirecionados para `janiopontes@janiopontes.com.br`. Para liberar: `EMAIL_MODE=intercept` → `production` (`.env` + `deploy.ps1`).

---

## 🔜 Próximos Passos

### Fase 2.4 — Testes Finais
- [ ] Testar intensivamente a plataforma (CRUD, webhooks, fluxos de atendimento na nova região)

### Fase 4 — Cutover (A Grande Virada)
- [ ] Travar planilhas do GAS (modo leitura) para evitar novas edições pela equipe
- [ ] Validar conectividade: Garantir que o IP local da execução está autorizado no Firewall do Cloud SQL (evitar erro de Connection Timeout)
- [ ] Wipe de Dados Seguro: Executar `python scripts/limpar_carga.py` (evita quebra da Foreign Key `usuarios_equipes` e preserva o Tenant/Admin)
- [ ] Carga Base de Cadastros: Executar `python scripts/migracao_gas_to_pg.py`
- [ ] Carga Operacional de Tarefas e Histórico: Executar `python scripts/import_tarefas_historico.py`
- [ ] **Validação com Prova Real:** Rodar `python scripts/validacao_migracao.py` para comparar totais do banco contra o GAS (Todos os indicadores devem dar "OK")
- [ ] Validar Dashboard Web: Confirmar se Pendentes, Entregas e Atrasos refletem a prova real no front-end

### Fase 5 — Go-Live
- [ ] Habilitar Reverse Sync (backup para planilhas)
- [ ] Mudar `EMAIL_MODE` para `production`
- [ ] Operação exclusiva em `app.janiopontes.com.br`
- [ ] Monitorar logs (Google Cloud Logging) por 48h
- [ ] Desligar Reverse Sync após 72h
- [ ] Arquivar scripts do Google Apps Script
