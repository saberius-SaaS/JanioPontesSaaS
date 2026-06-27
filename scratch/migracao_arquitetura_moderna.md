# 🚀 Checklist de Migração — Janio Pontes SaaS

Referências de arquitetura: [RLS Multi-Tenant](./doc_arquitetura_rls_multitenant.md) · [Segurança e Deploy](./doc_seguranca_deploy_gcp.md) · [Chatwoot Infra](./doc_chatwoot_infra.md)
Deploys: Todos os deploys serão realizados exclusivamente pelo usuario.
---

## 📧 Modo Produção (Ativo)
E-mails sendo enviados normalmente. Flag `EMAIL_MODE=production` ativada.

---

## 🔜 Próximos Passos

### Fase 2.4 — Testes Finais
- [ ] Testar intensivamente a plataforma (CRUD, webhooks, fluxos de atendimento na nova região)

### Fase 4 — Cutover (A Grande Virada)
- [x] Travar planilhas do GAS (modo leitura) para evitar novas edições pela equipe
- [x] Validar conectividade: Garantir que o IP local da execução está autorizado no Firewall do Cloud SQL (evitar erro de Connection Timeout)
- [x] Wipe de Dados Seguro: Executar `python scripts/limpar_carga.py` (evita quebra da Foreign Key `usuarios_equipes` e preserva o Tenant/Admin)
- [x] Carga Base de Cadastros: Executar `python scripts/migracao_gas_to_pg.py`
- [x] Carga Operacional de Tarefas e Histórico: Executar `python scripts/import_tarefas_historico.py`
- [x] Carga de Protocolos: Executar `python scripts/migrar_protocolos.py`
- [x] **Ação Manual Obrigatória:** Acessar menu *Equipes de Trabalho* no SaaS, recriar os times (Contábil A, Fiscal A, etc) e **adicionar os respectivos membros**. Isso vincula as tarefas antigas ao novo "Ranking de Produtividade".
- [x] **Ação Manual Obrigatória:** Configurar **Google Cloud Scheduler**: Criar o Job `jp-saas-whatsapp-reminders` apontando para `/scheduler/whatsapp-reminders` (POST) com o cabeçalho `X-Scheduler-Key`. Use a frequência `0 9 * * 1-5` para rodar apenas de Segunda a Sexta (às 09:00), substituindo a rotina antiga do GAS.
- [x] **Validação com Prova Real:** Rodar `python scripts/validacao_migracao.py` para comparar totais do banco contra o GAS (Todos os indicadores devem dar "OK")
- [x] Validar Dashboard Web: Confirmar se Pendentes, Entregas e Atrasos refletem a prova real no front-end
- [ ] **Teste de WhatsApp:** Executar `scripts/teste_whatsapp_reminder.py` após a Meta aprovar o template `automatico_protocolos`.

### Fase 5 — Go-Live
- [x] Habilitar Reverse Sync (backup para planilhas)
- [x] Mudar `EMAIL_MODE` para `production`
- [x] Operação exclusiva em `app.janiopontes.com.br`
- [ ] Monitorar logs (Google Cloud Logging) por 48h
- [ ] Desligar Reverse Sync após 72h
- [ ] Arquivar scripts do Google Apps Script
