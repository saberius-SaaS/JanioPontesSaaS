# 🚀 Checklist de Migração — Janio Pontes SaaS

Referências de arquitetura: [RLS Multi-Tenant](./doc_arquitetura_rls_multitenant.md) · [Segurança e Deploy](./doc_seguranca_deploy_gcp.md) · [Chatwoot Infra](./doc_chatwoot_infra.md)
Deploys: Todos os deploys serão realizados exclusivamente pelo usuario.
---

## ✅ Concluído
- [x] Fase 1 — Inicialização do Banco (Cloud SQL, Alembic, RLS, Super Admin)
- [x] Fase 2.1–2.3 — Script de migração GAS → PostgreSQL executado (129 clientes, 58 regras, 10 usuários, 69 workflows)
- [x] Fase 3 — Chatwoot integrado (SDK, WhatsApp Cloud API, Central de Atendimento via iframe)
  - [x] Resolução de conectividade com WhatsApp (Injeção de Permanent Token da Meta)
  - [x] Configuração da Ponte (Bridge) em Python (`typebot-bridge` rodando em background na porta 8002)
  - [x] Bypassing da trava de SSRF do Chatwoot usando rota `/typebot-webhook` no Nginx
  - [x] Correção do Typebot Viewer: Adicionadas variáveis ausentes (`NEXTAUTH_URL` e `ENCRYPTION_SECRET`) no `docker-compose.yml`
  - [x] Desativação da "Atribuição Automática" na Inbox do WhatsApp (para permitir que mensagens nasçam como Pendentes e acionem o bot)
  - [x] Redirecionamento da Bridge para a URL do **Viewer** (`https://bot.janiopontes.com.br`) com o Public ID correto (`atendimento-razjlcs`)
## 📧 Modo Sandbox (Ativo)
E-mails redirecionados para `janiopontes@janiopontes.com.br`. Para liberar: `EMAIL_MODE=intercept` → `production` (`.env` + `deploy.ps1`).

---

## 🔜 Próximos Passos

### Fase 3.5: Otimização de Custos (Migração Região us-east1) [CONCLUÍDO]
- [x] Limpar Artifact Registry via script no deploy (manter últimas 3 imagens).
- [x] Migrar bucket do Cloud Storage de `southamerica-east1` para `us-east1`.
- [x] Migrar instâncias de banco de dados (`jpsaas-db` e Chatwoot) para nova VM em `us-east1`.
- [x] Criar snapshot da VM Chatwoot/Typebot e restaurar em nova instância `e2-medium` em `us-east1`.
- [x] Alterar deploy.ps1 e Firebase Hosting para publicar backend em `us-east1`.
- [x] Descomissionar recursos ociosos em `southamerica-east1` (DB, VM, IP, Bucket, Cloud Run).

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
