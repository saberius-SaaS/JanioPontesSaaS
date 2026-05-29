# 🚀 Checklist Final de Migração (Status Board)

Este documento centraliza as tarefas finais da migração do sistema GAS para GCP.
Todo o conhecimento teórico e arquitetural foi transferido para a base de conhecimento focada:
- 📖 [Arquitetura RLS e Multi-Tenant](./doc_arquitetura_rls_multitenant.md)
- 📖 [Segurança, IAM e Deploy GCP](./doc_seguranca_deploy_gcp.md)
- 📖 [Infraestrutura Chatwoot](./doc_chatwoot_infra.md)

---

## 📧 Modo Sandbox (Interceptação de E-mails)
O sistema opera em **modo de interceptação**: todas as funcionalidades rodam 100% (uploads reais, links acessíveis, e-mails reais via Gmail API), mas **todos os e-mails são redirecionados exclusivamente para `janiopontes@janiopontes.com.br`**, independentemente do destinatário original.

Cada e-mail interceptado contém:
- Um banner amarelo indicando o destinatário original.
- O assunto prefixado com `[INTERCEPTADO de cliente@email.com]`.

### 🔀 Procedimento de Go-Live (Liberar comunicação para clientes)
Quando todos os testes forem aprovados, basta alterar **UMA variável** em dois lugares:

| Arquivo | Variável | Valor Atual | Valor Go-Live |
|---|---|---|---|
| `.env` (local) | `EMAIL_MODE` | `intercept` | `production` |
| `deploy.ps1` (Cloud Run) | `EMAIL_MODE` na lista `$ENV_VARS` | `intercept` | `production` |

Após a alteração, rode `.\deploy.ps1` para publicar. Nenhuma outra mudança de código é necessária.

- [ ] **9.3.1.** Verificar se o Cloud SQL aceita conexões *apenas via Unix Socket* (sem IP público exposto).
- [ ] **9.3.2.** Criar usuário PostgreSQL dedicado para a aplicação (`app_user`) com privilégios mínimos.
- [ ] **9.3.4.** Habilitar backups automáticos no Cloud SQL com retenção de 7 dias.
- [ ] **9.4.3.** Escrever teste automatizado (pytest) para RLS (validação cruzada entre tenants).
- [ ] **9.4.4.** Verificar se `app.bypass_rls = 'on'` existe *somente* em rotas internas (scheduler, seed).
- [ ] **9.5.1.** Auditar todas as rotas FastAPI garantindo `Depends(require_login)` ou `Depends(verify_scheduler_key)`.
- [ ] **9.5.3.** Adicionar *rate limiting* nas rotas públicas (especialmente `/login`).

## 🔶 Etapa 10: Homologação Final e Migração de Dados (Pendências)
- [ ] **10.2.1.** Travar a edição das planilhas do GAS atual (modo leitura).
- [ ] **10.3.1.** Habilitar script de Reverse Sync: Cada novo registro no banco salva uma cópia na planilha antiga (Rollback).
- [ ] **10.3.2.** Manter este script rodando por 72h em produção.

## 🚀 Etapa 11: Go-Live (Lançamento em Produção)
- [ ] **11.1.1.** Acessar gerenciador de DNS do domínio da empresa.
- [ ] **11.1.2.** Criar registro CNAME/A apontando para o Cloud Run (`app.janiopontes.com.br`).
- [ ] **11.1.3.** Aguardar propagação e emissão do certificado SSL (Automático pelo Google).
- [ ] **11.2.1.** Comunicar à equipe e clientes a nova URL de acesso.
- [ ] **11.2.2.** Iniciar a operação exclusiva no novo sistema.
- [ ] **11.3.1.** Acompanhar os logs no *Google Cloud Logging* intensivamente por 48h.
- [ ] **11.3.2.** Fim da janela de 72h: Desligar o *Reverse Sync*.
- [ ] **11.3.3.** Arquivar os scripts antigos do Google Apps Script definitivamente.
